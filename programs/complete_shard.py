"""Complete AI_A while freezing the delivered first 10,000 geometries and families."""
import argparse,csv,hashlib,json,os,sqlite3,time
from collections import Counter,defaultdict
from concurrent.futures import ProcessPoolExecutor,as_completed
from contextlib import ExitStack
import numpy as np
from geometry import CATEGORIES,REQUIRED,plan,build
from checks import validate,digest,canonical
from produce import ROOT,VERSION,savejson,part_metrics,export
from repair_review import scaled_occ,featurevec
from render import sheets

POP=np.array([i.bit_count() for i in range(256)],np.uint8)
FILES=['model.json','model.npz','model.obj','model.mtl','model.vox','preview.png','validation.json','prompts.json']

def quota(c,f):return 48 if f<=(20 if c=='vessel' else 25) else 47

def allocate():
    frozen=json.loads((ROOT/'first10000_manifest.json').read_text(encoding='utf-8'))['models']
    existing={r['modelId'] for r in frozen};fc=Counter(r['variantId'] for r in frozen);jobs=[]
    for ci,c in enumerate(CATEGORIES):
        slots=[]
        # Keep reviewed families of the first batch. Fill each exact 47/48 quota.
        for instance in range(1,49):
            for f in range(1,41):
                vid=f'vx80k5p_20261010_A_{c}_v{f:03d}'
                if fc[vid]<instance<=quota(c,f):slots.append((f,instance,vid))
        missing=[n for n in range(1,(1900 if c=='vessel' else 1905)+1) if f'vx80k5p_20261010_A_{c}_m{n:04d}' not in existing]
        assert len(missing)==len(slots)
        for number,(f,instance,vid) in zip(missing,slots):
            jobs.append({'category':c,'categoryId':ci+1,'family':f,'instance':instance,'variantId':vid,
                'modelId':f'vx80k5p_20261010_A_{c}_m{number:04d}','globalOrdinal':ci*1905+number})
    assert len(jobs)==30000
    return frozen,jobs

def expanded_plan(job,revision,anchor):
    c=job['category'];p=plan(c,job['family'],job['instance'],revision)
    rng=np.random.default_rng(970000000+job['globalOrdinal']*10007+revision*7919);u=rng.random(12)
    p.update(profileVersion=2,shapeProfile=anchor['shapeProfile'],structuralMode=anchor['structuralMode'],
        widthFactor=float(.65+u[0]*.95),depthFactor=float(.65+u[1]*.95),heightFactor=float(.68+u[2]*.85),
        thickness=float(1.2+u[3]*1.25),attachmentRatio=float(.22+u[4]*.68),
        supportSpread=float(.47+u[5]*.34),spacingRatio=float(.42+u[6]*.42),
        openingRatio=float(.17+u[7]*.25),curve=float(.08+u[8]*.48),
        reviewedFamilyAnchorModelId=anchor['modelId'])
    # Category identity and analytic-world limits are constraints on proportions.
    if c=='bed':p['depthFactor']=max(p['depthFactor'],p['widthFactor']*.8)
    if c=='bench':p['depthFactor']=min(p['depthFactor'],p['widthFactor']*1.35)
    if c=='sofa':p['depthFactor']=min(p['depthFactor'],p['widthFactor']*1.3)
    if c=='chair':p['depthFactor']=float(np.clip(p['depthFactor'],p['widthFactor']*.8,p['widthFactor']*1.4))
    if c=='guitar':
        p['heightFactor']=float(.72+u[2]*.55);p['widthFactor']=float(.83+u[0]*.67)
        p['depthFactor']=float(.86+u[1]*.60)
    if c in ['bus','train']:
        p['depthFactor']=float(.76+u[1]*(.56 if c=='train' else .74))
        p['widthFactor']=min(p['widthFactor'],p['depthFactor']*1.4)
    if c=='vessel':p['depthFactor']=float(.78+u[1]*.72)
    if c in ['mug','pot']:p['heightFactor']=float(.86+u[2]*.66)
    if c=='bottle':
        p['thickness']=float(1.2+u[3]*.65)
        p['heightFactor']=max(p['heightFactor'],p['widthFactor']*.85)
    if c=='bowl':
        p['heightFactor']=float(.78+u[2]*.74)
        p['baseRadiusRatio']=float(.35+u[9]*.42)
        p['bellyExponent']=float(.6+u[10]*1.05)
    p['changedAttributes']=['actual body width/depth and height/width ratios',
        'actual required-part dimensions and relative volumes','actual attachment and support positions',
        'category continuous contour, opening or functional-part proportions']
    return p

def generate(job,revision,anchor):
    p=expanded_plan(job,revision,anchor)
    initial=len(build(p)[0]);scale=1. if 750<=initial<=1250 else (1000/initial)**(1/3)
    history=[]
    for attempt in range(1,21):
        co,la,pa,cl,e=build(p,scale);v=validate(p,co,la,pa,e)
        if e.get('samplingBoundaryTouched'):v['failureReasons'].append('analytic_geometry_clipped_at_sampling_boundary');v['passed']=False
        history.append({'attempt':attempt,'absoluteUniformScaleFromOriginal':round(scale,8),
            'voxelCount':len(co),'failureReasons':v['failureReasons']})
        if v['passed']:return p,co,la,pa,cl,e,v,history,initial
        if e.get('samplingBoundaryTouched'):scale*=.91
        elif not 750<=len(co)<=1250:scale*=np.clip((1000/max(1,len(co)))**(1/3),.8,1.25)
        else:scale*=1.045 if attempt%2 else .96
    return None,history

def descriptor(co,e):
    vol=scaled_occ(co);dims=np.array(e['boundsSize']);views=[vol.any(axis=a) for a in [2,0,1]]
    cross=np.array(list(dims/dims.max())+[vol.mean()]+[v.mean() for v in views])
    coarse=np.concatenate([dims/dims.max()]+[np.array(e['partMeasurements'][p]['size'])/dims.max() for p in REQUIRED[e['_category']]])
    pts=co-co.min(0);pts=np.rint(pts*(31/max(1,dims.max()-1))).astype(int);original=[]
    for a,b in [(0,1),(2,1),(0,2)]:
        image=np.zeros((32,32),bool);image[pts[:,a],pts[:,b]]=1;original.append(np.packbits(image))
    return cross,coarse,np.packbits(vol),np.array([np.packbits(v) for v in views]),np.array(original)

def overlaps(a,b):
    intersection=POP[np.bitwise_and(a,b)].sum();union=POP[np.bitwise_or(a,b)].sum()
    return float(intersection/union)

def document_row(doc,folder):
    row={k:doc[k] for k in ['datasetVersion','shardId','modelId','category','categoryId','variantId','geometryFamilyId',
        'semanticGroupKey','modelSeed','globalOrdinal','actualVoxelCount','exactOccupancyHash','canonicalGeometryHash']}
    p=doc['geometryPlan'].copy();p.pop('actualMeasurements');rel=folder.relative_to(ROOT).as_posix()
    return row|dict(modelJsonPath=rel+'/model.json',modelNpzPath=rel+'/model.npz',previewPath=rel+'/preview.png',
        geometryPlan=p,designSignature=hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest())

def category_worker(category,jobs):
    from verify import verify_model
    frozen=json.loads((ROOT/'first10000_manifest.json').read_text(encoding='utf-8'))['models']
    rows=[r for r in frozen if r['category']==category]
    design=json.loads((ROOT/'design_manifest.json').read_text(encoding='utf-8'))
    families=next(c['families'] for c in design['categories'] if c['category']==category)
    anchors={int(f['variantId'][-3:]):dict(f['anchorGeometryPlan'],modelId=f['anchorModelId']) for f in families}
    historic={json.loads(x)['exactOccupancyHash'] for x in (ROOT/'historical_models_55255.jsonl').read_text(encoding='utf-8').splitlines()}
    connection=sqlite3.connect(ROOT/'checkpoints'/'dedup_registry.sqlite',timeout=120)
    familyvec=defaultdict(list);descs=[];coarse=[];volumes=[];views=[];original=[]
    def register(doc,co):
        e=doc['geometryPlan']['actualMeasurements'];e['_category']=category
        fam=int(doc['variantId'][-3:]);familyvec[fam].append(featurevec(doc))
        cr,cs,vo,vi,ori=descriptor(co,e);descs.append(cr);coarse.append(cs);volumes.append(vo);views.append(vi);original.append(ori)
        e.pop('_category',None)
    for row in rows:
        doc=json.loads((ROOT/row['modelJsonPath']).read_text(encoding='utf-8'));co=np.array([[v['x'],v['y'],v['z']] for v in doc['voxels']]);register(doc,co)
    retries_path=ROOT/'checkpoints'/f'{category}_retries.jsonl';retrycounts=Counter();newrows=[];readback=[]
    def retry(handle,job,rev,reason,history=None):
        retrycounts[reason]+=1
        entry={'modelId':job['modelId'],'revision':rev,'reason':reason,'status':'replanned_preserving_quota'}
        if history is not None:entry['resamplingHistory']=history
        handle.write(json.dumps(entry,ensure_ascii=False,separators=(',',':'))+'\n')
    with retries_path.open('a',encoding='utf-8',buffering=1) as retryhandle:
        for index,job in enumerate(jobs,1):
            folder=ROOT/'models'/category/job['modelId'];resumed=False
            if all((folder/name).exists() for name in FILES):
                doc=json.loads((folder/'model.json').read_text(encoding='utf-8'))
                co=np.array([[v['x'],v['y'],v['z']] for v in doc['voxels']]);row=document_row(doc,folder);register(doc,co);resumed=True
            else:
                connection.execute('DELETE FROM models WHERE modelId=?',(job['modelId'],));connection.commit()
                for revision in range(2000):
                    result=generate(job,revision,anchors[job['family']])
                    if result[0] is None:retry(retryhandle,job,revision,'semantic_or_density',result[1]);continue
                    p,co,la,pa,cl,e,v,history,initial=result;e['partMeasurements']=part_metrics(co,la,pa)
                    minimal={'category':category,'geometryPlan':{'actualMeasurements':e},'actualVoxelCount':len(co),'validation':v}
                    fv=featurevec(minimal);old=np.array(familyvec[job['family']])
                    if len(old) and np.any((np.abs(old-fv)>=.025).sum(1)<2):
                        retry(retryhandle,job,revision,'fewer_than_two_observable_category_changes');continue
                    ex=digest(co)
                    if ex in historic:retry(retryhandle,job,revision,'historical_exact_duplicate');continue
                    e['_category']=category;cr,cs,vo,vi,ori=descriptor(co,e);e.pop('_category')
                    dd=np.array(descs);cc=np.array(coarse)
                    candidates=np.flatnonzero((np.abs(dd-cr).max(1)<=.055)|(np.abs(cc-cs).max(1)<.055))
                    near=False
                    for j in candidates:
                        if overlaps(vo,volumes[j])<.975:continue
                        if min(overlaps(a,b) for a,b in zip(vi,views[j]))>=.985 or min(overlaps(a,b) for a,b in zip(ori,original[j]))>=.985:
                            near=True;break
                    if near:retry(retryhandle,job,revision,'normalized_geometry_near_duplicate');continue
                    ch=canonical(co)
                    try:
                        connection.execute('INSERT INTO models VALUES(?,?,?)',(job['modelId'],ex,ch));connection.commit()
                    except sqlite3.IntegrityError:
                        connection.rollback();retry(retryhandle,job,revision,'global_exact_or_canonical_duplicate');continue
                    e['nearDuplicateAudit']={'normalizedVolumeRejectThreshold':.975,'minimumThreeSilhouetteRejectThreshold':.985,
                        'measuredWithinFamilyAttributeThreshold':.025,'requiredChangedAttributes':2,'scope':'retained_and_new_category_models'}
                    row=export(job,result,ex,ch,revision+1)
                    doc={'category':category,'variantId':job['variantId'],'geometryPlan':{'actualMeasurements':e},'actualVoxelCount':len(co),'validation':v}
                    register(doc,co);break
                else:raise RuntimeError(f'{category} could not complete {job["modelId"]}; quota retained in retry queue')
            rows.append(row);newrows.append(row)
            if not resumed:readback.append(row)
            if index%25==0 or index==len(jobs):
                savejson(ROOT/'checkpoints'/f'{category}.json',{'completed':len(rows),'remainingNewJobs':len(jobs)-index,
                    'target':1900 if category=='vessel' else 1905,'models':rows,'retryCounts':dict(retrycounts)})
                print(f'{category}: retained={len(rows)-index}, new={index}/{len(jobs)}, retries={sum(retrycounts.values())}',flush=True)
            if len(readback)>=250 or index==len(jobs):
                evidence=[verify_model(r) for r in readback];failed=[r for r in evidence if r['errors']]
                assert not failed,failed[:3]
                with (ROOT/'checkpoints'/f'{category}_independent_readback.jsonl').open('a',encoding='utf-8') as handle:
                    for r in evidence:handle.write(json.dumps(r,ensure_ascii=False)+'\n')
                readback.clear()
    connection.close();return rows

def aggregate(rows):
    rows=sorted(rows,key=lambda r:r['globalOrdinal']);assert len(rows)==40000
    counts=dict(Counter(x['category'] for x in rows))
    savejson(ROOT/'manifest.json',{'datasetVersion':VERSION,'shardId':'A','modelCount':len(rows),'promptRecordCount':len(rows)*5,
        'categoryCounts':counts,'fullShardTarget':40000,'trainingInputFields':['captionZh','captionEn'],'models':rows,
        'historicalCanonicalDedupStatus':'unavailable_coordinates','crossShardDedupStatus':'awaiting_merge'})
    (ROOT/'training_subsets').mkdir(exist_ok=True);(ROOT/'previews').mkdir(exist_ok=True)
    with ExitStack() as stack:
        alljson=stack.enter_context((ROOT/'all_prompts.jsonl').open('w',encoding='utf-8'))
        allcsv=stack.enter_context((ROOT/'all_prompts.csv').open('w',encoding='utf-8-sig',newline=''))
        dedup=stack.enter_context((ROOT/'dedup_index.jsonl').open('w',encoding='utf-8'))
        subsets={(c,l):stack.enter_context((ROOT/'training_subsets'/f'{c}_L{l}.jsonl').open('w',encoding='utf-8')) for c in CATEGORIES for l in range(1,6)}
        writer=None
        for row in rows:
            recs=json.loads((ROOT/row['modelJsonPath']).with_name('prompts.json').read_text(encoding='utf-8'))
            if writer is None:writer=csv.DictWriter(allcsv,fieldnames=list(recs[0]));writer.writeheader()
            dedup.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
            for rec in recs:
                line=json.dumps(rec,ensure_ascii=False,separators=(',',':'))+'\n';alljson.write(line);subsets[(rec['category'],rec['promptLevel'])].write(line)
                writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in rec.items()})
    design=json.loads((ROOT/'design_manifest.json').read_text(encoding='utf-8'));design['scope']='complete AI_A 40000 models'
    for c in design['categories']:
        c['modelCount']=counts[c['category']];c['retainedFirstBatchCount']=477 if CATEGORIES.index(c['category'])<4 else 476
        for f in c['families']:f['fullTaskModelCount']=quota(c['category'],int(f['variantId'][-3:]));f['modelCountThisBatch']=f['fullTaskModelCount']
        c['continuationDesignPolicy']='Retain first-batch anchor geometry and reviewed families; broaden actual category proportions, wall curvature and functional attachment positions; verify every new member differs from all retained/new members on at least two observable attributes.'
    savejson(ROOT/'design_manifest.json',design)
    with (ROOT/'retry_queue.jsonl').open('w',encoding='utf-8') as out:
        for path in sorted((ROOT/'checkpoints').glob('*_retries.jsonl')):
            with path.open(encoding='utf-8') as handle:
                for line in handle:out.write(line)
    sheets(ROOT,rows)
    savejson(ROOT/'generation_status.json',{'status':'generated_awaiting_full_independent_verification','completedModelCount':40000,
        'completedPromptRecordCount':200000,'retainedFirstBatchModelCount':10000,'newModelCount':30000,'pendingModelCount':0})

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=12);parser.add_argument('--aggregate-only',action='store_true');args=parser.parse_args()
    frozen,jobs=allocate();savejson(ROOT/'planned_remaining_models.json',jobs)
    (ROOT/'checkpoints').mkdir(exist_ok=True)
    conn=sqlite3.connect(ROOT/'checkpoints'/'dedup_registry.sqlite');conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('CREATE TABLE IF NOT EXISTS models(modelId TEXT PRIMARY KEY, exact TEXT UNIQUE, canonical TEXT UNIQUE)')
    conn.executemany('INSERT OR IGNORE INTO models VALUES(?,?,?)',[(r['modelId'],r['exactOccupancyHash'],r['canonicalGeometryHash']) for r in frozen]);conn.commit();conn.close()
    rows=[]
    if args.aggregate_only:
        for c in CATEGORIES:rows+=json.loads((ROOT/'checkpoints'/f'{c}.json').read_text(encoding='utf-8'))['models']
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            fs={pool.submit(category_worker,c,[j for j in jobs if j['category']==c]):c for c in CATEGORIES}
            for future in as_completed(fs):
                rows+=future.result();print('CATEGORY COMPLETE',fs[future],'accepted categories total',len(rows),flush=True)
    aggregate(rows);print('FULL SHARD GENERATED',len(rows),'models',len(rows)*5,'records',flush=True)

if __name__=='__main__':main()
