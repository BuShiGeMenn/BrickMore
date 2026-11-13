"""Warm the local Tectonic cache from byte ranges in its own verified bundle index."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import urllib.request, os

base=Path('D:/BrickMore/tmp/v12_build/tectonic_cache/bundles/data')
index=next(base.glob('*.index'))
cache=base/index.stem
names='''times.sty xspace.sty dvipsnam.def amsmath.sty amstext.sty amsgen.sty amsbsy.sty amsopn.sty amssymb.sty amsfonts.sty booktabs.sty natbib.sty silence.sty etoolbox.sty caption.sty caption3.sty subcaption.sty url.sty enumitem.sty hyperref.sty hyperref.cfg hpdftex.def hxetex.def pd1enc.def puenc.def pdfescape.sty hycolor.sty letltxmacro.sty auxhook.sty kvsetkeys.sty kvdefinekeys.sty pdftexcmds.sty infwarerr.sty ltxcmds.sty iftex.sty kvoptions.sty intcalc.sty bigintcalc.sty etexcmds.sty bitset.sty rerunfilecheck.sty uniquecounter.sty refcount.sty gettitlestring.sty nameref.sty array.sty placeins.sty helvet.sty fontenc.sty t1enc.def l3backend-xetex.def epstopdf-base.sty grfext.sty pdftex.map texglyphlist.txt pdfglyphlist.txt glyphlist.txt 8r.enc'''.split()
entries=[]
for line in index.read_text().splitlines():
    f=line.split()
    if len(f)!=3: continue
    name,offset,length=f[0],int(f[1]),int(f[2])
    pick=(name in names or name.startswith(('pgf','tikz','t1phv','t1ptm','ot1ptm','ot1phv','ts1phv','ts1ptm'))
          or (name.startswith(('phv','ptm','uhv','utm','cmr','cmmi','cmsy','msam','msbm')) and name.endswith(('.tfm','.vf','.pfb','.enc'))))
    if pick and not (cache/name).exists(): entries.append((offset,length,name))
entries.sort()
groups=[]
for e in entries:
    if groups and e[0]-(groups[-1][-1][0]+groups[-1][-1][1])<8192 and e[0]-groups[-1][0][0]<8_000_000:
        groups[-1].append(e)
    else: groups.append([e])
print('Prefetch',len(entries),'files in',len(groups),'ranges',flush=True)
def fetch(group):
    start=group[0][0]; end=group[-1][0]+group[-1][1]-1
    req=urllib.request.Request('https://data1b.fullyjustified.net/tlextras-2022.0r0.tar',
        headers={'Range':f'bytes={start}-{end}','User-Agent':'tectonic/0.17.0'})
    try:
        with urllib.request.urlopen(req,timeout=25) as response:
            assert response.status==206
            assert response.headers['Content-Range'].startswith(f'bytes {start}-{end}/')
            payload=response.read(end-start+2)
            assert len(payload)==end-start+1
        for offset,length,name in group:
            target=cache/name
            if target.exists(): continue
            temp=target.with_name(name+'.prefetching')
            temp.write_bytes(payload[offset-start:offset-start+length])
            os.replace(temp,target)
        return len(group)
    except Exception as exc:
        print('Deferred',group[0][2],type(exc).__name__,str(exc)[:120],flush=True)
        return 0
with ThreadPoolExecutor(max_workers=6) as pool:
    count=sum(pool.map(fetch,groups))
print('Cached',count,'resources',flush=True)
