"""Supplemental MRV exact-cover search; never loosens assembly policies.

Keeps the initial run immutable. Only independently read-back successful
refinements can replace its search-failed entries in the final selection.
"""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
import json
from pathlib import Path
import shutil
import time

import assembly_pipeline as a


VERSION = 'B_layer_mrv_exact_cover_v1'
_BASE = None
_OUT = None
_DATASET = None
_POLICY = None


def solve(model, cfg, max_seconds=3, max_nodes=10000):
    """Exact-cover each complete layer, branching on the most constrained cell.

    Supported candidate rectangles are precomputed. The same-color source
    footprint and lower studs cannot change during a layer, so bitset coverage
    avoids consuming the only feasible anchor of a narrow unsupported region.
    The first layer solution is retained; this is not complete global search.
    """
    started = time.monotonic()
    deadline = started+max_seconds
    nodes = 0
    state = a.GeometryState(cfg)
    best = state
    stop = 'complete'
    for z in sorted({p[2] for p in model.cells}):
        points = sorted(p for p in model.cells if p[2]==z)
        indices = {p:i for i,p in enumerate(points)}
        candidates = []
        by_point = [[] for _ in points]
        for x,y,_ in points:
            for h,w in cfg.dimensions:
                b = a.Placement(h,w,x,y,z)
                cells = tuple(b.cells())
                if not all(p in indices and model.cells[p]==model.cells[(x,y,z)] for p in cells):
                    continue
                # Eligibility ignores only temporary component budget; it is
                # checked again on the actual prefix before each commit.
                supports = [(p[0],p[1]) for p in cells if (p[0],p[1],z-1) in state.occupied]
                if z and (not supports or len(supports)/len(cells)<cfg.min_support_fraction):
                    continue
                if z and cfg.max_cantilever_distance is not None and max(
                        min(abs(p[0]-x0)+abs(p[1]-y0) for x0,y0 in supports) for p in cells)>cfg.max_cantilever_distance:
                    continue
                mask = sum(1<<indices[p] for p in cells)
                index = len(candidates)
                candidates.append((mask,b))
                for p in cells:
                    by_point[indices[p]].append(index)
        full = (1<<len(points))-1
        def search(current, remaining):
            nonlocal nodes,best,stop
            if len(current.occupied)>len(best.occupied):
                best=current
            if not remaining:
                return current
            nodes += 1
            if nodes>max_nodes or time.monotonic()>=deadline:
                stop='node_budget' if nodes>max_nodes else 'time_budget'
                return None
            smallest = None
            bits = remaining
            while bits:
                bit=bits&-bits
                i=bit.bit_length()-1
                bits-=bit
                # Geometry/support are precomputed against the fixed preceding
                # layer. Component budget depends on brick partitions and is
                # checked at the actual commit, not in every MRV cell scan.
                live=[j for j in by_point[i] if candidates[j][0]&remaining==candidates[j][0]]
                if not live:
                    return None
                if smallest is None or len(live)<len(smallest):
                    smallest=live
                    if len(live)==1:
                        break
            def rank(j):
                mask,b=candidates[j]
                support,contacts=current.contact(b)
                roots={current.find(i) for i in contacts}
                from interlocking import seam_metrics
                seam=seam_metrics(b,current)
                return (max(0,len(roots)-1)*100+mask.bit_count()*2+support*2
                        +seam['crossed_seams']*4-seam['aligned_seams']*3,
                        int((b.h>b.w)==(z%2==0)), -b.x,-b.y)
            for j in sorted(smallest,key=rank,reverse=True):
                mask,b=candidates[j]
                if current.check(b)!='success':
                    continue
                child=current.clone()
                child.add(b)
                found=search(child,remaining^mask)
                if found is not None:
                    return found
                if stop in ('node_budget','time_budget'):
                    return None
            return None
        next_state=search(state,full)
        if next_state is None:
            if stop=='complete':
                stop='layer_search_exhausted'
            break
        state=next_state
        best=state
    raw=[{**asdict(b),'color':model.cells[(b.x,b.y,b.z)]} for b in best.bricks]
    return raw,{'algorithmVersion':VERSION,'nodes':nodes,'termination':stop,
                'elapsedSeconds':time.monotonic()-started,
                'maxSeconds':max_seconds,'maxNodes':max_nodes,
                'scope':'layer exact cover with fixed previous layer, not complete global search'}


def initialize(base,out,dataset,policy):
    global _BASE,_OUT,_DATASET,_POLICY
    _BASE,_OUT,_DATASET,_POLICY=Path(base),Path(out),Path(dataset),policy


def process(job):
    folder=_OUT/'models'/job['category']/job['modelId']
    source_path=_DATASET/job['modelPath']/'model.json'
    source=json.loads(source_path.read_text(encoding='utf8'))
    model,original=a.dataset_model(source)
    if a.exact_hash(original)!=job['exactOccupancyHash']:
        raise ValueError('input manifest mismatch')
    if (folder/'report.json').exists():
        old=json.loads((folder/'report.json').read_text(encoding='utf8'))
        if a.file_sha(source_path)!=old['sourceFileSha256'] or not all(
                a.file_sha(folder/name)==v for name,v in old['outputFileSha256'].items()):
            raise ValueError('refinement checkpoint changed')
        return old
    cfg=a.GeometryConfig(world_dim=48,min_bricks=1,brick_library=_POLICY['brick_library'],
                         min_support_fraction=_POLICY['min_support_fraction'],
                         max_components=_POLICY['max_components'],
                         max_cantilever_distance=_POLICY['max_cantilever_distance'])
    raw,search=solve(model,cfg)
    check=a.independent_audit(raw,model.cells,_POLICY)
    status='success' if check['passed'] else 'search_failed'
    folder.mkdir(parents=True,exist_ok=True)
    a.dump(folder/'assembly.json',{'algorithmVersion':VERSION,'modelId':job['modelId'],
                                 'status':'success' if check['passed'] else 'draft',
                                 'assemblyOutcome':status,'bricks':raw,'policy':_POLICY,
                                 'coordinateSystem':{'sourceToInternal':'[x,y,z] -> [x,z,y]',
                                     'ldrUnitScales':[20,20,24],
                                     'physicalAspectRatioDiffersFromIsotropicVoxelPreview':True},
                                 'staticVerified':None,'fullPhysics':False})
    suffix='' if check['passed'] else '.draft'
    geometry=[{k:b[k] for k in ('h','w','x','y','z')} for b in raw]
    (folder/f'model{suffix}.txt').write_text(''.join(a.Placement(**b).to_txt() for b in geometry),encoding='utf8')
    (folder/f'model{suffix}.ldr').write_text(a.to_ldr({'status':'success' if check['passed'] else 'draft','bricks':geometry},model.cells),encoding='utf8')
    readback=a.exported_audit(folder,source,_POLICY)
    if readback['passed']!=check['passed']:
        raise ValueError('refinement export mismatch')
    a.dump(folder/'validation.json',readback)
    report={'modelId':job['modelId'],'category':job['category'],'status':status,
            'geometryPassed':readback['passed'],'validation':readback,'search':search,
            'sourceFileSha256':a.file_sha(source_path),'sourceExactOccupancyHash':job['exactOccupancyHash'],
            'sourceCanonicalGeometryHash':job['canonicalGeometryHash'],
            'sourceModelPath':str(source_path.resolve()),'staticVerified':None,'fullPhysics':False,
            'outputFileSha256':{p.name:a.file_sha(p) for p in sorted(folder.iterdir())}}
    a.dump(folder/'report.json',report)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('probe','run','verify','select'))
    p.add_argument('--base',type=Path,default=a.HERE/'runs'/'B_extended_v2')
    p.add_argument('--out',type=Path,default=a.HERE/'runs'/'B_layer_refinement_v1')
    p.add_argument('--workers',type=int,default=12)
    p.add_argument('--count',type=int,default=10)
    p.add_argument('--per-category',type=int,default=0,help='balanced probe limit per category')
    args=p.parse_args()
    base_config=json.loads((args.base/'config.json').read_text(encoding='utf8'))
    dataset=Path(base_config['datasetPath'])
    policy=base_config['policy']
    jobs=json.loads((args.base/'selection.json').read_text(encoding='utf8'))
    base_rows={}
    failed=[]
    for job in jobs:
        path=args.base/'models'/job['category']/job['modelId']/'report.json'
        if not path.exists():
            continue
        row=json.loads(path.read_text(encoding='utf8'))
        base_rows[job['modelId']]={k:row[k] for k in ('status','category','geometryPassed')}
        if row['status']=='search_failed':
            failed.append(job)
    if args.action=='probe':
        if args.per_category:
            category_counts=Counter()
            balanced=[]
            for job in failed:
                if category_counts[job['category']]<args.per_category:
                    balanced.append(job)
                    category_counts[job['category']]+=1
            failed=balanced
        failed=failed[:args.count]
    args.out.mkdir(parents=True,exist_ok=True)
    config={'algorithmVersion':VERSION,'baseRun':str(args.base.resolve()),'datasetPath':str(dataset),
            'policy':policy,'sourceFileSha256':a.file_sha(__file__),
            'adapterSourceFileSha256':a.file_sha(a.__file__),
            'baseConfigSha256':a.file_sha(args.base/'config.json'),
            'maxSeconds':3,'maxNodes':10000,
            'toolkitSourceSha256':base_config['toolkitSourceSha256']}
    if (args.out/'config.json').exists():
        if json.loads((args.out/'config.json').read_text(encoding='utf8'))!=config:
            p.error('configuration changed; choose a new refinement directory')
    else:
        a.dump(args.out/'config.json',config)
        shutil.copyfile(__file__,args.out/'refinement_runner_snapshot.py')
    initialize(args.base,args.out,dataset,policy)
    if args.action in ('run','probe'):
        counts=Counter()
        with ProcessPoolExecutor(max_workers=args.workers,initializer=initialize,
                                 initargs=(args.base,args.out,dataset,policy)) as pool:
            for number,result in enumerate(pool.map(process,failed),1):
                counts[result['status']]+=1
                if args.action=='probe' or number%100==0 or number==len(failed):
                    print('REFINEMENT_PROGRESS',number,'/',len(failed),dict(counts),flush=True)
        a.dump(args.out/'summary.json',{'attemptedModelCount':len(failed),'statusCounts':dict(counts),
                                      'staticVerified':None,'fullPhysics':False})
    elif args.action=='verify':
        verification_jobs=[j for j in failed if (args.out/'models'/j['category']/j['modelId']/'report.json').exists()]
        a.initialize(dataset,args.out,policy)
        counts=Counter()
        with ProcessPoolExecutor(max_workers=args.workers,initializer=a.initialize,
                                 initargs=(dataset,args.out,policy)) as pool:
            for outcome in pool.map(a.verify_job,verification_jobs,chunksize=8):
                counts[outcome]+=1
        a.dump(args.out/'readback_verification.json',{'readbackVerifiedModelCount':len(verification_jobs),
                    'counts':dict(counts),'allDeliveredOutputsReadbackPassed':not counts['missing_output'],
                    'staticVerified':None,'fullPhysics':False})
        print('REFINEMENT_READBACK',dict(counts),flush=True)
    # Final index retains every source model exactly once. Failed refinements
    # do not replace the first run's draft or infer infeasibility.
    selected=[]
    refined=0
    for job in jobs:
        if job['modelId'] not in base_rows:
            continue
        base=base_rows[job['modelId']]
        folder=args.base/'models'/job['category']/job['modelId']
        candidate=args.out/'models'/job['category']/job['modelId']
        if (candidate/'report.json').exists():
            row=json.loads((candidate/'report.json').read_text(encoding='utf8'))
            if row['geometryPassed']:
                base={'status':'success','category':job['category'],'geometryPassed':True}
                folder=candidate
                refined+=1
        selected.append({'modelId':job['modelId'],**base,'resultPath':str(folder.resolve()),
                         'sourceExactOccupancyHash':job['exactOccupancyHash'],
                         'sourceCanonicalGeometryHash':job['canonicalGeometryHash'],
                         'reportFileSha256':a.file_sha(folder/'report.json'),'fullPhysics':False})
    (args.out/'selected_assembly_index.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in selected),encoding='utf8')
    counts=Counter(row['status'] for row in selected)
    a.dump(args.out/'selected_summary.json',{'sourceModelCount':len(jobs),'processedModelCount':len(selected),
               'remainingModelCount':len(jobs)-len(selected),'statusCounts':dict(counts),
               'additionalPassedModelCount':refined,'voxelSourceModified':False,
               'staticVerified':None,'fullPhysics':False})
    print('SELECTED_SUMMARY',dict(counts),'refined',refined,flush=True)


if __name__=='__main__':
    main()
