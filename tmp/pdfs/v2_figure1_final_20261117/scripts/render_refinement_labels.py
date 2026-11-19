"""Render the English refinement labels in the historical paper figures."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
F=ROOT/'figures'
FONT='C:/Windows/Fonts/arial.ttf'
def font(n): return ImageFont.truetype(FONT,n)
def put(im,xy,text,size=38,fill='black',anchor='mm'):
    ImageDraw.Draw(im).multiline_text(xy,text,font=font(size),fill=fill,anchor=anchor,align='center',spacing=5)
def wipe(im,box,color='white'): ImageDraw.Draw(im).rectangle(box,fill=color)
def save(im,name): im.save(F/(name+'_en.png'),dpi=(300,300))

# Category bars are copied exactly: no values are inferred from bar heights.
im=Image.open(F/'image15.png').convert('RGB');wipe(im,(0,0,2099,100))
for x,c,t in [(250,'#c9d7e8','Strict v3'),(810,'#729cd0','Relaxed'),(1370,'#23538a','Refined')]:
    ImageDraw.Draw(im).rectangle((x,46,x+55,72),fill=c);put(im,(x+80,59),t,40,anchor='lm')
wipe(im,(0,110,95,540));lab=Image.new('RGBA',(450,70));ImageDraw.Draw(lab).text((225,35),'Geometric pass rate (%)',font=font(40),fill='black',anchor='mm');lab=lab.rotate(90,expand=True);im.paste(lab,(15,110),lab)
save(im,'image15')

src=Image.open(F/'generated_gallery.png').convert('RGB')
im=Image.new('RGB',(2400,900),'white')
names=['Birdhouse · refined','Camera · refined','Car · refined','Chair · raw','Guitar · refined','Piano · refined','Table · refined','Vessel · refined']
for i,name in enumerate(names):
    col,row=i%4,i//4
    tile=src.crop((45+600*col,5+625*row,555+600*col,515+625*row))
    # Background is neutral gray. Crop around colored model pixels only.
    mask=tile.point(lambda v: v)
    from PIL import ImageChops
    r,g,b=tile.split();mask=ImageChops.lighter(ImageChops.difference(r,b),ImageChops.difference(g,b)).point(lambda v: 255 if v>15 else 0)
    box=mask.getbbox()
    if box: tile=tile.crop((max(0,box[0]-6),max(0,box[1]-6),min(510,box[2]+6),min(510,box[3]+6)))
    tile.thumbnail((525,365),Image.Resampling.LANCZOS)
    im.paste(tile,(col*600+(600-tile.width)//2,row*450+10+(365-tile.height)//2))
    put(im,(300+600*col,row*450+412),name,46)
save(im,'generated_gallery')
im=Image.open(F/'original_comparison.png').convert('RGB');wipe(im,(250,0,2199,90))
for x,t in [(550,'BrickForma (raw)'),(1200,'BrickForma (refined)'),(1850,'BrickGPT')]:put(im,(x,42),t,42)
wipe(im,(900,1475,1500,1549));put(im,(1200,1502),'No refinement needed',42)
save(im,'original_comparison')

from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT=Path(__file__).resolve().parents[1]
F=ROOT/'figures'
data=json.loads((ROOT/'figure_data/historical_release_counts.json').read_text())
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9.5,
    'axes.titlesize':10,'axes.labelsize':9.5,'xtick.labelsize':9.5,
    'ytick.labelsize':9.5,'legend.fontsize':9.5,'pdf.fonttype':42,
    'axes.spines.top':False,'axes.spines.right':False})
def save(fig,name):
    fig.savefig(F/(name+'_en.pdf'))
    plt.close(fig)

fig,axs=plt.subplots(1,2,figsize=(7,2.7),gridspec_kw={'width_ratios':[1.25,1]})
fig.subplots_adjust(left=.085,right=.99,bottom=.22,top=.84,wspace=.34)
ax=axs[0];vals=data['conversion']['passes'];rates=[v/800 for v in vals]
bars=ax.bar(range(4),rates,color=['#9eb9d3','#5e91c3','#2e5d94','#183d68'])
ax.set_ylim(0,130);ax.set_yticks([0,50,100]);ax.set_ylabel('Geometric pass rate (%)')
ax.set_title('(a) Conversion: 80,000 models',pad=9)
ax.set_xticks(range(4),['Strict v3\nOct 11','Relaxed\nOct 12','Refined\nOct 13','Piano B\nOct 14'])
for b,v,p in zip(bars,vals,rates):
    ax.text(b.get_x()+b.get_width()/2,p+2,f'{v:,}\n({p:.2f}%)',ha='center',va='bottom',fontsize=9)
ax=axs[1]
for k,(label,color,values) in enumerate([
    ('Final equilibrium','#e5a534',[2650,220]),
    ('Final + prefixes','#b54730',[478,128])]):
    xs=[x+(k-.5)*.33 for x in range(2)]
    bars=ax.bar(xs,values,width=.33,color=color,label=label)
    for b,v in zip(bars,values):ax.text(b.get_x()+b.get_width()/2,v*1.1,f'{v:,}',ha='center',va='bottom',fontsize=9)
ax.set_yscale('log');ax.set_ylim(50,30000)
ax.set_xticks([0,1],['Relaxed\nOct 12','Refined\nOct 13'])
ax.set_title('(b) Gravity screening',pad=9)
ax.legend(loc='upper right',frameon=False,handlelength=1,borderpad=0,labelspacing=.25)
save(fig,'image14')

statuses=data['physics']['statuses'];colors=data['physics']['colors']
fig,ax=plt.subplots(figsize=(7,2.8));fig.subplots_adjust(left=.11,right=.945,bottom=.23,top=.57)
for y,release in enumerate(['Relaxed','Retiled']):
    left=0
    for key,c in zip(statuses,colors):
        v=data['physics'][release].get(key,0)
        ax.barh(y,v,left=left,color=c,height=.65,edgecolor='white',linewidth=.4)
        if v>=10000:ax.text(left+v/2,y,f'{v:,}',ha='center',va='center',fontsize=9.5)
        left+=v
    assert left==80000
ax.set_yticks([0,1],['Relaxed','Refined']);ax.set_xlim(0,80000)
ax.set_xticks([0,20000,40000,60000,80000],['0','20,000','40,000','60,000','80,000'])
ax.set_xlabel('Number of models (80,000 total)')
fig.legend([Patch(facecolor=c) for c in colors],data['physics']['labels'],
    loc='upper center',ncol=3,frameon=False,handlelength=1.2,columnspacing=1,
    handletextpad=.5,bbox_to_anchor=(.5,1),fontsize=9)
save(fig,'image17')

