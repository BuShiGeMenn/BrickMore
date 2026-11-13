from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

BASE=Path(r'D:\BrickMore\tmp\docx_review\english')
BASE.mkdir(parents=True,exist_ok=True)
OUT=Path(r'D:\BrickMore\output\documents\BrickMore48_Flowcharts_and_Pseudocode_EN.docx')
INK='#202020';LINE='#535353';LIGHT='#F4F6F7';WHITE='white'
font_path=r'C:\Windows\Fonts\arial.ttf'
source=Path(r'D:\BrickMore\tmp\docx_review\build_flow_version.py').read_text(encoding='utf-8')
class_source=source[source.index('def font(size)'):source.index('f=Flow(1800,850)')]
exec(compile(class_source,'flow_primitives','exec'))

f=Flow(1800,850)
f.box((30,165,290,265),'Text prompt',True)
f.box((390,165,760,265),'Generate and\nselect a draft')
f.box((860,165,1230,265),'Clean target\nvoxels')
f.box((1330,165,1770,265),'MILP retiling\nwith a time limit')
f.arrow([(290,215),(390,215)]);f.arrow([(760,215),(860,215)])
f.arrow([(1230,215),(1330,215)])
f.diamond((1550,455),'Independent\nchecks pass?')
f.arrow([(1550,265),(1550,375)])
f.box((1290,670,1790,775),'Export successful layout',True)
f.arrow([(1550,535),(1550,670)],'Yes',(1600,595))
f.arrow([(1705,455),(1785,455),(1785,85),(1550,85),(1550,165)],'No; budget remains',(1560,42))
f.box((700,670,1160,775),'Keep the draft;\nqueue a new seed',True)
f.arrow([(1395,455),(930,455),(930,670)],'No; budget exhausted',(1110,415))
f.box((360,440,790,545),'Record generation failure',True)
f.arrow([(575,265),(575,440)],'No normally\nterminated sample',(845,350))
f.txt((410,735),'Shape is preserved relative\nto the cleaned target voxels',size=28)
fig1=f.save('inference_flow_EN.png')

g=Flow(1800,900)
g.box((40,125,370,235),'Colored voxel\nmodel',True)
g.box((490,125,1000,235),'Normalize coordinates;\nbuild a complete tiling')
g.diamond((1350,180),'Geometry\nchecks pass?',rx=180,ry=90)
g.arrow([(370,180),(490,180)]);g.arrow([(1000,180),(1170,180)])
g.box((1580,125,1790,235),'Return\nsuccess',True)
g.arrow([(1530,180),(1580,180)],'Yes',(1555,135))
g.box((1100,370,1600,480),'Try a bridge and\nretile the local region')
g.arrow([(1350,270),(1350,370)],'No',(1400,320))
g.diamond((1350,650),'Connectivity\nstrictly improves?',rx=180,ry=90)
g.arrow([(1350,480),(1350,560)])
g.box((490,595,950,705),'Update the layout;\ncheck repair limits')
g.arrow([(1170,650),(950,650)],'Yes',(1060,605))
g.arrow([(720,595),(720,315),(1090,315),(1090,180),(1170,180)])
g.box((80,600,385,710),'Try fallback;\naudit and label',True)
g.arrow([(1350,740),(1350,830),(230,830),(230,710)],'No improvement or local budget exhausted',(740,785))
g.txt((350,425),'Retain a verified valid baseline',size=28)
g.txt((350,480),'Side contact is not a stud joint',size=28)
fig2=g.save('repair_flow_EN.png')

doc=Document();s=doc.sections[0]
s.page_width=Cm(21);s.page_height=Cm(29.7)
s.top_margin=Cm(1.6);s.bottom_margin=Cm(1.6)
s.left_margin=Cm(2);s.right_margin=Cm(2);s.footer_distance=Cm(.7)
for style in doc.styles:
    for e in list(style.element.iter(qn('w:pBdr'))):e.getparent().remove(e)
for name in ['Normal','Title','Heading 1','Heading 2','Caption']:
    st=doc.styles[name];st.font.name='Times New Roman';st.font.color.rgb=RGBColor(0,0,0)
normal=doc.styles['Normal'];normal.font.size=Pt(10.5)
normal.paragraph_format.line_spacing=1.05;normal.paragraph_format.space_after=Pt(4)
doc.styles['Title'].font.size=Pt(18);doc.styles['Title'].paragraph_format.space_after=Pt(6)
doc.styles['Heading 1'].font.size=Pt(13)
doc.styles['Heading 1'].paragraph_format.space_before=Pt(6)
doc.styles['Heading 1'].paragraph_format.space_after=Pt(5)
doc.styles['Heading 2'].font.size=Pt(11)
doc.styles['Heading 2'].paragraph_format.space_before=Pt(4)
doc.styles['Heading 2'].paragraph_format.space_after=Pt(3)
doc.styles['Caption'].font.size=Pt(9)
doc.styles['Caption'].paragraph_format.space_after=Pt(5)
def para(text,lead=None,small=False):
    p=doc.add_paragraph()
    if lead and text.startswith(lead):p.add_run(lead).bold=True;p.add_run(text[len(lead):])
    else:p.add_run(text)
    if small:
        p.paragraph_format.space_after=Pt(3)
        for r in p.runs:r.font.size=Pt(9)
    return p
def figure(path,caption,alt):
    p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after=Pt(2);p.paragraph_format.keep_with_next=True
    pic=p.add_run().add_picture(str(path),width=Cm(17));pic._inline.docPr.set('descr',alt)
    p=doc.add_paragraph(caption,'Caption');p.alignment=WD_ALIGN_PARAGRAPH.CENTER
def pseudo(title,lines):
    doc.add_paragraph(title,'Heading 2')
    for i,(indent,txt) in enumerate(lines,1):
        p=doc.add_paragraph();pf=p.paragraph_format
        pf.space_before=Pt(0);pf.space_after=Pt(0);pf.line_spacing=Pt(12.5)
        pf.keep_together=True;pf.keep_with_next=i<len(lines);pf.left_indent=Cm(.15+indent*.5)
        r=p.add_run(f'{i:02d}  ');r.font.name='Consolas';r.font.size=Pt(9.5)
        r=p.add_run(txt);r.font.name='Times New Roman';r.font.size=Pt(10)
    p.paragraph_format.space_after=Pt(5)

doc.add_paragraph('BrickMore48 Flowcharts and Pseudocode','Title')
para('Flowcharts show the main branches and loops. Concise pseudocode retains key control logic, with simple operations written in plain language.')
doc.add_paragraph('Algorithm 1  Text Inference and Shape Preserving Retiling','Heading 1')
para('Input  Text prompt and trained model     Output  One stud component, or a labeled draft or failure',small=True)
figure(fig1,'Figure 1  Text generation and shape preserving retiling',
       'Generate and select a draft, clean its voxels, and run MILP retiling. Independent checks lead to success, a larger solver budget, or a retained draft queued for a new seed. No normally terminated sample leads to failure.')
pseudo('Pseudocode 1  Inference and retiling',[
 (0,'Generate candidates in seed order; stop at the first complete, geometrically valid B;'),
 (0,'If none is valid, choose the complete draft B with the fewest errors;'),
 (0,'if B is absent then return FAILED;'),
 (0,'C ← cleaned target voxels of B; save the raw output;'),
 (0,'for τ ∈ {12, 60, 180} seconds do'),
 (1,'B* ← solve an exact cover of C with one stud component within τ seconds;'),
 (1,'if B* exists and passes independent checks then'),
 (2,'Export B*; return (B*, SUCCESS);'),
 (1,'end if'),
 (0,'end for'),
 (0,'Keep B and queue regeneration with a new seed;'),
 (0,'return (B, DRAFT);')])
para('Notes. Seeds are 42, 104, and 2026; complete means normally terminated with EOS. Cleaning normalizes dimension conventions, filters unsupported bricks, clips out-of-bounds cells, and merges overlaps. Independent checks verify the inventory, bounds, absence of overlaps, exact coverage, and stud connectivity. Shape preservation is relative to the cleaned target C.','Notes.')
para('Sampling  Temperature 0.7; top-p 0.9; at most 8192 new tokens; thinking disabled.',small=True)

doc.add_page_break()
doc.add_paragraph('Algorithm 2  Assembly Repair by Local Bridge Retiling','Heading 1')
para('Input  Colored voxel model and time budget     Output  Repaired layout or a full-coverage failure draft',small=True)
figure(fig2,'Figure 2  Local bridge retiling and repair',
       'Normalize coordinates and construct a complete tiling. If geometry checks fail, try bridge retiling and update only on strict connectivity improvement. When no improvement is found or the local budget expires, try the fallback and label the result.')
pseudo('Pseudocode 2  Local bridge retiling',[
 (0,'Swap y and z in O; validate bounds, colors, and ground contact;'),
 (0,'if a baseline is independently verified and repair compliant then return it;'),
 (0,'(B, C) ← the better of two complete monochrome tilings and its target;'),
 (0,'for at most 64 local updates do'),
 (1,'if the local budget is exhausted or geometry checks pass then break;'),
 (1,'Try bridges in priority order; remove intersected bricks and retile the remainder;'),
 (1,'M ← the better variant of the first candidate that strictly improves connectivity;'),
 (1,'if M is absent then break;'),
 (1,'(B, C) ← M; recheck repair limits;'),
 (0,'end for'),
 (0,'if geometry checks still fail and time remains then'),
 (1,'Try the previous optimizer; accept only an independently verified valid fallback;'),
 (0,'end if'),
 (0,'return (B, C, SUCCESS or DRAFT according to the final audit);')])
para('Decision rule. Minimize ungrounded voxel count first, then ungrounded component count; this pair must strictly improve. Ties between variants favor fewer added voxels, then fewer bricks. A stud joint requires overlapping projections in adjacent layers; side contact does not qualify.','Decision rule.')
para('Repair limits. Local search uses about 82% of the budget. Local moves preserve original cells and colors; additions must lie within one grid step of the original model and stay within 2% of its voxel count. Baseline or fallback deletions require a valid total-change budget, deletion eligibility, and evidence of an additions-only failure. Drafts must still cover the entire target.','Repair limits.')
para('Acceptance  Algorithm 1 requires one stud component. Algorithm 2 permits multiple grounded components. Geometry checks do not certify physical stability.',small=True)
para('References  BrickGPT, arXiv 2505.05469v3, pp. 5-6; project files gen_levels2.py and retile_core.py.',small=True)
p=s.footer.paragraphs[0];p.alignment=WD_ALIGN_PARAGRAPH.CENTER
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');p._p.append(fld)
doc.core_properties.title='BrickMore48 Flowcharts and Pseudocode'
doc.core_properties.subject='Text inference and local assembly repair'
doc.core_properties.author=''
doc.save(OUT)
print(OUT)
