from pathlib import Path
import json, shutil, re

ROOT=Path('D:/BrickMore')
PROJECT=ROOT/'Essay/BrickMore/V1.2'
OUT=PROJECT/'figure2_units'
(OUT/'assets').mkdir(parents=True,exist_ok=True)
(OUT/'content').mkdir(exist_ok=True)
(OUT/'references').mkdir(exist_ok=True)
TMP=ROOT/'tmp/figure2_units_build'
TMP.mkdir(exist_ok=True)

for name in ['birdhouse_voxels','birdhouse_dataset','brickmore__birdhouse-L1__stitched']:
    shutil.copy2(PROJECT/'figures/parts'/f'{name}.png',OUT/'assets'/f'{name}.png')
style=(PROJECT/'figure_tex/style.tex').read_text(encoding='utf-8').replace('figures/parts/','assets/')
style+=r'''
\definecolor{levelone}{HTML}{3D7BCE}
\definecolor{leveltwo}{HTML}{298D81}
\definecolor{levelthree}{HTML}{8063B3}
\definecolor{levelfour}{HTML}{BD7A25}
\definecolor{levelfive}{HTML}{638E39}
\newcommand{\unitheader}[2]{
  \path[use as bounding box] (0,0) rectangle (14,10.6);
  \path[card,line width=.8pt,rounded corners=5pt] (.12,.12) rectangle (13.88,10.48);
  \node[circle,fill=accent,text=white,minimum size=.62cm,font=\bfseries\fontsize{12}{14}\selectfont] at (.72,.76) {#1};
  \node[anchor=west,font=\bfseries\fontsize{18}{21}\selectfont] at (1.25,.76) {#2};
}
'''
(OUT/'style.tex').write_text(style,encoding='utf-8')

titles={1:('pending','Specification'),2:('llm_code','LLM programs'),3:('five_levels','Voxels + five prompt levels'),
        4:('deduplication','Deduplication'),5:('tiling_repair','Tiling + repair'),
        6:('contact_screening','Contact screening'),7:('training_records','Training records'),
        8:('brickmore_model','BrickMore model')}

def write_unit(n,body):
    name,title=titles[n]
    content=r'\begin{tikzpicture}[x=1cm,y=-1cm]'+'\n'+f'\\unitheader{{{n}}}{{{title}}}\n'+body+'\n'+r'\end{tikzpicture}'+'\n'
    stem=f'unit_{n:02}_{name}'
    (OUT/'content'/f'{stem}.tex').write_text(content,encoding='utf-8')
    (OUT/f'{stem}.tex').write_text(r'\documentclass[border=0pt]{standalone}'+'\n'+
        r'\input{style}'+'\n'+r'\begin{document}'+'\n'+r'\input{content/'+stem+'}\n'+r'\end{document}'+'\n',encoding='utf-8')

write_unit(1,r'''
\path[draw=line,dashed,line width=1pt,rounded corners=5pt] (2.3,2.55) rectangle (11.7,7.75);
\node[text=muted,font=\bfseries\fontsize{36}{42}\selectfont] at (7,4.75) {TBD};
\node[text=muted,font=\fontsize{13}{16}\selectfont] at (7,6.15) {Content to be defined};
''')

code='''def generate(job, revision):
    p = plan(job["category"], job["family"],
             job["instance"], revision)
    ...
    for attempt in range(1, 21):
        co, la, pa, cl, e = build(p, scale)
        v = validate(p, co, la, pa, e)
        ...
        if v["passed"]:
            return (p, co, la, pa, cl, e, v,
                    history, initial)
'''
(OUT/'references/generation_excerpt.py').write_text(code,encoding='utf-8')
def esc(text):
    return ''.join({'\\':r'\textbackslash{}','_':r'\_','{':r'\{','}':r'\}','#':r'\#','%':r'\%','&':r'\&'}.get(c,c) for c in text)
body=r'''
\path[fill=wash,draw=line,line width=.7pt,rounded corners=4pt] (.72,1.65) rectangle (13.28,8.82);
\path[fill=accent,rounded corners=3pt] (.72,1.65) rectangle (13.28,2.34);
\node[anchor=west,text=white,font=\bfseries\fontsize{11}{13}\selectfont] at (1.05,2.00) {produce.py};
\node[anchor=east,text=white,font=\fontsize{10}{12}\selectfont] at (12.93,2.00) {AI\_A + AI\_B};
'''
for i,line in enumerate(code.splitlines()):
    indent=len(line)-len(line.lstrip())
    text=esc(line.lstrip())
    for keyword in ['def','for','in','if','return']:
        text=re.sub(r'\b'+keyword+r'\b',lambda m:r'\textcolor{levelthree}{'+m.group()+'}',text)
    for function in ['plan','build','validate']:
        text=re.sub(r'\b'+function+r'\b',lambda m:r'\textcolor{leveltwo}{'+m.group()+'}',text)
    y=2.90+i*.47
    body+=f'\\node[anchor=east,text=muted,font=\\ttfamily\\fontsize{{8}}{{10}}\\selectfont] at (1.27,{y}) {{{i+1:02}}};\n'
    body+=f'\\node[anchor=west,font=\\ttfamily\\fontsize{{10.3}}{{13}}\\selectfont] at ({1.60+indent*.185},{y}) {{{text}}};\n'
body+=r'''
\node[text=accent,font=\bfseries\fontsize{14}{17}\selectfont] at (7,9.37) {Parameterize $\rightarrow$ Build $\rightarrow$ Validate};
\node[tinylabel,font=\fontsize{9}{11}\selectfont] at (7,9.98) {Project code excerpt; setup and resampling details omitted.};
'''
write_unit(2,body)

prompts_path=ROOT/'Train/samples/models/birdhouse/vx80k5p_20261010_A_birdhouse_m0001/prompts.json'
records=json.loads(prompts_path.read_text(encoding='utf-8'))
full=[{k:r[k] for k in ['modelId','promptLevel','promptType','captionEn','captionZh','recordId']} for r in records]
(OUT/'references/birdhouse_prompts_L1_L5.json').write_text(json.dumps(full,ensure_ascii=False,indent=2),encoding='utf-8')

body=r'''
\tikzset{ray/.style={-{Stealth[length=2.6mm,width=1.8mm]},line width=1.0pt}}
% Exactly five arrows, all directed outwards from the same voxel model.
\draw[ray,levelone] (7,3.65)--(7,3.06);
\draw[ray,leveltwo] (5.66,4.61)--(5.04,4.38);
\draw[ray,levelthree] (8.34,4.61)--(8.96,4.38);
\draw[ray,levelfour] (6.05,6.53)--(4.97,7.44);
\draw[ray,levelfive] (7.95,6.53)--(9.03,7.44);
\asset{birdhouse_voxels}{7}{5.18}{3.10}
\node[text=muted,font=\fontsize{9.5}{11}\selectfont] at (7,6.94) {One voxel model};

\path[fill=levelone!4,draw=levelone!45,rounded corners=4pt,line width=.7pt] (4.23,1.39) rectangle (9.77,3.06);
\node[anchor=west,text=levelone,font=\bfseries\fontsize{11}{13}\selectfont] at (4.50,1.76) {Level 1 $\cdot$ Minimal};
\node[align=left,text width=4.99cm,font=\fontsize{10}{12.3}\selectfont] at (7,2.42) {An oval birdhouse with curved roof, enclosed room and front entrance.};

\path[fill=leveltwo!4,draw=leveltwo!45,rounded corners=4pt,line width=.7pt] (.47,3.55) rectangle (5.04,6.20);
\node[anchor=west,text=leveltwo,font=\bfseries\fontsize{11}{13}\selectfont] at (.73,3.96) {Level 2 $\cdot$ Basic structure};
\node[align=left,text width=4.02cm,font=\fontsize{10}{12.3}\selectfont] at (2.755,5.10) {\ldots\ The protective roof joins the walls; the circular front entrance reaches a real interior cavity.};

\path[fill=levelthree!4,draw=levelthree!45,rounded corners=4pt,line width=.7pt] (8.96,3.55) rectangle (13.53,6.20);
\node[anchor=west,text=levelthree,font=\bfseries\fontsize{11}{13}\selectfont] at (9.22,3.96) {Level 3 $\cdot$ Geometry};
\node[align=left,text width=4.02cm,font=\fontsize{10}{12.3}\selectfont] at (11.245,5.10) {\ldots\ Curved substantial surfaces carry their continuously attached functional parts.};

\path[fill=levelfour!4,draw=levelfour!45,rounded corners=4pt,line width=.7pt] (.68,7.44) rectangle (6.42,9.72);
\node[anchor=west,text=levelfour,font=\bfseries\fontsize{11}{13}\selectfont] at (.95,7.85) {Level 4 $\cdot$ Proportion};
\node[align=left,text width=5.18cm,font=\fontsize{10}{12.3}\selectfont] at (3.55,8.81) {\ldots\ Overall width is 1.15 times depth; height is 0.80 times width. Parts follow functional positions.};

\path[fill=levelfive!4,draw=levelfive!45,rounded corners=4pt,line width=.7pt] (7.58,7.44) rectangle (13.32,9.72);
\node[anchor=west,text=levelfive,font=\bfseries\fontsize{11}{13}\selectfont] at (7.85,7.85) {Level 5 $\cdot$ Comprehensive};
\node[align=left,text width=5.18cm,font=\fontsize{10}{12.3}\selectfont] at (10.45,8.81) {\ldots\ Continuous red, tan, brown color regions distinguish the body and attachments. \ldots};
\node[text=muted,font=\fontsize{8.7}{10.5}\selectfont] at (7,10.15) {Prompt excerpts; each level retains earlier details.};
'''
write_unit(3,body)

original=(PROJECT/'figure_tex/figure2_content.tex').read_text(encoding='utf-8')
markers={4:('% 4. Dedup:','% The main path,'),5:('% 5. Tiling and repair:','% 6. Visual contact model:'),
         6:('% 6. Visual contact model:','% Repair return path,'),7:('% 7. Machine-readable','% 8. Compact neural-network'),
         8:('% 8. Compact neural-network',r'\node[heading,text=accent] at (.12,7.66)')}
origins={4:(13.77,.55),5:(13.77,4.30),6:(9.22,4.30),7:(4.67,4.30),8:(.12,4.30)}
for n in range(4,9):
    begin,end=markers[n]
    segment=original[original.index(begin):original.index(end)]
    x,y=origins[n]
    body=r'''\begin{scope}[shift={(.55,.50)},scale=3.30,transform shape]
\tikzset{every node/.append style={font=\fontsize{4.3}{5.2}\selectfont},
         tinylabel/.style={font=\fontsize{3.7}{4.5}\selectfont,text=muted}}
'''+f'\\begin{{scope}}[shift={{(-{x},-{y})}}]\n'+segment+'\n'+r'\end{scope}'+'\n'+r'\end{scope}'
    write_unit(n,body)

manifest={'unit_count':8,'first_unit_status':'TBD, per user request',
 'unit_2_source':'Train/programs/produce.py: generate(); whitespace reformatted and omissions marked with ellipses',
 'unit_3_source':str(prompts_path.relative_to(ROOT)),
 'unit_3_model':'birdhouse voxel model vx80k5p_20261010_A_birdhouse_m0001',
 'unit_3_prompt_display':'Exact excerpts from captionEn; complete five levels attached in references',
 'units_4_to_8':'Same imagery and text as Figure 2; independently framed and scaled',
 'units':[{'number':n,'stem':f'unit_{n:02}_{titles[n][0]}','title':titles[n][1]} for n in titles]}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'README.md').write_text('''# Figure 2：八个独立单元

本目录提供八张独立 PNG（300 dpi）及对应的可编辑 TikZ / LaTeX 源码，供逐项修改和重新组合。

1. `unit_01_pending`：第一单元待定，保留空白占位。
2. `unit_02_llm_code`：项目 `Train/programs/produce.py` 中 `generate()` 的代码摘录；省略部分以 `...` 表示。完整显示文本见 `references/generation_excerpt.py`。
3. `unit_03_five_levels`：同一体素模型向五个 Level 提示词发散，恰好五个向外箭头。图中文字是项目真实提示词的简短摘录；五级完整中英文描述见 `references/birdhouse_prompts_L1_L5.json`。
4. `unit_04_deduplication`：去重。
5. `unit_05_tiling_repair`：拼接与修复。
6. `unit_06_contact_screening`：接触筛选。
7. `unit_07_training_records`：数据输出。
8. `unit_08_brickmore_model`：BrickMore 模型。

第 4–8 单元保留现有图中的图像和文字，只调整为独立画布，去掉单元之间的连接线。单元内部箭头保留。

`overview.png` 仅供并排审阅；每个单元的独立 PNG 都在本目录。`content/` 可编辑具体布局，`style.tex` 可编辑公共样式，`assets/` 为模型渲染素材。

在本目录执行 `tectonic unit_03_five_levels.tex`（或其他对应文件）即可生成独立矢量 PDF。也可以使用 `pdflatex`。修改后再执行 `pdftoppm -png -singlefile -r 300 unit_03_five_levels.pdf unit_03_five_levels` 导出图片。

这一版是拆分审阅图，原论文及整张 Figure 2 暂保持原样。
''',encoding='utf-8')
print(OUT)
