"""
TableGridExtractorV1B.py

Hybrid table grid extractor combining:
  - Rule-based candidate grid lines from bbox geometry (same as V1A).
  - V1-style heatmap threshold + 1D CCL to define active intervals.
  - A candidate line survives if its position falls inside any active
    interval; its confidence score is then 1.0. Lines outside every
    active interval receive score 0.0 and are discarded.

Design philosophy
-----------------
V1  : heatmap CCL determines position directly (coarse but fast).
V1A : bbox geometry determines position; heatmap value at the position
      acts as a soft confidence filter.
V1B : bbox geometry determines position (precise); heatmap CCL defines
      which regions are "active" at all (coarse region gate). A candidate
      that lands inside an active CCL interval is accepted unconditionally
      (score = 1.0). This separates localisation (rule-based) from
      region-level detection (heatmap CCL).

bbox source priority
--------------------
- Caller-supplied bboxes : used as-is.
- bboxes=None            : extracted automatically from the db_prob map
                           produced by the same inference pass (same as V1A).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import onnxruntime as ort

from .table_grid_types import GridPrediction, CellInfo
from .common_util import make_session


# ---------------------------------------------------------------------------
# Candidate grid extraction (V3 algorithm, identical to V1A)
# ---------------------------------------------------------------------------

def _find_grid_lines_by_empty_space(
    candidate_boundaries: set,
    all_cell_bboxes: list,
    is_horizontal_coord: bool,
    min_empty_gap_size: float,
) -> list:
    """
    Derive grid lines from candidate boundary coordinates by detecting
    empty strips between cell bboxes (V3 algorithm, unchanged from V1A).
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
    Derive candidate h/v grid lines from cell bboxes (unchanged from V1A).

    Returns
    -------
    (candidate_h_lines, candidate_v_lines, cells_bbox_shrunk)
    """
    all_h_boundaries: set = set()
    all_v_boundaries: set = set()
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
# V1-style 1D CCL active-interval extraction
# ---------------------------------------------------------------------------

def _ccl_1d_active_intervals(
    heatmap: np.ndarray,
    threshold: float,
) -> list[tuple[int, int]]:
    """
    Apply threshold to a 1D heatmap and return the (start, end) pixel
    intervals of every connected active component.

    Parameters
    ----------
    heatmap   : 1D float32 array (already resized to image pixel space)
    threshold : minimum activation value

    Returns
    -------
    List of (start_px, end_px) tuples, inclusive on both ends, sorted by
    start position.
    """
    active = heatmap >= threshold
    intervals: list[tuple[int, int]] = []
    in_group = False
    group_start = 0

    for i, is_active in enumerate(active):
        if is_active and not in_group:
            in_group = True
            group_start = i
        elif not is_active and in_group:
            intervals.append((group_start, i - 1))
            in_group = False

    if in_group:
        intervals.append((group_start, len(heatmap) - 1))

    return intervals


def _score_candidates_by_ccl_intervals(
    positions_px: list,
    intervals: list[tuple[int, int]],
    heatmap: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Assign score 1.0 to each candidate position that falls inside at least
    one CCL active interval; assign 0.0 otherwise.
    Also return the heatmap value at each candidate position for top_k ranking.

    Parameters
    ----------
    positions_px : list of integer candidate positions in pixel space
    intervals    : list of (start, end) active intervals from CCL
    heatmap      : 1D float32 heatmap array in pixel space

    Returns
    -------
    gate_scores  : np.ndarray of float32, 1.0 if inside interval else 0.0
    heat_scores  : np.ndarray of float32, heatmap value at each candidate position
    """
    gate_scores = np.zeros(len(positions_px), dtype=np.float32)
    heat_scores = np.zeros(len(positions_px), dtype=np.float32)
    n = len(heatmap)
    for i, pos in enumerate(positions_px):
        heat_scores[i] = heatmap[min(int(pos), n - 1)]
        for start, end in intervals:
            if start <= pos <= end:
                gate_scores[i] = 1.0
                break
    return gate_scores, heat_scores


def _apply_top_k_per_interval(
    lines: list,
    intervals: list[tuple[int, int]],
    heat_map: dict,
    top_k: int,
) -> list:
    """
    Within each CCL active interval, retain at most top_k candidates ranked
    by their heatmap value (highest first). Candidates not covered by any
    interval are passed through unchanged (they have already been gate-filtered
    before this call, so in practice none should remain).

    Parameters
    ----------
    lines     : list of candidate positions that passed the CCL gate
    intervals : list of (start, end) active intervals
    heat_map  : dict mapping position -> heatmap value for each line
    top_k     : maximum number of candidates to keep per interval

    Returns
    -------
    Sorted list of surviving candidate positions.
    """
    kept: set = set()
    for start, end in intervals:
        members = [y for y in lines if start <= y <= end]
        if not members:
            continue
        members_sorted = sorted(members, key=lambda y: heat_map.get(y, 0.0), reverse=True)
        for y in members_sorted[:top_k]:
            kept.add(y)
    return sorted(kept)


# ---------------------------------------------------------------------------
# Main extractor class
# ---------------------------------------------------------------------------

class TableGridExtractorV1B:
    """
    Hybrid table grid extractor (V1B).

    Candidate grid lines are derived from cell bbox geometry (V3 rule-based
    algorithm, same as V1A). Active regions are determined by applying V1-style
    heatmap threshold + 1D CCL. A candidate line is kept (score = 1.0) if and
    only if it falls inside a CCL active interval; otherwise it is rejected
    (score = 0.0).

    This decouples localisation (bbox geometry, pixel-accurate) from region
    detection (heatmap CCL, coarse but model-driven).

    When bboxes=None is passed, cell bboxes are extracted automatically from
    the db_prob map produced by the same inference pass (same as V1A).
    """

    def __init__(
        self,
        onnx_path: str | Path,
        h_on_threshold: float = 0.15,
        v_on_threshold: float = 0.4,
        grid_margin_px: float = 5.0,
        db_prob_threshold: float = 0.3,
        db_min_area: int = 10,
        top_k: int = 1,
        providers: list | None = None,
    ) -> None:
        """
        Parameters
        ----------
        onnx_path          : path to exported GridModelV1 .onnx file
        h_on_threshold     : heatmap activation threshold for h CCL intervals
        v_on_threshold     : heatmap activation threshold for v CCL intervals
        grid_margin_px     : alignment tolerance for candidate grid extraction
        db_prob_threshold  : binarization threshold for automatic DB bbox extraction
        db_min_area        : minimum contour area (px) accepted during DB extraction
        top_k              : max candidates kept per CCL interval ranked by heatmap
                             value; candidates beyond top_k are dropped. Use 0 or
                             a negative value to disable (keep all).
        providers          : ONNX Runtime execution providers
        """
        if providers is None:
            providers = ["CPUExecutionProvider"]

        self.onnx_path         = Path(onnx_path)
        self.h_on_threshold    = h_on_threshold
        self.v_on_threshold    = v_on_threshold
        self.grid_margin_px    = grid_margin_px
        self.db_prob_threshold = db_prob_threshold
        self.db_min_area       = db_min_area
        self.top_k             = top_k

        self._sess = make_session(str(self.onnx_path), providers)

        inp = self._sess.get_inputs()[0]
        self._input_h = int(inp.shape[2])
        self._input_w = int(inp.shape[3])

        # Name-based output indexing (robust to export ordering)
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
        db_prob_map : (orig_h, orig_w)   float32, or None if not exported
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

        # Resize 1D heatmaps to input image pixel space
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
    # DB-based bbox extraction (identical to V1A)
    # ------------------------------------------------------------------

    def _extract_bboxes_from_db(self, db_prob_map: np.ndarray) -> list:
        """
        Extract cell bounding boxes from a DB probability map.

        Steps
        -----
        1. Binarize with db_prob_threshold.
        2. Find external contours.
        3. Accept contours whose area >= db_min_area as [x1, y1, x2, y2] boxes.
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
    # Empty-line filtering (identical to V1A)
    # ------------------------------------------------------------------

    @staticmethod
    def _filter_empty_lines(
        lines: list[float],
        centers: list[float],
        image_size: float,
    ) -> list[float]:
        """
        Remove adjacent line pairs that have no bbox center between them.
        Behaviour is identical to V1A._filter_empty_lines.
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

            if gap_empty[0] and current[0] != 0.0:
                current[0] = 0.0
                changed = True
                continue

            if gap_empty[-1] and current:
                current.pop()
                changed = True
                continue

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

    # ------------------------------------------------------------------
    # Grid prediction
    # ------------------------------------------------------------------

    def predict_grid(
        self,
        image_bgr: np.ndarray,
        bboxes: list | None = None,
    ) -> GridPrediction:
        """
        Derive candidate grid lines from bboxes and gate them by V1-style
        CCL active intervals extracted from the heatmap.

        Scoring rule
        ------------
        - Build CCL active intervals from the resized heatmap using threshold.
        - Candidate line position falls inside an interval  -> score = 1.0 (kept).
        - Candidate line position falls outside all intervals -> score = 0.0 (dropped).

        Parameters
        ----------
        image_bgr : cropped table BGR image (any size)
        bboxes    : list of [x1, y1, x2, y2] cell bbox pixel coordinates.
                    When None, extracted automatically from the db_prob map.

        Returns
        -------
        GridPrediction with filtered h/v lines and binary confidence scores.
        """
        orig_h, orig_w = image_bgr.shape[:2]

        h_heatmap, v_heatmap, db_prob_map = self._run_inference(image_bgr)

        if bboxes is None:
            if db_prob_map is None:
                raise RuntimeError(
                    "bboxes=None requires the ONNX model to export 'db_prob', "
                    "but it was not found in the model outputs."
                )
            bboxes = self._extract_bboxes_from_db(db_prob_map)

        # Derive candidate grid lines from bboxes (V3 rule-based)
        cand_h, cand_v, _ = extract_candidate_grid(
            bboxes, orig_h, orig_w, self.grid_margin_px
        )

        # Build CCL active intervals from heatmaps (V1-style, pixel space)
        h_intervals = _ccl_1d_active_intervals(h_heatmap, self.h_on_threshold)
        v_intervals = _ccl_1d_active_intervals(v_heatmap, self.v_on_threshold)

        # Score candidates: gate=1.0 if inside interval; heat=heatmap value at position
        h_scores, h_heat = _score_candidates_by_ccl_intervals(cand_h, h_intervals, h_heatmap)
        v_scores, v_heat = _score_candidates_by_ccl_intervals(cand_v, v_intervals, v_heatmap)

        # Keep only candidates with gate score == 1.0
        h_lines = [y for y, s in zip(cand_h, h_scores) if s > 0.0]
        v_lines = [x for x, s in zip(cand_v, v_scores) if s > 0.0]

        # Apply top_k: within each CCL interval keep at most top_k candidates
        # ranked by heatmap value (highest first). Disabled when top_k <= 0.
        if self.top_k > 0:
            h_heat_map = {y: float(h_heat[i])
                          for i, y in enumerate(cand_h) if h_scores[i] > 0.0}
            v_heat_map = {x: float(v_heat[i])
                          for i, x in enumerate(cand_v) if v_scores[i] > 0.0}

            h_lines = _apply_top_k_per_interval(h_lines, h_intervals, h_heat_map, self.top_k)
            v_lines = _apply_top_k_per_interval(v_lines, v_intervals, v_heat_map, self.top_k)

        return GridPrediction(
            h_lines=sorted(h_lines),
            v_lines=sorted(v_lines),
            h_heatmap=h_heatmap,
            v_heatmap=v_heatmap,
            h_confidences=h_scores,
            v_confidences=v_scores,
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
                         An empty list bypasses all processing.
        texts          : text strings aligned with bboxes
        span_threshold : fractional overlap to trigger span expansion

        Returns
        -------
        (GridPrediction, list[CellInfo])
        """
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

        grid = self.predict_grid(image_bgr, bboxes)

        effective_bboxes: list
        if bboxes is None:
            effective_bboxes = self._extract_bboxes_from_db(grid.db_prob_map) \
                if grid.db_prob_map is not None else []
        else:
            effective_bboxes = list(bboxes)

        if not effective_bboxes:
            return grid, []

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
    # Grid-based bbox assignment (identical to V1A)
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

        def find_cell_idx(pos: float, edges: list) -> int:
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
                    row_start = r - 1
                    r -= 1
                else:
                    break
            r = base_row
            while r < len(row_edges) - 2:
                h = row_edges[r + 1] - row_edges[r]
                if h > 0 and (y1 - row_edges[r + 1]) / h > span_threshold:
                    row_end = r + 2
                    r += 1
                else:
                    break
            c = base_col
            while c > 0:
                w = col_edges[c] - col_edges[c - 1]
                if w > 0 and (col_edges[c] - x0) / w > span_threshold:
                    col_start = c - 1
                    c -= 1
                else:
                    break
            c = base_col
            while c < len(col_edges) - 2:
                w = col_edges[c + 1] - col_edges[c]
                if w > 0 and (x1 - col_edges[c + 1]) / w > span_threshold:
                    col_end = c + 2
                    c += 1
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
        Visualize V1B results: CCL active intervals, candidates, kept/rejected
        lines, and heatmaps.

        Layout (2x2)
        ------------
        (1,1) image + kept lines (green h, orange v) +
              rejected candidates (red) + bbox rectangles (cyan)
              + CCL interval bands (semi-transparent yellow overlay)
        (1,2) h_heatmap tiled to 2D with CCL interval bands and candidate
              h line positions marked
        (2,1) v_heatmap tiled to 2D with CCL interval bands and candidate
              v line positions marked
        (2,2) db_prob_map heatmap when available; confidence bar chart
              (binary 0/1) otherwise

        Parameters
        ----------
        image_bgr : original BGR image
        pred      : GridPrediction from predict_grid() or predict()
        bboxes    : bbox list for candidate overlay; falls back to DB
                    extraction from pred.db_prob_map when None
        max_dim   : maximum single-panel dimension before downscaling
        """
        import cv2

        orig_h, orig_w = image_bgr.shape[:2]

        # Resolve bbox list for visualization
        vis_bboxes: list
        if bboxes is not None:
            vis_bboxes = list(bboxes)
        elif pred.db_prob_map is not None:
            vis_bboxes = self._extract_bboxes_from_db(pred.db_prob_map)
        else:
            vis_bboxes = []

        # Recompute all candidates and CCL intervals for visualization
        cand_h, cand_v, _ = extract_candidate_grid(
            vis_bboxes, orig_h, orig_w, self.grid_margin_px
        )
        h_intervals = _ccl_1d_active_intervals(pred.h_heatmap, self.h_on_threshold)
        v_intervals = _ccl_1d_active_intervals(pred.v_heatmap, self.v_on_threshold)
        h_scores, _ = _score_candidates_by_ccl_intervals(cand_h, h_intervals, pred.h_heatmap)
        v_scores, _ = _score_candidates_by_ccl_intervals(cand_v, v_intervals, pred.v_heatmap)

        kept_h = set(pred.h_lines)
        kept_v = set(pred.v_lines)

        # Panel (1,1): image with CCL bands, bboxes, and grid lines
        overlay = image_bgr.copy()

        # Draw CCL active interval bands as translucent yellow strips
        band_overlay = overlay.copy()
        for start, end in h_intervals:
            cv2.rectangle(band_overlay, (0, start), (orig_w, end),
                          (0, 220, 220), -1)
        for start, end in v_intervals:
            cv2.rectangle(band_overlay, (start, 0), (end, orig_h),
                          (0, 220, 220), -1)
        cv2.addWeighted(band_overlay, 0.15, overlay, 0.85, 0, overlay)

        for bbox in vis_bboxes:
            x1, y1, x2, y2 = [int(round(v)) for v in bbox]
            cv2.rectangle(overlay, (x1, y1), (x2, y2), (255, 255, 0), 1)

        for y, s in zip(cand_h, h_scores):
            yp = int(round(y))
            if y in kept_h:
                cv2.line(overlay, (0, yp), (orig_w, yp), (0, 255, 0), 1)
                cv2.putText(overlay, "1.0", (2, max(yp - 2, 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.28, (0, 255, 0), 1)
            else:
                cv2.line(overlay, (0, yp), (orig_w, yp), (0, 0, 255), 1)
                cv2.putText(overlay, "0.0", (2, max(yp - 2, 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.28, (0, 0, 255), 1)

        for x, s in zip(cand_v, v_scores):
            xp = int(round(x))
            color = (255, 128, 0) if x in kept_v else (0, 0, 255)
            cv2.line(overlay, (xp, 0), (xp, orig_h), color, 1)

        # Panel (1,2): h_heatmap with CCL bands and candidate lines
        h_2d = np.tile(pred.h_heatmap[:, np.newaxis], (1, orig_w))
        h_panel = cv2.applyColorMap(
            (h_2d * 255).clip(0, 255).astype(np.uint8), cv2.COLORMAP_JET
        )
        for start, end in h_intervals:
            cv2.rectangle(h_panel, (0, start), (orig_w - 1, end),
                          (255, 255, 255), 1)
        for y in cand_h:
            yp = int(round(y))
            color = (0, 255, 0) if y in kept_h else (0, 0, 255)
            cv2.line(h_panel, (0, yp), (orig_w, yp), color, 1)
        cv2.putText(h_panel, f"h_thr={self.h_on_threshold:.2f}",
                    (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)

        # Panel (2,1): v_heatmap with CCL bands and candidate lines
        v_2d = np.tile(pred.v_heatmap[np.newaxis, :], (orig_h, 1))
        v_panel = cv2.applyColorMap(
            (v_2d * 255).clip(0, 255).astype(np.uint8), cv2.COLORMAP_JET
        )
        for start, end in v_intervals:
            cv2.rectangle(v_panel, (start, 0), (end, orig_h - 1),
                          (255, 255, 255), 1)
        for x in cand_v:
            xp = int(round(x))
            color = (0, 255, 0) if x in kept_v else (0, 0, 255)
            cv2.line(v_panel, (xp, 0), (xp, orig_h), color, 1)
        cv2.putText(v_panel, f"v_thr={self.v_on_threshold:.2f}",
                    (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)

        # Panel (2,2): db_prob_map when available; binary bar chart otherwise
        if pred.db_prob_map is not None:
            db_panel = cv2.applyColorMap(
                (pred.db_prob_map * 255).clip(0, 255).astype(np.uint8),
                cv2.COLORMAP_JET,
            )
            db_panel = cv2.resize(db_panel, (orig_w, orig_h),
                                  interpolation=cv2.INTER_LINEAR)
            for bbox in vis_bboxes:
                x1, y1, x2, y2 = [int(round(v)) for v in bbox]
                cv2.rectangle(db_panel, (x1, y1), (x2, y2), (255, 255, 255), 1)
            cv2.putText(
                db_panel,
                f"db_thr={self.db_prob_threshold:.2f}  n={len(vis_bboxes)}",
                (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1,
            )
            bottom_right = db_panel
        else:
            bar_panel = np.zeros((orig_h, orig_w, 3), dtype=np.uint8)
            all_lines = (
                [(y, s, True)  for y, s in zip(cand_h, h_scores)] +
                [(x, s, False) for x, s in zip(cand_v, v_scores)]
            )
            n = len(all_lines)
            if n > 0:
                bar_w = max(1, orig_w // n)
                for idx, (pos, score, is_h) in enumerate(all_lines):
                    bx1 = idx * bar_w
                    bx2 = bx1 + bar_w - 1
                    # Binary score: either full height or zero
                    bar_h_px = int(score * (orig_h - 20))
                    color = (0, 200, 0) if is_h else (200, 100, 0)
                    if score < 1.0:
                        color = (0, 0, 180)
                    cv2.rectangle(bar_panel,
                                  (bx1, orig_h - bar_h_px), (bx2, orig_h),
                                  color, -1)
            cv2.putText(bar_panel, "Score: green=h(1.0)  orange=v(1.0)  red=0.0",
                        (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (200, 200, 200), 1)
            bottom_right = bar_panel

        # Compose 2x2 panel
        top_row  = np.concatenate([overlay,  h_panel],      axis=1)
        bot_row  = np.concatenate([v_panel,  bottom_right], axis=1)
        composed = np.concatenate([top_row,  bot_row],       axis=0)

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
            "Run TableGridExtractorV1B on all images in a directory. "
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
        help="Heatmap CCL threshold for h active intervals (default: 0.25).",
    )
    parser.add_argument(
        "--v_on_threshold", type=float, default=0.2,
        help="Heatmap CCL threshold for v active intervals (default: 0.2).",
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

    extractor = TableGridExtractorV1B(
        onnx_path=args.onnx_path,
        h_on_threshold=args.h_on_threshold,
        v_on_threshold=args.v_on_threshold,
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

        json_path = img_path.with_suffix(".json")
        if json_path.exists():
            with open(json_path, "r") as f:
                bboxes = json.load(f)
            bbox_source = f"sidecar ({len(bboxes)} boxes)"
        else:
            bboxes = None
            bbox_source = "DB auto"

        pred = extractor.predict_grid(img_bgr, bboxes)
        n_boxes = len(extractor._extract_bboxes_from_db(pred.db_prob_map)) \
                  if bboxes is None and pred.db_prob_map is not None else \
                  (len(bboxes) if bboxes is not None else 0)
        print(
            f"{img_path.name}  source={bbox_source}  "
            f"bboxes={n_boxes}  "
            f"h_lines={len(pred.h_lines)}  v_lines={len(pred.v_lines)}"
        )

        composed = extractor.visualize(img_bgr, pred, bboxes=bboxes, max_dim=args.max_dim)

        if save_dir is not None:
            out_path = save_dir / f"{img_path.stem}_v1b_vis{img_path.suffix}"
            cv2.imwrite(str(out_path), composed)
            print(f"  Saved -> {out_path}")
        else:
            window_title = f"TableGridExtractorV1B - {img_path.name}"
            cv2.imshow(window_title, composed)
            cv2.waitKey(0)
            cv2.destroyWindow(window_title)
