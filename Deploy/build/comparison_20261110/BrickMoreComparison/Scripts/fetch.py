"""Run on an internet-connected transfer machine; retain all incomplete downloads."""
import argparse,json,re,subprocess,sys,urllib.parse
from pathlib import Path
from common import ROOT,dump
from download import api,fetch

CPU={'bricknet':'0.1.0','numpy':'2.2.6','scipy':'1.15.3','meshlib':'3.1.4.297','meshlib-core':'3.1.4.297',
     'platformdirs':'4.4.0','numba':'0.61.2','llvmlite':'0.44.0','pillow':'11.3.0'}
REPOS={'vqa':'Qwen/Qwen2.5-VL-7B-Instruct','pe':'timm/PE-Core-bigG-14-448','siglip2':'google/siglip2-giant-opt-patch16-384'}

def linux312_rank(filename):
    if not filename.endswith('.whl'):return -1
    py,abi,platform=filename[:-4].rsplit('-',3)[-3:]
    if platform=='any':platform_rank=0
    else:
        ranks=[]
        for tag in platform.split('.'):
            if not tag.endswith('_x86_64') or not tag.startswith('manylinux'):continue
            match=re.search(r'manylinux_2_(\d+)_',tag)
            minor=int(match[1]) if match else (17 if '2014' in tag else 12 if '2010' in tag else 5)
            if minor<=31:ranks.append(minor)
        if not ranks:return -1
        platform_rank=max(ranks)
    if py=='cp312' and abi=='cp312':return 100+platform_rank
    if abi=='abi3' and py.startswith('cp3') and int(py[3:])<=12:return 80+platform_rank
    if 'py312' in py.split('.') and abi=='none':return 60+platform_rank
    if 'py3' in py.split('.') and abi=='none':return 40+platform_rank
    return -1

def wheels(dest):
    dest.mkdir(parents=True,exist_ok=True);manifest=[]
    for index,(name,version) in enumerate(CPU.items(),1):
        print(f'WHEEL {index}/{len(CPU)} {name}=={version}',flush=True)
        data=api(f'https://pypi.org/pypi/{name}/{version}/json')
        candidates=[f for f in data['urls'] if linux312_rank(f['filename'])>=0]
        if not candidates:raise ValueError(f'No compatible Linux CPython3.12 x86_64 wheel: {name}')
        item=max(candidates,key=lambda f:linux312_rank(f['filename']));checksum=item['digests']['sha256']
        fetch(item['url'],dest/item['filename'],size=item['size'],sha256=checksum)
        manifest.append(dict(name=name,version=version,file=item['filename'],sha256=checksum,size=item['size']))
    dump(dest/'wheel_manifest.json',dict(target='Linux x86_64 CPython3.12 glibc>=2.31',packages=manifest))

def models(dest,which,endpoint):
    for metric in which:
        repo=REPOS[metric];metadata=api(endpoint+'/api/models/'+repo);revision=metadata['sha']
        tree=api(endpoint+'/api/models/'+repo+'/tree/'+revision+'?recursive=true&expand=false')
        files=[f for f in tree if f['type']=='file' and '/' not in f['path'] and f['path'].endswith(('.json','.safetensors','.txt','.model','.jinja','.tiktoken','.bpe'))]
        if not any(f['path'].endswith('.safetensors') for f in files):files += [f for f in tree if f['type']=='file' and '/' not in f['path'] and f['path'].endswith('.bin')]
        folder=dest/metric;folder.mkdir(parents=True,exist_ok=True);saved=[]
        print(f'MODEL {metric}: {repo} revision={revision} files={len(files)} total={sum(f["size"] for f in files)/2**30:.2f} GiB',flush=True)
        for index,item in enumerate(files,1):
            print(f'MODEL_FILE {index}/{len(files)} {item["path"]}',flush=True)
            lfs=item.get('lfs',{});url=endpoint+'/'+repo+'/resolve/'+revision+'/'+urllib.parse.quote(item['path'])+'?download=true'
            fetch(url,folder/item['path'],size=item['size'],sha256=lfs.get('oid'),git_sha1=None if lfs else item['oid'])
            saved.append(dict(path=item['path'],size=item['size'],sha256=lfs.get('oid'),git_sha1=None if lfs else item['oid']))
        dump(folder/'download_provenance.json',dict(repo=repo,revision=revision,files=saved))

def pip_plan(dest,python,requirements):
    # This command resolves native GPU dependencies on an online Linux/WSL host.
    # Full wheel payloads are then fetched with our persistent .part/Range client.
    dest.mkdir(parents=True,exist_ok=True);report=dest/'pip_download_plan.json'
    command=[python,'-m','pip','install','--dry-run','--ignore-installed','--only-binary=:all:',
             '--report',str(report),'--retries','12','--timeout','45','-r',str(requirements)]
    subprocess.run(command,check=True)
    for item in json.loads(report.read_text(encoding='utf-8'))['install']:
        info=item['download_info'];url=info['url'];name=Path(urllib.parse.unquote(urllib.parse.urlparse(url).path)).name
        checksum=info.get('archive_info',{}).get('hashes',{}).get('sha256')
        if not name.endswith('.whl') or not checksum:raise ValueError('Only hash-verified binary wheels are accepted')
        fetch(url,dest/name,sha256=checksum)

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='mode',required=True)
    q=sub.add_parser('wheels');q.add_argument('--dest',type=Path,default=ROOT/'Downloads/wheels')
    q=sub.add_parser('models');q.add_argument('--dest',type=Path,default=ROOT/'Downloads/models');q.add_argument('--metrics',nargs='+',choices=REPOS,default=list(REPOS));q.add_argument('--endpoint',default='https://huggingface.co')
    q=sub.add_parser('pip-plan');q.add_argument('--dest',type=Path,default=ROOT/'Downloads/gpu_wheels');q.add_argument('--python',default=sys.executable);q.add_argument('--requirements',type=Path,default=ROOT/'requirements-gpu.txt')
    a=p.parse_args()
    if a.mode=='wheels':wheels(a.dest)
    elif a.mode=='models':models(a.dest,a.metrics,a.endpoint.rstrip('/'))
    else:pip_plan(a.dest,a.python,a.requirements)

if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:
        print('\nINTERRUPTED: .part downloads retained. Repeat the same fetch command to resume.',flush=True);sys.exit(130)
