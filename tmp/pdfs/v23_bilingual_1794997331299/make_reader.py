from pathlib import Path
import json,re
from collections import Counter
from extract import ROOT,HERE,sentences,block
items=json.loads((HERE/'items.json').read_bytes())
units=['']+json.loads((HERE/'units.json').read_bytes())
zh={}
for f in sorted(HERE.glob('zh*.txt')):
    for line in f.read_text(encoding='utf8').splitlines():
        if not line.strip():continue
        k,t=line.split(' ',1);k=int(k)
        assert k not in zh
        zh[k]=t.replace('%',r'\%')
# A commented-out citation lies inside this sentence in the English TeX source.
assert units[19].endswith('through') and units[20].startswith('paper folding')
units[19]+=' '+units[20]
zh[103]=zh[103].replace('该批次','B 批次')
preamble=r"""% !TeX program = lualatex
% V2.3 sentence-aligned reading copy. Build in the V2.3 project with LuaLaTeX twice.
\documentclass[11pt,letterpaper]{article}
\usepackage[margin=0.83in,top=0.68in,bottom=0.72in,footskip=23pt]{geometry}
\usepackage{fix-cm,fontspec}
\IfFileExists{C:/Windows/Fonts/times.ttf}{
  \setmainfont{times.ttf}[Path=C:/Windows/Fonts/,BoldFont=timesbd.ttf,ItalicFont=timesi.ttf,BoldItalicFont=timesbi.ttf]
}{}
\IfFileExists{C:/Windows/Fonts/simsun.ttc}{
  \newfontfamily\chinesefont{simsun.ttc}[Path=C:/Windows/Fonts/,FontIndex=0,AutoFakeBold=1.5]
}{\newfontfamily\chinesefont{FandolSong-Regular.otf}[BoldFont=FandolSong-Bold.otf]}
\usepackage{graphicx,booktabs,array,amsmath,algorithm,algorithmic,caption,float,xcolor}
\usepackage[authoryear]{natbib}
\bibpunct{(}{)}{;}{a}{}{,}
\let\cite\citep
\usepackage[hyphens]{url}
\urlstyle{rm}
\definecolor{translation}{HTML}{20454B}
\definecolor{muted}{HTML}{435660}
\frenchspacing
\setlength{\parindent}{0pt}
\setlength{\parskip}{0pt}
\setlength{\emergencystretch}{2em}
\DeclareMathSizes{10.5}{10}{7}{5}
\renewcommand{\topfraction}{0.9}
\renewcommand{\bottomfraction}{0.85}
\renewcommand{\textfraction}{0.08}
\captionsetup{font=small,labelfont=bf,justification=raggedright,singlelinecheck=false}
\raggedbottom
% Insert legal breakpoints between Chinese characters and avoid leaving closing
% punctuation at the beginning of a line. Latin text and mathematics are untouched.
\directlua{
  local glyph=node.id("glyph")
  local function han(c) return (c>=0x2E80 and c<=0x9FFF) or (c>=0xFF00 and c<=0xFFEF) or (c>=0x2010 and c<=0x203F) end
  local closing={[0xFF0C]=true,[0x3002]=true,[0xFF1F]=true,[0xFF01]=true,[0xFF1B]=true,[0xFF1A]=true,[0x3001]=true,[0xFF09]=true,[0x201D]=true,[0x300B]=true}
  local opening={[0xFF08]=true,[0x201C]=true,[0x300A]=true}
  luatexbase.add_to_callback("pre_linebreak_filter", function(head)
    for n in node.traverse_id(glyph,head) do
      local p=n.prev
      if p and p.id==glyph and han(p.char) and han(n.char) and not opening[p.char] and not closing[n.char] then
        head=node.insert_before(head,n,node.new("glue"))
      end
    end
    return head
  end,"brickforma.chinese.linebreaks")
}
\newcommand{\zh}[1]{{\chinesefont #1}}
\newcommand{\pair}[2]{\par\addvspace{4pt}\noindent
  \begin{minipage}{\linewidth}\raggedright
  #1\par\nobreak\vspace{1pt}
  {\color{translation}\chinesefont\fontsize{10.5}{15.3}\selectfont #2\par}
  \end{minipage}\par}
\newcommand{\readinghead}[2]{\par\addvspace{9pt}\noindent\textbf{#1}\enspace
  {\color{translation}\zh{#2}}\par\nobreak}
"""
original_aux=(Path("D:/BrickMore/tmp/pdfs/v23_compile_1794996227397/main.aux")).read_text(encoding='utf8')
citations=re.findall(r'^\\bibcite[^\n]+',original_aux,flags=re.M)
assert len(citations)==15
# Page and figure numbers for material outside this main-text reading copy
# follow the original PDF. Local section/figure/table numbers are live references.
labels=dict(re.findall(r'\\newlabel\{([^}]+)\}\{\{([^}]+)\}',original_aux))
extern=['app:dataset','app:training','app:eval','fig:comparison-zero-invalid',
        'fig:comparison-means','fig:comparison-distributions','fig:comparison-levels']
out=[preamble, r'\makeatletter']
for k in extern:
    out.append(r'\expandafter\def\csname r@'+k+r'\endcsname{{'+labels[k]+r'}{}{ }{}{}}')
out.extend(citations)
out.extend([r'\makeatother', r'\begin{document}',r"""\begin{center}
{\Large\bfseries BrickForma: Crystallizing LLM Geometric Knowledge\\into Small Models for Text-to-Brick Assembly\par}
\vspace{5pt}{\large\chinesefont BrickForma：将大语言模型的几何知识凝练到用于文本生成积木拼装体的小模型中\par}
\vspace{5pt}{\small Anonymous submission \enspace/\enspace \zh{匿名投稿}\par}
{\small\color{muted} V2.3\enspace\zh{正文逐句中英对照}\par}
\end{center}"""])
paired=[]
display=[]
def with_zh(kind,ids):
    first=ids[0]
    if kind in ('p','note'):
        for i in ids:
            if i==20:continue
            assert zh[i]!='@JOIN'
            out.append(r'\pair{'+units[i]+'}{'+zh[i]+'}')
            paired.append(i)
    else:
        assert len(ids)==1
        k={'abstract':'section*','section':'section','subsection':'subsection'}.get(kind)
        if k:
            if first==172:out.append(r'\clearpage')
            out.append('\\'+k+'{'+units[first]+r'\enspace\zh{'+zh[first]+'}}')
        else:out.append(r'\readinghead{'+units[first]+'}{'+zh[first]+'}')
        paired.append(first)
for item in items:
    k=item['kind']
    if k=='bibliography':break
    if k in ('teaser','figure','table','algorithm'):
        ids=item['ids'];display.extend(ids)
        if k=='teaser':
            cap=' '.join(units[i] for i in ids)
            out.append(r'\begin{center}\includegraphics[width=0.77\linewidth]{figure1.pdf}\captionof{figure}{'+cap+r'}\label{fig:teaser}\end{center}')
        elif k=='figure' and item['label']=='fig:data-workflow':
            cap=' '.join(units[i] for i in ids)
            out.append(r'\begin{figure}[!htbp]\centering\includegraphics[width=\linewidth]{figure2.pdf}\caption{'+cap+r'}\label{fig:data-workflow}\end{figure}')
        else:
            raw=item['raw'].replace('{figure*}','{figure}').replace('{table*}','{table}')
            raw=re.sub(r'(\\begin\{(?:figure|algorithm|table)\})\[[^]]*\]',r'\1[!htbp]',raw)
            raw=raw.replace(r'\includegraphics[width=\textwidth]',r'\includegraphics[width=0.92\linewidth,height=.53\textheight,keepaspectratio]')
            out.append(raw)
    elif k=='label':out.append(item['raw'])
    else:with_zh(k,item['ids'])
out.extend([r'\clearpage',r'\end{document}'])
assert set(range(1,180))==set(paired)|set(display)|{20}
assert not set(paired)&set(display)
text='\n\n'.join(out)
assert '@JOIN' not in text and r'\section{Technical Appendix' not in text
# Source citations and numbers in each English sentence are copied directly.
for i in paired:assert units[i] in text
(HERE/'main-bilingual.tex').write_text(text+'\n',encoding='utf8')
print('Translated prose sentences',text.count(r'\pair{'), 'sentences/headings',len(paired),'original caption units',len(display))
