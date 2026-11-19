"""
Adaptive RoI-pooling feature extraction.

Automatically dispatches between:
  - Naive per-bbox loop: zero setup cost, best for small B
  - SAT (integral image) path: O(C*H*W) setup, O(1) per-bbox mean/min/max query,
    best for large B

Calibrated for ~300x300 feature maps with C~10.

Crossover points (B * avg_patch_area / H*W):
  - entropy/margin requested: ~2.0   (SAT setup amortized across the extra maps)
  - otherwise:                ~50.0  (naive loop is extremely fast without probs)

Pooling ops (pooling_ops parameter)
------------------------------------
Two families of ops are supported, and they behave differently:

  - Per-channel ops:  'mean', 'min', 'max'
        Each produces one value per input channel (C dims).
  - Per-region ops:   'entropy', 'margin'
        Each collapses the channel axis into a single confidence/uncertainty
        scalar per bbox (1 dim). Always computed from channel-softmax
        probabilities regardless of `apply_softmax` (they are only
        meaningful over a probability distribution).

The output is the concatenation of all requested per-channel ops (in the
order given, each C-wide) followed by all requested per-region ops (in the
order given, each 1-wide). For example pooling_ops=('mean', 'min', 'max',
'entropy', 'margin') on a C-channel input produces a (B, 3*C + 2) array.
"""

import numpy as np
from typing import List, Tuple
from collections import defaultdict

# Recommended default pooling schemes, shared by all callers (node-level and
# edge-level) so that image feature pooling stays consistent across the
# codebase. See BoxRFDGNN.get_nn_input_from_datadict and
# pymupdf_util_edge.append_image_edge_features.
DEFAULT_FEATURE_MAP_POOLING_OPS = ('mean', 'max')
DEFAULT_CLASS_LOGITS_POOLING_OPS = ('mean', 'min', 'max', 'entropy', 'margin')

_CHANNEL_OPS = ('mean', 'min', 'max')
_REGION_OPS = ('entropy', 'margin')
_VALID_OPS = set(_CHANNEL_OPS) | set(_REGION_OPS)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _softmax_channels(fmap: np.ndarray) -> np.ndarray:
    """Channel-wise softmax along axis=0 of a (C, H, W) tensor."""
    C, H, W = fmap.shape
    f = fmap.reshape(C, -1).copy()
    f -= f.max(axis=0, keepdims=True)
    np.exp(f, out=f)
    f /= f.sum(axis=0, keepdims=True) + 1e-12
    return f.reshape(C, H, W)


def _pixel_entropy(probs: np.ndarray) -> np.ndarray:
    """Per-pixel entropy of a (C, H, W) probability map. Returns (H, W)."""
    eps = 1e-12
    return -(probs * np.log(probs + eps)).sum(axis=0)


def _pixel_margin(probs: np.ndarray) -> np.ndarray:
    """Per-pixel top1-top2 margin of a (C, H, W) probability map. Returns (H, W)."""
    C = probs.shape[0]
    if C < 2:
        return probs[0]
    idx = np.argpartition(probs, -2, axis=0)[-2:]
    top2 = np.take_along_axis(probs, idx, axis=0)
    top2.sort(axis=0)
    return top2[1] - top2[0]


def _build_sat(arr: np.ndarray) -> np.ndarray:
    """Summed Area Table over the last two axes. Returns (..., H+1, W+1)."""
    prefix = arr.shape[:-2]
    H, W = arr.shape[-2], arr.shape[-1]
    sat = np.zeros((*prefix, H + 1, W + 1), dtype=np.float64)
    np.cumsum(arr, axis=-2, out=sat[..., 1:, 1:])
    np.cumsum(sat[..., 1:, 1:], axis=-1, out=sat[..., 1:, 1:])
    return sat


def _sat_rect_sum(sat, y1, x1, y2, x2):
    """Vectorized rectangle sum on a SAT. Coords are inclusive."""
    return (
        sat[..., y2 + 1, x2 + 1]
        - sat[..., y1, x2 + 1]
        - sat[..., y2 + 1, x1]
        + sat[..., y1, x1]
    )


def _grid_coords_vec(bb, W, H, page_width, page_height):
    """Map image-space bboxes to feature-grid indices (vectorized)."""
    sx = W / float(page_width)
    sy = H / float(page_height)
    gx1 = np.floor(bb[:, 0] * sx).astype(np.intp).clip(0, W - 1)
    gy1 = np.floor(bb[:, 1] * sy).astype(np.intp).clip(0, H - 1)
    gx2 = (np.ceil(bb[:, 2] * sx).astype(np.intp) - 1).clip(0, W - 1)
    gy2 = (np.ceil(bb[:, 3] * sy).astype(np.intp) - 1).clip(0, H - 1)
    gx2 = np.maximum(gx2, gx1)
    gy2 = np.maximum(gy2, gy1)
    return gx1, gy1, gx2, gy2


def _split_ops(pooling_ops):
    """Split a pooling_ops tuple into (channel_ops, region_ops), each
    preserving the relative order they appeared in pooling_ops."""
    channel_ops = [op for op in pooling_ops if op in _CHANNEL_OPS]
    region_ops = [op for op in pooling_ops if op in _REGION_OPS]
    return channel_ops, region_ops


def _output_dim(C, channel_ops, region_ops):
    return C * len(channel_ops) + len(region_ops)


# ---------------------------------------------------------------------------
# Path A: naive per-bbox loop (low overhead)
# ---------------------------------------------------------------------------

def _path_naive(fmap_used, probs, gx1, gy1, gx2, gy2, pooling_ops):
    channel_ops, region_ops = _split_ops(pooling_ops)
    C = fmap_used.shape[0]
    B = len(gx1)
    out_dim = _output_dim(C, channel_ops, region_ops)
    out = np.zeros((B, out_dim), dtype=np.float32)

    for i in range(B):
        y1i, y2i, x1i, x2i = gy1[i], gy2[i], gx1[i], gx2[i]
        patch = fmap_used[:, y1i:y2i + 1, x1i:x2i + 1]
        if patch.size == 0:
            continue

        parts = []
        for op in channel_ops:
            if op == 'mean':
                parts.append(patch.mean(axis=(1, 2)))
            elif op == 'max':
                parts.append(patch.max(axis=(1, 2)))
            elif op == 'min':
                parts.append(patch.min(axis=(1, 2)))

        if region_ops:
            pp = probs[:, y1i:y2i + 1, x1i:x2i + 1]
            for op in region_ops:
                if op == 'entropy':
                    parts.append(np.array([_pixel_entropy(pp).mean()]))
                elif op == 'margin':
                    parts.append(np.array([_pixel_margin(pp).mean()]))

        pooled = np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)
        out[i, :pooled.shape[0]] = pooled.astype(np.float32)
    return out


# ---------------------------------------------------------------------------
# Path B: SAT-based (amortized O(1) mean/min/max via grouped batch slicing)
# ---------------------------------------------------------------------------

def _grouped_minmax(fmap_used, gx1, gy1, gx2, gy2, need_max, need_min):
    """
    Compute per-bbox min and/or max via grouped batch slicing: bboxes with
    the same (height, width) in feature-grid units are stacked into one
    array and reduced together, avoiding a per-bbox python loop.

    min/max cannot be expressed via a summed-area table (unlike mean), so
    this always has to run against the actual bboxes -- there is nothing
    here that can be precomputed once and reused across different bbox
    sets (contrast with RoiPoolingSession's sat_mean / sat_region, which
    ARE bbox-independent and shareable).

    Returns:
        (max_all, min_all) -- each either an (B, C) float32 array or None
        depending on whether it was requested.
    """
    C = fmap_used.shape[0]
    B = len(gx1)
    max_all = np.empty((B, C), dtype=np.float32) if need_max else None
    min_all = np.empty((B, C), dtype=np.float32) if need_min else None

    ph_arr = gy2 - gy1 + 1
    pw_arr = gx2 - gx1 + 1
    groups = defaultdict(list)
    for i in range(B):
        groups[(int(ph_arr[i]), int(pw_arr[i]))].append(i)
    for (ph, pw), indices in groups.items():
        idx = np.array(indices, dtype=np.intp)
        n = len(idx)
        patches = np.empty((n, C, ph, pw), dtype=fmap_used.dtype)
        for j, bi in enumerate(idx):
            patches[j] = fmap_used[:, gy1[bi]:gy1[bi] + ph, gx1[bi]:gx1[bi] + pw]
        if need_max:
            max_all[idx] = patches.max(axis=(2, 3))
        if need_min:
            min_all[idx] = patches.min(axis=(2, 3))
    return max_all, min_all


def _path_sat(fmap_used, probs, gx1, gy1, gx2, gy2, pooling_ops):
    channel_ops, region_ops = _split_ops(pooling_ops)
    C, H, W = fmap_used.shape
    B = len(gx1)
    areas = ((gy2 - gy1 + 1) * (gx2 - gx1 + 1)).astype(np.float64)

    mean_all = None
    if 'mean' in channel_ops:
        sat_f = _build_sat(fmap_used)  # (C, H+1, W+1)
        mean_all = (_sat_rect_sum(sat_f, gy1, gx1, gy2, gx2)
                    / areas[np.newaxis, :]).T.astype(np.float32)  # (B, C)

    need_max = 'max' in channel_ops
    need_min = 'min' in channel_ops
    max_all, min_all = (
        _grouped_minmax(fmap_used, gx1, gy1, gx2, gy2, need_max, need_min)
        if (need_max or need_min) else (None, None)
    )

    channel_results = {'mean': mean_all, 'max': max_all, 'min': min_all}

    region_results = {}
    for op in region_ops:
        if op == 'entropy':
            region_map = _pixel_entropy(probs)
        elif op == 'margin':
            region_map = _pixel_margin(probs)
        sat_r = _build_sat(region_map)
        region_mean = (_sat_rect_sum(sat_r, gy1, gx1, gy2, gx2)
                       / areas).astype(np.float32)
        region_results[op] = region_mean

    parts = [channel_results[op] for op in channel_ops]
    parts += [region_results[op][:, np.newaxis] for op in region_ops]

    if not parts:
        return np.zeros((B, 0), dtype=np.float32)
    return np.concatenate(parts, axis=1)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_bbox_features_by_roi_pooling(
    features: np.ndarray,
    bboxes: List[Tuple[float, float, float, float]],
    page_width: int,
    page_height: int,
    pooling_ops: tuple = ('mean', 'max'),
    apply_softmax: bool = False,
) -> np.ndarray:
    """
    Extract per-bbox features via configurable pooling ops.

    Args:
        features: (1, C, H, W) feature map (raw activations or logits).
        bboxes: list of [x1, y1, x2, y2] in the same coordinate space as
            page_width/page_height (NOT necessarily the feature map's own
            H/W; this function rescales internally).
        page_width, page_height: dimensions of the coordinate space the
            bboxes are expressed in (e.g. the page raster used to run the
            model, not the model's internal H/W).
        pooling_ops: subset of {'mean', 'min', 'max', 'entropy', 'margin'}.
            - 'mean'/'min'/'max' are per-channel (C dims each) and are
              computed on `features` directly, or on softmax(features) if
              apply_softmax=True.
            - 'entropy'/'margin' are per-region scalars (1 dim each) and are
              ALWAYS computed on softmax(features), regardless of
              apply_softmax -- they are only meaningful over a probability
              distribution, so this is not user-configurable.
            Output is the concatenation of per-channel ops (in the order
            given) followed by per-region ops (in the order given).
        apply_softmax: whether the per-channel ops ('mean'/'min'/'max') pool
            over raw `features` or over channel-softmax probabilities.
            Has no effect on 'entropy'/'margin'.

    Returns:
        np.ndarray of shape (B, C*len(channel_ops) + len(region_ops)).

    Adaptively dispatches between a naive per-bbox loop and a SAT-based
    vectorized path based on the estimated computational cost ratio.
    """
    assert features.ndim == 4
    N, C, H, W = features.shape
    assert N == 1

    unknown_ops = set(pooling_ops) - _VALID_OPS
    if unknown_ops:
        raise ValueError(f"Unknown pooling_ops: {sorted(unknown_ops)}. "
                         f"Valid ops are {sorted(_VALID_OPS)}.")

    channel_ops, region_ops = _split_ops(pooling_ops)
    needs_probs = bool(region_ops)

    B = len(bboxes)
    if B == 0:
        return np.zeros((0, _output_dim(C, channel_ops, region_ops)), dtype=np.float32)

    fmap = features[0]
    bb = np.asarray(bboxes, dtype=np.float64)
    gx1, gy1, gx2, gy2 = _grid_coords_vec(bb, W, H, page_width, page_height)

    # ---- Dispatch heuristic ----
    # Cost metric: B * avg_patch_area / (H * W)
    # Empirically calibrated thresholds for 300x300, C=10:
    #   entropy/margin requested -> crossover at metric ~ 2   (SAT builds extra tables)
    #   otherwise                -> crossover at metric ~ 50  (loop skips probs entirely)
    avg_patch_area = float(((gy2 - gy1 + 1) * (gx2 - gx1 + 1)).mean())
    cost_metric = B * avg_patch_area / float(H * W)
    threshold = 2.0 if needs_probs else 50.0

    use_sat = cost_metric > threshold

    if use_sat:
        # probs is needed either for channel-ops (apply_softmax) or region-ops.
        if apply_softmax or needs_probs:
            probs = _softmax_channels(fmap)
        else:
            probs = None
        fmap_used = probs if apply_softmax else fmap
        return _path_sat(fmap_used, probs, gx1, gy1, gx2, gy2, pooling_ops)
    else:
        # Lazy computation: skip softmax when not needed
        if apply_softmax:
            fmap_used = _softmax_channels(fmap)
            probs = fmap_used if needs_probs else None
        else:
            fmap_used = fmap
            probs = _softmax_channels(fmap) if needs_probs else None
        return _path_naive(fmap_used, probs, gx1, gy1, gx2, gy2, pooling_ops)


# ---------------------------------------------------------------------------
# Multi-query session (shares bbox-independent setup across queries)
# ---------------------------------------------------------------------------

class RoiPoolingSession:
    """
    Precomputes the bbox-INDEPENDENT parts of ROI pooling once for a given
    (features, pooling_ops, apply_softmax) combination, then lets you
    query() it against multiple different bbox sets cheaply.

    Motivating case: BoxRFDGNN pools the same feature_map/class_logits
    tensor twice per page -- once for node bboxes, once for edge-union
    bboxes (when use_image_edge=True). Calling
    extract_bbox_features_by_roi_pooling() twice rebuilds the channel
    softmax and the 'mean'/'entropy'/'margin' summed-area tables (SATs)
    twice, even though those depend only on the tensor + pooling_ops, not
    on which bboxes are being queried. This class builds them once and
    reuses them for every query() call.

    'min'/'max' are NOT expressible via a SAT (unlike mean), so they are
    always recomputed per query() call directly from that call's bboxes
    (grouped batch slicing) -- there is nothing to share for those ops.

    When to use this vs. extract_bbox_features_by_roi_pooling():
      - Querying a tensor ONCE (e.g. YF's per-page feature map): use the
        plain function. It dispatches naive-vs-SAT based on bbox count, so
        small queries stay cheap; a session would force the SAT build cost
        even for a single small query.
      - Querying the SAME tensor MULTIPLE times (e.g. node bboxes then edge
        bboxes against the same feature_map): use a session. The one-time
        SAT build cost is paid once and amortized across all query() calls,
        which is strictly cheaper than paying it (or the naive-path cost)
        separately per call.
    """

    def __init__(self, features: np.ndarray, pooling_ops: tuple = ('mean', 'max'),
                apply_softmax: bool = False):
        assert features.ndim == 4
        N, C, H, W = features.shape
        assert N == 1

        unknown_ops = set(pooling_ops) - _VALID_OPS
        if unknown_ops:
            raise ValueError(f"Unknown pooling_ops: {sorted(unknown_ops)}. "
                             f"Valid ops are {sorted(_VALID_OPS)}.")

        self._C, self._H, self._W = C, H, W
        self._channel_ops, self._region_ops = _split_ops(pooling_ops)

        fmap = features[0]
        needs_probs = bool(self._region_ops)
        if apply_softmax or needs_probs:
            probs = _softmax_channels(fmap)
        else:
            probs = None
        self._fmap_used = probs if apply_softmax else fmap

        # Bbox-independent, shareable precomputation:
        self._sat_mean = (_build_sat(self._fmap_used)
                          if 'mean' in self._channel_ops else None)
        self._sat_region = {}
        for op in self._region_ops:
            region_map = _pixel_entropy(probs) if op == 'entropy' else _pixel_margin(probs)
            self._sat_region[op] = _build_sat(region_map)

    def query(self, bboxes: List[Tuple[float, float, float, float]],
             page_width: int, page_height: int) -> np.ndarray:
        """
        Pool this session's tensor over a new set of bboxes. Cheap to call
        repeatedly: 'mean'/'entropy'/'margin' are O(1) per bbox (SAT lookup,
        built once in __init__); 'min'/'max' still cost a grouped batch
        slicing pass over these specific bboxes (unavoidable, see class
        docstring).
        """
        B = len(bboxes)
        if B == 0:
            return np.zeros((0, _output_dim(self._C, self._channel_ops, self._region_ops)),
                            dtype=np.float32)

        bb = np.asarray(bboxes, dtype=np.float64)
        gx1, gy1, gx2, gy2 = _grid_coords_vec(bb, self._W, self._H, page_width, page_height)
        areas = ((gy2 - gy1 + 1) * (gx2 - gx1 + 1)).astype(np.float64)

        mean_all = None
        if self._sat_mean is not None:
            mean_all = (_sat_rect_sum(self._sat_mean, gy1, gx1, gy2, gx2)
                        / areas[np.newaxis, :]).T.astype(np.float32)

        need_max = 'max' in self._channel_ops
        need_min = 'min' in self._channel_ops
        max_all, min_all = (
            _grouped_minmax(self._fmap_used, gx1, gy1, gx2, gy2, need_max, need_min)
            if (need_max or need_min) else (None, None)
        )

        channel_results = {'mean': mean_all, 'max': max_all, 'min': min_all}
        parts = [channel_results[op] for op in self._channel_ops]

        for op in self._region_ops:
            region_mean = (_sat_rect_sum(self._sat_region[op], gy1, gx1, gy2, gx2)
                          / areas).astype(np.float32)
            parts.append(region_mean[:, np.newaxis])

        if not parts:
            return np.zeros((B, 0), dtype=np.float32)
        return np.concatenate(parts, axis=1)
