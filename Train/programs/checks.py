import hashlib,itertools
import numpy as np
from scipy import ndimage as ndi
from geometry import REQUIRED

STRUCT=ndi.generate_binary_structure(3,1)
DIRS=[(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]
DNAME=['+x','-x','+y','-y','+z','-z']
TOKEN=[f'{x},{y},{z}'.encode() for x in range(48) for y in range(48) for z in range(48)]
TRANSFORMS=list(itertools.product(itertools.permutations(range(3)),itertools.product([-1,1],repeat=3)))

def digest(coords):
    a=np.asarray(coords,dtype=np.int32)
    ids=np.sort(a[:,0]*2304+a[:,1]*48+a[:,2])
    return hashlib.sha256(b';'.join(TOKEN[i] for i in ids)).hexdigest()

def canonical(coords):
    a=np.asarray(coords,dtype=np.int32); out=[]
    for perm,sign in TRANSFORMS:
        b=a[:,perm]*sign; b-=b.min(axis=0)
        out.append(digest(b))
    return min(out)

def togrid(world,e):
    return np.rint(np.array(world)*e['worldToGrid']['scale']+e['worldToGrid']['offset']).astype(int)

def air_path(occ,point,direction):
    p=np.asarray(point,dtype=int)
    if np.any(p<0) or np.any(p>=48):return False
    while np.all((p>=0)&(p<48)):
        if occ[tuple(p)]:return False
        p=p+direction
    return True

def surface_records(coords,labs,parts,e):
    occ=np.zeros((48,48,48),bool); occ[tuple(coords.T)]=True
    label=np.zeros(occ.shape,np.uint8);label[tuple(coords.T)]=labs
    records=[]
    for name,owner,views in [('glass','lens',['front']),('shutter','body',['top']),
              ('viewfinder','body',['top']),('window','cabin',['front','right','left']),
              ('door','body',['right']),('key','keyboard',['top']),('black_key','keyboard',['top']),
              ('pickup','body',['front']),('bridge','body',['front'])]:
        if name not in parts:continue
        cells=coords[labs==parts.index(name)]
        group=[name,owner]
        if name in ['key','black_key']:group+=['key','black_key']
        if name=='door':group+=['cabin','window']
        joint=np.isin(label,[parts.index(x) for x in group if x in parts])
        jc,_=ndi.label(joint,STRUCT)
        owner_components=set(jc[label==parts.index(owner)]) if owner in parts else set()
        owner_components.discard(0)
        for coord in cells:
            exposed=[]; connections=[]; actualviews=[]
            for di,delta in enumerate(DIRS):
                nb=coord+delta
                if np.any(nb<0) or np.any(nb>=48) or not occ[tuple(nb)]:exposed.append(DNAME[di])
                elif owner in parts and label[tuple(nb)]==parts.index(owner): connections.append(DNAME[di])
            if not exposed:continue
            for view in views:
                direction={'front':(0,0,1),'right':(1,0,0),'left':(-1,0,0),'top':(0,1,0)}[view]
                if air_path(occ,coord+direction,direction):actualviews.append(view)
            if actualviews:
                records.append({'featureId':name,'ownerPart':owner,'coordinate':coord.tolist(),
                  'localPosition':((coord-e['worldToGrid']['offset'])/e['worldToGrid']['scale']).round(3).tolist(),
                  'airNeighborCount':len(exposed),'exposedFaceDirections':exposed,
                  'connectedToOwner':int(jc[tuple(coord)]) in owner_components,'directOwnerFaceDirections':connections,'expectedViews':views,
                  'rayClear':{v:v in actualviews for v in views},'unoccludedPixels':{v:int(v in actualviews) for v in views}})
    return records

def validate(p,coords,labs,parts,e):
    errors=[]; n=len(coords)
    occ=np.zeros((48,48,48),bool);occ[tuple(coords.T)]=1
    label=np.zeros(occ.shape,np.uint8);label[tuple(coords.T)]=labs
    _,components=ndi.label(occ,STRUCT)
    bounds=coords.min(axis=0).tolist()+coords.max(axis=0).tolist()
    missing=[v for v in REQUIRED[p['category']] if v not in parts or not np.any(labs==parts.index(v))]
    if not 750<=n<=1250:errors.append('voxel_count')
    if components!=1:errors.append('disconnected')
    if missing:errors.append('missing_parts:'+','.join(missing))
    if coords[:,1].min()!=0:errors.append('ground')
    details={}; c=p['category']
    for part,expected in [('wheel',e.get('wheelCount')),('leg',e.get('legCount')),('handle',e.get('handleCount')),('coupler',e.get('couplerCount'))]:
        if expected is None:continue
        pm=label==parts.index(part); cm,nc=ndi.label(pm,STRUCT)
        adjacent=ndi.binary_dilation(pm,structure=STRUCT)&occ&~pm
        component_roots=[]; boxes=[]
        for ix in range(1,nc+1):
            m=cm==ix; root=ndi.binary_dilation(m,structure=STRUCT)&occ&~pm
            pc=np.argwhere(m);component_roots.append(int(root.sum()))
            boxes.append({'minimum':pc.min(axis=0).tolist(),'maximum':pc.max(axis=0).tolist(),'voxelCount':len(pc)})
        good=nc==expected and all(v>=2 for v in component_roots)
        if part=='leg':good &= all(b['minimum'][1]==0 for b in boxes)
        details[part]={'expectedCount':expected,'measuredComponents':nc,'attachmentFaceCellCounts':component_roots,'componentBounds':boxes,'passed':bool(good)}
        if not good:errors.append(part+'_topology')
    if c in ['basket','bottle','bowl','jar','mug','pot']:
        point=togrid(e['cavityCenter'],e)
        # Seek a genuine centered empty cell above the bottom and beneath the mouth.
        cap=int(coords[labs==parts.index('rim'),1].max())
        ys=[y for y in range(point[1],min(cap,47)) if not occ[point[0],y,point[2]]]
        if ys:point[1]=ys[0]
        up=bool(ys) and air_path(occ,point,(0,1,0))
        if c=='basket' and ys:
            # Carrying arch may occlude the center ray; the mouth is still open.
            air_components,_=ndi.label(~occ,STRUCT)
            inside=air_components[tuple(point)]
            up=inside!=0 and bool(np.any(air_components[:,cap+1:,:]==inside))
        cropped=occ[:,:min(48,cap+1),:];empty=~cropped
        seed=np.zeros_like(empty);seed[0]=empty[0];seed[-1]=empty[-1];seed[:,:,0]|=empty[:,:,0];seed[:,:,-1]|=empty[:,:,-1];seed[:,0,:]|=empty[:,0,:]
        outside=ndi.binary_propagation(seed,structure=STRUCT,mask=empty)
        sealed=bool(ys) and not outside[tuple(point)]
        details['cavity']={'center':point.tolist(),'openingAxis':'+y','opensThroughMouth':bool(up),'closedBottomAndNoSideLeak':bool(sealed),'passed':bool(up and sealed)}
        if not up or not sealed:errors.append('container_cavity')
        if c=='mug':
            pm=label==parts.index('handle'); pc=np.argwhere(pm)
            z=int(round(np.median(pc[:,2]))); plane=pm[:,:,z]
            filled=ndi.binary_fill_holes(plane); hole=filled&~plane
            holes,nh=ndi.label(hole)
            validhole=False
            for hi in range(1,nh+1):
                for x,y in np.argwhere(holes==hi):
                    if not occ[x,y,z] and air_path(occ,[x,y,z],(0,0,1)) and air_path(occ,[x,y,z],(0,0,-1)):validhole=True;break
            # The two roots must be separated vertically and both face attached to cup wall.
            adjacent=ndi.binary_dilation(pm,structure=STRUCT)&occ&~pm
            yy=np.argwhere(adjacent)[:,1] if adjacent.any() else []
            roots=bool(len(yy)) and max(yy)-min(yy)>=3
            details['handleHole']={'throughHole':bool(validhole),'upperAndLowerRoots':bool(roots),'passed':bool(validhole and roots)}
            if not validhole or not roots:errors.append('handle_hole')
    if c in ['birdhouse','guitar'] and 'cavityCenter' in e:
        point=togrid(e['cavityCenter'],e);good=air_path(occ,point,(0,0,1))
        details['functionalOpening']={'center':point.tolist(),'opensIntoInterior':bool(good),'axis':'+z','passed':bool(good)}
        if not good:errors.append('functional_opening')
        if c=='birdhouse':
            entry=togrid(e['entryCenter'],e);closed=occ.copy()
            radius=e['entryRadius']*e['worldToGrid']['scale']+1.5
            xx,yy=np.indices((48,48))
            cap=(xx-entry[0])**2+(yy-entry[1])**2<=radius**2
            closed[:,:,max(0,entry[2]-1):min(48,entry[2]+2)]|=cap[:,:,None]
            air=~closed;seed=np.zeros_like(air)
            for axis in range(3):
                ix=[slice(None)]*3;ix[axis]=0;seed[tuple(ix)]|=air[tuple(ix)];ix[axis]=-1;seed[tuple(ix)]|=air[tuple(ix)]
            outside=ndi.binary_propagation(seed,structure=STRUCT,mask=air)
            protected=not outside[tuple(point)]
            details['protectedRoom']={'entryTemporarilyCapped':True,'noOtherSideOrRoofLeak':bool(protected),'passed':bool(protected)}
            if not protected:errors.append('birdhouse_side_or_roof_leak')
    if c=='bookshelf':
        pm=label==parts.index('shelf');layers=sorted(set(np.argwhere(pm)[:,1]))
        groups=1+sum(b>a+1 for a,b in zip(layers,layers[1:])) if layers else 0
        good=groups==e['shelfCount']
        details['shelfGaps']={'expectedLayers':int(e['shelfCount']),'measuredLayers':int(groups),'occupiedYLayers':[int(x) for x in layers],'passed':bool(good)}
        if not good:errors.append('shelf_gaps')
    if c=='vessel':
        point=togrid(e['cockpitCenter'],e);good=air_path(occ,point,(0,1,0))
        details['deckOpening']={'center':point.tolist(),'openToTop':bool(good),'passed':bool(good)}
        if not good:errors.append('deck_opening')
    features=surface_records(coords,labs,parts,e)
    if any(not x['connectedToOwner'] for x in features):errors.append('feature_owner_connection')
    for feature in ['glass','shutter','window','door','key','bridge','pickup']:
        if feature in parts and np.any(labs==parts.index(feature)):
            exposed=[v for v in features if v['featureId']==feature]
            if not exposed:errors.append('surface_invisible:'+feature)
    return {'passed':not errors,'actualVoxelCount':n,'sixNeighborComponentCount':int(components),'coordinateBounds':bounds,
       'lowestContactY':int(coords[:,1].min()),'missingRequiredParts':missing,'semanticMeasurements':details,
       'surfaceFeatures':features,'featureCheckStatus':'measured' if features else 'not_applicable',
       'featureCheckReason':'No painted functional surface feature in this subtype.' if not features else '',
       'failureReasons':errors}
