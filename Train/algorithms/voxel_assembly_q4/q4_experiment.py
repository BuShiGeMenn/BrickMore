"""Q4 deletion fallback experiments, with sealed additions-only failure evidence."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import json
import math
from pathlib import Path
import shutil
import sys
import time

import mixed_cover as j
import mixed_quality as m
import experiment as prior
import gravity_audit as g
q=j.q
import quality_pipeline as old

HERE=Path(__file__).resolve().parent
REPO=HERE.parent.parent
VERSION='quality_mixed_detail_gravity_q4_v2'


def hashes():
    files=list(HERE.glob('*.py'))+list((HERE.parent/'voxel_assembly_q2').glob('*.py'))+list((HERE.parent/'voxel_assembly_q3').glob('*.py'))
    files+=[q.LEGACY/'assembly_pipeline.py']+list((q.LEGACY/'toolkit_snapshot').glob('*.py'))
    return {p.relative_to(REPO).as_posix():q.a.file_sha(p) for p in sorted(files)}


def physics_summary(value):
    result={k:v for k,v in value.items() if k not in ('equilibriumWitness','layerPrefixReports')}
    if 'layerPrefixReports' in value:
        result['layerPrefixReports']=[dict(throughLayer=r['throughLayer'],componentLabel=r['componentLabel'],physics=physics_summary(r['physics'])) for r in value['layerPrefixReports']]
    return result


def verify(folder,source_path=None):
    folder=Path(folder);report=json.loads((folder/'report.json').read_text(encoding='utf8'))
    for name,digest in report['outputFileSha256'].items():
        if Path(name).name!=name or q.a.file_sha(folder/name)!=digest:raise ValueError('Q3 artifact SHA mismatch')
    if source_path is not None and q.a.file_sha(source_path)!=report['sourceFileSha256']:raise ValueError('original modified')
    if q.a.file_sha(folder/'source.model.json')!=report['sourceFileSha256']:raise ValueError('source copy changed')
    source=json.loads((folder/'source.model.json').read_text(encoding='utf-8-sig'))
    target=json.loads((folder/'target.model.json').read_text(encoding='utf8'))
    if report['modelId']!=source['modelId'] or report['targetModelId']!=target['modelId']:raise ValueError('report identity mismatch')
    original,_=q.a.dataset_model(source); model,_=q.a.dataset_model(target)
    repair=m.repair_audit(original.cells,model.cells,report['options']['ratio'])
    if not repair['passed'] or repair!=report['repairAudit']:raise ValueError('repair bound mismatch')
    expected=old.target_value(source,model.cells,repair)
    if expected['derivedGeometry']:expected['modelId']=expected['modelId'].replace('_q2_','_q4_')
    if target!=expected:raise ValueError('derived identity mismatch')
    assembly=json.loads((folder/'assembly.json').read_text(encoding='utf8'))
    if assembly['policy']!=q.POLICY or assembly['modelId']!=target['modelId']:raise ValueError('assembly metadata changed')
    fast=q.independent_audit(assembly['bricks'],model.cells)
    legacy=q.a.exported_audit(folder,target,q.POLICY)
    if any(fast[k]!=legacy[k] for k in fast):raise ValueError('auditors disagree')
    if legacy!=report['geometryValidation'] or legacy!=json.loads((folder/'validation.json').read_text(encoding='utf8')):raise ValueError('geometry readback mismatch')
    if report['status']!=('success' if legacy['passed'] else 'draft') or assembly['status']!=report['status']:raise ValueError('false success')
    physical=json.loads((folder/'physics.json').read_text(encoding='utf8'))
    if report['physics']!=physics_summary(physical):raise ValueError('physical report mismatch')
    if any(v.get('fullPhysics') is not False or v.get('staticVerified') is not None for v in (report,assembly,physical)):
        raise ValueError('unsupported physical certification claim')
    if physical['assumptions']!=g.ASSUMPTIONS:raise ValueError('physics assumptions changed')
    if physical.get('equilibriumWitness'):
        g.verify_screen(assembly['bricks'],model.cells,physical)
    elif physical['gravityEquilibriumPassed']:raise ValueError('missing physical witness')
    if report['qualityScreenedSuccess']!=(legacy['passed'] and physical['layerPrefixGravityPassed']):raise ValueError('false quality-screened success')
    actual_added=set(model.cells)-set(original.cells)
    if set(map(tuple,report['addedInternalXYZ']))!=actual_added or len(report['addedInternalXYZ'])!=len(actual_added):
        raise ValueError('repair history mismatch')
    actual_removed=set(original.cells)-set(model.cells)
    if set(map(tuple,report['removedInternalXYZ']))!=actual_removed or len(report['removedInternalXYZ'])!=len(actual_removed):
        raise ValueError('deletion history mismatch')
    gate=json.loads((folder/'additions_only_evidence.json').read_text(encoding='utf8'))
    if gate!=report['additionsOnlyGate'] or gate['sourceFileSha256']!=report['sourceFileSha256']:raise ValueError('fallback gate binding mismatch')
    gate_cells=q.a.dataset_model(gate['target'])[0].cells
    gate_geometry=q.independent_audit(gate['bricks'],gate_cells)
    if not q.repair_audit(original.cells,gate_cells,report['options']['ratio'])['passed']:raise ValueError('gate was not additions-only')
    if gate['geometryPassed']!=gate_geometry['passed']:raise ValueError('false additions-only gate')
    if actual_removed and gate_geometry['passed']:raise ValueError('deletion before additions-only failure')
    if gate_geometry['passed'] and (assembly['bricks']!=gate['bricks'] or model.cells!=gate_cells):raise ValueError('prior success was not retained exactly')
    if report.get('semanticVerified') is not False:raise ValueError('unsupported semantic claim')
    return report


def worker(task):
    job,dataset,out,options=task
    source_path=Path(dataset)/job['modelPath']/'model.json'
    folder=Path(out)/'models'/job['category']/job['modelId']
    if folder.exists():
        row=verify(folder,source_path)
        if row['sourceCodeSha256']!=hashes() or row['options']!=options:raise ValueError('checkpoint config changed')
        return row
    source=json.loads(source_path.read_text(encoding='utf-8-sig'));model,coords=q.a.dataset_model(source)
    if source['modelId']!=job['modelId'] or q.a.exact_hash(coords)!=job['exactOccupancyHash']:raise ValueError('source manifest binding mismatch')
    started=time.monotonic();attempts=[];result=None;gate=None
    if job.get('priorQ3Path'):
        path=Path(job['priorQ3Path'])
        if q.a.file_sha(path/'report.json')!=job['priorQ3ReportSha256']:raise ValueError('prior Q3 report changed')
        row=prior.verify(path,source_path)
        prior_raw=json.loads((path/'assembly.json').read_text(encoding='utf8'))['bricks']
        prior_target=json.loads((path/'target.model.json').read_text(encoding='utf8'))
        gate={'sourceFileSha256':q.a.file_sha(source_path),'kind':'independently_reread_prior_q3',
              'priorReportSha256':job['priorQ3ReportSha256'],'geometryPassed':row['status']=='success',
              'boundedFailureNotImpossibility':True,'bricks':prior_raw,'target':prior_target,
              'searchAttempts':row['searchAttempts'],'sourceCodeSha256':row['sourceCodeSha256']}
        if row['status']=='success':
            result={'bricks':prior_raw,'targetCells':q.a.dataset_model(prior_target)[0].cells}
            outcome='geometry_retained_q3'
    if result is None and gate is None and job.get('baselineStatus')=='success':
        result=old.retain_baseline(job['baselinePath'],source,source_path);outcome='geometry_retained_original'
        gate={'sourceFileSha256':q.a.file_sha(source_path),'kind':'independently_reread_original_success',
              'geometryPassed':True,'bricks':result['bricks'],'target':old.target_value(source,model.cells,q.repair_audit(model.cells,model.cells,options['ratio']))}
    if job.get('priorQ4Path'):
        path=Path(job['priorQ4Path'])
        if q.a.file_sha(path/'report.json')!=job['priorQ4ReportSha256']:raise ValueError('prior Q4 report changed')
        previous=verify(path,source_path)
        if previous['status']!=job['priorQ4Status']:raise ValueError('prior Q4 status changed')
        if previous['status']=='success':
            result={'bricks':json.loads((path/'assembly.json').read_text(encoding='utf8'))['bricks'],
                    'targetCells':q.a.dataset_model(json.loads((path/'target.model.json').read_text(encoding='utf8')))[0].cells}
            gate=previous['additionsOnlyGate'];outcome='geometry_retained_q4'
    def physics_accept(raw,target):
        return g.screen(raw,target,min(2,options['physicsSeconds']))['layerPrefixGravityPassed']
    if result is None and gate is None:
        raw,target,stats=m.prior.solve(model.cells,options['ratio'],options['additionsSeconds'],options['candidateLimit'],options['cutRounds'],physics_accept=physics_accept)
        passed=q.independent_audit(raw,target)['passed']
        gate={'sourceFileSha256':q.a.file_sha(source_path),'kind':'fresh_additions_only_search',
              'geometryPassed':passed,'boundedFailureNotImpossibility':True,'bricks':raw,
              'target':old.target_value(source,target,q.repair_audit(model.cells,target,options['ratio'])),
              'searchAttempts':[stats],'sourceCodeSha256':hashes()}
        attempts.append(dict(stage='additions_only',**stats))
        if passed:result={'bricks':raw,'targetCells':target};outcome='geometry_additions_only'
    if result is None:
        raw,target,stats=j.solve(model.cells,options['ratio'],options['seconds'],options['candidateLimit'],options['cutRounds'],physics_accept=physics_accept,additions_only_failure={k:gate[k] for k in ('kind','geometryPassed','sourceFileSha256')})
        attempts.append(dict(stage='mixed_fallback',**stats))
        result={'bricks':raw,'targetCells':target}
        outcome='geometry_mixed_fallback' if set(model.cells)-set(target) else 'geometry_additions_retry'
    raw=result['bricks'];cells=result['targetCells'];repair=m.repair_audit(model.cells,cells,options['ratio'])
    if not repair['passed']:raise ValueError('quality bound failed')
    passed=q.independent_audit(raw,cells)['passed'];status='success' if passed else 'draft'
    if not passed:outcome='bounded_mixed_search_not_passed'
    target=old.target_value(source,cells,repair)
    if target['derivedGeometry']:target['modelId']=target['modelId'].replace('_q2_','_q4_')
    physics=g.screen(raw,cells,options['physicsSeconds'])
    folder.mkdir(parents=True);shutil.copyfile(source_path,folder/'source.model.json')
    q.a.dump(folder/'target.model.json',target)
    q.a.dump(folder/'assembly.json',{'algorithmVersion':VERSION,'modelId':target['modelId'],
             'sourceModelId':source['modelId'],'status':status,'bricks':raw,'policy':q.POLICY,
             'sourceToInternal':'[x,y,z] -> [x,z,y]','ldrUnitScales':[20,20,24],
             'fullPhysics':False,'staticVerified':None})
    geometry=[{k:b[k] for k in ('h','w','x','y','z')} for b in raw];suffix='' if passed else '.draft'
    (folder/f'model{suffix}.txt').write_text(''.join(q.a.Placement(**b).to_txt() for b in geometry),encoding='utf8')
    (folder/f'model{suffix}.ldr').write_text(q.a.to_ldr({'status':status,'bricks':geometry},cells),encoding='utf8')
    validation=q.a.exported_audit(folder,target,q.POLICY)
    if validation['passed']!=passed:raise ValueError('exported assembly disagrees')
    q.a.dump(folder/'physics.json',physics);q.a.dump(folder/'validation.json',validation)
    q.a.dump(folder/'additions_only_evidence.json',gate)
    report={'algorithmVersion':VERSION,'modelId':source['modelId'],'targetModelId':target['modelId'],
            'category':job['category'],'status':status,'outcome':outcome,'options':options,
            'baselineStatus':job.get('baselineStatus'),'q2Status':job.get('q2Status'),'priorQ3Status':job.get('priorQ3Status'),
            'priorQ4Status':job.get('priorQ4Status'),
            'repairAudit':repair,'addedInternalXYZ':[list(p) for p in sorted(set(cells)-set(model.cells))],
            'removedInternalXYZ':[list(p) for p in sorted(set(model.cells)-set(cells))],
            'additionsOnlyGate':gate,
            'geometryValidation':validation,'physics':physics_summary(physics),
            'qualityScreenedSuccess':passed and physics['layerPrefixGravityPassed'],
            'searchAttempts':attempts,'elapsedSeconds':time.monotonic()-started,
            'sourceFileSha256':q.a.file_sha(source_path),'sourceCodeSha256':hashes(),
            'originalModelBytesPreserved':True,'promptBindingStatus':'original_only_not_revalidated' if cells!=model.cells else 'original_geometry_preserved',
            'fullPhysics':False,'staticVerified':None,'semanticVerified':False,
            'outputFileSha256':{p.name:q.a.file_sha(p) for p in sorted(folder.iterdir())}}
    q.a.dump(folder/'report.json',report)
    return verify(folder,source_path)


def select(dataset,index,count,seed,q2_run=None,prior_q3_run=None):
    import re
    manifest=json.loads((dataset/'manifest.json').read_text(encoding='utf8'))
    jobs=q.a.manifest_jobs(manifest)
    config=json.loads((index.parent/'config.json').read_text(encoding='utf8'))
    bases=[index.parent.resolve(),Path(config['baseRun']).resolve()]
    baseline={}
    for line in index.read_text(encoding='utf8').splitlines():
        row=json.loads(line)
        if row['modelId'] in baseline:raise ValueError('duplicate baseline')
        if not any(Path(row['resultPath']).resolve()==base/'models'/row['category']/row['modelId'] for base in bases):raise ValueError('unsealed baseline path')
        baseline[row['modelId']]=row
    if set(baseline)!={job['modelId'] for job in jobs}:raise ValueError('baseline/manifest mismatch')
    if any(not re.fullmatch(r'[A-Za-z0-9_-]+',job[k]) for job in jobs for k in ('category','modelId')):raise ValueError('unsafe model ID')
    jobs=[dict(job,baselinePath=baseline[job['modelId']]['resultPath'],
               baselineReportSha256=baseline[job['modelId']]['reportFileSha256'],
               baselineStatus=baseline[job['modelId']]['status']) for job in jobs]
    if prior_q3_run:
        prior_config=json.loads((prior_q3_run/'config.json').read_text(encoding='utf8'))
        if prior_config['manifestSha256']!=q.a.file_sha(dataset/'manifest.json'):raise ValueError('prior dataset changed')
        prior_jobs=json.loads((prior_q3_run/'selection.json').read_text(encoding='utf8'))
        if prior_config['selectionSha256']!=q.a.sha(json.dumps(prior_jobs,sort_keys=True).encode()):raise ValueError('prior selection changed')
        by_id={job['modelId']:job for job in jobs}
        jobs=[]
        for prior in prior_jobs:
            job=by_id[prior['modelId']];path=prior_q3_run/'models'/job['category']/job['modelId']
            row=json.loads((path/'report.json').read_text(encoding='utf8'))
            jobs.append(dict(job,priorQ3Path=str(path.resolve()),priorQ3ReportSha256=q.a.file_sha(path/'report.json'),priorQ3Status=row['status']))
    elif q2_run:
        jobs=json.loads((q2_run/'selection.json').read_text(encoding='utf8'))
        for job in jobs:
            path=q2_run/'models'/job['category']/job['modelId']
            job.update(q2Path=str(path.resolve()),q2Status=json.loads((path/'report.json').read_text())['status'])
    else:
        jobs.sort(key=lambda job:q.a.sha((str(seed)+'uniform'+job['modelId']).encode()))
    jobs=jobs[:count] if count else jobs
    for job in jobs:
        row=baseline[job['modelId']]
        if job['baselineReportSha256']!=row['reportFileSha256'] or q.a.file_sha(Path(job['baselinePath'])/'report.json')!=row['reportFileSha256']:raise ValueError('selected baseline report changed')
    return manifest,jobs


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',type=Path,required=True);p.add_argument('--baseline-index',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--q2-run',type=Path)
    p.add_argument('--prior-q3-run',type=Path)
    p.add_argument('--prior-q4-run',type=Path)
    p.add_argument('--count',type=int,default=80);p.add_argument('--seed',type=int,default=38177)
    p.add_argument('--seconds',type=float,default=60);p.add_argument('--physics-seconds',type=float,default=5)
    p.add_argument('--additions-seconds',type=float,default=24)
    p.add_argument('--candidate-limit',type=int,default=40000);p.add_argument('--cut-rounds',type=int,default=8)
    p.add_argument('--workers',type=int,default=6);p.add_argument('--ratio',type=float,default=.02)
    p.add_argument('--verify',action='store_true');p.add_argument('--public-summary',type=Path)
    args=p.parse_args();q.budget_for(100,args.ratio)
    if args.q2_run:p.error('Q4 consumes Q3 evidence; upgrade Q2 using Q3 first')
    if args.prior_q4_run and not args.prior_q3_run:p.error('paired Q4 retry also requires its original Q3 cohort')
    if args.count<0 or args.workers<1 or args.candidate_limit<1 or args.cut_rounds<1 or any(not math.isfinite(v) or v<=0 for v in (args.seconds,args.physics_seconds,args.additions_seconds)):p.error('invalid budgets')
    options={'ratio':args.ratio,'seconds':args.seconds,'physicsSeconds':args.physics_seconds,
             'candidateLimit':args.candidate_limit,'cutRounds':args.cut_rounds,'additionsSeconds':args.additions_seconds}
    if args.verify:
        config=json.loads((args.out/'config.json').read_text());jobs=json.loads((args.out/'selection.json').read_text());options=config['options']
        if config['sourceCodeSha256']!=hashes() or config['manifestSha256']!=q.a.file_sha(args.dataset/'manifest.json'):p.error('frozen source changed')
        if any(q.a.file_sha(args.out/'source_snapshot'/name)!=digest for name,digest in config['sourceCodeSha256'].items()):p.error('source snapshot changed')
        if config['selectionSha256']!=q.a.sha(json.dumps(jobs,sort_keys=True).encode()):p.error('selection changed')
    else:
        manifest,jobs=select(args.dataset,args.baseline_index,args.count,args.seed,args.q2_run,args.prior_q3_run)
        if args.prior_q4_run:
            previous_config=json.loads((args.prior_q4_run/'config.json').read_text(encoding='utf8'))
            previous_jobs=json.loads((args.prior_q4_run/'selection.json').read_text(encoding='utf8'))
            if previous_config['manifestSha256']!=q.a.file_sha(args.dataset/'manifest.json') or previous_config['selectionSha256']!=q.a.sha(json.dumps(previous_jobs,sort_keys=True).encode()):p.error('prior Q4 manifest/selection changed')
            if [job['modelId'] for job in previous_jobs]!=[job['modelId'] for job in jobs]:p.error('prior Q4 changed paired cohort')
            for job in jobs:
                path=args.prior_q4_run/'models'/job['category']/job['modelId']
                previous=json.loads((path/'report.json').read_text(encoding='utf8'))
                job.update(priorQ4Path=str(path.resolve()),priorQ4ReportSha256=q.a.file_sha(path/'report.json'),priorQ4Status=previous['status'])
        config={'algorithmVersion':VERSION,'options':options,'sourceCodeSha256':hashes(),
                'manifestSha256':q.a.file_sha(args.dataset/'manifest.json'),
                'baselineIndexSha256':q.a.file_sha(args.baseline_index),
                'selectionSha256':q.a.sha(json.dumps(jobs,sort_keys=True).encode()),
                'seed':args.seed,'sampleDesign':'previous Q3 cohort; paired deletion fallback, not new holdout' if args.prior_q3_run else 'uniform deterministic hash sample from whole 40000 manifest',
                'priorRunConfigSha256':q.a.file_sha(args.prior_q3_run/'config.json') if args.prior_q3_run else None,
                'priorQ4RunConfigSha256':q.a.file_sha(args.prior_q4_run/'config.json') if args.prior_q4_run else None,
                'datasetVersion':manifest['datasetVersion'],'datasetPath':str(args.dataset.resolve())}
        if (args.out/'config.json').exists():
            if config!=json.loads((args.out/'config.json').read_text()):p.error('checkpoint changed')
        else:
            if args.out.exists():p.error('unsealed output directory')
            args.out.mkdir(parents=True);q.a.dump(args.out/'config.json',config);q.a.dump(args.out/'selection.json',jobs)
            old.snapshot_sources(args.out,config['sourceCodeSha256'])
    started=time.monotonic();rows=[];counts=Counter()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        tasks=((job,str(args.dataset),str(args.out),options) for job in jobs)
        for i,row in enumerate(pool.map(worker,tasks,chunksize=1),1):
            rows.append(row);counts[row['outcome']]+=1
            if i%10==0 or i==len(jobs):print('Q4_PROGRESS',i,'/',len(jobs),dict(counts),flush=True)
    summary={'algorithmVersion':VERSION,'modelCount':len(rows),
             'baselineGeometryPassed':sum(r['baselineStatus']=='success' for r in rows),
             'q2GeometryPassed':sum(r['q2Status']=='success' for r in rows) if rows and all(r['q2Status'] is not None for r in rows) else None,
             'priorQ3GeometryPassed':sum(r['priorQ3Status']=='success' for r in rows) if rows and all(r['priorQ3Status'] is not None for r in rows) else None,
             'q4GeometryPassed':sum(r['status']=='success' for r in rows),
             'gravityScreenedPassed':sum(r['qualityScreenedSuccess'] for r in rows),
             'physicalStatusCounts':dict(Counter(r['physics']['status'] for r in rows)),
             'outcomeCounts':dict(counts),'maximumChangeRatio':max((r['repairAudit']['changeRatio'] for r in rows),default=0),
             'originalDataModified':False,'fullPhysics':False,'staticVerified':None,
             'allArtifactsIndependentlyReadBack':True,'notAn80000ModelCensus':True,
             'configuration':{k:v for k,v in config.items() if k!='datasetPath'},
             'elapsedSeconds':time.monotonic()-started,
             'models':[{k:r[k] for k in ('modelId','category','baselineStatus','q2Status','priorQ3Status','status','outcome','repairAudit','physics','qualityScreenedSuccess')} for r in rows]}
    q.a.dump(args.out/'summary.json',summary)
    if args.public_summary:q.a.dump(args.public_summary,summary)
    print('Q4_SUMMARY',json.dumps({k:summary[k] for k in ('modelCount','baselineGeometryPassed','priorQ3GeometryPassed','q4GeometryPassed','gravityScreenedPassed','physicalStatusCounts')}),flush=True)


if __name__=='__main__':main()
