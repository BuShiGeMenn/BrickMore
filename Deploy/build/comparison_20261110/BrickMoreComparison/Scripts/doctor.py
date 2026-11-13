"""Read-only role, CUDA, part-assets and offline model-cache checks."""
import argparse,importlib,importlib.metadata,importlib.util,json,os,subprocess,sys
from pathlib import Path
from common import ROOT,dump,Progress

REPOS={'vqa':'Qwen/Qwen2.5-VL-7B-Instruct','pe':'timm/PE-Core-bigG-14-448','siglip2':'google/siglip2-giant-opt-patch16-384'}

def probe():
    modules=['numpy','scipy','numba','PIL','bricknet','meshlib','torch','torchvision','transformers','open_clip','qwen_vl_utils','huggingface_hub','accelerate']
    result=dict(python=sys.executable,version=sys.version,modules={m:importlib.util.find_spec(m) is not None for m in modules},models={})
    result['bricknet_version']=importlib.metadata.version('bricknet') if result['modules']['bricknet'] else None
    result['versions']={}
    for package in ['numpy','numba','meshlib','torch','transformers','open_clip_torch','qwen-vl-utils','pillow']:
        try:result['versions'][package]=importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:pass
    result['render_ready']=False;result['structure_ready']=False
    try:
        for module in ['numpy','numba','PIL.Image']:importlib.import_module(module)
        result['render_ready']=True
    except Exception as e:result['render_error']=repr(e)
    try:
        os.environ['BRICKNET_DATA']=str(ROOT/'Assets')
        import bricknet
        from bricknet.data import load_catalog
        from bricknet.collision import _mesh
        _mesh(load_catalog().stem_to_id['3001'])
        result['structure_ready']=bricknet.__version__=='0.1.0'
    except Exception as e:result['structure_error']=repr(e)
    if result['modules']['torch']:
        try:
            import torch
            result['cuda']=torch.cuda.is_available()
            if result['cuda']:
                free,total=torch.cuda.mem_get_info();result['gpu']=dict(name=torch.cuda.get_device_name(0),free_gib=free/2**30,total_gib=total/2**30)
        except Exception as e:result['torch_error']=repr(e);result['cuda']=False
    if result['modules']['huggingface_hub']:
        from huggingface_hub import snapshot_download
        for metric,repo in REPOS.items():
            try:
                local=ROOT/'Downloads/models'/metric
                path=local if local.is_dir() else Path(snapshot_download(repo,local_files_only=True))
                for file in ('config.json',) if metric!='pe' else ('open_clip_config.json',):
                    if not (path/file).is_file():raise ValueError(f'Missing {file}')
                indices=list(path.glob('*.safetensors.index.json'))
                if indices:
                    for index in indices:
                        missing=[name for name in set(json.loads(index.read_text())['weight_map'].values()) if not (path/name).is_file()]
                        if missing:raise ValueError(f'Missing weight shards: {missing}')
                elif not list(path.glob('*.safetensors')):raise ValueError('No safetensors weights')
                if list(path.rglob('*.part')):raise ValueError('Incomplete .part model downloads')
                if metric=='pe':
                    import open_clip
                    open_clip.get_tokenizer('local-dir:'+path.resolve().as_posix())
                else:
                    from transformers import AutoProcessor
                    AutoProcessor.from_pretrained(path,local_files_only=True,use_fast=False)
                result['models'][metric]=dict(ok=True,path=str(path))
            except Exception as e:result['models'][metric]=dict(ok=False,error=str(e)[:350])
    print('DOCTOR_JSON '+json.dumps(result,ensure_ascii=False),flush=True)

def discover(explicit=None):
    candidates=[]
    def add(value):
        if not value:return
        p=Path(value)
        if p.is_dir():p=p/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        if p.is_file() and str(p) not in candidates:candidates.append(str(p))
    for value in (explicit or []):add(value)
    for name in ['GPU_PYTHON','CPU_PYTHON','RENDER_PYTHON','BRICKMORE_GPU_PYTHON','BRICKMORE_RENDER_PYTHON','BRICKMORE_CPU_PYTHON','BRICKMORE_ENV','BRICKMORE_RENDER_ENV','BRICKMORE_CPU_ENV']:
        add(os.environ.get(name))
    add(sys.executable);add(ROOT/'.runtime/cpu');add(ROOT/'.runtime/gpu')
    previous=Path('/mnt/brickmore-data/brickmore-jrd-20261025')
    if previous.is_dir():
        for pattern in ['*/bin/python','*/*/bin/python','*/*/*/bin/python']:
            for path in previous.glob(pattern):add(path)
    return candidates

def check(a):
    candidates=discover([a.gpu_python,a.structure_python,a.render_python]);probes=[];progress=Progress('Environment probes',len(candidates))
    env={**os.environ,'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','PYTHONUTF8':'1'}
    for i,python in enumerate(candidates,1):
        try:
            r=subprocess.run([python,'-X','utf8',str(Path(__file__)),'--probe'],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120,env=env)
            line=next(l for l in reversed(r.stdout.splitlines()) if l.startswith('DOCTOR_JSON '));value=json.loads(line[len('DOCTOR_JSON '):]);probes.append(value)
        except Exception as e:probes.append(dict(python=python,error=str(e)[:300],modules={}))
        progress.update(i,python,force=True)
    def choose(required,explicit=None,cuda=False,bricknet=False):
        values=sorted(probes,key=lambda v:0 if explicit and Path(v['python'])==Path(explicit) else 1)
        return next((v for v in values if all(v['modules'].get(m) for m in required) and (not cuda or v.get('cuda')) and (not bricknet or v.get('bricknet_version')=='0.1.0')),None)
    gpu=choose(['torch','torchvision','transformers','open_clip','qwen_vl_utils','huggingface_hub','accelerate','PIL'],a.gpu_python,cuda=True)
    def role_values(explicit):return sorted(probes,key=lambda v:0 if explicit and Path(v['python'])==Path(explicit) else 1)
    structural=next((v for v in role_values(a.structure_python) if v.get('structure_ready')),None)
    renderer=next((v for v in role_values(a.render_python) if v.get('render_ready')),None)
    missing=[]
    if not structural:missing.append('Structure runtime: bricknet==0.1.0, MeshLib, NumPy, SciPy')
    if not renderer and not getattr(a,'structure_only',False):missing.append('Render runtime: NumPy, Numba, Pillow')
    if not a.cpu_only:
        if not gpu:missing.append('GPU runtime: CUDA + torch/torchvision/transformers/open_clip/qwen-vl-utils/accelerate')
        elif any(not gpu.get('models',{}).get(m,{}).get('ok') for m in REPOS):missing.append('One or more offline VQA/PE/SigLIP2 model snapshots are missing/incomplete')
    catalog=ROOT/'Assets/catalog.json';assets_ok=catalog.exists()
    if assets_ok:
        parts=json.loads(catalog.read_text(encoding='utf-8'))['parts']
        assets_ok=all((ROOT/'Assets/inset'/(stem+'.ply')).is_file() and (ROOT/'Assets/render_meshes'/(stem+'.npz')).is_file() for stem in parts)
    if not assets_ok:missing.append('Bundled collider/render assets incomplete: verify/retransfer archive')
    result=dict(ok=not missing,cpu_only=a.cpu_only,roles=dict(gpu=gpu['python'] if gpu else None,
       structure=structural['python'] if structural else None,render=renderer['python'] if renderer else None),
       models=gpu.get('models',{}) if gpu else {},missing=missing,probes=probes,assets_ok=assets_ok,
       download_instructions=['On a connected Windows/Linux transfer host: python Scripts/fetch.py wheels',
          'If model cache is missing: python Scripts/fetch.py models --metrics vqa pe siglip2',
          'GPU dependency wheels: use matching Linux/WSL Python with python Scripts/fetch.py pip-plan',
          'Transfer Downloads/ to the same extracted package on the internal server, then bash setup.sh --offline'])
    dump(a.out,result)
    for role,path in result['roles'].items():print(f'{role.upper():10} '+(path or 'MISSING'),flush=True)
    for metric,v in result['models'].items():print(f'MODEL {metric:8} '+(v.get('path') if v['ok'] else 'MISSING: '+v['error']),flush=True)
    if gpu and gpu.get('gpu'):print('GPU '+json.dumps(gpu['gpu']),flush=True)
    for problem in missing:print('MISSING '+problem,flush=True)
    print('ENVIRONMENT '+('READY' if result['ok'] else 'NOT READY')+' report='+str(a.out),flush=True)
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--probe',action='store_true');p.add_argument('--cpu-only',action='store_true');p.add_argument('--gpu-python');p.add_argument('--structure-python');p.add_argument('--render-python');p.add_argument('--out',type=Path,default=ROOT/'.runtime/environment.json');a=p.parse_args()
    if a.probe:probe()
    else:sys.exit(0 if check(a)['ok'] else 2)

if __name__=='__main__':main()
