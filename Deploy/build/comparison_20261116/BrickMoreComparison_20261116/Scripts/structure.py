"""Original BrickNet 0.1.0 collision kernel over a common file-order representation."""
import argparse,json,os,sys
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path
from common import ROOT,Journal,digest,dump,emit,rows,sha

def one(row,root):
    import numpy as np
    import bricknet
    from bricknet.data import load_catalog
    from bricknet.collision import check_placements
    if bricknet.__version__!='0.1.0':raise RuntimeError('P_inv requires pinned BrickNet 0.1.0')
    value=json.loads((Path(root)/row['assembly_path']).read_text(encoding='utf-8'));catalog=load_catalog()
    parts=[catalog.stem_to_id[p['part_stem']] for p in value['instances']]
    matrices=[np.asarray(p['matrix_ldu'],dtype=float) for p in value['instances']]
    bad=check_placements(parts,matrices)
    return dict(sample_id=row['sample_id'],status='ok',metric='pinv_file_order',n_actions=len(parts),
        collisions=bad,invalid_placements=len(bad),pinv=len(bad)/len(parts),
        order_provenance=row['order_provenance'],original_generation_order_verified=False,
        fixed_edge_exemptions=False,missing_colliders_are_zero=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--workers',type=int,default=1);a=p.parse_args()
    if a.workers!=1:p.error('Use --workers 1 for the validated isolated MeshLib runtime')
    os.environ['BRICKNET_DATA']=str(ROOT/'Assets');items=rows(a.input)
    journal=Journal(a.out,dict(input_sha256=sha(a.input),backend='bricknet-0.1.0 original inset MeshLib kernel',
       metric='pinv_file_order',catalog_sha256=sha(ROOT/'Assets/catalog.json'),source_sha256=sha(__file__)))
    pool=None;consecutive=0
    try:
        for index,row in enumerate(items,1):
            ih=digest({'assembly':row['assembly_sha256'],'source':row['source_sha256']})
            if not journal.cached(row['sample_id'],ih):
                if pool is None:pool=ProcessPoolExecutor(max_workers=1,mp_context=get_context('spawn'))
                print('STRUCTURE_START '+row['sample_id'],flush=True)
                try:result=pool.submit(one,row,str(ROOT)).result();consecutive=0
                except Exception as exc:
                    result=dict(sample_id=row['sample_id'],status='error',error=repr(exc),pinv=None,n_actions=row['part_count'])
                    pool.shutdown(wait=False,cancel_futures=True);pool=None;consecutive+=1
                    if consecutive>=3:raise RuntimeError('Three consecutive structural failures; inspect environment/structure.log') from exc
                journal.add(result,ih)
            emit('structure',index,len(items),row['sample_id'])
    finally:
        if pool:pool.shutdown(wait=True,cancel_futures=True)
    valid=[v for v in journal.done.values() if v['status']=='ok']
    dump(a.out.with_suffix('.summary.json'),dict(metric='pinv_file_order',scored=len(valid),missing=len(items)-len(valid),
      pinv_macro=sum(v['pinv'] for v in valid)/len(valid) if valid else None,
      pinv_micro=sum(v['invalid_placements'] for v in valid)/sum(v['n_actions'] for v in valid) if valid else None,
      original_generation_order_verified=False))

if __name__=='__main__':main()
