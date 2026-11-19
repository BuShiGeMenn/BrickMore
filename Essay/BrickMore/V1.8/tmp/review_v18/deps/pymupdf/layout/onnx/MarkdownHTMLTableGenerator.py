"""
MarkdownHTMLTableGenerator.py

Variant of MarkdownGenerator that renders tables as HTML (<table>) instead of
pipe-style Markdown. All other block types follow standard Markdown rules.

This format is compatible with CommonMark and is the expected input format for
benchmarks such as ParseBench, which parse <table> tags for table evaluation.

Usage
-----
    from source.layout.onnx.MarkdownHTMLTableGenerator import MarkdownHTMLTableGenerator
    gen = MarkdownHTMLTableGenerator(model)
    md  = gen.generate(page)
"""

from __future__ import annotations

from typing import Any

from .HTMLGenerator import HTMLGenerator
from .MarkdownGenerator import MarkdownGenerator


class MarkdownHTMLTableGenerator(MarkdownGenerator):
    """
    Variant of MarkdownGenerator that renders tables as HTML instead of
    pipe-style Markdown. All other block types follow standard Markdown rules.

    Parameters
    ----------
    model : BoxRFDGNN instance used to run inference.
    """

    @staticmethod
    def _render_table(cells: list[Any]) -> str:
        return HTMLGenerator._render_table(cells)
