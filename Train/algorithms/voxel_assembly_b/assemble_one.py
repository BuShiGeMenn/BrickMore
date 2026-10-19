"""Run exact-grid LEGO assembly and independent readback on one Y-up RGB JSON."""
import argparse
from dataclasses import asdict
import json
import math
from pathlib import Path

import assembly_pipeline as a
import layer_cover


def run_model(input_path, out, seconds=3, nodes=1500):
    if not math.isfinite(seconds) or seconds <= 0 or nodes < 1:
        raise ValueError('finite positive search budgets required')
    input_path,out=Path(input_path),Path(out)
    if out.exists():
        raise ValueError('output already exists; choose a new directory')
    value=json.loads(input_path.read_text(encoding='utf-8-sig'))
    if not isinstance(value,dict) or 'voxels' not in value:
        raise ValueError('expected object with Y-up voxels and RGB triplets')
    value={**value,'modelId':value.get('modelId',input_path.stem),
           'actualVoxelCount':value.get('actualVoxelCount',len(value['voxels']))}
    model,original=a.dataset_model(value)
    cfg=a.GeometryConfig(world_dim=48,min_bricks=1,brick_library='extended',
                         min_support_fraction=.1,max_cantilever_distance=2,max_components=64)
    policy={**asdict(cfg),'max_seconds':seconds,'max_nodes':nodes,'beam_width':8}
    necessary=a.feasibility(model,cfg)
    raw=[]
    attempts=[]
    if necessary['passed']:
        raw,details=a.greedy(model,cfg,value.get('modelSeed',42),seconds)
        attempts.append({'algorithm':'checked_greedy','details':details})
        if not a.independent_audit(raw,model.cells,policy)['passed']:
            result=a.assemble(model,cfg,max_nodes=nodes,beam_width=8,seed=value.get('modelSeed',42),
                              max_seconds=seconds,solution_limit=1,improve_nodes=0)
            candidate=[{**b,'color':model.cells[(b['x'],b['y'],b['z'])]} for b in result['bricks']]
            if a.independent_audit(candidate,model.cells,policy)['passed'] or sum(b['h']*b['w'] for b in candidate)>sum(b['h']*b['w'] for b in raw):
                raw=candidate
            attempts.append({'algorithm':'exact_interlocking_v2','stop':result['search_stop'],'nodes':result['nodes']})
        if not a.independent_audit(raw,model.cells,policy)['passed']:
            candidate,details=layer_cover.solve(model,cfg,max_seconds=seconds,max_nodes=10000)
            if a.independent_audit(candidate,model.cells,policy)['passed'] or sum(b['h']*b['w'] for b in candidate)>sum(b['h']*b['w'] for b in raw):
                raw=candidate
            attempts.append({'algorithm':layer_cover.VERSION,'details':details})
    check=a.independent_audit(raw,model.cells,policy)
    status='success' if check['passed'] else 'draft'
    geometry=[{k:b[k] for k in ('h','w','x','y','z')} for b in raw]
    out.mkdir(parents=True)
    a.dump(out/'assembly.json',{'modelId':value['modelId'],'status':status,'bricks':raw,'policy':policy,
           'sourceUpAxis':'y','internalUpAxis':'z','sourceToInternal':'[x,y,z] -> [x,z,y]',
           'ldrUnitScales':[20,20,24],'staticVerified':None,'fullPhysics':False})
    suffix='' if status=='success' else '.draft'
    (out/f'model{suffix}.txt').write_text(''.join(a.Placement(**b).to_txt() for b in geometry),encoding='utf8')
    (out/f'model{suffix}.ldr').write_text(a.to_ldr({'status':status,'bricks':geometry},model.cells),encoding='utf8')
    readback=a.exported_audit(out,value,policy)
    if readback['passed']!=check['passed']:
        raise ValueError('exported files do not match the selected geometry')
    a.dump(out/'validation.json',readback)
    report={'status':status,'algorithm':'checked greedy + exact_interlocking_v2 + layer MRV exact cover',
            'sourceFileSha256':a.file_sha(input_path),'sourceExactOccupancyHash':a.exact_hash(original),
            'feasibility':necessary,'searchAttempts':attempts,'validation':readback,
            'staticVerified':None,'fullPhysics':False}
    a.dump(out/'report.json',report)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',type=Path)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--seconds',type=float,default=3)
    p.add_argument('--nodes',type=int,default=1500)
    args=p.parse_args()
    if not math.isfinite(args.seconds) or args.seconds<=0 or args.nodes<1:
        p.error('finite positive search budgets required')
    try:
        result=run_model(args.input,args.out,args.seconds,args.nodes)
    except (ValueError,KeyError,OSError) as exc:
        p.error(str(exc))
    print(json.dumps({'status':result['status'],'geometryPassed':result['validation']['passed'],
                      'fullPhysics':False,'report':str((args.out/'report.json').resolve())},ensure_ascii=False))
    return 0 if result['validation']['passed'] else 2


if __name__=='__main__':
    raise SystemExit(main())
