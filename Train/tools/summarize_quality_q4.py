"""Verify Q4 frozen runs, original bytes, actual exports, gates and prior successes."""
import json
from collections import Counter
from pathlib import Path
import sys

REPO=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(REPO/'algorithms'/'voxel_assembly_q4'))
import q4_experiment as e


def verify_run(name):
    root=REPO/'downloads'/'quality_q4'/name
    config=json.loads((root/'config.json').read_text(encoding='utf8'))
    jobs=json.loads((root/'selection.json').read_text(encoding='utf8'))
    if config['selectionSha256']!=e.q.a.sha(json.dumps(jobs,sort_keys=True).encode()):raise ValueError('selection changed')
    if e.q.a.file_sha(Path(config['datasetPath'])/'manifest.json')!=config['manifestSha256']:raise ValueError('manifest changed')
    for path,digest in config['sourceCodeSha256'].items():
        if e.q.a.file_sha(root/'source_snapshot'/path)!=digest:raise ValueError('snapshot changed')
    import ast
    def function(path,name):
        return next(ast.dump(n,include_attributes=False) for n in ast.parse(path.read_text(encoding='utf8')).body if isinstance(n,ast.FunctionDef) and n.name==name)
    relative='algorithms/voxel_assembly_q4/q4_experiment.py'
    for name_ in ('verify','physics_summary'):
        if function(REPO/relative,name_)!=function(root/'source_snapshot'/relative,name_):raise ValueError('measured independent verifier changed')
    for relative in ('algorithms/voxel_assembly_q4/mixed_quality.py','algorithms/voxel_assembly_q3/gravity_audit.py'):
        if e.q.a.file_sha(REPO/relative)!=config['sourceCodeSha256'][relative]:raise ValueError('repair or physics quality conditions changed')
    rows=[];proofs=[];prior_rows=[]
    for job in jobs:
        folder=root/'models'/job['category']/job['modelId']
        source=Path(config['datasetPath'])/job['modelPath']/'model.json'
        row=e.verify(folder,source)
        if row['sourceCodeSha256']!=config['sourceCodeSha256'] or row['options']!=config['options'] or row['algorithmVersion']!=config['algorithmVersion'] or row['modelId']!=job['modelId']:raise ValueError('frozen result binding mismatch')
        if job.get('priorQ3Path'):
            prior_path=Path(job['priorQ3Path'])
            if e.q.a.file_sha(prior_path.parents[2]/'config.json')!=config['priorRunConfigSha256']:raise ValueError('prior Q3 configuration changed')
            if e.q.a.file_sha(prior_path/'report.json')!=job['priorQ3ReportSha256']:raise ValueError('prior report changed')
            prior=e.prior.verify(prior_path,source);prior_rows.append(prior)
            gate=row['additionsOnlyGate']
            if gate['priorReportSha256']!=job['priorQ3ReportSha256'] or gate['bricks']!=json.loads((prior_path/'assembly.json').read_text(encoding='utf8'))['bricks'] or gate['target']!=json.loads((prior_path/'target.model.json').read_text(encoding='utf8')):raise ValueError('prior additions-only gate changed')
            if row['priorQ3Status']!=prior['status']:raise ValueError('prior status changed')
        if job.get('priorQ4Path'):
            previous_path=Path(job['priorQ4Path'])
            if e.q.a.file_sha(previous_path.parents[2]/'config.json')!=config['priorQ4RunConfigSha256']:raise ValueError('prior Q4 configuration changed')
            if e.q.a.file_sha(previous_path/'report.json')!=job['priorQ4ReportSha256']:raise ValueError('prior Q4 report changed')
            previous=e.verify(previous_path,source)
            if row.get('priorQ4Status')!=previous['status']:raise ValueError('prior Q4 status changed')
            if previous['status']=='success':
                if row['status']!='success' or json.loads((folder/'assembly.json').read_text(encoding='utf8'))['bricks']!=json.loads((previous_path/'assembly.json').read_text(encoding='utf8'))['bricks']:raise ValueError('prior Q4 success regression')
                current=e.q.a.dataset_model(json.loads((folder/'target.model.json').read_text(encoding='utf8')))[0].cells
                old=e.q.a.dataset_model(json.loads((previous_path/'target.model.json').read_text(encoding='utf8')))[0].cells
                if current!=old or row['additionsOnlyGate']!=previous['additionsOnlyGate']:raise ValueError('prior mixed target/gate changed')
        rows.append(row)
        proofs.append({'modelId':job['modelId'],'reportSha256':e.q.a.file_sha(folder/'report.json'),
                       'sourceFileSha256':row['sourceFileSha256'],'outputFileSha256':row['outputFileSha256']})
    if len({r['modelId'] for r in rows})!=len(rows):raise ValueError('duplicate denominator')
    return rows,prior_rows,{'run':name,'modelCount':len(rows),'configSha256':e.q.a.file_sha(root/'config.json'),
                          'selectionSha256':config['selectionSha256'],'sourceCodeSha256':config['sourceCodeSha256'],
                          'priorRunConfigSha256':config['priorRunConfigSha256'],
                          'priorQ4RunConfigSha256':config.get('priorQ4RunConfigSha256'),'proofs':proofs}


def counts(rows):
    passed=[r for r in rows if r['status']=='success']
    attempts=[a for r in rows for a in r['searchAttempts'] if a.get('stage')=='mixed_fallback']
    return {'modelCount':len(rows),'geometryPassed':len(passed),'geometryPassRate':len(passed)/len(rows),
            'finalGravityEquilibriumPassed':sum(r['physics']['gravityEquilibriumPassed'] for r in rows),
            'allCompletedLayerGravityPassed':sum(r['qualityScreenedSuccess'] for r in rows),
            'physicalStatusCounts':dict(Counter(r['physics']['status'] for r in rows)),
            'outcomeCounts':dict(Counter(r['outcome'] for r in rows)),
            'maximumChangeRatio':max(r['repairAudit']['changeRatio'] for r in rows),
            'successfulDerivedModelsWithDeletions':sum(r['repairAudit']['removedVoxelCount']>0 for r in passed),
            'addedVoxelCountAllResults':sum(r['repairAudit']['addedVoxelCount'] for r in rows),
            'removedVoxelCountAllResults':sum(r['repairAudit']['removedVoxelCount'] for r in rows),
            'removedVoxelCountSuccessfulResults':sum(r['repairAudit']['removedVoxelCount'] for r in passed),
            'recoloredOriginalVoxelCount':sum(r['repairAudit']['recoloredOriginalVoxelCount'] for r in rows),
            'mixedSolverTerminationCounts':dict(Counter(a['termination'] for a in attempts)),
            'mixedSolverStatusCounts':dict(Counter(str(a.get('lastSolverStatus','not_called')) for a in attempts)),
            'candidateEnumerationTruncatedCount':sum(a['candidateEnumerationTruncated'] for a in attempts),
            'totalMixedSearchElapsedSeconds':sum(a['elapsedSeconds'] for a in attempts)}


def main():
    runs={};all_priors={};proofs=[]
    for name in ('A_uniform_fallback_v1','B_uniform_fallback_v1','A_uniform_sparse_v2','B_uniform_sparse_v2'):
        new,prior,proof=verify_run(name);runs[name]=new;all_priors[name]=prior;proofs.append(proof)
        print('VERIFIED_Q4_RUN',name,len(new),flush=True)
    first=runs['A_uniform_fallback_v1']+runs['B_uniform_fallback_v1']
    rows=runs['A_uniform_sparse_v2']+runs['B_uniform_sparse_v2']
    priors=all_priors['A_uniform_sparse_v2']+all_priors['B_uniform_sparse_v2']
    by_id={r['modelId']:r for r in priors}
    if set(by_id)!={r['modelId'] for r in rows} or len(rows)!=160:raise ValueError('changed paired cohort')
    if set(by_id)!={r['modelId'] for r in first}:raise ValueError('first mixed cohort changed')
    regressions=sum(by_id[r['modelId']]['status']=='success' and r['status']!='success' for r in rows)
    if regressions:raise ValueError('geometry regression')
    tests=json.loads((REPO/'algorithms'/'voxel_assembly_q4'/'reports'/'tests.json').read_text(encoding='utf8'))
    if not tests['passed'] or tests['sourceCodeSha256']!=e.hashes():raise ValueError('test evidence stale')
    value={'algorithmVersion':e.VERSION,'verificationDriverSha256':e.q.a.file_sha(Path(__file__)),
           'verificationSourceCodeSha256':e.hashes(),'testCount':tests['testCount'],
           'allFrozenSnapshotsChecked':True,'allSourceBytesAndActualJSONTXTLDRReadBack':True,
           'allRemovalEligibilityAndCombinedBudgetsIndependentlyRecomputed':True,
           'allAdditionsOnlyFailureGatesVerified':True,'allForceWitnessesIndependentlyVerified':True,
           'independentRepairAndPhysicsRulesUnchangedBetweenRuns':True,
           'generationChangesBetweenV1AndV2':['equivalent sparse support constraint representation using original occupancy = 1 - deletion variable','retain freshly verified prior Q4 successes; preserve original additions-only failure gate'],
           'uniqueSourceModelCount':len(rows),'resultFoldersVerified':sum(len(rs) for rs in runs.values()),
           'firstMixedFallback':counts(first),
           'pairedUniformCohort':dict(counts(rows),originalBaselineGeometryPassed=sum(r['baselineStatus']=='success' for r in rows),
               priorQ3GeometryPassed=sum(r['status']=='success' for r in priors),geometryRegressions=regressions,
               priorQ4V1GeometryPassed=sum(r['status']=='success' for r in first),
               priorQ3LayerPrefixGravityPassed=sum(r['qualityScreenedSuccess'] for r in priors),
               physicalScreenRegressions=sum(by_id[r['modelId']]['qualityScreenedSuccess'] and not r['qualityScreenedSuccess'] for r in rows),
               design='same 80 hash-uniform models per shard, seed 38177, as Q3; paired tuning, NOT a new independent holdout'),
           'targetGeometryPassRate':.5,'targetReachedOnPairedCohort':sum(r['status']=='success' for r in rows)>=80,
           'populationTargetProven':False,'full80000RerunCompleted':False,'uploaded':False,
           'originalModelsModified':False,'originalModelsRemoved':False,'originalTrainingPromptsRebound':False,
           'repairBudget':'floor(originalVoxelCount * ratio); additions + deletions + recolor <= budget; recolor forbidden',
           'fullPhysics':False,'staticVerified':None,'calibratedPhysicalVerified':None,'semanticVerified':False,
           'physicsScope':'unchanged Q3 assumed uniform masses, self-weight, unanchored floor, real stud contact force/moment equilibrium and completed layer prefixes; unknown clutch not certified',
           'runs':proofs}
    e.q.a.dump(REPO/'algorithms'/'voxel_assembly_q4'/'reports'/'benchmark_summary.json',value)
    print('Q4_COMBINED',json.dumps(value['pairedUniformCohort']),flush=True)


if __name__=='__main__':main()
