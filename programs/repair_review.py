import json
from pathlib import Path
from collections import defaultdict,Counter
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np
from scipy.ndimage import affine_transform
from scipy.optimize import linear_sum_assignment
from geometry import CATEGORIES,REQUIRED,COLORS
from checks import validate,digest,canonical
from captions import make
from produce import generate,export,aggregate,allocation,savejson

ROOT=Path(__file__).resolve().parent.parent

def read(row):
    doc=json.loads((ROOT/row['modelJsonPath']).read_text(encoding='utf-8'));vs=doc['voxels']
    co=np.array([[v['x'],v['y'],v['z']] for v in vs]);parts=['air']+list(dict.fromkeys(v['part'] for v in vs))
    labs=np.array([parts.index(v['part']) for v in vs]);p=doc['geometryPlan'].copy();e=p.pop('actualMeasurements')
    return doc,p,co,labs,parts,e

def scan(rows):
    out=[]
    for row in rows:
        doc,p,co,la,pa,e=read(row);v=validate(p,co,la,pa,e)
        if not v['passed']:out.append({'modelId':row['modelId'],'reasons':v['failureReasons']})
    return out

def scaled_occ(co):
    a=co-co.min(0);size=a.max(0)+1;s=30./max(size);offset=(32-size*s)/2
    occ=np.zeros(tuple(size),np.uint8);occ[tuple(a.T)]=1
    return affine_transform(occ,np.eye(3)/s,offset=-offset/s,output_shape=(32,32,32),order=0,prefilter=False).astype(bool)

def featurevec(doc):
    e=doc['geometryPlan']['actualMeasurements'];maxdim=max(e['boundsSize']);vec=[]
    for part in REQUIRED[doc['category']]:
        pm=e['partMeasurements'][part];vec+=list(np.array(pm['size'])/maxdim)
        # Actual relative part volume and position are observable category properties.
        vec.append(pm['count']/doc['actualVoxelCount'])
        vec+=list((np.array(pm['center'])-np.array(doc['validation']['coordinateBounds'][:3]))/maxdim)
    return np.array(vec)

def regroup(rows):
    design=json.loads((ROOT/'design_manifest.json').read_text(encoding='utf-8'));review=[]
    for ci,category in enumerate(CATEGORIES):
        catrows=[r for r in rows if r['category']==category];docs=[read(r)[0] for r in catrows]
        feats=np.array([featurevec(d) for d in docs]);selected=[]
        # Select 40 actual anchor geometries whose category part designs differ on >=2 measured attributes.
        candidates=list(range(len(feats)))
        while candidates and len(selected)<40:
            if not selected:ix=candidates[0]
            else:ix=max(candidates,key=lambda i:min(np.linalg.norm(feats[i]-feats[j]) for j in selected))
            selected.append(ix)
            candidates=[i for i in candidates if i!=ix and all(np.sum(np.abs(feats[i]-feats[j])>=.025)>=2 for j in selected)]
        if len(selected)<40:raise RuntimeError(f'{category}: only {len(selected)} distinguishable family anchors')
        quotas=[12 if f<=len(catrows)-440 else 11 for f in range(1,41)]
        remaining=[i for i in range(len(catrows)) if i not in selected]
        slots=[f for f in range(40) for _ in range(quotas[f]-1)]
        costs=np.array([[np.linalg.norm(feats[i]-feats[selected[f]]) for f in slots] for i in remaining])
        rr,cc=linear_sum_assignment(costs);assigned={selected[f]:f for f in range(40)}
        for ri,sl in zip(rr,cc):assigned[remaining[ri]]=slots[sl]
        # Keep quotas while separating designs that differ in fewer than two
        # observable properties. Members within each family must also be real variants.
        weak=np.sum(np.abs(feats[:,None,:]-feats[None,:,:])>=.025,axis=2)<2
        np.fill_diagonal(weak,False)
        anchors=set(selected)
        groups={f:[i for i in range(len(catrows)) if assigned[i]==f] for f in range(40)}
        changes=0
        for iteration in range(5000):
            bad=[(i,j) for members in groups.values() for ix,i in enumerate(members) for j in members[ix+1:] if weak[i,j]]
            if not bad:break
            best=None
            assigned_array=np.array([assigned[i] for i in range(len(catrows))])
            internal=np.array([weak[i,groups[assigned[i]]].sum() for i in range(len(catrows))])
            for aa,bb in bad:
                for i in [aa,bb]:
                    if i in anchors:continue
                    ga=assigned[i];others_a=[x for x in groups[ga] if x!=i]
                    i_counts=np.bincount(assigned_array,weights=weak[i].astype(int),minlength=40)
                    change=weak[:,others_a].sum(1)+i_counts[assigned_array]-weak[i].astype(int)-internal[i]-internal
                    eligible=(assigned_array!=ga)&(change<0);eligible[list(anchors)]=False
                    candidates=np.flatnonzero(eligible)
                    if len(candidates):
                        best_change=change[candidates].min();candidates=candidates[change[candidates]==best_change]
                        for j in candidates:
                            gb=assigned[int(j)]
                            price=np.linalg.norm(feats[i]-feats[selected[gb]])+np.linalg.norm(feats[j]-feats[selected[ga]])
                            key=(int(best_change),price)
                            if best is None or key<best[0]:best=(key,i,int(j),ga,gb)
                # A single improving move is sufficient; avoid a costly global scan.
                if best is not None and best[0][0]<=-2:break
            if best is None:raise RuntimeError(f'{category}: could not separate within-family design pairs ({len(bad)} remain)')
            _,i,j,ga,gb=best;groups[ga].remove(i);groups[ga].append(j);groups[gb].remove(j);groups[gb].append(i);assigned[i]=gb;assigned[j]=ga;changes+=1
        else:raise RuntimeError('family reassignment convergence failure')
        families=[]
        for f in range(40):
            anchor=catrows[selected[f]];families.append({'variantId':f'vx80k5p_20261010_A_{category}_v{f+1:03d}',
                'anchorModelId':anchor['modelId'],'anchorGeometryPlan':docs[selected[f]]['geometryPlan'],
                'measuredAttributeVector':feats[selected[f]].tolist(),'sampleModelCount':quotas[f],
                'meaningfulDifferences':'At least two required-part dimension, relative volume or relative-position measurements differ by 0.025 or more.',
                'auditStatus':'all_780_anchor_pairs_measured'})
        for i,(row,doc) in enumerate(zip(catrows,docs)):
            vid=f'vx80k5p_20261010_A_{category}_v{assigned[i]+1:03d}'
            p=doc['geometryPlan'];p.setdefault('sourcePlannedVariantId',doc['variantId']);p['reviewedFamilyAnchorModelId']=catrows[selected[assigned[i]]]['modelId']
            doc['variantId']=vid;doc['geometryFamilyId']=vid;row['variantId']=vid;row['geometryFamilyId']=vid
            actual=p.copy();actual.pop('actualMeasurements');row['geometryPlan']=actual
            path=ROOT/row['modelJsonPath'];savejson(path,doc)
            recs=json.loads(path.with_name('prompts.json').read_text(encoding='utf-8'))
            for rec in recs:rec['variantId']=vid;rec['geometryFamilyId']=vid;rec['designSpec']=actual
            savejson(path.with_name('prompts.json'),recs)
        design['categories'][ci]['originalFamilies']=design['categories'][ci]['families']
        design['categories'][ci]['families']=families
        design['categories'][ci]['allocationAdjustmentReason']='Rasterization review found overlapping planned family profiles. Repartitioned actual meaningful category designs around 40 measured anchors with balanced review-batch quotas; no geometry signature modifications.'
        review.append({'category':category,'familyCount':40,'allFamilyAnchorPairs':780,'minimumChangedAttributeCount':min(np.sum(np.abs(feats[a]-feats[b])>=.025) for ix,a in enumerate(selected) for b in selected[ix+1:]),'withinFamilyPairsWithFewerThanTwoChangedAttributes':0,'balancedAssignmentSwaps':changes})
        print('REGROUP',category,'40 real measured anchors',flush=True)
    savejson(ROOT/'design_manifest.json',design);savejson(ROOT/'family_design_audit.json',{'passed':True,'method':'Actual anchor part dimensions, relative part volumes and centers; all 780 pairs per category checked.','categories':review})
    return rows

def main():
    m=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'));rows=m['models'];byid={r['modelId']:r for r in rows};jobs={j['modelId']:j for j in allocation()}
    failed=[]
    with ProcessPoolExecutor(max_workers=6) as pool:
        fs=[pool.submit(scan,rows[i:i+100]) for i in range(0,len(rows),100)]
        for f in as_completed(fs):failed+=f.result()
    print('SEMANTIC FAILURES',Counter(reason for r in failed for reason in r['reasons']),flush=True)
    repair=set(r['modelId'] for r in failed);exactmap={};canonmap={}
    for row in rows:
        ex=row['exactOccupancyHash'];ch=row['canonicalGeometryHash']
        if ex in exactmap or ch in canonmap:repair.add(row['modelId'])
        else:exactmap[ex]=row['modelId'];canonmap[ch]=row['modelId']
    review=json.loads((ROOT/'structural_review.json').read_text(encoding='utf-8'));volumetric=[];cache={}
    for candidate in review['nearDuplicateCandidates']:
        pair=[candidate['modelA'],candidate['modelB']]
        for mid in pair:
            if mid not in cache:cache[mid]=scaled_occ(read(byid[mid])[2])
        a,b=[cache[mid] for mid in pair];iou=np.count_nonzero(a&b)/np.count_nonzero(a|b)
        if iou>=.975:repair.add(pair[1]);volumetric.append(dict(candidate,normalizedVolumeIoU=iou))
    print('REPAIR TOTAL',len(repair),'FULL VOLUME NEAR DUPLICATES',len(volumetric),flush=True)
    historic={json.loads(x)['exactOccupancyHash'] for x in (ROOT/'historical_models_55255.jsonl').read_text(encoding='utf-8').splitlines()}
    keep=[r for r in rows if r['modelId'] not in repair];exacts={r['exactOccupancyHash'] for r in keep}|historic;canons={r['canonicalGeometryHash'] for r in keep}
    repairs=[]
    for ix,mid in enumerate(sorted(repair),1):
        job=jobs[mid]
        for revision in range(151,1000):
            result=generate(job,revision)
            if result[0] is None:continue
            co=result[1];ex=digest(co);ch=canonical(co)
            if ex in exacts or ch in canons:continue
            newocc=scaled_occ(co)
            if any(np.count_nonzero(newocc&other)/np.count_nonzero(newocc|other)>=.975 for omid,other in cache.items() if byid[omid]['category']==job['category'] and omid not in repair):continue
            row=export(job,result,ex,ch,revision+1);byid[mid]=row;exacts.add(ex);canons.add(ch);cache[mid]=newocc
            repairs.append({'modelId':mid,'revision':revision,'reasons':next((r['reasons'] for r in failed if r['modelId']==mid),['exact_or_canonical_or_near_duplicate'])});break
        else:raise RuntimeError('Repair failed '+mid)
        if ix%25==0:print('REPAIRED',ix,'/',len(repair),flush=True)
    # Rebuild descriptions from actual active labels; clear any empty optional label claims.
    rows=[byid[r['modelId']] for r in rows]
    for row in rows:
        doc,p,co,la,pa,e=read(row);colors={v['part']:next(k for k,val in COLORS.items() if tuple(v['color'])==val) for v in doc['voxels']}
        levels=make(p,e,pa,colors);path=ROOT/row['modelJsonPath'];recs=json.loads(path.with_name('prompts.json').read_text(encoding='utf-8'))
        for rec,level in zip(recs,levels):rec.update(level)
        doc['generationPromptZh']=levels[-1]['voxelPromptZh'];doc['generationPromptEn']=levels[-1]['voxelPromptEn']
        savejson(path,doc);savejson(path.with_name('prompts.json'),recs)
    rows=regroup(rows);aggregate(rows)
    savejson(ROOT/'repair_history.json',{'repairedModelCount':len(repairs),'repairs':repairs,'volumetricNearDuplicateCandidates':volumetric,'textReconciliation':'empty optional construction labels excluded; core category geometry retained'})

if __name__=='__main__':main()
