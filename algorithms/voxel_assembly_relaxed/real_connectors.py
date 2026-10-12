"""Full original-color partitions plus actual, local, budgeted connector bricks."""
from collections import Counter
import time

import relaxed_core as r
q=r.q
VERSION='explicit_local_connector_bricks_v1'


def cover(cells,variant=0):
    remaining=set(cells);raw=[];dims=q.a.dimensions_for_library('extended')
    while remaining:
        x,y,z=min(remaining,key=lambda p:(p[2],p[0],p[1]));choices=[]
        for h,w in dims:
            footprint=tuple((xx,yy,z) for xx in range(x,x+h) for yy in range(y,y+w))
            if all(p in remaining and cells[p]==cells[(x,y,z)] for p in footprint):
                contacts=sum((p[0],p[1],z-1) in cells or (p[0],p[1],z+1) in cells for p in footprint)
                choices.append(((h*w,contacts,int((h>w)==((z+variant)%2==0))),h,w,footprint))
        _,h,w,points=max(choices)
        raw.append(dict(h=h,w=w,x=x,y=y,z=z,color=cells[(x,y,z)]));remaining.difference_update(points)
    return raw


def connect(original,cells,raw,deadline):
    cells=cells.copy();raw=list(raw);allowed=q.allowed_additions(original);actions=[]
    cap=q.budget_for(len(original),.02);dims=q.a.dimensions_for_library('extended')
    while time.monotonic()<deadline:
        validation=r.audit(raw,cells)
        if validation['passed']:return raw,cells,actions
        remaining_budget=cap-len(set(original)^set(cells))
        if remaining_budget<=0:break
        labels=q.brick_component_labels(raw);ground={labels[p] for p in cells if p[2]==0}
        size=Counter(labels.values());available=allowed-set(cells);best=None
        for x,y,z in sorted(available):
            if time.monotonic()>=deadline:break
            for h,w in dims:
                if h*w>remaining_budget:continue
                points=tuple((xx,yy,z) for xx in range(x,x+h) for yy in range(y,y+w))
                if not all(p in available for p in points):continue
                contacts={s for p in points for s in ((p[0],p[1],z-1),(p[0],p[1],z+1)) if s in cells}
                groups={labels[p] for p in contacts};unrooted=groups-ground
                if not unrooted or (z!=0 and len(groups)<2):continue
                reaches_floor=z==0 or bool(groups&ground)
                score=(int(reaches_floor),len(unrooted)/(h*w),sum(size[g] for g in unrooted)/(h*w),-h*w,-z,-x,-y)
                if best is None or score>best[0]:
                    colors=Counter(cells[p] for p in contacts);color=min(colors,key=lambda c:(-colors[c],c))
                    best=(score,dict(h=h,w=w,x=x,y=y,z=z,color=color),points)
        if best is None:break
        _,brick,points=best;raw.append(brick);raw.sort(key=lambda b:(b['z'],b['x'],b['y'],b['h'],b['w']))
        for p in points:cells[p]=brick['color']
        actions.append(dict(stage='append_real_local_connector',brick=brick,addedInternalXYZ=[list(p) for p in points],
                            reason='actual_vertical_contacts_join_stud_components'))
        if not q.repair_audit(original,cells,.02)['passed']:raise AssertionError('connector add-only budget/locality/color violated')
    return raw,cells,actions


def optimize(original,seconds=2.):
    deadline=time.monotonic()+seconds;attempts=[];best=None
    for variant in (0,1):
        raw=cover(original,variant);raw,cells,actions=connect(original,original,raw,deadline)
        attempts.extend([dict(stage='full_monochrome_partition',variant=variant),*actions])
        validation=r.audit(raw,cells)
        if validation['passed']:
            return dict(bricks=raw,targetCells=cells,repairAudit=r.strict.m.repair_audit(original,cells,.02),
                        searchAttempts=attempts,additionsOnlyFailure=False)
        if best is None or validation['groundedComponentCount']>best[0]:best=(validation['groundedComponentCount'],raw,cells)
        if time.monotonic()>=deadline:break
    _,raw,cells=best
    return dict(bricks=raw,targetCells=cells,repairAudit=r.strict.m.repair_audit(original,cells,.02),searchAttempts=attempts,
                additionsOnlyFailure=True,additionsOnlyEvidence=dict(bricks=raw,targetCells=cells,passed=False))
