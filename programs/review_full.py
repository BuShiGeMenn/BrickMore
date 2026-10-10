"""Bounded-memory whole-shard structural and family review, using saved geometry."""
import argparse,json
from collections import defaultdict,Counter
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np
from scipy.spatial import cKDTree
from produce import ROOT,savejson,part_metrics
from geometry import CATEGORIES,REQUIRED
from repair_review import scaled_occ,featurevec

POP=np.array([i.bit_count() for i in range(256)],np.uint8)
def iou(a,b):return float(POP[np.bitwise_and(a,b)].sum()/POP[np.bitwise_or(a,b)].sum())

def measured(row):
    doc=json.loads((ROOT/row['modelJsonPath']).read_text(encoding='utf-8'))
    co=np.array([[v['x'],v['y'],v['z']] for v in doc['voxels']],np.int16)
    parts=list(dict.fromkeys(v['part'] for v in doc['voxels']));labels=np.array([parts.index(v['part']) for v in doc['voxels']])
    e=doc['geometryPlan']['actualMeasurements'];e['boundsSize']=(co.max(0)-co.min(0)+1).tolist();e['partMeasurements']=part_metrics(co,labels,parts)
    doc['validation']['coordinateBounds']=co.min(0).tolist()+co.max(0).tolist()
    return doc,co,e

def category_review(category,rows,design):
    features=[];views=[];volumes=[];familyvecs=defaultdict(list);byid={}
    for row in rows:
        doc,co,e=measured(row);dims=np.array(e['boundsSize']);mx=dims.max()
        features.append(np.concatenate([dims/mx]+[np.array(e['partMeasurements'][p]['size'])/mx for p in REQUIRED[category]]))
        vec=featurevec(doc);familyvecs[row['variantId']].append(vec);byid[row['modelId']]=vec
        pts=np.rint((co-co.min(0))*(31/max(1,mx-1))).astype(int);sil=[]
        for a,b in [(0,1),(2,1),(0,2)]:
            v=np.zeros((32,32),bool);v[pts[:,a],pts[:,b]]=1;sil.append(np.packbits(v))
        views.append(sil);volumes.append(np.packbits(scaled_occ(co)))
    feats=np.array(features);tree=cKDTree(feats);closest=0.;flagged=[];tested=0
    for i in range(len(rows)):
        for j in tree.query_ball_point(feats[i],.055,p=np.inf):
            if j<=i or np.abs(feats[i]-feats[j]).max()>=.055:continue
            tested+=1;score=min(iou(a,b) for a,b in zip(views[i],views[j]));closest=max(closest,score)
            if score<.985:continue
            vi=iou(volumes[i],volumes[j])
            if vi>=.975:flagged.append({'modelA':rows[i]['modelId'],'modelB':rows[j]['modelId'],
                'minimumThreeViewIoU':score,'normalizedVolumeIoU':vi,'maximumNormalizedPartDimensionDifference':float(np.abs(feats[i]-feats[j]).max())})
    weak=[];within=0;minimum=100000
    anchors={f['variantId']:byid[f['anchorModelId']] for f in design['families']};keys=sorted(anchors)
    for i,a in enumerate(keys):
        for b in keys[i+1:]:
            n=int((np.abs(anchors[a]-anchors[b])>=.025).sum());minimum=min(minimum,n)
            if n<2:weak.append({'familyA':a,'familyB':b,'changedMeasuredAttributeCount':n})
    for members in familyvecs.values():
        array=np.array(members)
        for i in range(len(array)):within+=int(np.count_nonzero((np.abs(array[i+1:]-array[i])>=.025).sum(1)<2))
    if within:weak.append({'category':category,'withinFamilyWeakPairCount':within})
    report={'category':category,'modelCount':len(rows),'allPairCount':len(rows)*(len(rows)-1)//2,
        'proportionCandidatePairCount':tested,'nearDuplicateCandidateCount':len(flagged),
        'maximumScreenedMinimumThreeViewIoU':closest,'familyPairCount':780,'minimumChangedAnchorAttributeCount':minimum,
        'familyPairsWithFewerThanTwoAttributeDifferences':len(weak)-(1 if within else 0),
        'withinFamilyPairsWithFewerThanTwoAttributeDifferences':within,'familyCount':len(familyvecs),
        'familyModelCounts':{k:len(v) for k,v in familyvecs.items()}}
    return report,flagged,weak

def cross_review(rows):
    feats=[];volumes=[];views=[]
    for i,row in enumerate(rows):
        doc,co,e=measured(row);vol=scaled_occ(co);dims=np.array(e['boundsSize']);sil=[vol.any(axis=a) for a in [2,0,1]]
        feats.append(list(dims/dims.max())+[vol.mean()]+[v.mean() for v in sil]);volumes.append(np.packbits(vol));views.append([np.packbits(v) for v in sil])
        if (i+1)%2000==0:print('CROSS DESCRIPTORS',i+1,'/',len(rows),flush=True)
    feats=np.array(feats);tree=cKDTree(feats);flags=[];tested=0
    # Query one point at a time, avoiding the unbounded all-pairs Python set.
    for i in range(len(rows)):
        for j in tree.query_ball_point(feats[i],.055,p=np.inf):
            if j<=i or rows[i]['category']==rows[j]['category']:continue
            tested+=1;score=min(iou(a,b) for a,b in zip(views[i],views[j]))
            if score<.985:continue
            vi=iou(volumes[i],volumes[j])
            if vi>=.975:flags.append({'modelA':rows[i]['modelId'],'modelB':rows[j]['modelId'],
                'categoryA':rows[i]['category'],'categoryB':rows[j]['category'],'minimumThreeViewIoU':score,'normalizedVolumeIoU':vi})
        if (i+1)%5000==0:print('CROSS PAIRS',i+1,'/',len(rows),'screened',tested,'flags',len(flags),flush=True)
    report={'modelCount':len(rows),'screenedDescriptorPairCount':tested,'candidateCount':len(flags),'candidates':flags,
        'method':'All categories in one Chebyshev descriptor-radius index; uniformly normalized aspect, volume and three silhouette areas. All close cross-category pairs receive full three-view and volume IoU checks.',
        'thresholds':{'descriptorRadius':.055,'minimumThreeViewIoU':.985,'volumeIoU':.975},'passed':not flags}
    savejson(ROOT/'cross_category_structural_review.json',report);return flags

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=10);parser.add_argument('--cross-only',action='store_true');args=parser.parse_args()
    rows=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))['models']
    if not args.cross_only:
        design=json.loads((ROOT/'design_manifest.json').read_text(encoding='utf-8'));results=[];flags=[];weak=[]
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures={pool.submit(category_review,c,[r for r in rows if r['category']==c],next(x for x in design['categories'] if x['category']==c)):c for c in CATEGORIES}
            for future in as_completed(futures):
                r,f,w=future.result();results.append(r);flags+=f;weak+=w;print('CATEGORY STRUCTURAL REVIEW',futures[future],'near',len(f),'weak',len(w),flush=True)
        results.sort(key=lambda r:CATEGORIES.index(r['category']))
        report={'modelCount':len(rows),'method':'All within-category pairs screened on measured normalized body and required-part dimensions; close pairs compared on three uniformly normalized silhouettes and complete occupancy.',
            'normalization':'one common linear scale on XYZ; preserves aspect ratios and cavities',
            'candidateThresholds':{'partDimensionDelta':.055,'minimumThreeViewIoU':.985,'uniformlyNormalizedVolumeIoU':.975},
            'nearDuplicateCandidateCount':len(flags),'nearDuplicateCandidates':flags,'familyReviewPairCount':len(weak),'familyReviewPairs':weak,
            'familyAuditMethod':'All 780 actual anchor pairs per category and all within-family member pairs; at least two actual required-part dimensions, relative volumes or positions differ by .025.',
            'categoryResults':results,'status':'review_required' if flags or weak else 'screens_passed',
            'limitations':'Automatic screens cannot replace aesthetic or comprehensive human semantic review.'}
        savejson(ROOT/'structural_review.json',report)
        savejson(ROOT/'family_design_audit.json',{'passed':not weak,'modelCount':len(rows),'totalFamilyCount':840,
            'method':report['familyAuditMethod'],'categories':results})
    flags=cross_review(rows)
    if flags:
        report=json.loads((ROOT/'structural_review.json').read_text(encoding='utf-8'))
        report['nearDuplicateCandidates']+=flags;report['nearDuplicateCandidateCount']=len(report['nearDuplicateCandidates']);report['status']='review_required';savejson(ROOT/'structural_review.json',report)
    print('STRUCTURAL REVIEW FINISHED',flush=True)

if __name__=='__main__':main()
