"""Explicitly lower MODULAR GEOMETRY tier; never a physical pass certificate."""
from collections import defaultdict
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'voxel_assembly_q4'))
import q4_experiment as strict
q=strict.q
VERSION='modular_grounded_actual_connectors_flow_v4'
POLICY=dict(world_dim=48,brick_library='extended',requireExactColorCoverage=True,
            requireAtLeastOneRealLowerStud=False,requireAtLeastOneRealVerticalStud=True,
            allowStudAttachmentFromAbove=True,requireEveryComponentGrounded=True,
            requireSingleStudComponent=False,minSupportFraction=None,maxCantileverDistance=None,
            prefixComponentLimit=None,installationSequenceVerified=False,fullPhysics=False,staticVerified=None)


def audit(bricks,cells):
    """Reconstruct occupancy/actual stud components; no virtual ground union."""
    occupied={};parents=[];ground=[];valid=[];issues=[];supports=[];distances=[];last=-1
    dimensions=set(q.a.dimensions_for_library('extended'))
    def find(i):
        while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
        return i
    for n,b in enumerate(bricks):
        if not isinstance(b,dict) or any(type(b.get(k)) is not int for k in ('h','w','x','y','z','color')):
            issues.append(f'brick_{n}:invalid_integer_fields');continue
        h,w,x,y,z,c=(b[k] for k in ('h','w','x','y','z','color'))
        if (h,w) not in dimensions or not 0<=c<=0xffffff or not (0<=x<=48-h and 0<=y<=48-w and 0<=z<48):
            issues.append(f'brick_{n}:library_bounds_or_color');continue
        points=tuple((xx,yy,z) for xx in range(x,x+h) for yy in range(y,y+w))
        if any(p in occupied for p in points):issues.append(f'brick_{n}:collision');continue
        if z<last:issues.append(f'brick_{n}:not_bottom_up')
        last=z;lower=[p for p in points if (p[0],p[1],z-1) in occupied]
        supports.append(len(lower)/len(points) if z else 1.)
        if lower:distances.append(max(min(abs(p[0]-r[0])+abs(p[1]-r[1]) for r in lower) for p in points))
        i=len(parents);parents.append(i);ground.append(z==0);valid.append((n,b,points,bool(lower)))
        for p in lower:
            other=occupied[(p[0],p[1],z-1)][0];parents[find(other)]=find(i)
        for p in points:occupied[p]=(i,c)
    roots={find(i) for i in range(len(parents))};floor={find(i) for i in range(len(parents)) if ground[i]}
    hanging=0
    for n,b,points,lower in valid:
        contacts=[p for p in points if (p[0],p[1],p[2]-1) in occupied or (p[0],p[1],p[2]+1) in occupied]
        if b['z'] and not contacts:issues.append(f'brick_{n}:no_real_vertical_stud')
        if b['z'] and not lower:hanging+=1
    output={p:c for p,(_,c) in occupied.items()}
    missing=set(cells)-set(output);extra=set(output)-set(cells)
    recolored={p for p in set(cells)&set(output) if cells[p]!=output[p]}
    if not roots or roots!=floor:issues.append('one_or_more_components_not_ground_reachable')
    if missing or extra or recolored:issues.append('shape_or_color_mismatch')
    return dict(passed=not issues,tier='relaxed_modular_geometry_not_physics',issues=issues,
                brickCount=len(bricks),studComponentCount=len(roots),groundedComponentCount=len(floor),
                allComponentsGrounded=bool(roots) and roots==floor,exactCoverage=not missing and not extra,
                colorPreserved=not recolored,missingVoxelCount=len(missing),extraVoxelCount=len(extra),
                upperAttachedBrickCount=hanging,installationSequenceVerified=False,
                recoloredVoxelCount=len(recolored),minimumSupportFraction=min(supports,default=0.),
                maximumActualCantileverDistance=max(distances,default=0),
                fullPhysics=False,staticVerified=None)


def tile(cells,seconds=.8,max_nodes=30000,bridge_labels=None):
    """Separate layer exact covers: lower STUD presence independent of brick IDs.

    This decomposition is valid only for the explicit multi-grounded-component
    tier. It is not used to pass the stricter one-component policy.
    """
    deadline=time.monotonic()+seconds;raw=[];nodes=0;uncoverable=[]
    for z in sorted({p[2] for p in cells}):
        points=sorted(p for p in cells if p[2]==z);ids={p:i for i,p in enumerate(points)}
        candidates=[];by_point=[[] for _ in points]
        for p in points:
            if time.monotonic()>deadline:return raw,dict(reason='enumeration_time_budget',completeSearch=False,nodes=nodes,unsupported=uncoverable)
            x,y,_=p
            for h,w in q.a.dimensions_for_library('extended'):
                footprint=tuple((xx,yy,z) for xx in range(x,x+h) for yy in range(y,y+w))
                if not all(r in ids and cells[r]==cells[p] for r in footprint):continue
                lower=sum((r[0],r[1],z-1) in cells or (r[0],r[1],z+1) in cells for r in footprint)
                if z and not lower:continue
                mask=sum(1<<ids[r] for r in footprint);index=len(candidates)
                candidates.append((mask,dict(h=h,w=w,x=x,y=y,z=z,color=cells[p]),lower))
                for r in footprint:by_point[ids[r]].append(index)
        unsupported=[p for p,options in zip(points,by_point) if not options]
        if unsupported:return raw,dict(reason='no_supported_monochrome_rectangle',completeSearch=True,nodes=nodes,unsupported=unsupported)
        full=(1<<len(points))-1;dead=set();stack=[(full,None,0,None)];chosen=[];solved=False
        while stack:
            nodes+=1
            if nodes>max_nodes or time.monotonic()>deadline:
                return raw,dict(reason='bounded_layer_cover_budget',completeSearch=False,nodes=nodes,unsupported=[])
            remaining,options,cursor,parent_choice=stack[-1]
            if not remaining:solved=True;break
            if options is None:
                if remaining in dead:options=[]
                else:
                    live=None;bits=remaining
                    while bits:
                        bit=bits&-bits;bits-=bit;idx=bit.bit_length()-1
                        current=[i for i in by_point[idx] if candidates[i][0]&remaining==candidates[i][0]]
                        if not current:live=[];break
                        if live is None or len(current)<len(live):live=current
                        if len(live)==1:break
                    def rank(i):
                        mask,b,contacts=candidates[i]
                        groups={bridge_labels[p] for p in q.a.Placement(**{k:b[k] for k in ('h','w','x','y','z')}).cells() if p in bridge_labels} if bridge_labels else set()
                        return (max(0,len(groups)-1)*100+mask.bit_count(),contacts,-i)
                    options=sorted(live or [],key=rank,reverse=True)
                stack[-1]=(remaining,options,0,parent_choice);cursor=0
            if cursor<len(options):
                index=options[cursor];stack[-1]=(remaining,options,cursor+1,parent_choice)
                chosen.append(index);stack.append((remaining^candidates[index][0],None,0,index))
            else:
                dead.add(remaining);stack.pop()
                if parent_choice is not None:chosen.pop()
        if not solved:return raw,dict(reason='layer_cover_exhausted',completeSearch=True,nodes=nodes,unsupported=[])
        raw.extend(candidates[i][1] for i in chosen)
    return raw,dict(reason='complete',completeSearch=True,nodes=nodes,unsupported=[])


def optimize(original,seconds=1.5):
    started=time.monotonic();deadline=started+seconds;target=original.copy();attempts=[]
    from real_connectors import optimize as connectors
    connected=connectors(original,min(2.,seconds*.4))
    attempts.extend(connected['searchAttempts'])
    if audit(connected['bricks'],connected['targetCells'])['passed']:
        return {**connected,'elapsedSeconds':time.monotonic()-started}
    # Original first, then real local supports. No deletions before audited failure.
    raw,stats=tile(target,min(.6,max(.05,seconds*.4)))
    attempts.append(dict(stage='original_modular_cover',**stats))
    if audit(raw,target)['passed']:
        return dict(bricks=raw,targetCells=target,repairAudit=strict.m.repair_audit(original,target,.02),searchAttempts=attempts,
                    additionsOnlyFailure=False,elapsedSeconds=time.monotonic()-started)
    if stats['reason']=='complete' and time.monotonic()<deadline:
        labels=q.brick_component_labels(raw)
        raw,stats=tile(target,min(.4,max(.05,deadline-time.monotonic())),bridge_labels=labels)
        attempts.append(dict(stage='actual_stud_component_bridge_retile',**stats))
        if audit(raw,target)['passed']:
            return dict(bricks=raw,targetCells=target,repairAudit=strict.m.repair_audit(original,target,.02),searchAttempts=attempts,
                        additionsOnlyFailure=False,elapsedSeconds=time.monotonic()-started)
    if time.monotonic()<deadline:
        from grounded_flow import solve
        flow_raw,flow_stats=solve(target,max(.05,min(4.,deadline-time.monotonic()-.3)))
        attempts.append(dict(stage='joint_real_stud_ground_flow',**flow_stats))
        if audit(flow_raw,target)['passed']:
            return dict(bricks=flow_raw,targetCells=target,repairAudit=strict.m.repair_audit(original,target,.02),searchAttempts=attempts,
                        additionsOnlyFailure=False,elapsedSeconds=time.monotonic()-started)
    cap=q.budget_for(len(original),.02);allowed=q.allowed_additions(original)
    for _ in range(cap):
        unsupported=stats.get('unsupported',[])
        if not unsupported or time.monotonic()>=deadline:break
        p=unsupported[0];below=(p[0],p[1],p[2]-1)
        if below not in allowed or below in target or p[2]==0:break
        adjacent=[r for r in q.neighbours(below) if r in target and r[2]==below[2]]
        color=target[min(adjacent)] if adjacent else original.get(p,target[p])
        target[below]=color
        raw,stats=tile(target,max(.03,min(.3,deadline-time.monotonic())))
        attempts.append(dict(stage='local_addition_cover',addedInternalXYZ=list(below),**stats))
        if audit(raw,target)['passed']:
            return dict(bricks=raw,targetCells=target,repairAudit=strict.m.repair_audit(original,target,.02),searchAttempts=attempts,
                        additionsOnlyFailure=False,elapsedSeconds=time.monotonic()-started)
    gate=dict(bricks=raw,targetCells=target.copy(),passed=audit(raw,target)['passed'])
    if gate['passed']:raise AssertionError('deletion attempted after additions success')
    # Original-only, fully enumerated eligibility is never inferred from a timeout.
    eligible=strict.m.deletion_eligibility(original,.02)
    # Failed hypothetical additions do not consume the final target's budget.
    # Preserve their actual failure evidence, then start deletion fallback from
    # the untouched original instead of keeping ineffective support material.
    target=original.copy();raw,stats=tile(target,max(.03,min(.3,deadline-time.monotonic())))
    while time.monotonic()<deadline and len(set(target)^set(original))<cap:
        unsupported=[p for p in stats.get('unsupported',[]) if p in target and p in eligible and p[2]>0]
        if not unsupported:break
        remaining=cap-len(set(target)^set(original));removed=unsupported[:remaining]
        for p in removed:del target[p]
        raw,stats=tile(target,max(.03,min(.3,deadline-time.monotonic())))
        attempts.append(dict(stage='eligible_detail_deletion_cover',removedInternalXYZ=[list(p) for p in removed],**stats))
        if audit(raw,target)['passed']:break
    repair=strict.m.repair_audit(original,target,.02)
    if not repair['passed']:raise AssertionError('relaxed planner violated unchanged edit quality')
    return dict(bricks=raw,targetCells=target,repairAudit=repair,searchAttempts=attempts,additionsOnlyFailure=True,
                additionsOnlyEvidence=gate,elapsedSeconds=time.monotonic()-started)
