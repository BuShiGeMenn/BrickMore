"""
Edge feature computation module
Maintained by: PDF Engineers (edge_type implementations) + AI Researchers (orchestration)
Purpose: Compute edge attributes for graph neural network input

Edge types:
    - default: Relative bbox geometry (get_edge_transform_bbox)
    - SEO: Default + alignment features (get_edge_transform_bbox_add_alignment)
    - PRS: Presidio spatial features (compute_edge_features)
    - YF: Default + "what's between the two endpoints" features
          (get_edge_transform_yf) -- num_bbox_cross / num_vector_cross,
          how many other text bboxes / vector lines the straight line
          between the edge's two node centers passes through. Unlike SEO's
          alignment flags (redundant with the default 18-dim relation
          features and with DGCNN's own h_j-h_i difference-vector
          inductive bias), this is genuine page-level context that neither
          endpoint bbox alone, nor the two together, can express.

To add a new edge type:
    1. Implement compute function in this file
    2. Register it in get_edge_attr()
"""

import numpy as np

from .common_util import (get_edge_by_directional_nn, get_edge_by_alignment,
                          get_edge_transform_bbox, get_edge_transform_bbox_add_alignment)
from .pymupdf_util_base import get_rect_member_id, find_closed_border_rects
from .roi_pooling import (extract_bbox_features_by_roi_pooling,
                          DEFAULT_FEATURE_MAP_POOLING_OPS,
                          DEFAULT_CLASS_LOGITS_POOLING_OPS)


def _segment_rect_intersect_mask(x0, y0, x1, y1, rx1, ry1, rx2, ry2):
    """
    Liang-Barsky segment-vs-many-axis-aligned-rects intersection test,
    vectorized over rects for one fixed segment.

    Segment: (x0, y0) -> (x1, y1), scalars.
    Rects: rx1, ry1, rx2, ry2 -- each an (M,) array (parallel arrays of
        rectangle bounds to test against).

    Returns:
        (M,) bool array: whether the segment intersects each rect (full
        containment of either endpoint inside a rect also counts as an
        intersection -- no special-casing needed, Liang-Barsky handles it
        the same way as a proper crossing).
    """
    dx = x1 - x0
    dy = y1 - y0
    t0 = np.zeros(rx1.shape, dtype=np.float64)
    t1 = np.ones(rx1.shape, dtype=np.float64)
    valid = np.ones(rx1.shape, dtype=bool)

    for p, q in ((-dx, x0 - rx1), (dx, rx2 - x0), (-dy, y0 - ry1), (dy, ry2 - y0)):
        if abs(p) < 1e-12:
            # Segment is parallel to this axis' bounds: only invalid where
            # the segment starts outside the slab on this axis.
            valid &= (q >= 0)
        else:
            r = q / p
            if p < 0:
                t0 = np.maximum(t0, r)
            else:
                t1 = np.minimum(t1, r)

    valid &= (t0 <= t1)
    return valid


def get_edge_transform_yf(bboxes, edge_index, data_dict=None):
    """
    edge_type='YF': the default 18-dim relation features
    (get_edge_transform_bbox) plus 2 new columns that require knowing every
    OTHER element's position on the page -- genuinely non-local information
    that neither the 18-dim relation features nor DGCNN's own h_j-h_i
    difference-vector message construction can express, unlike SEO's
    alignment flags (see module docstring):

        num_bbox_cross:     how many other text bboxes the straight line
            between the two endpoint centers passes through.
        num_vector_cross:   how many vector lines (from
            data_dict['vector_lines'], the same cache used by
            pymupdf_util_yf.py's vector_margin_* channels) that line
            passes through.
        same_rect_member:   1.0 if both endpoints' centers fall inside the
            SAME fully-closed border rectangle (e.g. the same full-border
            table -- see pymupdf_util_base.find_closed_border_rects), else
            0.0. This is what actually disambiguates "two cells of the same
            table" (should connect) from "two cells of separate, nearby
            tables" (should not) -- num_bbox_cross/num_vector_cross alone
            can't reliably tell these apart, since both situations can show
            small counts of each. Deliberately NOT based on
            page.cluster_drawings()-style proximity clustering -- see
            find_closed_border_rects's docstring for why.

    num_bbox_cross and num_vector_cross are log1p-compressed before being
    appended: raw counts range from 0 (short adjacent edges) to several
    dozen (edges spanning most of the page), and log1p keeps one large
    count from dominating. same_rect_member is already a clean binary flag.

    Assumes no bbox-fully-contains-another-bbox case among text elements
    (true for PDF-native text extraction: one parsed text line/word never
    encloses another). Liang-Barsky handles full containment the same as
    a proper crossing regardless, so this assumption affects interpretation
    ("crossing" vs "containing") but not correctness of the count.

    Args:
        bboxes: (N, 4) array/list of [x1, y1, x2, y2].
        edge_index: list of (i, j) node-index tuples.
        data_dict: optional; if data_dict['vector_lines'] / ['closed_rects']
            are present (see pymupdf_util_base.extract_base_elements),
            they're reused instead of being recomputed. If 'vector_lines'
            is present but 'closed_rects' isn't, it's computed here from
            the cached lines. If neither is present, num_vector_cross is 0
            and same_rect_member is 0 for every edge (shape stays
            consistent; only get_edge_dim's dummy-data probing relies on
            this graceful fallback).

    Returns:
        (E, 21) array: 18 relation features + [log1p(num_bbox_cross),
        log1p(num_vector_cross), same_rect_member].
    """
    base = get_edge_transform_bbox(bboxes, edge_index)
    E = len(edge_index)
    if E == 0:
        return np.concatenate([base, np.empty((0, 3), dtype=np.float32)], axis=1)

    bboxes_arr = np.asarray(bboxes, dtype=np.float64)
    centers_x = (bboxes_arr[:, 0] + bboxes_arr[:, 2]) / 2.0
    centers_y = (bboxes_arr[:, 1] + bboxes_arr[:, 3]) / 2.0
    all_x1, all_y1, all_x2, all_y2 = (bboxes_arr[:, 0], bboxes_arr[:, 1],
                                      bboxes_arr[:, 2], bboxes_arr[:, 3])
    N = len(bboxes_arr)

    vec_rects = None
    closed_rects = None
    if data_dict is not None:
        closed_rects = data_dict.get('closed_rects')
        vector_lines = data_dict.get('vector_lines')
        if vector_lines is not None:
            h_lines, v_lines = vector_lines
            all_vec = list(h_lines) + list(v_lines)
            if all_vec:
                vec_rects = (
                    np.array([r.x0 for r in all_vec]),
                    np.array([r.y0 for r in all_vec]),
                    np.array([r.x1 for r in all_vec]),
                    np.array([r.y1 for r in all_vec]),
                )
            if closed_rects is None:
                closed_rects = find_closed_border_rects(h_lines, v_lines)

    # Per-node rect membership, computed once (not per edge).
    rect_ids = None
    if closed_rects:
        rect_ids = np.array([get_rect_member_id(b, closed_rects) for b in bboxes_arr])

    num_bbox_cross = np.zeros(E, dtype=np.float32)
    num_vector_cross = np.zeros(E, dtype=np.float32)
    same_rect_member = np.zeros(E, dtype=np.float32)
    self_exclude_base = np.ones(N, dtype=bool)

    for e_idx, (i, j) in enumerate(edge_index):
        x0, y0 = centers_x[i], centers_y[i]
        x1, y1 = centers_x[j], centers_y[j]

        exclude = self_exclude_base.copy()
        exclude[i] = False
        exclude[j] = False

        hit = _segment_rect_intersect_mask(x0, y0, x1, y1, all_x1, all_y1, all_x2, all_y2)
        num_bbox_cross[e_idx] = np.count_nonzero(hit & exclude)

        if vec_rects is not None:
            vx1, vy1, vx2, vy2 = vec_rects
            vhit = _segment_rect_intersect_mask(x0, y0, x1, y1, vx1, vy1, vx2, vy2)
            num_vector_cross[e_idx] = np.count_nonzero(vhit)

        if rect_ids is not None and rect_ids[i] != -1 and rect_ids[i] == rect_ids[j]:
            same_rect_member[e_idx] = 1.0

    extra = np.stack(
        [np.log1p(num_bbox_cross), np.log1p(num_vector_cross), same_rect_member],
        axis=1,
    ).astype(np.float32)
    return np.concatenate([base, extra], axis=1)


def get_edge_attr(bboxes, edge_index, edge_type='', data_dict=None, page_img=None):
    """
    Compute edge attributes based on edge type.

    Args:
        bboxes: np.ndarray of shape (N, 4), float32
        edge_index: list of (i, j) tuples
        edge_type: str — '', 'SEO', 'PRS', 'YF', etc.
        page_img: page image array (required for 'PRS')

    Returns:
        edge_attr: np.ndarray of shape (E, D)
    """
    if edge_type == 'SEO':
        return get_edge_transform_bbox_add_alignment(bboxes, edge_index)

    elif edge_type == 'YF':
        return get_edge_transform_yf(bboxes, edge_index, data_dict=data_dict)

    elif edge_type == 'PRS':
        from .presidio.graph import compute_edge_features
        page_h, page_w, _ = page_img.shape
        temp_edge_idx = np.array(edge_index).T
        return compute_edge_features(node_bboxes=bboxes, edge_index=temp_edge_idx,
                                     page_width=page_w, page_height=page_h)

    else:
        return get_edge_transform_bbox(bboxes, edge_index)


def get_edge_dim(edge_type='', page_img=None):
    """
    Get edge attribute dimension by computing on dummy data.
    Used for single-node edge case.

    Args:
        edge_type: str
        page_img: page image array (required for 'PRS')

    Returns:
        int: edge feature dimension
    """
    dummy_bboxes = np.array([
        [0.0, 0.0, 10.0, 10.0],
        [20.0, 20.0, 30.0, 30.0]
    ], dtype=np.float32)
    dummy_edge_index = [(0, 1), (1, 0)]
    dummy_attr = get_edge_attr(dummy_bboxes, dummy_edge_index, edge_type, page_img=page_img)
    return dummy_attr.shape[1]


def build_edge_index(bboxes, edge_sampling='4D'):
    """
    Build edge index from bboxes.

    Args:
        bboxes: np.ndarray of shape (N, 4)
        edge_sampling: '4D' (directional NN) or '4D+AL' (directional NN + alignment)

    Returns:
        edge_index: list of (i, j) tuples
    """
    if edge_sampling == '4D+AL':
        edge_index1, _ = get_edge_by_directional_nn(bboxes, 50000, vertical_gap=0.3)
        edge_index2 = get_edge_by_alignment(bboxes, dist_threshold=0)
        edge_index = sorted(set(edge_index1 + edge_index2))
    else:
        edge_index, _ = get_edge_by_directional_nn(bboxes, 50000, vertical_gap=0.3)
    return edge_index


def compute_edge_union_bboxes(edge_index, original_bboxes):
    """
    Compute the union bbox of each edge's two endpoint node bboxes.

    NOTE: for image-edge features specifically, prefer
    compute_edge_gap_bboxes() instead -- see its docstring for why a plain
    union tends to just re-pool each node's own visual content rather than
    capturing what's actually between the two nodes. This function is kept
    as a general "bounding box of two boxes" utility.

    Args:
        edge_index: np.ndarray of shape (2, E) or any (row, col) pair of
            equal-length sequences of node indices.
        original_bboxes: list of [x1, y1, x2, y2], indexed by node.

    Returns:
        list of [x1, y1, x2, y2], one per edge.
    """
    edge_bboxes = []
    row, col = edge_index
    for node_idx_1, node_idx_2 in zip(row, col):
        bbox1 = original_bboxes[node_idx_1]
        bbox2 = original_bboxes[node_idx_2]
        x1 = min(bbox1[0], bbox2[0])
        y1 = min(bbox1[1], bbox2[1])
        x2 = max(bbox1[2], bbox2[2])
        y2 = max(bbox1[3], bbox2[3])
        edge_bboxes.append([x1, y1, x2, y2])
    return edge_bboxes


def compute_edge_gap_bboxes(edge_index, original_bboxes):
    """
    Compute the "corridor" rectangle between each edge's two endpoint node
    bboxes -- the space between them, excluding both nodes' own areas --
    rather than the union (which mostly just re-covers each node's own
    content for adjacent neighbors, diluting whatever visual signal
    actually sits in the gap: a ruling line, whitespace, another element).

    For two boxes A, B:
      - On the axis where they're separated (no overlap), the gap uses
        the actual space BETWEEN them on that axis (excludes both boxes).
      - On the perpendicular axis, the gap uses the INTERSECTION of A and
        B's extents on that axis (only the band both boxes actually
        occupy), not the union (which would include the part of one box
        that has no counterpart in the other).
      - If A and B are separated on BOTH axes (diagonal neighbors), the
        gap is the small rectangle between their facing corners.
      - If A and B overlap (no separating axis on either side -- rare for
        PDF-parser-derived text bboxes, but possible e.g. when a chart or
        image bbox contains a text bbox), there's no meaningful "between"
        region, so this falls back to the union -- an intersection here
        would lose the very context (the smaller box) that an edge to it
        is meant to capture.

    Args:
        edge_index: np.ndarray of shape (2, E) or any (row, col) pair of
            equal-length sequences of node indices.
        original_bboxes: list of [x1, y1, x2, y2], indexed by node.

    Returns:
        list of [x1, y1, x2, y2], one per edge.
    """
    edge_bboxes = []
    row, col = edge_index
    for node_idx_1, node_idx_2 in zip(row, col):
        ax1, ay1, ax2, ay2 = original_bboxes[node_idx_1]
        bx1, by1, bx2, by2 = original_bboxes[node_idx_2]

        if ax2 <= bx1:
            gx0, gx1 = ax2, bx1
        elif bx2 <= ax1:
            gx0, gx1 = bx2, ax1
        else:
            gx0, gx1 = None, None

        if ay2 <= by1:
            gy0, gy1 = ay2, by1
        elif by2 <= ay1:
            gy0, gy1 = by2, ay1
        else:
            gy0, gy1 = None, None

        if gx0 is not None and gy0 is not None:
            # Diagonal neighbors: small rect between the facing corners.
            edge_bboxes.append([gx0, gy0, gx1, gy1])
        elif gx0 is not None:
            # Horizontal neighbors: x is the gap; y is the band both boxes
            # actually occupy (guaranteed non-empty -- gy0 is None means
            # the y-ranges do overlap, that's precisely why it's None).
            edge_bboxes.append([gx0, max(ay1, by1), gx1, min(ay2, by2)])
        elif gy0 is not None:
            # Vertical neighbors: y is the gap; x is the shared band.
            edge_bboxes.append([max(ax1, bx1), gy0, min(ax2, bx2), gy1])
        else:
            # A and B overlap -- no "between" region exists; union preserves
            # context instead of discarding it via a (possibly empty or
            # misleading) intersection.
            edge_bboxes.append([min(ax1, bx1), min(ay1, by1), max(ax2, bx2), max(ay2, by2)])

    return edge_bboxes


def append_image_edge_features(edge_attr, edge_index, original_bboxes,
                                feature_map, class_logits, page_w, page_h,
                                feature_map_pooling_ops=DEFAULT_FEATURE_MAP_POOLING_OPS,
                                class_logits_pooling_ops=DEFAULT_CLASS_LOGITS_POOLING_OPS):
    """
    Append ROI-pooled image features to edge attributes.

    Pools feature_map (decoder embedding) and class_logits (per-class scores)
    SEPARATELY, using the same scheme as node-level image features
    (see BoxRFDGNN.get_nn_input_from_datadict), then concatenates both onto
    edge_attr. class_logits is always softmaxed before pooling since its
    entropy/margin ops are only meaningful over a probability distribution.

    This is a standalone, single-shot entry point: it builds its own
    softmax/SAT tables via extract_bbox_features_by_roi_pooling() every call.
    If you are ALSO pooling the same feature_map/class_logits for node
    bboxes in the same request (as BoxRFDGNN does), prefer building a
    RoiPoolingSession per tensor and calling .query() for both node and
    edge bboxes instead -- that shares the bbox-independent softmax/SAT
    setup between the two queries rather than rebuilding it here. See
    roi_pooling.RoiPoolingSession and BoxRFDGNN.get_nn_input_from_datadict.

    Args:
        edge_attr: existing edge attributes, shape (E, D)
        edge_index: np.ndarray of shape (2, E)
        original_bboxes: list of [x1, y1, x2, y2]
        feature_map: decoder embedding output, shape (1, 5*F, H, W)
        class_logits: per-class segmentation logits, shape (1, C, H, W)
        page_w, page_h: page dimensions
        feature_map_pooling_ops: pooling_ops applied to feature_map
        class_logits_pooling_ops: pooling_ops applied to class_logits

    Returns:
        edge_attr: np.ndarray of shape (E, D + D_img)
    """
    edge_bboxes = compute_edge_gap_bboxes(edge_index, original_bboxes)

    feat_pooled = extract_bbox_features_by_roi_pooling(
        feature_map, edge_bboxes, page_w, page_h,
        pooling_ops=feature_map_pooling_ops,
    )
    logit_pooled = extract_bbox_features_by_roi_pooling(
        class_logits, edge_bboxes, page_w, page_h,
        pooling_ops=class_logits_pooling_ops,
        apply_softmax=True,
    )
    edge_image_features = np.concatenate([feat_pooled, logit_pooled], axis=1)
    return np.concatenate([edge_attr, edge_image_features], axis=1)
