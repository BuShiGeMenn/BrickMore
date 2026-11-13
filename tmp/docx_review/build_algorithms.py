from pathlib import Path
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

OUT = Path(r'D:\BrickMore\output\documents\BrickMore48_精简算法与逻辑说明.docx')
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.top_margin, sec.bottom_margin = Cm(1.8), Cm(1.8)
sec.left_margin, sec.right_margin = Cm(2.0), Cm(2.0)
sec.footer_distance = Cm(.8)

for name in ['Normal', 'Title', 'Heading 1', 'Heading 2']:
    st = doc.styles[name]
    st.font.name = 'Times New Roman'
    st.font.color.rgb = RGBColor(0,0,0)
    st.element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'), 'SimSun')
for st in doc.styles:
    for border in list(st.element.iter(qn('w:pBdr'))):
        border.getparent().remove(border)
doc.styles['Normal'].font.size = Pt(10.5)
doc.styles['Normal'].paragraph_format.line_spacing = 1.15
doc.styles['Normal'].paragraph_format.space_after = Pt(5)
doc.styles['Title'].font.size = Pt(19)
doc.styles['Title'].paragraph_format.space_after = Pt(9)
doc.styles['Heading 1'].font.size = Pt(13)
doc.styles['Heading 1'].paragraph_format.space_before = Pt(8)
doc.styles['Heading 1'].paragraph_format.space_after = Pt(6)
doc.styles['Heading 2'].font.size = Pt(11)
doc.styles['Heading 2'].paragraph_format.space_before = Pt(7)
doc.styles['Heading 2'].paragraph_format.space_after = Pt(4)

def body(text, lead=None):
    p = doc.add_paragraph()
    if lead and text.startswith(lead):
        p.add_run(lead).bold = True
        p.add_run(text[len(lead):])
    else:
        p.add_run(text)
    return p

def small(text):
    p=doc.add_paragraph(text)
    for r in p.runs:r.font.size=Pt(9)
    p.paragraph_format.space_after=Pt(3)
    return p

def algorithm(title, inputs, outputs, lines):
    p = doc.add_paragraph()
    p.paragraph_format.keep_with_next=True
    p.paragraph_format.space_after=Pt(4)
    r=p.add_run(title);r.bold=True;r.font.size=Pt(11)
    for label, txt in [('Input',inputs),('Output',outputs)]:
        p=doc.add_paragraph()
        p.paragraph_format.space_after=Pt(2)
        p.paragraph_format.keep_with_next=True
        p.add_run(label+': ').bold=True
        p.add_run(txt)
    for i,(indent,line) in enumerate(lines,1):
        p=doc.add_paragraph()
        pf=p.paragraph_format
        pf.space_before=Pt(0);pf.space_after=Pt(0)
        pf.line_spacing=Pt(12.5)
        pf.keep_with_next=i<len(lines)
        pf.keep_together=True
        r=p.add_run(f'{i:2d}  '+ '    '*indent+line)
        r.font.name='Consolas';r.font.size=Pt(9.5)
        r._element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'SimSun')
    p=doc.add_paragraph()
    p.paragraph_format.space_after=Pt(0)
    p.paragraph_format.line_spacing=Pt(3)
    p.add_run(' ').font.size=Pt(3)

def math_run(parent,text):
    r=OxmlElement('m:r'); t=OxmlElement('m:t');t.set(qn('xml:space'),'preserve');t.text=text;r.append(t);parent.append(r)

def sub(parent,base,index):
    s=OxmlElement('m:sSub');e=OxmlElement('m:e');math_run(e,base)
    su=OxmlElement('m:sub');math_run(su,index);s.append(e);s.append(su);parent.append(s)

doc.add_paragraph('BrickMore48 精简算法与逻辑说明', 'Title')
body('本文给出文本推理与局部装配修复两段精简伪代码，并用正文说明采样规则、连接判定和失败处理。算法框保留主要控制流程，参数和子过程定义移入文字说明；两种算法采用不同的几何验收条件。')
doc.add_paragraph('算法一 文本推理与保形重铺', 'Heading 1')
algorithm('Algorithm 1  BrickMore48 inference with shape preserving retiling',
          'Text prompt c; model θ; seeds S; solver budgets T',
          'Brick structure B and status', [
(0,'B ← SampleAndSelect(θ, c, S);'),
(0,'if B = ∅ then return (∅, FAILED);'),
(0,'C ← CanonicalVoxels(B);'),
(0,'SaveRaw(B);'),
(0,'for τ ∈ T do'),
(1,'B* ← SingleStudCover(C, τ);'),
(1,'if B* ≠ ∅ and AuditSingleStud(B*, C) then'),
(2,'Export(B*);'),
(2,'return (B*, SUCCESS);'),
(1,'end if'),
(0,'end for'),
(0,'EnqueueReseed(c);'),
(0,'return (B, DRAFT);')])
body('采样与草稿选择。依次使用种子 S = {42, 104, 2026} 生成完整砖块序列，优先接受以 EOS 正常结束且几何合法的结果；若不存在，则从正常结束的结果中选择几何错误最少者。所有尝试均未正常结束时返回失败。采样温度为 0.7，top-p 为 0.9，输出上限为 8192 token，并关闭 thinking。正常结束不等于形状或语义完整。', '采样与草稿选择。')
body('保形重铺。CanonicalVoxels 统一尺寸约定，过滤不支持的砖型，裁剪越界部分并合并重复占用，得到目标体素集合 C。求解预算依次为 12、60、180 秒。MILP 在砖型白名单内寻找精确覆盖 C 的布局，要求每个目标格恰好覆盖一次，且全部砖块构成单一真实凸点连通分量。', '保形重铺。')
body('验收与失败处理。独立审计检查砖型、边界、无重叠、精确覆盖及单连通；通过后再作为成功结果导出。预算耗尽仍未通过时，保留草稿并提交换种子重生成任务。“保形”以清理后的 C 为参照；入队表示后续任务，当前调用仍返回 DRAFT。', '验收与失败处理。')

doc.add_page_break()
doc.add_paragraph('算法二 局部跨接梁重铺修复', 'Heading 1')
algorithm('Algorithm 2  Brick assembly repair by local bridge retiling',
          'Voxel model O; time budget t; optional baseline Y',
          'Layout B, target C, and status', [
(0,'O ← NormalizeAndValidate(O);'),
(0,'if VerifiedBaseline(Y, O) then return Result(Y);'),
(0,'(B, C) ← InitialCover(O);'),
(0,'while WithinLocalBudget(t) do'),
(1,'if AuditGrounded(B, C) then break;'),
(1,'A ← RankedBridges(B, C, O);'),
(1,'M ← FirstImprovingRetile(B, C, A, O);'),
(1,'if M = ∅ then break;'),
(1,'(B, C) ← M;'),
(1,'assert RepairAudit(O, C);'),
(0,'end while'),
(0,'if not AuditGrounded(B, C) and TimeRemaining(t) then'),
(1,'(B, C) ← AuditedFallback(O, B, C);'),
(0,'end if'),
(0,'return Result(B, C, AuditGrounded(B, C));')])
body('初始化与连接判定。输入由 Y-up 转为内部 Z-up，即 (x, y, z) → (x, z, y)，再验证边界、颜色与接地。Y 必须独立验证通过且满足改动约束；若含删除，还需真实的仅新增修复失败证据。否则生成两种方向偏好的同色完整覆盖，按下述目标的字典序选取较好者。连接图以砖块为节点，仅将上下相邻层且水平投影重叠的砖连边；侧面接触不算凸点连接。', '初始化与连接判定。')
p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before=Pt(3);p.paragraph_format.space_after=Pt(5)
om=OxmlElement('m:oMath');math_run(om,'F(B, C) = (');sub(om,'U','v');math_run(om,'(B), ');sub(om,'U','c');math_run(om,'(B), |C ∖ O|, |B|)');p._p.append(om)
body('目标元组前两项分别为未接地体素数和组件数，后两项为新增体素数和砖块数。仅当前两项构成的元组严格减小时才接受局部动作；前两项相同的候选再比较后两项。')
body('跨接与局部重铺。在未接地组件附近，优先尝试零新增候选，再尝试少量局部新增。候选梁必须满足砖型、边界及同色要求。放置时移除与其相交的旧砖，并完整重铺剩余体素。按候选优先级找到首个改善候选，比较其两种重铺变体。每次更新均复查原色、一步邻域内新增及 2% 总改动预算。', '跨接与局部重铺。')
body('预算与返回。局部搜索使用约 82% 的时间预算，最多更新 64 次；剩余时间尝试旧优化器回退，只有独立审计通过的回退结果才替换当前布局。Result 返回成功或完整覆盖的失败草稿。Algorithm 2 允许多个组件分别接地，Algorithm 1 要求单一凸点连通分量；两者的几何通过均不等于物理稳定性通过。', '预算与返回。')
doc.add_paragraph('参考依据', 'Heading 2')
small('[1] BrickGPT 论文 arXiv 2505.05469v3，第 5 至 6 页，第 4.2 节与 Algorithm 1。')
small('[2] 项目实现 brickmore48_tools/pipeline/gen_levels2.py 与 Train/algorithms/voxel_assembly_retile/retile_core.py。')

footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)
doc.core_properties.title='BrickMore48 精简算法与逻辑说明'
doc.core_properties.subject='文本推理与局部装配修复算法'
doc.core_properties.author=''
OUT.parent.mkdir(parents=True,exist_ok=True)
doc.save(OUT)
print(OUT)
