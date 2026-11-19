"""
TableGridExtractorV1A.py

Combines bbox-based candidate grid extraction (V3 algorithm) with
GridModelV1 heatmap confidence scoring.

Post-processing pipeline
------------------------
1. Accept cell bboxes (optional) -> if not provided, extract automatically
   from the GridModelV1 DB head output (db_prob map).
2. Resize input image to model input size.
3. Run GridModelV1 ONNX inference -> h_heatmap (H_out,), v_heatmap (W_out,),
   db_prob (input_h, input_w).
4. Resize heatmaps to input image size.
5. For each candidate grid line, sample mean heatmap value within a
   neighborhood band -> confidence score.
6. Remove candidate lines whose confidence is below threshold.
7. Optionally run _post_process_grid -> CellInfo with span.

bbox source priority
--------------------
- Caller-supplied bboxes  : used as-is (same behaviour as before).
- bboxes=None             : cell bboxes are extracted from the db_prob map
                            produced by the same ONNX inference pass,
                            so no extra network call is needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import onnxruntime as ort

from .table_grid_types import GridPrediction, CellInfo
from .common_util import make_session

# ---------------------------------------------------------------------------
# Candidate grid extraction (V3 algorithm)
# ---------------------------------------------------------------------------

def _find_grid_lines_by_empty_space(
    candidate_boundaries: set,
    all_cell_bboxes: list,
    is_horizontal_coord: bool,
    min_empty_gap_size: float,
) -> list:
    """
    Derive grid lines from candidate boundary coordinates by detecting
    empty strips between cell bboxes.

    Strips where no same-row/column cell strictly enters the interior are
    treated as grid line candidates. The midpoint of each such strip is
    registered as a grid line regardless of gap size.
    """
    if not candidate_boundaries:
        return []

    sorted_boundaries = sorted(list(candidate_boundaries))
    final_lines = set()

    for i in range(len(sorted_boundaries) - 1):
        coord1 = sorted_boundaries[i]
        coord2 = sorted_boundaries[i + 1]
        gap_size = coord2 - coord1

        if gap_size < 0:
            continue

        is_empty_strip = True
        for bbox in all_cell_bboxes:
            bx1, by1, bx2, by2 = bbox
            if is_horizontal_coord:
                same_row = (
                    abs(by1 - coord1) <= min_empty_gap_size or
                    abs(by2 - coord1) <= min_empty_gap_size or
                    abs(by1 - coord2) <= min_empty_gap_size or
                    abs(by2 - coord2) <= min_empty_gap_size
                )
                if not same_row:
                    continue
                if by2 > coord1 and by1 < coord2:
                    is_empty_strip = False
                    break
            else:
                same_col = (
                    abs(bx1 - coord1) <= min_empty_gap_size or
                    abs(bx2 - coord1) <= min_empty_gap_size or
                    abs(bx1 - coord2) <= min_empty_gap_size or
                    abs(bx2 - coord2) <= min_empty_gap_size
                )
                if not same_col:
                    continue
                if bx2 > coord1 and bx1 < coord2:
                    is_empty_strip = False
                    break

        if is_empty_strip:
            final_lines.add(int(round((coord1 + coord2) / 2)))

    return sorted(list(final_lines))


def extract_candidate_grid(
    bboxes: list,
    orig_h: int,
    orig_w: int,
    grid_margin_px: float = 5.0,
) -> tuple:
    """
    Derive candidate h/v grid lines from cell bboxes.

    Returns
    -------
    (candidate_h_lines, candidate_v_lines, cells_bbox_shrunk)
    All coordinates are in input image pixel space.
    """
    all_h_boundaries = set()
    all_v_boundaries = set()
    cells_bbox_shrunk = []

    for bbox in bboxes:
        x1_f, y1_f, x2_f, y2_f = bbox

        x1, y1 = int(round(x1_f)), int(round(y1_f))
        x2, y2 = int(round(x2_f)), int(round(y2_f))
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(orig_w, x2), min(orig_h, y2)

        if x2 <= x1 or y2 <= y1:
            continue

        w = x2 - x1
        h = y2 - y1
        x_shrink = 1 if w >= 3 else 0
        y_shrink = 1 if h >= 3 else 0
        sx1 = x1 + x_shrink
        sy1 = y1 + y_shrink
        sx2 = x2 - x_shrink
        sy2 = y2 - y_shrink
        cells_bbox_shrunk.append([sx1, sy1, sx2, sy2])

        all_h_boundaries.add(sy1)
        all_h_boundaries.add(sy2)
        all_v_boundaries.add(sx1)
        all_v_boundaries.add(sx2)

    h_lines = _find_grid_lines_by_empty_space(
        all_h_boundaries, cells_bbox_shrunk,
        is_horizontal_coord=True,
        min_empty_gap_size=grid_margin_px,
    )
    v_lines = _find_grid_lines_by_empty_space(
        all_v_boundaries, cells_bbox_shrunk,
        is_horizontal_coord=False,
        min_empty_gap_size=grid_margin_px,
    )

    return h_lines, v_lines, cells_bbox_shrunk


# ---------------------------------------------------------------------------
# Heatmap confidence scoring
# ---------------------------------------------------------------------------

def _sample_heatmap_confidence(
    heatmap_1d: np.ndarray,
    positions_px: list,
    band_radius_px: int,
) -> np.ndarray:
    """
    For each candidate line position, compute the mean heatmap value
    within [pos - band_radius, pos + band_radius].

    Parameters
    ----------
    heatmap_1d    : 1D float32 array of length N (already resized to image size)
    positions_px  : list of candidate line positions in pixel coords
    band_radius_px: half-width of the sampling band in pixels

    Returns
    -------
    np.ndarray of shape (len(positions_px),) with confidence scores in [0, 1].
    """
    n = len(heatmap_1d)
    confidences = np.zeros(len(positions_px), dtype=np.float32)
    for i, pos in enumerate(positions_px):
        lo = max(0, int(round(pos)) - band_radius_px)
        hi = min(n, int(round(pos)) + band_radius_px + 1)
        if hi > lo:
            confidences[i] = float(heatmap_1d[lo:hi].mean())
    return confidences


# ---------------------------------------------------------------------------
# Main extractor class
# ---------------------------------------------------------------------------

class TableGridExtractorV1A:
    """
    Hybrid table grid extractor:
    - Candidate grid lines derived from cell bboxes (rule-based, V3 algorithm).
    - GridModelV1 heatmap used as confidence to filter spurious candidates.
    - When bboxes are not supplied, cell bboxes are extracted automatically
      from the DB probability map produced by the same inference pass.
    """

    def __init__(
        self,
        onnx_path: str | Path,
        h_on_threshold: float = 0.15,
        v_on_threshold: float = 0.5,
        band_radius_ratio: float = 0.02,
        grid_margin_px: float = 5.0,
        db_prob_threshold: float = 0.3,
        db_min_area: int = 10,
        providers: list | None = None,
    ) -> None:
        """
        Parameters
        ----------
        onnx_path          : path to exported GridModelV1 .onnx file
        h_on_threshold     : minimum heatmap confidence to keep a candidate h line
        v_on_threshold     : minimum heatmap confidence to keep a candidate v line
        band_radius_ratio  : sampling band half-width as a fraction of image size
                             (e.g. 0.02 = 2% of image height/width)
        grid_margin_px     : alignment tolerance for candidate grid extraction
        db_prob_threshold  : binarization threshold applied to db_prob map when
                             extracting cell bboxes automatically (used only when
                             bboxes=None is passed to predict_grid / predict)
        db_min_area        : minimum contour area in pixels to accept as a cell bbox
                             during automatic DB extraction
        providers          : ONNX Runtime execution providers
        """
        if providers is None:
            providers = ["CPUExecutionProvider"]

        self.onnx_path         = Path(onnx_path)
        self.h_on_threshold    = h_on_threshold
        self.v_on_threshold    = v_on_threshold
        self.band_radius_ratio = band_radius_ratio
        self.grid_margin_px    = grid_margin_px
        self.db_prob_threshold = db_prob_threshold
        self.db_min_area       = db_min_area

        self._sess = make_session(str(self.onnx_path), providers)

        inp = self._sess.get_inputs()[0]
        self._input_h = int(inp.shape[2])
        self._input_w = int(inp.shape[3])

        # Resolve output indices by name so the class is robust to output
        # ordering differences across export versions.
        output_names = [o.name for o in self._sess.get_outputs()]
        self._idx_h_heatmap = output_names.index("h_heatmap")
        self._idx_v_heatmap = output_names.index("v_heatmap")
        self._idx_db_prob   = output_names.index("db_prob") if "db_prob" in output_names else None

        dummy   = np.zeros((1, 3, self._input_h, self._input_w), dtype=np.float32)
        outputs = self._sess.run(None, {"image": dummy})
        self._out_h = int(outputs[self._idx_h_heatmap].shape[1])
        self._out_w = int(outputs[self._idx_v_heatmap].shape[1])

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def _run_inference(self, image_bgr: np.ndarray) -> tuple:
        """
        Run GridModelV1 inference and return heatmaps and db_prob map,
        all resized to the original image dimensions.

        Returns
        -------
        (h_heatmap, v_heatmap, db_prob_map)
        h_heatmap   : (orig_h,)          float32
        v_heatmap   : (orig_w,)          float32
        db_prob_map : (orig_h, orig_w)   float32, or None if the ONNX model
                      does not export the db_prob output
        """
        import cv2

        orig_h, orig_w = image_bgr.shape[:2]

        img_resized = cv2.resize(image_bgr, (self._input_w, self._input_h))
        img_rgb = img_resized[:, :, ::-1].astype(np.float32)
        mn, mx = img_rgb.min(), img_rgb.max()
        if mx > mn:
            img_rgb = (img_rgb - mn) / (mx - mn)
        else:
            img_rgb = np.zeros_like(img_rgb)
        inp = img_rgb.transpose(2, 0, 1)[np.newaxis]

        outputs = self._sess.run(None, {"image": inp})

        h_raw = outputs[self._idx_h_heatmap][0]  # (H_out,)
        v_raw = outputs[self._idx_v_heatmap][0]  # (W_out,)

        # Resize 1D heatmaps to input image dimensions
        h_heatmap = cv2.resize(
            h_raw[np.newaxis, :].astype(np.float32),
            (orig_h, 1),
            interpolation=cv2.INTER_LINEAR,
        )[0]  # (orig_h,)
        v_heatmap = cv2.resize(
            v_raw[np.newaxis, :].astype(np.float32),
            (orig_w, 1),
            interpolation=cv2.INTER_LINEAR,
        )[0]  # (orig_w,)

        # Resize db_prob map to original image size
        db_prob_map: np.ndarray | None = None
        if self._idx_db_prob is not None:
            db_raw = outputs[self._idx_db_prob][0, 0]  # (model_h, model_w)
            db_prob_map = cv2.resize(
                db_raw.astype(np.float32),
                (orig_w, orig_h),
                interpolation=cv2.INTER_LINEAR,
            )  # (orig_h, orig_w)

        return h_heatmap, v_heatmap, db_prob_map

    # ------------------------------------------------------------------
    # DB-based bbox extraction
    # ------------------------------------------------------------------

    def _extract_bboxes_from_db(
        self,
        db_prob_map: np.ndarray,
    ) -> list:
        """
        Extract cell bounding boxes from a DB probability map.

        Steps
        -----
        1. Binarize the map with db_prob_threshold.
        2. Find external contours in the binary mask.
        3. Convert each contour whose area >= db_min_area to an
           axis-aligned bounding box [x1, y1, x2, y2].

        Parameters
        ----------
        db_prob_map : (H, W) float32 array with values in [0, 1]

        Returns
        -------
        List of [x1, y1, x2, y2] bounding boxes in pixel coordinates.
        """
        import cv2

        binary = (db_prob_map >= self.db_prob_threshold).astype(np.uint8) * 255
        contours, _ = cv2.findContours(
            binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        bboxes = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.db_min_area:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            bboxes.append([x, y, x + w, y + h])
        return bboxes

    # ------------------------------------------------------------------
    # Grid prediction
    # ------------------------------------------------------------------

    @staticmethod
    def _filter_empty_lines(
        lines: list[float],
        centers: list[float],
        image_size: float,
    ) -> list[float]:
        """
        Remove adjacent line pairs that have no bbox center between them,
        and handle empty outer gaps:

        - If the gap between 0 and the first line contains no bbox center,
          the first line is moved to 0.0 (collapsed to the image edge).
        - If the gap between the last line and image_size contains no bbox
          center, the last line is removed entirely.
        - For inner lines: when two adjacent lines share an empty gap between
          them, they are replaced by their midpoint.

        The process repeats until stable.

        Parameters
        ----------
        lines      : sorted list of boundary coordinates
        centers    : list of bbox center coordinates (along same axis)
        image_size : image dimension along this axis (H or W)

        Returns
        -------
        Filtered and possibly merged list of boundary lines (sorted).
        """
        if not lines:
            return lines

        current = sorted(lines)
        changed = True

        while changed:
            changed = False
            if not current:
                break
            edges  = [0.0] + current + [float(image_size)]
            n_gaps = len(edges) - 1

            gap_empty = [
                not any(edges[i] < c < edges[i + 1] for c in centers)
                for i in range(n_gaps)
            ]

            # Handle leading empty gap: move first line to 0.0
            if gap_empty[0] and current[0] != 0.0:
                current[0] = 0.0
                changed = True
                continue

            # Handle trailing empty gap: remove last line
            if gap_empty[-1] and current:
                current.pop()
                changed = True
                continue

            # Merge adjacent inner lines that share an empty gap
            merged: list[float] = []
            skip_next = False
            for i in range(len(current)):
                if skip_next:
                    skip_next = False
                    continue
                gap_right_empty = gap_empty[i + 1]
                if gap_right_empty and i + 1 < len(current):
                    merged.append((current[i] + current[i + 1]) / 2.0)
                    skip_next = True
                    changed   = True
                else:
                    merged.append(current[i])
            current = sorted(merged)

        return current

    def predict_grid(
        self,
        image_bgr: np.ndarray,
        bboxes: list | None = None,
    ) -> GridPrediction:
        """
        Derive candidate grid lines from bboxes and filter by heatmap confidence.

        Parameters
        ----------
        image_bgr : cropped table BGR image (any size)
        bboxes    : list of [x1, y1, x2, y2] cell bbox pixel coordinates.
                    When None, bboxes are extracted automatically from the
                    db_prob map produced by the same inference pass.

        Returns
        -------
        GridPrediction with filtered h/v lines and per-line confidence scores.
        GridPrediction.db_prob_map is populated when DB auto-extraction is used
        or when the ONNX model exports a db_prob output.
        """
        orig_h, orig_w = image_bgr.shape[:2]

        # Single inference call: heatmaps + db_prob map
        h_heatmap, v_heatmap, db_prob_map = self._run_inference(image_bgr)

        # Resolve bboxes: use caller-supplied list, or fall back to DB extraction
        if bboxes is None:
            if db_prob_map is None:
                raise RuntimeError(
                    "bboxes=None requires the ONNX model to export 'db_prob', "
                    "but it was not found in the model outputs."
                )
            bboxes = self._extract_bboxes_from_db(db_prob_map)

        # Derive candidate grid lines from bboxes
        cand_h, cand_v, _ = extract_candidate_grid(
            bboxes, orig_h, orig_w, self.grid_margin_px
        )

        # Sample heatmap confidence for each candidate line
        h_band = max(1, int(round(orig_h * self.band_radius_ratio)))
        v_band = max(1, int(round(orig_w * self.band_radius_ratio)))

        h_conf = _sample_heatmap_confidence(h_heatmap, cand_h, h_band)
        v_conf = _sample_heatmap_confidence(v_heatmap, cand_v, v_band)

        # Filter candidates by confidence threshold
        h_lines = [y for y, c in zip(cand_h, h_conf) if c >= self.h_on_threshold]
        v_lines = [x for x, c in zip(cand_v, v_conf) if c >= self.v_on_threshold]

        return GridPrediction(
            h_lines=sorted(h_lines),
            v_lines=sorted(v_lines),
            h_heatmap=h_heatmap,
            v_heatmap=v_heatmap,
            h_confidences=h_conf,
            v_confidences=v_conf,
            db_prob_map=db_prob_map,
        )

    def predict(
        self,
        image_bgr: np.ndarray,
        bboxes: list | None = None,
        texts: list | None = None,
        span_threshold: float = 0.1,
    ) -> tuple:
        """
        Predict grid and assign bboxes to grid cells.

        Parameters
        ----------
        image_bgr      : cropped table BGR image
        bboxes         : list of [x1, y1, x2, y2] in crop space, or None to
                         extract bboxes automatically from the DB output.
                         An empty list bypasses both DB extraction and
                         post-processing (returns empty CellInfo list).
        texts          : text strings aligned with bboxes
        span_threshold : fractional overlap to trigger span expansion

        Returns
        -------
        (GridPrediction, list[CellInfo])
        """
        # An explicitly empty list means: skip cell assignment entirely
        if isinstance(bboxes, (list, np.ndarray)) and len(bboxes) == 0:
            orig_h, orig_w = image_bgr.shape[:2]
            _, _, db_prob_map = self._run_inference(image_bgr)
            return GridPrediction(
                h_lines=[],
                v_lines=[],
                h_heatmap=np.zeros(orig_h, dtype=np.float32),
                v_heatmap=np.zeros(orig_w, dtype=np.float32),
                h_confidences=np.array([], dtype=np.float32),
                v_confidences=np.array([], dtype=np.float32),
                db_prob_map=db_prob_map,
            ), []

        # predict_grid handles bboxes=None via DB auto-extraction
        grid = self.predict_grid(image_bgr, bboxes)

        # Resolve effective bbox list for _filter_empty_lines and _post_process_grid.
        # All bbox coordinates are in crop space (origin = 0,0).
        effective_bboxes: list
        if bboxes is None:
            effective_bboxes = self._extract_bboxes_from_db(grid.db_prob_map) \
                if grid.db_prob_map is not None else []
        else:
            effective_bboxes = list(bboxes)

        if not effective_bboxes:
            return grid, []

        # Remove grid lines that have no bbox center between them
        crop_h = float(image_bgr.shape[0])
        crop_w = float(image_bgr.shape[1])
        cx_list = sorted((float(b[0]) + float(b[2])) / 2.0 for b in effective_bboxes)
        cy_list = sorted((float(b[1]) + float(b[3])) / 2.0 for b in effective_bboxes)

        filtered_h = self._filter_empty_lines(grid.h_lines, cy_list, crop_h)
        filtered_v = self._filter_empty_lines(grid.v_lines, cx_list, crop_w)

        grid = GridPrediction(
            h_lines=filtered_h,
            v_lines=filtered_v,
            h_heatmap=grid.h_heatmap,
            v_heatmap=grid.v_heatmap,
            h_confidences=grid.h_confidences,
            v_confidences=grid.v_confidences,
            db_prob_map=grid.db_prob_map,
        )

        bboxes_arr = np.asarray(effective_bboxes, dtype=np.float32)
        cells = self._post_process_grid(
            bboxes_page=bboxes_arr,
            grid=grid,
            span_threshold=span_threshold,
        )

        if texts is not None:
            for cell in cells:
                if 0 <= cell.bbox_idx < len(texts):
                    cell.text = texts[cell.bbox_idx]

        return grid, cells

    # ------------------------------------------------------------------
    # Grid-based bbox assignment (same logic as V1)
    # ------------------------------------------------------------------

    def _post_process_grid(
        self,
        bboxes_page: np.ndarray,
        grid: GridPrediction,
        span_threshold: float,
    ) -> list:
        if grid.h_lines:
            last_h = sorted(grid.h_lines)[-1]
            row_edges = [0.0] + sorted(grid.h_lines) + [max(last_h * 2, last_h + 1)]
        else:
            row_edges = [0.0, 1.0]

        if grid.v_lines:
            last_v = sorted(grid.v_lines)[-1]
            col_edges = [0.0] + sorted(grid.v_lines) + [max(last_v * 2, last_v + 1)]
        else:
            col_edges = [0.0, 1.0]

        def find_cell_idx(pos, edges):
            for i in range(len(edges) - 1):
                if edges[i] <= pos < edges[i + 1]:
                    return i
            return max(0, len(edges) - 2)

        results = []
        for i, bbox in enumerate(bboxes_page):
            x0 = float(bbox[0])
            y0 = float(bbox[1])
            x1 = float(bbox[2])
            y1 = float(bbox[3])
            cx = (x0 + x1) / 2.0
            cy = (y0 + y1) / 2.0

            base_row = find_cell_idx(cy, row_edges)
            base_col = find_cell_idx(cx, col_edges)
            row_start, row_end = base_row, base_row + 1
            col_start, col_end = base_col, base_col + 1

            r = base_row
            while r > 0:
                h = row_edges[r] - row_edges[r - 1]
                if h > 0 and (row_edges[r] - y0) / h > span_threshold:
                    row_start = r - 1; r -= 1
                else:
                    break
            r = base_row
            while r < len(row_edges) - 2:
                h = row_edges[r + 1] - row_edges[r]
                if h > 0 and (y1 - row_edges[r + 1]) / h > span_threshold:
                    row_end = r + 2; r += 1
                else:
                    break
            c = base_col
            while c > 0:
                w = col_edges[c] - col_edges[c - 1]
                if w > 0 and (col_edges[c] - x0) / w > span_threshold:
                    col_start = c - 1; c -= 1
                else:
                    break
            c = base_col
            while c < len(col_edges) - 2:
                w = col_edges[c + 1] - col_edges[c]
                if w > 0 and (x1 - col_edges[c + 1]) / w > span_threshold:
                    col_end = c + 2; c += 1
                else:
                    break

            results.append(CellInfo(
                bbox_idx=i, row_start=row_start, row_end=row_end,
                col_start=col_start, col_end=col_end,
                row=base_row, col=base_col,
            ))

        return results

    # ------------------------------------------------------------------
    # Visualization
    # ------------------------------------------------------------------

    def visualize(
        self,
        image_bgr: np.ndarray,
        pred: GridPrediction,
        bboxes: list | None = None,
        max_dim: int = 1000,
    ) -> np.ndarray:
        """
        Visualize candidate lines (all) vs filtered lines, and heatmaps.

        Layout (2x2)
        ------------
        (1,1) image + filtered grid lines (green h, orange v)
              + rejected candidates (red) + bbox rectangles (cyan)
        (1,2) h_heatmap tiled to 2D with candidate h line positions marked
        (2,1) v_heatmap tiled to 2D with candidate v line positions marked
        (2,2) db_prob_map as a heatmap when available; otherwise a
              confidence bar chart per candidate line

        Parameters
        ----------
        image_bgr : original BGR image
        pred      : GridPrediction from predict_grid() or predict()
        bboxes    : bbox list used for candidate extraction (for overlay).
                    When None, bboxes stored in pred.db_prob_map are used
                    to recompute candidates for the overlay.
        max_dim   : maximum single-panel dimension before downscaling
        """
        import cv2

        orig_h, orig_w = image_bgr.shape[:2]

        # Resolve the bbox list used to recompute pre-filter candidates
        vis_bboxes: list
        if bboxes is not None:
            vis_bboxes = list(bboxes)
        elif pred.db_prob_map is not None:
            vis_bboxes = self._extract_bboxes_from_db(pred.db_prob_map)
        else:
            vis_bboxes = []

        # Recompute all candidates (before filtering) for visualization
        cand_h, cand_v, _ = extract_candidate_grid(
            vis_bboxes, orig_h, orig_w, self.grid_margin_px
        )
        h_band = max(1, int(round(orig_h * self.band_radius_ratio)))
        v_band = max(1, int(round(orig_w * self.band_radius_ratio)))
        h_conf = _sample_heatmap_confidence(pred.h_heatmap, cand_h, h_band)
        v_conf = _sample_heatmap_confidence(pred.v_heatmap, cand_v, v_band)

        kept_h = set(pred.h_lines)
        kept_v = set(pred.v_lines)

        # Panel (1,1): image with bbox rectangles and grid lines
        overlay = image_bgr.copy()
        for bbox in vis_bboxes:
            x1, y1, x2, y2 = [int(round(v)) for v in bbox]
            cv2.rectangle(overlay, (x1, y1), (x2, y2), (255, 255, 0), 1)
        for y, c in zip(cand_h, h_conf):
            yp = int(round(y))
            if y in kept_h:
                cv2.line(overlay, (0, yp), (orig_w, yp), (0, 255, 0), 1)
                cv2.putText(overlay, f"{c:.2f}", (2, max(yp - 2, 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.28, (0, 255, 0), 1)
            else:
                cv2.line(overlay, (0, yp), (orig_w, yp), (0, 0, 255), 1)
                cv2.putText(overlay, f"{c:.2f}", (2, max(yp - 2, 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.28, (0, 0, 255), 1)
        for x, c in zip(cand_v, v_conf):
            xp = int(round(x))
            if x in kept_v:
                cv2.line(overlay, (xp, 0), (xp, orig_h), (255, 128, 0), 1)
            else:
                cv2.line(overlay, (xp, 0), (xp, orig_h), (0, 0, 255), 1)

        # Panel (1,2): h_heatmap tiled to 2D
        h_2d = np.tile(pred.h_heatmap[:, np.newaxis], (1, orig_w))
        h_panel = cv2.applyColorMap(
            (h_2d * 255).clip(0, 255).astype(np.uint8), cv2.COLORMAP_JET
        )
        for y in cand_h:
            yp = int(round(y))
            color = (0, 255, 0) if y in kept_h else (0, 0, 255)
            cv2.line(h_panel, (0, yp), (orig_w, yp), color, 1)
        cv2.putText(h_panel, f"h_thr={self.h_on_threshold:.2f}",
                    (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)

        # Panel (2,1): v_heatmap tiled to 2D
        v_2d = np.tile(pred.v_heatmap[np.newaxis, :], (orig_h, 1))
        v_panel = cv2.applyColorMap(
            (v_2d * 255).clip(0, 255).astype(np.uint8), cv2.COLORMAP_JET
        )
        for x in cand_v:
            xp = int(round(x))
            color = (0, 255, 0) if x in kept_v else (0, 0, 255)
            cv2.line(v_panel, (xp, 0), (xp, orig_h), color, 1)
        cv2.putText(v_panel, f"v_thr={self.v_on_threshold:.2f}",
                    (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)

        # Panel (2,2): db_prob_map heatmap when available; confidence bars otherwise
        if pred.db_prob_map is not None:
            db_panel = cv2.applyColorMap(
                (pred.db_prob_map * 255).clip(0, 255).astype(np.uint8),
                cv2.COLORMAP_JET,
            )
            db_panel = cv2.resize(db_panel, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
            # Draw DB-extracted bbox contours on the db panel
            for bbox in vis_bboxes:
                x1, y1, x2, y2 = [int(round(v)) for v in bbox]
                cv2.rectangle(db_panel, (x1, y1), (x2, y2), (255, 255, 255), 1)
            cv2.putText(db_panel, f"db_thr={self.db_prob_threshold:.2f}  n={len(vis_bboxes)}",
                        (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
            bottom_right = db_panel
        else:
            bar_panel = np.zeros((orig_h, orig_w, 3), dtype=np.uint8)
            all_lines = (
                [(y, c, True)  for y, c in zip(cand_h, h_conf)] +
                [(x, c, False) for x, c in zip(cand_v, v_conf)]
            )
            n = len(all_lines)
            if n > 0:
                bar_w = max(1, orig_w // n)
                for idx, (pos, conf, is_h) in enumerate(all_lines):
                    bx1 = idx * bar_w
                    bx2 = bx1 + bar_w - 1
                    bar_h_px = int(conf * (orig_h - 20))
                    color = (0, 200, 0) if is_h else (200, 100, 0)
                    thr = self.h_on_threshold if is_h else self.v_on_threshold
                    if conf < thr:
                        color = (0, 0, 180)
                    cv2.rectangle(bar_panel,
                                   (bx1, orig_h - bar_h_px), (bx2, orig_h),
                                   color, -1)
                thr_h_y = orig_h - int(self.h_on_threshold * (orig_h - 20))
                thr_v_y = orig_h - int(self.v_on_threshold * (orig_h - 20))
                cv2.line(bar_panel, (0, thr_h_y), (orig_w // 2, thr_h_y), (0, 255, 0), 1)
                cv2.line(bar_panel, (orig_w // 2, thr_v_y), (orig_w, thr_v_y), (200, 100, 0), 1)
            cv2.putText(bar_panel, "Conf: green=h  orange=v  red=rejected",
                        (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (200, 200, 200), 1)
            bottom_right = bar_panel

        # Compose 2x2 panel
        top_row = np.concatenate([overlay,  h_panel],     axis=1)
        bot_row = np.concatenate([v_panel,  bottom_right], axis=1)
        composed = np.concatenate([top_row, bot_row],      axis=0)

        ch, cw = composed.shape[:2]
        if ch > max_dim or cw > max_dim * 2:
            scale    = min(max_dim / ch, max_dim * 2 / cw)
            composed = cv2.resize(
                composed,
                (max(1, int(cw * scale)), max(1, int(ch * scale))),
                interpolation=cv2.INTER_AREA,
            )

        return composed


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import json
    import cv2

    parser = argparse.ArgumentParser(
        description=(
            "Run TableGridExtractorV1A on all images in a directory. "
            "When a JSON sidecar (<image_stem>.json) exists next to the image, "
            "the bboxes stored in it are used directly. "
            "When no sidecar is found, bboxes are extracted automatically from "
            "the DB probability map output of the model (DB auto mode)."
        )
    )
    parser.add_argument("onnx_path", help="Path to the exported GridModelV1 .onnx model.")
    parser.add_argument("image_dir", help="Directory containing input images.")
    parser.add_argument(
        "--h_on_threshold", type=float, default=0.25,
        help="Heatmap confidence threshold for h lines (default: 0.25).",
    )
    parser.add_argument(
        "--v_on_threshold", type=float, default=0.2,
        help="Heatmap confidence threshold for v lines (default: 0.2).",
    )
    parser.add_argument(
        "--band_radius_ratio", type=float, default=0.02,
        help="Sampling band half-width as a fraction of image size (default: 0.02).",
    )
    parser.add_argument(
        "--grid_margin_px", type=float, default=5.0,
        help="Alignment tolerance for candidate grid extraction in px (default: 5.0).",
    )
    parser.add_argument(
        "--db_prob_threshold", type=float, default=0.3,
        help="DB binarization threshold for auto bbox extraction (default: 0.3).",
    )
    parser.add_argument(
        "--db_min_area", type=int, default=10,
        help="Minimum contour area in px for DB bbox extraction (default: 10).",
    )
    parser.add_argument(
        "--extensions", nargs="*",
        default=["png", "jpg", "jpeg", "bmp", "tif", "tiff"],
        help="Image file extensions to scan.",
    )
    parser.add_argument(
        "--max_dim", type=int, default=1400,
        help="Maximum dimension of the visualization panel (default: 1400).",
    )
    parser.add_argument(
        "--save_dir", default=None,
        help="If set, save visualization images to this directory instead of displaying.",
    )
    args = parser.parse_args()

    extractor = TableGridExtractorV1A(
        onnx_path=args.onnx_path,
        h_on_threshold=args.h_on_threshold,
        v_on_threshold=args.v_on_threshold,
        band_radius_ratio=args.band_radius_ratio,
        grid_margin_px=args.grid_margin_px,
        db_prob_threshold=args.db_prob_threshold,
        db_min_area=args.db_min_area,
    )

    image_dir = Path(args.image_dir)
    save_dir  = Path(args.save_dir) if args.save_dir else None
    if save_dir is not None:
        save_dir.mkdir(parents=True, exist_ok=True)

    img_paths: list[Path] = []
    for ext in args.extensions:
        img_paths.extend(sorted(image_dir.glob(f"*.{ext}")))
        img_paths.extend(sorted(image_dir.glob(f"*.{ext.upper()}")))
    img_paths = sorted(set(img_paths))

    if not img_paths:
        print(f"No images found in: {image_dir}")
    else:
        mode = "saving" if save_dir else "displaying (press any key to advance)"
        print(f"Found {len(img_paths)} image(s). Mode: {mode}.")

    for img_path in img_paths:
        img_bgr = cv2.imread(str(img_path))
        if img_bgr is None:
            print(f"Cannot read: {img_path.name}")
            continue

        # Load bboxes from sidecar JSON when available; otherwise use DB auto mode
        json_path = img_path.with_suffix(".json")
        if json_path.exists():
            with open(json_path, "r") as f:
                bboxes = json.load(f)
            bbox_source = f"sidecar ({len(bboxes)} boxes)"
        else:
            bboxes = None  # triggers DB auto-extraction inside predict_grid
            bbox_source = "DB auto"

        pred = extractor.predict_grid(img_bgr, bboxes)
        n_db = len(extractor._extract_bboxes_from_db(pred.db_prob_map)) \
               if bboxes is None and pred.db_prob_map is not None else \
               (len(bboxes) if bboxes is not None else 0)
        print(
            f"{img_path.name}  source={bbox_source}  "
            f"bboxes={n_db}  "
            f"h_lines={len(pred.h_lines)}  v_lines={len(pred.v_lines)}"
        )

        composed = extractor.visualize(img_bgr, pred, bboxes=bboxes, max_dim=args.max_dim)

        if save_dir is not None:
            out_path = save_dir / f"{img_path.stem}_v1a_vis{img_path.suffix}"
            cv2.imwrite(str(out_path), composed)
            print(f"  Saved -> {out_path}")
        else:
            window_title = f"TableGridExtractorV1A - {img_path.name}"
            cv2.imshow(window_title, composed)
            cv2.waitKey(0)
            cv2.destroyWindow(window_title)
