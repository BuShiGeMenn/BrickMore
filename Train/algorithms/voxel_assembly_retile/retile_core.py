"""Monochrome bridge placement with local retiling of existing bricks.

Uses the published modular geometry policy and unchanged <=2% repair auditor.
All trials cover their entire target; side contact is never a stud connection.
"""
from collections import Counter
import heapq
import math
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'voxel_assembly_relaxed'))
import relaxed_core as base
import real_connectors as connectors

VERSION = 'local_monochrome_bridge_retile_v1'
DIMENSIONS = tuple(base.q.a.dimensions_for_library('extended'))


def footprint(brick):
    return tuple((x,y,brick['z']) for x in range(brick['x'],brick['x']+brick['h'])
                 for y in range(brick['y'],brick['y']+brick['w']))


def ordered(bricks):
    return sorted(bricks, key=lambda b:(b['z'],b['x'],b['y'],b['h'],b['w'],b['color']))


def graph(bricks):
    owner = {}; parent = list(range(len(bricks)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for i,b in enumerate(bricks):
        for p in footprint(b):
            if p in owner: raise ValueError('Overlapping input bricks')
            owner[p] = i
    for (x,y,z),i in owner.items():
        other = owner.get((x,y,z+1))
        if other is not None: parent[find(i)] = find(other)
    labels = {p:find(i) for p,i in owner.items()}
    sizes = Counter(labels.values())
    grounded = {labels[p] for p in labels if p[2] == 0}
    loose = set(sizes)-grounded
    return dict(owner=owner,labels=labels,sizes=sizes,grounded=grounded,loose=loose,
                ungroundedVoxels=sum(sizes[c] for c in loose),ungroundedComponents=len(loose))


def objective(bricks,cells,original):
    g = graph(bricks)
    return (g['ungroundedVoxels'],g['ungroundedComponents'],len(set(cells)-set(original)),len(bricks))


def bridge_candidates(bricks,cells,original,allowed,deadline,allow_additions=True):
    """A bridge may overlap old bricks, while preserving every original RGB.

    Enumerate around actual above/below contacts of ungrounded components;
    score real vertical component joins, never adjacency or a virtual floor.
    """
    g = graph(bricks); labels = g['labels']; old_owner = g['owner']
    remaining_budget = base.q.budget_for(len(original),.02)-len(set(cells)-set(original))
    anchors = set()
    for (x,y,z),group in labels.items():
        if group not in g['loose']: continue
        for height in (z-1,z+1):
            p = (x,y,height)
            if 0 <= height < 48 and (p in cells or (allow_additions and p in allowed)):
                anchors.add(p)
    seen = set(); heaps = [[],[]]; enumerated = 0
    for ax,ay,z in sorted(anchors):
        for h,w in DIMENSIONS:
            for dx in range(h):
                x = ax-dx
                if not 0 <= x <= 48-h: continue
                for dy in range(w):
                    y = ay-dy
                    if not 0 <= y <= 48-w: continue
                    marker = (x,y,z,h,w)
                    if marker in seen: continue
                    seen.add(marker); enumerated += 1
                    if enumerated % 256 == 0 and time.monotonic() >= deadline:
                        return [row[2] for heap in heaps for row in sorted(heap,reverse=True)]
                    points = tuple((xx,yy,z) for xx in range(x,x+h) for yy in range(y,y+w))
                    extra = tuple(p for p in points if p not in cells)
                    if extra and (not allow_additions or len(extra)>remaining_budget or any(p not in allowed for p in extra)): continue
                    colors = {cells[p] for p in points if p in cells}
                    if len(colors)>1: continue
                    contacts = {(p[0],p[1],p[2]+dz) for p in points for dz in (-1,1)}
                    groups = {labels[p] for p in contacts if p in labels}
                    loose = groups & g['loose']
                    rooted = z == 0 or bool(groups & g['grounded'])
                    if not loose or (len(groups)<2 and not (z==0 and loose)): continue
                    if colors: color = next(iter(colors))
                    else:
                        pool = Counter(cells[p] for p in contacts if p in cells)
                        if not pool: continue
                        color = min(pool,key=lambda c:(-pool[c],c))
                    affected = {old_owner[p] for p in points if p in old_owner}
                    benefit = sum(g['sizes'][group] for group in loose) if rooted else 0
                    rank = (int(rooted),benefit/max(1,len(extra)),len(groups),-len(extra),-len(affected),h*w)
                    candidate = {'brick':dict(x=x,y=y,z=z,h=h,w=w,color=color),'points':points,
                                 'added':extra,'affected':affected,'predictedGroundedVoxelGain':benefit}
                    heap = heaps[bool(extra)]
                    item = (rank,marker,candidate)
                    if len(heap)<64: heapq.heappush(heap,item)
                    elif item[:2]>heap[0][:2]: heapq.heapreplace(heap,item)
    return [row[2] for heap in heaps for row in sorted(heap,reverse=True)]


def place_bridge(bricks,cells,candidate,variant=0):
    """Remove intersected bricks and exactly tile their remaining cells."""
    points = set(candidate['points']); affected = candidate['affected']
    remainder = {p:cells[p] for i in affected for p in footprint(bricks[i]) if p not in points}
    raw = [b for i,b in enumerate(bricks) if i not in affected]
    if remainder: raw.extend(connectors.cover(remainder,variant))
    raw.append(candidate['brick'])
    target = cells.copy()
    for p in candidate['added']: target[p] = candidate['brick']['color']
    return ordered(raw),target


def search(original,bricks,cells,deadline,allow_additions=True):
    allowed = base.q.allowed_additions(original)
    actions = []; trials = 0; start_score = objective(bricks,cells,original)
    # Strict improvement in disconnected voxel count / component count prevents
    # the oscillating endpoint repairs encountered by the old local stitcher.
    for iteration in range(64):
        before = objective(bricks,cells,original)
        if before[0] == 0 or time.monotonic() >= deadline: break
        candidates = bridge_candidates(bricks,cells,original,allowed,deadline,allow_additions)
        best = None
        for candidate in candidates:
            if time.monotonic() >= deadline: break
            for variant in (0,1):
                raw,target = place_bridge(bricks,cells,candidate,variant); trials += 1
                score = objective(raw,target,original)
                if score[:2] >= before[:2]: continue
                if best is None or score<best[0]: best = (score,raw,target,candidate)
            # Prefer retiling without additions; stop after an improving trial
            # and re-evaluate the real graph before spending another voxel.
            if best is not None: break
        if best is None: break
        score,bricks,cells,candidate = best
        repair = base.q.repair_audit(original,cells,.02)
        if not repair['passed']: raise AssertionError('Bridge trial violated unchanged local-addition policy')
        actions.append(dict(stage='rebuild_existing_and_added_bridge',brick=candidate['brick'],
                            affectedBrickCount=len(candidate['affected']),addedInternalXYZ=[list(p) for p in candidate['added']],
                            ungroundedVoxelsBefore=before[0],ungroundedVoxelsAfter=score[0],
                            ungroundedComponentsBefore=before[1],ungroundedComponentsAfter=score[1]))
    return bricks,cells,dict(stage='local_bridge_retile',algorithmVersion=VERSION,
                            trialCount=trials,actions=actions,initialObjective=list(start_score),
                            finalObjective=list(objective(bricks,cells,original)),boundedSearchNotImpossibility=True)


def result(original,bricks,cells,attempts,started,**fields):
    repair = base.strict.m.repair_audit(original,cells,.02)
    if not repair['passed']: raise AssertionError('Final repair gate rejected candidate')
    output = {p:b['color'] for b in bricks for p in footprint(b)}
    if output != cells or sum(b['h']*b['w'] for b in bricks)!=len(cells):
        raise AssertionError('Optimizer returned an incomplete or overlapping draft')
    return dict(bricks=ordered(bricks),targetCells=cells,repairAudit=repair,searchAttempts=attempts,
                elapsedSeconds=time.monotonic()-started,algorithmVersion=VERSION,**fields)


def optimize(original,seconds=8.,baseline=None):
    if not math.isfinite(seconds) or seconds<=0: raise ValueError('seconds must be positive and finite')
    if not original: raise ValueError('Empty original model')
    # Validate all original coordinates/colors before placing any brick.
    if not base.q.repair_audit(original,original,.02)['passed']: raise ValueError('Invalid original voxel model')
    if min(p[2] for p in original)!=0: raise ValueError('Original model must have actual ground contact')
    started=time.monotonic(); deadline=started+seconds; attempts=[]
    if baseline is not None:
        raw=baseline['bricks'];cells=baseline['targetCells']
        if base.audit(raw,cells)['passed'] and base.strict.m.repair_audit(original,cells,.02)['passed']:
            gate=baseline.get('additionsOnlyEvidence')
            if set(original)-set(cells):
                if not isinstance(gate,dict) or gate.get('auditor') not in ('strict_q4','relaxed_modular'):
                    raise ValueError('Retaining a deletion requires the actual additions-only failure evidence')
                auditor=base.q.independent_audit if gate['auditor']=='strict_q4' else base.audit
                if not base.strict.m.repair_audit(original,gate['targetCells'],.02)['passed'] or set(original)-set(gate['targetCells']) or auditor(gate['bricks'],gate['targetCells'])['passed'] or gate.get('passed') is not False:
                    raise ValueError('Retained deletion has no valid additions-only failure gate')
            return result(original,raw,cells,[dict(stage='retain_independently_verified_success')],started,
                          additionsOnlyFailure=bool(set(original)-set(cells)),
                          additionsOnlyEvidence=gate,retainedBaseline=True)
    candidates=[]
    for variant in (0,1):
        raw=ordered(connectors.cover(original,variant))
        candidates.append((objective(raw,original,original),raw,original.copy()))
    score,raw,cells=min(candidates,key=lambda item:item[0])
    if base.audit(raw,cells)['passed']:
        return result(original,raw,cells,[dict(stage='original_full_monochrome_cover')],started,
                      additionsOnlyFailure=False,retainedBaseline=False)
    # Use most of the budget for whole-target, actual-component retiling. The
    # former optimizer remains a separately audited fallback, not a new policy.
    retile_deadline=started+seconds*.82
    raw,cells,info=search(original,raw,cells,retile_deadline)
    attempts.append(info)
    if base.audit(raw,cells)['passed']:
        return result(original,raw,cells,attempts,started,additionsOnlyFailure=False,retainedBaseline=False)
    if time.monotonic()<deadline-.10:
        prior=base.optimize(original,seconds=max(.10,deadline-time.monotonic()))
        attempts.append(dict(stage='audited_previous_optimizer_fallback',searchAttempts=prior['searchAttempts']))
        prior_check=base.audit(prior['bricks'],prior['targetCells'])
        if prior_check['passed'] and base.strict.m.repair_audit(original,prior['targetCells'],.02)['passed']:
            return result(original,prior['bricks'],prior['targetCells'],attempts,started,
                          additionsOnlyFailure=prior['additionsOnlyFailure'],
                          additionsOnlyEvidence=prior.get('additionsOnlyEvidence'),retainedBaseline=False)
    # A failed search remains a full-coverage failure, instead of an empty or
    # truncated MILP incumbent that conceals the input geometry in previews.
    return result(original,raw,cells,attempts,started,additionsOnlyFailure=True,
                  additionsOnlyEvidence=dict(bricks=raw,targetCells=cells.copy(),passed=False),retainedBaseline=False)
