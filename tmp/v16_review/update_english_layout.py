from pathlib import Path
import re,json,hashlib
P=Path('D:/BrickMore/Essay/BrickMore/V1.6')
main=P/'main.tex';s=main.read_text(encoding='utf-8')
assert hashlib.sha256(main.read_bytes()).hexdigest()=='5569db553c0f739e67edfa7d32b8120c9ecaf6af39e0ccba5001fb2f7271fa87', 'Concurrent main.tex change: review before editing'
s=s.replace('TODO 待用户确认:', 'TODO:').replace('待用户确认 (U3)','Author verification pending (U3)')
s=s.replace(r'\caption{\textbf{BrickForma overview.}',r'\caption{BrickForma overview.')
s=s.replace(r'\caption{\textbf{Data-construction workflow.}',r'\caption{Data-construction workflow.')
s=s.replace('width=0.94\\textwidth','width=\\textwidth').replace('width=0.85\\textwidth','width=\\textwidth').replace('width=0.75\\textwidth','width=\\textwidth')
for n in ['image7','image13','image14','image15','image16','image17','image18','image19','generated_gallery','original_comparison']:
    ext='pdf' if n in ['image14','image17','image19'] else 'png'
    s=s.replace('figures/'+n+'.png','figures/'+n+'_en.'+ext)
s=s.replace(r'\includegraphics[width=0.475\textwidth]{figures/image7_en.png}\hfill'+'\n'+r'\includegraphics[width=0.475\textwidth]{figures/image8.png}',r'\includegraphics[width=\textwidth]{figures/image7_en.png}')
# Preserve the second gallery as its own readable figure.
needle=r'\caption{Voxel model samples spanning the 21 object categories.}'+'\n'+r'\end{figure*}'
s=s.replace(needle,needle+'\n\n'+r'''\begin{figure*}[t]
\centering
\includegraphics[width=0.8\textwidth]{figures/image8.png}
\caption{Additional historical voxel model examples.}
\end{figure*}''')
for n,width in [('image13','0.75'),('image16','0.72')]:
    pat=r'\\begin\{figure\}\[!htbp\]\s*\\centering\s*\\includegraphics\[width=\\columnwidth\]\{figures/'+n+r'_en.png\}(.*?)\\end\{figure\}'
    s=re.sub(pat,lambda m:r'\begin{figure*}[t]'+'\n'+r'\centering'+'\n'+r'\includegraphics[width='+width+r'\textwidth]{figures/'+n+'_en.png}'+m[1]+r'\end{figure*}',s,flags=re.S)
s=s.replace('Historical contact-based gravity screening model (source labels in Chinese are retained).','Historical contact-based gravity screening model, with English labels. The stated contact and ground assumptions are retained.')
s=s.replace('Historical material with Chinese labels; not used for any claim. The figures and tables in this appendix are retained from the supplied reference material. Several figures still contain Chinese labels and use historical versions or criteria; they are not substitutes for the integrated statistics or the current main comparison.','The historical figures and tables in this appendix retain the supplied measurements and model renders, with labels translated into English. They use release-specific versions and criteria and are not substitutes for the integrated statistics or the current main comparison.')
s=s.replace('a library of 20 brick types.','a library of 20 oriented rectangular footprints (11 brick sizes up to planar rotation).')
s=s.replace('20-type library','20-footprint library').replace(r'$\mathcal{L}$ (20 types)',r'$\mathcal{L}$ (20 footprints)')
s=s.replace(r'\STATE $C \gets \mathrm{UnionVoxels}(B;\ \mathcal{L},\ 48^3)$ \COMMENT{clip; overlaps count once}',r'''\STATE $C \gets \mathrm{UnionVoxels}(B;\ \mathcal{L},\ 48^3)$ \COMMENT{clip; overlaps count once}
\IF{$\mathrm{Audit}(B,C)$}
  \RETURN $(B,\ \textsc{Success})$ \COMMENT{valid raw layout}
\ENDIF''')
s=s.replace(r'''  \IF{$B^{*}\neq\emptyset$}
    \STATE $\mathrm{Audit}(B^{*},C)$ \COMMENT{one stud component, $\mathrm{voxels}(B^{*}){=}C$}''',r'''  \IF{$B^{*}\neq\emptyset \land \mathrm{Audit}(B^{*},C)$}''')
s=s.replace('and audits the result independently.','and audits the result independently. The audit requires supported, in-bounds, non-overlapping placements, exact coverage of $C$, and one stud-connected component; a raw layout that already passes is retained.')
# Preserve all diagnostic and significance results supplied by GrokBoT.
for token in ['525','2,240','1,320','920','396,610','2,228,044,818','326 / 133 / 18 / 2']:
    assert token in s,token
main.write_text(s,encoding='utf-8')

for name in ['style.tex','figure1_content.tex','figure2_content.tex']:
    f=P/'figure_tex'/name;t=f.read_text(encoding='utf-8')
    t=re.sub(r'\\fontsize\{([\d.]+)\}\{([\d.]+)\}',lambda m:r'\fontsize{'+str(max(float(m[1]),9.2))+'}{'+str(max(float(m[2]),10.4))+'}',t)
    t=t.replace('BrickMore model generation','BrickForma generation').replace('8/BrickMore model','8/BrickForma')
    if name=='figure1_content.tex':
        t=t.replace('80k source shapes $\\cdot$ 21 categories $\\cdot$ 5 captions','80k shapes $\\cdot$ 21 classes $\\cdot$ 5 captions')
    if name=='figure2_content.tex':
        t=t.replace('From reusable programs to diverse source shapes','Programs $\\rightarrow$ diverse source shapes')
        t=t.replace('Deterministic, parameterized shapes','Parametric programs')
        t=t.replace('Write + run generation code','Write + run generators')
        t=t.replace('Exact + canonical hashing','Exact + canonical hashes')
        t=t.replace('48 axis transforms $\\cdot$ 80k unique','48 transforms $\\cdot$ 80k shapes')
        t=t.replace('MRV / MILP / beam $\\cdot$ $\\leq$2\\% edits','MRV / MILP / beam; $\\leq$2\\% edits')
        t=t.replace('Self-weight LP + layer prefixes','Self-weight LP + prefixes')
        t=t.replace('Round-trip audit + screening status','Audit + screening status')
        t=t.replace('Text $\\rightarrow$ brick sequence + repair','Text $\\rightarrow$ bricks + repair')
        t=t.replace('minimum size=.30cm','minimum size=.34cm')
        a=t.index('% 3. Real voxel image');b=t.index('% 4. Dedup:')
        t=t[:a]+r'''% 3. One source model with five outward caption-level arrows.
\asset{birdhouse_voxels}{11.175}{1.94}{1.15}
\foreach \x/\y/\lab in {10.12/1.40/L1,11.175/1.24/L2,12.28/1.40/L3,12.28/2.44/L4,10.12/2.44/L5} {
  \draw[flow] ($(11.175,1.94)!.54!(\x,\y)$)--($(11.175,1.94)!.84!(\x,\y)$);
  \node[text=accent,font=\bfseries\fontsize{9.2}{10.4}\selectfont] at (\x,\y) {\lab};
}
\node at (11.175,2.94) {Five caption levels};
\node[tinylabel] at (11.175,3.20) {One shared geometry};
''' +t[b:]
    f.write_text(t,encoding='utf-8')

f=P/'archive/historical_tables.tex';t=f.read_text(encoding='utf-8')
t=t.replace(r'\centering\scriptsize',r'\centering\small')
t=t.replace(r'\begin{tabular}{llrrrrr}',r'\setlength{\tabcolsep}{3pt}'+'\n'+r'\begin{tabular}{@{}l>{\raggedright\arraybackslash}p{3.9cm}>{\raggedright\arraybackslash}p{2.5cm}rrrr@{}}')
t=t.replace('Final + prefixes \\', 'Both \\')
t=t.replace('Final and prefix columns report screening outcomes under the stated historical assumptions.','Final and Both columns report final-equilibrium and final-plus-prefix screening passes under the stated historical assumptions.')
t=t.replace('BrickGPT median bricks & BrickNet median parts','GPT median bricks & Net median parts')
f.write_text(t,encoding='utf-8')

repo=P.parents[2]
ret=json.loads((repo/'Train/datasets/retile_assembly_80000/summary.json').read_text(encoding='utf-8'))
rel=json.loads((repo/'Train/datasets/relaxed_assembly_80000/assembly_summary.json').read_text(encoding='utf-8'))
data={'conversion':{'passes':[7902,65503,79298,79301]},'physics':{
 'statuses':['gravity_equilibrium_passed','requires_uncalibrated_clutch','clutch_requirement_inconclusive','global_tipping_or_zero_margin','physics_solver_inconclusive','solver_witness_rejected','not_evaluated_geometry_failed'],
 'labels':['Compression-only balance','Uncalibrated clutch force','Clutch demand unknown','Tipping / zero margin','Solver undetermined','Witness rejected','Geometry failed / not screened'],
 'colors':['#3b914b','#e5a534','#f0d27b','#b54730','#888888','#444444','#c8c8c8'],
 'Relaxed':rel['physicalStatusCounts'],'Retiled':ret['physicsStatusCounts']},
 'provenance':{'conversion':'Historical image14 and release reports; integrated 79,301 is derived, not a new run.',
 'physics_relaxed':'Train/datasets/relaxed_assembly_80000/assembly_summary.json: physicalStatusCounts',
 'physics_retiled':'Train/datasets/retile_assembly_80000/summary.json: physicsStatusCounts',
 'failures':'Counts transcribed from image19; historical run records, not new measurements.'}}
(P/'figure_data/chart_counts.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print('Applied English layout; diagnostic and training counts retained.')
