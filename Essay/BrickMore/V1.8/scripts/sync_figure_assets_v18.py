"""Synchronize V1.8 raster previews using existing assets and source labels.

Requires Pillow. Run from any directory with Python 3.12.
Figure 14 is redrawn from the manuscript and transcribed release table.
Other outputs preserve existing renders and replace specified label regions.
The Figure 2 geometric-check panel is redrawn from its updated TikZ source.
Compile figure1.tex and figure2.tex separately for final vector PDFs.
"""

from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import re
import shutil

from PIL import Image, ImageChops, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / "backup_v18"
FONTS = Path("C:/Windows/Fonts")
INK = "#222B36"
MUTED = "#647180"
ACCENT = "#235780"
WASH = "#F0F4F8"
LINE = "#DCE2E8"


def font(size, bold=False, chinese=False):
    family = "msyh" if chinese else "arial"
    suffix = "bd" if bold else ""
    extension = ".ttc" if chinese else ".ttf"
    return ImageFont.truetype(str(FONTS / (family + suffix + extension)), size)


def original(relative_path):
    path = ROOT / relative_path
    backup = BACKUP / relative_path
    if not backup.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup)
    return Image.open(backup).convert("RGB")


def label(image, rectangle, text, size, *, bold=False, color=INK,
          background="white", left=False):
    draw = ImageDraw.Draw(image)
    draw.rectangle(rectangle, fill=background)
    x0, y0, x1, y1 = rectangle
    face = font(size, bold)
    assert draw.textlength(text, font=face) <= x1 - x0 - 6, text
    anchor = "lm" if left else "mm"
    x = x0 + 3 if left else (x0 + x1) / 2
    draw.text((x, (y0 + y1) / 2), text, font=face, fill=color, anchor=anchor)


def save(relative_path, image, regions=None):
    path = ROOT / relative_path
    if regions is not None:
        before = original(relative_path)
        outside = Image.new("L", image.size, 255)
        mask = ImageDraw.Draw(outside)
        for rectangle in regions:
            mask.rectangle(rectangle, fill=0)
        difference = ImageChops.difference(before, image).convert("L")
        assert ImageChops.multiply(difference, outside).getbbox() is None, relative_path
    image.save(path, dpi=(300, 300))
    print("Updated", relative_path)


def source_has(relative_path, *labels):
    source = (ROOT / relative_path).read_text(encoding="utf-8")
    for text in labels:
        assert text in source, (relative_path, text)


def check_panel(image, rectangle, size):
    x0, y0, x1, y1 = rectangle
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(rectangle, radius=max(4, size // 5), fill=WASH,
                           outline=LINE, width=max(1, size // 16))
    checks = ["One voxel component", "Grounded brick components",
              "Exact derived-target cover"]
    face = font(size)
    for index, text in enumerate(checks):
        y = y0 + (index + 0.5) * (y1 - y0) / 3
        x = x0 + size * 0.7
        draw.line([(x, y), (x + size * 0.3, y + size * 0.3),
                   (x + size * 0.85, y - size * 0.4)],
                  fill=ACCENT, width=max(2, size // 9))
        text_x = x0 + size * 2.0
        assert text_x + draw.textlength(text, font=face) < x1 - 5
        draw.text((text_x, y), text, fill=INK, font=face, anchor="lm")


def figure_previews():
    source_has("figure_tex/figure1_content.tex", "(c) Constructed dataset layouts")
    image = original("figures/figure1.png")
    region = (5, 580, 1050, 625)
    label(image, region, "(c) Constructed dataset layouts", 38, bold=True, left=True)
    save("figures/figure1.png", image, [region])

    source_has("figure_tex/figure2_content.tex", "GPT-6.1 Sol", "Geometric checks",
               "Grounded brick components", "Local bridging + retiling",
               "Geometry selects training data", "Voxels + bilingual L1--L5",
               "Geometric pass + screening status", "48 axis/sign transforms")
    image = original("figures/figure2.png")
    edits = [
        ((26, 330, 465, 362), "21 categories · 40 families each", 30, {}),
        ((630, 150, 940, 184), "GPT-6.1 Sol", 29,
         dict(bold=True, color="white", background=ACCENT)),
        ((1100, 331, 1540, 361), "Voxels + bilingual L1–L5", 30, {}),
        ((1100, 363, 1540, 392), "80,000 models · 48³ grid", 27, dict(color=MUTED)),
        ((1640, 362, 2080, 392), "48 axis/sign transforms · unique", 27,
         dict(color=MUTED)),
        ((1160, 519, 1538, 565), "Geometric checks", 33, dict(bold=True, left=True)),
        ((1380, 431, 1722, 468), "Repair / retile as needed", 26, dict(color="#B35845")),
        ((1640, 783, 2080, 817), "Same-color brick tiling", 31, {}),
        ((1640, 820, 2080, 852), "Local bridging + retiling", 27, dict(color=MUTED)),
        ((560, 783, 1008, 817), "Passing layouts + 5 captions", 30, {}),
        ((560, 820, 1008, 852), "Geometric pass + screening status", 26,
         dict(color=MUTED)),
    ]
    regions = []
    for rectangle, text, size, options in edits:
        label(image, rectangle, text, size, **options)
        regions.append(rectangle)
    rectangle = (1097, 570, 1540, 859)
    ImageDraw.Draw(image).rectangle(rectangle, fill="white")
    check_panel(image, (1130, 607, 1515, 754), 26)
    label(image, (1100, 783, 1537, 817), "Contact screening recorded", 30)
    label(image, (1100, 820, 1537, 852), "Geometry selects training data", 27, color=MUTED)
    regions.append(rectangle)
    save("figures/figure2.png", image, regions)


def unit_previews():
    edits = {
        "unit_02_llm_code": [
            ((1286, 210, 1540, 263), "GPT-6.1 Sol", 42,
             dict(color="white", background=ACCENT)),
        ],
        "unit_04_deduplication": [
            ((100, 1090, 1550, 1182), "48 axis/sign transforms · unique", 51,
             dict(color=MUTED)),
        ],
        "unit_05_tiling_repair": [
            ((110, 980, 1540, 1079), "Same-color brick tiling", 60, {}),
            ((100, 1090, 1550, 1182), "Local bridging + retiling", 51,
             dict(color=MUTED)),
        ],
        "unit_07_training_records": [
            ((110, 980, 1540, 1079), "Passing layouts + 5 captions", 60, {}),
            ((100, 1090, 1550, 1182), "Geometric pass + screening status", 51,
             dict(color=MUTED)),
        ],
        "unit_08_brickmore_model": [
            ((143, 32, 1550, 141), "BrickForma model", 75, dict(bold=True, left=True)),
        ],
    }
    for stem, changes in edits.items():
        path = f"figure2_units/{stem}.png"
        image = original(path)
        regions = []
        for rectangle, text, size, options in changes:
            label(image, rectangle, text, size, **options)
            regions.append(rectangle)
        save(path, image, regions)

    path = "figure2_units/unit_06_contact_screening.png"
    image = original(path)
    header = (143, 32, 1550, 141)
    body = (100, 175, 1550, 1200)
    label(image, header, "Geometric checks", 75, bold=True, left=True)
    ImageDraw.Draw(image).rectangle(body, fill="white")
    check_panel(image, (194, 385, 1468, 870), 86)
    label(image, (110, 980, 1540, 1079), "Contact screening recorded", 60)
    label(image, (100, 1090, 1550, 1182), "Geometry selects training data", 51, color=MUTED)
    save(path, image, [header, body])

    import json
    manifest = json.loads((ROOT / "figure2_units/manifest.json").read_text(encoding="utf-8"))
    overview = Image.new("RGB", (2000, 772), "#EAF0F5")
    original("figure2_units/overview.png").close()
    for index, unit in enumerate(manifest["units"]):
        tile = Image.open(ROOT / "figure2_units" / (unit["stem"] + ".png")).convert("RGB")
        tile = tile.resize((480, 361), Image.Resampling.LANCZOS)
        overview.paste(tile, (10 + (index % 4) * 500, 10 + (index // 4) * 386))
    save("figure2_units/overview.png", overview)


def historical_conversion_plot():
    import math
    source = (ROOT / "archive/historical_tables.tex").read_text(encoding="utf-8")
    manuscript = (ROOT / "main.tex").read_text(encoding="utf-8")
    counts = []
    for name in ["Strict v3", "Relaxed", "Local bridging and retiling"]:
        match = re.search(re.escape(name) + r" & ([\d,]+)", manuscript)
        counts.append(int(match.group(1).replace(",", "")))
    match = re.search(r"Integrated passing models & ([\d,]+)", manuscript)
    counts.append(int(match.group(1).replace(",", "")))
    screening = []
    for name in ["Relaxed", "Retile"]:
        row = next(line for line in source.splitlines()
                   if line.startswith(name + " & Each component grounded"))
        columns = row.rstrip(" \\").split(" & ")
        screening.append([int(value.replace(",", "")) for value in columns[-2:]])

    relative = "figures/image14.png"
    original(relative).close()
    scale = 2
    image = Image.new("RGB", (2100 * scale, 780 * scale), "white")
    draw = ImageDraw.Draw(image)

    def text(x, y, value, size=30, anchor="mm", color="black"):
        draw.multiline_text((x * scale, y * scale), value,
                            font=font(size * scale, chinese=True), fill=color,
                            anchor=anchor, align="center", spacing=3 * scale)

    def line(points, width=3, color="black"):
        draw.line([(x * scale, y * scale) for x, y in points], fill=color, width=width * scale)

    def rectangle(box, fill):
        draw.rectangle(tuple(int(value * scale) for value in box), fill=fill)

    text(650, 54, "(a) 80,000 模型的几何检查", 33)
    text(1690, 54, "(b) 历史自重平衡筛查（对数轴）", 33)
    bottom, top = 610, 112
    line([(180, top), (180, bottom), (1155, bottom)])
    for tick in range(0, 121, 20):
        y = bottom - tick / 120 * (bottom - top)
        line([(168, y), (180, y)])
        text(151, y, str(tick), 35, anchor="rm")
    # Rotated axis title is drawn on a separate transparent layer.
    axis = Image.new("RGBA", (650 * scale, 75 * scale), (255, 255, 255, 0))
    ImageDraw.Draw(axis).text((325 * scale, 37 * scale), "几何检查通过率（%）",
                             font=font(34 * scale, chinese=True), fill="black", anchor="mm")
    axis = axis.rotate(90, expand=True)
    image.paste(axis, (32 * scale, 39 * scale), axis)
    colors = ["#9EB9D5", "#608FC3", "#315E9D", "#193C6B"]
    names = ["严格策略 v3\n(10-11)", "放宽档\n多接地组件\n(10-12)",
             "局部桥接与重铺\nretile 全量\n(10-13)", "整合口径\n（报告推算）"]
    for x, count, color, name in zip([320, 550, 780, 1010], counts, colors, names):
        rate = Decimal(count) / Decimal(800)
        y = bottom - float(rate) / 120 * (bottom - top)
        rectangle((x - 90, y, x + 90, bottom - 2), color)
        formatted = rate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        text(x, y - 44, f"{count:,}\n({formatted}%)", 29)
        line([(x, bottom), (x, bottom + 12)])
        text(x, 682, name, 27)

    def log_y(value):
        return bottom - math.log10(value / 50) / math.log10(20000 / 50) * (bottom - top)

    line([(1280, top), (1280, bottom), (2060, bottom)])
    for tick, title in [(100, "10²"), (1000, "10³"), (10000, "10⁴")]:
        y = log_y(tick)
        line([(1268, y), (1280, y)])
        text(1250, y, title, 35, anchor="rm")
    for x, color, title in [(1610, "#E6A438", "最终状态自重平衡通过"),
                            (1610, "#B44731", "最终与全部层前缀通过")]:
        index = 0 if color == "#E6A438" else 1
        y = 137 + index * 43
        rectangle((x, y - 10, x + 42, y + 10), color)
        text(x + 58, y, title, 25, anchor="lm")
    for x, values, name in zip([1470, 1880], screening,
                                ["放宽档 (10-12)", "retile 全量 (10-13)"]):
        for offset, value, color in zip([-72, 72], values, ["#E6A438", "#B44731"]):
            y = log_y(value)
            rectangle((x + offset - 68, y, x + offset + 68, bottom - 2), color)
            text(x + offset, y - 24, f"{value:,}", 29)
        line([(x, bottom), (x, bottom + 12)])
        text(x, 657, name, 27)
    image = image.resize((2100, 780), Image.Resampling.LANCZOS)
    save(relative, image)


def sample_percentage_label():
    source = (ROOT / "archive/historical_tables.tex").read_text(encoding="utf-8")
    row = next(line for line in source.splitlines() if line.startswith("Q4 (sparse) &"))
    columns = row.split(" & ")
    count = int(columns[3])
    percentage = Decimal(count * 100) / Decimal(160)
    percentage = percentage.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    assert columns[4] == str(percentage) + r"\%"
    relative = "figures/image16.png"
    image = original(relative)
    region = (755, 109, 925, 171)
    draw = ImageDraw.Draw(image)
    draw.rectangle(region, fill="white")
    draw.text((837, 125), str(count), font=font(28), fill="black", anchor="mm")
    draw.text((837, 153), f"({percentage}%)", font=font(27), fill="black", anchor="mm")
    save(relative, image, [region])


def main():
    figure_previews()
    unit_previews()
    historical_conversion_plot()
    sample_percentage_label()


if __name__ == "__main__":
    main()
