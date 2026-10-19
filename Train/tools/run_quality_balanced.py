"""Deadline-aware Q4 scheduling, retaining audited earlier outcomes unchanged."""
import argparse
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shutil
import subprocess
import time
import traceback

import run_quality_full as core
import balanced_quality_seed as seed
pack=core.pack;e=core.e;q=core.q
ROOT=Path(__file__).resolve().parent.parent
VERSION='deadline_balanced_q4_scheduler_v2_fast_seed'
_WORKER=None


def utc(value):
    return datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()


def profile(now,deadline,remaining,workers,initial_total=5.):
    """Search limits only. Never alter geometry, edit or physics predicates."""
    usable=max(0.,deadline-now-7200.)  # reserve two hours for final delivery/upload
    total=min(initial_total,max(.5,usable*workers/max(1,remaining)*.85))
    return dict(ratio=.02,additionsSeconds=round(total*.4,4),seconds=round(total*.6,4),
                physicsSeconds=5.,candidateLimit=80000,cutRounds=16)


def validate_previous(previous):
    path=Path(previous).resolve();plan=json.loads(path.read_bytes())
    if plan['workflowVersion']!=core.VERSION or Path(plan['out']).resolve()!=path.parent:
        raise ValueError('previous census identity changed')
    if plan['algorithmSourceCodeSha256']!=e.hashes():raise ValueError('previous Q4 generation differs')
    if len(plan['jobs'])!=80000 or len({j['modelId'] for j in plan['jobs']})!=80000:
        raise ValueError('previous census is incomplete')
    for name,digest in plan['runtimeSourceCodeSha256'].items():
        if q.a.file_sha(path.parent/'source_snapshot'/name)!=digest:raise ValueError('previous frozen runtime changed')
    for name,digest in plan['originalReleaseManifestSha256'].items():
        if q.a.file_sha(ROOT/name)!=digest:raise ValueError('original release metadata changed')
    for shard,meta in plan['sourceInputs'].items():
        dataset=Path(next(j['datasetPath'] for j in plan['jobs'] if j['shardId']==shard))
        if q.a.file_sha(dataset/'manifest.json')!=meta['manifestSha256'] or q.a.file_sha(meta['baselineIndexPath'])!=meta['baselineIndexSha256']:
            raise ValueError('original source/baseline metadata changed')
    return path,plan


def initialize_worker(light,out,plan_sha):
    global _WORKER
    _WORKER=light
    core.initialize_worker(light,out,plan_sha)


def run_epochs(jobs,options,light,out,plan_sha,workers,recycle):
    """Explicit pool lifetimes avoid Python 3.12 max_tasks_per_child stalls."""
    for start in range(0,len(jobs),workers*recycle):
        epoch=jobs[start:start+workers*recycle];iterator=iter(epoch);pending={}
        with ProcessPoolExecutor(max_workers=workers,initializer=initialize_worker,
                                 initargs=(light,str(out),plan_sha)) as pool:
            def refill():
                while len(pending)<workers*2:
                    try:job=next(iterator)
                    except StopIteration:break
                    pending[pool.submit(compute,(job,options))]=job['modelId']
            refill()
            while pending:
                done,_=wait(pending,timeout=5,return_when=FIRST_COMPLETED)
                if not done:
                    yield None;continue
                for future in done:
                    model_id=pending.pop(future);row=future.result()
                    if row['modelId']!=model_id:raise ValueError('balanced worker identity mismatch')
                    yield row
                refill()


def compute(task):
    job,options=task;core._PLAN['options']=options
    folder=core._OUT/'models'/job['category']/job['modelId']
    if job.get('retainedQ4Path') and not folder.exists():
        prior=Path(job['retainedQ4Path']);source=Path(job['datasetPath'])/job['modelPath']/'model.json'
        if q.a.file_sha(prior/'report.json')!=job['retainedQ4ReportSha256']:raise ValueError('retained Q4 report changed')
        if q.a.file_sha(source)!=job['originalModelFileSha256'] or q.a.file_sha(source.parent/'prompts.json')!=job['originalPromptFileSha256']:
            raise ValueError('retained original differs from published ZIP bytes')
        row=e.verify(prior,source)
        if row['sourceCodeSha256']!=_WORKER['algorithmSourceCodeSha256']:raise ValueError('retained Q4 generation changed')
        stage=core._OUT/'retained_staging'/job['modelId']
        if stage.exists():raise ValueError('incomplete retained copy; inspect before recovery')
        stage.mkdir(parents=True)
        for name in [*row['outputFileSha256'],'report.json']:shutil.copyfile(prior/name,stage/name)
        pack.atomic_json(stage/'workflow.json',dict(planSha256=core._PLAN_SHA,origin='verified_previous_census',
                         cachedReportSha256=job['retainedQ4ReportSha256'],actualOptions=row['options'],
                         reportSha256=q.a.file_sha(stage/'report.json'),elapsedSeconds=0.,
                         retainedPlanSha256=_WORKER['previousPlanSha256'],balancedPolicyVersion=VERSION))
        folder.parent.mkdir(parents=True,exist_ok=True);stage.rename(folder)
    return core.compute(job,worker_fn=seed.worker)


def prepare(args):
    previous,old=validate_previous(args.from_plan);out=args.out.resolve()
    if not out.is_relative_to(ROOT/'downloads') or out==ROOT/'downloads' or out.exists():
        raise ValueError('new dedicated downloads child required')
    if shutil.disk_usage(ROOT).free<25_000_000_000:raise ValueError('at least 25 GB free required')
    if subprocess.check_output(['git','remote','get-url','origin'],cwd=ROOT,text=True).strip()!=core.REPOSITORY_URL:
        raise ValueError('remote outside authorized repository')
    for name,expected in (('HEAD',old['baseGitCommit']),):
        if subprocess.check_output(['git','rev-parse',name],cwd=ROOT,text=True).strip()!=expected:raise ValueError('Git changed since previous plan')
    previous_sha=q.a.file_sha(previous);algorithm_hashes=e.hashes()
    jobs=old['jobs'];by_id={j['modelId']:j for j in jobs};retained=[]
    for report_path in sorted((previous.parent/'models').glob('*/*/report.json')):
        job=by_id[report_path.parent.name];report=json.loads(report_path.read_bytes())
        workflow=json.loads((report_path.parent/'workflow.json').read_bytes())
        if workflow['planSha256']!=previous_sha or workflow['reportSha256']!=q.a.file_sha(report_path):
            raise ValueError('previous result checkpoint changed')
        if report['sourceCodeSha256']!=algorithm_hashes or report['modelId']!=job['modelId']:raise ValueError('retained generation/ID differs')
        job.update(retainedQ4Path=str(report_path.parent),retainedQ4ReportSha256=q.a.file_sha(report_path))
        retained.append(dict(modelId=job['modelId'],status=report['status'],reportSha256=job['retainedQ4ReportSha256']))
    runtime={name:q.a.file_sha(ROOT/name) for name in old['runtimeSourceCodeSha256']}
    for name in ('tools/run_quality_balanced.py','tools/test_quality_balanced.py','tools/balanced_quality_seed.py'):
        runtime[name]=q.a.file_sha(ROOT/name)
    owned=core.inventory(ROOT)
    for name in ('tools/run_quality_balanced.py','tools/test_quality_balanced.py','tools/balanced_quality_seed.py','datasets/q4_assembly_80000/balanced_tests.json'):
        owned[name]=q.a.file_sha(ROOT/name)
    now=time.time();deadline=utc(args.deadline)
    if not math.isfinite(deadline) or deadline<=now:raise ValueError('future deadline required')
    options=profile(now,deadline,80000-len(retained),args.workers,args.search_seconds)
    plan={**old,'workflowVersion':VERSION,'out':str(out),'releaseTag':args.tag,'workers':args.workers,
          'options':options,'runtimeSourceCodeSha256':runtime,'publishInventorySha256':owned,
          'previousPlanSha256':previous_sha,'previousCensusRuntimeSourceCodeSha256':old['runtimeSourceCodeSha256'],
          'retainedPreviousRuntimeSnapshotPath':str(previous.parent/'source_snapshot'),
          'retainedPreviousOutcomes':retained,'deadlineUtc':args.deadline,'deadlineEpoch':deadline,
          'initialSearchSeconds':args.search_seconds,'maxTasksPerChild':args.recycle,
          'packageWorkers':args.package_workers,'publishAfterFullVerification':True,
          'schedulerPolicy':dict(version=VERSION,deadlineUtc=args.deadline,reservedDeliveryUploadSeconds=7200,
                                 computeWorkers=args.workers,packageWorkers=args.package_workers,
                                 explicitRecycleEpochModels=args.workers*args.recycle,
                                 initialSearchSeconds=args.search_seconds,onlySearchBudgetAdaptive=True,
                                 fastAdditionsStageVersion=seed.VERSION,
                                 incompleteSearchNeverMeansGeometricInfeasibility=True,certifiedRealWorldPhysics=False),
          'startedAtUtc':datetime.now(timezone.utc).isoformat(),
          'reusePolicy':'previous completed Q4 successes AND drafts retained byte-for-byte; original/sample successes retained; only search time is adaptive; 2% edit/unchanged color/geometry/physics audits unchanged'}
    out.mkdir(parents=True);pack.atomic_json(out/'plan.json',plan)
    for name,digest in runtime.items():
        if q.a.file_sha(ROOT/name)!=digest:raise ValueError('runtime changed during freeze')
        target=out/'source_snapshot'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
    pack.atomic_json(out/'status.json',dict(phase='planned',workflowVersion=VERSION,modelCount=80000,
                     processedModelCount=0,retainedModelCount=len(retained),deadlineUtc=args.deadline,
                     releaseTag=args.tag,planSha256=q.a.file_sha(out/'plan.json')))
    pack.atomic_json(previous.parent/'reconfiguration.json',dict(oldRunnerStopped=True,oldOutputsPreserved=True,
                     replacementStatus=str(out/'status.json'),replacementPlanSha256=q.a.file_sha(out/'plan.json'),reason='user requested balanced completion within approximately twelve hours'))
    previous_status=json.loads((previous.parent/'status.json').read_bytes())
    pack.atomic_json(previous.parent/'status.json',{**previous_status,'phase':'superseded_by_balanced_run',
                     'completedOutputFolderCount':len(retained),'outputsPreserved':True,'replacementStatus':str(out/'status.json')})
    print('BALANCED_PLAN_FROZEN',len(retained),'retained',options,flush=True)


def benchmark(args):
    previous,plan=validate_previous(args.from_plan);out=args.out.resolve()
    if not out.is_relative_to(ROOT/'downloads') or out.exists():raise ValueError('new benchmark directory required')
    jobs=sorted(plan['jobs'],key=lambda j:q.a.sha(('balanced-speed-39871'+j['modelId']).encode()))[:args.count]
    options=dict(ratio=.02,additionsSeconds=args.search_seconds*.4,seconds=args.search_seconds*.6,
                 physicsSeconds=5.,candidateLimit=80000,cutRounds=16)
    light=dict(options=options,algorithmSourceCodeSha256=e.hashes(),previousPlanSha256=q.a.file_sha(previous))
    out.mkdir(parents=True);pack.atomic_json(out/'config.json',dict(options=options,sourceCodeSha256=e.hashes(),
                     workers=args.workers,maxTasksPerChild=args.recycle,selection=[j['modelId'] for j in jobs]))
    started=time.monotonic();rows=[]
    for row in run_epochs(jobs,options,light,out,'benchmark-not-census',args.workers,args.recycle):
        if row is not None:rows.append(row)
    elapsed=time.monotonic()-started;packing_started=time.monotonic()
    with ProcessPoolExecutor(max_workers=args.package_workers) as audit_pool:
        for shard in ('A','B'):
            selected=[j for j in jobs if j['shardId']==shard]
            if selected:pack.make_package(out,shard,1,selected,'balanced-benchmark-not-published','benchmark-not-census',audit_pool=audit_pool)
    packing_elapsed=time.monotonic()-packing_started
    result=dict(modelCount=len(rows),elapsedSeconds=elapsed,modelsPerSecond=len(rows)/elapsed,
                geometryPassed=sum(r['status']=='success' for r in rows),gravityScreenedPassed=sum(r['qualityScreenedSuccess'] for r in rows),
                options=options,workers=args.workers,maxTasksPerChild=args.recycle,
                projectedComputeHours=80000*elapsed/len(rows)/3600,
                actualZipPackagingAndReadbackSeconds=packing_elapsed,
                projectedPackagingHours=80000*packing_elapsed/len(rows)/3600,
                benchmarkIsNotPopulationPassRate=True,rows=rows)
    pack.atomic_json(out/'benchmark.json',result);print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)


def update(out,phase,rows,plan,**extra):
    core.status(out,phase,rows,workflowVersion=VERSION,deadlineUtc=plan['deadlineUtc'],
                retainedPreviousModelCount=len(plan['retainedPreviousOutcomes']),**extra)


def run(args):
    out=args.out.resolve();plan=json.loads((out/'plan.json').read_bytes());plan_sha=q.a.file_sha(out/'plan.json')
    if plan['workflowVersion']!=VERSION or Path(plan['out'])!=out or ROOT!=(out/'source_snapshot').resolve():
        raise ValueError('execute exact frozen balanced runtime')
    for name,digest in plan['runtimeSourceCodeSha256'].items():
        if q.a.file_sha(ROOT/name)!=digest:raise ValueError('balanced frozen runtime changed')
    if e.hashes()!=plan['algorithmSourceCodeSha256']:raise ValueError('Q4 source changed')
    for shard,meta in plan['sourceInputs'].items():
        dataset=Path(next(j['datasetPath'] for j in plan['jobs'] if j['shardId']==shard))
        if q.a.file_sha(dataset/'manifest.json')!=meta['manifestSha256'] or q.a.file_sha(meta['baselineIndexPath'])!=meta['baselineIndexSha256']:
            raise ValueError('source metadata changed after balanced freeze')
    handle=core.lock_run(out);rows=[];current=[]
    try:
        if json.loads((out/'status.json').read_bytes())['phase']=='complete':return
        by_shard={s:[j for j in plan['jobs'] if j['shardId']==s] for s in ('A','B')}
        light={k:plan[k] for k in ('options','algorithmSourceCodeSha256','previousPlanSha256')}
        started=time.monotonic()
        if True:
            for number in range(1,41):
                for shard in ('A','B'):
                    jobs=by_shard[shard][(number-1)*1000:number*1000]
                    checkpoint=out/'delivery'/'checkpoints'/shard/f'{number:02d}.json'
                    if checkpoint.exists():
                        proof=pack.make_package(out,shard,number,jobs,plan['releaseTag'],plan_sha)
                        rows.extend(proof['rows']);continue
                    if shutil.disk_usage(out).free<12_000_000_000:raise RuntimeError('insufficient disk space; preserve checkpoints')
                    current=[];last_update=time.monotonic()
                    options=profile(time.time(),plan['deadlineEpoch'],80000-len(rows),plan['workers'],plan['initialSearchSeconds'])
                    update(out,'processing',rows,plan,currentShard=shard,currentPackage=number,activeSearchOptions=options,
                           computeWorkers=plan['workers'],packageWorkers=plan['packageWorkers'])
                    for row in run_epochs(jobs,options,light,out,plan_sha,plan['workers'],plan['maxTasksPerChild']):
                        if row is not None:current.append(row)
                        if time.monotonic()-last_update>=10:
                            elapsed=time.monotonic()-started;rate=(len(rows)+len(current))/max(.001,elapsed)
                            update(out,'processing',rows+current,plan,currentShard=shard,currentPackage=number,
                                   activeSearchOptions=options,modelsPerSecondIncludingPackaging=rate,
                                   deadlineExceeded=time.time()>plan['deadlineEpoch'])
                            print('BALANCED_PROGRESS',len(rows)+len(current),'/ 80000','geometry',sum(r['status']=='success' for r in rows+current),flush=True)
                            last_update=time.monotonic()
                    update(out,'sealing_package',rows+current,plan,currentShard=shard,currentPackage=number)
                    with ProcessPoolExecutor(max_workers=plan['packageWorkers']) as audit_pool:
                        proof=pack.make_package(out,shard,number,jobs,plan['releaseTag'],plan_sha,audit_pool=audit_pool)
                    rows.extend(proof['rows']);current=[]
                    print('BALANCED_PACKAGE_SEALED',shard,number,flush=True)
        update(out,'finalizing',rows,plan)
        summary,manifest=pack.finalize(out,plan,plan_sha)
        summary['deadlineUtc']=plan['deadlineUtc'];summary['deadlineMetAtLocalCompletion']=time.time()<=plan['deadlineEpoch']
        # Delivery metadata remains exactly the sealed packager result. Scheduling evidence
        # is separate; never modify already-sealed public summary/ZIP hashes.
        pack.atomic_json(out/'deadline_status.json',dict(deadlineUtc=plan['deadlineUtc'],localDeliveryCompletedUtc=datetime.now(timezone.utc).isoformat(),
                         beforeDeadline=time.time()<=plan['deadlineEpoch'],retainedPreviousModelCount=len(plan['retainedPreviousOutcomes'])))
        pack.atomic_json(out/'full_verification.json',summary)
        update(out,'uploading',rows,plan)
        proof=core.publish(out,plan,summary,manifest)
        update(out,'complete',rows,plan,releaseUrl=proof['releaseUrl'],allRemoteAssetSizesAndSha256Passed=True,
               finishedBeforeDeadline=time.time()<=plan['deadlineEpoch'])
    except BaseException as error:
        update(out,'needs_attention',rows+current,plan,errorType=type(error).__name__,error=str(error),checkpointsPreserved=True)
        traceback.print_exc();raise
    finally:handle.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('benchmark','init','run','status'))
    p.add_argument('--out',type=Path,required=True);p.add_argument('--from-plan',type=Path)
    p.add_argument('--deadline',default='2026-10-12T04:48:57Z')
    p.add_argument('--tag',default='lego-assembly-q4-ab-80000-20261012-balanced-v1')
    p.add_argument('--workers',type=int,default=8);p.add_argument('--package-workers',type=int,default=3)
    p.add_argument('--recycle',type=int,default=8);p.add_argument('--search-seconds',type=float,default=5.)
    p.add_argument('--count',type=int,default=96);args=p.parse_args()
    if not 1<=args.workers<=12 or not 1<=args.package_workers<=4 or not 1<=args.recycle<=32 or not math.isfinite(args.search_seconds) or args.search_seconds<=0:
        p.error('invalid concurrency/search budget')
    if args.action in ('init','benchmark'):
        if args.from_plan is None:p.error('--from-plan required')
        if args.action=='benchmark' and not 1<=args.count<=1000:p.error('1..1000 benchmark models required')
        (prepare if args.action=='init' else benchmark)(args)
    elif args.action=='run':run(args)
    else:print((args.out/'status.json').read_text(encoding='utf8'))


if __name__=='__main__':main()
