"""Regenerate B uprights with a measured two-layer keybed; exact LEGO only."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor,as_completed
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import time
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import pipeline
import strict_core
sys.path.insert(0,str(HERE/'generator_snapshot'))
import geometry
import captions
import produce
import verify as readback
from checks import validate,digest,canonical

ROOT=Path(r'D:\brickgpt10-1\outputs\piano_B_supported_20261014')
OLD=Path(r'D:\brickgpt10-1\outputs\retile_80000_20261013')
REPO=HERE.parents[1]
VERSION='voxel_piano_B_supported_keyboard_20261014_v1'
captions.BASE['piano']=(
 '立式钢琴有连续黑白键盘、完整琴体和四个承重脚',
 'An upright piano with a continuous black and white keyboard, a complete cabinet and four supporting legs.',
 '每个琴键下方都有至少两层连续键床，键床接入琴体承重框；黑白键仅占键床上表面，四脚各自接地',
 'Every key rests on at least two continuous keybed layers joined to the cabinet frame; black and white keys occupy its exposed top surface, and all four legs reach the ground.')
captions.TECH_ZH+='琴键下方必须有至少两层连续实心底托，底托在原始模型内与琴体面连接；琴键黑白分区必须俯视可见，不允许悬空琴键、外露补撑或为拼接临时加杆。'
captions.TECH_EN+=' Each key must have at least two solid continuous supporting layers in the original geometry, face-connected to the cabinet frame. Both key colors must be exposed from above. Do not use unsupported keys, exterior repair props or temporary connecting rods.'
produce.ROOT=ROOT;produce.VERSION=VERSION;readback.ROOT=ROOT

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def dump(path,value):produce.savejson(path,value)

def build(number,attempt):
    rng=np.random.default_rng(202610140000+number*1009+attempt*7919)
    W=int(rng.integers(16,24));D=int(rng.integers(5,9));P=int(rng.integers(3,6));L=int(rng.integers(3,6));H=int(rng.integers(6,13))
    foot=int(rng.integers(2,4));inset=int(rng.integers(0,3));wall=int(rng.integers(1,3));chamfer=int(rng.integers(0,3))
    Z=D+P;top=L+2;musicW=int(rng.integers(max(4,W//3),max(5,2*W//3)));musicH=int(rng.integers(2,4))
    labels=np.zeros((W,top+H+2,Z),np.uint8)
    parts=['air','case','leg','keyboard','key','black_key','music_rest']
    colors={'case':'black','leg':'wood','keyboard':'wood','key':'white','black_key':'black','music_rest':'black'}
    # The full keybed is original piano structure, not an after-the-fact prop.
    labels[:,L:L+2,:]=parts.index('keyboard')
    for x in (inset,W-foot-inset):
        for z in (inset,Z-foot-inset):labels[x:x+foot,:L,z:z+foot]=parts.index('leg')
    labels[:wall,top:top+H,:D]=1;labels[-wall:,top:top+H,:D]=1
    labels[:,top:top+H,:wall]=1;labels[:,top:top+H,D-wall:D]=1
    labels[:,top+H-wall:top+H,:D]=1
    # Planned symmetric upper chamfers vary cabinet silhouette without cell noise.
    for offset in range(chamfer):
        labels[:chamfer-offset,top+H-1-offset,:D]=0
        labels[W-chamfer+offset:,top+H-1-offset,:D]=0
    labels[1:W-1,top,D:]=parts.index('key')
    phase=int(rng.integers(0,7))
    for x in range(1,W-1):
        if (x+phase)%7 in (1,2,4,5,6):labels[x,top,D:D+min(2,P-1)]=parts.index('black_key')
    left=(W-musicW)//2;labels[left:left+musicW,top+1:top+1+musicH,D-1]=parts.index('music_rest')
    coords=np.argwhere(labels>0).astype(np.int16);labs=labels[tuple(coords.T)]
    shift=np.array([(48-W)//2,0,(48-Z)//2],dtype=np.int16);coords+=shift
    p=dict(category='piano',family=(number-1)%40+1,shapeProfile=chamfer,structuralMode=(number-1)%5,
           designRevision=attempt,subtype='连续双层键床立式钢琴',seed=202610140000+number*1009+attempt*7919,
           bodyWidth=W,cabinetDepth=D,keyboardProjection=P,legHeight=L,cabinetHeight=H,
           supportThickness=foot,supportInset=inset,wallThickness=wall,upperChamfer=chamfer,
           musicRestWidth=musicW,musicRestHeight=musicH,blackKeyPatternPhase=phase,minimumKeybedLayers=2,
           changedAttributes=['cabinet width/depth/height','four-leg cross section and inset','keyboard projection','upper cabinet chamfers','music rest dimensions','black-key group phase'])
    e=dict(legCount=4,bodyWidth=W,bodyDepth=Z,bodyHeight=top+H,boundsSize=(coords.max(0)-coords.min(0)+1).tolist(),
           worldToGrid=dict(scale=1.,offset=shift.tolist()),samplingBoundaryTouched=False)
    result=validate(p,coords,labs,parts,e)
    cells={tuple(map(int,c)):parts[int(l)] for c,l in zip(coords,labs)}
    keys=[c for c in cells if cells[c] in ('key','black_key')]
    supported=bool(keys) and all(cells.get((x,y-1,z))=='keyboard' and cells.get((x,y-2,z))=='keyboard' for x,y,z in keys)
    visible=all((x,y+1,z) not in cells for x,y,z in keys)
    exposedKinds={f['featureId'] for f in result['surfaceFeatures'] if f['connectedToOwner'] and f['rayClear'].get('top')}
    extra=dict(keyVoxelCount=len(keys),minimumContinuousSupportingLayers=2,allKeysHaveTwoSolidOwnerLayers=supported,
               allKeysTopFacesExposed=visible,bothKeyColorsVisible={'key','black_key'}<=exposedKinds)
    extra['passed']=all(extra[k] for k in ('allKeysHaveTwoSolidOwnerLayers','allKeysTopFacesExposed','bothKeyColorsVisible'))
    e['keyboardSupportAudit']=extra
    if not extra['passed']:result['passed']=False;result['failureReasons'].append('keyboard_support_or_exposure')
    return p,coords,labs,parts,colors,e,result,[],len(coords)

def worker(number):
    mid=f'vx80k5p_20261010_B_piano_m{number:04d}'
    folder=ROOT/'models/piano'/mid;out=ROOT/'results/B/piano'/mid;checkpoint=ROOT/'checkpoints'/f'{mid}.json'
    if checkpoint.exists():
        row=json.loads(checkpoint.read_bytes());report=pipeline.verify(out)
        if sha(folder/'model.json')!=row['sourceFileSha256'] or report['sourceFileSha256']!=row['sourceFileSha256']:raise ValueError('Resume source changed')
        return row
    forbidden=json.loads((ROOT/'forbidden_geometry_hashes.json').read_bytes());history=[]
    registry=sqlite3.connect(ROOT/'geometry_registry.sqlite',timeout=60)
    existing=registry.execute('SELECT attempt FROM geometries WHERE modelId=?',(mid,)).fetchone()
    for attempt in ([existing[0]] if existing else range(100)):
        result=build(number,attempt)
        p,coords,labs,parts,colors,e,validation,_,initial=result
        if not validation['passed']:continue
        exact=digest(coords);canon=canonical(coords)
        if exact in forbidden['exact'] or canon in forbidden['canonical']:continue
        original={(int(c[0]),int(c[2]),int(c[1])):int.from_bytes(bytes(geometry.COLORS[colors[parts[int(l)]]]),'big') for c,l in zip(coords,labs)}
        selected=strict_core.optimize(original,8.)
        if not strict_core.retile.base.audit(selected['bricks'],original)['passed']:
            history.append(dict(attempt=attempt,reason='zero_change_assembly_not_found'));continue
        if not existing:
            try:
                registry.execute('INSERT INTO geometries VALUES(?,?,?,?)',(mid,exact,canon,attempt));registry.commit()
            except sqlite3.IntegrityError:
                registry.rollback();history.append(dict(attempt=attempt,reason='duplicate_new_geometry'));continue
        job=dict(category='piano',categoryId=15,family=p['family'],instance=number,modelId=mid,
                 globalOrdinal=40000+14*1905+number,variantId=f'vx80k5p_20261010_B_piano_v{p["family"]:03d}')
        row=produce.export(job,result,exact,canon,history)
        doc=json.loads((folder/'model.json').read_bytes());records=json.loads((folder/'prompts.json').read_bytes())
        doc.update(shardId='B',modelSeed=p['seed'],keyboardSupportAudit=e['keyboardSupportAudit'],
                   promptTemplateSource='AI_A five-level caption format, revised B upright with a two-layer keybed',
                   supersedes=dict(datasetRelease='lego-retile-ab-80000-20261013-v1',modelId=mid))
        row.update(shardId='B',modelSeed=p['seed'])
        for record in records:record.update(shardId='B',modelSeed=p['seed'])
        dump(folder/'model.json',doc);dump(folder/'prompts.json',records)
        checked=readback.verify_model(row)
        if checked['errors']:raise ValueError(checked['errors'])
        report=pipeline.run_one(folder/'model.json',out,8.,5.,selected)
        pipeline.verify(out)
        if any(report['repairAudit'][k] for k in ('addedVoxelCount','removedVoxelCount','recoloredOriginalVoxelCount')):raise ValueError('Assembly changed regenerated appearance')
        old=json.loads((OLD/'results/B/piano'/mid/'report.json').read_bytes())
        row.update(sourceFileSha256=sha(folder/'model.json'),promptFileSha256=sha(folder/'prompts.json'),
                   geometryPassed=report['geometryValidation']['passed'],oldGeometryPassed=old['geometryValidation']['passed'],
                   baselinePassed=False,retainedBaseline=False,originalVoxelCount=len(coords),addedVoxelCount=0,removedVoxelCount=0,
                   recoloredOriginalVoxelCount=0,changeRatio=0.,brickCount=report['geometryValidation']['brickCount'],
                   physicsStatus=report['physics']['status'],finalGravityEquilibriumPassed=report['physics']['gravityEquilibriumPassed'],
                   qualityScreenedSuccess=report['qualityScreenedSuccess'],keyboardSupportAudit=e['keyboardSupportAudit'],
                   reportRelativePath=(out/'report.json').relative_to(ROOT).as_posix(),reportSha256=sha(out/'report.json'),
                   sourceMode='regenerated_B_keyboard_support_20261014',freshSearchAttempted=True,freshGeometryPassed=True)
        dump(checkpoint,row);return row
    raise ValueError('No semantically valid exact-assembly design within 100 plans: '+mid)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--count',type=int,default=1905);parser.add_argument('--workers',type=int,default=12);args=parser.parse_args()
    if not 1<=args.count<=1905:parser.error('count must be between 1 and 1905')
    for name in ('models','results','checkpoints','source_snapshot'):(ROOT/name).mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(ROOT/'geometry_registry.sqlite') as connection:
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('CREATE TABLE IF NOT EXISTS geometries(modelId TEXT PRIMARY KEY, exact TEXT UNIQUE, canonical TEXT UNIQUE, attempt INTEGER NOT NULL)')
    path=ROOT/'forbidden_geometry_hashes.json'
    if not path.exists():
        records=[json.loads(line) for line in (REPO/'datasets/model_index.jsonl').read_text(encoding='utf-8').splitlines()]
        dump(path,dict(exact=[r['exactOccupancyHash'] for r in records],canonical=[r['canonicalGeometryHash'] for r in records]))
    runtime=pipeline.code_hashes();dump(ROOT/'run_plan.json',dict(datasetVersion=VERSION,scope='Regenerate and exactly assemble only all 1905 B pianos; other 78095 models untouched',
          sourceCodeSha256=runtime,workers=args.workers,searchSeconds=8.,physicsSeconds=5.,minimumKeybedLayers=2,addedRemovedRecoloredVoxelBudget=0))
    for relative,expected in runtime.items():
        target=ROOT/'source_snapshot'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(REPO/relative,target)
        if sha(target)!=expected:raise ValueError('Runtime snapshot differs')
    rows=[];started=time.monotonic()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        jobs=[pool.submit(worker,n) for n in range(1,args.count+1)]
        for future in as_completed(jobs):
            rows.append(future.result())
            if len(rows)%25==0 or len(rows)==args.count:
                progress=dict(requestedModelCount=args.count,completedModelCount=len(rows),geometryPassed=sum(r['geometryPassed'] for r in rows),
                              allSelectedAssembliesHaveZeroVoxelChanges=True,elapsedSeconds=time.monotonic()-started)
                dump(ROOT/'progress.json',progress);print(json.dumps(progress),flush=True)
    rows.sort(key=lambda r:r['modelId'])
    if len({r['exactOccupancyHash'] for r in rows})!=len(rows) or len({r['canonicalGeometryHash'] for r in rows})!=len(rows):raise ValueError('New geometry duplicates: regenerate conflicts before delivery')
    (ROOT/'assembly_index.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
    (ROOT/'all_prompts.jsonl').write_text(''.join(json.dumps(p,ensure_ascii=False)+'\n' for r in rows for p in json.loads((ROOT/'models/piano'/r['modelId']/'prompts.json').read_bytes())),encoding='utf-8')
    summary=dict(datasetVersion=VERSION,requestedModelCount=1905,completedModelCount=len(rows),complete=len(rows)==1905,
                 geometryPassed=sum(r['geometryPassed'] for r in rows),geometryFailed=sum(not r['geometryPassed'] for r in rows),
                 promptRecordCount=len(rows)*5,allKeybedsHaveTwoContinuousLayers=True,allKeysExposedAndBothColorsVisible=True,
                 originalToAssemblyAddedVoxelCount=0,originalToAssemblyRemovedVoxelCount=0,originalToAssemblyRecoloredVoxelCount=0,
                 oldPianoBGeometryReused=False,allOriginalFormatsAndActualJsonTxtLdrVerified=True,allNewExactAndCanonicalGeometryHashesUnique=True,
                 noNewGeometryDuplicatesOriginal80000=True,physicsStatusCounts=dict(Counter(r['physicsStatus'] for r in rows)),
                 finalGravityEquilibriumPassed=sum(r['finalGravityEquilibriumPassed'] for r in rows),qualityScreenedSuccess=sum(r['qualityScreenedSuccess'] for r in rows),
                 gridSize=[48,48,48],fullPhysics=False,staticVerified=None,elapsedSeconds=time.monotonic()-started)
    dump(ROOT/'summary.json',summary);print('REGENERATED B PIANOS READY',json.dumps(summary),flush=True)

if __name__=='__main__':main()
