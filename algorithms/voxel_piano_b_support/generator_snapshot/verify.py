"""Independent disk readback. Recompute measurements; never trust saved true flags."""
import argparse,csv,hashlib,json,struct,time,traceback
from pathlib import Path
from collections import Counter
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np
from PIL import Image
from checks import validate,digest,canonical,DIRS
from geometry import COLORS,CATEGORIES,REQUIRED
from captions import make

ROOT=Path(__file__).resolve().parent.parent

def read_vox(path):
    data=path.read_bytes();assert data[:4]==b'VOX '
    pos=8;xyzi=None;palette=None;size=None
    while pos<len(data):
        name=data[pos:pos+4];n,ch=struct.unpack_from('<II',data,pos+4);payload=data[pos+12:pos+12+n]
        if name==b'SIZE':size=list(struct.unpack('<III',payload))
        if name==b'XYZI':xyzi=np.frombuffer(payload[4:],np.uint8).reshape(-1,4).copy();assert len(xyzi)==struct.unpack_from('<I',payload)[0]
        if name==b'RGBA':palette=np.frombuffer(payload,np.uint8).reshape(256,4)
        pos+=12+n
    assert size==[48,48,48] and xyzi is not None and palette is not None
    return xyzi[:,[0,2,1]],palette[xyzi[:,3]-1,:3]

def obj_readback(path,coords,rgb):
    vertices=[];faces=[];materials=[];active=None;mtllib=None
    for line in path.read_text(encoding='ascii').splitlines():
        a=line.split()
        if not a:continue
        if a[0]=='mtllib':mtllib=a[1]
        elif a[0]=='usemtl':active=a[1]
        elif a[0]=='v':vertices.append(tuple(float(v) for v in a[1:]))
        elif a[0]=='f':faces.append(tuple(int(v.split('/')[0])-1 for v in a[1:]));materials.append(active)
    assert mtllib=='model.mtl' and path.with_name(mtllib).exists()
    mtl={};name=None
    for line in path.with_name(mtllib).read_text().splitlines():
        a=line.split()
        if a and a[0]=='newmtl':name=a[1]
        if a and a[0]=='Kd':mtl[name]=tuple(round(float(v)*255) for v in a[1:])
    occupied={tuple(p):tuple(v) for p,v in zip(coords,rgb)}
    # Each cube surface is represented by its geometric face center and exact RGB.
    expected=set()
    for p,color in occupied.items():
        for delta in DIRS:
            if tuple(a+b for a,b in zip(p,delta)) not in occupied:
                center=tuple(2*a+1+b for a,b in zip(p,delta));expected.add((center,color))
    measured=set()
    for face,mat in zip(faces,materials):
        assert len(face)==4 and all(0<=v<len(vertices) for v in face)
        points=np.asarray([vertices[v] for v in face]);assert np.all(points==np.rint(points))
        extent=points.max(0)-points.min(0)
        assert sorted(extent.tolist())==[0.,1.,1.]
        center=tuple(np.rint(points.mean(0)*2).astype(int));measured.add((center,mtl[mat]))
    assert len(measured)==len(faces) and measured==expected
    return {'surfaceFaceCount':len(faces),'vertices':len(vertices),'exactExteriorAndMaterialsMatch':True}

def verify_model(row,recompute_hash=True):
    errors=[];path=ROOT/row['modelJsonPath'];folder=path.parent
    try:
        doc=json.loads(path.read_text(encoding='utf-8'));vox=doc['voxels']
        co=np.array([[v['x'],v['y'],v['z']] for v in vox],dtype=np.int16)
        rgb=np.array([v['color'] for v in vox],dtype=np.int16)
        assert len(co)==doc['actualVoxelCount'] and len(set(map(tuple,co)))==len(co)
        assert np.all((co>=0)&(co<48)) and np.all((rgb>=0)&(rgb<=255))
        assert all(isinstance(v[k],int) for v in vox for k in ['x','y','z'])
        n=np.load(folder/'model.npz');assert np.array_equal(co,n['coords']) and np.array_equal(rgb,n['colors'])
        occ=np.zeros((48,48,48),np.uint8);occ[tuple(co.T)]=1
        assert np.array_equal(occ,n['occupancy'])
        vc,vr=read_vox(folder/'model.vox');assert np.array_equal(co,vc) and np.array_equal(rgb,vr)
        obj=obj_readback(folder/'model.obj',co,rgb)
        with Image.open(folder/'preview.png') as im:assert im.size==(420,445);im.verify()
        p=doc['geometryPlan'].copy();e=p.pop('actualMeasurements')
        pa=['air']+list(dict.fromkeys(v['part'] for v in vox));la=np.array([pa.index(v['part']) for v in vox],dtype=np.uint8)
        from produce import part_metrics
        assert e['partMeasurements']==part_metrics(co,la,pa),'stored part measurements do not match geometry'
        assert e['boundsSize']==(co.max(0)-co.min(0)+1).tolist(),'stored bounds do not match geometry'
        v=validate(p,co,la,pa,e);assert v['passed'],v['failureReasons']
        ex=digest(co);assert ex==doc['exactOccupancyHash']==row['exactOccupancyHash']
        ch=canonical(co) if recompute_hash else doc['canonicalGeometryHash']
        assert ch==doc['canonicalGeometryHash']==row['canonicalGeometryHash']
        recs=json.loads((folder/'prompts.json').read_text(encoding='utf-8'))
        assert len(recs)==5 and [x['promptLevel'] for x in recs]==[1,2,3,4,5]
        expected=make(p,e,pa,{v['part']:next(k for k,val in COLORS.items() if tuple(v['color'])==val) for v in vox})
        for rec,exp in zip(recs,expected):
            assert rec['recordId']==row['modelId']+f"_l{rec['promptLevel']}"
            for key in ['captionZh','captionEn','voxelPromptZh','voxelPromptEn']:assert rec[key]==exp[key]
            assert rec['factGroups']==list(range(1,rec['promptLevel']+1))
            assert rec['modelId']==doc['modelId'] and rec['semanticGroupKey']==doc['modelId']
            assert rec['modelSeed']==doc['modelSeed'] and rec['variantId']==doc['variantId']
            assert rec['targetOccupancyHash']==ex and rec['targetCanonicalGeometryHash']==ch
            assert rec['modelJsonPath']==row['modelJsonPath'] and rec['modelNpzPath']==row['modelNpzPath']
        evidence={'status':'passed','jsonNpzExact':True,'voxAxisAndRgbExact':True,'objSurfaceExact':obj,
                   'previewDecoded':True,'fiveLevelPairing':True,'captionRebuiltFromMeasuredGeometry':True}
        saved=json.loads((folder/'validation.json').read_text(encoding='utf-8'))
        saved.update(v)
        saved['formatReadback']=evidence
        (folder/'validation.json').write_text(json.dumps(saved,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
        doc['validation']=v;doc['semanticFeatures']=v['semanticMeasurements']
        path.write_text(json.dumps(doc,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
        return {'modelId':row['modelId'],'category':row['category'],'count':len(co),'exact':ex,'canonical':ch,
                'recordIds':[x['recordId'] for x in recs],
                'recordDigests':[hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest() for x in recs],
                'lengths':[(len(x['captionZh']),len(x['captionEn'].split())) for x in recs],'errors':[]}
    except Exception as exc:
        errors.append(type(exc).__name__+': '+str(exc)+' '+traceback.format_exc().splitlines()[-3])
        return {'modelId':row['modelId'],'category':row['category'],'errors':errors}

def verify_group(rows):return [verify_model(row) for row in rows]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--pilot',action='store_true');parser.add_argument('--workers',type=int,default=6);args=parser.parse_args()
    manifest=json.loads((ROOT/('pilot_manifest.json' if args.pilot else 'manifest.json')).read_text(encoding='utf-8'))
    rows=manifest['models'];results=[]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        fs=[pool.submit(verify_group,rows[i:i+100]) for i in range(0,len(rows),100)]
        for f in as_completed(fs):
            results+=f.result();print(f'INDEPENDENT READBACK {len(results)}/{len(rows)}',flush=True)
    errors=[r for r in results if r['errors']]
    with (ROOT/'readback_results.jsonl').open('w',encoding='utf-8') as f:
        for r in results:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    successful=[r for r in results if not r['errors']]
    historical={json.loads(x)['exactOccupancyHash'] for x in (ROOT/'historical_models_55255.jsonl').read_text(encoding='utf-8').splitlines()}
    exacts={x['exact'] for x in successful};canons={x['canonical'] for x in successful}
    if len(exacts)!=len(rows):errors.append({'global':'exact duplicate or failed model'})
    if len(canons)!=len(rows):errors.append({'global':'canonical duplicate or failed model'})
    if exacts&historical:errors.append({'global':'historical exact overlap'})
    if not args.pilot:
        ids=set();expected_ids={v for r in successful for v in r['recordIds']}
        expected_hashes={i:h for r in successful for i,h in zip(r['recordIds'],r['recordDigests'])}
        grouped=Counter();levels=Counter();subset_hashes={(c,l):hashlib.sha256() for c in CATEGORIES for l in range(1,6)}
        record_count=0
        with (ROOT/'all_prompts.jsonl').open(encoding='utf-8') as jf,(ROOT/'all_prompts.csv').open(encoding='utf-8-sig',newline='') as cf:
            cr=csv.DictReader(cf)
            for line in jf:
                rec=json.loads(line);record_count+=1;ids.add(rec['recordId']);grouped[rec['modelId']]+=1;levels[rec['promptLevel']]+=1
                normalized=json.dumps(rec,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
                h=hashlib.sha256(normalized).hexdigest()
                if h!=expected_hashes.get(rec['recordId']):errors.append({'global':'aggregated record differs from model prompts','recordId':rec['recordId']})
                subset_hashes[(rec['category'],rec['promptLevel'])].update(normalized+b'\n')
                csvrow=next(cr,None)
                desired={k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else str(v) if v is not None else '' for k,v in rec.items()}
                if csvrow!=desired:errors.append({'global':'csv record mismatch','recordId':rec['recordId']})
            if next(cr,None) is not None:errors.append({'global':'extra csv row'})
        if ids!=expected_ids or record_count!=5*len(rows):errors.append({'global':'aggregated prompt relation'})
        if set(grouped.values())!={5} or levels!=Counter({l:40000 for l in range(1,6)}):errors.append({'global':'one to five ratio or level quota'})
        for c in CATEGORIES:
            for l in range(1,6):
                h=hashlib.sha256();count=0
                with (ROOT/'training_subsets'/f'{c}_L{l}.jsonl').open(encoding='utf-8') as sf:
                    for line in sf:
                        rec=json.loads(line);count+=1;h.update(json.dumps(rec,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()+b'\n')
                if h.digest()!=subset_hashes[(c,l)].digest() or count!=(1900 if c=='vessel' else 1905):errors.append({'global':'subset mismatch','category':c,'level':l})
        if Counter(r['category'] for r in rows)!=Counter({c:1900 if c=='vessel' else 1905 for c in CATEGORIES}):errors.append({'global':'category quota'})
        if sorted(r['globalOrdinal'] for r in rows)!=list(range(1,40001)):errors.append({'global':'ordinal quota'})
        if any(r['modelSeed']!=800000000+r['globalOrdinal'] for r in rows):errors.append({'global':'seed mapping'})
        families=Counter(r['variantId'] for r in rows)
        if any(families[f'vx80k5p_20261010_A_{c}_v{f:03d}']!=(48 if f<=(20 if c=='vessel' else 25) else 47) for c in CATEGORIES for f in range(1,41)):errors.append({'global':'family quota'})
        retained=json.loads((ROOT/'retained_first10000.json').read_text(encoding='utf-8'))['models'];byid={r['modelId']:r for r in rows}
        if any(mid not in byid or byid[mid]['exactOccupancyHash']!=r['exact'] or byid[mid]['canonicalGeometryHash']!=r['canonical'] or byid[mid]['variantId']!=r['family'] for mid,r in retained.items()):errors.append({'global':'first batch was not retained'})
    report={'passed':not errors,'scope':'complete AI_A 40000 models' if not args.pilot else '21 category pilot',
       'modelCount':len(rows),'promptRecordCount':len(rows)*5,'successfulReadbackCount':len(successful),
       'categoryCounts':dict(Counter(x['category'] for x in rows)),'perLevelRecordCount':len(rows),
       'minimumVoxelCount':min(x['count'] for x in successful),'maximumVoxelCount':max(x['count'] for x in successful),
       'uniqueExactOccupancyHashCount':len(exacts),'uniqueCanonicalGeometryHashCount':len(canons),
       'historicalIndexCount':len(historical),'historicalExactOverlap':len(exacts&historical),
       'historicalCanonicalDedupStatus':'unavailable_coordinates','crossShardDedupStatus':'awaiting_merge',
       'captionConsistencyMethod':'bilingual template facts rebuilt from disk geometry measurements and verified category features',
       'structuralReviewReport':'structural_review.json','familyDesignAuditReport':'family_design_audit.json',
       'retainedFirstBatchModelCount':10000,'newModelCount':30000,'retainedGeometryAndFamilyChecked':not args.pilot,
       'limitations':['Automatic geometry and silhouette screens do not replace visual or full semantic quality review.',
                      'Historical canonical comparison is unavailable because the provided history has hashes without coordinates.',
                      'Cross-shard A/B dedup awaits the B index. LEGO placement and physical processing have not run.'],
       'errorCount':len(errors),'errors':errors[:100]}
    dest=ROOT/('pilot_independent_verification.json' if args.pilot else 'independent_verification.json')
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='errors'},ensure_ascii=False,indent=2),flush=True)
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
