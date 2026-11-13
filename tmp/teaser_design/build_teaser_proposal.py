"""Compose a first-page layout proposal from existing BrickMore research renders."""
from pathlib import Path
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyArrowPatch, Rectangle


ROOT = Path('D:/BrickMore')
FIGURES = ROOT / 'Essay/BrickMore/V1.1XZC/BrickMore_LaTeX_工程/figures'
EVALUATION = ROOT / 'Results/three_model_comparison_20261111/intake/Results/comparison_full'
OUTPUT = ROOT / 'output/figures/brickmore_teaser_proposal.png'
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

# All geometry images are reused as supplied, preserving their pixels and colors.
# This is a layout proposal, not a newly measured experiment or a final paper figure.
FONT = FontProperties(fname='C:/Windows/Fonts/arial.ttf')
BOLD = FontProperties(fname='C:/Windows/Fonts/arialbd.ttf')
INK = '#22252b'
MUTED = '#626974'
BLUE = '#235780'

fig = plt.figure(figsize=(12.6, 8.55), facecolor='white')
canvas = fig.add_axes([0, 0, 1, 1], frameon=False)
canvas.set_xlim(0, 1)
canvas.set_ylim(0, 1)
canvas.set_axis_off()


def label(x, y, text, size=12, bold=False, color=INK, align='left'):
    return fig.text(x, y, text, fontsize=size, fontproperties=BOLD if bold else FONT,
                    color=color, ha=align, va='center')


def show(path, x, y, width, height):
    axis = fig.add_axes([x, y, width, height], frameon=False)
    axis.imshow(plt.imread(path))
    axis.set_axis_off()
    return axis


def arrow(x0, y0, x1, y1, color=MUTED):
    canvas.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle='-|>',
                                    mutation_scale=12, linewidth=1.15, color=color))


label(.026, .972, '(a)  Voxel-to-brick construction', 15, True)
label(.535, .972, '(b)  Brick connectivity repair', 15, True)
label(.145, .93, 'Source voxels', 13, align='center')
label(.379, .93, 'Brick layouts', 13, align='center')
label(.641, .93, 'Raw layouts', 13, align='center')
label(.875, .93, 'After retiling', 13, align='center')
canvas.plot([.509, .509], [.535, .978], color='#d6dae0', lw=.8)

for y, source, target, name, action in [
    (.735, 'image4.png', 'image5.png', 'Table', 'Tile'),
    (.535, 'image1.png', 'image3.png', 'Piano', 'Tile + repair'),
]:
    show(FIGURES / source, .04, y, .208, .184)
    show(FIGURES / target, .275, y, .208, .184)
    arrow(.246, y + .10, .281, y + .10)
    label(.264, y + .065, action, 12, align='center', color=MUTED)
    label(.055, y + .01, name, 12, color=MUTED)

for y, source, target, name in [
    (.735, 'image20.png', 'image21.png', 'Camera'),
    (.535, 'image26.png', 'image27.png', 'Car'),
]:
    show(FIGURES / source, .538, y, .208, .184)
    show(FIGURES / target, .772, y, .208, .184)
    arrow(.743, y + .10, .779, y + .10)
    label(.762, y + .065, 'Retile', 12, align='center', color=MUTED)
    label(.55, y + .01, name, 12, color=MUTED)

canvas.add_patch(Rectangle((.025, .428), .95, .083, facecolor='#f0f4f8', edgecolor='none'))
label(.042, .483, 'Automated dataset construction', 12, True, BLUE)
label(.042, .452, '80k source shapes · 21 classes · 5 captions each', 12)
arrow(.445, .469, .488, .469, BLUE)
label(.594, .483, 'LoRA training', 12, True, BLUE, 'center')
label(.594, .452, 'Qwen3-1.7B', 13, align='center')
arrow(.698, .469, .741, .469, BLUE)
label(.858, .483, 'Text-to-brick pipeline', 12, True, BLUE, 'center')
label(.858, .452, 'Generate + repair', 13, align='center')

label(.026, .398, '(c)  Text-conditioned generation', 15, True)
label(.975, .398, 'Existing evaluated outputs', 12, color=MUTED, align='right')

selections = [
    ('Birdhouse', 'brickmore__birdhouse-L1__stitched'),
    ('Camera', 'brickmore__camera_L2_P1_G__stitched'),
    ('Chair', 'brickmore__chair-L2V5__raw'),
    ('Car', 'brickmore__car-L1V2__stitched'),
    ('Vessel', 'brickmore__vessel_L1_P2_G__stitched'),
    ('Bookshelf', 'brickmore__bookshelf-L1-C1__stitched'),
    ('Guitar', 'brickmore__guitar_L1_P2_G__stitched'),
    ('Table', 'brickmore__table-L1V3__stitched'),
    ('Pot', 'brickmore__pot-L1-A__stitched'),
    ('Sofa', 'brickmore__sofa-L1V3__stitched'),
]
records = {
    record['sample_id']: record
    for line in (EVALUATION / 'selected_manifest.jsonl').read_text(encoding='utf-8').splitlines()
    if (record := json.loads(line))['system'] == 'BrickMore'
}
for index, (name, sample_id) in enumerate(selections):
    record = records[sample_id]
    x = .025 + (index % 5) * .193
    y = .218 if index < 5 else .025
    path = EVALUATION / 'rendered/views' / sample_id / '01.png'
    show(path, x, y + .024, .177, .14)
    variant = 'raw' if record['variant'] == 'raw' else 'retiled'
    label(x + .0885, y + .011, f'{name} · {variant}', 13, align='center')

fig.savefig(OUTPUT, dpi=220, facecolor='white', bbox_inches=None)
plt.close(fig)
print(OUTPUT)
