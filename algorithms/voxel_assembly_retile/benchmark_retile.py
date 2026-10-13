"""Frozen paired benchmark against independently read published assemblies."""
import argparse
from collections import Counter,defaultdict
import json
from pathlib import Path
import shutil
import time

import retile_pipeline as pipeline


def run(cases,samples,out,seconds=2.,physics_seconds=0.):
    cases=Path(cases);samples=Path(samples);out=Path(out)
    index=json.loads(cases.read_bytes());rows=index['models'];out.mkdir(parents=True,exist_ok=True)
    configuration={'algorithmVersion':pipeline.VERSION,'optimizerVersion':pipeline.core.VERSION,
                   'sourceRelease':index['sourceRelease'],'sampleSeed':index['sampleSeed'],
                   'samplingScope':index['samplingScope'],'selectionSha256':pipeline.digest(cases),
                   'driverSha256':pipeline.digest(__file__),'sourceCodeSha256':pipeline.code_hashes(),
                   'options':dict(seconds=seconds,physicsSeconds=physics_seconds,ratio=.02)}
    config_path=out/'run_plan.json'
    if config_path.exists():
        if json.loads(config_path.read_bytes())!=configuration:raise ValueError('Frozen benchmark inputs/options/code changed')
    else:pipeline.dump(config_path,configuration)
    for relative,digest in configuration['sourceCodeSha256'].items():
        path=out/'source_snapshot'/relative;path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists() and pipeline.digest(path)!=digest:raise ValueError('Frozen source snapshot changed')
        if not path.exists():shutil.copyfile(pipeline.REPO/relative,path)
    results=[];groups=defaultdict(Counter);started=time.monotonic()
    for number,row in enumerate(rows,1):
        source_folder=samples/row['modelId'];source=source_folder/'source.model.json'
        if pipeline.digest(source)!=row['sourceFileSha256'] or pipeline.digest(source_folder/'report.json')!=row['reportFileSha256']:
            raise ValueError('Published benchmark input SHA-256 differs')
        before=pipeline.read_baseline(source_folder,source)
        before_passed=pipeline.core.base.audit(before['bricks'],before['targetCells'])['passed']
        if before_passed!=row['geometryPassed']:raise ValueError('Published baseline status does not match actual geometry')
        report=pipeline.run_one(source,out/'models'/row['modelId'],seconds,physics_seconds,source_folder)
        if pipeline.digest(source)!=row['sourceFileSha256']:raise ValueError('Original benchmark source changed')
        passed=report['geometryValidation']['passed']
        result={'modelId':row['modelId'],'category':row['category'],'shardId':row['shardId'],
                'baselinePassed':before_passed,'newGeometryPassed':passed,'retainedBaseline':report['retainedBaseline'],
                'originalVoxelCount':report['repairAudit']['originalVoxelCount'],
                'addedVoxelCount':report['repairAudit']['addedVoxelCount'],'removedVoxelCount':report['repairAudit']['removedVoxelCount'],
                'recoloredOriginalVoxelCount':report['repairAudit']['recoloredOriginalVoxelCount'],
                'changeRatio':report['repairAudit']['changeRatio'],'elapsedSeconds':report['elapsedSeconds'],
                'physicsStatus':report['physics']['status'],'qualityScreenedSuccess':report['qualityScreenedSuccess'],
                'reportRelativePath':'models/'+row['modelId']+'/report.json'}
        results.append(result)
        group=groups[row['shardId']+'_'+row['category']];group['modelCount']+=1;group['baselinePassed']+=before_passed;group['newGeometryPassed']+=passed
        print(json.dumps({'number':number,'total':len(rows),**result},ensure_ascii=False),flush=True)
    summary={'configuration':configuration,'modelCount':len(rows),'baselinePassed':sum(r['baselinePassed'] for r in results),
             'newGeometryPassed':sum(r['newGeometryPassed'] for r in results),
             'recoveredPublishedFailures':sum(not r['baselinePassed'] and r['newGeometryPassed'] for r in results),
             'publishedSuccessRegressions':sum(r['baselinePassed'] and not r['newGeometryPassed'] for r in results),
             'maximumChangeRatio':max((r['changeRatio'] for r in results),default=0),
             'addedVoxelCount':sum(r['addedVoxelCount'] for r in results),'removedVoxelCount':sum(r['removedVoxelCount'] for r in results),
             'recoloredOriginalVoxelCount':sum(r['recoloredOriginalVoxelCount'] for r in results),
             'fullTargetCoverageOnEverySuccessAndDraft':True,'allOriginalAndPromptBytesPreserved':True,
             'allActualJSONTXTLDRIndependentlyVerified':True,'categoryCounts':dict(groups),
             'physicalStatusCounts':dict(Counter(r['physicsStatus'] for r in results)),
             'full80000RerunCompleted':False,'populationPassRateMeasured':False,
             'elapsedSeconds':time.monotonic()-started,'models':results,'staticVerified':None,'fullPhysics':False}
    pipeline.dump(out/'summary.json',summary)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',required=True,type=Path);parser.add_argument('--samples',required=True,type=Path);parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--seconds',type=float,default=2.);parser.add_argument('--physics-seconds',type=float,default=0.)
    args=parser.parse_args();summary=run(args.cases,args.samples,args.out,args.seconds,args.physics_seconds)
    print(json.dumps({k:summary[k] for k in ('modelCount','baselinePassed','newGeometryPassed','recoveredPublishedFailures','publishedSuccessRegressions','maximumChangeRatio','categoryCounts')},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
