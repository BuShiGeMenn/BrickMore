"""
PDF feature extraction utilities - Orchestrator
Purpose: Coordinate feature extractors (RF, IMF, YF, JF)
         Each extractor lives in its own module for independent maintenance.
"""

from .pymupdf_util_base import make_custom_feature
from .pymupdf_util_rf import extract_rf_features
from .pymupdf_util_imf import image_feature_extraction_task
from .pymupdf_util_yf import extract_yf_features
from .pymupdf_util_jf import extract_jf_features


def _bbox_dedup_key(bbox):
    """
    Round bbox coords to integer (pixel-level) granularity for cheap,
    tolerance-aware dedup. Detected bboxes (e.g. from IMF, which rescales
    from model resolution back to page pixel space) rarely match an
    existing bbox to the exact float, so exact-equality dedup effectively
    never fires; integer rounding treats near-identical boxes as the same
    box, which is what "already detected this region" is meant to capture.
    """
    return tuple(int(round(c)) for c in bbox)


def apply_feature_extractors(data_dict, feature_set_name='rf+imf+yf',
                             input_type=('text'), feature_extractor=None, page=None, page_dict=None):
    """
    Apply experimental feature extractors to base data.

    Args:
        data_dict: Base data dictionary from extract_base_elements
        feature_set_name: String indicating which features to extract (e.g., 'rf+imf+yf')
        feature_extractor: ONNX model for image feature extraction
        page: PyMuPDF page object (required for YF features)
        page_dict: Page dictionary (required for YF features)

    Returns:
        data_dict: Enhanced with custom_features

    Raises:
        ValueError: if feature_set_name requests both 'imf' and 'ymf'. These
            are mutually exclusive image-input strategies -- 'imf' runs the
            model on the plain page image, 'ymf' runs it on the page image
            with an extra YF-derived channel appended (aug_fetmap) -- not
            features meant to be combined. Declaring both would leave
            data_dict['feature_map']/['class_logits'] ambiguous (silently
            overwritten by whichever block runs second) and would run
            inference twice for no benefit.
    """
    if 'imf' in feature_set_name and 'ymf' in feature_set_name:
        raise ValueError(
            f"feature_set_name={feature_set_name!r} requests both 'imf' and "
            "'ymf', which are mutually exclusive image-input strategies "
            "(plain image vs. YF-augmented image channel). Choose one."
        )

    # Initialize custom_features if not exists
    if 'custom_features' not in data_dict:
        _init_custom_features(data_dict)

    # Apply Image Model Features (IMF)
    # No try/except here: a failure in model inference (bad ONNX session,
    # corrupted/unexpected page image, shape mismatch, etc.) is not
    # recoverable at this level -- there is no meaningful fallback feature
    # to substitute. The caller (a data-generation loop, or BoxRFDGNN.predict
    # for serving) is in the right position to decide what to do about a
    # failed page (skip it, log it, retry, abort), so the exception is left
    # to propagate rather than being swallowed here.
    if 'imf' in feature_set_name and feature_extractor is not None:
        page_img = data_dict['image']
        feature_map, class_logits, bboxes_to_add, box_types_to_add = image_feature_extraction_task(
            page_img, feature_extractor, input_type,
        )
        data_dict['feature_map'] = feature_map
        data_dict['class_logits'] = class_logits

        # Add detected bboxes.
        # Dedup via a set of integer-rounded coords: bboxes_to_add is
        # small per page (a handful of picture detections), so the K*M
        # cost of the old list-scan wasn't the concern -- exact-float
        # equality was. Rounding makes near-identical boxes (e.g. from
        # rescaling model-resolution coords back to page pixels) collide
        # as intended, at the same O(1)-per-check cost as a set lookup.
        existing_bbox_keys = {_bbox_dedup_key(b) for b in data_dict['bboxes']}
        for bbox, type_val in zip(bboxes_to_add, box_types_to_add):
            key = _bbox_dedup_key(bbox)
            if key not in existing_bbox_keys:
                existing_bbox_keys.add(key)
                data_dict['bboxes'].append(bbox)
                data_dict['text'].append('')
                if 'box_type' in data_dict:
                    data_dict['box_type'].append(type_val)

                custom_feature = make_custom_feature(type_val, '')
                data_dict['custom_features'].append(custom_feature)

    # Apply Robin's Features (RF)
    if 'rf' in feature_set_name:
        stext_page = data_dict.get('stext_page')
        if stext_page is not None:
            extract_rf_features(data_dict, stext_page)

    # Apply Youngmin's Features (YF)
    if 'yf' in feature_set_name:
        if page is not None and page_dict is not None:
            extract_yf_features(data_dict, page, page_dict)
    elif 'ymf' in feature_set_name and feature_extractor is not None:
        # Same rationale as the 'imf' block above: no try/except, let a
        # failed inference propagate to the caller.
        yfm = extract_yf_features(data_dict, page, page_dict, return_fet_map=True)
        page_img = data_dict['image']
        feature_map, class_logits, bboxes_to_add, box_types_to_add = image_feature_extraction_task(
            page_img, feature_extractor, ('',), aug_fetmap=yfm,
        )
        data_dict['feature_map'] = feature_map
        data_dict['class_logits'] = class_logits

    # Apply JF features
    if 'jf' in feature_set_name:
        extract_jf_features(data_dict)

    return data_dict


def _init_custom_features(data_dict):
    """Initialize custom_features from box_type list."""
    data_dict['custom_features'] = []
    box_type = data_dict.get('box_type', [])

    for row_idx in range(len(data_dict['bboxes'])):
        bt = box_type[row_idx] if row_idx < len(box_type) else 'unknown'
        text = data_dict['text'][row_idx]
        data_dict['custom_features'].append(make_custom_feature(bt, text))
