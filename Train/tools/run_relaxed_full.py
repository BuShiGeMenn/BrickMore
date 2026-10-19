"""Frozen 80k grounded modular census; sealed readback before a separate release."""
from concurrent.futures import ProcessPoolExecutor,as_completed
from datetime import datetime,timezone
import argparse
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
import zipfile

import package_quality as pack
import run_quality_full as legacy
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'algorithms/voxel_assembly_relaxed'))
import relaxed_pipeline as p
q=p.q
VERSION='grounded_modular_census_delivery_v1'
_PLAN=None;_OUT=None;_PLAN_SHA=None


def initialize(light,out,sha):
    global _PLAN,_OUT,_PLAN_SHA
    if p.hashes()!=light['algorithmSourceCodeSha256']:raise ValueError('modular worker source changed')
    p._HASHES=light['algorithmSourceCodeSha256'];_PLAN=light;_OUT=Path(out);_PLAN_SHA=sha


def compute(task):
    job,options=task;source=Path(job['datasetPath'])/job['modelPath']/'model.json'
    if q.a.file_sha(source)!=job['originalModelFileSha256'] or q.a.file_sha(source.parent/'prompts.json')!=job['originalPromptFileSha256']:
        raise ValueError('original model/prompt differs from published ZIP bytes')
    folder=_OUT/'models'/job['category']/job['modelId']
    if folder.exists():
        report=p.verify(folder,source);workflow=json.loads((folder/'workflow.json').read_bytes())
        if workflow['planSha256']!=_PLAN_SHA or workflow['reportSha256']!=q.a.file_sha(folder/'report.json'):raise ValueError('modular checkpoint changed')
    else:
        stage=_OUT/'staging'/job['modelId']
        if stage.exists():
            import uuid
            target=_OUT/'interrupted_staging'/(job['modelId']+'_'+uuid.uuid4().hex)
            if not stage.resolve().is_relative_to((_OUT/'staging').resolve()) or not target.resolve().is_relative_to((_OUT/'interrupted_staging').resolve()):raise ValueError('unsafe staging recovery path')
            target.parent.mkdir(parents=True,exist_ok=True);stage.rename(target)
        report=p.worker((job,job['datasetPath'],str(stage),options))
        staged=stage/'models'/job['category']/job['modelId'];p.verify(staged,source)
        pack.atomic_json(staged/'workflow.json',dict(planSha256=_PLAN_SHA,origin=report['origin'],actualOptions=report['options'],reportSha256=q.a.file_sha(staged/'report.json'),elapsedSeconds=report['elapsedSeconds']))
        folder.parent.mkdir(parents=True,exist_ok=True);staged.rename(folder)
    if report['sourceCodeSha256']!=_PLAN['algorithmSourceCodeSha256']:raise ValueError('modular generation differs')
    return dict(modelId=report['modelId'],status=report['status'],qualityScreenedSuccess=report['qualityScreenedSuccess'],physicsStatus=report['physics']['status'],
                finalGravityEquilibriumPassed=report['physics']['gravityEquilibriumPassed'],changeRatio=report['repairAudit']['changeRatio'])


def prepare(args):
    old_path=args.from_plan.resolve();old=json.loads(old_path.read_bytes());out=args.out.resolve()
    if Path(old['out']).resolve()!=old_path.parent or Path(old['workspace']).resolve()!=ROOT:raise ValueError('previous plan workspace identity differs')
    first_proof=json.loads((old_path.parent/'delivery/checkpoints/A/01.json').read_bytes())
    if first_proof['runPlanSha256']!=q.a.file_sha(old_path):raise ValueError('previous plan differs from sealed package proof')
    for name,digest in old['runtimeSourceCodeSha256'].items():
        if q.a.file_sha(old_path.parent/'source_snapshot'/name)!=digest:raise ValueError('old frozen runtime changed')
    for name,digest in old['originalReleaseManifestSha256'].items():
        if q.a.file_sha(ROOT/name)!=digest:raise ValueError('original release manifest changed')
    if not out.is_relative_to(ROOT/'downloads') or out==ROOT/'downloads' or out.exists():raise ValueError('new dedicated output required')
    if len(old['jobs'])!=80000 or len({j['modelId'] for j in old['jobs']})!=80000:raise ValueError('incomplete original census')
    if shutil.disk_usage(ROOT).free<25_000_000_000:raise ValueError('25 GB free required')
    if subprocess.check_output(['git','remote','get-url','origin'],cwd=ROOT,text=True).strip()!=legacy.REPOSITORY_URL:raise ValueError('unauthorized Git remote')
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()!=old['baseGitCommit']:raise ValueError('Git changed since original plan')
    for shard,meta in old['sourceInputs'].items():
        dataset=Path(next(j['datasetPath'] for j in old['jobs'] if j['shardId']==shard))
        if q.a.file_sha(dataset/'manifest.json')!=meta['manifestSha256'] or q.a.file_sha(meta['baselineIndexPath'])!=meta['baselineIndexSha256']:raise ValueError('original source metadata changed')
    jobs=old['jobs'];prior_out=Path(old['out']);known=[]
    manifest=json.loads((prior_out/'delivery/download_manifest.json').read_bytes())
    asset=next(a for a in manifest['assets'] if a['kind']=='metadata');archive=prior_out/'delivery'/asset['sourceRelativePath']
    if archive.stat().st_size!=asset['bytes'] or pack.legacy.digest(archive)!=asset['sha256']:raise ValueError('completed strict metadata archive changed')
    with zipfile.ZipFile(archive) as z:
        summary=json.loads(z.read('assembly_summary.json'))
        if summary['runPlanSha256']!=q.a.file_sha(old_path) or summary['processedModelCount']!=80000 or not summary['allPublicZipCrcShaGeometryRepairGateAndPhysicsReadbackPassed']:
            raise ValueError('strict metadata is not a sealed complete census')
        previous_rows={row['modelId']:row for row in map(json.loads,z.read('assembly_index.jsonl').decode('utf8').splitlines())}
    if set(previous_rows)!={j['modelId'] for j in jobs}:raise ValueError('strict index IDs differ from original plan')
    for job in jobs:
        if any(not re.fullmatch(r'[A-Za-z0-9_-]+',job[k]) for k in ('modelId','category')) or Path(job['modelPath']).as_posix()!=f'models/{job["category"]}/{job["modelId"]}':raise ValueError('unsafe model path')
        job['priorStrictFolder']=str(prior_out/'models'/job['category']/job['modelId'])
        previous=previous_rows[job['modelId']]
        if previous['sourceFileSha256']!=job['originalModelFileSha256'] or previous['sourcePromptFileSha256']!=job['originalPromptFileSha256']:raise ValueError('strict index original byte binding differs')
        if previous['status']=='success':known.append(dict(modelId=job['modelId'],status='success',priorPublicReportSha256=previous['reportFileSha256']))
    runtime={name:q.a.file_sha(ROOT/name) for name in old['runtimeSourceCodeSha256']}
    runtime.update(p.hashes())
    for name in ('tools/run_relaxed_full.py','tools/benchmark_relaxed.py','tools/test_relaxed_delivery.py'):
        runtime[name]=q.a.file_sha(ROOT/name)
    inventory=legacy.inventory(ROOT)
    for name in runtime:inventory[name]=q.a.file_sha(ROOT/name)
    for name in ('datasets/relaxed_assembly_80000/README.md','datasets/relaxed_assembly_80000/tests.json'):
        inventory[name]=q.a.file_sha(ROOT/name)
    deadline=datetime.fromisoformat(args.deadline.replace('Z','+00:00')).timestamp()
    if deadline<=time.time():raise ValueError('future deadline required')
    plan={**old,'workflowVersion':VERSION,'out':str(out),'jobs':jobs,'releaseTag':args.tag,'algorithmVersion':p.VERSION,
          'auditorName':'relaxed_pipeline','geometryPolicy':p.r.POLICY,'options':dict(ratio=.02,seconds=args.seconds,physicsSeconds=5.),
          'workers':args.workers,'epochModels':args.workers*16,'packageWorkers':3,'algorithmSourceCodeSha256':p.hashes(),
          'runtimeSourceCodeSha256':runtime,'publishInventorySha256':inventory,'retainedPreviousOutcomes':known,
          'deadlineUtc':args.deadline,'deadlineEpoch':deadline,'publishAfterFullVerification':True,
          'reusePolicy':'fresh independent verification preserves original and prior strict successes; modular successes require actual stud paths to floor in every component; source/prompt bytes unchanged',
          'schedulerPolicy':dict(deadlineUtc=args.deadline,geometryGoal=.6,initialSearchSeconds=args.seconds,reservedUploadSeconds=7200,physicsAssumptionsUnchanged=True),
          'previousPlanSha256':q.a.file_sha(old_path),'previousCensusRuntimeSourceCodeSha256':old['runtimeSourceCodeSha256'],
          'retainedPreviousRuntimeSnapshotPath':str(prior_out/'source_snapshot'),'startedAtUtc':datetime.now(timezone.utc).isoformat()}
    out.mkdir(parents=True);pack.atomic_json(out/'plan.json',plan)
    for name,digest in runtime.items():
        if q.a.file_sha(ROOT/name)!=digest:raise ValueError('source changed while freezing')
        target=out/'source_snapshot'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
    pack.atomic_json(out/'status.json',dict(phase='planned',modelCount=80000,processedModelCount=0,deadlineUtc=args.deadline,
                     knownStrictGeometryPassed=len(known),releaseTag=args.tag,planSha256=q.a.file_sha(out/'plan.json')))
    print('MODULAR_PLAN_FROZEN',len(known),'known strict successes retained',flush=True)


def update(out,phase,rows,plan,**extra):
    legacy.status(out,phase,rows,workflowVersion=VERSION,geometryTier='relaxed_modular_grounded_not_physical_certification',
                  deadlineUtc=plan['deadlineUtc'],releaseTag=plan['releaseTag'],**extra)


def run(args):
    out=args.out.resolve();plan=json.loads((out/'plan.json').read_bytes());sha=q.a.file_sha(out/'plan.json')
    if ROOT!=(out/'source_snapshot').resolve() or plan['workflowVersion']!=VERSION or Path(plan['out'])!=out:raise ValueError('use exact frozen modular runtime')
    for name,digest in plan['runtimeSourceCodeSha256'].items():
        if q.a.file_sha(ROOT/name)!=digest:raise ValueError('frozen modular source changed')
    handle=legacy.lock_run(out);rows=[];current=[];started=time.monotonic();budget=plan['options']['seconds']
    try:
        if json.loads((out/'status.json').read_bytes())['phase']=='complete':return
        by_shard={s:[j for j in plan['jobs'] if j['shardId']==s] for s in ('A','B')}
        light={k:plan[k] for k in ('algorithmSourceCodeSha256',)}
        for number in range(1,41):
            for shard in ('A','B'):
                jobs=by_shard[shard][(number-1)*1000:number*1000];checkpoint=out/'delivery/checkpoints'/shard/f'{number:02d}.json'
                if checkpoint.exists():
                    rows.extend(pack.make_package(out,shard,number,jobs,plan['releaseTag'],sha,auditor_name='relaxed_pipeline')['rows']);continue
                if shutil.disk_usage(out).free<12_000_000_000:raise RuntimeError('insufficient disk space; checkpoints retained')
                if len(rows)>=2000:
                    rate=len(rows)/max(.001,time.monotonic()-started);needed=(80000-len(rows))/rate
                    available=max(1.,plan['deadlineEpoch']-time.time()-7200.)
                    if needed>available:budget=max(2.,budget*available/needed)
                options={**plan['options'],'seconds':budget};current=[];last=time.monotonic()
                update(out,'processing',rows,plan,currentShard=shard,currentPackage=number,activeSearchOptions=options)
                for first in range(0,len(jobs),plan['epochModels']):
                    with ProcessPoolExecutor(max_workers=plan['workers'],initializer=initialize,initargs=(light,str(out),sha)) as pool:
                        futures=[pool.submit(compute,(job,options)) for job in jobs[first:first+plan['epochModels']]]
                        for future in as_completed(futures):
                            current.append(future.result())
                            if time.monotonic()-last>=10:
                                update(out,'processing',rows+current,plan,currentShard=shard,currentPackage=number,activeSearchOptions=options,
                                       modelsPerSecondIncludingPackaging=(len(rows)+len(current))/max(.001,time.monotonic()-started))
                                print('MODULAR_PROGRESS',len(rows)+len(current),'/80000 geometry',sum(r['status']=='success' for r in rows+current),flush=True);last=time.monotonic()
                update(out,'sealing_package',rows+current,plan,currentShard=shard,currentPackage=number)
                with ProcessPoolExecutor(max_workers=plan['packageWorkers']) as audit_pool:
                    proof=pack.make_package(out,shard,number,jobs,plan['releaseTag'],sha,audit_pool=audit_pool,auditor_name='relaxed_pipeline')
                rows.extend(proof['rows']);current=[];print('MODULAR_PACKAGE_SEALED',shard,number,flush=True)
        update(out,'finalizing',rows,plan);summary,manifest=pack.finalize(out,plan,sha)
        pack.atomic_json(out/'full_verification.json',summary)
        update(out,'uploading',rows,plan);proof=legacy.publish(out,plan,summary,manifest,publication_directory='relaxed_assembly_80000')
        update(out,'complete',rows,plan,releaseUrl=proof['releaseUrl'],geometryGoalAchieved=summary['geometryGoalAchieved'],
               finishedBeforeDeadline=time.time()<=plan['deadlineEpoch'],allRemoteAssetSizesAndSha256Passed=True)
    except BaseException as error:
        update(out,'needs_attention',rows+current,plan,errorType=type(error).__name__,error=str(error),checkpointsPreserved=True)
        traceback.print_exc();raise
    finally:handle.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('init','run','status'))
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--from-plan',type=Path)
    parser.add_argument('--deadline',default='2026-10-12T14:09:29Z');parser.add_argument('--workers',type=int,default=8)
    parser.add_argument('--seconds',type=float,default=8.);parser.add_argument('--tag',default='lego-modular-grounded-ab-80000-20261012-v1')
    args=parser.parse_args()
    if not 1<=args.workers<=12 or not 0<args.seconds<=30:parser.error('safe worker/search bounds required')
    if args.action=='init':
        if args.from_plan is None:parser.error('--from-plan required')
        prepare(args)
    elif args.action=='run':run(args)
    else:print((args.out/'status.json').read_text(encoding='utf8'))


if __name__=='__main__':main()
