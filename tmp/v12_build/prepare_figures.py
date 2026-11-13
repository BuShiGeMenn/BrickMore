from pathlib import Path
import json, shutil, re

ROOT=Path('D:/BrickMore')
DEST=ROOT/'Essay/BrickMore/V1.2'
DATA=DEST/'figure_data'
MESH=DATA/'meshes'
MESH.mkdir(exist_ok=True)
PACKAGE=ROOT/'Deploy/build/comparison_20261110/BrickMoreComparison'
palette=[('3005','1x1','DF4C4C'),('3004','1x2','3D7BCE'),('3622','1x3','E79A34'),
         ('3010','1x4','33A697'),('3009','1x6','9472C7'),('3008','1x8','D6BE39'),
         ('3003','2x2','E37BA7'),('3002','2x3','62BBCB'),('3001','2x4','86AA52'),
         ('2456','2x6','AD7956'),('3007','2x8','687686')]
colors={stem:{'size':size,'hex':'#'+color,'rgb':[int(color[i:i+2],16) for i in (0,2,4)]}
        for stem,size,color in palette}
(DATA/'brick_type_colors.json').write_text(json.dumps(colors,indent=2),encoding='utf-8')
for stem,_,_ in palette:
    shutil.copy2(PACKAGE/'Assets/render_meshes'/f'{stem}.npz',MESH/f'{stem}.npz')
sources={}
for category in ['table','birdhouse','camera','chair','car','vessel']:
    folder=(ROOT/'Train/preview/piano_table_retile/results/A/table/vx80k5p_20261010_A_table_m0001'
            if category=='table' else ROOT/'tmp/teaser_design'/f'{category}_conversion')
    shutil.copy2(folder/'model.ldr',DATA/f'{category}_dataset.ldr')
    shutil.copy2(folder/'source.model.json',DATA/f'{category}_voxels.json')
    sources[category]={'source_voxels':str((folder/'source.model.json').relative_to(ROOT)),
                       'brick_layout':str((folder/'model.ldr').relative_to(ROOT))}
samples=['brickmore__camera_L2_P1_G__raw','brickmore__camera_L2_P1_G__stitched',
         'brickmore__birdhouse-L1__stitched','brickmore__chair-L2V5__raw',
         'brickmore__car-L1V2__stitched','brickmore__vessel_L1_P2_G__stitched']
for sample in samples:
    shutil.copy2(PACKAGE/'Data/assemblies'/f'{sample}.json',DATA/f'{sample}.json')
(DATA/'provenance.json').write_text(json.dumps({'dataset_examples':sources,
    'generated_examples':samples,'assembly_source':str((PACKAGE/'Data/assemblies').relative_to(ROOT)),
    'colors':'Diagnostic brick-type colors, not original voxel colors or model predictions.',
    'rotations':'Rotated copies use the same color (e.g., 1x2 and 2x1).'},indent=2),encoding='utf-8')

renderer=(ROOT/'tmp/teaser_design/render_colored_models.py').read_text(encoding='utf-8')
start=renderer.index('ROOT = ')
end=renderer.index('@njit')
renderer=renderer[:start]+'''ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'figure_data'
OUT = ROOT / 'figures/parts'
OUT.mkdir(parents=True, exist_ok=True)
TYPE_COLORS = json.loads((DATA / 'brick_type_colors.json').read_text(encoding='utf-8'))


'''+renderer[end:]
renderer=renderer.replace("PACKAGE / 'Assets/render_meshes'", "DATA / 'meshes'")
start=renderer.index('def colored_geometry(')
end=renderer.index('def voxel_geometry(')
renderer=renderer[:start]+'''def colored_geometry(assembly):
    all_vertices, all_faces, all_colors = [], [], []
    offset = 0
    for part in assembly['instances']:
        stem = part['part_stem']
        vertices, faces = mesh(stem)
        matrix = np.asarray(part['matrix_ldu'])
        world = vertices @ matrix[:3, :3].T + matrix[:3, 3]
        world[:, 1] *= -1
        # A subpixel visual seam separates adjacent pieces of the same type.
        # Stored assembly coordinates and brick sizes are unchanged.
        center = (world.min(0)+world.max(0))*.5
        world = center + (world-center)*.994
        color = TYPE_COLORS[stem]['rgb']
        all_vertices.append(world)
        all_faces.append(faces+offset)
        all_colors.append(np.tile(color, (len(faces), 1)))
        offset += len(world)
    return np.concatenate(all_vertices), np.concatenate(all_faces), np.concatenate(all_colors)


'''+renderer[end:]
renderer=renderer.replace('def render(name, geometry, size=760):','def render(name, geometry, size=1100):')
start=renderer.index('def main():')
renderer=renderer[:start]+'''def main():
    for category in ['table','birdhouse','camera','chair','car','vessel']:
        render(category+'_voxels', voxel_geometry(DATA / (category+'_voxels.json')))
        render(category+'_dataset', colored_geometry(ldraw(DATA / (category+'_dataset.ldr'))))
    samples = json.loads((DATA/'provenance.json').read_text(encoding='utf-8'))['generated_examples']
    for name in samples:
        assembly = json.loads((DATA/(name+'.json')).read_text(encoding='utf-8'))
        render(name, colored_geometry(assembly))
    (OUT/'render_note.json').write_text(json.dumps({
        'colors':'Fixed per brick type; rotation invariant; see figure_data/brick_type_colors.json',
        'display_colors_are_model_predictions':False,
        'geometry':'Actual source voxel coordinates and exported LDraw part transforms',
        'visual_seam':'0.6 percent per-part shrink for display only; stored geometry unchanged',
        'view':{'azimuth_degrees':42,'elevation_degrees':28},
    },indent=2),encoding='utf-8')


if __name__ == '__main__':
    main()
'''
renderer=renderer.replace('diagnostic per-brick colors','fixed diagnostic brick-type colors')
(DEST/'scripts/render_figure_assets.py').write_text(renderer,encoding='utf-8')

style=r'''\usepackage{graphicx}
\usepackage{tikz}
\usepackage{helvet}
\usepackage{amsmath}
\renewcommand{\familydefault}{\sfdefault}
\usetikzlibrary{arrows.meta,calc,positioning}
\definecolor{ink}{HTML}{222B36}
\definecolor{muted}{HTML}{647180}
\definecolor{line}{HTML}{DCE2E8}
\definecolor{accent}{HTML}{235780}
\definecolor{wash}{HTML}{F0F4F8}
\definecolor{warm}{HTML}{AC6830}
\definecolor{repair}{HTML}{B35845}
\tikzset{every node/.style={inner sep=0pt,text=ink,font=\fontsize{7.4}{9}\selectfont},
  flow/.style={-{Stealth[length=1.5mm,width=1.1mm]},draw=muted,line width=.65pt},
  heading/.style={anchor=west,font=\bfseries\fontsize{9}{10}\selectfont},
  tinylabel/.style={font=\fontsize{6.6}{8}\selectfont,text=muted},
  card/.style={draw=line,line width=.6pt,rounded corners=2pt,fill=white}}
\newcommand{\asset}[4]{\node at (#2,#3) {\includegraphics[width=#4cm]{figures/parts/#1.png}};}
'''
style+='\n'.join(r'\definecolor{brick'+stem+'}{HTML}{'+color+'}' for stem,_,color in palette)+'\n'
(DEST/'figure_tex/style.tex').write_text(style,encoding='utf-8')
for number in (1,2):
    (DEST/f'figure{number}.tex').write_text(r'''\documentclass[border=0pt]{standalone}
\input{figure_tex/style}
\begin{document}
\input{figure_tex/figure'''+str(number)+r'''_content}
\end{document}
''',encoding='utf-8')

f1=r'''% Editable TikZ layout. Units are centimetres; PNG assets contain only model renders.
\begin{tikzpicture}[x=1cm,y=-1cm]
\path[use as bounding box] (0,0) rectangle (17.8,10.15);
\node[heading] at (.08,.20) {(a) Voxel-to-brick construction};
\node[heading] at (12.1,.20) {(b) Connectivity repair};
\draw[line] (11.80,.05)--(11.80,3.30);
'''
top=[('table_voxels',1.4,'Voxels'),('table_dataset',4.20,'Bricks'),
     ('birdhouse_voxels',7.1,'Voxels'),('birdhouse_dataset',9.9,'Bricks'),
     ('brickmore__camera_L2_P1_G__raw',13.28,'Raw'),
     ('brickmore__camera_L2_P1_G__stitched',16.35,'Retiled')]
for name,x,label in top:
    f1+=f'\\node at ({x},.61) {{{label}}};\n\\asset{{{name}}}{{{x}}}{{1.91}}{{2.38}}\n'
for x1,x2 in [(2.68,2.95),(8.38,8.65),(14.60,14.93)]:
    f1+=f'\\draw[flow] ({x1},1.91)--({x2},1.91);\n'
f1+=r'''\node at (2.8,3.24) {Table: 1,117 voxels $\rightarrow$ 197 bricks};
\node at (8.5,3.24) {Birdhouse: 937 voxels $\rightarrow$ 200 bricks};
\node at (14.84,3.24) {Camera: raw $\rightarrow$ retiled};
\draw[line] (.08,3.47)--(17.72,3.47);
\node[anchor=west,tinylabel] at (.12,3.74) {Brick type};
'''
for i,(stem,size,color) in enumerate(palette):
    x=1.63+i*1.36
    f1+=f'\\fill[brick{stem}] ({x},3.62) rectangle ++(.24,.24);\n'
    f1+=f'\\node[anchor=west,font=\\fontsize{{6.6}}{{8}}\\selectfont] at ({x+.32},3.74) {{$'+size.replace('x',r'\!\times\!')+'$};\n'
f1+=r'''\fill[wash,rounded corners=2pt] (.08,4.02) rectangle (17.72,4.78);
\node[anchor=west,text=accent,font=\bfseries\fontsize{8}{9}\selectfont] at (.28,4.24) {Automated dataset construction};
\node[anchor=west,tinylabel] at (.28,4.56) {80k source shapes $\cdot$ 21 categories $\cdot$ 5 captions};
\draw[flow] (7.38,4.4)--(8.12,4.4);
\node[text=accent,font=\bfseries\fontsize{8}{9}\selectfont] at (10.32,4.24) {LoRA training};
\node at (10.32,4.56) {Qwen3-1.7B};
\draw[flow] (12.12,4.4)--(12.88,4.4);
\node[text=accent,font=\bfseries\fontsize{8}{9}\selectfont] at (15.27,4.24) {Text-to-brick pipeline};
\node at (15.27,4.56) {Generate + repair};
\node[heading] at (.08,5.11) {(c) LLM-assisted data distillation};
\node[anchor=east,tinylabel] at (17.72,5.11) {Constructed dataset examples};
'''
for i,cat in enumerate(['birdhouse','camera','chair','car','vessel']):
    x=1.70+i*3.60
    f1+=f'\\asset{{{cat}_dataset}}{{{x}}}{{6.29}}{{2.15}}\n\\node at ({x},7.39) {{{cat.title()}}};\n'
f1+=r'''\draw[line] (.08,7.60)--(17.72,7.60);
\node[heading] at (.08,7.88) {(d) BrickMore model generation};
\node[anchor=east,tinylabel] at (17.72,7.88) {Qwen3-1.7B outputs};
'''
names=[('Birdhouse','brickmore__birdhouse-L1__stitched'),('Camera','brickmore__camera_L2_P1_G__stitched'),
       ('Chair','brickmore__chair-L2V5__raw'),('Car','brickmore__car-L1V2__stitched'),('Vessel','brickmore__vessel_L1_P2_G__stitched')]
for i,(cat,name) in enumerate(names):
    x=1.70+i*3.60
    variant='raw' if name.endswith('__raw') else 'retiled'
    f1+=f'\\asset{{{name}}}{{{x}}}{{8.99}}{{2.04}}\n\\node at ({x},10.07) {{{cat} $\\cdot$ {variant}}};\n'
f1+='\\end{tikzpicture}\n'
(DEST/'figure_tex/figure1_content.tex').write_text(f1,encoding='utf-8')
print('Prepared portable figure sources and renderer:',DEST)
