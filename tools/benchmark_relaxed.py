"""Independent random modular-geometry trial; no publication or old flag edits."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import argparse
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'algorithms/voxel_assembly_relaxed'))
import relaxed_core as r


def check(task):
    job,seconds,deliver_out=task
    if deliver_out is not None:
        import relaxed_pipeline as p
        report=p.worker((job,job['datasetPath'],deliver_out,dict(ratio=.02,seconds=seconds,physicsSeconds=5.)))
        return dict(modelId=job['modelId'],shardId=job['shardId'],passed=report['status']=='success',audit=report['geometryValidation'],repair=report['repairAudit'],
                    attempts=report['searchAttempts'],seconds=report['elapsedSeconds'],physicsStatus=report['physics']['status'],qualityScreenedSuccess=report['qualityScreenedSuccess'])
    source=json.loads((Path(job['datasetPath'])/job['modelPath']/'model.json').read_bytes())
    model,_=r.q.a.dataset_model(source);outcome=r.optimize(model.cells,seconds)
    result=r.audit(outcome['bricks'],outcome['targetCells'])
    return dict(modelId=job['modelId'],shardId=job['shardId'],passed=result['passed'],audit=result,
                repair=outcome['repairAudit'],attempts=outcome['searchAttempts'],seconds=outcome['elapsedSeconds'])


def main():
    p=argparse.ArgumentParser();p.add_argument('--count',type=int,default=400);p.add_argument('--workers',type=int,default=4)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--seconds',type=float,default=6.);p.add_argument('--seed',default='relaxed-eval-independent-89213');p.add_argument('--deliver',action='store_true');args=p.parse_args()
    plan=json.loads((ROOT/'downloads/quality_q4_balanced_80000_20261012/plan.json').read_bytes())
    jobs=sorted(plan['jobs'],key=lambda j:r.q.a.sha((args.seed+j['modelId']).encode()))[:args.count]
    deliver_out=None
    if args.deliver:
        deliver_out=str(args.out.resolve().with_suffix(''))
        if not Path(deliver_out).is_relative_to(ROOT/'downloads') or Path(deliver_out).exists():raise ValueError('new private pilot directory required')
        for job in jobs:job['priorStrictFolder']=str(Path(plan['out'])/'models'/job['category']/job['modelId'])
    started=time.monotonic()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:rows=list(pool.map(check,[(job,args.seconds,deliver_out) for job in jobs]))
    value=dict(policy=r.POLICY,policyVersion=r.VERSION,sampleCount=len(rows),passed=sum(row['passed'] for row in rows),
               seconds=time.monotonic()-started,failureReasons=dict(Counter(row['attempts'][-1].get('reason',row['attempts'][-1]['stage']) for row in rows if not row['passed'])),
               rows=rows,isFullCensus=False,physicalPassRateNotClaimed=True,searchSeconds=args.seconds,
               actualJSONTXTLDRAndForceWitnessReadback=args.deliver)
    r.q.a.dump(args.out,value);print(json.dumps({k:v for k,v in value.items() if k!='rows'},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
