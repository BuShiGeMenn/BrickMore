"""Small, portable I/O, integrity journals and terminal progress for offline comparison."""
from __future__ import annotations
import hashlib,json,os,sys,time
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def dump(path,value):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8');t.replace(p)

def rows(path):
    p=Path(path)
    if not p.exists():return []
    data=p.read_text(encoding='utf-8-sig');out=[];lines=data.splitlines(keepends=True)
    for i,line in enumerate(lines):
        if not line.strip():continue
        try:out.append(json.loads(line))
        except json.JSONDecodeError:
            if i!=len(lines)-1 or line.endswith('\n'):raise
            backup=p.with_suffix(p.suffix+f'.interrupted-{time.time_ns()}');backup.write_text(data,encoding='utf-8')
            p.write_text(''.join(lines[:i]),encoding='utf-8')
            print(f'Recovered incomplete final journal line; original saved: {backup}',flush=True)
    return out

def write_rows(path,values):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(''.join(json.dumps(v,ensure_ascii=False,allow_nan=False)+'\n' for v in values),encoding='utf-8')

class Journal:
    def __init__(self,path,config):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.signature=digest(config);cfg={**config,'signature':self.signature};cp=self.path.with_suffix('.config.json')
        if cp.exists() and json.loads(cp.read_text(encoding='utf-8'))!=cfg:raise ValueError(f'Configuration/input changed: use a new output directory: {cp}')
        if not cp.exists() and self.path.exists() and self.path.stat().st_size:raise ValueError('Journal without config; refusing unverified resume')
        dump(cp,cfg);self.done={v['sample_id']:v for v in rows(self.path)}
        if any(v.get('config_signature')!=self.signature for v in self.done.values()):raise ValueError('Mixed journal signatures')
    def cached(self,sid,ih):
        v=self.done.get(sid)
        if v and v['input_sha256']!=ih:raise ValueError(f'Changed input: {sid}')
        return v
    def add(self,value,ih):
        v={**value,'input_sha256':ih,'config_signature':self.signature}
        with self.path.open('a',encoding='utf-8') as f:f.write(json.dumps(v,ensure_ascii=False,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
        self.done[v['sample_id']]=v

class Progress:
    def __init__(self,label,total,initial=0,unit='items'):
        self.label,self.total,self.initial,self.unit=label,total,initial,unit;self.start=time.monotonic();self.last=0
    def update(self,n,detail='',force=False):
        elapsed=time.monotonic()-self.start
        if not force and elapsed-self.last<1 and n!=self.total:return
        self.last=elapsed;speed=(n-self.initial)/max(elapsed,.001);eta=(self.total-n)/speed if speed>0 else None
        percent=100*n/self.total if self.total else 0;filled=int(percent/5)
        line=f'{self.label} [{"#"*filled}{"-"*(20-filled)}] {n}/{self.total} {percent:5.1f}% elapsed={elapsed:.0f}s ETA={eta:.0f}s' if eta is not None else f'{self.label} [{"#"*filled}{"-"*(20-filled)}] {n}/{self.total} {percent:5.1f}% elapsed={elapsed:.0f}s ETA=--'
        line+=' '+detail
        line+=f' speed={speed/2**20:.2f} MiB/s' if self.unit=='bytes' else f' speed={speed:.2f}/s'
        print(('\r\033[2K' if sys.stdout.isatty() else '')+line,end='\n' if n==self.total or not sys.stdout.isatty() else '',flush=True)

def emit(stage,n,total,sid):
    print('PROGRESS '+json.dumps(dict(stage=stage,done=n,total=total,sample_id=sid),ensure_ascii=False),flush=True)
