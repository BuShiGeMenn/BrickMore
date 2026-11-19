class DefaultSorter:
    """
    Complete reading-order sorter for layout groups.

    Logic:
    1. Headers (page-header) are placed at the absolute beginning.
    2. Footers (page-footer) are placed at the absolute end.
    3. Main content is sorted by (footnote flag, column index, quantized top-y, left-x).
    4. Y-axis tolerance (gap=10) is applied to handle slight vertical misalignments.
    """

    _HEADER_CLASS = "page-header"
    _FOOTER_CLASS = "page-footer"
    _Y_GAP = 10  # Tolerance in pixels for vertical alignment

    def sort(self, page, groups, det_result) -> list[int]:
        """
        Sort groups and det_result into a logical reading order.

        Args:
            page: PyMuPDF page object (used for page.rect.width).
            groups: list[dict] of layout groups with 'group_bbox' and 'class_name'.
            det_result: list of detection entries paired 1-to-1 with groups.

        Returns:
            list[int]: Indices into groups/det_result in reading order.
        """
        page_width = page.rect.width
        boundaries = self.detect_columns(groups, page_width)

        def _sort_key(idx):
            g   = groups[idx]
            cls = g.get("class_name", "")
            bbox = g.get("group_bbox", [0, 0, 0, 0])

            is_footnote = 1 if cls == "footnote" else 0
            col_idx     = self.get_col_idx(g, boundaries)
            quantized_y = bbox[1] // self._Y_GAP
            left_x      = bbox[0]

            return (is_footnote, col_idx, quantized_y, left_x)

        # Categorize indices to enforce Header -> Content -> Footer flow
        headers = []
        footers = []
        content = []

        for idx, g in enumerate(groups):
            cls = g.get("class_name")
            if cls == self._HEADER_CLASS:
                headers.append(idx)
            elif cls == self._FOOTER_CLASS:
                footers.append(idx)
            else:
                content.append(idx)

        content.sort(key=_sort_key)

        return headers + content + footers

    @staticmethod
    def detect_columns(groups: list, page_width: float) -> list:
        """
        Detect column boundaries using x-center positions of text groups.
        """
        TEXT_CLASSES = {"text", "list-item"}
        MAX_COLUMNS = 4
        MIN_RATIO = 0.08
        MIN_ABS = 2
        GAP_RATIO = 0.04
        WIDE_BLOCK_RATIO = 0.80

        candidates = [g for g in groups if g.get("class_name") in TEXT_CLASSES]
        if not candidates:
            return [0.0, page_width]

        wide_threshold = page_width * WIDE_BLOCK_RATIO
        filtered = [
            g for g in candidates
            if (g["group_bbox"][2] - g["group_bbox"][0]) < wide_threshold
        ]

        source = filtered if len(filtered) >= MIN_ABS * 2 else candidates

        x_centers = sorted(
            (g["group_bbox"][0] + g["group_bbox"][2]) / 2
            for g in source
        )
        total = len(x_centers)
        if not total:
            return [0.0, page_width]

        gap_threshold = page_width * GAP_RATIO
        min_count = max(MIN_ABS, int(total * MIN_RATIO))

        gap_candidates = []
        for i in range(1, total):
            gap = x_centers[i] - x_centers[i - 1]
            if gap > gap_threshold:
                mid = (x_centers[i] + x_centers[i - 1]) / 2
                gap_candidates.append((gap, mid))

        if not gap_candidates:
            return [0.0, page_width]

        gap_candidates.sort(key=lambda t: -t[0])
        top_mids = sorted(mid for _, mid in gap_candidates[: MAX_COLUMNS - 1])

        all_regions = [0.0] + top_mids + [page_width]

        def count_in_band(lo, hi):
            return sum(1 for x in x_centers if lo <= x < hi)

        valid_boundaries = []
        for idx in range(1, len(all_regions) - 1):
            boundary = all_regions[idx]
            left_lo  = all_regions[idx - 1]
            right_hi = all_regions[idx + 1]

            if (count_in_band(left_lo, boundary) >= min_count and
                    count_in_band(boundary, right_hi) >= min_count):
                valid_boundaries.append(boundary)

        return [0.0] + valid_boundaries + [page_width]

    @staticmethod
    def get_col_idx(group: dict, boundaries: list) -> int:
        """Determines which column a group belongs to based on its left edge."""
        bbox   = group.get("group_bbox", [0, 0, 0, 0])
        left_x = bbox[0]
        for i in range(len(boundaries) - 1):
            if boundaries[i] <= left_x < boundaries[i + 1]:
                return i
        return len(boundaries) - 2
