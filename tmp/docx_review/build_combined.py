from pathlib import Path

source=Path(r'D:\BrickMore\tmp\docx_review\build_flow_version.py').read_text(encoding='utf-8')
prefix=source.split("doc.add_paragraph('BrickMore48 算法流程与关键逻辑','Title')")[0]
exec(compile(prefix,'flow_layout','exec'))
OUT=Path(r'D:\BrickMore\output\documents\BrickMore48_流程图与精简伪代码.docx')
BASE=Path(r'D:\BrickMore\tmp\docx_review\combined')
BASE.mkdir(parents=True,exist_ok=True)
doc.styles['Title'].font.size=Pt(18)
doc.styles['Normal'].paragraph_format.space_after=Pt(4)
doc.styles['Normal'].paragraph_format.line_spacing=1.08
doc.styles['Caption'].paragraph_format.space_after=Pt(5)
doc.styles['Heading 2'].paragraph_format.space_before=Pt(4)
doc.styles['Heading 2'].paragraph_format.space_after=Pt(3)

def pseudo(title,lines):
    doc.add_paragraph(title,'Heading 2')
    for i,(indent,txt) in enumerate(lines,1):
        p=doc.add_paragraph()
        pf=p.paragraph_format;pf.space_before=Pt(0);pf.space_after=Pt(0)
        pf.line_spacing=Pt(12.5);pf.keep_together=True
        pf.keep_with_next=i<len(lines)
        pf.left_indent=Cm(.15+indent*.5)
        r=p.add_run(f'{i:02d}  ')
        r.font.name='Consolas';r.font.size=Pt(9.5)
        r=p.add_run(txt);r.font.size=Pt(10)
        r.font.name='Times New Roman'
        r._element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'SimSun')
    p.paragraph_format.space_after=Pt(5)

doc.add_paragraph('BrickMore48 流程图与精简伪代码','Title')
para('流程图展示主要分支与循环，伪代码保留关键控制逻辑；简单操作直接用文字表达。')
doc.add_paragraph('算法一 文本推理与保形重铺','Heading 1')
para('输入 文本描述与训练好的模型    输出 单连通布局或带状态的失败草稿',small=True)
figure(fig1,'图 1  文本生成与保形重铺流程','生成并选择草稿，清理体素，限时MILP重铺；独立检查通过则导出，未通过则升级预算或保留草稿并换种子。所有尝试未正常结束则记录失败。')
pseudo('Algorithm 1  文本推理与保形重铺',[
 (0,'依次生成候选，遇到正常结束且几何合法的 B 即停止；'),
 (0,'若无合法候选，则选正常结束且错误最少的 B；'),
 (0,'if B 不存在 then return FAILED；'),
 (0,'C ← 清理 B 得到的目标体素；保存原始输出；'),
 (0,'for τ ∈ {12, 60, 180} 秒 do'),
 (1,'B* ← 在 τ 秒内求解精确覆盖 C 且单一凸点连通的布局；'),
 (1,'if B* 存在且独立检查通过 then'),
 (2,'导出 B*；return (B*, SUCCESS)；'),
 (1,'end if'),
 (0,'end for'),
 (0,'保留 B，并提交换种子重生成任务；'),
 (0,'return (B, DRAFT)；')])
para('说明。种子依次为 42、104、2026，正常结束由 EOS 判断。清理包括统一尺寸方向、过滤非法砖型、裁剪越界和合并重叠。独立检查验证砖型、边界、无重叠及覆盖；保形以清理后的 C 为参照。','说明。')
para('采样设置 温度 0.7；top-p 0.9；最多 8192 token；关闭 thinking。',small=True)

doc.add_page_break()
doc.add_paragraph('算法二 局部跨接梁重铺修复','Heading 1')
para('输入 彩色体素模型与时间预算    输出 修复布局或完整覆盖的失败草稿',small=True)
figure(fig2,'图 2  局部跨接修复流程','坐标统一并完整排砖，几何检查未通过时尝试跨接与重铺；连接严格改善才更新并循环。没有改善或预算耗尽后，限时回退并标记结果。')
pseudo('Algorithm 2  局部跨接梁重铺修复',[
 (0,'交换 O 的 y、z，检查边界、颜色及接地；'),
 (0,'if 旧布局已独立验证且改动合规 then return 旧布局；'),
 (0,'(B, C) ← 两种完整同色排砖中较好的布局与目标；'),
 (0,'for 至多 64 轮局部更新 do'),
 (1,'if 局部预算耗尽 or 几何检查通过 then break；'),
 (1,'按优先级尝试跨接梁，拆除相交旧砖并重铺剩余格；'),
 (1,'M ← 首个使连接严格改善的候选的较好重铺方案；'),
 (1,'if M 不存在 then break；'),
 (1,'(B, C) ← M；复查改动限制；'),
 (0,'end for'),
 (0,'if 未通过检查且仍有剩余时间 then'),
 (1,'尝试原优化器，仅接受独立检查合格的回退布局；'),
 (0,'end if'),
 (0,'return (B, C, 成功或失败草稿)；')])
para('判断规则。先减少未接地体素数，其次减少未接地组件数；前两项按顺序比较严格改善才接受。前两项相同的方案，再优先少新增、少用砖。上下相邻层且投影重叠才算凸点连接，侧贴不算。','判断规则。')
para('修复边界。局部搜索用约 82% 的预算；新增限定在原模型一步邻域内且不超过原体素数的 2%，不删除或改色。旧布局或回退若含删除，须满足总改动预算、删除资格及仅新增失败证据。失败草稿也必须完整覆盖目标。','修复边界。')
para('验收区别 算法一要求单连通；算法二允许多个组件分别接地。几何通过不等于物理稳定。',small=True)
para('参考 BrickGPT 论文 arXiv 2505.05469v3 第 5 至 6 页；项目 gen_levels2.py 与 retile_core.py。',small=True)

p=s.footer.paragraphs[0];p.alignment=WD_ALIGN_PARAGRAPH.CENTER
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');p._p.append(fld)
doc.core_properties.title='BrickMore48 流程图与精简伪代码';doc.core_properties.author=''
doc.save(OUT)
print(OUT)
