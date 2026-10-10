"""Whole-batch cross-category silhouette/volume screen, ignoring part labels/color."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from repair_review import read,scaled_occ

ROOT=Path(__file__).resolve().parent.parent
POP=np.array([i.bit_count() for i in range(256)],np.uint8)

def iou(a,b):return POP[np.bitwise_and(a,b)].sum()/POP[np.bitwise_or(a,b)].sum()

def main():
    rows=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))['models'];features=[];volumes=[];projections=[]
    for ix,row in enumerate(rows):
        doc,p,co,la,pa,e=read(row);vol=scaled_occ(co);dims=np.array(e['boundsSize'])
        views=[vol.any(axis=a) for a in [2,0,1]]
        features.append(list(dims/dims.max())+[vol.mean()]+[v.mean() for v in views])
        volumes.append(np.packbits(vol));projections.append([np.packbits(v) for v in views])
        if (ix+1)%2000==0:print('CROSS-CATEGORY DESCRIPTORS',ix+1,flush=True)
    pairs=cKDTree(features).query_pairs(.055,p=np.inf);flags=[];tested=0
    for i,j in sorted(pairs):
        if rows[i]['category']==rows[j]['category']:continue
        tested+=1
        views=[float(iou(a,b)) for a,b in zip(projections[i],projections[j])]
        if min(views)<.985:continue
        vol=float(iou(volumes[i],volumes[j]))
        if vol>=.975:flags.append({'modelA':rows[i]['modelId'],'modelB':rows[j]['modelId'],
          'categoryA':rows[i]['category'],'categoryB':rows[j]['category'],'minimumThreeViewIoU':min(views),'normalizedVolumeIoU':vol})
    report={'modelCount':len(rows),'screenedDescriptorPairCount':tested,'candidateCount':len(flags),'candidates':flags,
         'method':'All categories in one Chebyshev descriptor-radius index; descriptors include aspect ratios, normalized volume and three silhouette areas. Close cross-category pairs receive complete three-silhouette and volume IoU checks.',
         'thresholds':{'descriptorRadius':.055,'minimumThreeViewIoU':.985,'volumeIoU':.975},'passed':not flags}
    (ROOT/'cross_category_structural_review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    if flags:
        path=ROOT/'structural_review.json';review=json.loads(path.read_text(encoding='utf-8'));review['nearDuplicateCandidates']+=flags;review['nearDuplicateCandidateCount']=len(review['nearDuplicateCandidates']);review['status']='review_required';path.write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
    print('CROSS-CATEGORY COMPLETE',tested,'screened pairs;',len(flags),'candidates',flush=True)

if __name__=='__main__':main()
