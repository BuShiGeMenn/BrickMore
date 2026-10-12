"""Resumable frozen Q4 census; publish only after all 80,000 portable outcomes pass."""
import argparse
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import traceback
import uuid
import zipfile

import package_quality as pack
e=pack.e;q=e.q
ROOT=Path(__file__).resolve().parent.parent
VERSION='frozen_q4_census_publisher_v2'
REPOSITORY_URL='https://github.com/BuShiGeMenn/BrickMore.git'
_PLAN=None
_OUT=None
_PLAN_SHA=None


def source_jobs(dataset,index,shard,expected_count=40000):
    dataset=Path(dataset).resolve();index=Path(index).resolve()
    manifest=json.loads((dataset/'manifest.json').read_bytes());jobs=q.a.manifest_jobs(manifest)
    cfg=json.loads((index.parent/'config.json').read_bytes())
    bases=[index.parent.resolve(),Path(cfg['baseRun']).resolve()];baseline={}
    for line in index.read_text(encoding='utf8').splitlines():
        row=json.loads(line)
        if row['modelId'] in baseline:raise ValueError('duplicate selected baseline ID')
        if not any(Path(row['resultPath']).resolve()==base/'models'/row['category']/row['modelId'] for base in bases):raise ValueError('unsealed baseline path')
        baseline[row['modelId']]=row
    if len(jobs)!=expected_count or len(baseline)!=expected_count or set(baseline)!={j['modelId'] for j in jobs}:raise ValueError('source/baseline model count mismatch')
    result=[]
    for job in jobs:
        if any(not re.fullmatch(r'[A-Za-z0-9_-]+',job[k]) for k in ('modelId','category')):raise ValueError('unsafe model ID/category')
        if Path(job['modelPath']).as_posix()!=f'models/{job["category"]}/{job["modelId"]}':raise ValueError('unsafe source model path')
        row=baseline[job['modelId']]
        result.append(dict(job,datasetPath=str(dataset),shardId=shard,baselinePath=row['resultPath'],
                           baselineReportSha256=row['reportFileSha256'],baselineStatus=row['status']))
    result.sort(key=lambda j:q.a.sha(('q4-full-38177'+j['modelId']).encode()))
    return result,{'manifestSha256':q.a.file_sha(dataset/'manifest.json'),
                   'baselineIndexSha256':q.a.file_sha(index),'baselineIndexPath':str(index)}


def attach_cached(jobs,workspace):
    """Retain actual verified Q4 outcomes and proven Q3 successes; never fake versions."""
    by_id={j['modelId']:j for j in jobs};root=Path(workspace)/'downloads'
    for name in ('A_regression_v2','B_regression_v2','A_uniform_retry_v3','B_uniform_retry_v3'):
        run=root/'quality_q3'/name
        if not (run/'config.json').exists():continue
        config=json.loads((run/'config.json').read_bytes())
        selection=json.loads((run/'selection.json').read_bytes())
        if config['selectionSha256']!=q.a.sha(json.dumps(selection,sort_keys=True).encode()):raise ValueError('prior Q3 selection changed')
        for job in selection:
            folder=run/'models'/job['category']/job['modelId'];report=json.loads((folder/'report.json').read_bytes())
            if report['status']!='success':continue
            if job['modelId'] not in by_id:raise ValueError('cached Q3 model outside census')
            by_id[job['modelId']].update(priorQ3Path=str(folder.resolve()),priorQ3ReportSha256=q.a.file_sha(folder/'report.json'),priorQ3Status='success')
    for name in ('A_uniform_sparse_v2','B_uniform_sparse_v2'):
        run=root/'quality_q4'/name
        if not (run/'config.json').exists():continue
        config=json.loads((run/'config.json').read_bytes());selection=json.loads((run/'selection.json').read_bytes())
        if config['sourceCodeSha256']!=e.hashes() or config['selectionSha256']!=q.a.sha(json.dumps(selection,sort_keys=True).encode()):raise ValueError('cached Q4 generation/selection changed')
        for job in selection:
            if job['modelId'] not in by_id:raise ValueError('cached Q4 outside census')
            folder=run/'models'/job['category']/job['modelId']
            by_id[job['modelId']].update(cachedQ4Path=str(folder.resolve()),cachedQ4ReportSha256=q.a.file_sha(folder/'report.json'),
                                       cachedQ4ConfigSha256=q.a.file_sha(run/'config.json'))


def bind_original_archives(jobs,workspace):
    """Bind exact original model/prompt bytes to already published ZIP SHA-256."""
    proofs={}
    for shard in ('A','B'):
        selected=[j for j in jobs if j['shardId']==shard];by_path={j['modelPath']:j for j in selected};seen=set()
        manifest_path=workspace/('download_manifest.json' if shard=='A' else 'datasets/AI_B/download_manifest.json')
        manifest=json.loads(manifest_path.read_bytes());assets=[a for a in manifest['assets'] if a['kind']=='model_package']
        if len(assets)!=40:raise ValueError('40 original model packages per shard required')
        verified=[]
        for number,asset in enumerate(assets,1):
            path=Path(selected[0]['datasetPath'])/'packages'/asset['name']
            if Path(asset['name']).name!=asset['name'] or path.stat().st_size!=asset['bytes'] or pack.legacy.digest(path)!=asset['sha256']:raise ValueError('original ZIP size/SHA mismatch')
            with zipfile.ZipFile(path) as archive:
                names=archive.namelist()
                if len(names)!=len(set(names)):raise ValueError('duplicate original ZIP member')
                model_names=[name for name in names if name.endswith('/model.json')]
                if len(model_names)!=1000:raise ValueError('original ZIP must contain 1000 models')
                for name in model_names:
                    parent=Path(name).parent.as_posix()
                    if parent not in by_path or parent in seen:raise ValueError('original ZIP/manifest model mismatch')
                    job=by_path[parent];seen.add(parent)
                    job['originalModelFileSha256']=q.a.sha(archive.read(name))
                    job['originalPromptFileSha256']=q.a.sha(archive.read(parent+'/prompts.json'))
            verified.append({k:asset[k] for k in ('name','bytes','sha256')})
            print('Q4_ORIGINAL_ZIP_VERIFIED',shard,number,'/',40,flush=True)
        if len(seen)!=40000:raise ValueError('original ZIP source inventory incomplete')
        proofs[shard]=verified
    return proofs


def inventory(workspace):
    files=[Path('README.md'),Path('.gitignore')]
    for lane in ('voxel_assembly_q2','voxel_assembly_q3','voxel_assembly_q4'):
        files.extend(p.relative_to(workspace) for p in (workspace/'algorithms'/lane).rglob('*') if p.is_file() and p.suffix in ('.py','.md','.json'))
    names=('optimize_assembly.py','summarize_quality_q3.py','summarize_quality_q4.py','package_quality.py',
           'run_quality_full.py','download_quality.py','test_quality_delivery.py')
    files.extend(Path('tools')/n for n in names)
    files.append(Path('datasets/q4_assembly_80000/README.md'))
    files.append(Path('datasets/q4_assembly_80000/delivery_tests.json'))
    return {p.as_posix():q.a.file_sha(workspace/p) for p in sorted(set(files))}


def prepare(args):
    workspace=ROOT.resolve();out=args.out.resolve()
    if not out.is_relative_to(workspace/'downloads') or out==workspace/'downloads':raise ValueError('census output must be a new dedicated downloads child')
    if out.exists():raise ValueError('existing plan: use run/resume, not init')
    if shutil.disk_usage(workspace).free<25_000_000_000:raise ValueError('at least 25 GB free required')
    if subprocess.check_output(['git','remote','get-url','origin'],cwd=workspace,text=True).strip()!=REPOSITORY_URL:raise ValueError('Git remote outside authorized repository')
    jobs=[];metadata={}
    for shard,dataset,index in (('A',args.dataset_a,args.index_a),('B',args.dataset_b,args.index_b)):
        selected,metadata[shard]=source_jobs(dataset,index,shard);jobs.extend(selected)
        print('CENSUS_SOURCE_PLANNED',shard,len(selected),flush=True)
    if len(jobs)!=80000 or len({j['modelId'] for j in jobs})!=80000:raise ValueError('80,000 unique input IDs required')
    attach_cached(jobs,workspace)
    archive_proofs=bind_original_archives(jobs,workspace)
    for shard in ('A','B'):metadata[shard]['originalArchivesVerified']=archive_proofs[shard]
    runtime=dict(e.hashes())
    for name in ('package_quality.py','run_quality_full.py','download_quality.py','package_assembly.py',
                 'github_release.py','download_dataset.py','test_quality_delivery.py'):
        path=workspace/'tools'/name;runtime[path.relative_to(workspace).as_posix()]=q.a.file_sha(path)
    original_manifests=('download_manifest.json','datasets/AI_B/download_manifest.json','datasets/assembly_80000/download_manifest.json')
    options=dict(ratio=.02,seconds=60.,additionsSeconds=60.,physicsSeconds=5.,candidateLimit=80000,cutRounds=16)
    plan={'workflowVersion':VERSION,'workspace':str(workspace),'out':str(out),'releaseTag':args.tag,
          'options':options,'workers':args.workers,'publishAfterFullVerification':args.publish_after_verify,
          'algorithmVersion':e.VERSION,'algorithmSourceCodeSha256':e.hashes(),'runtimeSourceCodeSha256':runtime,
          'sourceMetadataSha256':{s:{k:v for k,v in m.items() if k!='baselineIndexPath'} for s,m in metadata.items()},
          'sourceInputs':metadata,'jobs':jobs,'publishInventorySha256':inventory(workspace),
          'originalReleaseManifestSha256':{n:q.a.file_sha(workspace/n) for n in original_manifests},
          'baseGitCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=workspace,text=True).strip(),
          'baseGitBranch':subprocess.check_output(['git','symbolic-ref','--short','HEAD'],cwd=workspace,text=True).strip(),
          'reusePolicy':'fresh readback retains published successes; cached Q4 outcomes preserve their actual prior options/generation/report hashes; original prompts never rebound',
          'startedAtUtc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    out.mkdir(parents=True);pack.atomic_json(out/'plan.json',plan)
    for name,digest in runtime.items():
        if q.a.file_sha(workspace/name)!=digest:raise ValueError('runtime changed during freeze')
        target=out/'source_snapshot'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(workspace/name,target)
    pack.atomic_json(out/'status.json',{'phase':'planned','processedModelCount':0,'modelCount':80000,
                                     'releaseTag':args.tag,'planSha256':q.a.file_sha(out/'plan.json')})
    print('CENSUS_PLAN_FROZEN',out,'cached_q4',sum('cachedQ4Path' in j for j in jobs),'prior_q3_success',sum('priorQ3Path' in j for j in jobs),flush=True)


def initialize_worker(plan,out,plan_sha):
    global _PLAN,_OUT,_PLAN_SHA
    _PLAN=plan;_OUT=Path(out);_PLAN_SHA=plan_sha
    if e.hashes()!=plan['algorithmSourceCodeSha256']:raise ValueError('worker algorithm differs from frozen generation')


def compute(job,worker_fn=None):
    out=_OUT;plan=_PLAN;folder=out/'models'/job['category']/job['modelId']
    source=Path(job['datasetPath'])/job['modelPath']/'model.json'
    if q.a.file_sha(source)!=job['originalModelFileSha256'] or q.a.file_sha(source.parent/'prompts.json')!=job['originalPromptFileSha256']:raise ValueError('input differs from original published ZIP bytes')
    def compact(row):
        return {'modelId':row['modelId'],'status':row['status'],'qualityScreenedSuccess':row['qualityScreenedSuccess'],
                'physicsStatus':row['physics']['status'],'finalGravityEquilibriumPassed':row['physics']['gravityEquilibriumPassed'],
                'changeRatio':row['repairAudit']['changeRatio'],'addedVoxelCount':row['repairAudit']['addedVoxelCount'],
                'removedVoxelCount':row['repairAudit']['removedVoxelCount']}
    if folder.exists():
        row=e.verify(folder,source);workflow=json.loads((folder/'workflow.json').read_bytes())
        if workflow['planSha256']!=_PLAN_SHA or workflow['reportSha256']!=q.a.file_sha(folder/'report.json'):raise ValueError('census checkpoint changed')
        if row['sourceCodeSha256']!=plan['algorithmSourceCodeSha256'] or row['algorithmVersion']!=e.VERSION or workflow['actualOptions']!=row['options']:raise ValueError('checkpoint generation changed')
        return compact(row)
    if q.a.file_sha(Path(job['baselinePath'])/'report.json')!=job['baselineReportSha256']:raise ValueError('selected baseline changed')
    stage=out/'staging'/job['modelId'];staged=stage/'models'/job['category']/job['modelId']
    # Interrupted outputs remain recoverable; only this plan-owned staging tree moves.
    if stage.exists():
        destination=out/'interrupted_staging'/(job['modelId']+'_'+uuid.uuid4().hex)
        if not stage.resolve().is_relative_to((out/'staging').resolve()) or not destination.resolve().is_relative_to((out/'interrupted_staging').resolve()):raise ValueError('unsafe recovery move')
        destination.parent.mkdir(parents=True,exist_ok=True);stage.rename(destination)
    started=time.monotonic();origin='new_q4_processing';seed_sha=None
    if job.get('cachedQ4Path'):
        prior=Path(job['cachedQ4Path'])
        if q.a.file_sha(prior/'report.json')!=job['cachedQ4ReportSha256'] or q.a.file_sha(prior.parents[2]/'config.json')!=job['cachedQ4ConfigSha256']:raise ValueError('cached Q4 proof changed')
        row=e.verify(prior,source)
        if row['sourceCodeSha256']!=plan['algorithmSourceCodeSha256']:raise ValueError('cached Q4 code mismatch')
        staged.mkdir(parents=True)
        for name in list(row['outputFileSha256'])+['report.json']:shutil.copyfile(prior/name,staged/name)
        origin='verified_cached_q4';seed_sha=job['cachedQ4ReportSha256']
    else:
        row=(worker_fn or e.worker)((job,job['datasetPath'],str(stage),plan['options']))
    e.verify(staged,source)
    pack.atomic_json(staged/'workflow.json',{'planSha256':_PLAN_SHA,'origin':origin,
                     'cachedReportSha256':seed_sha,'actualOptions':row['options'],
                     'reportSha256':q.a.file_sha(staged/'report.json'),'elapsedSeconds':time.monotonic()-started})
    folder.parent.mkdir(parents=True,exist_ok=True);staged.rename(folder)
    return compact(row)


def lock_run(out):
    path=out/'run.lock';handle=path.open('a+b')
    if path.stat().st_size==0:handle.write(b'0');handle.flush()
    handle.seek(0)
    if os.name=='nt':
        import msvcrt
        try:msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:handle.close();raise RuntimeError('this census is already running')
    else:
        import fcntl
        fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    return handle


def status(out,phase,rows,**extra):
    value={'workflowVersion':VERSION,'phase':phase,'modelCount':80000,'processedModelCount':len(rows),
           'geometryPassed':sum(r.get('geometryPassed',r['status']=='success') for r in rows),
           'gravityScreenedPassed':sum(r['qualityScreenedSuccess'] for r in rows),
           'statusCounts':dict(Counter(r['status'] for r in rows)),
           'updatedAtUtc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'pid':os.getpid(),**extra}
    pack.atomic_json(out/'status.json',value)


def check_original_releases(plan,token):
    import github_release as publisher
    workspace=Path(plan['workspace'])
    for name,digest in plan['originalReleaseManifestSha256'].items():
        path=workspace/name
        if q.a.file_sha(path)!=digest:raise ValueError('original release manifest changed')
        manifest=json.loads(path.read_bytes());release=publisher.find_release(token,manifest['releaseTag'])
        if release is None or release['draft']:raise ValueError('original release missing/unpublished')
        remote={r['name']:r for r in publisher.assets(token,release['id'])}
        if set(remote)!={r['name'] for r in manifest['assets']} or any(not publisher.matches(remote[r['name']],r) for r in manifest['assets']):raise ValueError('original release inventory/digest changed')


def publish(out,plan,summary,manifest,publication_directory='q4_assembly_80000'):
    if summary['processedModelCount']!=80000 or summary['remainingModelCount'] or manifest['assetCount']!=81 or not summary['allPublicZipCrcShaGeometryRepairGateAndPhysicsReadbackPassed']:raise ValueError('refuse publication before full census checks')
    if publication_directory not in ('q4_assembly_80000','relaxed_assembly_80000'):raise ValueError('unauthorized publication directory')
    workspace=Path(plan['workspace']);public=workspace/'datasets'/publication_directory
    if subprocess.check_output(['git','remote','get-url','origin'],cwd=workspace,text=True).strip()!=REPOSITORY_URL:raise ValueError('authorized Git remote changed; refusing publication')
    if subprocess.check_output(['git','symbolic-ref','--short','HEAD'],cwd=workspace,text=True).strip()!=plan['baseGitBranch']:raise ValueError('user Git branch changed; refusing publication')
    for name,digest in plan['publishInventorySha256'].items():
        if q.a.file_sha(workspace/name)!=digest:raise ValueError('workspace source changed: '+name)
    for name in ('assembly_summary.json','ASSEMBLY_REPORT.md','provenance.json'):
        source=out/'delivery'/'metadata'/name;target=public/name
        if target.exists() and target.read_bytes()!=source.read_bytes():raise ValueError('public artifact already differs: '+name)
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    target=public/'download_manifest.json'
    if target.exists() and json.loads(target.read_bytes())!=manifest:raise ValueError('public download manifest conflict')
    pack.atomic_json(target,manifest)
    for name in ('assembly_summary.json','provenance.json','download_manifest.json'):
        if pack.legacy.private_paths(json.loads((public/name).read_bytes())):raise ValueError('private path in final public metadata')
    files=list(plan['publishInventorySha256'])+[f'datasets/{publication_directory}/{n}' for n in ('assembly_summary.json','ASSEMBLY_REPORT.md','provenance.json','download_manifest.json')]
    expected_publish={name:q.a.file_sha(workspace/name) for name in files}
    commit_file=out/'publication_commit.json'
    def git(*args):return subprocess.check_output(['git','-c','http.proxy=','-c','https.proxy=',*args],cwd=workspace,text=True).strip()
    remote=git('ls-remote','origin','refs/heads/main').split()[0]
    if commit_file.exists():
        commit=json.loads(commit_file.read_bytes())['commit']
        if git('rev-parse','HEAD')!=commit or remote not in (commit,plan['baseGitCommit']):raise ValueError('Git changed since publication commit')
    else:
        if git('rev-parse','HEAD')!=plan['baseGitCommit'] or remote!=plan['baseGitCommit']:raise ValueError('Git HEAD/remote changed; no automatic merge or force push')
        if git('diff','--cached','--name-only'):raise ValueError('user staged changes present; leave index untouched')
        for name in files:
            if (workspace/name).stat().st_size>=45_000_000:raise ValueError('artifact too large for source history')
        subprocess.run(['git','add','--',*files],cwd=workspace,check=True)
        subprocess.run(['git','commit','--only','-m','算法：Q4 全量 80000 模型拼接、修复与独立物理筛查','--',*files],cwd=workspace,check=True)
        commit=git('rev-parse','HEAD');pack.atomic_json(commit_file,{'commit':commit})
    # Recheck the committed content too; accept Git's CRLF/LF text normalization,
    # never concurrent source changes or accidental staging of different content.
    for name,digest in expected_publish.items():
        raw=(workspace/name).read_bytes()
        blob=subprocess.check_output(['git','show',commit+':'+name],cwd=workspace)
        if q.a.sha(raw)!=digest or raw.replace(b'\r\n',b'\n')!=blob.replace(b'\r\n',b'\n'):raise ValueError('publication content changed during commit')
    if remote!=commit:subprocess.run(['git','-c','http.proxy=','-c','https.proxy=','push',REPOSITORY_URL,'HEAD:main'],cwd=workspace,check=True)
    if git('ls-remote','origin','refs/heads/main').split()[0]!=commit:raise ValueError('pushed commit not visible on remote')
    import github_release as publisher
    publisher.ROOT=workspace;token=publisher.credential();check_original_releases(plan,token)
    publisher.upload(token,out/'delivery'/'download_manifest.json',out/'delivery',3,commit,
                     proof_path=public/'release_verification.json')
    check_original_releases(plan,token)
    proof=json.loads((public/'release_verification.json').read_bytes())
    if not proof['published'] or proof['assetCount']!=81 or not proof['allRemoteAssetSizesAndSha256Passed']:raise ValueError('publication not fully verified')
    # The release proof is its own small, scoped follow-up commit. Never include unrelated changes.
    proof_name=f'datasets/{publication_directory}/release_verification.json'
    if git('rev-parse','HEAD')!=commit or git('diff','--cached','--name-only'):raise ValueError('Git changed during upload; proof retained locally')
    subprocess.run(['git','add','--',proof_name],cwd=workspace,check=True)
    if git('diff','--cached','--name-only'):
        subprocess.run(['git','commit','--only','-m','校验：Q4 发布资源 SHA256 与旧发布完整性','--',proof_name],cwd=workspace,check=True)
        subprocess.run(['git','-c','http.proxy=','-c','https.proxy=','push',REPOSITORY_URL,'HEAD:main'],cwd=workspace,check=True)
    return proof


def run(args):
    out=args.out.resolve();plan=json.loads((out/'plan.json').read_bytes());plan_sha=q.a.file_sha(out/'plan.json')
    if plan['workflowVersion']!=VERSION or Path(plan['out'])!=out:raise ValueError('plan identity changed')
    if ROOT.resolve()!=(out/'source_snapshot').resolve():raise ValueError('run using the plan frozen source_snapshot/tools/run_quality_full.py')
    for name,digest in plan['runtimeSourceCodeSha256'].items():
        if q.a.file_sha(ROOT/name)!=digest:raise ValueError('frozen runtime changed')
    for shard,meta in plan['sourceInputs'].items():
        dataset=Path(next(j['datasetPath'] for j in plan['jobs'] if j['shardId']==shard))
        if q.a.file_sha(dataset/'manifest.json')!=meta['manifestSha256'] or q.a.file_sha(meta['baselineIndexPath'])!=meta['baselineIndexSha256']:raise ValueError('source metadata changed')
    if len(plan['jobs'])!=80000 or len({j['modelId'] for j in plan['jobs']})!=80000:raise ValueError('incomplete census plan')
    handle=lock_run(out);rows=[];current=[]
    try:
        previous=json.loads((out/'status.json').read_bytes())
        if previous['phase']=='complete':
            print('Q4_CENSUS_ALREADY_COMPLETE',previous.get('releaseUrl'),flush=True)
            return
        by_shard={s:[j for j in plan['jobs'] if j['shardId']==s] for s in ('A','B')}
        worker_plan={k:plan[k] for k in ('options','algorithmSourceCodeSha256')}
        with ProcessPoolExecutor(max_workers=plan['workers'],max_tasks_per_child=100,
                                 initializer=initialize_worker,initargs=(worker_plan,str(out),plan_sha)) as pool:
            for number in range(1,41):
                for shard in ('A','B'):
                    jobs=by_shard[shard][(number-1)*1000:number*1000]
                    checkpoint=out/'delivery'/'checkpoints'/shard/f'{number:02d}.json'
                    if checkpoint.exists():
                        proof=pack.make_package(out,shard,number,jobs,plan['releaseTag'],plan_sha);rows.extend(proof['rows']);continue
                    if shutil.disk_usage(out).free<12_000_000_000:raise RuntimeError('insufficient free disk; checkpoints retained, no automatic deletion')
                    status(out,'processing',rows,currentShard=shard,currentPackage=number,releaseTag=plan['releaseTag'])
                    iterator=iter(jobs);pending={};current=[];last_update=time.monotonic()
                    def refill():
                        while len(pending)<plan['workers']*2:
                            try:job=next(iterator)
                            except StopIteration:break
                            pending[pool.submit(compute,job)]=job['modelId']
                    refill()
                    while pending:
                        completed,_=wait(pending,timeout=5,return_when=FIRST_COMPLETED)
                        for future in completed:
                            model_id=pending.pop(future);row=future.result()
                            if row['modelId']!=model_id:raise ValueError('worker identity mismatch')
                            current.append(row)
                        refill()
                        if time.monotonic()-last_update>=10 or not pending:
                            status(out,'processing',rows+current,currentShard=shard,currentPackage=number,releaseTag=plan['releaseTag'])
                            print('Q4_CENSUS_PROGRESS',len(rows)+len(current),'/',80000,'geometry',sum(r.get('geometryPassed',r['status']=='success') for r in rows+current),flush=True)
                            last_update=time.monotonic()
                    status(out,'sealing_package',rows+current,currentShard=shard,currentPackage=number,releaseTag=plan['releaseTag'])
                    proof=pack.make_package(out,shard,number,jobs,plan['releaseTag'],plan_sha);rows.extend(proof['rows'])
                    current=[]
                    print('Q4_CENSUS_PACKAGE_SEALED',shard,number,flush=True)
        status(out,'finalizing',rows,releaseTag=plan['releaseTag'])
        summary,manifest=pack.finalize(out,plan,plan_sha)
        pack.atomic_json(out/'full_verification.json',summary)
        if plan['publishAfterFullVerification']:
            status(out,'uploading',rows,releaseTag=plan['releaseTag'])
            proof=publish(out,plan,summary,manifest)
            status(out,'complete',rows,releaseTag=plan['releaseTag'],releaseUrl=proof['releaseUrl'],allRemoteAssetSizesAndSha256Passed=True)
        else:status(out,'ready_to_publish',rows,releaseTag=plan['releaseTag'])
    except BaseException as error:
        status(out,'needs_attention',rows+current,releaseTag=plan['releaseTag'],errorType=type(error).__name__,error=str(error),checkpointsPreserved=True)
        traceback.print_exc();raise
    finally:handle.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('init','run','status'))
    p.add_argument('--out',type=Path,required=True);p.add_argument('--dataset-a',type=Path);p.add_argument('--dataset-b',type=Path)
    p.add_argument('--index-a',type=Path);p.add_argument('--index-b',type=Path)
    p.add_argument('--tag',default='lego-assembly-q4-ab-80000-20261011-v1');p.add_argument('--workers',type=int,default=12)
    p.add_argument('--publish-after-verify',action='store_true')
    args=p.parse_args()
    if args.action=='init':
        if not all((args.dataset_a,args.dataset_b,args.index_a,args.index_b)) or not 1<=args.workers<=16:p.error('four source paths and 1..16 workers required')
        prepare(args)
    elif args.action=='run':run(args)
    else:print((args.out/'status.json').read_text(encoding='utf8'),flush=True)


if __name__=='__main__':main()
