"""
table_grid_types.py

Shared dataclasses for all TableGridExtractor versions (V1, V1A, V2).

Placing GridPrediction and CellInfo in a single module ensures that
isinstance() checks and type annotations are consistent across extractors,
table_to_markdown, and eval_table_TEDs regardless of which extractor version
is active at runtime.

Version-specific fields are optional (default None) so that each extractor
only populates the fields it actually produces.

GridPrediction field availability by version
--------------------------------------------
Field             V1    V1A   V2
h_lines           yes   yes   yes
v_lines           yes   yes   yes
h_heatmap         yes   yes   no
v_heatmap         yes   yes   no
h_confidences     no    yes   no
v_confidences     no    yes   no
db_prob_map       no    yes   no
h_on_prob         no    no    yes
v_on_prob         no    no    yes
h_lines_norm      no    no    yes
v_lines_norm      no    no    yes
h_cls             no    no    yes
connectivity      no    no    yes
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# GridPrediction
# ---------------------------------------------------------------------------

@dataclass
class GridPrediction:
    """
    Predicted grid structure for one table image.

    Required fields (all versions)
    --------------------------------
    h_lines : sorted boundary y-coordinates in crop image pixel space.
    v_lines : sorted boundary x-coordinates in crop image pixel space.

    V1 / V1A fields
    ----------------
    h_heatmap : raw horizontal heatmap, shape (H_out,) or (orig_h,).
    v_heatmap : raw vertical heatmap,   shape (W_out,) or (orig_w,).

    V1A-only fields
    ----------------
    h_confidences : per-candidate h-line confidence scores, shape (N_h,).
    v_confidences : per-candidate v-line confidence scores, shape (N_v,).
    db_prob_map   : DB probability map, shape (orig_h, orig_w), or None.

    V2-only fields
    ---------------
    h_on_prob    : sigmoid activation probabilities for all h anchors, shape (max_h,).
    v_on_prob    : sigmoid activation probabilities for all v anchors, shape (max_v,).
    h_lines_norm : detected h-line positions normalized to [0, 1], shape (N_h,).
    v_lines_norm : detected v-line positions normalized to [0, 1], shape (N_v,).
    h_cls        : integer class label per h-line (e.g. 1=normal, 2=header), shape (N_h,).
    connectivity : cell connectivity probability array, shape (N_row-1, N_col-1, C),
                   or None when the ConnClassifier model is absent.
    """

    # --- Required (all versions) ---
    h_lines: list
    v_lines: list

    # --- V1 / V1A ---
    h_heatmap: Optional[np.ndarray] = None
    v_heatmap: Optional[np.ndarray] = None

    # --- V1A only ---
    h_confidences: Optional[np.ndarray] = None
    v_confidences: Optional[np.ndarray] = None
    db_prob_map:   Optional[np.ndarray] = None

    # --- V2 only ---
    h_on_prob:    Optional[np.ndarray] = None
    v_on_prob:    Optional[np.ndarray] = None
    h_lines_norm: Optional[np.ndarray] = None
    v_lines_norm: Optional[np.ndarray] = None
    h_cls:        Optional[np.ndarray] = None
    connectivity: Optional[np.ndarray] = None


# ---------------------------------------------------------------------------
# CellInfo
# ---------------------------------------------------------------------------

@dataclass
class CellInfo:
    """
    Grid cell assignment for one text bbox.

    bbox_idx  : index into the original bboxes list passed to predict().
    row_start : 0-based inclusive start row.
    row_end   : 0-based exclusive end row   (row_span = row_end - row_start).
    col_start : 0-based inclusive start col.
    col_end   : 0-based exclusive end col   (col_span = col_end - col_start).
    row       : canonical grid row for direct table indexing (== row_start).
    col       : canonical grid col for direct table indexing (== col_start).
    text      : text content of the bbox.
    """

    bbox_idx  : int
    row_start : int
    row_end   : int
    col_start : int
    col_end   : int
    row       : int = 0
    col       : int = 0
    text      : str = ""

    @property
    def row_span(self) -> int:
        return self.row_end - self.row_start

    @property
    def col_span(self) -> int:
        return self.col_end - self.col_start
