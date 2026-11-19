from pathlib import Path
from collections import Counter
from PIL import Image
import json
import csv

root = Path("D:/BrickMore")
project = root / "Essay/BrickMore/V2.2"
data_path = root / "Train/datasets"
strict = json.loads((data_path / "assembly_80000/assembly_summary.json").read_bytes())["shards"]
with (data_path / "retile_assembly_80000/category_summary.csv").open(encoding="utf-8-sig") as source:
    records = list(csv.DictReader(source))

im = Image.open(project / "figures/image15_en.png").convert("RGB")
print(im.size)
regions = [(70, 70), (10, 10), (305, 545), (318, 510), (333, 510)]
print([(loc, im.getpixel(loc)) for loc in regions])
print(Counter(im.crop((275, 131, 1975, 546)).getdata()).most_common(8))
cats = sorted({record["group"].split("_", 1)[1] for record in records})
assert len(cats) == 21
width = 81.65
height = 418.0
base = 548
maximum = 0
for i, cat in enumerate(cats):
    rows = [record for record in records if record["group"].split("_", 1)[1] == cat]
    source_n = sum(int(record["modelCount"]) for record in rows)
    counts = [sum(s["categoryStatusCounts"][cat].get("success", 0) for s in strict.values())] + [
        sum(int(record[k]) for record in rows) for k in ["baselinePassed", "geometryPassed"]
    ]
    expected = [count / source_n for count in counts]
    rgb = [(198, 212, 230), (115, 156, 205), (31, 75, 134)]
    left = 286
    xs = [round(left + width * i + 22 * j) for j in range(3)]
    heights = []
    for x, color in zip(xs, rgb):
        matches = [y for y in range(108, 547) if max(abs(a-b) for a, b in zip(im.getpixel((x,y)), color)) <= 11]
        heights.append((base - min(matches)) / height if matches else 0.0)
    delta = max(abs(e-h) for e,h in zip(expected, heights))
    maximum = max(maximum, delta)
    print(cat, ", ".join(f"{e:.2%}/{h:.2%}" for e,h in zip(expected, heights)), f"{delta:.3%}")
print("Max residual:", maximum)
assert maximum < .015, maximum

