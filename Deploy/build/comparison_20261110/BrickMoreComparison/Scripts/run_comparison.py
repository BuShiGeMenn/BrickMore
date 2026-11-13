"""Visible stage progress, preflight, checked resume and result export."""
import argparse,json,os,queue,re,signal,subprocess,sys,tarfile,threading,time
from pathlib import Path
from common import ROOT,Progress,digest,dump,rows,sha,write_rows
from doctor import check
from report import make

def verify():
    entries=(ROOT/'CHECKSUMS.sha256').read_text(encoding='utf-8').splitlines();bar=Progress('Verify bundle',len(entries))
    for i,line in enumerate(entries,1):
        expected,name=line.split('  ',1);path=(ROOT/name).resolve()
        if not path.is_relative_to(ROOT.resolve()) or sha(path)!=expected:raise ValueError('Integrity mismatch: '+name)
        bar.update(i,name)
    print('VERIFY OK: '+str(len(entries))+' hash-checked files',flush=True)

def run_stage(stage,command,out,total,state):
    logpath=out/(stage+'.log');record=dict(status='running',done=0,total=total,start=time.time(),pid=os.getpid(),log=str(logpath))
    state['stages'][stage]=record;state['current_stage']=stage;dump(out/'progress.json',state)
    print('\n=== '+stage.upper()+' ===\nLOG '+str(logpath),flush=True)
    env={**os.environ,'PYTHONUTF8':'1','PYTHONUNBUFFERED':'1','BRICKNET_DATA':str(ROOT/'Assets'),
         'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1',
         'MKL_NUM_THREADS':'1','NUMEXPR_NUM_THREADS':'1','TBB_NUM_THREADS':'1','PYTHONFAULTHANDLER':'1',
         'NUMBA_CACHE_DIR':str(ROOT/'.runtime/numba-cache')}
    process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',bufsize=1,env=env,start_new_session=os.name!='nt')
    messages=queue.Queue()
    def reader():
        for line in process.stdout:messages.put(line)
        messages.put(None)
    thread=threading.Thread(target=reader,daemon=True);thread.start();bar=Progress(stage,total);ended=False;last_dump=0
    try:
        with logpath.open('a',encoding='utf-8') as log:
            log.write('\nCOMMAND '+json.dumps(command)+'\n');log.flush()
            while not ended or process.poll() is None:
                try:line=messages.get(timeout=1)
                except queue.Empty:line=''
                if line is None:ended=True
                elif line:
                    log.write(line);log.flush()
                    if line.startswith('PROGRESS '):
                        item=json.loads(line[len('PROGRESS '):]);record.update(done=item['done'],total=item['total'],sample_id=item['sample_id'])
                    else:
                        m=re.match(r'^(\d+)/(\d+)\s+(\S+)',line)
                        if m:record.update(done=int(m[1]),total=int(m[2]),sample_id=m[3])
                bar.total=record['total'];bar.update(record['done'],record.get('sample_id','loading/checking cached files'))
                if time.monotonic()-last_dump>2:
                    record['heartbeat']=time.time();dump(out/'progress.json',state);last_dump=time.monotonic()
        code=process.wait();record.update(status='completed' if code==0 else 'failed',exit_code=code,end=time.time())
        if code:raise RuntimeError(f'{stage} failed (exit={code}); see {logpath}')
        record['done']=record['total'];bar.update(record['done'],'completed',force=True);dump(out/'progress.json',state)
    except BaseException:
        if process.poll() is None:
            if os.name!='nt':os.killpg(process.pid,signal.SIGTERM)
            else:process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill()
        record.update(status='interrupted' if isinstance(sys.exc_info()[1],KeyboardInterrupt) else 'failed',end=time.time());dump(out/'progress.json',state);raise

def status(out,watch):
    while True:
        path=out/'progress.json'
        if not path.exists():print('No run state: '+str(path));return
        value=json.loads(path.read_text(encoding='utf-8'))
        if watch and sys.stdout.isatty():print('\033[2J\033[H',end='')
        print('Three-system evaluation | current='+str(value.get('current_stage')))
        for name,item in value.get('stages',{}).items():
            n,t=item.get('done',0),item.get('total',0);print(f'{name:12} {item["status"]:12} {n:6}/{t:<6} {100*n/t if t else 0:6.1f}% '+item.get('sample_id',''))
        if not watch:return
        time.sleep(3)

def selected(a):
    items=rows(ROOT/'Data/manifest.jsonl')
    if a.scope=='primary':items=[r for r in items if r['primary']]
    if a.mode=='smoke':
        chosen=[]
        predicates=[lambda r:r['system']=='BrickMore' and r.get('reconstruction'),
                    lambda r:r['system']=='BrickMore' and r.get('source_kind')=='regenerated',
                    lambda r:r['system']=='BrickMore' and not r.get('reconstruction') and r.get('source_kind')!='regenerated',
                    lambda r:r['system']=='BrickGPT',lambda r:r['system']=='BrickNet',
                    lambda r:r['system']=='BrickNet' and r['category']=='car']
        for pi,pred in enumerate(predicates):
            row=next((r for r in items if (r['primary'] or pi==0) and pred(r) and r not in chosen),None)
            if row:chosen.append(row)
        items=chosen
    if a.limit:items=items[:a.limit]
    return items

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['verify','doctor','dry-run','smoke','full','status','export','report'])
    p.add_argument('--out',type=Path);p.add_argument('--scope',choices=['all','primary'],default='all');p.add_argument('--limit',type=int)
    p.add_argument('--workers',type=int,default=1);p.add_argument('--cpu-only',action='store_true');p.add_argument('--structure-only',action='store_true')
    p.add_argument('--gpu-python');p.add_argument('--structure-python');p.add_argument('--render-python');p.add_argument('--device',default='cuda:0');p.add_argument('--watch',action='store_true')
    a=p.parse_args();out=(a.out or ROOT/'Results'/('comparison_smoke' if a.mode=='smoke' else 'comparison_full')).resolve();out.mkdir(parents=True,exist_ok=True)
    if a.mode=='verify':verify();return
    if a.mode=='status':status(out,a.watch);return
    if a.mode=='doctor':
        a.out=ROOT/'.runtime/environment.json';sys.exit(0 if check(a)['ok'] else 2)
    if a.mode=='export':
        archive=out.parent/(out.name+'-results.tar.gz')
        with tarfile.open(archive,'w:gz') as tar:tar.add(out,arcname=out.name)
        archive.with_name(archive.name+'.sha256').write_text(sha(archive)+'  '+archive.name+'\n',encoding='ascii');print('EXPORTED '+str(archive));return
    manifest=out/'selected_manifest.jsonl'
    if a.mode=='report':make(manifest,out);return
    verify();items=selected(a);assert items
    config=dict(bundle_manifest_sha256=sha(ROOT/'Data/manifest.jsonl'),scope=a.scope,mode=a.mode,limit=a.limit,
        sample_ids=[r['sample_id'] for r in items],cpu_only=a.cpu_only,structure_only=a.structure_only,device=a.device,workers=a.workers)
    print(json.dumps(dict(records=len(items),views=len(items)*8,primary=sum(r['primary'] for r in items),
       counts={s:sum(r['system']==s for r in items) for s in ['BrickMore','BrickGPT','BrickNet']},
       models={'vqa':'Qwen/Qwen2.5-VL-7B-Instruct','pe':'timm/PE-Core-bigG-14-448','siglip2':'google/siglip2-giant-opt-patch16-384'}),indent=2),flush=True)
    if a.mode=='dry-run':print('DRY RUN OK: no model allocation or network access');return
    cp=out/'run_config.json'
    if cp.exists() and json.loads(cp.read_text(encoding='utf-8'))!=config:raise ValueError('Run options/input changed; use a new --out directory')
    dump(cp,config);write_rows(manifest,items)
    probe=argparse.Namespace(cpu_only=a.cpu_only or a.structure_only,structure_only=a.structure_only,gpu_python=a.gpu_python,structure_python=a.structure_python,render_python=a.render_python,out=out/'environment.json')
    environment=check(probe)
    if not environment['ok']:raise RuntimeError('Preflight failed; see environment.json. No downloads were started.')
    roles=environment['roles'];state={'started':time.time(),'stages':{}}
    run_stage('structure',[roles['structure'],'-X','utf8',str(ROOT/'Scripts/structure.py'),'--input',str(manifest),'--out',str(out/'structure.jsonl'),'--workers',str(a.workers)],out,len(items),state)
    if not a.structure_only:
        run_stage('render',[roles['render'],'-X','utf8',str(ROOT/'Scripts/render.py'),'--input',str(manifest),'--out',str(out/'rendered')],out,len(items)*8,state)
    if not a.cpu_only and not a.structure_only:
        for metric in ['vqa','pe','siglip2']:
            run_stage(metric,[roles['gpu'],'-X','utf8',str(ROOT/'Scripts/evaluate_paper_images.py'),'--metric',metric,'--preset','paper-text',
                '--model',environment['models'][metric]['path'],'--offline','--device',a.device,'--batch-size','1',
                '--renders',str(out/'rendered/renders.jsonl'),'--out',str(out/(metric+'.jsonl'))],out,len(items),state)
    make(manifest,out);state.update(current_stage='finished',finished=time.time());dump(out/'progress.json',state)
    print('FINISHED '+str(out)+'\nReport: '+str(out/'report/report.html'),flush=True)

if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:print('\nINTERRUPTED: completed journals, images and .part downloads retained. Repeat the identical command to resume.',flush=True);sys.exit(130)
