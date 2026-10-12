"""Independently verify frozen Q3 runs and publish a path-free evidence summary."""
import json
import math
from pathlib import Path
import sys

REPO=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(REPO/'algorithms'/'voxel_assembly_q3'))
import experiment as e


def verify_run(name):
    root=REPO/'downloads'/'quality_q3'/name
    config=json.loads((root/'config.json').read_text(encoding='utf8'))
    jobs=json.loads((root/'selection.json').read_text(encoding='utf8'))
    if config['selectionSha256']!=e.q.a.sha(json.dumps(jobs,sort_keys=True).encode()):raise ValueError('selection SHA changed')
    if e.q.a.file_sha(Path(config['datasetPath'])/'manifest.json')!=config['manifestSha256']:raise ValueError('manifest changed')
    for path,digest in config['sourceCodeSha256'].items():
        if e.q.a.file_sha(root/'source_snapshot'/path)!=digest:raise ValueError('snapshot changed')
    rows=[];proofs=[]
    for job in jobs:
        folder=root/'models'/job['category']/job['modelId']
        source=Path(config['datasetPath'])/job['modelPath']/'model.json'
        report=e.verify(folder,source)
        if report['sourceCodeSha256']!=config['sourceCodeSha256'] or report['options']!=config['options'] or report['algorithmVersion']!=config['algorithmVersion']:raise ValueError('result not bound to frozen configuration')
        if report['modelId']!=job['modelId']:raise ValueError('wrong source identity')
        rows.append(report)
        proofs.append({'modelId':job['modelId'],'reportSha256':e.q.a.file_sha(folder/'report.json'),
                       'sourceFileSha256':report['sourceFileSha256'],'outputFileSha256':report['outputFileSha256']})
    return rows,{'run':name,'algorithmVersion':config['algorithmVersion'],'configSha256':e.q.a.file_sha(root/'config.json'),
                 'selectionSha256':config['selectionSha256'],'sourceCodeSha256':config['sourceCodeSha256'],
                 'modelCount':len(rows),'proofs':proofs}


def counts(rows):
    from collections import Counter
    n=len(rows);passed=sum(r['status']=='success' for r in rows)
    return {'modelCount':n,'baselineGeometryPassed':sum(r['baselineStatus']=='success' for r in rows),
            'geometryPassed':passed,'geometryPassRate':passed/n,
            'finalGravityEquilibriumPassed':sum(r['physics']['gravityEquilibriumPassed'] for r in rows),
            'finalAndAllCompletedLayerGravityPassed':sum(r['qualityScreenedSuccess'] for r in rows),
            'physicalStatusCounts':dict(Counter(r['physics']['status'] for r in rows)),
            'maximumChangeRatio':max(r['repairAudit']['changeRatio'] for r in rows),
            'deletedOriginalVoxelCount':sum(r['repairAudit']['removedVoxelCount'] for r in rows),
            'recoloredOriginalVoxelCount':sum(r['repairAudit']['recoloredOriginalVoxelCount'] for r in rows)}


def main():
    import ast
    names=('A_regression_v2','B_regression_v2','A_uniform_v2','B_uniform_v2','A_uniform_retry_v3','B_uniform_retry_v3')
    runs={};proofs=[]
    stable_physics_functions=('audit','screen','expected_contacts','hull','witness_residual')
    def functions(path):
        return {node.name:ast.dump(node,include_attributes=False) for node in ast.parse(path.read_text(encoding='utf8')).body if isinstance(node,ast.FunctionDef)}
    current_physics=functions(REPO/'algorithms'/'voxel_assembly_q3'/'gravity_audit.py')
    for name in names:
        frozen_physics=functions(REPO/'downloads'/'quality_q3'/name/'source_snapshot'/'algorithms'/'voxel_assembly_q3'/'gravity_audit.py')
        if any(current_physics[k]!=frozen_physics[k] for k in stable_physics_functions):raise ValueError('measured physics generation changed')
        rows,proof=verify_run(name);runs[name]=rows;proofs.append(proof)
        print('VERIFIED_Q3_RUN',name,len(rows),flush=True)
    regression=runs['A_regression_v2']+runs['B_regression_v2']
    uniform=runs['A_uniform_v2']+runs['B_uniform_v2']
    retry=runs['A_uniform_retry_v3']+runs['B_uniform_retry_v3']
    by_id={r['modelId']:r for r in uniform}
    if set(by_id)!={r['modelId'] for r in retry}:raise ValueError('retry changed denominator')
    regressions=sum(by_id[r['modelId']]['status']=='success' and r['status']!='success' for r in retry)
    if regressions:raise ValueError('geometry regression')
    old_ids=set()
    for name in ('A_dev_final','B_dev_final','A_holdout_final','B_holdout_final'):
        old_ids.update(job['modelId'] for job in json.loads((REPO/'downloads'/'quality_q2'/name/'selection.json').read_text(encoding='utf8')))
    if old_ids & set(by_id):raise ValueError('initial uniform cohort overlapped old tuning cohort')
    n=len(retry);p=sum(r['status']=='success' for r in retry)/n;z=1.959963984540054
    center=(p+z*z/(2*n))/(1+z*z/n);half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    value={'latestAlgorithmVersion':e.VERSION,'verificationDriverSha256':e.q.a.file_sha(Path(__file__)),
           'verificationSourceCodeSha256':e.hashes(),'allFrozenSnapshotsChecked':True,
           'postMeasurementVerifierChanges':['gravity_audit.verify_witness: additionally recompute COM, ground polygon, tipping metadata and contact count; accompanying tamper test'],
           'physicsGenerationFunctionASTsUnchanged':True,
           'allActualSourceCopiesAndArtifactsReadBack':True,'allForceWitnessesIndependentlyBalanced':True,
           'uniqueSourceModelCount':len({r['modelId'] for rows in runs.values() for r in rows}),
           'resultFoldersVerified':sum(len(rows) for rows in runs.values()),
           'oldStratifiedRegression':dict(counts(regression),q2GeometryPassed=sum(r['q2Status']=='success' for r in regression),
               interpretation='reused category x old status cohort; not a population pass rate'),
           'initialUniformSample':dict(counts(uniform),design='80 uniform hash-selected models from each 40000 shard; seed 38177; disjoint from previous 295 tuning models'),
           'sameUniformCohortRetry':dict(counts(retry),geometryRegressions=regressions,
               additionalGeometryPasses=sum(r['status']=='success' and by_id[r['modelId']]['status']!='success' for r in retry),
               interpretation='paired tuning/retry of the same fixed cohort, not a new independent holdout',
               approximateWilson95Interval=[center-half,center+half],
               intervalAssumption='descriptive Bernoulli/uniform-sampling approximation; not a guarantee after algorithm tuning'),
           'targetGeometryPassRate':.5,'targetReachedOnUniformRetry':p>=.5,
           'full80000RerunCompleted':False,'originalModelsModified':False,
           'fullPhysics':False,'staticVerified':None,'calibratedPhysicalVerified':None,
           'physicsScope':'assumed uniform masses, self weight, inset vertical contact patches, unanchored horizontal floor; every completed layer prefix; not every individual placement or dynamic insertion',
           'runs':proofs}
    e.q.a.dump(REPO/'algorithms'/'voxel_assembly_q3'/'reports'/'benchmark_summary.json',value)
    print('Q3_COMBINED',json.dumps({k:value[k] for k in ('uniqueSourceModelCount','resultFoldersVerified','targetReachedOnUniformRetry')}),flush=True)
    print('Q3_UNIFORM_RETRY',json.dumps(value['sameUniformCohortRetry']),flush=True)


if __name__=='__main__':main()
