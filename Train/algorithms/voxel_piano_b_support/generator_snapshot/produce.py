import argparse,csv,hashlib,json,os,time,zipfile,shutil
from pathlib import Path
from collections import Counter,defaultdict
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np
from geometry import *
from checks import validate,digest,canonical
from captions import make
from render import preview,sheets
import export_core as core

ROOT=Path(__file__).resolve().parent.parent
VERSION='voxel_80000_models_400000_prompts_20261010_v2'
core.PALETTE={k:tuple(v)+(255,) for k,v in COLORS.items()}

def savejson(path,data):
    path=Path(path);tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'),default=lambda x:x.item() if hasattr(x,'item') else str(x)),encoding='utf-8')
    os.replace(tmp,path)

def allocation():
    jobs=[]
    for ci,c in enumerate(CATEGORIES):
        n=477 if ci<4 else 476
        for family in range(1,41):
            sample_n=12 if family<=n-440 else 11
            prefix=sum((48 if v<=25 else 47) if c!='vessel' else (48 if v<=20 else 47) for v in range(1,family))
            for instance in range(1,sample_n+1):
                number=prefix+instance; mid=f'vx80k5p_20261010_A_{c}_m{number:04d}'
                jobs.append({'category':c,'categoryId':ci+1,'family':family,'instance':instance,
                             'modelId':mid,'globalOrdinal':ci*1905+number,'variantId':f'vx80k5p_20261010_A_{c}_v{family:03d}'})
    assert len(jobs)==10000
    return jobs

def generate(job,revision):
    p=plan(job['category'],job['family'],job['instance'],revision)
    if job['category']=='train':p['railCoupler']=True
    initial=len(build(p)[0]);scale=1. if 750<=initial<=1250 else (1000/initial)**(1/3)
    history=[]; best=None
    for attempt in range(1,21):
        co,la,pa,cl,e=build(p,scale); v=validate(p,co,la,pa,e)
        history.append({'attempt':attempt,'absoluteUniformScaleFromOriginal':round(scale,8),'voxelCount':len(co),'failureReasons':v['failureReasons']})
        if v['passed']:
            return p,co,la,pa,cl,e,v,history,initial
        if len(co)<750 or len(co)>1250:
            scale*=np.clip((1000/max(1,len(co)))**(1/3),.8,1.25)
        else:
            # Change sampling density, retaining all original analytic features.
            scale*=1.045 if attempt%2 else .96
        if max(e['boundsSize'])>=47:scale*=.94
    return None,history

def part_metrics(co,la,pa):
    out={}
    for i,part in enumerate(pa):
        cells=co[la==i]
        if len(cells):out[part]={'count':len(cells),'size':(cells.max(0)-cells.min(0)+1).tolist(),
                               'center':cells.mean(0).round(3).tolist()}
    return out

def export(job,result,exact,canon,attempts):
    p,co,la,pa,cl,e,v,history,initial=result
    folder=ROOT/'models'/job['category']/job['modelId'];folder.mkdir(parents=True,exist_ok=True)
    e['partMeasurements']=part_metrics(co,la,pa)
    usedcolors={x:cl[x] for x in pa if x in cl and np.any(la==pa.index(x))}
    levels=make(p,e,[x for x in pa if np.any(la==pa.index(x))],usedcolors)
    base={
      'datasetVersion':VERSION,'shardId':'A','modelId':job['modelId'],'category':job['category'],
      'categoryId':job['categoryId'],'variantId':job['variantId'],'geometryFamilyId':job['variantId'],
      'semanticGroupKey':job['modelId'],'tier':'detailed','modelSeed':800000000+job['globalOrdinal'],
      'globalOrdinal':job['globalOrdinal'],'gridSize':[48,48,48],'requestedVoxelRange':[750,1250],
      'geometryPlan':dict(p,actualMeasurements=e),'initialVoxelCount':initial,'actualVoxelCount':len(co),
      'coordinateSystem':{'X':'left/right','Y':'up','Z':'front/back','localForward':'+Z','VOX':'JSON(x,y,z) -> VOX(x,z,y)'},
      'preferredVoxelTarget':1000,'generationPromptZh':levels[4]['voxelPromptZh'],
      'generationPromptEn':levels[4]['voxelPromptEn'],'generationMethod':'deterministic analytic parameter interpreter',
      'generationPromptBinding':'L5 describes the preplanned category program; parameters are the executable geometryPlan',
      'trainingInputFields':['captionZh','captionEn'],'resamplingHistory':history,
      'semanticFeatures':v['semanticMeasurements'],'exactOccupancyHash':exact,'canonicalGeometryHash':canon,
      'canonicalHashAlgorithm':'axis48_min_sha256_xyz_semicolon_v1',
      'promptRecordIds':[job['modelId']+f'_l{i}' for i in range(1,6)],
      'validation':v,'historicalCanonicalDedupStatus':'unavailable_coordinates','crossShardDedupStatus':'awaiting_merge'}
    voxels=[]; colors=[];model=core.Model()
    for coord,label in zip(co,la):
        part=pa[int(label)]; color=cl[part];rgb=list(COLORS[color]);colors.append(rgb)
        xyz=[int(x) for x in coord]
        voxels.append(dict(zip(['x','y','z'],xyz),color=rgb,part=part))
        model.cells[tuple(xyz)]=core.Cell(color,part)
    doc=dict(base,object=job['category'],voxels=voxels)
    savejson(folder/'model.json',doc)
    # Derive every format from the saved canonical JSON, including coordinates and RGB.
    canonical_doc=json.loads((folder/'model.json').read_text(encoding='utf-8'))
    co2=np.array([[x['x'],x['y'],x['z']] for x in canonical_doc['voxels']],dtype=np.uint8)
    rgb2=np.array([x['color'] for x in canonical_doc['voxels']],dtype=np.uint8)
    occ=np.zeros((48,48,48),np.uint8);occ[tuple(co2.T)]=1
    np.savez_compressed(folder/'model.npz',coords=co2,colors=rgb2,occupancy=occ)
    core.save_obj(folder/'model.obj',model);core.save_vox(folder/'model.vox',model);preview(folder/'preview.png',model)
    rel=folder.relative_to(ROOT).as_posix()
    records=[]
    for lev in levels:
        records.append({k:base[k] for k in ['datasetVersion','shardId','modelId','category','categoryId','variantId','geometryFamilyId','semanticGroupKey','modelSeed','tier','gridSize','requestedVoxelRange']}|
          lev|{'recordId':job['modelId']+f"_l{lev['promptLevel']}",'structuralVariant':p['subtype'],
            'requiredParts':REQUIRED[job['category']],'invariantFeatures':REQUIRED[job['category']],
            'changedAttributes':p['changedAttributes'],'designSpec':p,'modelJsonPath':rel+'/model.json',
            'modelNpzPath':rel+'/model.npz','targetOccupancyHash':exact,'targetCanonicalGeometryHash':canon,
            'sharesGeometryAcrossLevels':True,'expectedIndependentGeometryAcrossLevels':False})
    savejson(folder/'prompts.json',records)
    savejson(folder/'validation.json',dict(v,resamplingHistory=history,exactOccupancyHash=exact,canonicalGeometryHash=canon,
        designAttempts=attempts,formatReadback={'status':'pending_independent_readback'},
        legoPhysicalProcessingStatus='not_run'))
    row={k:base[k] for k in ['datasetVersion','shardId','modelId','category','categoryId','variantId','geometryFamilyId','semanticGroupKey','modelSeed','globalOrdinal','actualVoxelCount','exactOccupancyHash','canonicalGeometryHash']}
    row.update(modelJsonPath=rel+'/model.json',modelNpzPath=rel+'/model.npz',previewPath=rel+'/preview.png',
               designSignature=hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest(),geometryPlan=p)
    return row

def category_worker(category,jobs,pilot=False):
    historic={json.loads(x)['exactOccupancyHash'] for x in (ROOT/'historical_models_55255.jsonl').read_text(encoding='utf-8').splitlines()}
    exacts=set();canons=set();near=defaultdict(list);rows=[];retries=[];family_metrics=defaultdict(list)
    logdir=ROOT/'checkpoints';logdir.mkdir(exist_ok=True)
    for index,job in enumerate(jobs,1):
        folder=ROOT/'models'/category/job['modelId']
        if (folder/'model.json').exists() and (folder/'prompts.json').exists() and not pilot:
            doc=json.loads((folder/'model.json').read_text(encoding='utf-8'))
            co=np.array([[x['x'],x['y'],x['z']] for x in doc['voxels']]);pa=['air']+list(dict.fromkeys(x['part'] for x in doc['voxels']))
            la=np.array([pa.index(x['part']) for x in doc['voxels']]);p=doc['geometryPlan'];p.pop('actualMeasurements',None)
            # Resume only when every required file exists.
            if all((folder/f).exists() for f in ['model.npz','model.vox','model.obj','model.mtl','preview.png','validation.json']):
                co0=co-co.min(0);size=tuple(co.max(0)-co.min(0)+1)
                near[size].append(set(map(tuple,co0)))
                exacts.add(doc['exactOccupancyHash']);canons.add(doc['canonicalGeometryHash'])
                row={k:doc[k] for k in ['datasetVersion','shardId','modelId','category','categoryId','variantId','geometryFamilyId','semanticGroupKey','modelSeed','globalOrdinal','actualVoxelCount','exactOccupancyHash','canonicalGeometryHash']}
                rel=folder.relative_to(ROOT).as_posix();row.update(modelJsonPath=rel+'/model.json',modelNpzPath=rel+'/model.npz',previewPath=rel+'/preview.png',geometryPlan=p,designSignature=hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest());rows.append(row);continue
        for revision in range(150):
            result=generate(job,revision)
            if result[0] is None:
                retries.append({'modelId':job['modelId'],'revision':revision,'reason':'semantic_or_density','attempts':result[1]});continue
            p,co,la,pa,cl,e,v,history,initial=result
            ex=digest(co)
            if ex in historic or ex in exacts:
                retries.append({'modelId':job['modelId'],'revision':revision,'reason':'exact_duplicate'});continue
            ch=canonical(co)
            if ch in canons:
                retries.append({'modelId':job['modelId'],'revision':revision,'reason':'canonical_duplicate'});continue
            co0=co-co.min(0);size=tuple(co.max(0)-co.min(0)+1);pts=set(map(tuple,co0))
            closest=0.
            for previous in near[size]:
                overlap=len(pts&previous);iou=overlap/(len(pts)+len(previous)-overlap)
                closest=max(closest,iou)
            if closest>=.975:
                retries.append({'modelId':job['modelId'],'revision':revision,'reason':'near_duplicate','IoU':closest});continue
            exs=[p['widthFactor']/p['depthFactor'],p['heightFactor']/p['widthFactor'],p['partRatio'],p['spacingRatio'],p['attachmentRatio'],p['openingRatio'],p['supportSpread']]
            observable=part_metrics(co,la,pa)
            vec=np.array([x for part in REQUIRED[category] for x in observable.get(part,{'size':[0,0,0]})['size']],float)
            meaningful=True
            for old in family_metrics[job['family']]:
                changed=np.abs(vec-old)/np.maximum(2,np.maximum(vec,old))>=.075
                if changed.sum()<2:meaningful=False;break
            if not meaningful:
                retries.append({'modelId':job['modelId'],'revision':revision,'reason':'fewer_than_two_observable_part_changes'});continue
            family_metrics[job['family']].append(vec)
            e['nearDuplicateAudit']={'sameBoundsAlignedOccupancyMaximumIoU':closest,'rejectThreshold':.975,'scope':'category_same_bounds','differentBoundsStatus':'not_covered_by_IoU_test','twoChangedObservablePartDimensions':True}
            row=export(job,result,ex,ch,revision+1)
            rows.append(row);exacts.add(ex);canons.add(ch);near[size].append(pts)
            break
        else:
            savejson(logdir/f'{category}_failure.json',{'failedJob':job,'retries':retries[-150:]})
            raise RuntimeError('Unable to satisfy design quota: '+job['modelId'])
        if index%25==0 or index==len(jobs):
            savejson(logdir/f'{category}.json',{'completed':len(rows),'target':len(jobs),'models':rows,'retryCount':len(retries)})
            print(f'{category}: {len(rows)}/{len(jobs)} models, {len(rows)*5} records, redesigns={len(retries)}',flush=True)
    savejson(logdir/f'{category}.json',{'completed':len(rows),'target':len(jobs),'models':rows,'retryCount':len(retries)})
    with (logdir/f'{category}_retries.jsonl').open('w',encoding='utf-8') as f:
        for x in retries:f.write(json.dumps(x,ensure_ascii=False)+'\n')
    return rows

def design_manifest(jobs):
    categories=[]
    for c in CATEGORIES:
        cj=[j for j in jobs if j['category']==c]
        families=[]
        for f in range(1,41):
            pp=plan(c,f,1)
            families.append({'variantId':next(j['variantId'] for j in cj if j['family']==f),
                 'shapeProfile':pp['shapeProfile'],'structuralMode':pp['structuralMode'],
                 'modelCountThisBatch':sum(j['family']==f for j in cj),
                 'structuralAxes':['continuous category contour','functional part proportion/spacing'],
                 'instanceAxes':pp['changedAttributes'],'designDifferenceAudit':'measured per instance; family pairwise audit pending'})
        categories.append({'category':c,'invariantFeatures':REQUIRED[c],
            'variableFeatures':['body aspect ratios','curvature','part proportions','opening and support spacing'],
            'optionalFeatures':['attached subtype features explicitly encoded in structuralMode'],
            'forbiddenChanges':['category loss','rigid transform as independent model','color-only difference','noise or signature geometry','unrelated support'],
            'topologyConstraints':['one six neighbor component','face attachments','category-specific openings and supports'],
            'visibleSurfaceFeatures':['functional feature positions checked by air neighbors and camera rays'],
            'sampleModelCount':len(cj),'fullTaskModelCount':1900 if c=='vessel' else 1905,'families':families})
    savejson(ROOT/'design_manifest.json',{'datasetVersion':VERSION,'shardId':'A','scope':'first 10000 review batch','categories':categories})
    savejson(ROOT/'planned_models.json',jobs)

def aggregate(rows,pilot=False):
    rows=sorted(rows,key=lambda r:r['globalOrdinal']); counts=dict(Counter(x['category'] for x in rows))
    savejson(ROOT/('pilot_manifest.json' if pilot else 'manifest.json'),{'datasetVersion':VERSION,'shardId':'A',
      'modelCount':len(rows),'promptRecordCount':len(rows)*5,'categoryCounts':counts,'sampleTarget':10000,
      'fullShardTarget':40000,'trainingInputFields':['captionZh','captionEn'],'models':rows,
      'historicalCanonicalDedupStatus':'unavailable_coordinates','crossShardDedupStatus':'awaiting_merge'})
    (ROOT/'previews').mkdir(exist_ok=True);sheets(ROOT,rows)
    if pilot:return
    records=[]
    for row in rows:
        records.extend(json.loads((ROOT/row['modelJsonPath']).with_name('prompts.json').read_text(encoding='utf-8')))
    with (ROOT/'all_prompts.jsonl').open('w',encoding='utf-8') as handle:
        for rec in records:handle.write(json.dumps(rec,ensure_ascii=False,separators=(',',':'))+'\n')
    fields=list(records[0])
    with (ROOT/'all_prompts.csv').open('w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
        for rec in records:writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in rec.items()})
    with (ROOT/'dedup_index.jsonl').open('w',encoding='utf-8') as f:
        for row in rows:f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
    (ROOT/'training_subsets').mkdir(exist_ok=True)
    for category in CATEGORIES:
        for lev in range(1,6):
            with (ROOT/'training_subsets'/f'{category}_L{lev}.jsonl').open('w',encoding='utf-8') as f:
                for rec in records:
                    if rec['category']==category and rec['promptLevel']==lev:f.write(json.dumps(rec,ensure_ascii=False,separators=(',',':'))+'\n')
    with (ROOT/'retry_queue.jsonl').open('w',encoding='utf-8') as out:
        for file in sorted((ROOT/'checkpoints').glob('*_retries.jsonl')):out.write(file.read_text(encoding='utf-8'))
    savejson(ROOT/'generation_status.json',{'status':'generated_awaiting_independent_verification','completedModelCount':len(rows),
        'completedPromptRecordCount':len(records),'pendingModelCount':10000-len(rows),'fullTaskRemainingModelCount':40000-len(rows)})

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--pilot',action='store_true');parser.add_argument('--full',action='store_true');parser.add_argument('--workers',type=int,default=6)
    args=parser.parse_args();jobs=allocation();design_manifest(jobs)
    groups={c:[j for j in jobs if j['category']==c][:1 if args.pilot else 1000] for c in CATEGORIES}
    rows=[]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(category_worker,c,g,args.pilot):c for c,g in groups.items()}
        for future in as_completed(futures):
            rows+=future.result()
            print(f'CATEGORY COMPLETE {futures[future]}: accepted={len(rows)}, promptRecords={len(rows)*5}',flush=True)
    aggregate(rows,args.pilot)
    print(f'GENERATED {len(rows)} models / {len(rows)*5} prompt records',flush=True)

if __name__=='__main__':main()
