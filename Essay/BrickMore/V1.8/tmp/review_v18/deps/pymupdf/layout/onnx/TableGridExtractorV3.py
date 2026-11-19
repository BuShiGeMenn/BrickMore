"""
TableGridExtractorV3.py

Loads an exported GridModelV3 ONNX model and predicts table grid structure
(h/v line positions) from a cropped table image.

Key differences from V2
-----------------------
- GridModelV3 outputs candidate logits rather than anchor-based on/offset maps.
  Candidate positions (h_positions, v_positions) must be supplied at inference.
- Candidate generation has two modes depending on whether bboxes are available:
    * bbox mode  : candidates are derived directly from bbox boundaries using
                   the same empty-strip algorithm as TableGridDatasetV3.
                   The DB pass is skipped entirely.
    * DB mode    : when no bboxes are available, a first ONNX pass with empty
                   candidates obtains db_prob, from which candidates are derived
                   via connected-component analysis (mirrors the dataset logic).
- No ConnClassifier: V3 does not produce a feature_map output for connectivity.
- snap_to_bbox_gaps is removed (not supported in V3).

ONNX model I/O (GridModelV3 _ExportWrapper)
--------------------------------------------
Inputs  : image       (1, 3, H, W)  float32
          h_positions (N_h,)         float32  candidate y coords in model input px
          v_positions (N_v,)         float32  candidate x coords in model input px
Outputs : h_logits    (N_h,)         float32
          v_logits    (N_v,)         float32
          db_prob     (1, 1, H, W)   float32  sigmoid probability map
          db_thresh   (1, 1, H, W)   float32  threshold map in [0, 1]

Post-processing pipeline (bbox mode)
--------------------------------------
1. Resize input image to model input size.
2. Scale bboxes to model input px coords.
3. Derive h/v candidates from scaled bbox boundaries (empty-strip detection).
4. Run ONNX model once with derived candidates -> h_logits, v_logits.
5. Sigmoid + threshold + 1D NMS -> active line positions.
6. Scale to original image pixel coords.
7. Optionally filter empty lines using bbox centers.

Post-processing pipeline (DB mode, no bboxes)
----------------------------------------------
1. Resize input image to model input size.
2. Run ONNX model with empty candidates -> db_prob.
3. Derive h/v candidates from db_prob via connected-component analysis.
4. Run ONNX model again with derived candidates -> h_logits, v_logits.
5. Sigmoid + threshold + 1D NMS -> active line positions.
6. Scale to original image pixel coords.

filter_empty_lines behaviour
-----------------------------
Applied in predict() when bboxes are provided. Works on (pos, score) tuples
where score is the per-line sigmoid value retained from the classifier output.

Algorithm (CCL-style, converges in multiple passes):
  For each consecutive pair of kept lines (lo, hi):
    - If no bbox center y falls in [lo_pos, hi_pos]:
        remove the line with the lower score (keep the higher-score one).
        mark changed=True and restart the scan.
  Repeat until no pair is removed.

After convergence:
  - Remove leading lines where no bbox center falls in [0, line_pos].
  - Remove trailing lines where no bbox center falls in [line_pos, image_height].

The same logic applies symmetrically to v_lines using cx (bbox center x).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import onnxruntime as ort

from .GlobalConfig import get_config
from .table_grid_types import GridPrediction, CellInfo
from .common_util import make_session


# ---------------------------------------------------------------------------
# Candidate generation from bboxes (mirrors TableGridDatasetV3._find_grid_lines)
# ---------------------------------------------------------------------------

def _bboxes_to_candidates(
    bboxes_scaled: np.ndarray,
    grid_margin_px: float = 5.0,
) -> tuple[list[float], list[float]]:
    """
    Derive h/v candidate grid line positions from bbox boundaries.

    Mirrors the empty-strip detection logic in TableGridDatasetV3.
    bboxes_scaled must already be in model input pixel coordinates.

    Parameters
    ----------
    bboxes_scaled  : (N, 4) float32 array of [x1, y1, x2, y2] in model input px
    grid_margin_px : proximity margin for strip detection (default 5.0)

    Returns
    -------
    h_candidates : list[float]  candidate y midpoints (model input px, unsorted)
    v_candidates : list[float]  candidate x midpoints (model input px, unsorted)
    """
    if len(bboxes_scaled) == 0:
        return [], []

    all_h_boundaries: set[float] = set()
    all_v_boundaries: set[float] = set()
    cell_bboxes: list[list[float]] = []

    for bbox in bboxes_scaled:
        x1_f, y1_f, x2_f, y2_f = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
        if x2_f <= x1_f or y2_f <= y1_f:
            continue
        w  = x2_f - x1_f
        h  = y2_f - y1_f
        xs = 1 if w >= 3 else 0
        ys = 1 if h >= 3 else 0
        sx1, sy1 = x1_f + xs, y1_f + ys
        sx2, sy2 = x2_f - xs, y2_f - ys
        cell_bboxes.append([sx1, sy1, sx2, sy2])
        all_h_boundaries.add(sy1)
        all_h_boundaries.add(sy2)
        all_v_boundaries.add(sx1)
        all_v_boundaries.add(sx2)

    def _find_candidates(boundaries, bboxes, is_h):
        if not boundaries:
            return []
        sorted_b = sorted(boundaries)
        results  = []
        seen     = set()
        for i in range(len(sorted_b) - 1):
            c1, c2 = sorted_b[i], sorted_b[i + 1]
            if c2 - c1 < 0:
                continue
            is_empty = True
            for bbox in bboxes:
                bx1, by1, bx2, by2 = bbox
                if is_h:
                    near = (
                        abs(by1 - c1) <= grid_margin_px or
                        abs(by2 - c1) <= grid_margin_px or
                        abs(by1 - c2) <= grid_margin_px or
                        abs(by2 - c2) <= grid_margin_px
                    )
                    if not near:
                        continue
                    if by2 > c1 and by1 < c2:
                        is_empty = False
                        break
                else:
                    near = (
                        abs(bx1 - c1) <= grid_margin_px or
                        abs(bx2 - c1) <= grid_margin_px or
                        abs(bx1 - c2) <= grid_margin_px or
                        abs(bx2 - c2) <= grid_margin_px
                    )
                    if not near:
                        continue
                    if bx2 > c1 and bx1 < c2:
                        is_empty = False
                        break
            if is_empty:
                mid     = (c1 + c2) / 2.0
                mid_int = int(round(mid))
                if mid_int not in seen:
                    seen.add(mid_int)
                    results.append(mid)
        return results

    h_candidates = _find_candidates(all_h_boundaries, cell_bboxes, is_h=True)
    v_candidates = _find_candidates(all_v_boundaries, cell_bboxes, is_h=False)
    return h_candidates, v_candidates


# ---------------------------------------------------------------------------
# Candidate generation from DBHead probability map (DB fallback mode)
# ---------------------------------------------------------------------------

def _db_predictions_to_candidates(
    db_prob_np: np.ndarray,
    prob_threshold: float = 0.5,
    shrink_ratio: float = 0.1,
    grid_margin_px: float = 5.0,
) -> tuple[list[float], list[float]]:
    """
    Convert a DBHead probability map to candidate h/v grid line positions.

    Used only when no external bboxes are available.
    Mirrors TableGridModelsV3.db_predictions_to_candidates.

    Parameters
    ----------
    db_prob_np      : (H, W) float32 sigmoid probability map
    prob_threshold  : binarisation threshold
    shrink_ratio    : shrink ratio assumed during training, for bbox expansion
    grid_margin_px  : empty-strip margin for candidate detection

    Returns
    -------
    h_positions : list[float]  candidate y-coordinates (model input px, unsorted)
    v_positions : list[float]  candidate x-coordinates (model input px, unsorted)
    """
    import cv2
    binary     = (db_prob_np >= prob_threshold).astype(np.uint8) * 255
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        binary, connectivity=8
    )

    expand = 1.0 / max(1.0 - shrink_ratio, 1e-6)
    H, W   = db_prob_np.shape

    reconstructed_bboxes: list[list[float]] = []

    for lbl in range(1, num_labels):
        x, y, w, h, area = stats[lbl]
        if area < 4:
            continue
        cx = x + w / 2.0
        cy = y + h / 2.0
        ew = w * expand
        eh = h * expand
        x1 = max(0.0,    cx - ew / 2.0)
        y1 = max(0.0,    cy - eh / 2.0)
        x2 = min(float(W), cx + ew / 2.0)
        y2 = min(float(H), cy + eh / 2.0)
        if x2 - x1 < 1 or y2 - y1 < 1:
            continue
        reconstructed_bboxes.append([x1, y1, x2, y2])

    if not reconstructed_bboxes:
        return [], []

    bboxes_np = np.array(reconstructed_bboxes, dtype=np.float32)
    return _bboxes_to_candidates(bboxes_np, grid_margin_px)


# ---------------------------------------------------------------------------
# 1D NMS
# ---------------------------------------------------------------------------

def _nms_1d(
    positions: np.ndarray,
    scores: np.ndarray,
    nms_min_dist: float,
) -> np.ndarray:
    """
    Greedy score-descending 1D NMS.

    Parameters
    ----------
    positions    : (N,) float32 line positions
    scores       : (N,) float32 corresponding sigmoid scores
    nms_min_dist : minimum distance between kept lines (same coord space)

    Returns
    -------
    Indices of kept lines, sorted by position.
    """
    if nms_min_dist <= 0.0 or len(positions) == 0:
        return np.argsort(positions)

    order      = np.argsort(-scores)
    suppressed = np.zeros(len(positions), dtype=bool)
    keep       = []

    for i in order:
        if suppressed[i]:
            continue
        keep.append(i)
        for j in range(len(positions)):
            if not suppressed[j] and j != i:
                if abs(float(positions[j]) - float(positions[i])) < nms_min_dist:
                    suppressed[j] = True

    return np.array(sorted(keep, key=lambda k: positions[k]), dtype=np.int32)


# ---------------------------------------------------------------------------
# Main extractor
# ---------------------------------------------------------------------------

class TableGridExtractorV3:
    """
    ONNX-based table grid extractor using the V3 candidate classifier model.

    Candidate generation mode is selected automatically in predict_grid:
      - bboxes provided -> bbox boundary-based candidates (1 ONNX pass)
      - bboxes absent   -> DBHead probability map-based candidates (2 ONNX passes)
    """

    def __init__(
        self,
        grid_onnx_path,
        h_on_threshold: float = 0.5,
        v_on_threshold: float = 0.5,
        nms_min_dist: float = 5.0,
        filter_empty_lines: bool = True,
        db_prob_threshold: float = 0.5,
        db_shrink_ratio: float = 0.1,
        db_grid_margin_px: float = 5.0,
        bbox_grid_margin_px: float = 5.0,
        header_type = "1-Row",
        merge_type  = "BBox",
        providers   = None,
    ) -> None:
        """
        Parameters
        ----------
        grid_onnx_path      : path to GridModelV3 .onnx file
        h_on_threshold      : sigmoid threshold for h-line activation (default 0.5)
        v_on_threshold      : sigmoid threshold for v-line activation (default 0.5)
        nms_min_dist        : minimum distance (model input px) between kept lines
                              after thresholding (default 5.0)
        filter_empty_lines  : merge adjacent lines with no bbox center between them
                              when bboxes are supplied (default True)
        db_prob_threshold   : binarisation threshold for DB probability map,
                              used only in DB fallback mode (default 0.5)
        db_shrink_ratio     : shrink ratio assumed during model training, used for
                              bbox expansion in DB candidate generation (default 0.1)
        db_grid_margin_px   : empty-strip margin for DB candidate generation (default 5.0)
        bbox_grid_margin_px : empty-strip margin for bbox candidate generation (default 5.0)
        """
        if providers is None:
            providers = ["CPUExecutionProvider"]

        self.grid_onnx_path      = Path(grid_onnx_path)
        self.h_on_threshold      = h_on_threshold
        self.v_on_threshold      = v_on_threshold
        self.nms_min_dist        = nms_min_dist
        self.filter_empty_lines  = filter_empty_lines
        self.db_prob_threshold   = db_prob_threshold
        self.db_shrink_ratio     = db_shrink_ratio
        self.db_grid_margin_px   = db_grid_margin_px
        self.bbox_grid_margin_px = bbox_grid_margin_px
        self.header_type         = header_type
        self.merge_type          = merge_type

        global_config = get_config()
        if global_config.get("TableGridExtractorV3") is not None:
            self.h_on_threshold  = global_config.get("TableGridExtractorV3.h_on_threshold")
            self.v_on_threshold  = global_config.get("TableGridExtractorV3.v_on_threshold")
            self.nms_min_dist    = global_config.get("TableGridExtractorV3.nms_min_dist")

        self._sess = make_session(str(self.grid_onnx_path), providers)

        inp = self._sess.get_inputs()[0]
        self._input_h = int(inp.shape[2])
        self._input_w = int(inp.shape[3])

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _preprocess(self, image_bgr: np.ndarray) -> np.ndarray:
        """Resize + normalize -> (1, 3, H, W) float32."""
        import cv2
        img_resized = cv2.resize(image_bgr, (self._input_w, self._input_h))
        img_rgb     = img_resized[:, :, ::-1].astype(np.float32) / 255.0
        return img_rgb.transpose(2, 0, 1)[np.newaxis]

    def _run_onnx(
        self,
        inp: np.ndarray,
        h_positions: np.ndarray,
        v_positions: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Single ONNX session run.

        Returns
        -------
        h_logits  : (N_h,)
        v_logits  : (N_v,)
        db_prob   : (H, W)  sigmoid probability map
        db_thresh : (H, W)  threshold map
        """
        outputs = self._sess.run(None, {
            "image":       inp,
            "h_positions": h_positions.astype(np.float32),
            "v_positions": v_positions.astype(np.float32),
        })
        return outputs[0], outputs[1], outputs[2][0, 0], outputs[3][0, 0]

    @staticmethod
    def _sigmoid(x: np.ndarray) -> np.ndarray:
        return (1.0 / (1.0 + np.exp(-x.astype(np.float64)))).astype(np.float32)

    def _classify_candidates(
        self,
        inp: np.ndarray,
        h_cands: list[float],
        v_cands: list[float],
        orig_h: int,
        orig_w: int,
    ) -> tuple[list[float], list[float], list[float], list[float]]:
        """
        Run ONNX classifier on given candidates and return kept lines with scores.

        Candidates must be in model input pixel coordinates.
        Returned lines are in original image pixel coordinates.

        Returns
        -------
        h_lines  : list[float]  kept h-line positions (orig px, sorted)
        v_lines  : list[float]  kept v-line positions (orig px, sorted)
        h_scores : list[float]  per-kept-line sigmoid scores
        v_scores : list[float]  per-kept-line sigmoid scores
        """
        empty     = np.zeros(0, dtype=np.float32)
        h_pos_arr = np.array(sorted(h_cands), dtype=np.float32) if h_cands else empty
        v_pos_arr = np.array(sorted(v_cands), dtype=np.float32) if v_cands else empty

        h_logits, v_logits, _, _ = self._run_onnx(inp, h_pos_arr, v_pos_arr)

        h_sig = self._sigmoid(h_logits)
        v_sig = self._sigmoid(v_logits)

        h_mask       = h_sig >= self.h_on_threshold
        v_mask       = v_sig >= self.v_on_threshold
        h_pos_active = h_pos_arr[h_mask]
        h_scr_active = h_sig[h_mask]
        v_pos_active = v_pos_arr[v_mask]
        v_scr_active = v_sig[v_mask]

        h_keep = _nms_1d(h_pos_active, h_scr_active, self.nms_min_dist)
        v_keep = _nms_1d(v_pos_active, v_scr_active, self.nms_min_dist)

        scale_h  = orig_h / float(self._input_h)
        scale_w  = orig_w / float(self._input_w)
        h_lines  = [float(h_pos_active[k]) * scale_h for k in h_keep]
        v_lines  = [float(v_pos_active[k]) * scale_w for k in v_keep]
        h_scores = [float(h_scr_active[k]) for k in h_keep]
        v_scores = [float(v_scr_active[k]) for k in v_keep]

        return h_lines, v_lines, h_scores, v_scores

    @staticmethod
    def _filter_empty_lines(
        lines: list[tuple[float, float]],
        centers: list[float],
        image_size: float,
    ) -> list[tuple[float, float]]:
        """
        Remove lines that have no bbox center in the gap they bound.

        Input/output: list of (pos, score) tuples, sorted by pos.

        Algorithm
        ---------
        Scan consecutive pairs (lo, hi). If no bbox center falls in
        [lo_pos, hi_pos], discard the line with the lower score and
        restart the scan. Repeat until no pair is removed (CCL convergence).

        After convergence, additionally remove:
          - leading lines where no center falls in [0, line_pos]
          - trailing lines where no center falls in [line_pos, image_size]
        """
        if not lines:
            return lines

        current = sorted(lines, key=lambda t: t[0])
        changed = True

        while changed:
            changed = False
            if len(current) < 2:
                break
            result = [current[0]]
            for i in range(1, len(current)):
                lo_pos, lo_score = result[-1]
                hi_pos, hi_score = current[i]
                has_center = any(lo_pos <= c <= hi_pos for c in centers)
                if not has_center:
                    if hi_score >= lo_score:
                        result[-1] = (hi_pos, hi_score)
                    changed = True
                else:
                    result.append(current[i])
            current = result

        while current and not any(0.0 <= c <= current[0][0] for c in centers):
            current = current[1:]
        while current and not any(current[-1][0] <= c <= image_size for c in centers):
            current = current[:-1]

        return current

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict_grid(
        self,
        image_bgr: np.ndarray,
        bboxes: np.ndarray | None = None,
    ) -> GridPrediction:
        """
        Run grid line prediction.

        Parameters
        ----------
        image_bgr : cropped table BGR image (any size)
        bboxes    : (N, 4) float32 array of [x1, y1, x2, y2] in crop pixel coords.
                    When provided, candidates are derived from bbox boundaries
                    (1 ONNX pass, DB skipped). When None or empty, candidates
                    are derived from the DBHead probability map (2 ONNX passes).

        Returns
        -------
        GridPrediction with h_lines / v_lines in original image pixel coords.
        h_on_prob / v_on_prob hold per-kept-line sigmoid scores (not the full
        candidate array) so that filter_empty_lines can use meaningful scores.
        """
        orig_h, orig_w = image_bgr.shape[:2]
        inp = self._preprocess(image_bgr)

        has_bboxes = bboxes is not None and len(bboxes) > 0

        if has_bboxes:
            # Bbox mode: scale bboxes to model input px and derive candidates directly
            bboxes_arr    = np.asarray(bboxes, dtype=np.float32)
            scale_x       = self._input_w / float(orig_w)
            scale_y       = self._input_h / float(orig_h)
            bboxes_scaled = bboxes_arr * np.array(
                [scale_x, scale_y, scale_x, scale_y], dtype=np.float32
            )
            h_cands, v_cands = _bboxes_to_candidates(
                bboxes_scaled,
                grid_margin_px=self.bbox_grid_margin_px,
            )
        else:
            # DB fallback mode: pass 1 with empty candidates to obtain db_prob
            empty = np.zeros(0, dtype=np.float32)
            _, _, db_prob, _ = self._run_onnx(inp, empty, empty)
            h_cands, v_cands = _db_predictions_to_candidates(
                db_prob,
                prob_threshold = self.db_prob_threshold,
                shrink_ratio   = self.db_shrink_ratio,
                grid_margin_px = self.db_grid_margin_px,
            )

        if not h_cands and not v_cands:
            return GridPrediction(
                h_lines      = [],
                v_lines      = [],
                h_on_prob    = np.zeros(0, dtype=np.float32),
                v_on_prob    = np.zeros(0, dtype=np.float32),
                h_lines_norm = np.zeros(0, dtype=np.float32),
                v_lines_norm = np.zeros(0, dtype=np.float32),
                h_cls        = np.zeros(0, dtype=np.int32),
                connectivity = None,
            )

        h_lines, v_lines, h_scores, v_scores = self._classify_candidates(
            inp, h_cands, v_cands, orig_h, orig_w,
        )

        h_lines_norm = np.array([y / orig_h for y in h_lines], dtype=np.float32)
        v_lines_norm = np.array([x / orig_w for x in v_lines], dtype=np.float32)

        # --- START TEMPORARY VISUALIZATION CODE ---
        if '' == 'D':
            # Scale candidates for visualization on the original image
            scale_h_cand = orig_h / float(self._input_h)
            scale_w_cand = orig_w / float(self._input_w)

            img_viz = image_bgr.copy()

            import cv2
            # Visualize raw h_cands (green lines)
            for y_cand in h_cands:
                y_scaled = int(y_cand * scale_h_cand)
                cv2.line(img_viz, (0, y_scaled), (orig_w, y_scaled), (0, 255, 0), 1)
            # Visualize raw v_cands (green lines)
            for x_cand in v_cands:
                x_scaled = int(x_cand * scale_w_cand)
                cv2.line(img_viz, (x_scaled, 0), (x_scaled, orig_h), (0, 255, 0), 1)

            # Visualize kept h_lines with scores (red lines)
            for i, y_line in enumerate(h_lines):
                y_int = int(y_line)
                score = h_scores[i]
                cv2.line(img_viz, (0, y_int), (orig_w, y_int), (0, 0, 255), 2) # Red
                cv2.putText(img_viz, f"{score:.2f}", (5, y_int - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

            # Visualize kept v_lines with scores (blue lines)
            for i, x_line in enumerate(v_lines):
                x_int = int(x_line)
                score = v_scores[i]
                cv2.line(img_viz, (x_int, 0), (x_int, orig_h), (255, 0, 0), 2) # Blue
                cv2.putText(img_viz, f"{score:.2f}", (x_int + 5, 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)

            cv2.imshow("Grid Candidate Visualization (Green: Candidates, Red/Blue: Kept Lines)", img_viz)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        # --- END TEMPORARY VISUALIZATION CODE ---

        return GridPrediction(
            h_lines      = sorted(h_lines),
            v_lines      = sorted(v_lines),
            h_on_prob    = np.array(h_scores, dtype=np.float32),
            v_on_prob    = np.array(v_scores, dtype=np.float32),
            h_lines_norm = h_lines_norm,
            v_lines_norm = v_lines_norm,
            h_cls        = np.ones(len(h_lines), dtype=np.int32),
            connectivity = None,
        )

    def predict(
        self,
        image_bgr: np.ndarray,
        bboxes=None,
        texts=None,
        span_threshold: float = 0.1,
    ) -> tuple:
        """
        Predict grid boundaries and optionally assign bboxes to grid cells.

        Parameters
        ----------
        image_bgr      : cropped table BGR image (any size)
        bboxes         : (N, 4) array-like of [x1, y1, x1, y2] in crop px.
                         When provided, used for candidate generation and
                         empty-line filtering. When None, DB mode is used
                         and no CellInfo is returned.
        texts          : list of text strings aligned with bboxes.
        span_threshold : fractional overlap to trigger span expansion (default 0.1)

        Returns
        -------
        (GridPrediction, list[CellInfo])
        CellInfo list is empty when bboxes is None or empty.
        """
        bboxes_arr = (
            np.asarray(bboxes, dtype=np.float32)
            if bboxes is not None and len(bboxes) > 0
            else None
        )

        grid = self.predict_grid(image_bgr, bboxes=bboxes_arr)

        if bboxes_arr is None:
            return grid, []

        crop_h  = float(image_bgr.shape[0])
        crop_w  = float(image_bgr.shape[1])
        cx_list = sorted((float(b[0]) + float(b[2])) / 2.0 for b in bboxes_arr)
        cy_list = sorted((float(b[1]) + float(b[3])) / 2.0 for b in bboxes_arr)

        # h_on_prob / v_on_prob hold per-kept-line scores from the classifier
        h_tuples = list(zip(sorted(grid.h_lines), grid.h_on_prob.tolist()))
        v_tuples = list(zip(sorted(grid.v_lines), grid.v_on_prob.tolist()))

        if self.filter_empty_lines:
            h_tuples = self._filter_empty_lines(h_tuples, cy_list, crop_h)
            v_tuples = self._filter_empty_lines(v_tuples, cx_list, crop_w)

        filtered_h     = [y for y, _ in h_tuples]
        filtered_v     = [x for x, _ in v_tuples]
        filtered_h_scr = np.array([s for _, s in h_tuples], dtype=np.float32)
        filtered_v_scr = np.array([s for _, s in v_tuples], dtype=np.float32)

        orig_h          = float(image_bgr.shape[0])
        orig_w          = float(image_bgr.shape[1])
        filtered_h_norm = np.array([y / orig_h for y in filtered_h], dtype=np.float32)
        filtered_v_norm = np.array([x / orig_w for x in filtered_v], dtype=np.float32)

        grid = GridPrediction(
            h_lines      = sorted(filtered_h),
            v_lines      = sorted(filtered_v),
            h_on_prob    = filtered_h_scr,
            v_on_prob    = filtered_v_scr,
            h_lines_norm = filtered_h_norm,
            v_lines_norm = filtered_v_norm,
            h_cls        = np.ones(len(filtered_h), dtype=np.int32),
            connectivity = None,
        )

        cells = self._post_process_grid(
            bboxes_page    = bboxes_arr,
            grid           = grid,
            span_threshold = span_threshold,
        )

        if texts is not None:
            for cell in cells:
                if 0 <= cell.bbox_idx < len(texts):
                    cell.text = texts[cell.bbox_idx]

        return grid, cells

    # ------------------------------------------------------------------
    # Grid-based bbox assignment (identical to V2)
    # ------------------------------------------------------------------

    def _post_process_grid(self, bboxes_page, grid, span_threshold):
        if grid.h_lines:
            last_h    = sorted(grid.h_lines)[-1]
            row_edges = [0.0] + sorted(grid.h_lines) + [max(last_h * 2, last_h + 1)]
        else:
            row_edges = [0.0, 1.0]

        if grid.v_lines:
            last_v    = sorted(grid.v_lines)[-1]
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

            base_row  = find_cell_idx(cy, row_edges)
            base_col  = find_cell_idx(cx, col_edges)
            row_start = base_row
            row_end   = base_row + 1
            col_start = base_col
            col_end   = base_col + 1

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
                bbox_idx  = i,
                row_start = row_start,
                row_end   = row_end,
                col_start = col_start,
                col_end   = col_end,
                row       = base_row,
                col       = base_col,
            ))

        return results

