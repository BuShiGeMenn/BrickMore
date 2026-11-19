"""
Youngmin's Features (YF) extraction
Maintained by: AI Researchers
Purpose: Spatial feature maps from PDF page layout analysis

No OpenCV dependency: ruling-line detection uses PyMuPDF's own vector
drawing objects (get_vector_lines/merge_lines, PDF-native) instead of
Sobel/morphology on a rasterized page image, and per-channel diffusion
(previously done via cv2.GaussianBlur with a hand-picked kernel per channel)
is superseded by apply_multiscale_pyramid()'s FPN-style multi-scale
concatenation, which diffuses every channel uniformly via nearest-neighbor
downsample+upsample rather than a per-channel-tuned blur radius.
"""

import re
import math
import numpy as np
from collections import Counter, defaultdict

from .pymupdf_util_base import get_vector_lines, merge_lines
from .roi_pooling import extract_bbox_features_by_roi_pooling

DEFAULT_PYRAMID_SCALES = (0.5, 0.25, 0.125)


def get_centered_feature(val, mode_val):
    """
    Log-sigmoid normalization of val relative to a page-derived baseline
    (mode_val): returns 0.5 when val == mode_val, approaching 1 as val
    grows much larger than the baseline and 0 as it shrinks much smaller.
    Used in YF for font_distance and width/height_diff_distance.
    NOTE: margin_l/r/t/b, vector_margin_l/r/t/b, column_degree, and
    line_indent_degree deliberately do NOT go through this anymore. Page-
    local mode/boundary baselines were unstable on sparse pages, so they
    instead go through suppress_extremes() below, which caps outliers using
    a FIXED corpus-wide constant rather than a per-page mode.
    """
    if mode_val <= 0:
        return 0.5
    safe_val = max(val, 0.001)
    ratio = safe_val / mode_val
    diff_log = math.log2(ratio)
    return 1.0 / (1.0 + math.exp(-diff_log))


# Fixed, corpus-wide scale constants for suppress_extremes() below.
# These are NOT recomputed per page/document -- that per-page recomputation
# is exactly what made get_centered_feature's mode_val unstable on sparse
# pages. Pick each value once from an offline pass over the training corpus
# (e.g. median or ~90th percentile of the raw channel) and hardcode it here.
# training -- current numbers are reasonable order-of-magnitude guesses only.
MARGIN_SUPPRESS_SCALE = 100.0          # raw margin_l/r/t/b unit: PDF points
VECTOR_MARGIN_SUPPRESS_SCALE = 50.0    # raw vector_margin_* unit: canvas px (canvas is fixed 300x300)
COLUMN_DEGREE_SUPPRESS_SCALE = 5.0     # raw column_degree unit: column index (1, 2, 3, ...)
INDENT_SUPPRESS_SCALE_PDF = 100.0      # raw line_indent_degree (create_pdf_information path), unit: PDF points
INDENT_SUPPRESS_SCALE_CANVAS = 50.0    # raw line_indent_degree (create_feature_map recompute path), unit: canvas px


def suppress_extremes(val, scale, mode='log1p'):
    """
    Suppress large/outlier values with a FIXED (page-independent) squashing
    function -- the middle ground between raw unbounded values and
    get_centered_feature's page-local mode normalization.

    Unlike get_centered_feature, `scale` here must be a constant decided
    once from corpus-wide statistics, never recomputed per page/document.
    Recomputing it per page reintroduces the exact instability (noisy
    reference on sparse pages) that motivated removing get_centered_feature
    from margin_l/r/t/b, vector_margin_l/r/t/b, column_degree, and
    line_indent_degree in the first place.

    mode='log1p' (default): log1p(val / scale). Unbounded but grows very
        slowly past `scale` -- never fully saturates, so two very large
        values (e.g. two different isolated-line sentinel gaps) still end
        up numerically distinguishable, just compressed. Safest default.
    mode='tanh': tanh(val / scale). Hard-bounded to [0, 1). Fully saturates
        for val >> scale, so very large values collapse to ~1 and become
        indistinguishable from each other -- same saturating behavior as
        the removed get_centered_feature, but referenced to a fixed
        constant instead of a per-page mode.
    mode='clip': min(val, scale). Simplest possible cap -- linear/raw below
        `scale`, hard-clipped above it. Easiest to reason about but throws
        away all information above the cap.
    """
    safe_val = max(val, 0.0)
    if mode == 'log1p':
        return math.log1p(safe_val / scale)
    elif mode == 'tanh':
        return math.tanh(safe_val / scale)
    elif mode == 'clip':
        return min(safe_val, scale)
    else:
        raise ValueError(f'unknown suppress_extremes mode: {mode}')

def _compute_directional_margins(all_raw_data, page_width, page_height,
                                 vertical_gap=0.3, horizontal_gap=0.3):
    """
    Compute per-line margin_l/r/t/b: the gap to the nearest neighboring line
    in each direction (not the distance to the physical page edge).

    Row/column band tolerance mirrors get_edge_by_directional_nn's
    vertical_gap convention: a candidate neighbor for left/right search must
    have its center_y within the line's own height * vertical_gap of the
    line's y-range (and symmetrically, center_x within width * horizontal_gap
    for top/bottom search).

    When no neighbor is found in a direction, the raw gap is set to the
    page dimension (page_width for l/r, page_height for t/b) as a sentinel --
    NOT the line's actual distance to the physical page edge. This is
    deliberate: "no neighbor in this direction" is the meaningful signal
    (isolation), and using the page dimension guarantees a large, distinct
    raw value regardless of where the line happens to physically sit on
    the page. NOTE: this raw value is emitted as-is now (no page-mode
    normalization -- see get_centered_feature docstring).

    Known perf note: O(L^2) via per-line masking, matching the existing
    style of v_l/v_r counting in this module. Left as a follow-up
    optimization item, consistent with prior review of this file.

    Returns:
        raw_l, raw_r, raw_t, raw_b: np.ndarray (L,) raw gap values
        found_l, found_r, found_t, found_b: np.ndarray (L,) bool, True where
            an actual neighbor was found (i.e. the value is NOT the sentinel)
    """
    n = len(all_raw_data)
    xs1 = np.array([l['bbox'][0] for l, f in all_raw_data])
    ys1 = np.array([l['bbox'][1] for l, f in all_raw_data])
    xs2 = np.array([l['bbox'][2] for l, f in all_raw_data])
    ys2 = np.array([l['bbox'][3] for l, f in all_raw_data])
    heights = ys2 - ys1
    widths = xs2 - xs1
    cy = (ys1 + ys2) / 2.0
    cx = (xs1 + xs2) / 2.0

    raw_l = np.full(n, page_width, dtype=np.float64)
    raw_r = np.full(n, page_width, dtype=np.float64)
    raw_t = np.full(n, page_height, dtype=np.float64)
    raw_b = np.full(n, page_height, dtype=np.float64)
    found_l = np.zeros(n, dtype=bool)
    found_r = np.zeros(n, dtype=bool)
    found_t = np.zeros(n, dtype=bool)
    found_b = np.zeros(n, dtype=bool)

    for i in range(n):
        h_i = heights[i]
        row_band = (cy >= ys1[i] - h_i * vertical_gap) & (cy <= ys2[i] + h_i * vertical_gap)
        row_band[i] = False

        left_mask = row_band & (xs2 <= xs1[i])
        if np.any(left_mask):
            raw_l[i] = xs1[i] - xs2[left_mask].max()
            found_l[i] = True

        right_mask = row_band & (xs1 >= xs2[i])
        if np.any(right_mask):
            raw_r[i] = xs1[right_mask].min() - xs2[i]
            found_r[i] = True

        w_i = widths[i]
        col_band = (cx >= xs1[i] - w_i * horizontal_gap) & (cx <= xs2[i] + w_i * horizontal_gap)
        col_band[i] = False

        top_mask = col_band & (ys2 <= ys1[i])
        if np.any(top_mask):
            raw_t[i] = ys1[i] - ys2[top_mask].max()
            found_t[i] = True

        bottom_mask = col_band & (ys1 >= ys2[i])
        if np.any(bottom_mask):
            raw_b[i] = ys1[bottom_mask].min() - ys2[i]
            found_b[i] = True

    return raw_l, raw_r, raw_t, raw_b, found_l, found_r, found_t, found_b


def _compute_vector_margins(bboxes, h_lines_scaled, v_lines_scaled, canvas_w, canvas_h, tolerance=3):
    """
    Per-bbox gap to the nearest vector line in each direction (all
    coordinates already in feature-map canvas space):
      vector_margin_l/r: nearest VERTICAL line whose y-range overlaps the
          bbox's y-range (+/- tolerance), to the left/right.
      vector_margin_t/b: nearest HORIZONTAL line whose x-range overlaps the
          bbox's x-range (+/- tolerance), above/below.

    Same sentinel convention as _compute_directional_margins: no matching
    line in a direction -> raw gap = canvas_w (l/r) or canvas_h (t/b), a
    clean, deterministic extreme value rather than an arbitrary small
    distance-to-page-edge value. NOTE: this raw value is emitted as-is now
    (no page-mode normalization -- see get_centered_feature docstring).

    Args:
        bboxes: list of [x1, y1, x2, y2], canvas-scaled.
        h_lines_scaled, v_lines_scaled: list of (x0, y0, x1, y1) tuples,
            canvas-scaled (h_lines are ~zero-height, v_lines ~zero-width).

    Returns:
        raw_l, raw_r, raw_t, raw_b, found_l, found_r, found_t, found_b
        (each an np.ndarray of length len(bboxes)).
    """
    n = len(bboxes)
    bx1 = np.array([b[0] for b in bboxes], dtype=np.float64)
    by1 = np.array([b[1] for b in bboxes], dtype=np.float64)
    bx2 = np.array([b[2] for b in bboxes], dtype=np.float64)
    by2 = np.array([b[3] for b in bboxes], dtype=np.float64)

    raw_l = np.full(n, canvas_w, dtype=np.float64)
    raw_r = np.full(n, canvas_w, dtype=np.float64)
    raw_t = np.full(n, canvas_h, dtype=np.float64)
    raw_b = np.full(n, canvas_h, dtype=np.float64)
    found_l = np.zeros(n, dtype=bool)
    found_r = np.zeros(n, dtype=bool)
    found_t = np.zeros(n, dtype=bool)
    found_b = np.zeros(n, dtype=bool)

    if v_lines_scaled:
        vx = np.array([(r[0] + r[2]) / 2.0 for r in v_lines_scaled])
        vy0 = np.array([r[1] for r in v_lines_scaled])
        vy1 = np.array([r[3] for r in v_lines_scaled])
        for i in range(n):
            y_overlap = (vy1 >= by1[i] - tolerance) & (vy0 <= by2[i] + tolerance)
            left_mask = y_overlap & (vx <= bx1[i])
            if np.any(left_mask):
                raw_l[i] = bx1[i] - vx[left_mask].max()
                found_l[i] = True
            right_mask = y_overlap & (vx >= bx2[i])
            if np.any(right_mask):
                raw_r[i] = vx[right_mask].min() - bx2[i]
                found_r[i] = True

    if h_lines_scaled:
        hy = np.array([(r[1] + r[3]) / 2.0 for r in h_lines_scaled])
        hx0 = np.array([r[0] for r in h_lines_scaled])
        hx1 = np.array([r[2] for r in h_lines_scaled])
        for i in range(n):
            x_overlap = (hx1 >= bx1[i] - tolerance) & (hx0 <= bx2[i] + tolerance)
            top_mask = x_overlap & (hy <= by1[i])
            if np.any(top_mask):
                raw_t[i] = by1[i] - hy[top_mask].max()
                found_t[i] = True
            bottom_mask = x_overlap & (hy >= by2[i])
            if np.any(bottom_mask):
                raw_b[i] = hy[bottom_mask].min() - by2[i]
                found_b[i] = True

    return raw_l, raw_r, raw_t, raw_b, found_l, found_r, found_t, found_b


def create_pdf_information(page_dict):
    """Create statistical and structural information from PDF page for YF features."""
    info_list = []
    tolerance = 3.0
    width_threshold_ratio = 0.25
    num_threshold_ratio = 0.2
    page_width = page_dict['width']
    page_height = page_dict['height']
    list_prefix_pattern = re.compile(r'^(\d+[\.\)]|\(\d+\)|[a-zA-Z][\.\)]|\([a-zA-Z]\)|[-■●])')

    all_raw_data = []
    x1_coords, y1_coords = [], []
    widths, heights = [], []
    font_counts = Counter()

    seen_bboxes = set()
    for block in page_dict["blocks"]:
        if block["type"] != 0: continue
        for line in block["lines"]:
            x1, y1, x2, y2 = line['bbox']

            bbox_key = (int(x1), int(y1), int(x2), int(y2))
            if bbox_key in seen_bboxes:
                continue
            seen_bboxes.add(bbox_key)

            w, h = round(x2 - x1, 1), round(y2 - y1, 1)

            full_text = " ".join([span['text'] for span in line['spans']])
            clean_text = "".join(full_text.split())
            text_len = len(clean_text)

            if text_len > 0:
                num_count = len(re.findall(r'\d', clean_text))
                current_num_ratio = num_count / text_len

                is_noise_for_mode = (current_num_ratio > 0.8) or (current_num_ratio < 0.2 and text_len <= 3)

                if not is_noise_for_mode:
                    widths.append(w)
                    heights.append(h)

            x1_coords.append(x1)
            y1_coords.append(y1)
            if line['spans']:
                font_counts[line['spans'][0]['font']] += 1
                all_raw_data.append((line, line['spans'][0]['font']))

    # Global baseline setup
    indent_baseline = Counter([round(x / tolerance) * tolerance for x in x1_coords]).most_common(1)[0][
        0] if x1_coords else 0
    mode_w = Counter(widths).most_common(1)[0][0] if widths else 1.0
    mode_h = Counter(heights).most_common(1)[0][0] if heights else 1.0
    sorted_fonts = [f[0] for f in font_counts.most_common()]
    font_to_rank = {font: i for i, font in enumerate(sorted_fonts)}
    max_font_rank = len(sorted_fonts) - 1

    # margin_l/r/t/b: gap to nearest neighboring line in each direction (not
    # distance to the physical page edge -- see _compute_directional_margins).
    # Kept as 4 independent channels/baselines (not merged into shared
    # horizontal/vertical baselines), since l/r gaps reflect column spacing
    # while t/b gaps reflect line spacing -- different statistical character.
    (raw_margin_l, raw_margin_r, raw_margin_t, raw_margin_b,
     found_l, found_r, found_t, found_b) = _compute_directional_margins(
        all_raw_data, page_width, page_height)

    # NOTE: page-local mode_margin_l/r/t/b baseline removed on purpose.
    # margin_l/r/t/b now pass through as raw gap distances (page coordinate
    # units) instead of get_centered_feature(raw, page_mode). Scale
    # normalization across the corpus is left to the downstream batch norm
    # layer, avoiding the per-page mode instability discussed in review
    # (mode computed from very few lines on short/sparse pages).

    def count_within_tolerance(target, coord_list, tol):
        return sum(1 for c in coord_list if abs(c - target) <= tol)

    # Row Context Pre-Analysis
    y_groups = defaultdict(list)
    for line, font in all_raw_data:
        y1 = line['bbox'][1]
        found = False
        for ref_y in y_groups.keys():
            if abs(ref_y - y1) <= tolerance:
                y_groups[ref_y].append(line)
                found = True
                break
        if not found: y_groups[y1].append(line)

    # Feature Calculation
    for line_idx, (line, font) in enumerate(all_raw_data):
        x1, y1, x2, y2 = line['bbox']
        w, h = x2 - x1, y2 - y1
        full_text = " ".join([span['text'] for span in line['spans']])
        clean_text = "".join(full_text.split())
        len_full, len_clean = len(full_text), len(clean_text)

        num_ratio = len(re.findall(r'\d', clean_text)) / len_clean if len_clean > 0 else 0.0
        ws_ratio = ((len_full - len_clean) / len_full) * 2 if len_full > 0 else 0.0
        is_list = list_prefix_pattern.match(full_text.strip())

        row_items = next(items for ref_y, items in y_groups.items() if abs(ref_y - y1) <= tolerance)
        row_count = len(row_items)
        has_strong_anchor = any(len(re.findall(r'\d', "".join(" ".join([s['text'] for s in l['spans']]).split()))) /
                                max(1, len("".join(" ".join([s['text'] for s in l['spans']]).split()))) > 0.8
                                for l in row_items)

        is_grid_candidate = 1.0 if (
                (w / page_width) <= width_threshold_ratio and not is_list and
                (num_ratio >= num_threshold_ratio or (row_count >= 3 and has_strong_anchor))
        ) else 0.0

        h_grid_density = min((row_count - 1) * 0.33 * is_grid_candidate * (1 - ws_ratio) * num_ratio,
                             1.0) if row_count >= 2 else 0.0

        v_l = count_within_tolerance(x1, [l['bbox'][0] for l, f in all_raw_data], tolerance)
        v_r = count_within_tolerance(x2, [l['bbox'][2] for l, f in all_raw_data], tolerance)
        v_grid_density = min((max(v_l, v_r) / 5.0) * is_grid_candidate * (1 - ws_ratio) * num_ratio, 1.0) if max(v_l,
                                                                                                                 v_r) >= 3 else 0.0

        text_density = 1 - num_ratio

        w_diff_distance = get_centered_feature(w, mode_w)
        h_diff_distance = get_centered_feature(h, mode_h)

        # Fixed-scale suppression, no page-relative normalization (see
        # suppress_extremes docstring above).
        margin_l = suppress_extremes(raw_margin_l[line_idx], MARGIN_SUPPRESS_SCALE)
        margin_r = suppress_extremes(raw_margin_r[line_idx], MARGIN_SUPPRESS_SCALE)
        margin_t = suppress_extremes(raw_margin_t[line_idx], MARGIN_SUPPRESS_SCALE)
        margin_b = suppress_extremes(raw_margin_b[line_idx], MARGIN_SUPPRESS_SCALE)

        # Explicit isolation signal: 1.0 if an actual neighboring line was
        # found in this direction, 0.0 if margin_* is the sentinel (no
        # neighbor at all). Kept separate from margin_* itself because
        # suppress_extremes() compresses large sentinel values, which can
        # blur the "isolated" signal into "just a somewhat large gap" --
        # see discussion on why this shouldn't be inferred from margin_*
        # alone.
        margin_l_found = 1.0 if found_l[line_idx] else 0.0
        margin_r_found = 1.0 if found_r[line_idx] else 0.0
        margin_t_found = 1.0 if found_t[line_idx] else 0.0
        margin_b_found = 1.0 if found_b[line_idx] else 0.0

        symbols_count = sum(1 for char in clean_text if not char.isalnum() and char not in [',', '.'])
        sym_ratio = symbols_count / len(full_text)

        info_list.append({
            'bbox': [x1, y1, x2, y2],
            'text': [span['text'] for span in line['spans']],
            'num_ratio': num_ratio,
            'sym_ratio': sym_ratio,
            'start_list_prefix': 1.0 if is_list else 0.0,
            'font_distance': font_to_rank[font] / max_font_rank if max_font_rank > 0 else 0.0,
            'horizontal_grid_density': h_grid_density,
            'vertical_grid_density': v_grid_density,
            'width_diff_distance': w_diff_distance,
            'height_diff_distance': h_diff_distance,
            'margin_l': margin_l,
            'margin_r': margin_r,
            'margin_t': margin_t,
            'margin_b': margin_b,
            'margin_l_found': margin_l_found,
            'margin_r_found': margin_r_found,
            'margin_t_found': margin_t_found,
            'margin_b_found': margin_b_found,
            'whitespace_ratio': ws_ratio,
            # Fixed-scale suppression, no page_width normalization (see
            # suppress_extremes docstring above).
            'line_indent_degree': suppress_extremes(
                abs(x1 - indent_baseline), INDENT_SUPPRESS_SCALE_PDF),
            'text_density': text_density
        })

    return info_list


def create_feature_map(page_img, page, fet_names, info_list, fmap_width=300, fmap_height=300,
                       vector_lines=None):
    """Create multi-channel spatial feature map for YF features.

    Args:
        vector_lines: optional pre-computed (h_lines, v_lines) tuple (as
            returned by get_vector_lines()+merge_lines()), e.g. cached in
            data_dict['vector_lines'] by pymupdf_util_base.extract_base_elements
            when 'vec_line' was in input_type. Passing this avoids
            re-parsing page.get_drawings() and re-rasterizing
            page.get_pixmap() (needed internally by get_vector_lines just to
            sample a background color) a second time for the same page. If
            not given, computed here as before.
    """
    original_h, original_w = page_img.shape[0], page_img.shape[1]

    scale_w = fmap_width / original_w
    scale_h = fmap_height / original_h

    info_list_scaled = []
    for info in info_list:
        info_scaled = info.copy()
        bbox = info['bbox']
        info_scaled['bbox'] = [
            bbox[0] * scale_w,
            bbox[1] * scale_h,
            bbox[2] * scale_w,
            bbox[3] * scale_h
        ]
        info_list_scaled.append(info_scaled)

    page_h, page_w = fmap_height, fmap_width
    num_channels = len(fet_names)
    feature_map = np.zeros((num_channels, page_h, page_w), dtype=np.float32)

    NON_ACCUMULATIVE_FEATURES = {
        'start_list_prefix', 'font_distance', 'width_diff_distance',
        'height_diff_distance', 'line_indent_degree', 'num_ratio',
        'margin_l', 'margin_r', 'margin_t', 'margin_b',
        'margin_l_found', 'margin_r_found', 'margin_t_found', 'margin_b_found',
        'vector_margin_l', 'vector_margin_r', 'vector_margin_t', 'vector_margin_b',
    }

    ACCUMULATIVE_FEATURES = {
        'horizontal_grid_density', 'vertical_grid_density',
        'text_density', 'image_density'
    }

    if 'image_density' in fet_names:
        idx = fet_names.index('image_density')
        img_bboxes = [itm["bbox"] for itm in page.get_image_info()]
        for rect in img_bboxes:
            x1 = int(rect[0] * scale_w)
            y1 = int(rect[1] * scale_h)
            x2 = int(rect[2] * scale_w)
            y2 = int(rect[3] * scale_h)

            x1, x2 = max(0, x1), min(page_w, x2)
            y1, y2 = max(0, y1), min(page_h, y2)

            min_size = int(20 * min(scale_w, scale_h))
            if (x2 - x1) >= min_size and (y2 - y1) >= min_size:
                feature_map[idx, y1:y2, x1:x2] = 1.0
        # No blur here: diffusion is provided downstream by
        # apply_multiscale_pyramid(), applied uniformly across all channels.

    if any(n in fet_names for n in ('vector_margin_l', 'vector_margin_r', 'vector_margin_t', 'vector_margin_b')):
        # PDF-native ruling line detection: read PyMuPDF's actual vector
        # drawing objects instead of running edge detection (Sobel +
        # morphological opening) on the rasterized page image. Real ruling
        # lines are almost always drawn as PDF vector paths, so this is both
        # more accurate and removes the OpenCV dependency entirely.
        #
        # These four channels replaced horizontal/vertical_line_diffusion:
        # a binary "there's a line somewhere near here" field turned out not
        # to be useful once diffusion moved to apply_multiscale_pyramid (no
        # per-channel blur left to give it directional falloff), and it
        # never encoded *which side* the line was on anyway. vector_margin_*
        # gives an actual per-direction gap instead -- the same
        # nearest-neighbor-gap pattern as margin_l/r/t/b, but measured
        # against vector lines instead of neighboring text lines. This lets
        # e.g. a table-cell-enclosed bbox (small gap in all 4 directions)
        # read differently from one sitting between two horizontal rules
        # with open left/right sides (small gap top/bottom, sentinel/large
        # gap left/right).
        h_lines, v_lines = vector_lines if vector_lines is not None else get_vector_lines(page, omit_invisible=True)
        if vector_lines is None:
            h_lines = merge_lines(h_lines, orientation='h', tolerance=3)
            v_lines = merge_lines(v_lines, orientation='v', tolerance=3)

        h_lines_scaled = [(r.x0 * scale_w, r.y0 * scale_h, r.x1 * scale_w, r.y1 * scale_h) for r in h_lines]
        v_lines_scaled = [(r.x0 * scale_w, r.y0 * scale_h, r.x1 * scale_w, r.y1 * scale_h) for r in v_lines]

        vm_bboxes = [info['bbox'] for info in info_list_scaled]
        (vm_raw_l, vm_raw_r, vm_raw_t, vm_raw_b,
         vm_found_l, vm_found_r, vm_found_t, vm_found_b) = _compute_vector_margins(
            vm_bboxes, h_lines_scaled, v_lines_scaled, page_w, page_h)

        # NOTE: page-local vm_mode_l/r/t/b baseline removed on purpose, same
        # reasoning as margin_l/r/t/b above -- vector_margin_* now goes
        # through suppress_extremes() (fixed canvas-unit scale) instead of
        # get_centered_feature(raw, page_mode).
        vm_channel_data = {
            'vector_margin_l': vm_raw_l,
            'vector_margin_r': vm_raw_r,
            'vector_margin_t': vm_raw_t,
            'vector_margin_b': vm_raw_b,
        }
        for name, raw_arr in vm_channel_data.items():
            if name not in fet_names:
                continue
            idx = fet_names.index(name)
            for i, info in enumerate(info_list_scaled):
                x1, y1, x2, y2 = map(int, info['bbox'])
                x1, x2 = max(0, x1), min(page_w, x2)
                y1, y2 = max(0, y1), min(page_h, y2)
                val = suppress_extremes(raw_arr[i], VECTOR_MARGIN_SUPPRESS_SCALE)
                feature_map[idx, y1:y2, x1:x2] = np.maximum(feature_map[idx, y1:y2, x1:x2], val)

    for info in info_list_scaled:
        x1, y1, x2, y2 = map(int, info['bbox'])
        x1, x2 = max(0, x1), min(page_w, x2)
        y1, y2 = max(0, y1), min(page_h, y2)

        for ch_idx, name in enumerate(fet_names):
            if name in ['column_degree', 'image_density',
                       'vector_margin_l', 'vector_margin_r', 'vector_margin_t', 'vector_margin_b']:
                continue

            val = info[name]

            if val <= 0: continue

            roi = feature_map[ch_idx, y1:y2, x1:x2]

            if name in NON_ACCUMULATIVE_FEATURES:
                roi = np.maximum(roi, val)
            elif name in ACCUMULATIVE_FEATURES:
                roi = np.clip(roi + val, 0.0, 1.0)
            else:
                roi = np.clip(roi + val, 0.0, 1.0)

            feature_map[ch_idx, y1:y2, x1:x2] = roi

    if 'column_degree' in fet_names:
        idx = fet_names.index('column_degree')
        total_bboxes = len(info_list_scaled)

        boundaries = [0]

        if total_bboxes > 0:
            filtered_coords = [round(i['bbox'][0], 0) for i in info_list_scaled if i.get('num_ratio', 0.0) <= 0.2]
            filtered_coords += [round(i['bbox'][2], 0) for i in info_list_scaled if i.get('num_ratio', 0.0) <= 0.2]

            if filtered_coords:
                coord_counts = Counter(filtered_coords)
                threshold = total_bboxes * 0.25
                found_boundaries = sorted([x for x, c in coord_counts.items() if c > threshold])
                boundaries = sorted(list(set([0] + found_boundaries)))

            extended = boundaries + [page_w]
            for i in range(len(extended) - 1):
                # Fixed-scale suppression of the raw column index, no
                # per-page cap (see suppress_extremes docstring above).
                degree_val = suppress_extremes(float(i + 1), COLUMN_DEGREE_SUPPRESS_SCALE)
                feature_map[idx, :, int(extended[i]):int(extended[i + 1])] = degree_val

            if 'line_indent_degree' in fet_names:
                li_idx = fet_names.index('line_indent_degree')
                for info in info_list_scaled:
                    x1, y1, x2, y2 = map(int, info['bbox'])

                    insert_idx = np.searchsorted(boundaries, x1 + 5.0)
                    b_idx = max(0, insert_idx - 1)
                    local_baseline = boundaries[b_idx]

                    # Fixed-scale suppression, no page_w normalization (see
                    # suppress_extremes docstring above).
                    indent_dist = abs(x1 - local_baseline)
                    line_indent_degree = suppress_extremes(indent_dist, INDENT_SUPPRESS_SCALE_CANVAS)

                    x1_f, x2_f = max(0, x1), min(page_w, x2)
                    y1_f, y2_f = max(0, y1), min(page_h, y2)
                    feature_map[li_idx, y1_f:y2_f, x1_f:x2_f] = line_indent_degree

    # No per-channel Gaussian blur here anymore: text_density,
    # vertical/horizontal_grid_density used to each get a hand-picked blur
    # kernel size to diffuse their values spatially. That per-channel kernel
    # tuning is superseded by apply_multiscale_pyramid() (called by
    # extract_yf_features), which diffuses every channel uniformly via
    # nearest-neighbor downsample+upsample at a shared set of scales,
    # leaving it to the downstream model to learn which scale matters.

    return feature_map


def _nn_resize(arr, out_h, out_w):
    """Nearest-neighbor resize of a (..., H, W) array via pure numpy indexing.
    No interpolation, no image library -- deliberately the cheapest possible
    resampling operator. Used only for the UPSAMPLE step in
    apply_multiscale_pyramid: broadcasting an already-aggregated coarse
    value back out doesn't need filtering, just a cheap repeat."""
    in_h, in_w = arr.shape[-2], arr.shape[-1]
    row_idx = (np.arange(out_h) * in_h / out_h).astype(np.intp).clip(0, in_h - 1)
    col_idx = (np.arange(out_w) * in_w / out_w).astype(np.intp).clip(0, in_w - 1)
    return arr[..., row_idx[:, None], col_idx[None, :]]


def _average_pool_resize(arr, out_h, out_w):
    """
    Area-average downsample of a (C, H, W) array to (C, out_h, out_w),
    via a summed-area table (same integral-image technique used in
    roi_pooling.py's SAT path).

    This is deliberately NOT nearest-neighbor: NN downsampling is point
    sampling, not filtering -- for a sparse/thin signal (e.g. a 1px-wide
    isolated region in an otherwise mostly-zero channel), the coarse sampling grid can
    simply miss it entirely, silently zeroing the signal out at every
    downstream scale (classic aliasing from decimating without a lowpass
    step first). Averaging over each output cell's full input footprint is
    the minimal "filter" that CNN pooling layers rely on to make a
    downsampled representation still reflect everything underneath it,
    rather than one arbitrary sample of it.

    Handles non-integer downsample ratios (e.g. 300 -> 38) by using
    fractional-but-rounded bin edges; this is an approximation (edge pixels
    can be a cell off) rather than exact sub-pixel area weighting, which is
    an acceptable simplification given feature map values are already
    smooth/near-binary indicators rather than precise imagery.
    """
    C, H, W = arr.shape
    sat = np.zeros((C, H + 1, W + 1), dtype=np.float64)
    np.cumsum(arr, axis=1, out=sat[:, 1:, 1:])
    np.cumsum(sat[:, 1:, 1:], axis=2, out=sat[:, 1:, 1:])

    row_edges = np.linspace(0, H, out_h + 1)
    col_edges = np.linspace(0, W, out_w + 1)
    r0 = np.floor(row_edges[:-1]).astype(np.intp)
    r1 = np.maximum(np.ceil(row_edges[1:]).astype(np.intp), r0 + 1).clip(0, H)
    c0 = np.floor(col_edges[:-1]).astype(np.intp)
    c1 = np.maximum(np.ceil(col_edges[1:]).astype(np.intp), c0 + 1).clip(0, W)

    out = np.empty((C, out_h, out_w), dtype=np.float32)
    for i in range(out_h):
        row_band = sat[:, r1[i], :] - sat[:, r0[i], :]  # (C, W+1)
        area_h = r1[i] - r0[i]
        for j in range(out_w):
            area = area_h * (c1[j] - c0[j])
            cell_sum = row_band[:, c1[j]] - row_band[:, c0[j]]
            out[:, i, j] = cell_sum / area
    return out


def apply_multiscale_pyramid(feature_map, scales=DEFAULT_PYRAMID_SCALES):
    """
    FPN-style multi-scale context: for each scale, downsample feature_map
    via area-averaging (a box filter -- see _average_pool_resize) then
    upsample it back to the original resolution via nearest-neighbor
    broadcast, and concatenate every scale's result -- plus the original --
    along the channel axis.

    Downsampling averages, rather than point-samples, so every output cell
    reflects everything in its input footprint -- this is what makes the
    pyramid a genuine (if very shallow) approximation of CNN pooling's
    bottom-up aggregation, rather than lossy decimation. Upsampling only
    needs to broadcast an already-aggregated value back out, so nearest-
    neighbor is sufficient and cheap there.

    This replaces the old approach of picking a hand-tuned Gaussian blur
    kernel per channel (see create_feature_map's former per-channel blur
    loop, now removed): every channel gets the identical set of scales
    here, and which scale is actually useful for which channel/class is
    left for the downstream model to learn, rather than fixed by a
    human-chosen kernel size.

    Args:
        feature_map: (C, H, W) float32
        scales: tuple of downsample factors in (0, 1), e.g. the default
            (0.5, 0.25, 0.125) for 1/2, 1/4, 1/8 resolution pyramids.

    Returns:
        (C * (1 + len(scales)), H, W) float32 -- original channels first,
        followed by each scale's upsampled-back version, in the order
        `scales` was given. Use build_pyramid_fet_names() for the matching
        channel name list.
    """
    C, H, W = feature_map.shape
    parts = [feature_map]
    for scale in scales:
        down_h = max(1, int(round(H * scale)))
        down_w = max(1, int(round(W * scale)))
        downsampled = _average_pool_resize(feature_map, down_h, down_w)
        upsampled = _nn_resize(downsampled, H, W)
        parts.append(upsampled)
    return np.concatenate(parts, axis=0)


def build_pyramid_fet_names(fet_names, scales=DEFAULT_PYRAMID_SCALES):
    """
    Expand a base channel name list to match apply_multiscale_pyramid()'s
    output channel order: original names, then each scale's names suffixed
    with '_ds{i}' (1-based index into `scales`, e.g. '_ds1' for the first
    scale given).
    """
    names = list(fet_names)
    for i in range(1, len(scales) + 1):
        names.extend(f'{n}_ds{i}' for n in fet_names)
    return names


def extract_yf_features(data_dict, page, page_dict, return_fet_map=False,
                        pyramid_scales=DEFAULT_PYRAMID_SCALES,
                        include_margin_found_flags=True):
    """
    Extract Youngmin's Features (YF) - spatial feature maps.

    Args:
        pyramid_scales: downsample factors passed to apply_multiscale_pyramid().
            Applied ONLY to the node/edge feature path below -- NOT to the
            raw feature_map returned when return_fet_map=True. That raw map
            feeds IMF's aug_fetmap channel and must keep its original,
            model-expected channel count; changing it would silently break
            any ymf-trained network's expected input shape.
        include_margin_found_flags: adds margin_l_found/r/t/b -- explicit
            binary "was an actual neighboring line found in this direction"
            channels, separate from margin_l/r/t/b's (now compressed) raw
            gap value. Default True.
            *** CHANNEL-COUNT-CHANGING FLAG ***: this adds 4 channels
            (21 -> 25 base channels, 84 -> 100 with the default pyramid).
            Any model/pipeline already trained against the old channel
            count/order -- in particular the IMF aug_fetmap path fed by
            return_fet_map=True -- MUST either be retrained or called with
            include_margin_found_flags=False to keep the old shape.
    """
    fet_names = [
        'num_ratio', 'start_list_prefix', 'font_distance', 'text_density',
        'horizontal_grid_density', 'vertical_grid_density', 'width_diff_distance',
        'whitespace_ratio', 'height_diff_distance', 'sym_ratio', 'column_degree',
        'line_indent_degree',
        'margin_l', 'margin_r', 'margin_t', 'margin_b',
        'vector_margin_l', 'vector_margin_r', 'vector_margin_t', 'vector_margin_b',
        'image_density',
    ]
    if include_margin_found_flags:
        fet_names += ['margin_l_found', 'margin_r_found', 'margin_t_found', 'margin_b_found']

    page_img = data_dict['image']
    page_h, page_w = page_img.shape[0], page_img.shape[1]

    pdf_info = create_pdf_information(page_dict)
    feature_map = create_feature_map(page_img, page, info_list=pdf_info, fet_names=fet_names,
                                     vector_lines=data_dict.get('vector_lines'))

    if return_fet_map:
        return feature_map

    pyramid_map = apply_multiscale_pyramid(feature_map, scales=pyramid_scales)
    pyramid_fet_names = build_pyramid_fet_names(fet_names, pyramid_scales)

    original_bboxes = data_dict['bboxes']
    yf_features_orig = extract_bbox_features_by_roi_pooling(
        pyramid_map[None, ...],
        original_bboxes,
        page_w,
        page_h,
        pooling_ops=('mean',),
    )

    for i, custom_feature in enumerate(data_dict['custom_features']):
        orig_vector = yf_features_orig[i]

        for f_idx, f_name in enumerate(pyramid_fet_names):
            val = float(orig_vector[f_idx])
            custom_feature['yf_' + f_name] = val

    # f_names = []
    # for i, custom_feature in enumerate(data_dict['custom_features']):
    #     for k in custom_feature.keys():
    #         if k.startswith('yf_'):
    #             f_names.append(k)
    #     break
    # f_names.sort()
    # print(f_names)

    return data_dict
