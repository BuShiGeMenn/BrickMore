from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

BASE=Path(r'D:\BrickMore\tmp\docx_review\flow_version')
BASE.mkdir(parents=True,exist_ok=True)
OUT=Path(r'D:\BrickMore\output\documents\BrickMore48_算法流程图简版.docx')
INK='#202020'; LINE='#535353'; LIGHT='#F4F6F7'; WHITE='white'
font_path=r'C:\Windows\Fonts\msyh.ttc'
def font(size): return ImageFont.truetype(font_path,size)

class Flow:
    def __init__(self,w,h):
        self.im=Image.new('RGB',(w,h),'white');self.d=ImageDraw.Draw(self.im)
    def txt(self,xy,text,size=34,fill=INK):
        self.d.multiline_text(xy,text,font=font(size),anchor='mm',align='center',spacing=9,fill=fill)
    def box(self,rect,text,terminal=False):
        self.d.rounded_rectangle(rect,radius=36 if terminal else 12,fill=WHITE if terminal else LIGHT,outline=LINE,width=3)
        x1,y1,x2,y2=rect;self.txt(((x1+x2)/2,(y1+y2)/2),text)
    def diamond(self,center,text,rx=155,ry=80):
        x,y=center;self.d.polygon([(x-rx,y),(x,y-ry),(x+rx,y),(x,y+ry)],fill=WHITE,outline=LINE,width=3)
        self.txt(center,text,size=32)
    def arrow(self,points,label=None,pos=None):
        self.d.line(points,fill=LINE,width=3,joint='curve')
        (x0,y0),(x1,y1)=points[-2:]
        import math
        a=math.atan2(y1-y0,x1-x0);length=15
        self.d.polygon([(x1,y1),(x1-length*math.cos(a-.45),y1-length*math.sin(a-.45)),(x1-length*math.cos(a+.45),y1-length*math.sin(a+.45))],fill=LINE)
        if label and pos:self.txt(pos,label,size=27)
    def save(self,name):
        p=BASE/name;self.im.save(p,dpi=(300,300));return p

f=Flow(1800,850)
f.box((30,165,290,265),'输入文本描述',True)
f.box((390,165,760,265),'生成并选择草稿')
f.box((860,165,1230,265),'清理目标体素')
f.box((1330,165,1770,265),'限时 MILP 重铺')
f.arrow([(290,215),(390,215)])
f.arrow([(760,215),(860,215)])
f.arrow([(1230,215),(1330,215)])
f.diamond((1550,455),'独立检查\n通过了吗')
f.arrow([(1550,265),(1550,375)])
f.box((1290,670,1790,775),'导出成功结果',True)
f.arrow([(1550,535),(1550,670)],'是',(1590,595))
f.arrow([(1705,455),(1785,455),(1785,85),(1550,85),(1550,165)],'否且还有预算',(1560,42))
f.box((700,670,1160,775),'保留草稿\n换种子重新生成',True)
f.arrow([(1395,455),(930,455),(930,670)],'否且预算耗尽',(1110,415))
f.box((360,440,790,545),'记录生成失败',True)
f.arrow([(575,265),(575,440)],'所有尝试均未正常结束',(845,350))
f.txt((470,735),'保形参照清理后的目标体素',size=28)
fig1=f.save('inference_flow.png')

g=Flow(1800,900)
g.box((40,125,370,235),'输入彩色体素',True)
g.box((490,125,1000,235),'统一坐标并完整排砖')
g.diamond((1350,180),'几何检查\n通过了吗',rx=180,ry=90)
g.arrow([(370,180),(490,180)])
g.arrow([(1000,180),(1170,180)])
g.box((1580,125,1790,235),'成功返回',True)
g.arrow([(1530,180),(1580,180)],'是',(1555,135))
g.box((1100,370,1600,480),'尝试跨接并局部重铺')
g.arrow([(1350,270),(1350,370)],'否',(1390,320))
g.diamond((1350,650),'连接严格\n改善了吗',rx=180,ry=90)
g.arrow([(1350,480),(1350,560)])
g.box((490,595,950,705),'更新布局并复查改动')
g.arrow([(1170,650),(950,650)],'是',(1060,605))
g.arrow([(720,595),(720,315),(1090,315),(1090,180),(1170,180)])
g.box((80,600,385,710),'限时回退\n检查并标记结果',True)
g.arrow([(1350,740),(1350,830),(230,830),(230,710)],'无改善或搜索预算耗尽',(740,785))
g.txt((350,425),'优先保留已经验证合格的旧布局',size=28)
g.txt((350,480),'侧面贴合不算凸点连接',size=28)
fig2=g.save('repair_flow.png')

doc=Document()
s=doc.sections[0];s.page_width=Cm(21);s.page_height=Cm(29.7)
s.top_margin=Cm(1.6);s.bottom_margin=Cm(1.6);s.left_margin=Cm(2);s.right_margin=Cm(2)
s.footer_distance=Cm(.7)
for style in doc.styles:
    for e in list(style.element.iter(qn('w:pBdr'))):e.getparent().remove(e)
for name in ['Normal','Title','Heading 1','Heading 2','Caption']:
    st=doc.styles[name];st.font.name='Times New Roman';st.font.color.rgb=RGBColor(0,0,0)
    st.element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'SimSun')
normal=doc.styles['Normal'];normal.font.size=Pt(10.5)
normal.paragraph_format.line_spacing=1.14;normal.paragraph_format.space_after=Pt(6)
doc.styles['Title'].font.size=Pt(19);doc.styles['Title'].paragraph_format.space_after=Pt(7)
doc.styles['Heading 1'].font.size=Pt(13);doc.styles['Heading 1'].paragraph_format.space_before=Pt(8);doc.styles['Heading 1'].paragraph_format.space_after=Pt(6)
doc.styles['Heading 2'].font.size=Pt(11);doc.styles['Heading 2'].paragraph_format.space_before=Pt(7);doc.styles['Heading 2'].paragraph_format.space_after=Pt(4)
doc.styles['Caption'].font.size=Pt(9)
doc.styles['Caption'].paragraph_format.space_after=Pt(8)
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
    shape=p.add_run().add_picture(str(path),width=Cm(17))
    shape._inline.docPr.set('descr',alt)
    p=doc.add_paragraph(caption,'Caption');p.alignment=WD_ALIGN_PARAGRAPH.CENTER

doc.add_paragraph('BrickMore48 算法流程与关键逻辑','Title')
para('两段算法分别完成文本生成后的保形重铺，以及已有体素模型的局部装配修复。流程图呈现主要判断与循环，具体操作用文字说明。')
doc.add_paragraph('算法一 文本推理与保形重铺','Heading 1')
para('输入 文本描述与训练好的模型    输出 单连通布局或带失败标记的草稿',small=True)
figure(fig1,'图 1  文本生成与保形重铺流程','文本描述经过生成与草稿选择、体素清理和限时MILP重铺。检查通过则导出；未通过时升级预算，耗尽后保留草稿并换种子。所有生成均未正常结束则记录失败。')
para('1  生成与选择。依次使用种子 42、104、2026，优先保留正常结束且几何合法的结果；若三次均未得到此类结果，则从正常结束的候选中选择错误最少者。所有尝试均未正常结束时记录失败。正常结束由 EOS 判断，不等同于语义完整。','1  生成与选择。')
para('2  清理与重铺。统一砖块尺寸的方向约定，过滤不支持的砖型、裁剪越界部分并合并重叠格，得到目标体素集合。随后依次使用 12、60、180 秒预算，重新划分砖块，但保持目标体素集合不变。','2  清理与重铺。')
para('3  检查与返回。独立检查砖型、边界、无重叠、完整覆盖和单一凸点连通。检查通过后导出；否则继续尝试更长预算，全部耗尽后保留原始草稿并提交换种子重生成任务。','3  检查与返回。')
para('必要约束。每个目标格恰好由一块砖覆盖，所有砖块属于同一真实凸点连通分量。“保形”相对清理后的目标体素定义，不能据此保证原始非法布局或提示词语义不变。','必要约束。')
para('采样设置 温度 0.7；top-p 0.9；最多 8192 token；关闭 thinking。',small=True)

doc.add_page_break()
doc.add_paragraph('算法二 局部跨接梁重铺修复','Heading 1')
para('输入 彩色体素模型与搜索预算    输出 修复后的布局或完整覆盖的失败草稿',small=True)
figure(fig2,'图 2  局部跨接修复流程','体素经坐标统一与完整排砖后进行几何检查。未通过则尝试跨接与局部重铺；严格改善连接才更新并复查。无改善或搜索预算耗尽后限时回退并标记结果。已验证合格的旧结果直接保留。')
para('1  初始化。将 Y-up 转为内部 Z-up，即交换原坐标的 y、z，再检查边界、颜色与接地。已有布局独立检查合格且改动合规时直接保留；否则生成两种方向偏好的同色完整排砖，选取较好者。','1  初始化。')
para('2  跨接与重铺。在未接地组件附近尝试同色桥梁，优先零新增，再尝试少量局部新增。放入桥梁前，拆除与其相交的旧砖，并把旧砖剩余的格子重新完整排砖，避免重叠与缺失。','2  跨接与重铺。')
para('3  接受与循环。优先减少未接地体素数，其次减少未接地组件数；只有这两项按先后顺序比较得到严格改善，才接受动作。按候选顺序选择首个改善候选，比较其两种重铺方案；前两项相同的方案再优先少新增、少用砖。每次更新后复查改动限制并重新检查连接。','3  接受与循环。')
para('4  停止与返回。局部搜索使用约 82% 的预算，最多更新 64 次。无改善或预算耗尽后，用剩余时间尝试原优化器；只有独立检查通过的回退结果才替换当前布局。最终明确标记成功或失败草稿，失败也必须完整覆盖目标。','4  停止与返回。')
para('必要约束。上下相邻层且水平投影重叠才形成凸点连接，侧面贴合不算连接。局部动作不删除或改色，新增格限定在原模型一步邻域内且不超过原体素数的 2%；旧布局或回退若含删除，须满足总改动预算、删除资格及仅新增修复失败证据。','必要约束。')
para('验收区别。本算法允许多个组件分别接地；算法一要求单一凸点连通分量。两者的几何通过均不等于物理稳定性通过。','验收区别。')
para('参考 BrickGPT 论文 arXiv 2505.05469v3 第 5 至 6 页；项目 gen_levels2.py 与 retile_core.py。',small=True)

p=s.footer.paragraphs[0];p.alignment=WD_ALIGN_PARAGRAPH.CENTER
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');p._p.append(fld)
doc.core_properties.title='BrickMore48 算法流程与关键逻辑';doc.core_properties.author=''
doc.save(OUT)
print(OUT)
