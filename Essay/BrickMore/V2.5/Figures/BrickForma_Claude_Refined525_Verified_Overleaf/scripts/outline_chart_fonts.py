"""Convert the active data charts' PDF glyphs into vector paths for submission."""

import subprocess
import tempfile
from pathlib import Path
from xml.etree import ElementTree

import cairosvg
from pypdf import PdfReader, PdfWriter


PROJECT = Path(__file__).resolve().parents[1]
CHARTS = (
    "figures/image14_en.pdf",
    "figures/image17_en.pdf",
    "figures/image19_en.pdf",
    "figures/comparison_20261119/01-zero-invalid.pdf",
    "figures/comparison_20261119/02-means.pdf",
    "figures/comparison_20261119/03-distributions.pdf",
    "figures/comparison_20261119/04-by-level.pdf",
)


def font_rows(pdf):
    result = subprocess.run(["pdffonts", str(pdf)], check=True, capture_output=True, text=True)
    return [line for line in result.stdout.splitlines()[2:] if line.strip()]


def outline(pdf):
    if not font_rows(pdf):
        return
    with tempfile.TemporaryDirectory(dir=pdf.parent) as scratch:
        svg = Path(scratch) / "chart.svg"
        cairo_pdf = Path(scratch) / "cairo.pdf"
        outlined = Path(scratch) / "chart.pdf"
        subprocess.run(["pdftocairo", "-svg", "-f", "1", "-l", "1", str(pdf), str(svg)], check=True)
        tags = {element.tag.rsplit("}", 1)[-1] for element in ElementTree.parse(svg).iter()}
        if "path" not in tags or tags & {"text", "image"}:
            raise RuntimeError(f"Expected vector paths without text or raster images: {pdf.name}")
        cairosvg.svg2pdf(url=str(svg), write_to=str(cairo_pdf))
        page = PdfReader(cairo_pdf, strict=True).pages[0]
        states = page["/Resources"].get("/ExtGState", {})
        for ref in states.values():
            state = ref.get_object()
            if any(state.get(key, 1) != 1 for key in ("/CA", "/ca")) or state.get("/SMask", "/None") != "/None":
                raise RuntimeError(f"Unexpected transparency in {pdf.name}")
        # Cairo adds a page group even for fully opaque plots. pdfTeX can
        # duplicate that dictionary when it embeds such a chart in the paper.
        page.pop("/Group", None)
        writer = PdfWriter()
        writer.add_page(page)
        writer.write(outlined)
        if font_rows(outlined):
            raise RuntimeError(f"Font resources remain in {pdf.name}")
        outlined.replace(pdf)


if __name__ == "__main__":
    for chart in CHARTS:
        outline(PROJECT / chart)
        print(chart)
