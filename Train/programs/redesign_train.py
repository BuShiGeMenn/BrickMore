import json
from pathlib import Path
from collections import defaultdict
import numpy as np
from repair_review import read,scaled_occ,regroup
from produce import allocation,ROOT,export,aggregate,savejson
from geometry import plan,build
from checks import validate,digest,canonical

def main():
    rows=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))['models'];jobs={j['modelId']:j for j in allocation()}
    others=[r for r in rows if r['category']!='train'];exacts={r['exactOccupancyHash'] for r in others};canons={r['canonicalGeometryHash'] for r in others}
    exacts|={json.loads(x)['exactOccupancyHash'] for x in (ROOT/'historical_models_55255.jsonl').read_text(encoding='utf-8').splitlines()}
    busvol=[scaled_occ(read(r)[2]) for r in rows if r['category']=='bus'];accepted=[];repairs=[]
    for row in rows:
        if row['category']!='train':continue
        job=jobs[row['modelId']]
        for revision in range(1200,2000):
            p=plan('train',job['family'],job['instance'],revision);p['railCoupler']=True
            raw=build(p);initial=len(raw[0]);scale=1 if 750<=initial<=1250 else (1000/initial)**(1/3);history=[];found=None
            for attempt in range(1,21):
                co,la,pa,cl,e=build(p,scale);v=validate(p,co,la,pa,e)
                history.append({'attempt':attempt,'absoluteUniformScaleFromOriginal':float(scale),'voxelCount':len(co),'failureReasons':v['failureReasons']})
                if v['passed']:found=(p,co,la,pa,cl,e,v,history,initial);break
                scale*=np.clip((1000/max(1,len(co)))**(1/3),.8,1.25) if len(co)<750 or len(co)>1250 else (1.045 if attempt%2 else .96)
            if found is None:continue
            ex=digest(co);ch=canonical(co)
            if ex in exacts or ch in canons:continue
            vol=scaled_occ(co)
            if any(np.count_nonzero(vol&vv)/np.count_nonzero(vol|vv)>=.975 for vv in busvol+accepted):continue
            new=export(job,found,ex,ch,revision+1);row.clear();row.update(new);exacts.add(ex);canons.add(ch);accepted.append(vol)
            repairs.append({'modelId':job['modelId'],'revision':revision,'reason':'functional_train_couplers_and_underframe; separate railway geometry from buses'})
            break
        else:raise RuntimeError('Train redesign failed '+job['modelId'])
        if len(repairs)%25==0:print('RAILWAY STRUCTURE REDESIGN',len(repairs),'/476',flush=True)
    rows=regroup(rows);aggregate(rows)
    savejson(ROOT/'train_category_redesign.json',{'replacedModelCount':len(repairs),'repairs':repairs,'actualNewParts':['coupler','underframe'],'meaning':'real front and rear rail couplings plus a load-carrying underframe; no signature or arbitrary geometry'})

if __name__=='__main__':main()
