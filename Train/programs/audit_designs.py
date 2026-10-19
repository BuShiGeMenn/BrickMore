"""Measured structural review: all within-category pairs and all family pairs.
These evidence screens are explicit; no claim of aesthetic or human semantic certification.
"""
import json
from pathlib import Path
from collections import defaultdict
import numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import affine_transform
from geometry import CATEGORIES,REQUIRED
from repair_review import featurevec

ROOT=Path(__file__).resolve().parent.parent

def main():
    m=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'));results=[];review=[];family_review=[]
    design=json.loads((ROOT/'design_manifest.json').read_text(encoding='utf-8'))
    for category in CATEGORIES:
        rows=[r for r in m['models'] if r['category']==category];features=[];surfaces=[];volumes=[];families=defaultdict(list)
        for row in rows:
            doc=json.loads((ROOT/row['modelJsonPath']).read_text(encoding='utf-8'));e=doc['geometryPlan']['actualMeasurements'];pm=e['partMeasurements']
            vec=[]
            dims=np.array(e['boundsSize'],float);maxdim=dims.max()
            vec.extend((dims/maxdim).tolist())
            for part in REQUIRED[category]:vec.extend((np.array(pm[part]['size'])/maxdim).tolist())
            features.append(vec);families[row['variantId']].append(featurevec(doc))
            co=np.array([[v['x'],v['y'],v['z']] for v in doc['voxels']]);co=co-co.min(0)
            dims3=co.max(0)+1;ss=30/max(dims3);off=(32-dims3*ss)/2
            occ=np.zeros(tuple(dims3),np.uint8);occ[tuple(co.T)]=1
            volumes.append(affine_transform(occ,np.eye(3)/ss,offset=-off/ss,output_shape=(32,32,32),order=0,prefilter=False).astype(bool))
            # Three orthographic silhouettes normalized by a SINGLE linear scale.
            co=np.rint(co*(31/max(1,maxdim-1))).astype(int)
            views=[]
            for axes in [(0,1),(2,1),(0,2)]:
                pts={(p[axes[0]],p[axes[1]]) for p in co};views.append(pts)
            surfaces.append(views)
        feats=np.array(features);pair_count=0;closest=0.;flagged=[]
        # All pairs are screened on normalized main and category part proportions.
        # Expensive silhouette comparison is only needed when every part ratio is close.
        for i in range(len(rows)):
            delta=np.abs(feats[i+1:]-feats[i]); candidates=np.flatnonzero((delta.max(1)<.055))
            pair_count+=len(rows)-i-1
            for jj in candidates:
                j=i+1+int(jj);scores=[]
                for a,b in zip(surfaces[i],surfaces[j]):scores.append(len(a&b)/len(a|b))
                score=min(scores);closest=max(closest,score)
                volume_iou=np.count_nonzero(volumes[i]&volumes[j])/np.count_nonzero(volumes[i]|volumes[j]) if score>=.985 else 0
                if score>=.985 and volume_iou>=.975:
                    flagged.append({'modelA':rows[i]['modelId'],'modelB':rows[j]['modelId'],'minimumThreeViewIoU':score,
                                    'normalizedVolumeIoU':volume_iou,
                                    'maximumNormalizedPartDimensionDifference':float(delta[jj].max())})
        # Family descriptions are reviewed by actual representative part proportions.
        reviewed=next(x for x in design['categories'] if x['category']==category)
        means={x['variantId']:np.array(x['measuredAttributeVector']) for x in reviewed['families']} if all('measuredAttributeVector' in x for x in reviewed['families']) else {k:np.mean(v,0) for k,v in families.items()}
        weak=[]
        keys=sorted(means)
        for i,ka in enumerate(keys):
            for kb in keys[i+1:]:
                count=int((np.abs(means[ka]-means[kb])>=.025).sum())
                if count<2:weak.append({'familyA':ka,'familyB':kb,'changedMeasuredDimensionsAt2_5Percent':count})
        within_weak=sum(int(np.sum(np.abs(a-b)>=.025)<2) for members in families.values() for ii,a in enumerate(members) for b in members[ii+1:])
        if within_weak:family_review.append({'category':category,'withinFamilyWeakPairCount':within_weak})
        results.append({'category':category,'modelCount':len(rows),'allPairCount':pair_count,
             'nearDuplicateCandidateCount':len(flagged),'maximumScreenedMinimumThreeViewIoU':closest,
             'familyPairCount':780,'familyPairsWithFewerThanTwoMeanDimensionDifferences':len(weak),'withinFamilyPairsWithFewerThanTwoAttributeDifferences':within_weak})
        review+=flagged;family_review+=weak
        print(category,'near candidates',len(flagged),'family review pairs',len(weak),flush=True)
    report={'modelCount':len(m['models']),'method':'All within-category pairs screened on normalized body and required-part dimensions; close pairs compared on three uniformly normalized silhouettes.',
            'normalization':'one common linear scale on XYZ; preserves body aspect ratios',
            'candidateThresholds':{'partDimensionDelta':.055,'minimumThreeViewIoU':.985,'uniformlyNormalizedVolumeIoU':.975},
            'nearDuplicateCandidateCount':len(review),'nearDuplicateCandidates':review,
            'familyReviewPairCount':len(family_review),'familyReviewPairs':family_review,
            'familyAuditMethod':'Pairwise measured actual anchor required-part dimensions, relative volumes and positions; requires two attribute changes of at least .025.',
            'categoryResults':results,'status':'review_required' if review or family_review else 'screens_passed',
            'limitations':'Silhouette and proportion screens cannot prove absence of every semantic near-duplicate or replace visual quality review.'}
    (ROOT/'structural_review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
