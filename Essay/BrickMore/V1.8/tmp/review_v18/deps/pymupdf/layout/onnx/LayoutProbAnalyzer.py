"""
LayoutProbAnalyzer
Purpose: Analyze per-class layout probability maps from a PDF page using an ONNX model.

The underlying network accepts a grayscale page image and returns a combined
output tensor containing internal feature channels followed by segmentation
logit channels. This class extracts only the segmentation head output
(the last num_classes channels) and converts it to per-pixel probability maps.

Usage:
    analyzer = LayoutProbAnalyzer()                  # uses default ONNX path
    analyzer = LayoutProbAnalyzer("custom.onnx")     # explicit path
    prob_map = analyzer.get_layout_prob(page)        # (H_page, W_page, num_classes)
"""

import glob
import os
from pathlib import Path

import numpy as np
import onnxruntime as ort


_CLASS_NAMES = [
    'background', 'text', 'title', 'picture', 'table',
    'list-item', 'page-header', 'page-footer',
    'section-header', 'footnote', 'caption', 'formula',
]

_VIZ_COLS = 6    # number of class heatmaps per row in test visualization
_VIZ_CMAP = "hot"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resize_bilinear(img, target_h, target_w):
    """
    Resize a 2-D or 3-D numpy array to (target_h, target_w) using bilinear
    interpolation. No external libraries required.

    Args:
        img:      np.ndarray, shape (H, W) or (H, W, C)
        target_h: int
        target_w: int

    Returns:
        np.ndarray of shape (target_h, target_w) or (target_h, target_w, C),
        dtype float32.
    """
    src_h, src_w = img.shape[:2]
    is_2d = img.ndim == 2
    if is_2d:
        img = img[:, :, np.newaxis]

    row_coords = (np.arange(target_h) + 0.5) * (src_h / target_h) - 0.5
    col_coords = (np.arange(target_w) + 0.5) * (src_w / target_w) - 0.5

    row0 = np.clip(np.floor(row_coords).astype(np.int32), 0, src_h - 1)
    row1 = np.clip(row0 + 1,                              0, src_h - 1)
    col0 = np.clip(np.floor(col_coords).astype(np.int32), 0, src_w - 1)
    col1 = np.clip(col0 + 1,                              0, src_w - 1)

    dr = (row_coords - row0).astype(np.float32)[:, np.newaxis]  # (target_h, 1)
    dc = (col_coords - col0).astype(np.float32)[np.newaxis, :]  # (1, target_w)

    # FIX(perf): vectorized over channel axis instead of a Python-level for-loop.
    # Transpose to (C, H, W), index all channels at once, then transpose back.
    img_chw = img.transpose(2, 0, 1).astype(np.float32)         # (C, src_h, src_w)
    top    = img_chw[:, row0, :][:, :, col0] * (1.0 - dc) \
           + img_chw[:, row0, :][:, :, col1] * dc               # (C, target_h, target_w)
    bottom = img_chw[:, row1, :][:, :, col0] * (1.0 - dc) \
           + img_chw[:, row1, :][:, :, col1] * dc
    out = (top * (1.0 - dr) + bottom * dr).transpose(1, 2, 0)   # (target_h, target_w, C)

    if is_2d:
        out = out[:, :, 0]
    return out


def _softmax_over_classes(seg_logits, temperature=1.0):
    """
    Apply temperature-scaled softmax across the class axis (axis 0).

    The input is expected to be raw segmentation logits, which may contain
    negative values. No ReLU masking is applied; standard numerically stable
    softmax is used directly.

    Temperature controls the sharpness of the distribution per pixel:
        T < 1 : sharper  (winner-takes-all strengthened)
        T = 1 : standard softmax
        T > 1 : smoother (probability spread more evenly across classes)

    Args:
        seg_logits:  np.ndarray, shape (num_classes, H, W), raw logits (may be negative)
        temperature: float, must be > 0 (default 1.0)

    Returns:
        np.ndarray, shape (num_classes, H, W), float32, values in [0, 1],
        summing to 1 along axis 0 at every pixel.
    """
    scaled = seg_logits / temperature

    # Numerically stable softmax: subtract per-pixel max before exponentiation
    safe_max = scaled.max(axis=0, keepdims=True)   # (1, H, W)
    exp      = np.exp(scaled - safe_max)
    denom    = exp.sum(axis=0, keepdims=True)

    return (exp / denom).astype(np.float32)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class LayoutProbAnalyzer:
    """
    Loads an ONNX segmentation model and produces per-class probability maps
    for a given PDF page.

    The network output is a combined tensor of internal feature channels and
    segmentation logit channels. Only the last num_classes channels (the
    segmentation head output) are used; all preceding feature channels are
    discarded.

    Per-pixel probabilities are computed via temperature-scaled softmax across
    the class axis, so all classes compete and probabilities sum to 1 per pixel.
    A higher temperature smooths the distribution (less winner-takes-all).
    """

    def __init__(self, onnx_path=None, temperature=1.0):
        """
        Args:
            onnx_path:   str or None.
                         If None, defaults to
                         <repo_root>/resources/onnx/feature_imf1.onnx
                         where <repo_root> is two directories above this file.
            temperature: float > 0 (default 1.0).
                         Controls softmax sharpness across classes per pixel.
                         T > 1 spreads probability more evenly (less winner-takes-all).
                         T = 1 is standard softmax.
                         T < 1 sharpens the distribution.
        """
        if onnx_path is None:
            script_dir = Path(__file__).resolve().parent.parent
            onnx_path  = f'{script_dir}/resources/onnx/feature_imf1.onnx'

        self._session     = make_session(onnx_path, None)
        input_shape       = self._session.get_inputs()[0].shape
        self._target_h    = input_shape[2]
        self._target_w    = input_shape[3]
        self._temperature = temperature
        self.class_names  = _CLASS_NAMES

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_layout_prob(self, page):
        """
        Compute per-class layout probability maps for a PyMuPDF page.

        Pipeline:
            1. Render the page to a numpy array at its default resolution.
            2. Convert to grayscale and resize to the model input resolution
               using numpy-only bilinear interpolation.
            3. Normalize the grayscale image to [0, 1].
            4. Run ONNX inference; slice the last num_classes channels from
               the combined output tensor to obtain segmentation logits.
            5. Apply temperature-scaled softmax to convert logits to
               per-pixel class probabilities.
            6. Resize the probability map back to the original page resolution.

        Args:
            page: fitz.Page (PyMuPDF page object)

        Returns:
            np.ndarray of shape (H_page, W_page, num_classes), float32.
            The last axis is aligned with self.class_names.
        """
        # Step 1: render page to numpy array (H, W, n_channels)
        pix        = page.get_pixmap()
        bytes_data = np.frombuffer(pix.samples, dtype=np.uint8)
        page_img   = bytes_data.reshape(pix.height, pix.width, pix.n)
        page_h, page_w = page_img.shape[:2]

        # Step 2: grayscale conversion (average RGB; drop alpha if present)
        if page_img.shape[2] >= 3:
            gray = (page_img[:, :, 0].astype(np.float32)
                    + page_img[:, :, 1].astype(np.float32)
                    + page_img[:, :, 2].astype(np.float32)) / 3.0
        else:
            gray = page_img[:, :, 0].astype(np.float32)

        # Step 3: resize to model input resolution, then min-max normalize
        gray_resized = _resize_bilinear(gray, self._target_h, self._target_w)
        lo, hi = gray_resized.min(), gray_resized.max()
        if hi > lo:
            gray_resized = (gray_resized - lo) / (hi - lo)
        else:
            gray_resized = np.zeros_like(gray_resized, dtype=np.float32)

        # Step 4: run inference once; slice segmentation channels from combined output.
        # The network returns a tensor of shape (1, total_channels, H, W) containing
        # internal feature channels followed by num_classes segmentation logit channels.
        # Only the last num_classes channels correspond to the segmentation head.
        nn_input   = gray_resized[np.newaxis, np.newaxis, :, :]   # (1, 1, H, W)
        input_name = self._session.get_inputs()[0].name
        raw_out    = self._session.run(None, {input_name: nn_input})[0]  # (1, total_C, H, W)

        n_classes = len(_CLASS_NAMES)
        seg_logits = raw_out[0, -n_classes:, :, :]                  # (n_classes, H, W)

        # Step 5: temperature-scaled softmax over class axis
        prob_map = _softmax_over_classes(seg_logits, self._temperature)  # (n_classes, H, W)

        # Step 6: resize back to page resolution
        prob_map_hwc = np.transpose(prob_map, (1, 2, 0))                 # (H_model, W_model, C)
        prob_resized = _resize_bilinear(prob_map_hwc, page_h, page_w)    # (H_page, W_page, C)

        return prob_resized


# ---------------------------------------------------------------------------
# Test / visualization (run via __main__)
# ---------------------------------------------------------------------------

def _page_img_to_rgb(page_img):
    """Return (H, W, 3) uint8 suitable for imshow from a pymupdf pixmap array."""
    if page_img.shape[2] == 4:
        return page_img[:, :, :3]
    if page_img.shape[2] == 1:
        return np.repeat(page_img, 3, axis=2)
    return page_img[:, :, :3]


def _visualize_page(page_img_rgb, prob_map, class_names, pdf_name, page_idx):
    """
    Display the original page image and per-class probability heatmaps.

    Args:
        page_img_rgb: np.ndarray (H, W, 3) uint8
        prob_map:     np.ndarray (H, W, C) float32
        class_names:  list[str]
        pdf_name:     str
        page_idx:     int, 0-based
    """
    import matplotlib.pyplot as plt

    num_classes = len(class_names)
    class_rows  = (num_classes + _VIZ_COLS - 1) // _VIZ_COLS
    total_rows  = 1 + class_rows

    fig, axes = plt.subplots(
        total_rows, _VIZ_COLS,
        figsize=(_VIZ_COLS * 3, total_rows * 3),
        squeeze=False,
    )
    fig.suptitle(f"{pdf_name}  |  page {page_idx + 1}", fontsize=13, y=1.01)

    # Row 0: original image in first cell; remaining cells hidden
    axes[0][0].imshow(page_img_rgb)
    axes[0][0].set_title("original", fontsize=9)
    axes[0][0].axis("off")
    for col in range(1, _VIZ_COLS):
        axes[0][col].axis("off")

    # Rows 1+: one heatmap per class
    for idx, name in enumerate(class_names):
        row = 1 + idx // _VIZ_COLS
        col = idx % _VIZ_COLS
        ax  = axes[row][col]
        im  = ax.imshow(prob_map[:, :, idx], cmap=_VIZ_CMAP, vmin=0.0, vmax=1.0)
        ax.set_title(name, fontsize=8)
        ax.axis("off")
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    # Hide unused axes in the last class row
    remainder = num_classes % _VIZ_COLS
    if remainder:
        for col in range(remainder, _VIZ_COLS):
            axes[total_rows - 1][col].axis("off")

    plt.tight_layout()
    plt.show()


def _scan_pdfs(pdf_dir):
    """Return a sorted list of PDF paths found recursively under pdf_dir."""
    paths = sorted(glob.glob(os.path.join(pdf_dir, "**", "*.pdf"), recursive=True))
    if not paths:
        paths = sorted(glob.glob(os.path.join(pdf_dir, "*.pdf")))
    return paths


def _run_test(pdf_dir):
    import fitz

    pdf_paths = _scan_pdfs(pdf_dir)
    if not pdf_paths:
        print(f"No PDF files found in: {pdf_dir}")
        return

    print(f"Found {len(pdf_paths)} PDF file(s).")
    analyzer = LayoutProbAnalyzer()

    for pdf_path in pdf_paths:
        pdf_name = os.path.basename(pdf_path)
        print(f"Processing: {pdf_path}")
        doc = fitz.open(pdf_path)

        for page_idx in range(len(doc)):
            page = doc[page_idx]

            pix        = page.get_pixmap()
            bytes_data = np.frombuffer(pix.samples, dtype=np.uint8)
            page_img   = bytes_data.reshape(pix.height, pix.width, pix.n)

            prob_map     = analyzer.get_layout_prob(page)
            page_img_rgb = _page_img_to_rgb(page_img)
            _visualize_page(page_img_rgb, prob_map, _CLASS_NAMES, pdf_name, page_idx)

        doc.close()


if __name__ == '__main__':
    pdf_dir = '/media/win/PTMP/PDF/BOKDataset/book/PDF'
    _run_test(pdf_dir)
