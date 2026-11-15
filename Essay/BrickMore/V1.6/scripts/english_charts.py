"""Publication-size English charts, redrawn from recorded counts (no new runs).

Requires matplotlib. The portable data snapshot records exact source fields.
"""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT=Path(__file__).resolve().parents[1]
F=ROOT/'figures'
data=json.loads((ROOT/'figure_data/chart_counts.json').read_text())
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9.5,
    'axes.titlesize':10,'axes.labelsize':9.5,'xtick.labelsize':9.5,
    'ytick.labelsize':9.5,'legend.fontsize':9.5,'pdf.fonttype':42,
    'axes.spines.top':False,'axes.spines.right':False})
def save(fig,name):
    fig.savefig(F/(name+'_en.pdf'))
    fig.savefig(F/(name+'_en.png'),dpi=300)
    plt.close(fig)

fig,axs=plt.subplots(1,2,figsize=(7,2.7),gridspec_kw={'width_ratios':[1.25,1]})
fig.subplots_adjust(left=.085,right=.99,bottom=.22,top=.84,wspace=.34)
ax=axs[0];vals=data['conversion']['passes'];rates=[v/800 for v in vals]
bars=ax.bar(range(4),rates,color=['#9eb9d3','#5e91c3','#2e5d94','#183d68'])
ax.set_ylim(0,130);ax.set_yticks([0,50,100]);ax.set_ylabel('Geometric pass rate (%)')
ax.set_title('(a) Conversion: 80,000 models',pad=9)
ax.set_xticks(range(4),['Strict v3\nOct 11','Relaxed\nOct 12','Retiled\nOct 13','Piano B\nOct 14'])
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
ax.set_xticks([0,1],['Relaxed\nOct 12','Retiled\nOct 13'])
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
ax.set_yticks([0,1],['Relaxed','Retiled']);ax.set_xlim(0,80000)
ax.set_xticks([0,20000,40000,60000,80000],['0','20,000','40,000','60,000','80,000'])
ax.set_xlabel('Number of models (80,000 total)')
fig.legend([Patch(facecolor=c) for c in colors],data['physics']['labels'],
    loc='upper center',ncol=3,frameon=False,handlelength=1.2,columnspacing=1,
    handletextpad=.5,bbox_to_anchor=(.5,1),fontsize=9)
save(fig,'image17')

fig,axs=plt.subplots(1,2,figsize=(7,2.9));fig.subplots_adjust(left=.15,right=.98,bottom=.16,top=.82,wspace=.7)
for ax,title,labels,values,color in [
    (axs[0],'(a) BrickGPT rejections\n114 prompts',
     ['Already\nrejected','Collision','Not in\nlibrary','Out of\nbounds'],[8207,2757,8,4],'#b54730'),
    (axs[1],'(b) BrickNet failures\n53 attempts',
     ['Dangling node','Missing\nconnector','Invalid edge\nsyntax','Index / dim.\nerror','Unknown part\nor color'],[24,10,10,6,3],'#e5a534')]:
    ax.barh(range(len(values)),values,color=color,height=.72);ax.invert_yaxis()
    ax.set_yticks(range(len(values)),labels);ax.set_title(title,pad=12)
    ax.set_xlim(0,max(values)*1.29)
    for i,v in enumerate(values):ax.text(v+max(values)*.02,i,f'{v:,}',va='center',fontsize=9.5)
axs[0].set_xticks([0,5000,10000],['0','5,000','10,000']);axs[1].set_xticks([0,10,20,30])
save(fig,'image19')
print('English vector charts written.')
