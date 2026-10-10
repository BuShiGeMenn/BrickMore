"""Repair only new continuation models identified by whole-shard review."""
import json,sqlite3
from collections import defaultdict
import numpy as np
from scipy.spatial import cKDTree
from complete_shard import ROOT,allocate,generate,descriptor,overlaps,aggregate
from produce import export,savejson,part_metrics
from checks import digest,canonical
from repair_review import featurevec
from review_full import measured

def main():
    rows=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))['models'];byid={r['modelId']:r for r in rows}
    frozen,jobs=allocate();protected={r['modelId'] for r in frozen};jobmap={j['modelId']:j for j in jobs}
    review=json.loads((ROOT/'structural_review.json').read_text(encoding='utf-8'));failed=set();reasons=defaultdict(list)
    for flag in review['nearDuplicateCandidates']:
        candidates=[m for m in [flag['modelB'],flag['modelA']] if m not in protected]
        assert candidates,'First-batch geometry cannot be repaired by this continuation tool'
        failed.add(candidates[0]);reasons[candidates[0]].append(flag)
    report=ROOT/'independent_verification.json'
    if report.exists():
        verification=json.loads(report.read_text(encoding='utf-8'))
        for error in verification['errors']:
            if 'modelId' in error:
                assert error['modelId'] not in protected
                failed.add(error['modelId']);reasons[error['modelId']].append(error)
    assert not review['familyReviewPairs'],'Family partition issue requires a separate measured assignment review'
    if not failed:print('NO CONTINUATION REPAIR REQUIRED');return
    historic={json.loads(x)['exactOccupancyHash'] for x in (ROOT/'historical_models_55255.jsonl').read_text(encoding='utf-8').splitlines()}
    retained=[r for r in rows if r['modelId'] not in failed];exacts=historic|{r['exactOccupancyHash'] for r in retained};canons={r['canonicalGeometryHash'] for r in retained}
    design=json.loads((ROOT/'design_manifest.json').read_text(encoding='utf-8'))
    anchors={f['variantId']:dict(f['anchorGeometryPlan'],modelId=f['anchorModelId']) for c in design['categories'] for f in c['families']}
    fam=defaultdict(list);cross=[];volumes=[];views=[];original=[];coarse=[]
    for row in retained:
        doc,co,e=measured(row);fam[row['variantId']].append(featurevec(doc));e['_category']=row['category']
        cr,cs,vo,vi,ori=descriptor(co,e);cross.append(cr);coarse.append(cs);volumes.append(vo);views.append(vi);original.append(ori)
    cross=np.array(cross);history=[]
    for n,mid in enumerate(sorted(failed),1):
        job=jobmap[mid]
        for revision in range(2001,6001):
            result=generate(job,revision,anchors[job['variantId']])
            if result[0] is None:continue
            p,co,la,pa,cl,e,v,h,initial=result;e['partMeasurements']=part_metrics(co,la,pa)
            fv=featurevec({'category':job['category'],'geometryPlan':{'actualMeasurements':e},'actualVoxelCount':len(co),'validation':v})
            if np.any((np.abs(np.array(fam[job['variantId']])-fv)>=.025).sum(1)<2):continue
            ex=digest(co);ch=canonical(co)
            if ex in exacts or ch in canons:continue
            e['_category']=job['category'];cr,cs,vo,vi,ori=descriptor(co,e);e.pop('_category')
            candidates=set(np.flatnonzero(np.abs(cross-cr).max(1)<=.055))
            for i,r in enumerate(retained):
                if r['category']==job['category'] and np.abs(coarse[i]-cs).max()<.055:candidates.add(i)
            if any(overlaps(vo,volumes[i])>=.975 and (min(overlaps(a,b) for a,b in zip(vi,views[i]))>=.985 or
                (retained[i]['category']==job['category'] and min(overlaps(a,b) for a,b in zip(ori,original[i]))>=.985)) for i in candidates):continue
            row=export(job,result,ex,ch,revision+1);byid[mid]=row;retained.append(row);exacts.add(ex);canons.add(ch)
            cross=np.vstack([cross,cr]);coarse.append(cs);volumes.append(vo);views.append(vi);original.append(ori);fam[job['variantId']].append(fv)
            history.append({'modelId':mid,'revision':revision,'reason':reasons[mid]});print('CONTINUATION REPAIR',n,'/',len(failed),mid,flush=True);break
        else:raise RuntimeError('Could not repair new geometry '+mid)
    conn=sqlite3.connect(ROOT/'checkpoints'/'dedup_registry.sqlite')
    for h in history:
        row=byid[h['modelId']];conn.execute('UPDATE models SET exact=?,canonical=? WHERE modelId=?',(row['exactOccupancyHash'],row['canonicalGeometryHash'],row['modelId']))
    conn.commit();conn.close()
    rows=[byid[r['modelId']] for r in rows]
    for c in {byid[mid]['category'] for mid in failed}:
        path=ROOT/'checkpoints'/f'{c}.json';checkpoint=json.loads(path.read_text(encoding='utf-8'));checkpoint['models']=[r for r in rows if r['category']==c];savejson(path,checkpoint)
    prior=ROOT/'continuation_repair_history.json';old=json.loads(prior.read_text(encoding='utf-8'))['repairs'] if prior.exists() else []
    savejson(prior,{'repairedModelCount':len(old)+len(history),'repairs':old+history,'retainedFirstBatchUntouched':True})
    aggregate(rows);print('CONTINUATION REPAIRS COMPLETE',len(history),flush=True)

if __name__=='__main__':main()
