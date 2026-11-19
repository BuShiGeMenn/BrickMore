"""
Image Model Features (IMF) extraction
Maintained by: AI Researchers
Purpose: Extract image-based features using neural network (ONNX)

image_feature_extraction_task() is the stable interface for pymupdf_util_ext.py.
Inference and detection logic lives in ImageFeatureExtractorV1 / V2.

feature_map / class_logits are returned SEPARATELY (not concatenated):
they have different statistical character (continuous embedding vs.
per-class score) and are meant to be pooled differently downstream -- see
roi_pooling.DEFAULT_FEATURE_MAP_POOLING_OPS / DEFAULT_CLASS_LOGITS_POOLING_OPS.
"""

from .pymupdf_util_base import BOX_IMAGE


def image_feature_extraction_task(page_img, feature_extractor, input_type, aug_fetmap=None):
    """
    Extract image-based features and segmentation-derived bboxes.

    Args:
        page_img:         np.ndarray (H, W, C), uint8 — page raster image
        feature_extractor: ImageFeatureExtractorV1 / V2 instance
        input_type:       tuple of element types; 'seg-image' enables bbox detection
        aug_fetmap:       optional extra channel map passed to predict()

    Returns:
        feature_map:      decoder embedding output, shape (1, 5*F, H, W)
        class_logits:     per-class segmentation logits, shape (1, C, H, W)
        bboxes_to_add:    list of [x1, y1, x2, y2] in page pixel space
        box_types_to_add: list of box type strings (parallel to bboxes_to_add)
    """
    # Skip inference if BoxRFDGNN.is_image_page() already ran predict() for this page.
    if not feature_extractor.consume_cache():
        feature_extractor.predict(page_img, aug_fetmap=aug_fetmap)

    feature_map = feature_extractor.get_feature_map()
    class_logits = feature_extractor.get_class_logits()
    bboxes_to_add = []
    box_types_to_add = []

    if 'seg-image' in input_type:
        for bbox in feature_extractor.get_picture_detections():
            bboxes_to_add.append(bbox)
            box_types_to_add.append(BOX_IMAGE)

    return feature_map, class_logits, bboxes_to_add, box_types_to_add
