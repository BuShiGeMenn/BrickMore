"""Compact figure layout using mesh-derived diagnostic brick renders."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyArrowPatch, Rectangle

ROOT = Path('D:/BrickMore')
RENDERS = ROOT / 'tmp/teaser_design/renders'
OUTPUT = ROOT / 'output/figures/brickmore_teaser_proposal_v2.png'
FONT = FontProperties(fname='C:/Windows/Fonts/arial.ttf')
BOLD = FontProperties(fname='C:/Windows/Fonts/arialbd.ttf')
INK, MUTED, BLUE = '#22252b', '#626974', '#235780'
fig = plt.figure(figsize=(11.8, 6.6), facecolor='white')
canvas = fig.add_axes([0,0,1,1], frameon=False)
canvas.set_xlim(0,1)
canvas.set_ylim(0,1)
canvas.set_axis_off()


def label(x,y,text,size=12,bold=False,color=INK,align='left'):
    fig.text(x,y,text,fontsize=size,fontproperties=BOLD if bold else FONT,
             color=color,ha=align,va='center')


def model(name,x,y,width,height):
    axis = fig.add_axes([x,y,width,height],frameon=False)
    axis.imshow(plt.imread(RENDERS / f'{name}.png'))
    axis.set_axis_off()


def arrow(x0,y,x1):
    canvas.add_patch(FancyArrowPatch((x0,y),(x1,y),arrowstyle='-|>',
                                    mutation_scale=12,lw=1.1,color=MUTED))


label(.018,.974,'(a)  Voxel-to-brick construction',15,True)
label(.683,.974,'(b)  Connectivity repair',15,True)
for center,text in [(.087,'Voxels'),(.24,'Bricks'),(.414,'Voxels'),(.567,'Bricks'),
                    (.752,'Raw'),(.913,'Retiled')]:
    label(center,.926,text,12.5,align='center')

for name,center in [('table_voxels',.087),('table_bricks',.24),
                    ('birdhouse_voxels',.414),('birdhouse_bricks',.567),
                    ('brickmore__camera_L2_P1_G__raw',.752),
                    ('brickmore__camera_L2_P1_G__stitched',.913)]:
    model(name,center-.077,.684,.154,.231)
for x0,x1 in [(.151,.176),(.478,.503),(.818,.848)]:
    arrow(x0,.797,x1)
canvas.plot([.66,.66],[.668,.983],color='#d9dde1',lw=.7)
label(.164,.667,'Table · 1,117 voxels → 197 bricks',11.5,align='center')
label(.49,.667,'Birdhouse · 937 voxels → 200 bricks',11.5,align='center')
label(.833,.667,'Camera · raw → retiled',11.5,align='center')

canvas.add_patch(Rectangle((.018,.571),.964,.071,facecolor='#f0f4f8',edgecolor='none'))
label(.031,.618,'Automated dataset construction',12,True,BLUE)
label(.031,.588,'80k source shapes · 21 classes · 5 captions each',10.8)
arrow(.437,.605,.48)
label(.589,.618,'LoRA training',12,True,BLUE,'center')
label(.589,.588,'Qwen3-1.7B',12,align='center')
arrow(.696,.605,.738)
label(.86,.618,'Text-to-brick pipeline',12,True,BLUE,'center')
label(.86,.588,'Generate + repair',12,align='center')

label(.018,.541,'(c)  Text-conditioned generation',15,True)
label(.98,.541,'Display colors distinguish individual bricks',10.5,color=MUTED,align='right')

selections = [
    ('Birdhouse','brickmore__birdhouse-L1__stitched'),
    ('Camera','brickmore__camera_L2_P1_G__stitched'),
    ('Chair','brickmore__chair-L2V5__raw'),
    ('Car','brickmore__car-L1V2__stitched'),
    ('Vessel','brickmore__vessel_L1_P2_G__stitched'),
    ('Bookshelf','brickmore__bookshelf-L1-C1__stitched'),
    ('Guitar','brickmore__guitar_L1_P2_G__stitched'),
    ('Table','brickmore__table-L1V3__stitched'),
    ('Pot','brickmore__pot-L1-A__stitched'),
    ('Sofa','brickmore__sofa-L1V3__stitched'),
]
for index,(name,sample) in enumerate(selections):
    x = .018 + (index%5)*.195
    y = .297 if index<5 else .039
    model(sample,x,y,.184,.229)
    variant = 'raw' if sample.endswith('__raw') else 'retiled'
    label(x+.092,y-.011,f'{name} · {variant}',11.5,align='center')

fig.savefig(OUTPUT,dpi=240,facecolor='white')
plt.close(fig)
print(OUTPUT)
