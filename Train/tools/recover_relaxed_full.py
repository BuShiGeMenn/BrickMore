"""Versioned recovery: unchanged sealed ZIPs, strict rejection diagnostics, full census."""
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
from datetime import datetime,timezone
import argparse
import json
import re
import shutil
import subprocess
import sys
import time
import traceback
import uuid

import package_quality as pack
import run_quality_full as legacy
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'algorithms/voxel_assembly_relaxed'))
import relaxed_pipeline as p
q=p.q
VERSION='grounded_modular_versioned_recovery_v2'
_PLAN=None;_OUT=None;_PLAN_SHA=None


def initialize(light,out,sha):
    global _PLAN,_OUT,_PLAN_SHA
    if p.hashes()!=light['algorithmSourceCodeSha256']:raise ValueError('recovery worker frozen source changed')
    p._HASHES=light['algorithmSourceCodeSha256'];_PLAN=light;_OUT=Path(out);_PLAN_SHA=sha


def generation(report,workflow,light,sha):
    expected=sha
    if report['sourceCodeSha256']==light['previousModularAlgorithmSourceCodeSha256']:
        expected=light['previousModularPlanSha256']
    elif report['sourceCodeSha256']!=light['algorithmSourceCodeSha256']:
        raise ValueError('unknown recovery source generation')
    if workflow.get('generationPlanSha256',sha)!=expected:raise ValueError('recovery generation lineage differs')


def compute(task):
    job,options=task;source=Path(job['datasetPath'])/job['modelPath']/'model.json'
    if q.a.file_sha(source)!=job['originalModelFileSha256'] or q.a.file_sha(source.parent/'prompts.json')!=job['originalPromptFileSha256']:
        raise ValueError('original published model/prompt bytes differ')
    folder=_OUT/'models'/job['category']/job['modelId']
    if folder.exists():
        report=p.verify(folder,source);workflow=json.loads((folder/'workflow.json').read_bytes())
        if workflow['planSha256']!=_PLAN_SHA or workflow['reportSha256']!=q.a.file_sha(folder/'report.json') or workflow['actualOptions']!=report['options']:raise ValueError('recovery checkpoint changed')
    else:
        stage=_OUT/'staging'/job['modelId']
        if stage.exists():
            target=_OUT/'interrupted_staging'/(job['modelId']+'_'+uuid.uuid4().hex)
            if not stage.resolve().is_relative_to((_OUT/'staging').resolve()) or not target.resolve().is_relative_to((_OUT/'interrupted_staging').resolve()):raise ValueError('unsafe recovery staging path')
            target.parent.mkdir(parents=True,exist_ok=True);stage.rename(target)
        staged=stage/'models'/job['category']/job['modelId'];previous=job.get('retainedModularFolder')
        if previous:
            previous=Path(previous)
            if q.a.file_sha(previous/'report.json')!=job['retainedModularReportSha256'] or q.a.file_sha(previous/'workflow.json')!=job['retainedModularWorkflowSha256']:raise ValueError('preserved unsealed outcome changed')
            report=p.verify(previous,source);old_workflow=json.loads((previous/'workflow.json').read_bytes())
            if old_workflow['planSha256']!=_PLAN['previousModularPlanSha256'] or old_workflow['reportSha256']!=q.a.file_sha(previous/'report.json') or old_workflow['actualOptions']!=report['options'] or report['sourceCodeSha256']!=_PLAN['previousModularAlgorithmSourceCodeSha256']:raise ValueError('preserved partial generation differs')
            shutil.copytree(previous,staged)
            lineage=dict(generationPlanSha256=_PLAN['previousModularPlanSha256'],preservedOriginalWorkflowSha256=job['retainedModularWorkflowSha256'])
        else:
            report=p.worker((job,job['datasetPath'],str(stage),options));lineage=dict(generationPlanSha256=_PLAN_SHA)
        p.verify(staged,source)
        workflow=dict(planSha256=_PLAN_SHA,origin=report['origin'],actualOptions=report['options'],reportSha256=q.a.file_sha(staged/'report.json'),elapsedSeconds=report['elapsedSeconds'],**lineage)
        pack.atomic_json(staged/'workflow.json',workflow)
        folder.parent.mkdir(parents=True,exist_ok=True);staged.rename(folder)
    generation(report,workflow,_PLAN,_PLAN_SHA)
    return dict(modelId=report['modelId'],status=report['status'],qualityScreenedSuccess=report['qualityScreenedSuccess'],physicsStatus=report['physics']['status'],
                finalGravityEquilibriumPassed=report['physics']['gravityEquilibriumPassed'],changeRatio=report['repairAudit']['changeRatio'])


def prepare(args):
    old_path=args.from_plan.resolve();old_out=old_path.parent;old=json.loads(old_path.read_bytes());out=args.out.resolve()
    if Path(old['out']).resolve()!=old_out or Path(old['workspace']).resolve()!=ROOT or old['workflowVersion']!='grounded_modular_census_delivery_v1':raise ValueError('unexpected recovery parent')
    if not old_out.is_relative_to(ROOT/'downloads') or not out.is_relative_to(ROOT/'downloads') or out==ROOT/'downloads' or out.exists():raise ValueError('new scoped recovery directory required')
    if len(old['jobs'])!=80000 or len({j['modelId'] for j in old['jobs']})!=80000:raise ValueError('incomplete parent census')
    if old['deadlineEpoch']<=time.time():raise ValueError('original deadline expired; new user direction required')
    if shutil.disk_usage(ROOT).free<25_000_000_000:raise ValueError('25 GB free required')
    if subprocess.check_output(['git','remote','get-url','origin'],cwd=ROOT,text=True).strip()!=legacy.REPOSITORY_URL or subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()!=old['baseGitCommit']:raise ValueError('authorized Git identity changed')
    changed={'tools/package_quality.py','tools/test_relaxed_delivery.py','algorithms/voxel_assembly_relaxed/modular_gravity.py','algorithms/voxel_assembly_relaxed/relaxed_pipeline.py',
             'datasets/relaxed_assembly_80000/README.md','datasets/relaxed_assembly_80000/tests.json','datasets/q4_assembly_80000/delivery_tests.json','algorithms/voxel_assembly_relaxed/README.md'}
    for name,digest in old['publishInventorySha256'].items():
        if name not in changed and q.a.file_sha(ROOT/name)!=digest:raise ValueError('unrelated workspace source changed: '+name)
    for name,digest in old['runtimeSourceCodeSha256'].items():
        if q.a.file_sha(old_out/'source_snapshot'/name)!=digest:raise ValueError('old frozen runtime changed')
    if old['algorithmSourceCodeSha256']['algorithms/voxel_assembly_relaxed/modular_gravity.py']!=p.physics.PREVIOUS_ADAPTER[1]:raise ValueError('unsupported previous physical adapter')
    for name,digest in old['originalReleaseManifestSha256'].items():
        if q.a.file_sha(ROOT/name)!=digest:raise ValueError('original release manifest changed')
    for shard,meta in old['sourceInputs'].items():
        dataset=Path(next(j['datasetPath'] for j in old['jobs'] if j['shardId']==shard))
        if q.a.file_sha(dataset/'manifest.json')!=meta['manifestSha256'] or q.a.file_sha(meta['baselineIndexPath'])!=meta['baselineIndexSha256']:raise ValueError('original metadata changed')
    inherited={};sealed_ids=set();old_sha=q.a.file_sha(old_path)
    for shard in ('A','B'):
        for number in range(1,41):
            proof_path=old_out/'delivery/checkpoints'/shard/f'{number:02d}.json'
            if not proof_path.exists():continue
            proof=json.loads(proof_path.read_bytes());asset=proof['asset']
            if proof['runPlanSha256']!=old_sha or proof['packagerSha256']!=old['runtimeSourceCodeSha256']['tools/package_quality.py'] or proof['modelCount']!=1000 or not proof['allPublicZipCrcShaGeometryRepairGateAndPhysicsReadbackPassed']:raise ValueError('parent sealed proof differs')
            selected=[j for j in old['jobs'] if j['shardId']==shard][(number-1)*1000:number*1000]
            if [r['modelId'] for r in proof['rows']]!=[j['modelId'] for j in selected]:raise ValueError('parent sealed model order differs')
            sealed_ids.update(r['modelId'] for r in proof['rows'])
            inherited[f'{shard}/{number:02d}']=dict(proofSha256=q.a.file_sha(proof_path),assetSha256=asset['sha256'],assetBytes=asset['bytes'],modelCount=1000)
    jobs=old['jobs'];retained=0
    for job in jobs:
        if any(not re.fullmatch(r'[A-Za-z0-9_-]+',job[k]) for k in ('modelId','category')) or Path(job['modelPath']).as_posix()!=f'models/{job["category"]}/{job["modelId"]}':raise ValueError('unsafe parent model path')
        if job['modelId'] in sealed_ids:continue
        folder=old_out/'models'/job['category']/job['modelId']
        if (folder/'workflow.json').is_file():
            job.update(retainedModularFolder=str(folder),retainedModularReportSha256=q.a.file_sha(folder/'report.json'),retainedModularWorkflowSha256=q.a.file_sha(folder/'workflow.json'));retained+=1
    runtime={name:q.a.file_sha(ROOT/name) for name in old['runtimeSourceCodeSha256']};runtime.update(p.hashes())
    runtime['tools/recover_relaxed_full.py']=q.a.file_sha(__file__)
    inventory={name:q.a.file_sha(ROOT/name) for name in old['publishInventorySha256']};inventory.update(runtime)
    inventory['algorithms/voxel_assembly_relaxed/README.md']=q.a.file_sha(ROOT/'algorithms/voxel_assembly_relaxed/README.md')
    plan={**old,'workflowVersion':VERSION,'out':str(out),'jobs':jobs,'algorithmSourceCodeSha256':p.hashes(),
          'runtimeSourceCodeSha256':runtime,'publishInventorySha256':inventory,'options':dict(ratio=.02,seconds=args.seconds,physicsSeconds=5.),
          'previousModularPlanSha256':old_sha,'previousModularRuntimeSourceCodeSha256':old['runtimeSourceCodeSha256'],
          'previousModularAlgorithmSourceCodeSha256':old['algorithmSourceCodeSha256'],'previousModularOut':str(old_out),
          'retainedPreviousModularRuntimeSnapshotPath':str(old_out/'source_snapshot'),'inheritedPackages':inherited,
          'recoveryPolicy':'old ZIP bytes preserved and freshly read back; old unsealed results verified with explicit parent generation; rejected solver candidates are diagnostic only; force/moment tolerances unchanged',
          'recoveryStartedAtUtc':datetime.now(timezone.utc).isoformat(),'retainedUnsealedModelCount':retained}
    out.mkdir(parents=True);pack.atomic_json(out/'plan.json',plan)
    for name,digest in runtime.items():
        if q.a.file_sha(ROOT/name)!=digest:raise ValueError('source changed during recovery freeze')
        target=out/'source_snapshot'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
    pack.atomic_json(out/'status.json',dict(workflowVersion=VERSION,phase='planned',modelCount=80000,processedModelCount=len(sealed_ids)+retained,
                     preservedSealedPackageCount=len(inherited),retainedUnsealedModelCount=retained,deadlineUtc=plan['deadlineUtc'],releaseTag=plan['releaseTag'],planSha256=q.a.file_sha(out/'plan.json')))
    print('RECOVERY_FROZEN',len(inherited),'sealed packages;',retained,'unsealed verified checkpoints to reuse',flush=True)


def update(out,phase,rows,plan,**extra):
    legacy.status(out,phase,rows,workflowVersion=VERSION,geometryTier='relaxed_modular_grounded_not_physical_certification',
                  deadlineUtc=plan['deadlineUtc'],releaseTag=plan['releaseTag'],**extra)


def run(args):
    out=args.out.resolve();plan=json.loads((out/'plan.json').read_bytes());sha=q.a.file_sha(out/'plan.json')
    if ROOT!=(out/'source_snapshot').resolve() or plan['workflowVersion']!=VERSION or Path(plan['out'])!=out:raise ValueError('use exact frozen recovery runtime')
    for name,digest in plan['runtimeSourceCodeSha256'].items():
        if q.a.file_sha(ROOT/name)!=digest:raise ValueError('frozen recovery source changed')
    handle=legacy.lock_run(out);rows=[];current=[];budget=plan['options']['seconds'];timed_count=0;timed_seconds=0.;inherited_count=0
    try:
        if json.loads((out/'status.json').read_bytes())['phase']=='complete':return
        by_shard={s:[j for j in plan['jobs'] if j['shardId']==s] for s in ('A','B')}
        light={k:plan[k] for k in ('algorithmSourceCodeSha256','previousModularAlgorithmSourceCodeSha256','previousModularPlanSha256')}
        for number in range(1,41):
            for shard in ('A','B'):
                jobs=by_shard[shard][(number-1)*1000:number*1000];key=f'{shard}/{number:02d}'
                if key in plan['inheritedPackages']:
                    update(out,'rechecking_preserved_packages',rows,plan,currentShard=shard,currentPackage=number,preservedSealedPackageCount=len(plan['inheritedPackages']),recheckedPreservedPackageCount=inherited_count)
                    with ProcessPoolExecutor(max_workers=plan['packageWorkers']) as pool:
                        proof=pack.reuse_sealed_package(out,plan['previousModularOut'],shard,number,jobs,plan['releaseTag'],sha,plan['previousModularPlanSha256'],
                                plan['previousModularRuntimeSourceCodeSha256']['tools/package_quality.py'],plan['inheritedPackages'][key]['proofSha256'],plan['previousModularAlgorithmSourceCodeSha256'],pool)
                    rows.extend(proof['rows']);inherited_count+=1;print('RECOVERY_PACKAGE_PRESERVED',shard,number,flush=True);continue
                checkpoint=out/'delivery/checkpoints'/shard/f'{number:02d}.json'
                if checkpoint.exists():
                    rows.extend(pack.make_package(out,shard,number,jobs,plan['releaseTag'],sha,auditor_name='relaxed_pipeline')['rows']);continue
                if shutil.disk_usage(out).free<12_000_000_000:raise RuntimeError('insufficient disk space; checkpoints retained')
                if timed_count>=1000:
                    rate=timed_count/max(.001,timed_seconds);needed=(80000-len(rows))/rate
                    available=max(1.,plan['deadlineEpoch']-time.time()-7200.)
                    if needed>available:budget=max(2.,budget*available/needed)
                options={**plan['options'],'seconds':budget};current=[];last=time.monotonic();started=last
                update(out,'processing',rows,plan,currentShard=shard,currentPackage=number,activeSearchOptions=options,recheckedPreservedPackageCount=inherited_count)
                for first in range(0,len(jobs),plan['epochModels']):
                    with ProcessPoolExecutor(max_workers=plan['workers'],initializer=initialize,initargs=(light,str(out),sha)) as pool:
                        futures={pool.submit(compute,(job,options)):job for job in jobs[first:first+plan['epochModels']]}
                        for future in as_completed(futures):
                            try:current.append(future.result())
                            except Exception as error:raise RuntimeError(f'model {futures[future]["modelId"]}: {error}') from error
                            if time.monotonic()-last>=10:
                                update(out,'processing',rows+current,plan,currentShard=shard,currentPackage=number,activeSearchOptions=options,
                                       resumedModelsPerSecondIncludingPackaging=(timed_count+len(current))/max(.001,timed_seconds+time.monotonic()-started))
                                print('RECOVERY_PROGRESS',len(rows)+len(current),'/80000 geometry',sum(r['status']=='success' for r in rows+current),flush=True);last=time.monotonic()
                update(out,'sealing_package',rows+current,plan,currentShard=shard,currentPackage=number)
                with ProcessPoolExecutor(max_workers=plan['packageWorkers']) as pool:
                    proof=pack.make_package(out,shard,number,jobs,plan['releaseTag'],sha,audit_pool=pool,auditor_name='relaxed_pipeline')
                rows.extend(proof['rows']);current=[];timed_count+=len(jobs);timed_seconds+=time.monotonic()-started
                print('RECOVERY_PACKAGE_SEALED',shard,number,flush=True)
        update(out,'finalizing',rows,plan);summary,manifest=pack.finalize(out,plan,sha);pack.atomic_json(out/'full_verification.json',summary)
        update(out,'uploading',rows,plan);proof=legacy.publish(out,plan,summary,manifest,publication_directory='relaxed_assembly_80000')
        update(out,'complete',rows,plan,releaseUrl=proof['releaseUrl'],geometryGoalAchieved=summary['geometryGoalAchieved'],finishedBeforeDeadline=time.time()<=plan['deadlineEpoch'],allRemoteAssetSizesAndSha256Passed=True)
    except BaseException as error:
        update(out,'needs_attention',rows+current,plan,errorType=type(error).__name__,error=str(error),checkpointsPreserved=True)
        traceback.print_exc();raise
    finally:handle.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('init','run','status'))
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--from-plan',type=Path);parser.add_argument('--seconds',type=float,default=8.)
    args=parser.parse_args()
    if not 0<args.seconds<=30:parser.error('safe search bound required')
    if args.action=='init':
        if args.from_plan is None:parser.error('--from-plan required')
        parent=legacy.lock_run(args.from_plan.resolve().parent)
        try:prepare(args)
        finally:parent.close()
    elif args.action=='run':run(args)
    else:print((args.out/'status.json').read_text(encoding='utf8'))


if __name__=='__main__':main()
