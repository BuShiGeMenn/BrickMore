"""
TableGridExtractorV2B.py

Hybrid table grid extractor combining:
  - Rule-based candidate grid lines from bbox geometry (same as V2A).
  - V2B-style region gate: GridModelV2 on_prob arrays are resized to pixel
    space and passed through 1D CCL to define active intervals. A candidate
    line survives if its position falls inside any active interval (score =
    1.0); otherwise it is rejected (score = 0.0).

Design philosophy
-----------------
V2  : anchor decode (on_logit + offset + NMS) determines position directly.
V2A : bbox geometry determines position; nearest anchor on_prob acts as a
      soft confidence filter.
V2B : bbox geometry determines position (precise); on_prob is resized to
      pixel space and treated as a continuous 1D signal, from which CCL
      extracts active regions. A candidate inside an active region is kept
      unconditionally (score = 1.0).

This is the V2 counterpart of V1B. The gate implementation (on_prob ->
resize -> CCL -> intervals) is identical to V1B; only the source of the
1D probability signal differs (heatmap in V1B, resized on_prob in V2B).
offset is intentionally unused: position accuracy comes from bbox geometry,
so the offset's role in V2 is superseded.

V2B inherits from V2A all V2-specific features:
  - ConnClassifier support.
  - GlobalConfig threshold override.
  - snap_to_bbox_gaps.
  - filter_empty_lines (tuple-based, score-aware merge).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import onnxruntime as ort

from .GlobalConfig import get_config
from .table_grid_types import GridPrediction, CellInfo
from .common_util import make_session


# ---------------------------------------------------------------------------
# Candidate grid extraction (V3 algorithm, identical to V2A)
# ---------------------------------------------------------------------------

def _find_grid_lines_by_empty_space(
    candidate_boundaries: set,
    all_cell_bboxes: list,
    is_horizontal_coord: bool,
    min_empty_gap_size: float,
) -> list:
    """
    Derive grid lines from candidate boundary coordinates by detecting
    empty strips between cell bboxes (unchanged from V2A).
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
    Derive candidate h/v grid lines from cell bboxes (unchanged from V2A).

    Returns
    -------
    (candidate_h_lines, candidate_v_lines, cells_bbox_shrunk)
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
# Cell feature extraction (identical to V2 / V2A)
# ---------------------------------------------------------------------------

def _extract_cell_features(
    feature_map: np.ndarray,
    h_lines_norm: np.ndarray,
    v_lines_norm: np.ndarray,
) -> np.ndarray:
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
# CCL active-interval extraction (identical to V1B, operates on pixel-space
# 1D signal regardless of its origin)
# ---------------------------------------------------------------------------

def _ccl_1d_active_intervals(
    signal_1d: np.ndarray,
    threshold: float,
) -> list[tuple[int, int]]:
    """
    Apply threshold to a 1D float array and return (start, end) pixel
    intervals of every connected active component.

    Parameters
    ----------
    signal_1d : 1D float32 array in pixel space (length = image dimension)
    threshold : minimum activation value

    Returns
    -------
    List of (start_px, end_px) tuples, inclusive, sorted by start.
    """
    active = signal_1d >= threshold
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
        intervals.append((group_start, len(signal_1d) - 1))

    return intervals


def _score_candidates_by_ccl_intervals(
    positions_px: list,
    intervals: list[tuple[int, int]],
    signal_1d: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Assign score 1.0 to each candidate position that falls inside at least
    one CCL active interval; assign 0.0 otherwise.
    Also return the signal value at each candidate position for top_k ranking.

    Parameters
    ----------
    positions_px : list of integer candidate positions in pixel space
    intervals    : list of (start, end) active intervals
    signal_1d    : 1D float32 array in pixel space (on_prob or heatmap)

    Returns
    -------
    gate_scores  : np.ndarray of float32, 1.0 if inside interval else 0.0
    prob_scores  : np.ndarray of float32, signal value at each candidate position
    """
    gate_scores = np.zeros(len(positions_px), dtype=np.float32)
    prob_scores = np.zeros(len(positions_px), dtype=np.float32)
    n = len(signal_1d)
    for i, pos in enumerate(positions_px):
        prob_scores[i] = signal_1d[min(int(pos), n - 1)]
        for start, end in intervals:
            if start <= pos <= end:
                gate_scores[i] = 1.0
                break
    return gate_scores, prob_scores


def _apply_top_k_per_interval(
    lines: list,
    intervals: list[tuple[int, int]],
    prob_map: dict,
    top_k: int,
) -> list:
    """
    Within each CCL active interval, retain at most top_k candidates ranked
    by their on_prob value (highest first). Candidates not covered by any
    interval are passed through unchanged (they have already been gate-filtered
    before this call, so in practice none should remain).

    Parameters
    ----------
    lines     : list of candidate positions that passed the CCL gate
    intervals : list of (start, end) active intervals
    prob_map  : dict mapping position -> on_prob value for each line
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
        members_sorted = sorted(members, key=lambda y: prob_map.get(y, 0.0), reverse=True)
        for y in members_sorted[:top_k]:
            kept.add(y)
    return sorted(kept)


# ---------------------------------------------------------------------------
# Main extractor class
# ---------------------------------------------------------------------------

class TableGridExtractorV2B:
    """
    Hybrid table grid extractor (V2B).

    Candidate grid lines are derived from cell bbox geometry (V3 rule-based
    algorithm, same as V2A). Active regions are determined by resizing the
    GridModelV2 on_prob arrays to pixel space and applying 1D CCL (same gate
    logic as V1B). A candidate line is kept (score = 1.0) if and only if it
    falls inside a CCL active interval.

    V2-specific features preserved from V2A:
      - ConnClassifier support.
      - GlobalConfig threshold override.
      - snap_to_bbox_gaps.
      - filter_empty_lines with score-aware tuple merge.
    """

    def __init__(
        self,
        grid_onnx_path,
        conn_onnx_path=None,
        h_on_threshold: float = 0.25,
        v_on_threshold: float = 0.2,
        conn_threshold: float = 0.2,
        grid_margin_px: float = 5.0,
        top_k: int = 1,
        filter_empty_lines: bool = True,
        snap_to_bbox_gaps: bool = False,
        header_type="1-Row",
        merge_type="BBox",
        providers=None,
    ) -> None:
        """
        Parameters
        ----------
        grid_onnx_path    : path to exported GridModelV2 .onnx file
        conn_onnx_path    : path to ConnClassifier .onnx file (optional)
        h_on_threshold    : on_prob threshold for h CCL active intervals
        v_on_threshold    : on_prob threshold for v CCL active intervals
        conn_threshold    : connectivity classifier probability threshold
        grid_margin_px    : alignment tolerance for candidate grid extraction
        top_k             : max candidates kept per CCL interval ranked by on_prob
                            value; candidates beyond top_k are dropped. Use 0 or
                            a negative value to disable (keep all).
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
        self.top_k              = top_k
        self.filter_empty_lines = filter_empty_lines
        self.snap_to_bbox_gaps  = snap_to_bbox_gaps
        self.header_type        = header_type
        self.merge_type         = merge_type

        global_config = get_config()
        if global_config.get("TableGridExtractorV2B") is not None:
            self.v_on_threshold = global_config.get("TableGridExtractorV2B.v_on_threshold")
            self.h_on_threshold = global_config.get("TableGridExtractorV2B.h_on_threshold")

        self._grid_sess = make_session(str(self.grid_onnx_path), providers)
        self._conn_sess = (
            make_session(str(self.conn_onnx_path), providers)
            if self.conn_onnx_path and self.conn_onnx_path.exists() else None
        )

        inp = self._grid_sess.get_inputs()[0]
        self._input_h = int(inp.shape[2])
        self._input_w = int(inp.shape[3])

        dummy   = np.zeros((1, 3, self._input_h, self._input_w), dtype=np.float32)
        outputs = self._grid_sess.run(None, {"image": dummy})
        self._max_h = int(outputs[0].shape[1])  # h_on_logit length
        self._max_v = int(outputs[2].shape[1])  # v_on_logit length

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def _run_inference(self, image_bgr: np.ndarray) -> tuple:
        """
        Run GridModelV2 inference and return raw outputs.

        Returns
        -------
        (h_on_logit, h_offset, v_on_logit, v_offset, feature_map,
         h_on_prob_px, v_on_prob_px)

        h_on_prob_px : (orig_h,) float32 - on_prob resized to pixel space
        v_on_prob_px : (orig_w,) float32 - on_prob resized to pixel space
        """
        import cv2

        orig_h, orig_w = image_bgr.shape[:2]

        img_resized = cv2.resize(image_bgr, (self._input_w, self._input_h))
        img_rgb     = img_resized[:, :, ::-1].astype(np.float32) / 255.0
        inp         = img_rgb.transpose(2, 0, 1)[np.newaxis]

        outputs     = self._grid_sess.run(None, {"image": inp})
        h_on_logit  = outputs[0][0]   # (max_h,)
        h_offset    = outputs[1][0]   # (max_h,)
        v_on_logit  = outputs[2][0]   # (max_v,)
        v_offset    = outputs[3][0]   # (max_v,)
        feature_map = outputs[4][0]   # (C, H', W')

        h_on_prob = (1.0 / (1.0 + np.exp(-h_on_logit.astype(np.float64)))).astype(np.float32)
        v_on_prob = (1.0 / (1.0 + np.exp(-v_on_logit.astype(np.float64)))).astype(np.float32)

        # Resize on_prob from anchor space to pixel space (Option C)
        # offset is intentionally ignored: position accuracy is delegated
        # to bbox geometry; on_prob alone is sufficient for region gating.
        h_on_prob_px = cv2.resize(
            h_on_prob[np.newaxis, :].astype(np.float32),
            (orig_h, 1),
            interpolation=cv2.INTER_LINEAR,
        )[0]  # (orig_h,)
        v_on_prob_px = cv2.resize(
            v_on_prob[np.newaxis, :].astype(np.float32),
            (orig_w, 1),
            interpolation=cv2.INTER_LINEAR,
        )[0]  # (orig_w,)

        return (
            h_on_logit, h_offset, v_on_logit, v_offset, feature_map,
            h_on_prob, v_on_prob,
            h_on_prob_px, v_on_prob_px,
        )

    # ------------------------------------------------------------------
    # Snap helper (identical to V2A)
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

        bottoms   = np.sort(bboxes_crop[:, 3])
        tops      = np.sort(bboxes_crop[:, 1])
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
    # Empty-line filter (V2 tuple-based, score-aware, identical to V2A)
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
    # Grid prediction
    # ------------------------------------------------------------------

    def predict_grid(
        self,
        image_bgr: np.ndarray,
        bboxes: list | None = None,
    ) -> GridPrediction:
        """
        Derive candidate grid lines from bboxes and gate them by CCL active
        intervals extracted from the pixel-space on_prob signal.

        Scoring rule
        ------------
        - Resize on_prob (anchor space) to pixel space.
        - Run 1D CCL with threshold to obtain active intervals.
        - Candidate inside any interval -> score = 1.0 (kept).
        - Candidate outside all intervals -> score = 0.0 (dropped).

        Parameters
        ----------
        image_bgr : cropped table BGR image (any size)
        bboxes    : list of [x1, y1, x2, y2] cell bbox pixel coordinates.
                    When None or empty, returns an empty GridPrediction with
                    h_on_prob / v_on_prob populated for downstream use.

        Returns
        -------
        GridPrediction with filtered h/v lines and binary confidence scores
        stored in h_confidences / v_confidences.
        h_on_prob / v_on_prob carry the full anchor-space sigmoid arrays.
        """
        orig_h, orig_w = image_bgr.shape[:2]

        (h_on_logit, h_offset, v_on_logit, v_offset, feature_map,
         h_on_prob, v_on_prob,
         h_on_prob_px, v_on_prob_px) = self._run_inference(image_bgr)

        if bboxes is None or len(bboxes) == 0:
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

        # Derive candidate grid lines from bboxes (V3 rule-based)
        cand_h, cand_v, _ = _extract_candidate_grid(
            bboxes, orig_h, orig_w, self.grid_margin_px
        )

        # Build CCL active intervals from pixel-space on_prob
        h_intervals = _ccl_1d_active_intervals(h_on_prob_px, self.h_on_threshold)
        v_intervals = _ccl_1d_active_intervals(v_on_prob_px, self.v_on_threshold)

        # Score candidates: gate=1.0 if inside interval; prob=on_prob value at position
        h_scores, h_probs = _score_candidates_by_ccl_intervals(cand_h, h_intervals, h_on_prob_px)
        v_scores, v_probs = _score_candidates_by_ccl_intervals(cand_v, v_intervals, v_on_prob_px)

        # Keep only candidates with gate score == 1.0
        h_lines = [y for y, s in zip(cand_h, h_scores) if s > 0.0]
        v_lines = [x for x, s in zip(cand_v, v_scores) if s > 0.0]

        # Apply top_k: within each CCL interval keep at most top_k candidates
        # ranked by on_prob value (highest first). Disabled when top_k <= 0.
        if self.top_k > 0:
            h_prob_map = {y: float(h_probs[i])
                          for i, y in enumerate(cand_h) if h_scores[i] > 0.0}
            v_prob_map = {x: float(v_probs[i])
                          for i, x in enumerate(cand_v) if v_scores[i] > 0.0}

            h_lines = _apply_top_k_per_interval(h_lines, h_intervals, h_prob_map, self.top_k)
            v_lines = _apply_top_k_per_interval(v_lines, v_intervals, v_prob_map, self.top_k)

        h_lines_norm = np.array([y / float(orig_h) for y in h_lines], dtype=np.float32)
        v_lines_norm = np.array([x / float(orig_w) for x in v_lines], dtype=np.float32)
        h_cls        = np.ones(len(h_lines), dtype=np.int32)

        # ConnClassifier (optional, identical to V2A)
        connectivity = None
        if (self._conn_sess is not None
                and len(h_lines_norm) >= 2
                and len(v_lines_norm) >= 2):
            cell_feat = _extract_cell_features(feature_map, h_lines_norm, v_lines_norm)
            if np.isfinite(cell_feat).all():
                cell_inp    = cell_feat.transpose(2, 0, 1)[np.newaxis].astype(np.float32)
                conn_out    = self._conn_sess.run(None, {"cell_features": cell_inp})
                conn_logits = conn_out[0][0]
                conn_prob   = 1.0 / (1.0 + np.exp(-conn_logits.astype(np.float64)))
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
        span_threshold : fractional overlap to trigger span expansion

        Returns
        -------
        (GridPrediction, list[CellInfo])
        """
        if bboxes is None or len(bboxes) == 0:
            return self.predict_grid(image_bgr, bboxes), []

        grid = self.predict_grid(image_bgr, bboxes)

        crop_h     = float(image_bgr.shape[0])
        crop_w     = float(image_bgr.shape[1])
        orig_h     = crop_h
        orig_w     = crop_w
        bboxes_arr = np.asarray(bboxes, dtype=np.float32)

        cx_list = sorted((float(b[0]) + float(b[2])) / 2.0 for b in bboxes_arr)
        cy_list = sorted((float(b[1]) + float(b[3])) / 2.0 for b in bboxes_arr)

        # Build (y, score, cls) tuples for empty-line filter.
        # Score is read from the nearest anchor in on_prob (same as V2A),
        # so that the score-aware merge keeps the more confident line.
        max_h    = len(grid.h_on_prob)
        anchors  = np.linspace(0.0, 1.0, max_h, dtype=np.float32)

        h_tuples = []
        for y, c in zip(
            grid.h_lines,
            grid.h_cls.tolist() if len(grid.h_cls) else [1] * len(grid.h_lines),
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
            while h_tuples and not any(0.0 <= c <= h_tuples[0][0] for c in cy_list):
                h_tuples = h_tuples[1:]
            while v_tuples and not any(0.0 <= c <= v_tuples[0][0] for c in cx_list):
                v_tuples = v_tuples[1:]
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
    # Grid-based bbox assignment (identical to V2A)
    # ------------------------------------------------------------------

    def _post_process_grid(
        self,
        bboxes_page: np.ndarray,
        grid: GridPrediction,
        span_threshold: float,
    ) -> list:
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
