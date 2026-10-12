"""Quality-bounded single-model and immutable baseline upgrade experiments."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import json
import math
from pathlib import Path
import random
import re
import shutil
import time

import quality_core as q

HERE=Path(__file__).resolve().parent
_DATASET=None; _OUT=None; _OPTIONS=None


def source_hashes():
    paths=list(HERE.glob('*.py'))+[q.LEGACY/'assembly_pipeline.py',HERE.parent.parent/'tools'/'optimize_assembly.py']+list((q.LEGACY/'toolkit_snapshot').glob('*.py'))
    return {str(path.relative_to(HERE.parent.parent)).replace('\\','/'):q.a.file_sha(path) for path in sorted(paths)}


def snapshot_sources(out,hashes):
    repo=HERE.parent.parent
    for name,digest in hashes.items():
        source=(repo/name).resolve()
        if not source.is_relative_to(repo.resolve()) or q.a.file_sha(source)!=digest:
            raise ValueError('snapshot source changed or escaped repository')
        target=out/'source_snapshot'/name
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():
            if q.a.file_sha(target)!=digest:raise ValueError('runner snapshot changed')
        else:shutil.copyfile(source,target)


def target_value(source,cells,repair):
    changed=repair['changedVoxelCount']>0
    identity=q.a.sha(json.dumps(sorted(cells.items()),sort_keys=True).encode())[:12]
    return {'modelId':source['modelId']+'_q2_'+identity if changed else source['modelId'],
            'sourceModelId':source['modelId'],'derivedGeometry':changed,
            'sourceUpAxis':'y','actualVoxelCount':len(cells),
            'exactOccupancyHash':repair['targetExactOccupancyHash'],
            'canonicalGeometryHashStatus':'not_recomputed_for_derived_variant',
            'originalExactOccupancyHash':repair['sourceExactOccupancyHash'],
            'voxels':[dict(x=x,y=z,z=y,color=[(c>>16)&255,(c>>8)&255,c&255])
                      for (x,y,z),c in sorted(cells.items())]}


def verify_output(folder,source_path=None):
    folder=Path(folder)
    report=json.loads((folder/'report.json').read_text(encoding='utf8'))
    for name,digest in report['outputFileSha256'].items():
        if Path(name).name!=name or q.a.file_sha(folder/name)!=digest:raise ValueError('output checkpoint tampered')
    if source_path is not None and q.a.file_sha(source_path)!=report['sourceFileSha256']:
        raise ValueError('original source changed')
    if q.a.file_sha(folder/'source.model.json')!=report['sourceFileSha256']:raise ValueError('source copy changed')
    source=json.loads((folder/'source.model.json').read_text(encoding='utf-8-sig'))
    source={**source,'modelId':source.get('modelId',report['modelId'])}
    target=json.loads((folder/'target.model.json').read_text(encoding='utf8'))
    original,_=q.a.dataset_model(source); model,_=q.a.dataset_model(target)
    repair=q.repair_audit(original.cells,model.cells,report['maximumChangeRatio'])
    if not repair['passed'] or repair!=report['repairAudit']:raise ValueError('repair audit mismatch')
    action_points=[]
    allowed_reasons={'complete_local_supported_rectangle','add_local_direct_lower_support',
                     'add_local_component_bridge','add_local_vertical_stud_bridge'}
    for action in report['repairActions']:
        if action['reason'] not in allowed_reasons:raise ValueError('unknown repair action')
        for point in action['addedInternalXYZ']:
            if not isinstance(point,list) or len(point)!=3 or any(type(v) is not int for v in point):
                raise ValueError('invalid repair action coordinate')
            action_points.append(tuple(point))
    if len(set(action_points))!=len(action_points) or set(action_points)!=set(model.cells)-set(original.cells):
        raise ValueError('repair action history does not match actual additions')
    expected=target_value(source,model.cells,repair)
    if target!=expected:raise ValueError('derived model metadata or identity mismatch')
    assembly=json.loads((folder/'assembly.json').read_text(encoding='utf8'))
    if assembly.get('policy')!=q.POLICY or assembly.get('modelId')!=target['modelId']:
        raise ValueError('assembly policy or model identity changed')
    if report.get('fullPhysics') is not False or report.get('staticVerified') is not None or report.get('semanticVerified') is not False:
        raise ValueError('unsupported physical or semantic verification claim')
    if assembly.get('fullPhysics') is not False or assembly.get('staticVerified') is not None:
        raise ValueError('unsupported assembly physics claim')
    fast=q.independent_audit(assembly['bricks'],model.cells,q.POLICY)
    legacy=q.a.exported_audit(folder,target,q.POLICY)
    if any(fast[k]!=legacy[k] for k in fast):raise ValueError('independent auditors disagree')
    validation={**legacy,'repairQualityPassed':repair['passed'],'auditorVersion':q.AUDITOR_VERSION,
                'legacyAuditorParityPassed':True,'sourceGeometryModified':repair['changedVoxelCount']>0}
    if validation!=report['validation'] or json.loads((folder/'validation.json').read_text(encoding='utf8'))!=validation:
        raise ValueError('readback validation changed')
    if report['status']=='success' and not validation['passed']:raise ValueError('false success')
    if report['status'] not in ('success','draft') or assembly['status']!=report['status']:
        raise ValueError('invalid status')
    return report


def retain_baseline(folder,source,source_path):
    """Keep a previously delivered success only after fresh SHA + readback."""
    folder=Path(folder); report=json.loads((folder/'report.json').read_text(encoding='utf8'))
    if report.get('sourceFileSha256')!=q.a.file_sha(source_path):raise ValueError('baseline source mismatch')
    for name,digest in report['outputFileSha256'].items():
        if Path(name).name!=name or q.a.file_sha(folder/name)!=digest:raise ValueError('baseline output changed')
    check=q.a.exported_audit(folder,source,q.POLICY)
    if not check['passed'] or check!=report['validation']:raise ValueError('baseline success no longer verifies')
    raw=json.loads((folder/'assembly.json').read_text(encoding='utf8'))['bricks']
    model,_=q.a.dataset_model(source)
    if not q.independent_audit(raw,model.cells)['passed']:raise ValueError('baseline fast audit mismatch')
    return {'status':'success','bricks':raw,'targetCells':model.cells,'repairActions':[],
            'repairAudit':q.repair_audit(model.cells,model.cells),'searchAttempts':[],
            'elapsedSeconds':0,'outcome':'success_original_retained'}


def run_model(source_path,out,ratio=.02,seconds=12,nodes=60000,baseline=None,baseline_status=None,category=None):
    source_path,out=Path(source_path),Path(out)
    options={'maximumChangeRatio':ratio,'maxSeconds':seconds,'maxNodes':nodes}
    q.budget_for(1,ratio)
    if not math.isfinite(seconds) or seconds<=0 or type(nodes) is not int or nodes<1:raise ValueError('invalid budgets')
    if out.exists():
        if not (out/'report.json').exists():raise ValueError('unsealed output directory exists; choose another')
        old=verify_output(out,source_path)
        if old['options']!=options or old['sourceCodeSha256']!=source_hashes():raise ValueError('checkpoint configuration changed')
        return old
    source=json.loads(source_path.read_text(encoding='utf-8-sig'))
    source={**source,'modelId':source.get('modelId',source_path.stem)}
    model,_=q.a.dataset_model(source)
    if baseline_status=='success':
        if baseline is None:raise ValueError('baseline success requires actual output path')
        result=retain_baseline(baseline,source,source_path)
        result['repairAudit']=q.repair_audit(model.cells,model.cells,ratio)
    else:result=q.optimize(model,ratio,seconds,nodes)
    if not result['repairAudit']['passed']:raise ValueError('quality budget violated')
    target=target_value(source,result['targetCells'],result['repairAudit'])
    out.mkdir(parents=True)
    shutil.copyfile(source_path,out/'source.model.json')
    q.a.dump(out/'target.model.json',target)
    raw=result['bricks']; status=result['status']; geometry=[{k:b[k] for k in ('h','w','x','y','z')} for b in raw]
    q.a.dump(out/'assembly.json',{'algorithmVersion':q.VERSION,'modelId':target['modelId'],
        'sourceModelId':source['modelId'],'status':status,'assemblyOutcome':result['outcome'],
        'bricks':raw,'policy':q.POLICY,'sourceToInternal':'[x,y,z] -> [x,z,y]',
        'ldrUnitScales':[20,20,24],'staticVerified':None,'fullPhysics':False})
    suffix='' if status=='success' else '.draft'
    (out/f'model{suffix}.txt').write_text(''.join(q.a.Placement(**b).to_txt() for b in geometry),encoding='utf8')
    (out/f'model{suffix}.ldr').write_text(q.a.to_ldr({'status':status,'bricks':geometry},result['targetCells']),encoding='utf8')
    fast=q.independent_audit(raw,result['targetCells'])
    legacy=q.a.exported_audit(out,target,q.POLICY)
    if any(fast[k]!=legacy[k] for k in fast):raise ValueError('independent auditors disagree')
    if status=='success' and not legacy['passed']:raise ValueError('exported success failed')
    validation={**legacy,'repairQualityPassed':True,'auditorVersion':q.AUDITOR_VERSION,
                'legacyAuditorParityPassed':True,'sourceGeometryModified':result['repairAudit']['changedVoxelCount']>0}
    q.a.dump(out/'validation.json',validation)
    report={'algorithmVersion':q.VERSION,'modelId':source['modelId'],'targetModelId':target['modelId'],
            'category':category,'status':status,'outcome':result['outcome'],'baselineStatus':baseline_status,
            'options':options,'maximumChangeRatio':ratio,'repairAudit':result['repairAudit'],
            'repairActions':result['repairActions'],'validation':validation,
            'searchAttempts':result['searchAttempts'],'elapsedSeconds':result['elapsedSeconds'],
            'sourceFileSha256':q.a.file_sha(source_path),'sourceCodeSha256':source_hashes(),
            'originalModelBytesPreserved':True,
            'promptBindingStatus':'original_source_only_not_revalidated_for_repaired_geometry'
                                  if result['repairAudit']['changedVoxelCount'] else 'original_source_geometry_preserved',
            'staticVerified':None,'fullPhysics':False,'semanticVerified':False,
            'outputFileSha256':{p.name:q.a.file_sha(p) for p in sorted(out.iterdir())}}
    q.a.dump(out/'report.json',report)
    return verify_output(out,source_path)


def initialize(dataset,out,options):
    global _DATASET,_OUT,_OPTIONS
    _DATASET,_OUT,_OPTIONS=Path(dataset),Path(out),options


def process(job):
    source=_DATASET/job['modelPath']/'model.json'
    value=json.loads(source.read_text(encoding='utf8')); model,original=q.a.dataset_model(value)
    if value['modelId']!=job['modelId'] or q.a.exact_hash(original)!=job['exactOccupancyHash']:
        raise ValueError('source manifest binding changed')
    return run_model(source,_OUT/'models'/job['category']/job['modelId'],
                     _OPTIONS['ratio'],_OPTIONS['seconds'],_OPTIONS['nodes'],
                     job.get('baselinePath'),job.get('baselineStatus'),job['category'])


def verify_job(job):
    row=verify_output(_OUT/'models'/job['category']/job['modelId'],_DATASET/job['modelPath']/'model.json')
    expected=json.loads((_OUT/'config.json').read_text(encoding='utf8'))
    if row['sourceCodeSha256']!=expected['sourceCodeSha256'] or row['options']!={
            'maximumChangeRatio':expected['options']['ratio'],'maxSeconds':expected['options']['seconds'],
            'maxNodes':expected['options']['nodes']}:
        raise ValueError('result does not match frozen runner/configuration')
    return row


def select_jobs(dataset,baseline_index,action,per_stratum,split,seed):
    manifest=json.loads((dataset/'manifest.json').read_text(encoding='utf8'))
    jobs=q.a.manifest_jobs(manifest)
    if any(not re.fullmatch(r'[A-Za-z0-9_-]+',j[k]) for j in jobs for k in ('modelId','category')):
        raise ValueError('unsafe output model or category name')
    rows={}
    if baseline_index is not None:
        root=baseline_index.parent
        config=json.loads((root/'config.json').read_text(encoding='utf8'))
        bases=[root.resolve(),Path(config['baseRun']).resolve()]
        for line in baseline_index.read_text(encoding='utf8').splitlines():
            row=json.loads(line)
            if row['modelId'] in rows:raise ValueError('duplicate baseline id')
            path=Path(row['resultPath']).resolve()
            if not any(path==base/'models'/row['category']/row['modelId'] for base in bases):
                raise ValueError('baseline path outside sealed runs')
            rows[row['modelId']]=row
        if set(rows)!={j['modelId'] for j in jobs}:raise ValueError('baseline does not cover exact source manifest')
        jobs=[{**j,'baselinePath':rows[j['modelId']]['resultPath'],
               'baselineReportSha256':rows[j['modelId']]['reportFileSha256'],
               'baselineStatus':rows[j['modelId']]['status']} for j in jobs]
    if action=='probe':
        if not rows:raise ValueError('probe requires sealed baseline index')
        groups=defaultdict(list)
        for job in jobs:
            fold=int(q.a.sha((str(seed)+job['modelId']).encode())[:8],16)%2
            if split!='all' and fold!=(0 if split=='dev' else 1):continue
            groups[(job['category'],job['baselineStatus'])].append(job)
        chosen=[]
        for key,group in sorted(groups.items()):
            group.sort(key=lambda j:q.a.sha((str(seed)+'order'+j['modelId']).encode()))
            chosen.extend(group[:per_stratum])
        jobs=chosen
    for job in jobs:
        if rows and q.a.file_sha(Path(job['baselinePath'])/'report.json')!=job['baselineReportSha256']:
            raise ValueError('selected baseline report SHA changed')
    return manifest,jobs


def summarize(out,jobs,config,started):
    rows=[]
    for job in jobs:
        path=out/'models'/job['category']/job['modelId']/'report.json'
        if path.exists():
            row=json.loads(path.read_text(encoding='utf8'))
            rows.append({k:row[k] for k in ('modelId','category','status','outcome','baselineStatus','repairAudit','elapsedSeconds')})
    by_category=defaultdict(Counter)
    for row in rows:by_category[row['category']][row['outcome']]+=1
    baseline_available=bool(rows) and all(r['baselineStatus'] is not None for r in rows)
    old=sum(r['baselineStatus']=='success' for r in rows) if baseline_available else None
    new=sum(r['status']=='success' for r in rows)
    summary={'algorithmVersion':q.VERSION,'requestedModelCount':len(jobs),'processedModelCount':len(rows),
        'baselineAvailable':baseline_available,'baselinePassedCount':old,'optimizedPassedCount':new,
        'additionalPassedCount':sum(r['status']=='success' and r['baselineStatus']!='success' for r in rows) if baseline_available else None,
        'baselineSuccessRegressions':sum(r['baselineStatus']=='success' and r['status']!='success' for r in rows) if baseline_available else None,
        'baselinePassRate':old/len(rows) if baseline_available else None,'optimizedPassRate':new/len(rows) if rows else 0,
        'outcomeCounts':dict(Counter(r['outcome'] for r in rows)),
        'categoryOutcomeCounts':{k:dict(v) for k,v in by_category.items()},
        'maximumObservedChangeRatio':max((r['repairAudit']['changeRatio'] for r in rows),default=0),
        'successfulRepairAddedVoxelCount':sum(r['repairAudit']['addedVoxelCount'] for r in rows if r['status']=='success'),
        'allQualityBoundsPassed':all(r['repairAudit']['passed'] for r in rows),
        'allOutputsIndependentlyReRead':True,'allSourceCopiesAndFileSha256Checked':True,
        'successfulRepairMeanChangeRatio':sum(r['repairAudit']['changeRatio'] for r in rows if r['status']=='success' and r['repairAudit']['changedVoxelCount'])/
                                        max(1,sum(r['status']=='success' and r['repairAudit']['changedVoxelCount']>0 for r in rows)),
        'sampleDesign':config['sampleDesign'],'split':config['split'],
        'seed':config['seed'],'perStratum':config['perStratum'],
        'configuration':{k:config[k] for k in ('algorithmVersion','options','manifestSha256','baselineIndexSha256','selectionSha256','sourceCodeSha256')},
        'elapsedSeconds':time.monotonic()-started,'staticVerified':None,'fullPhysics':False,
        'semanticVerified':False,'originalDatasetModified':False,
        'notAn80000ModelPassRateMeasurement':config['action']=='probe','models':rows}
    if summary['baselineSuccessRegressions'] or not summary['allQualityBoundsPassed']:raise ValueError('quality gate failed')
    q.a.dump(out/'summary.json',summary)
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('one','probe','run','verify'))
    p.add_argument('--input',type=Path); p.add_argument('--dataset',type=Path)
    p.add_argument('--baseline-index',type=Path); p.add_argument('--out',type=Path,required=True)
    p.add_argument('--workers',type=int,default=8); p.add_argument('--ratio',type=float,default=.02)
    p.add_argument('--seconds',type=float,default=12); p.add_argument('--nodes',type=int,default=60000)
    p.add_argument('--per-stratum',type=int,default=2); p.add_argument('--split',choices=('dev','holdout','all'),default='dev')
    p.add_argument('--seed',type=int,default=1729); p.add_argument('--public-summary',type=Path)
    args=p.parse_args()
    q.budget_for(1,args.ratio)
    if args.workers<1 or not math.isfinite(args.seconds) or args.seconds<=0 or args.nodes<1 or args.per_stratum<1:
        p.error('finite positive budgets required')
    if args.action=='one':
        if args.input is None:p.error('--input required')
        row=run_model(args.input,args.out,args.ratio,args.seconds,args.nodes)
        print('QUALITY_RESULT',row['outcome'],'changeRatio',row['repairAudit']['changeRatio'],flush=True)
        return 0 if row['status']=='success' else 2
    if args.dataset is None:p.error('--dataset required')
    started=time.monotonic(); options={'ratio':args.ratio,'seconds':args.seconds,'nodes':args.nodes}
    if args.action=='verify':
        config=json.loads((args.out/'config.json').read_text(encoding='utf8'))
        jobs=json.loads((args.out/'selection.json').read_text(encoding='utf8'))
        if config['sourceCodeSha256']!=source_hashes() or config['manifestSha256']!=q.a.file_sha(args.dataset/'manifest.json'):
            p.error('source/config changed; preserve this run and start another')
        if any(q.a.file_sha(args.out/'source_snapshot'/name)!=digest for name,digest in config['sourceCodeSha256'].items()):
            p.error('frozen runner snapshot changed')
        options=config['options']
    else:
        manifest,jobs=select_jobs(args.dataset,args.baseline_index,args.action,args.per_stratum,args.split,args.seed)
        config={'algorithmVersion':q.VERSION,'action':args.action,'options':options,
                'datasetPath':str(args.dataset.resolve()),'datasetVersion':manifest['datasetVersion'],
                'manifestSha256':q.a.file_sha(args.dataset/'manifest.json'),
                'baselineIndexSha256':q.a.file_sha(args.baseline_index) if args.baseline_index else None,
                'selectionSha256':q.a.sha(json.dumps(jobs,sort_keys=True).encode()),
                'sourceCodeSha256':source_hashes(),'split':args.split,
                'seed':args.seed,'perStratum':args.per_stratum,
                'sampleDesign':'category x sealed final status; deterministic disjoint hash dev/holdout folds'
                               if args.action=='probe' else 'full source manifest; inherited successes reverified'}
        if (args.out/'config.json').exists():
            if json.loads((args.out/'config.json').read_text(encoding='utf8'))!=config:p.error('checkpoint source or configuration changed')
        else:
            if args.out.exists():p.error('unsealed output directory exists')
            args.out.mkdir(parents=True); q.a.dump(args.out/'config.json',config); q.a.dump(args.out/'selection.json',jobs)
            snapshot_sources(args.out,config['sourceCodeSha256'])
    counts=Counter()
    with ProcessPoolExecutor(max_workers=args.workers,initializer=initialize,initargs=(args.dataset,args.out,options)) as pool:
        for i,row in enumerate(pool.map(verify_job if args.action=='verify' else process,jobs,chunksize=1),1):
            counts[row['outcome']]+=1
            if i%10==0 or i==len(jobs):print('QUALITY_PROGRESS',i,'/',len(jobs),dict(counts),flush=True)
    summary=summarize(args.out,jobs,config,started)
    if args.public_summary:q.a.dump(args.public_summary,summary)
    print('QUALITY_SUMMARY',json.dumps({k:summary[k] for k in ('processedModelCount','baselinePassedCount','optimizedPassedCount','additionalPassedCount','maximumObservedChangeRatio')},ensure_ascii=False),flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
