from pathlib import Path
import re, json
ROOT = Path("D:/BrickMore/Essay/BrickMore/V2.3")
HERE = Path(__file__).resolve().parent
def content(file):
    s=(ROOT/file).read_text(encoding='utf-8-sig')
    return '\n'.join(re.split(r'(?<!\\)%',line,1)[0] for line in s.splitlines())
def block(s,i):
    assert s[i]=='{'
    depth=0
    for j in range(i,len(s)):
        if j and s[j-1]=='\\':continue
        depth+=(s[j]=='{')-(s[j]=='}')
        if not depth:return s[i+1:j],j+1
    raise ValueError(s[i:])
def expand(s):
    return re.sub(r'\\input\{([^}]+)\}',lambda m:expand(content(m[1]+'.tex')), s)
def sentences(s):
    s=' '.join(s.split()).strip()
    s=s.replace(r'.\textquotedblright\ ',r'.\textquotedblright{} ')
    cuts=re.split(r"(?<=[.!?])(?:\s+)|(?<=\.\\textquotedblright\{\})\s+",s)
    return [t for t in cuts if t]
units=[]
items=[]
def parts(s):
    ids=[]
    for sentence in sentences(s):
        ids.append(len(units)+1)
        units.append(sentence)
    return ids
def heading(kind,s):
    items.append(dict(kind=kind,ids=[len(units)+1]))
    units.append(s)
def prose(s):
    s=' '.join(s.split())
    if not s:return
    if s.startswith((r'\textbf{',r'\emph{')):
        t,end=block(s,s.index('{'))
        if t.endswith('.') and (end==len(s) or s[end]==' '):
            heading('subhead',t)
            s=s[end:].strip()
    if r'\footnote{' in s:
        i=s.index(r'\footnote{')
        note,end=block(s,s.index('{',i))
        prose(s[:i]); items.append(dict(kind='note',ids=parts(note))); prose(s[end:]);return
    if s:items.append(dict(kind='p',ids=parts(s)))
def body(s):
    lines=s.splitlines()
    i=0
    buf=[]
    def flush():
        prose(' '.join(buf));buf.clear()
    while i<len(lines):
        t=lines[i].strip();i+=1
        if not t:flush();continue
        for k in ('figure','table','algorithm'):
            if re.match(r'\\begin\{'+k+r'\*?\}',t):
                flush()
                data=[t]
                while not re.match(r'\\end\{'+k+r'\*?\}',data[-1]):
                    data.append(lines[i].strip());i+=1
                raw='\n'.join(data)
                m=re.search(r'\\caption\{',raw); caption,end=block(raw,m.end()-1)
                label=re.search(r'\\label\{(.*?)\}',raw)
                items.append(dict(kind=k,ids=parts(caption),raw=raw,label=label[1] if label else ''))
                break
        else:
            if t==r'\maketitle':
                flush()
                raw=content('figure_tex/teaser.tex');start=raw.index(r'\captionof{figure}{')+len(r'\captionof{figure}')
                items.append(dict(kind='teaser',ids=parts(block(raw,start)[0]),label='fig:teaser'))
            elif t==r'\begin{abstract}':flush();heading('abstract','Abstract')
            elif t in (r'\end{abstract}',r'\begin{samepage}',r'\end{samepage}',r'\FloatBarrier',r'\end{document}'):flush()
            elif t in (r'\appendix',r'\bibliography{references}'):flush();items.append(dict(kind='appendix' if t==r'\appendix' else 'bibliography'))
            elif t.startswith(r'\label{'):flush();items.append(dict(kind='label',raw=t))
            elif (m:=re.match(r'\\(section|subsection|paragraph)\{',t)):
                flush();title,end=block(t,m.end()-1);heading(m[1],title)
                if t[end:].strip():buf.append(t[end:].strip())
            else:buf.append(t)
    flush()
source=expand(content('main.tex').split(r'\begin{document}',1)[1])
body(source)
(HERE/'items.json').write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf8')
(HERE/'units.json').write_text(json.dumps(units,ensure_ascii=False,indent=2),encoding='utf8')
(HERE/'units.txt').write_text('\n'.join(f'{i:03d} {s}' for i,s in enumerate(units,1)),encoding='utf8')
print(len(items),len(units))

