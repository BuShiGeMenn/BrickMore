"""
TableGridExtractorV2A.py

Combines bbox-based candidate grid extraction (V1A algorithm) with
GridModelV2 anchor confidence scoring.

Post-processing pipeline
------------------------
1. Accept cell bboxes (optional).
2. Resize input image to GridModelV2 input size.
3. Run GridModelV2 ONNX inference.
   Outputs: h_on_logit, h_offset, v_on_logit, v_offset, feature_map
4. For each candidate grid line (derived from bboxes), find the nearest
   anchor in the GridModelV2 anchor grid and read its sigmoid(on_logit)
   as a confidence score.
5. Remove candidate lines whose confidence is below threshold.
6. Optionally run _post_process_grid -> CellInfo with span.
7. Optionally run ConnClassifier on cell features.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import onnxruntime as ort

from .GlobalConfig import get_config
from .table_grid_types import GridPrediction, CellInfo
from .common_util import make_session


# ---------------------------------------------------------------------------
# Re-use candidate grid extraction helpers from V1A
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
    registered as a grid line.
    """
    if not candidate_boundaries:
        return []

    sorted_boundaries = sorted(list(candidate_boundaries))
    final_lines: set = set()

    for i in range(len(sorted_boundaries) - 1):
        coord1 = sorted_boundaries[i]
        coord2 = sorted_boundaries[i + 1]
        if coord2 - coord1 < 0:
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


def _extract_candidate_grid(
    bboxes: list,
    orig_h: int,
    orig_w: int,
    grid_margin_px: float = 5.0,
) -> tuple:
    """
    Derive candidate h/v grid lines from cell bboxes (same as V1A).

    Returns
    -------
    (candidate_h_lines, candidate_v_lines, cells_bbox_shrunk)
    All coordinates are in input image pixel space.
    """
    all_h_boundaries: set = set()
    all_v_boundaries: set = set()
    cells_bbox_shrunk: list = []

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
# Anchor confidence scoring
# ---------------------------------------------------------------------------

def _score_candidates_by_anchor(
    candidate_positions_px: list,
    on_logits: np.ndarray,
    image_size: float,
) -> np.ndarray:
    """
    For each candidate line position, find the nearest GridModelV2 anchor
    and return sigmoid(on_logit) as a confidence score.

    The anchor grid is uniformly spaced over [0, 1] with len(on_logits)
    points, matching the anchor layout used in _decode_anchors.

    Parameters
    ----------
    candidate_positions_px : list of candidate line positions in pixel coords
    on_logits              : raw logit array of shape (max_anchors,) from
                             GridModelV2 inference
    image_size             : image dimension (H for h-lines, W for v-lines)

    Returns
    -------
    np.ndarray of shape (len(candidate_positions_px),) with scores in [0, 1].
    """
    max_n   = len(on_logits)
    anchors = np.linspace(0.0, 1.0, max_n, dtype=np.float32)
    on_prob = (1.0 / (1.0 + np.exp(-on_logits.astype(np.float64)))).astype(np.float32)

    scores = np.zeros(len(candidate_positions_px), dtype=np.float32)
    for i, pos_px in enumerate(candidate_positions_px):
        pos_norm = float(pos_px) / float(image_size) if image_size > 0 else 0.0
        idx      = int(np.argmin(np.abs(anchors - pos_norm)))
        scores[i] = on_prob[idx]

    return scores


# ---------------------------------------------------------------------------
# Cell feature extraction (identical to V2)
# ---------------------------------------------------------------------------

def _extract_cell_features(feature_map, h_lines_norm, v_lines_norm):
    """Pool feature_map regions defined by detected line positions."""
    C, H, W = feature_map.shape
    N = len(h_lines_norm)
    M = len(v_lines_norm)

    if N < 2 or M < 2:
        return np.zeros((max(N - 1, 1), max(M - 1, 1), C), dtype=np.float32)

    ys = np.clip((h_lines_norm * H).astype(np.int32), 0, H)
    xs = np.clip((v_lines_norm * W).astype(np.int32), 0, W)

    cell_feat = np.zeros((N - 1, M - 1, C), dtype=np.float32)
    for i in range(N - 1):
        y1 = ys[i]
        y2 = max(y1 + 1, ys[i + 1])
        y2 = min(y2, H)
        if y1 >= H:
            continue
        for j in range(M - 1):
            x1 = xs[j]
            x2 = max(x1 + 1, xs[j + 1])
            x2 = min(x2, W)
            if x1 >= W:
                continue
            region = feature_map[:, y1:y2, x1:x2]
            if region.size == 0:
                continue
            cell_feat[i, j] = region.mean(axis=(1, 2))

    return cell_feat


# ---------------------------------------------------------------------------
# Main extractor class
# ---------------------------------------------------------------------------

class TableGridExtractorV2A:
    """
    Hybrid table grid extractor using GridModelV2:
    - Candidate grid lines derived from cell bboxes (rule-based, V1A algorithm).
    - GridModelV2 anchor on_logit used as confidence to filter spurious candidates.
    - Optionally runs ConnClassifier on pooled cell features.
    """

    def __init__(
        self,
        grid_onnx_path,
        conn_onnx_path = None,
        h_on_threshold: float = 0.25,
        v_on_threshold: float = 0.2,
        conn_threshold: float = 0.2,
        grid_margin_px: float = 5.0,
        filter_empty_lines: bool = True,
        snap_to_bbox_gaps: bool = False,
        header_type = "1-Row",
        merge_type = "BBox",
        providers = None,
    ) -> None:
        """
        Parameters
        ----------
        grid_onnx_path    : path to exported GridModelV2 .onnx file
        conn_onnx_path    : path to ConnClassifier .onnx file (optional)
        h_on_threshold    : minimum anchor confidence to keep a candidate h line
        v_on_threshold    : minimum anchor confidence to keep a candidate v line
        conn_threshold    : connectivity classifier probability threshold
        grid_margin_px    : alignment tolerance for candidate grid extraction (px)
        filter_empty_lines: whether to run empty-line filtering in predict()
        snap_to_bbox_gaps : whether to snap h lines to inter-row bbox gaps
        header_type       : passed through to downstream consumers
        merge_type        : passed through to downstream consumers
        providers         : ONNX Runtime execution providers
        """
        if providers is None:
            providers = ["CPUExecutionProvider"]

        self.grid_onnx_path     = Path(grid_onnx_path)
        self.conn_onnx_path     = Path(conn_onnx_path) if conn_onnx_path else None
        self.h_on_threshold     = h_on_threshold
        self.v_on_threshold     = v_on_threshold
        self.conn_threshold     = conn_threshold
        self.grid_margin_px     = grid_margin_px
        self.filter_empty_lines = filter_empty_lines
        self.snap_to_bbox_gaps  = snap_to_bbox_gaps
        self.header_type        = header_type
        self.merge_type         = merge_type

        global_config = get_config()
        if global_config.get("TableGridExtractorV2A") is not None:
            self.v_on_threshold = global_config.get("TableGridExtractorV2A.v_on_threshold")
            self.h_on_threshold = global_config.get("TableGridExtractorV2A.h_on_threshold")

        self._grid_sess = make_session(str(self.grid_onnx_path), providers)
        self._conn_sess = (
            make_session(str(self.conn_onnx_path), providers)
            if self.conn_onnx_path and self.conn_onnx_path.exists() else None
        )

        inp = self._grid_sess.get_inputs()[0]
        self._input_h = int(inp.shape[2])
        self._input_w = int(inp.shape[3])

        # Derive anchor counts via dummy forward pass
        dummy   = np.zeros((1, 3, self._input_h, self._input_w), dtype=np.float32)
        outputs = self._grid_sess.run(None, {"image": dummy})
        self._max_h = int(outputs[0].shape[1])  # h_on_logit length
        self._max_v = int(outputs[2].shape[1])  # v_on_logit length

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def _run_inference(self, image_bgr: np.ndarray) -> tuple:
        """
        Run GridModelV2 inference and return raw logits and feature map.

        Returns
        -------
        (h_on_logit, h_offset, v_on_logit, v_offset, feature_map)
        All arrays are in model output space (not resized to image dims).
        """
        import cv2

        img_resized = cv2.resize(image_bgr, (self._input_w, self._input_h))
        img_rgb     = img_resized[:, :, ::-1].astype(np.float32) / 255.0
        inp         = img_rgb.transpose(2, 0, 1)[np.newaxis]

        outputs     = self._grid_sess.run(None, {"image": inp})
        h_on_logit  = outputs[0][0]   # (max_h,)
        h_offset    = outputs[1][0]   # (max_h,)
        v_on_logit  = outputs[2][0]   # (max_v,)
        v_offset    = outputs[3][0]   # (max_v,)
        feature_map = outputs[4][0]   # (C, H', W')

        return h_on_logit, h_offset, v_on_logit, v_offset, feature_map

    # ------------------------------------------------------------------
    # Snap helper (identical to V2)
    # ------------------------------------------------------------------

    @staticmethod
    def _snap_lines_to_bbox_gaps(
        h_lines: list,
        bboxes_crop: np.ndarray,
        snap_threshold: float = 0.0,
    ) -> list:
        """Snap h_lines crossing a bbox to nearest inter-row gap center."""
        if len(bboxes_crop) == 0 or len(h_lines) == 0:
            return h_lines

        bottoms  = np.sort(bboxes_crop[:, 3])
        tops     = np.sort(bboxes_crop[:, 1])
        gap_lines = []
        for bot in bottoms:
            candidates = tops[tops > bot]
            if len(candidates) > 0:
                gap_lines.append((bot + float(candidates[0])) / 2.0)

        if not gap_lines:
            return h_lines

        gap_arr   = np.array(sorted(set(round(g, 4) for g in gap_lines)), dtype=np.float32)
        used_gaps: set = set()
        result    = []
        for y in h_lines:
            crosses = np.any((bboxes_crop[:, 1] < y) & (y < bboxes_crop[:, 3]))
            if crosses:
                dists = np.abs(gap_arr - y)
                order = np.argsort(dists)
                snapped = False
                for idx in order:
                    nearest = float(gap_arr[idx])
                    dist    = float(dists[idx])
                    if nearest in used_gaps:
                        continue
                    if snap_threshold <= 0.0 or dist <= snap_threshold:
                        result.append(nearest)
                        used_gaps.add(nearest)
                        snapped = True
                        break
                if not snapped:
                    result.append(y)
            else:
                result.append(y)
        return result

    # ------------------------------------------------------------------
    # Grid prediction
    # ------------------------------------------------------------------

    def predict_grid(
        self,
        image_bgr: np.ndarray,
        bboxes: list | None = None,
    ) -> GridPrediction:
        """
        Derive candidate grid lines from bboxes and filter by GridModelV2
        anchor confidence.

        Parameters
        ----------
        image_bgr : cropped table BGR image (any size)
        bboxes    : list of [x1, y1, x2, y2] cell bbox pixel coordinates
                    in crop space. Must not be None.

        Returns
        -------
        GridPrediction with filtered h/v lines.
        h_on_prob / v_on_prob carry the full sigmoid(on_logit) anchor arrays
        (model output space) for downstream consumers that need them.
        connectivity is populated when ConnClassifier is available and at
        least a 2x2 grid is detected.
        """
        if bboxes is None or len(bboxes) == 0:
            orig_h, orig_w = image_bgr.shape[:2]
            h_on_logit, _, v_on_logit, _, _ = self._run_inference(image_bgr)
            h_on_prob = (1.0 / (1.0 + np.exp(-h_on_logit.astype(np.float64)))).astype(np.float32)
            v_on_prob = (1.0 / (1.0 + np.exp(-v_on_logit.astype(np.float64)))).astype(np.float32)
            return GridPrediction(
                h_lines=[],
                v_lines=[],
                h_on_prob=h_on_prob,
                v_on_prob=v_on_prob,
                h_lines_norm=np.array([], dtype=np.float32),
                v_lines_norm=np.array([], dtype=np.float32),
                h_cls=np.array([], dtype=np.int32),
                connectivity=None,
            )

        orig_h, orig_w = image_bgr.shape[:2]

        h_on_logit, h_offset, v_on_logit, v_offset, feature_map = self._run_inference(image_bgr)
        h_on_prob = (1.0 / (1.0 + np.exp(-h_on_logit.astype(np.float64)))).astype(np.float32)
        v_on_prob = (1.0 / (1.0 + np.exp(-v_on_logit.astype(np.float64)))).astype(np.float32)

        # Derive candidate grid lines from bboxes (V1A rule-based algorithm)
        cand_h, cand_v, _ = _extract_candidate_grid(
            bboxes, orig_h, orig_w, self.grid_margin_px
        )

        # Score each candidate by nearest GridModelV2 anchor confidence
        h_scores = _score_candidates_by_anchor(cand_h, h_on_logit, float(orig_h))
        v_scores = _score_candidates_by_anchor(cand_v, v_on_logit, float(orig_w))

        # Filter candidates by threshold
        h_lines = [y for y, s in zip(cand_h, h_scores) if s >= self.h_on_threshold]
        v_lines = [x for x, s in zip(cand_v, v_scores) if s >= self.v_on_threshold]

        h_lines_norm = np.array([y / float(orig_h) for y in h_lines], dtype=np.float32)
        v_lines_norm = np.array([x / float(orig_w) for x in v_lines], dtype=np.float32)
        h_cls        = np.ones(len(h_lines), dtype=np.int32)

        # ConnClassifier (optional)
        connectivity = None
        if (self._conn_sess is not None
                and len(h_lines_norm) >= 2
                and len(v_lines_norm) >= 2):
            cell_feat = _extract_cell_features(feature_map, h_lines_norm, v_lines_norm)
            if np.isfinite(cell_feat).all():
                cell_inp     = cell_feat.transpose(2, 0, 1)[np.newaxis].astype(np.float32)
                conn_out     = self._conn_sess.run(None, {"cell_features": cell_inp})
                conn_logits  = conn_out[0][0]
                conn_prob    = 1.0 / (1.0 + np.exp(-conn_logits.astype(np.float64)))
                connectivity = conn_prob.transpose(1, 2, 0).astype(np.float32)

        return GridPrediction(
            h_lines=sorted(h_lines),
            v_lines=sorted(v_lines),
            h_on_prob=h_on_prob,
            v_on_prob=v_on_prob,
            h_lines_norm=h_lines_norm,
            v_lines_norm=v_lines_norm,
            h_cls=h_cls,
            connectivity=connectivity,
        )

    # ------------------------------------------------------------------
    # Full predict
    # ------------------------------------------------------------------

    def predict(
        self,
        image_bgr: np.ndarray,
        bboxes: list | None = None,
        texts: list | None = None,
        span_threshold: float = 0.1,
    ) -> tuple:
        """
        Predict grid boundaries and optionally assign bboxes to grid cells.

        Parameters
        ----------
        image_bgr      : cropped table BGR image (any size)
        bboxes         : list of [x1, y1, x2, y2] in crop space.
                         If None or empty, only grid prediction is returned.
        texts          : list of text strings aligned with bboxes.
        span_threshold : fractional overlap to trigger span expansion (default 0.1)

        Returns
        -------
        (GridPrediction, list[CellInfo])
        CellInfo list is empty when bboxes is None or empty.
        """
        if bboxes is None or len(bboxes) == 0:
            return self.predict_grid(image_bgr, bboxes), []

        grid = self.predict_grid(image_bgr, bboxes)

        crop_h = float(image_bgr.shape[0])
        crop_w = float(image_bgr.shape[1])

        bboxes_arr = np.asarray(bboxes, dtype=np.float32)

        cx_list = sorted((float(b[0]) + float(b[2])) / 2.0 for b in bboxes_arr)
        cy_list = sorted((float(b[1]) + float(b[3])) / 2.0 for b in bboxes_arr)

        # Build (y, score, cls) tuples for empty-line filter
        max_h    = len(grid.h_on_prob)
        anchors  = np.linspace(0.0, 1.0, max_h, dtype=np.float32)
        orig_h   = float(image_bgr.shape[0])
        orig_w   = float(image_bgr.shape[1])

        h_tuples = []
        for y, c in zip(
            grid.h_lines,
            grid.h_cls.tolist() if len(grid.h_cls) else [1] * len(grid.h_lines)
        ):
            y_norm = y / orig_h
            idx    = int(np.argmin(np.abs(anchors - y_norm)))
            score  = float(grid.h_on_prob[idx])
            h_tuples.append((y, score, c))

        max_v     = len(grid.v_on_prob)
        anchors_v = np.linspace(0.0, 1.0, max_v, dtype=np.float32)

        v_tuples = []
        for x in grid.v_lines:
            x_norm = x / orig_w
            idx    = int(np.argmin(np.abs(anchors_v - x_norm)))
            score  = float(grid.v_on_prob[idx])
            v_tuples.append((x, score, 0))

        if self.filter_empty_lines:
            h_tuples = self._filter_empty_lines(h_tuples, cy_list, crop_h)
            v_tuples = self._filter_empty_lines(v_tuples, cx_list, crop_w)
            # Remove leading lines with no bbox center between edge and line
            while h_tuples and not any(0.0 <= c <= h_tuples[0][0] for c in cy_list):
                h_tuples = h_tuples[1:]
            while v_tuples and not any(0.0 <= c <= v_tuples[0][0] for c in cx_list):
                v_tuples = v_tuples[1:]
            # Remove trailing lines with no bbox center between line and edge
            while h_tuples and not any(h_tuples[-1][0] <= c <= crop_h for c in cy_list):
                h_tuples = h_tuples[:-1]
            while v_tuples and not any(v_tuples[-1][0] <= c <= crop_w for c in cx_list):
                v_tuples = v_tuples[:-1]

        filtered_h     = [y for y, _, _ in h_tuples]
        filtered_v     = [x for x, _, _ in v_tuples]
        filtered_h_cls = np.array([c for _, _, c in h_tuples], dtype=np.int32)

        if self.snap_to_bbox_gaps:
            snapped    = self._snap_lines_to_bbox_gaps(filtered_h, bboxes_arr)
            h_tuples   = [(sy, sc, c) for sy, (_, sc, c) in zip(snapped, h_tuples)]
            filtered_h = [y for y, _, _ in h_tuples]

        filtered_h_norm = np.array([y / orig_h for y in filtered_h], dtype=np.float32)
        filtered_v_norm = np.array([x / orig_w for x in filtered_v], dtype=np.float32)

        grid = GridPrediction(
            h_lines=sorted(filtered_h),
            v_lines=sorted(filtered_v),
            h_on_prob=grid.h_on_prob,
            v_on_prob=grid.v_on_prob,
            h_lines_norm=filtered_h_norm,
            v_lines_norm=filtered_v_norm,
            h_cls=filtered_h_cls,
            connectivity=grid.connectivity,
        )

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
    # Empty-line filter (V2 tuple-based variant)
    # ------------------------------------------------------------------

    @staticmethod
    def _filter_empty_lines(
        lines: list,
        centers: list,
        image_size: float,
    ) -> list:
        """
        Merge adjacent (y, score, cls) line tuples that have no bbox center
        between them. When merging, the tuple with the higher score is kept.
        Convergence loop runs until stable.
        """
        if not lines:
            return lines

        current = sorted(lines)
        changed = True

        while changed:
            changed = False
            if len(current) < 2:
                break
            result = [current[0]]
            for i in range(1, len(current)):
                lo_y, lo_score, lo_cls = result[-1]
                hi_y, hi_score, hi_cls = current[i]
                has_center = any(lo_y <= c <= hi_y for c in centers)
                if not has_center:
                    if hi_score >= lo_score:
                        result[-1] = (hi_y, hi_score, hi_cls)
                    changed = True
                else:
                    result.append(current[i])
            current = result

        return current

    # ------------------------------------------------------------------
    # Grid-based bbox assignment
    # ------------------------------------------------------------------

    def _post_process_grid(
        self,
        bboxes_page: np.ndarray,
        grid: GridPrediction,
        span_threshold: float,
    ) -> list:
        """
        Assign each bbox to a grid cell (row, col) and compute span.
        All coordinates in crop space.
        """
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

        def find_cell_idx(pos: float, edges: list) -> int:
            for i in range(len(edges) - 1):
                if edges[i] <= pos < edges[i + 1]:
                    return i
            return max(0, len(edges) - 2)

        results: list[CellInfo] = []
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
                bbox_idx=i, row_start=row_start, row_end=row_end,
                col_start=col_start, col_end=col_end,
                row=base_row, col=base_col,
            ))

        return results
