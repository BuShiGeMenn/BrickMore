"""Bounded global backtracking and independently audited <=2% local additions.

The sealed v3 adapter/toolkit and published inputs are never modified.
"""
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from fractions import Fraction
import math
from pathlib import Path
import sys
import time

LEGACY = Path(__file__).resolve().parent.parent / 'voxel_assembly_b'
sys.path.insert(0, str(LEGACY))
import assembly_pipeline as a

VERSION = 'quality_bounded_global_cover_q2_v2'
AUDITOR_VERSION = 'independent_incremental_dsu_q2_v1'
POLICY = dict(world_dim=48, brick_library='extended', min_support_fraction=.10,
              max_cantilever_distance=2, max_components=64)
OFFSETS = ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1))


def neighbours(p):
    x,y,z = p
    return ((x+dx,y+dy,z+dz) for dx,dy,dz in OFFSETS)


def budget_for(count, ratio):
    if not isinstance(ratio, (int,float)) or not math.isfinite(ratio) or not 0 <= ratio <= .02:
        raise ValueError('repair ratio must be finite and in 0..0.02')
    return int(Fraction(str(ratio))*count)


def repair_audit(original, target, ratio=.02):
    """Recompute differences; do not trust planner counts, flags or history."""
    limit = budget_for(len(original), ratio)
    valid = all(isinstance(p,tuple) and len(p)==3 and
                all(type(v) is int and 0 <= v < 48 for v in p) and
                type(c) is int and 0 <= c <= 0xFFFFFF for p,c in target.items())
    if not valid:
        return {'passed':False,'issues':['invalid_target_coordinate_or_color'],
                'staticVerified':None,'fullPhysics':False}
    added = set(target)-set(original)
    removed = set(original)-set(target)
    recolored = {p for p in set(original)&set(target) if original[p]!=target[p]}
    local = all(any(q in original for q in neighbours(p)) for p in added)
    palette = set(original.values())
    palette_ok = all(target[p] in palette for p in added)
    changed = len(added)+len(removed)+len(recolored)
    return {'passed':bool(original) and valid and not removed and not recolored and
                    local and palette_ok and changed <= limit,
            'originalVoxelCount':len(original), 'targetVoxelCount':len(target),
            'addedVoxelCount':len(added),'removedVoxelCount':len(removed),
            'recoloredOriginalVoxelCount':len(recolored),'changedVoxelCount':changed,
            'changeRatio':changed/len(original) if original else None,
            'maximumChangeRatio':ratio,'maximumChangedVoxelCount':limit,
            'occupancyIoU':len(set(original)&set(target))/len(set(original)|set(target))
                           if original or target else 0,
            'allAdditionsWithinOneManhattanStepOfOriginal':local,
            'addedColorsFromOriginalPalette':palette_ok,
            'addedVoxelsInternalXYZRGB':[
                {'xyz':list(p),'rgb':[(target[p]>>16)&255,(target[p]>>8)&255,target[p]&255]}
                for p in sorted(added)],
            'sourceExactOccupancyHash':a.exact_hash({(x,z,y):c for (x,y,z),c in original.items()}),
            'targetExactOccupancyHash':a.exact_hash({(x,z,y):c for (x,y,z),c in target.items()}),
            'semanticVerified':False,'staticVerified':None,'fullPhysics':False}


def independent_audit(bricks, target, policy=POLICY):
    """Independent reconstruction; O(voxels + contacts alpha(bricks)), not B^2.

    Does not use the solver's rollback state or GeometryState. The original
    independent auditor is also used on every exported result (defence in depth).
    """
    issues=[]; occupied={}; parents=[]; sizes=[]; grounded=[]
    fractions=[]; distances=[]; components=0; last_z=0
    dimensions=set(a.dimensions_for_library(policy['brick_library']))
    def find(i):
        while parents[i]!=i:
            parents[i]=parents[parents[i]]; i=parents[i]
        return i
    for i,b in enumerate(bricks):
        keys=('h','w','x','y','z','color')
        if not isinstance(b,dict) or any(type(b.get(k)) is not int for k in keys):
            issues.append(f'brick_{i}:invalid_integer_fields'); continue
        h,w,x,y,z,c=(b[k] for k in keys)
        if (h,w) not in dimensions or not 0 <= c <= 0xFFFFFF:
            issues.append(f'brick_{i}:invalid_library_or_color'); continue
        if not (0 <= x <= policy['world_dim']-h and 0 <= y <= policy['world_dim']-w
                and 0 <= z < policy['world_dim']):
            issues.append(f'brick_{i}:out_of_bounds'); continue
        points=[(xx,yy,z) for xx in range(x,x+h) for yy in range(y,y+w)]
        if any(p in occupied for p in points):
            issues.append(f'brick_{i}:collision'); continue
        if z < last_z or z > last_z+1:issues.append(f'brick_{i}:layer_order_or_jump')
        last_z=z
        lower=[(p[0],p[1]) for p in points if (p[0],p[1],z-1) in occupied]
        fraction=len(lower)/(h*w) if z else 1.0
        distance=max(min(abs(p[0]-xx)+abs(p[1]-yy) for xx,yy in lower) for p in points) if lower else (0 if z==0 else None)
        fractions.append(fraction); distances.append(distance)
        if z and (not lower or fraction < policy['min_support_fraction']):issues.append(f'brick_{i}:lower_support')
        if z and policy['max_cantilever_distance'] is not None and (distance is None or distance > policy['max_cantilever_distance']):
            issues.append(f'brick_{i}:cantilever')
        index=len(parents); parents.append(index); sizes.append(1); grounded.append(z==0); components+=1
        contacts={occupied[q][0] for p in points for q in ((p[0],p[1],z-1),(p[0],p[1],z+1)) if q in occupied}
        for other in contacts:
            r,s=find(index),find(other)
            if r!=s:
                if sizes[r]<sizes[s]:r,s=s,r
                parents[s]=r; sizes[r]+=sizes[s]; grounded[r]=grounded[r] or grounded[s]; components-=1
        if components > policy['max_components']:issues.append(f'brick_{i}:prefix_component_budget')
        for p in points:occupied[p]=(index,c)
    output={p:v[1] for p,v in occupied.items()}
    missing=set(target)-set(output); added=set(output)-set(target)
    recolored={p for p in set(output)&set(target) if output[p]!=target[p]}
    roots={find(i) for i in range(len(parents))}
    grounded_roots={r for r in roots if grounded[r]}
    if len(roots)!=1:issues.append('multiple_or_zero_stud_components')
    if not roots or roots!=grounded_roots:issues.append('not_ground_reachable')
    if missing or added or recolored:issues.append('shape_or_color_mismatch')
    return {'passed':not issues,'issues':issues,'brickCount':len(bricks),
            'studComponentCount':len(roots),'groundReachable':bool(roots) and roots==grounded_roots,
            'inputVoxelCount':len(target),'outputVoxelCount':len(output),
            'missingVoxelCount':len(missing),'addedVoxelCount':len(added),
            'recoloredVoxelCount':len(recolored),'exactCoverage':not missing and not added,
            'colorPreserved':not recolored,'minimumPrefixSupportFraction':min(fractions,default=0),
            'maximumCantileverDistance':max((v for v in distances if v is not None),default=0),
            'sourceExactOccupancyHash':a.exact_hash({(x,z,y):c for (x,y,z),c in target.items()}),
            'assembledExactOccupancyHash':a.exact_hash({(x,z,y):c for (x,y,z),c in output.items()}),
            'staticVerified':None,'fullPhysics':False,'semanticVerified':False}


class RollbackState:
    """Generator state, deliberately separate from the independent auditor."""
    def __init__(self, max_components):
        self.max_components=max_components; self.bricks=[]; self.owner={}
        self.parents=[]; self.sizes=[]; self.components=0; self.history=[]
    def find(self,i):
        while self.parents[i]!=i:i=self.parents[i]
        return i
    def contacts(self,b):
        return {self.find(self.owner[(x,y,z-1)]) for x,y,z in b.cells() if (x,y,z-1) in self.owner}
    def push(self,b):
        roots=self.contacts(b)
        if self.components+1-len(roots)>self.max_components:return False
        index=len(self.bricks); old_components=self.components; changes=[]
        self.bricks.append(b); self.parents.append(index); self.sizes.append(1); self.components+=1
        for root in sorted(roots):
            r,s=self.find(index),self.find(root)
            if r!=s:
                if self.sizes[r]<self.sizes[s]:r,s=s,r
                changes.append((s,r,self.sizes[r])); self.parents[s]=r; self.sizes[r]+=self.sizes[s]; self.components-=1
        for p in b.cells():
            if p in self.owner:raise AssertionError('solver collision')
            self.owner[p]=index
        self.history.append((old_components,changes)); return True
    def pop(self):
        old_components,changes=self.history.pop(); b=self.bricks.pop()
        for p in b.cells():del self.owner[p]
        for s,r,old_size in reversed(changes):self.parents[s]=s; self.sizes[r]=old_size
        self.parents.pop(); self.sizes.pop(); self.components=old_components
    def raw(self,cells):
        return [{**asdict(b),'color':cells[(b.x,b.y,b.z)]} for b in self.bricks]


@dataclass
class Frame:
    layer: int
    remaining: int
    owns_brick: bool = False
    options: object = None
    cursor: int = 0
    memo_key: object = None


def solve(model,cfg=None,max_seconds=6,max_nodes=60000,future_pruning=True):
    """Iterative global exact-cover DFS: later failure can undo earlier layers.

    No layer's first solution is frozen. Orphan frontier pruning is necessary,
    not a quality relaxation. Exhausted bounded search never proves infeasible.
    """
    if not math.isfinite(max_seconds) or max_seconds<=0 or type(max_nodes) is not int or max_nodes<1:
        raise ValueError('finite positive solver budgets required')
    cfg=cfg or a.GeometryConfig(**POLICY,min_bricks=1)
    if not cfg.bottom_up or not cfg.require_lower_support:raise ValueError('bottom-up support required')
    started=time.monotonic(); deadline=started+max_seconds; nodes=0; stats=Counter()
    layers=[]; cells=model.cells; best=[]; best_count=0; stop='search_exhausted'
    has_upper=any(p[2]>0 for p in cells)
    suffix_labels={}
    if future_pruning:
        for z in sorted({p[2] for p in cells}):
            if time.monotonic()>=deadline:return [],{'algorithmVersion':VERSION,'nodes':0,
                'termination':'precomputation_time_budget','stats':dict(stats),
                'elapsedSeconds':time.monotonic()-started,'maxSeconds':max_seconds,
                'maxNodes':max_nodes,'completeSearch':False}
            suffix_labels[z]=possible_components({p:c for p,c in cells.items() if p[2]>z})[0]
    def result(raw,termination):
        return raw,{'algorithmVersion':VERSION,'nodes':nodes,'termination':termination,
                    'elapsedSeconds':time.monotonic()-started,'maxSeconds':max_seconds,
                    'maxNodes':max_nodes,'stats':dict(stats),'completeSearch':False,
                    'searchScope':'global layer backtracking, unchanged placement policy'}
    for z in sorted({p[2] for p in cells}):
        points=sorted(p for p in cells if p[2]==z); indices={p:i for i,p in enumerate(points)}
        candidates=[]; by_point=[[] for _ in points]
        for x,y,_ in points:
            if time.monotonic()>=deadline:return result(best,'precomputation_time_budget')
            for h,w in cfg.dimensions:
                b=a.Placement(h,w,x,y,z); footprint=tuple(b.cells())
                if not all(p in indices and cells[p]==cells[(x,y,z)] for p in footprint):continue
                if future_pruning and z==0 and has_upper and not any((p[0],p[1],1) in cells for p in footprint):
                    stats['ground_unconnectable_candidate_pruned']+=1; continue
                lower=[(p[0],p[1]) for p in footprint if (p[0],p[1],z-1) in cells]
                if z and (not lower or len(lower)/len(footprint)<cfg.min_support_fraction):continue
                distance=max(min(abs(p[0]-xx)+abs(p[1]-yy) for xx,yy in lower) for p in footprint) if lower else 0
                if z and cfg.max_cantilever_distance is not None and distance>cfg.max_cantilever_distance:continue
                mask=sum(1<<indices[p] for p in footprint); j=len(candidates)
                candidates.append((mask,b,len(lower)/len(footprint) if z else 1.0,distance))
                for p in footprint:by_point[indices[p]].append(j)
        if any(not options for options in by_point):return result(best,'no_supported_candidate')
        layers.append((z,points,candidates,by_point,(1<<len(points))-1))
    if not layers:return result(best,'empty_target')
    if [row[0] for row in layers]!=list(range(layers[-1][0]+1)):return result(best,'layer_gap')
    state=RollbackState(cfg.max_components); stack=[Frame(0,layers[0][4])]; dead_frontiers=set()
    def future_connectable(z):
        # A bipartite OVER-approximation: actual prefix roots on one side,
        # possible-stud components of all remaining voxels on the other.
        labels=suffix_labels[z]; roots={state.find(i) for i in range(len(state.bricks))}
        ids={('root',r):i for i,r in enumerate(sorted(roots))}
        for group in sorted(set(labels.values())):ids[('future',group)]=len(ids)
        parents=list(range(len(ids)))
        def find(i):
            while parents[i]!=i:parents[i]=parents[parents[i]]; i=parents[i]
            return i
        for p in layers[frame.layer][1]:
            above=(p[0],p[1],z+1)
            if above in labels:
                r=ids[('root',state.find(state.owner[p]))]; s=ids[('future',labels[above])]
                parents[find(r)]=find(s)
        return len({find(i) for i in range(len(ids))})==1
    while stack:
        if nodes>=max_nodes or time.monotonic()>=deadline:
            stop='node_budget' if nodes>=max_nodes else 'time_budget'; break
        frame=stack[-1]; z,points,candidates,by_point,full=layers[frame.layer]
        if frame.options is None:
            nodes+=1
            if len(state.owner)>best_count:
                best_count=len(state.owner); best=state.raw(cells)
            if not frame.remaining:
                frame.options=[]
                if frame.layer==len(layers)-1:
                    if state.components==1:
                        raw=state.raw(cells)
                        if independent_audit(raw,cells,asdict(cfg))['passed']:return result(raw,'complete')
                    stats['disconnected_complete_layouts']+=1
                else:
                    # An old component absent from the next layer's lower studs
                    # can never reconnect in any bottom-up continuation.
                    frontier={state.find(state.owner[(x,y,z)]) for x,y,_ in layers[frame.layer+1][1] if (x,y,z) in state.owner}
                    if len(frontier)!=state.components:
                        stats['orphan_frontier_pruned']+=1
                    elif future_pruning and not future_connectable(z):
                        stats['disconnected_future_graph_pruned']+=1
                    else:
                        labels={}; signature=[]
                        for p in points:
                            root=state.find(state.owner[p]); labels.setdefault(root,len(labels)); signature.append(labels[root])
                        key=(frame.layer,tuple(signature))
                        if key in dead_frontiers:stats['dead_frontier_cache_hits']+=1
                        else:
                            frame.memo_key=key
                            stack.append(Frame(frame.layer+1,layers[frame.layer+1][4])); continue
            else:
                choices=None; bits=frame.remaining
                while bits:
                    bit=bits&-bits; bits-=bit; i=bit.bit_length()-1
                    live=[j for j in by_point[i] if candidates[j][0]&frame.remaining==candidates[j][0]]
                    if not live:choices=[]; break
                    if choices is None or len(live)<len(choices):
                        choices=live
                        if len(live)==1:break
                def rank(j):
                    mask,b,support,distance=candidates[j]; roots=state.contacts(b)
                    future_groups={suffix_labels[z][(x,y,z+1)] for x,y,_ in b.cells()
                                   if (x,y,z+1) in suffix_labels.get(z,{})}
                    return (max(0,len(roots)-1)*100+max(0,len(future_groups)-1)*50
                            +mask.bit_count()*2+support*3-distance,
                            int((b.h>b.w)==(z%2==0)),-b.x,-b.y)
                frame.options=sorted(choices or [],key=rank,reverse=True)
        if frame.cursor<len(frame.options):
            j=frame.options[frame.cursor]; frame.cursor+=1; mask,b,_,_=candidates[j]
            if state.push(b):stack.append(Frame(frame.layer,frame.remaining^mask,True))
            else:stats['prefix_component_budget_rejections']+=1
        else:
            stack.pop()
            if frame.memo_key is not None and len(dead_frontiers)<20000:dead_frontiers.add(frame.memo_key)
            if frame.owns_brick:state.pop(); stats['rollback_bricks']+=1
    return result(best,stop)


def possible_components(cells):
    remaining=set(cells); labels={}; count=0
    while remaining:
        p=min(remaining); remaining.remove(p); pending=[p]; labels[p]=count
        while pending:
            p=pending.pop()
            for q in neighbours(p):
                if q in remaining and (q[2]!=p[2] or cells[q]==cells[p]):
                    remaining.remove(q); pending.append(q); labels[q]=count
        count+=1
    return labels,count


def allowed_additions(original):
    return {q for p in original for q in neighbours(p)
            if all(0 <= v < 48 for v in q) and q not in original}


def support_proposals(cells,witness,cfg,allowed):
    """Small local rectangle completion or one direct lower support voxel."""
    x,y,z=witness; proposals=[]; color=cells[witness]
    for h,w in cfg.dimensions:
        for dx in range(h):
            for dy in range(w):
                b=a.Placement(h,w,x-dx,y-dy,z); footprint=tuple(b.cells())
                if not all(0 <= v < cfg.world_dim for p in footprint for v in p):continue
                if any(p in cells and cells[p]!=color for p in footprint):continue
                added={p:color for p in footprint if p not in cells}
                if not added or not set(added)<=allowed:continue
                lower=[(p[0],p[1]) for p in footprint if (p[0],p[1],z-1) in cells]
                if z and (not lower or len(lower)/len(footprint)<cfg.min_support_fraction):continue
                if z and cfg.max_cantilever_distance is not None and max(
                    min(abs(p[0]-xx)+abs(p[1]-yy) for xx,yy in lower) for p in footprint)>cfg.max_cantilever_distance:continue
                proposals.append((added,'complete_local_supported_rectangle'))
    below=(x,y,z-1)
    if z and below not in cells and below in allowed:
        # The support's color comes from nearby original material, not a
        # recolor of the unsupported source voxel above it.
        nearby=Counter(cells[q] for q in neighbours(below) if q in cells and q[2]==below[2])
        if not nearby:nearby=Counter(cells[q] for q in neighbours(below) if q in cells)
        for c,_ in sorted(nearby.items(),key=lambda item:(-item[1],item[0]))[:3]:
            proposals.append(({below:c},'add_local_direct_lower_support'))
    unique={tuple(sorted(added.items())):(added,reason) for added,reason in proposals}
    return sorted(unique.values(),key=lambda item:(len(item[0]),
                  -sum((p[0],p[1],p[2]-1) in cells or p[2]==0 for p in item[0]),
                  tuple(sorted(item[0].items()))))


def bridge_proposals(cells,labels,allowed):
    """Real local material connecting labelled roots, never virtual unions."""
    candidates={}
    def consider(added,reason):
        if not added or not set(added)<=allowed:return
        roots={labels[q] for p,c in added.items() for q in neighbours(p)
               if q in labels and (q[2]!=p[2] or cells[q]==c)}
        if len(roots)<2:return
        key=tuple(sorted(added.items())); candidates[key]=(added,reason,len(roots))
    frontier={p for p in allowed if p not in cells and any(q in cells for q in neighbours(p))}
    for p in sorted(frontier):
        for c in sorted({cells[q] for q in neighbours(p) if q in cells}):
            consider({p:c},'add_local_component_bridge')
    for p in sorted(labels):
        x,y,z=p
        for q in ((x+1,y,z),(x,y+1,z)):
            if q not in labels or labels[p]==labels[q]:continue
            for dz in (1,-1):
                pair=((x,y,z+dz),(q[0],q[1],z+dz))
                if not all(0 <= v < 48 for r in pair for v in r):continue
                fixed={cells[r] for r in pair if r in cells}
                if len(fixed)>1:continue
                colors=fixed or {cells[p],cells[q]}
                for c in sorted(colors):
                    consider({r:c for r in pair if r not in cells},'add_local_vertical_stud_bridge')
    return [(added,reason) for added,reason,_ in sorted(candidates.values(),
            key=lambda item:(len(item[0]),-item[2],
                -sum(p[2]==0 or (p[0],p[1],p[2]-1) in cells for p in item[0]),
                tuple(sorted(item[0].items()))))]


def repair_plan(original,cfg,ratio=.02,variant=0,deadline=None,initial=None):
    cells=original.copy() if initial is None else initial.copy()
    if not repair_audit(original,cells,ratio)['passed']:raise ValueError('invalid initial repair')
    allowed=allowed_additions(original)
    limit=budget_for(len(original),ratio); actions=[]; steps=0
    while True:
        if deadline is not None and time.monotonic()>=deadline:
            return cells,actions,{'passed':False,'reason':'repair_planning_time_budget'}
        necessary=a.feasibility(a.VoxelModel(cells),cfg)
        if necessary['passed']:return cells,actions,necessary
        if len(cells)-len(original)>=limit:return cells,actions,necessary
        if necessary['reason']=='disconnected_possible_stud_graph':
            labels,_=possible_components(cells); proposals=bridge_proposals(cells,labels,allowed)
        else:
            witness=tuple(necessary['unsupportedVoxelWitnesses'][0])
            proposals=support_proposals(cells,witness,cfg,allowed)
        proposals=[(added,reason) for added,reason in proposals
                   if len(cells)+len(added)-len(original)<=limit]
        if not proposals:return cells,actions,necessary
        index=min(variant,len(proposals)-1) if steps==0 else 0
        added,reason=proposals[index]
        if any(p in cells for p in added):raise AssertionError('repair overwrites source')
        cells.update(added); actions.append({'reason':reason,'addedInternalXYZ':list(map(list,sorted(added)))})
        steps+=1
        if not repair_audit(original,cells,ratio)['passed']:raise AssertionError('planner quality violation')


def brick_component_labels(raw):
    owner={}; parents=list(range(len(raw)))
    def find(i):
        while parents[i]!=i:parents[i]=parents[parents[i]]; i=parents[i]
        return i
    for i,b in enumerate(raw):
        for p in a.Placement(**{k:b[k] for k in ('h','w','x','y','z')}).cells():owner[p]=i
    for p,i in owner.items():
        above=(p[0],p[1],p[2]+1)
        if above in owner:parents[find(i)]=find(owner[above])
    return {p:find(i) for p,i in owner.items()}


def optimize(model,max_ratio=.02,max_seconds=12,max_nodes=60000,repair_variants=3):
    """Exact first, then bounded additions. Only independent audits earn success."""
    budget_for(len(model.cells),max_ratio)
    if not math.isfinite(max_seconds) or max_seconds<=0 or type(repair_variants) is not int or repair_variants<1 or type(max_nodes) is not int or max_nodes<1:
        raise ValueError('positive finite optimization budgets required')
    started=time.monotonic(); deadline=started+max_seconds
    cfg=a.GeometryConfig(**POLICY,min_bricks=1); original=model.cells
    attempts=[]; selected=original; selected_raw=[]; selected_actions=[]
    necessary=a.feasibility(model,cfg)
    if necessary['passed']:
        strict_seconds=max_seconds if max_ratio==0 else min(4,max_seconds*.4)
        raw,details=solve(model,cfg,strict_seconds,max_nodes); selected_raw=raw
        attempts.append({'stage':'original_exact_global_search',**details})
        if independent_audit(raw,original)['passed']:
            return {'status':'success','bricks':raw,'targetCells':original.copy(),'repairActions':[],
                    'repairAudit':repair_audit(original,original,max_ratio),'searchAttempts':attempts,
                    'elapsedSeconds':time.monotonic()-started,'outcome':'success_original_exact'}
    seen=set()
    for variant in range(repair_variants if max_ratio else 0):
        if time.monotonic()>=deadline:break
        target,actions,necessary=repair_plan(original,cfg,max_ratio,variant,deadline)
        key=tuple(sorted((p,c) for p,c in target.items() if p not in original))
        if key in seen:continue
        seen.add(key)
        if not necessary['passed']:
            attempts.append({'stage':'bounded_repair_plan','variant':variant,
                             'termination':necessary['reason'],'addedVoxelCount':len(key)})
            continue
        remaining=deadline-time.monotonic()
        if remaining<=0:break
        raw,details=solve(a.VoxelModel(target),cfg,min(remaining,max(2,remaining/(repair_variants-variant))),max_nodes)
        attempts.append({'stage':'repaired_global_search','variant':variant,'addedVoxelCount':len(key),**details})
        check=independent_audit(raw,target)
        if check['outputVoxelCount']>sum(b['h']*b['w'] for b in selected_raw):
            selected,selected_raw,selected_actions=target,raw,actions
        if check['passed']:
            return {'status':'success','bricks':raw,'targetCells':target,'repairActions':actions,
                    'repairAudit':repair_audit(original,target,max_ratio),'searchAttempts':attempts,
                    'elapsedSeconds':time.monotonic()-started,'outcome':'success_repaired_q2' if key else 'success_original_exact'}
        # A completed but disconnected tiling supplies real brick roots, not
        # the loose voxel graph. Try one budgeted physical bridge and re-tile.
        if check['exactCoverage'] and check['studComponentCount']>1 and time.monotonic()<deadline:
            labels=brick_component_labels(raw)
            proposals=bridge_proposals(target,labels,allowed_additions(original))
            for added,reason in proposals:
                trial={**target,**added}
                if not repair_audit(original,trial,max_ratio)['passed']:continue
                trial,more,ok=repair_plan(original,cfg,max_ratio,0,deadline,initial=trial)
                if not ok['passed']:continue
                remaining=deadline-time.monotonic()
                if remaining<=0:break
                trial_raw,details=solve(a.VoxelModel(trial),cfg,remaining,max_nodes)
                attempts.append({'stage':'actual_brick_component_bridge',**details})
                if independent_audit(trial_raw,trial)['passed']:
                    return {'status':'success','bricks':trial_raw,'targetCells':trial,
                        'repairActions':actions+[{'reason':reason,'addedInternalXYZ':list(map(list,sorted(added)))}]+more,
                        'repairAudit':repair_audit(original,trial,max_ratio),'searchAttempts':attempts,
                        'elapsedSeconds':time.monotonic()-started,'outcome':'success_repaired_q2'}
                break
    return {'status':'draft','bricks':selected_raw,'targetCells':selected,
            'repairActions':selected_actions,'repairAudit':repair_audit(original,selected,max_ratio),
            'searchAttempts':attempts,'elapsedSeconds':time.monotonic()-started,
            'outcome':'bounded_search_or_repair_not_passed'}
