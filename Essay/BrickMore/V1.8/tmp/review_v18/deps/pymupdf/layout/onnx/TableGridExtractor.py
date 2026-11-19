"""
TableGridExtractor.py

Loads an exported GridModelV1 ONNX model and predicts horizontal / vertical
grid boundary positions from a cropped table image.

Post-processing pipeline
------------------------
1. Resize input image to model input size.
2. Run ONNX inference -> h_heatmap (H,), v_heatmap (W,).
3. Apply threshold to each 1D heatmap.
4. Run 1D Connected Component Labeling (CCL) on the thresholded signal.
5. Compute weighted centroid of each component -> boundary coordinate.

"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import onnxruntime as ort

from ..common_util import resize_image, to_gray
from .table_grid_types import GridPrediction, CellInfo
from .common_util import make_session

# ---------------------------------------------------------------------------
# 1D CCL helper
# ---------------------------------------------------------------------------

def _ccl_1d_centroids(
    heatmap: np.ndarray,
    threshold: float,
) -> list[float]:
    """
    Apply threshold to a 1D heatmap, find connected components, and return
    the weighted centroid of each component.

    Parameters
    ----------
    heatmap   : 1D float32 array
    threshold : minimum value to consider active

    Returns
    -------
    Sorted list of centroid positions (float, 0-based index space).
    """
    active = heatmap >= threshold
    centroids: list[float] = []

    in_group   = False
    group_vals: list[float] = []
    group_idxs: list[int]   = []

    for i, (val, is_active) in enumerate(zip(heatmap, active)):
        if is_active:
            in_group = True
            group_vals.append(float(val))
            group_idxs.append(i)
        else:
            if in_group:
                # Compute weighted centroid
                total = sum(group_vals)
                if total > 0:
                    centroid = sum(v * i for v, i in zip(group_vals, group_idxs)) / total
                else:
                    centroid = float(sum(group_idxs)) / len(group_idxs)
                centroids.append(centroid)
                group_vals = []
                group_idxs = []
                in_group = False

    # Flush last group
    if in_group and group_vals:
        total = sum(group_vals)
        if total > 0:
            centroid = sum(v * i for v, i in zip(group_vals, group_idxs)) / total
        else:
            centroid = float(sum(group_idxs)) / len(group_idxs)
        centroids.append(centroid)

    return sorted(centroids)



# ---------------------------------------------------------------------------
# Main extractor class
# ---------------------------------------------------------------------------

class TableGridExtractor:
    """
    ONNX-based table grid boundary extractor.

    Usage
    -----
    extractor = TableGridExtractor("grid_model_v1.onnx")
    pred = extractor.predict(image_bgr)
    print(pred.h_lines, pred.v_lines)
    """

    def __init__(
        self,
        onnx_path: str | Path,
        h_on_threshold: float = 0.35,
        v_on_threshold: float = 0.45,
        providers: Optional[list[str]] = None,
    ) -> None:
        """
        Parameters
        ----------
        onnx_path      : path to the exported .onnx model file
        hmap_threshold : activation threshold for h_heatmap CCL
        vmap_threshold : activation threshold for v_heatmap CCL
        providers      : ONNX Runtime execution providers
                         (default: ["CPUExecutionProvider"])
        """
        self.onnx_path      = Path(onnx_path)
        self.h_on_threshold = h_on_threshold
        self.v_on_threshold = v_on_threshold

        if providers is None:
            providers = ["CPUExecutionProvider"]

        self._sess = make_session(str(self.onnx_path), providers)

        # Read model input shape from ONNX metadata
        inp           = self._sess.get_inputs()[0]
        self._input_h = int(inp.shape[2])
        self._input_w = int(inp.shape[3])

        # Derive output heatmap sizes via dummy forward pass
        dummy   = np.zeros((1, 3, self._input_h, self._input_w), dtype=np.float32)
        outputs = self._sess.run(None, {"image": dummy})
        self._out_h = int(outputs[0].shape[1])  # h_heatmap length
        self._out_w = int(outputs[1].shape[1])  # v_heatmap length

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict_grid(self, image_bgr: np.ndarray) -> GridPrediction:
        """
        Run inference on a single BGR image.

        Parameters
        ----------
        image_bgr : H x W x 3 uint8 BGR image (any size)

        Returns
        -------
        GridPrediction with h_lines and v_lines in input image space.
        """
        orig_h, orig_w = image_bgr.shape[:2]

        # Resize to model input size
        img_resized = resize_image(
            image_bgr,
            (self._input_w, self._input_h),
        )

        # BGR -> RGB (channel reversal), min-max normalize to [0, 1]
        img_rgb = img_resized[:, :, ::-1].astype(np.float32)
        mn, mx  = img_rgb.min(), img_rgb.max()
        if mx > mn:
            img_rgb = (img_rgb - mn) / (mx - mn)
        else:
            img_rgb = np.zeros_like(img_rgb)

        # (H, W, 3) -> (1, 3, H, W)
        inp = img_rgb.transpose(2, 0, 1)[np.newaxis, :]

        # ONNX inference -> h_heatmap, v_heatmap (indices 0 and 1)
        outputs   = self._sess.run(None, {"image": inp})
        h_heatmap = outputs[0][0]   # (H_out,)
        v_heatmap = outputs[1][0]   # (W_out,)

        # 1D CCL -> centroids in model output space
        h_centroids_out = _ccl_1d_centroids(h_heatmap, self.h_on_threshold)
        v_centroids_out = _ccl_1d_centroids(v_heatmap, self.v_on_threshold)

        # Scale centroids from model output space to input image space
        h_lines = [c * orig_h / self._out_h for c in h_centroids_out]
        v_lines = [c * orig_w / self._out_w for c in v_centroids_out]

        return GridPrediction(
            h_lines=sorted(h_lines),
            v_lines=sorted(v_lines),
            h_heatmap=h_heatmap,
            v_heatmap=v_heatmap,
        )

    # ------------------------------------------------------------------
    # Grid-based bbox assignment
    # ------------------------------------------------------------------

    @staticmethod
    def _filter_empty_lines(
        lines: list[float],
        centers: list[float],
        image_size: float,
    ) -> list[float]:
        """
        Remove adjacent line pairs that have no bbox center between them,
        and handle empty outer gaps:

        - If the gap between 0 and the first line contains no bbox center,
          the first line is moved to 0.0 (collapsed to the image edge).
        - If the gap between the last line and image_size contains no bbox
          center, the last line is removed entirely.
        - For inner lines: when two adjacent lines share an empty gap between
          them, they are replaced by their midpoint.

        The process repeats until stable.

        Parameters
        ----------
        lines      : sorted list of boundary coordinates
        centers    : list of bbox center coordinates (along same axis)
        image_size : image dimension along this axis (H or W)

        Returns
        -------
        Filtered and possibly merged list of boundary lines (sorted).
        """
        if not lines:
            return lines

        current = sorted(lines)
        changed = True

        while changed:
            changed = False
            if not current:
                break
            # Build gap list: edges = [0] + current + [image_size]
            # gaps[i] = (edges[i], edges[i+1])
            edges = [0.0] + current + [float(image_size)]
            n_gaps = len(edges) - 1

            # Mark each gap as empty (True) or occupied (False)
            gap_empty = [
                not any(edges[i] < c < edges[i + 1] for c in centers)
                for i in range(n_gaps)
            ]

            # Handle leading empty gap: move first line to 0.0
            if gap_empty[0] and current[0] != 0.0:
                current[0] = 0.0
                changed = True
                continue

            # Handle trailing empty gap: remove last line
            if gap_empty[-1] and current:
                current.pop()
                changed = True
                continue

            # Merge adjacent inner lines that share an empty gap between them
            merged: list[float] = []
            skip_next = False

            for i in range(len(current)):
                if skip_next:
                    skip_next = False
                    continue
                # gap to the right of current[i] is gap_empty[i+1]
                gap_right_empty = gap_empty[i + 1]
                if gap_right_empty and i + 1 < len(current):
                    # Merge with next line
                    merged.append((current[i] + current[i + 1]) / 2.0)
                    skip_next = True
                    changed   = True
                else:
                    merged.append(current[i])

            current = sorted(merged)

        return current

    def _post_process_grid(
        self,
        bboxes_page: np.ndarray,
        grid: GridPrediction,
        crop_x0: float,
        crop_y0: float,
        crop_h: float,
        crop_w: float,
        span_threshold: float,
    ) -> list[CellInfo]:
        """
        Assign each bbox to a grid cell (row, col) and compute span.

        Steps
        -----
        1. Convert each bbox from page space to crop space.
        2. Locate the cell that contains the bbox center point.
        3. If the bbox extends beyond the center cell by more than
           span_threshold of that cell's dimension, expand the span.

        Parameters
        ----------
        bboxes_page    : (N, 4) array of [x0, y0, x1, y1] in page space
        grid           : GridPrediction with h_lines / v_lines in crop space
        crop_x0        : left edge of the table crop in page space
        crop_y0        : top  edge of the table crop in page space
        crop_h         : height of the crop image in pixels
        crop_w         : width of the crop image in pixels
        span_threshold : fractional overlap required to expand span (e.g. 0.1)

        Returns
        -------
        List of CellInfo, one per bbox.
        """
        _h_lines_sorted = sorted(grid.h_lines)
        _v_lines_sorted = sorted(grid.v_lines)

        row_edges = [0.0] + _h_lines_sorted + [crop_h]
        col_edges = [0.0] + _v_lines_sorted + [crop_w]

        # Deduplicate and sort edges to handle potential overlaps or identical values
        row_edges = sorted(list(set(row_edges)))
        col_edges = sorted(list(set(col_edges)))

        if len(row_edges) < 2:
            row_edges = [0.0, crop_h]
        if len(col_edges) < 2:
            col_edges = [0.0, crop_w]
        def find_cell_idx(pos: float, edges: list[float]) -> int:
            """Return 0-based index of the interval containing pos."""
            for i in range(len(edges) - 1):
                if edges[i] <= pos < edges[i + 1]:
                    return i
            return max(0, len(edges) - 2)

        results: list[CellInfo] = []

        for i, bbox in enumerate(bboxes_page):
            x0_p, y0_p, x1_p, y1_p = float(bbox[0]), float(bbox[1]), \
                                       float(bbox[2]), float(bbox[3])

            # Convert to crop space
            x0 = x0_p - crop_x0
            y0 = y0_p - crop_y0
            x1 = x1_p - crop_x0
            y1 = y1_p - crop_y0

            cx = (x0 + x1) / 2.0
            cy = (y0 + y1) / 2.0

            # Center cell
            base_row = find_cell_idx(cy, row_edges)
            base_col = find_cell_idx(cx, col_edges)

            row_start = base_row
            row_end   = base_row + 1
            col_start = base_col
            col_end   = base_col + 1

            # Expand row span upward
            r = base_row
            while r > 0:
                cell_top    = row_edges[r]
                cell_height = row_edges[r] - row_edges[r - 1]
                if cell_height > 0 and (cell_top - y0) / cell_height > span_threshold:
                    row_start = r - 1
                    r -= 1
                else:
                    break

            # Expand row span downward
            r = base_row
            while r < len(row_edges) - 2:
                cell_bottom = row_edges[r + 1]
                cell_height = row_edges[r + 1] - row_edges[r]
                if cell_height > 0 and (y1 - cell_bottom) / cell_height > span_threshold:
                    row_end = r + 2
                    r += 1
                else:
                    break

            # Expand col span leftward
            c = base_col
            while c > 0:
                cell_left  = col_edges[c]
                cell_width = col_edges[c] - col_edges[c - 1]
                if cell_width > 0 and (cell_left - x0) / cell_width > span_threshold:
                    col_start = c - 1
                    c -= 1
                else:
                    break

            # Expand col span rightward
            c = base_col
            while c < len(col_edges) - 2:
                cell_right = col_edges[c + 1]
                cell_width = col_edges[c + 1] - col_edges[c]
                if cell_width > 0 and (x1 - cell_right) / cell_width > span_threshold:
                    col_end = c + 2
                    c += 1
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

    def predict(
        self,
        image_bgr: np.ndarray,
        bboxes: Optional[np.ndarray] = None,
        texts: Optional[list[str]] = None,
        span_threshold: float = 0.1,
    ) -> tuple[GridPrediction, list[CellInfo]]:
        """
        Predict grid boundaries and optionally assign bboxes to grid cells.

        Parameters
        ----------
        image_bgr      : cropped table BGR image (any size)
        bboxes         : (N, 4) array of [x0, y0, x1, y1] in crop space.
                         If None, only grid prediction is performed.
        texts          : list of text strings aligned with bboxes.
                         If provided, each CellInfo.text is populated.
        span_threshold : fractional overlap to trigger span expansion (default 0.1)

        Returns
        -------
        (GridPrediction, list[CellInfo])
        CellInfo list is empty when bboxes is None.
        """
        grid = self.predict_grid(image_bgr)

        if bboxes is None or len(bboxes) == 0:
            return grid, []

        bboxes_arr = np.asarray(bboxes, dtype=np.float32)
        crop_h = float(image_bgr.shape[0])
        crop_w = float(image_bgr.shape[1])

        # bboxes are in crop space; centers are used directly without offset.
        cx_list = sorted((float(b[0]) + float(b[2])) / 2.0 for b in bboxes_arr)
        cy_list = sorted((float(b[1]) + float(b[3])) / 2.0 for b in bboxes_arr)

        # Remove adjacent line pairs with no bbox center between them
        filtered_h = self._filter_empty_lines(grid.h_lines, cy_list, crop_h)
        filtered_v = self._filter_empty_lines(grid.v_lines, cx_list, crop_w)

        grid = GridPrediction(
            h_lines=filtered_h,
            v_lines=filtered_v,
            h_heatmap=grid.h_heatmap,
            v_heatmap=grid.v_heatmap,
        )

        # bboxes are already in crop space, so crop_x0=0.0, crop_y0=0.0.
        cells = self._post_process_grid(
            bboxes_page=bboxes_arr,
            grid=grid,
            crop_x0=0.0,
            crop_y0=0.0,
            crop_h=crop_h,
            crop_w=crop_w,
            span_threshold=span_threshold,
        )

        # Populate text field using bbox_idx if texts list is provided
        if texts is not None:
            for cell in cells:
                if 0 <= cell.bbox_idx < len(texts):
                    cell.text = texts[cell.bbox_idx]

        return grid, cells

    # ------------------------------------------------------------------
    # Visualization
    # ------------------------------------------------------------------

    def visualize(
        self,
        image_bgr: np.ndarray,
        pred: GridPrediction,
        window_title: str = "TableGridExtractor",
        max_dim: int = 1000,
    ) -> np.ndarray:
        """
        Draw predicted grid lines on the image and display via OpenCV.

        Layout (2x2 grid, all panels same size)
        ----------------------------------------
        (1,1) input image with predicted grid lines overlaid
        (1,2) h_heatmap tiled to 2D  (rows = H axis)
        (2,1) v_heatmap tiled to 2D  (cols = W axis)
        (2,2) summary info panel

        Parameters
        ----------
        image_bgr    : original BGR image
        pred         : GridPrediction from predict()
        window_title : OpenCV window title
        max_dim      : maximum panel dimension before downscaling

        Returns
        -------
        The composed BGR visualization array.
        """
        import cv2  # visualization only

        img_h, img_w = image_bgr.shape[:2]

        # Panel (1,1): image + grid overlay
        overlay = image_bgr.copy()
        for y in pred.h_lines:
            y_px = int(round(y))
            cv2.line(overlay, (0, y_px), (img_w, y_px), (0, 255, 0), 1)
        for x in pred.v_lines:
            x_px = int(round(x))
            cv2.line(overlay, (x_px, 0), (x_px, img_h), (255, 0, 0), 1)

        # Panel (1,2): h_heatmap tiled to 2D
        h_heatmap_resized = cv2.resize(
            pred.h_heatmap[:, np.newaxis], (img_w, img_h),
            interpolation=cv2.INTER_LINEAR,
        )
        h_panel = cv2.applyColorMap(
            (h_heatmap_resized * 255).clip(0, 255).astype(np.uint8), cv2.COLORMAP_JET
        )
        cv2.putText(h_panel, f"h_thr={self.h_on_threshold:.2f}",
                    (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        # Panel (2,1): v_heatmap tiled to 2D
        v_heatmap_resized = cv2.resize(
            pred.v_heatmap[np.newaxis, :], (img_w, img_h),
            interpolation=cv2.INTER_LINEAR,
        )
        v_panel = cv2.applyColorMap(
            (v_heatmap_resized * 255).clip(0, 255).astype(np.uint8), cv2.COLORMAP_JET
        )
        cv2.putText(v_panel, f"v_thr={self.v_on_threshold:.2f}",
                    (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        # Panel (2,2): summary info
        info_panel = np.zeros((img_h, img_w, 3), dtype=np.uint8)
        summary = [
            f"h_lines : {len(pred.h_lines)}",
            f"v_lines : {len(pred.v_lines)}",
        ]
        for i, txt in enumerate(summary):
            cv2.putText(info_panel, txt, (10, 30 + i * 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1,
                        cv2.LINE_AA)

        # Compose 2x2
        top_row  = np.concatenate([overlay, h_panel], axis=1)
        bot_row  = np.concatenate([v_panel, info_panel],    axis=1) # Use info_panel for (2,2)
        composed = np.concatenate([top_row, bot_row], axis=0)

        # Fit within max_dim x max_dim
        ch, cw = composed.shape[:2]
        if ch > max_dim or cw > max_dim:
            scale    = max_dim / max(ch, cw)
            composed = cv2.resize(
                composed,
                (max(1, int(cw * scale)), max(1, int(ch * scale))),
                interpolation=cv2.INTER_AREA,
            )

        cv2.imshow(window_title, composed) # Use window_title
        cv2.waitKey(0)
        cv2.destroyWindow(window_title) # Use window_title

        return composed


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import cv2  # used for imread and imshow in CLI entry point

    parser = argparse.ArgumentParser(
        description="Run TableGridExtractor on all images in a directory."
    )
    parser.add_argument("onnx_path",  help="Path to the exported .onnx model.")
    parser.add_argument("image_dir",  help="Directory containing input images.")
    parser.add_argument(
        "--hmap_threshold", type=float, default=0.3,
        help="Activation threshold for h_heatmap CCL (default: 0.3).",
    )
    parser.add_argument(
        "--vmap_threshold", type=float, default=0.4,
        help="Activation threshold for v_heatmap CCL (default: 0.4).",
    )
    parser.add_argument(
        "--extensions", nargs="*",
        default=["png", "jpg", "jpeg", "bmp", "tif", "tiff"],
        help="Image file extensions to scan.",
    )
    args = parser.parse_args()

    extractor = TableGridExtractor(
        onnx_path=args.onnx_path,
        hmap_threshold=args.hmap_threshold,
        vmap_threshold=args.vmap_threshold,
    )

    image_dir = Path(args.image_dir)
    img_paths: list[Path] = []
    for ext in args.extensions:
        img_paths.extend(sorted(image_dir.glob(f"*.{ext}")))
        img_paths.extend(sorted(image_dir.glob(f"*.{ext.upper()}")))
    img_paths = sorted(set(img_paths))

    if not img_paths:
        print(f"No images found in: {image_dir}")
    else:
        print(f"Found {len(img_paths)} image(s). Press any key to advance.")

    for img_path in img_paths:
        img_bgr = cv2.imread(str(img_path))
        if img_bgr is None:
            print(f"Cannot read: {img_path.name}")
            continue

        pred = extractor.predict_grid(img_bgr)
        print(
            f"{img_path.name}  "
            f"h_lines={len(pred.h_lines)}  v_lines={len(pred.v_lines)}"
        )
        extractor.visualize(img_bgr, pred)
