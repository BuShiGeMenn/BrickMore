"""Deletion fallback: joint bricks/additions/deletions within one original budget."""
from collections import defaultdict
import math
from pathlib import Path
import sys
import time

import mixed_quality as m
q=m.q

VERSION = 'joint_mixed_detail_cover_q4_v2'


def candidates(original, ratio=.02, seconds=10, maximum=40000):
    """Enumerate real catalog rectangles, never remove/recolor original cells.

    Every catalog shape may use up to the full repair budget, including blank
    local support rectangles. Time/candidate limits still make this a bounded
    solver; a rejected or timed out MILP is NOT a general impossibility proof.
    """
    deadline=time.monotonic()+seconds; cap=q.budget_for(len(original),ratio)
    optional=q.allowed_additions(original) if cap else set()
    space=set(original)|optional; rows=[]; truncated=False
    for x,y,z in sorted(space,key=lambda p:(p[2],p[0],p[1])):
        if time.monotonic()>=deadline:truncated=True; break
        for h,w in q.a.dimensions_for_library(q.POLICY['brick_library']):
            footprint=tuple(q.a.Placement(h,w,x,y,z).cells())
            if not all(p in space for p in footprint):continue
            missing=tuple(p for p in footprint if p not in original)
            if len(missing)>cap:continue
            colors={original[p] for p in footprint if p in original}
            if len(colors)>1:continue
            if not colors:
                colors={original[n] for p in footprint for n in q.neighbours(p) if n in original}
            lower=tuple((p[0],p[1],z-1) for p in footprint if (p[0],p[1],z-1) in space)
            if z and len(lower)<math.ceil(h*w*q.POLICY['min_support_fraction']):continue
            if z and any(not any(abs(p[0]-s[0])+abs(p[1]-s[1])<=q.POLICY['max_cantilever_distance'] for s in lower) for p in footprint):continue
            for color in sorted(colors):
                rows.append((dict(h=h,w=w,x=x,y=y,z=z,color=color),footprint,missing,lower))
            if len(rows)>=maximum:truncated=True; break
        if truncated:break
    return rows,optional,truncated


def solve(original, ratio=.02, seconds=30, candidate_limit=40000, cut_rounds=8,
          preferred=None,physics_accept=None,additions_only_failure=None):
    """Protected source cover + shared edit budget + dynamic real stud support.

    Adds connectivity cuts only after checking an actual integer solution.
    Deleted lower voxels are NOT fixed support. Existing prefix policy is checked.
    Solver status
    alone NEVER earns success. HiGHS uses one worker to avoid batch oversubscription.
    """
    import numpy as np
    import scipy
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import coo_matrix
    if not isinstance(additions_only_failure,dict) or additions_only_failure.get('geometryPassed') is not False:
        raise ValueError('mixed fallback requires a recorded additions-only failure')
    if not math.isfinite(seconds) or seconds<=0 or candidate_limit<1 or cut_rounds<1:raise ValueError('invalid solver budgets')
    started=time.monotonic(); deadline=started+seconds
    eligible=m.deletion_eligibility(original,ratio)
    rows,optional,truncated=candidates(original,ratio,min(10,seconds*.4),candidate_limit)
    cover=defaultdict(list)
    for i,(_,footprint,_,_) in enumerate(rows):
        for p in footprint:cover[p].append(i)
    stats={'candidateCount':len(rows),'candidateEnumerationTruncated':truncated,
           'solver':'scipy.optimize.milp/HiGHS','scipyVersion':scipy.__version__,
           'connectivityCuts':0,'integerSolutionsAudited':0,'candidateMissingCellLimit':'full_budget_and_catalog',
           'physicsFeedbackRejections':0,'eligibleDeletionCount':len(eligible),
           'additionsOnlyFailure':additions_only_failure}
    def result(raw,target,reason):
        return raw,target,dict(stats,termination=reason,elapsedSeconds=time.monotonic()-started,
                               completeSearch=False,algorithmVersion=VERSION)
    if not original or any(p not in cover and p not in eligible for p in original):return result([],original.copy(),'protected_candidate_coverage_missing')
    deleted_variables={p:len(rows)+i for i,p in enumerate(sorted(eligible))}
    variable_count=len(rows)+len(deleted_variables)
    ri=[]; ci=[]; data=[]; lo=[]; hi=[]
    def constraint(terms,lower=-np.inf,upper=np.inf):
        index=len(lo)
        for j,v in terms.items():
            if v:ri.append(index); ci.append(j); data.append(v)
        lo.append(lower); hi.append(upper)
    for p in sorted(set(cover)|set(original)):
        terms={i:1 for i in cover.get(p,())}
        if p in deleted_variables:terms[deleted_variables[p]]=1
        constraint(terms,1 if p in original else 0,1)
    budget={i:len(row[2]) for i,row in enumerate(rows)}
    budget.update({i:1 for i in deleted_variables.values()})
    constraint(budget,0,q.budget_for(len(original),ratio))
    def support_row(i,positions,required):
        fixed=sum(p in original and p not in eligible for p in positions)
        if fixed>=required:return
        terms=defaultdict(float); terms[i]-=required-fixed
        deletable_count=0
        for p in positions:
            if p in eligible:
                # cover(original p) == 1 - deleted(p). This is algebraically
                # identical to summing thousands of candidate cover columns,
                # but much sparser. When p is deleted its support is still ZERO.
                terms[deleted_variables[p]]-=1;deletable_count+=1
            elif p not in original:
                for j in cover.get(p,()):terms[j]+=1
        constraint(terms,-deletable_count)
    for i,(b,footprint,_,lower) in enumerate(rows):
        if not b['z']:continue
        support_row(i,lower,math.ceil(len(footprint)*q.POLICY['min_support_fraction']))
        for p in footprint:
            nearby=[s for s in lower if abs(p[0]-s[0])+abs(p[1]-s[1])<=q.POLICY['max_cantilever_distance']]
            support_row(i,nearby,1)
    def shape_penalty(row):
        b,footprint,_,lower=row
        if not b['z']:return 0
        fixed=[p for p in lower if p in original]
        if not fixed:return 2
        cx=b['x']+b['h']/2;cy=b['y']+b['w']/2
        # Only a candidate ranking heuristic, NEVER a physical pass predicate.
        dx=max(min(p[0]+.25 for p in fixed)-cx,0,cx-max(p[0]+.75 for p in fixed))
        dy=max(min(p[1]+.25 for p in fixed)-cy,0,cy-max(p[1]+.75 for p in fixed))
        return 2*(dx+dy)
    objective=np.array([1000*len(row[2])+1+shape_penalty(row)+.001*(i%97)/97 for i,row in enumerate(rows)]+[1200.]*len(deleted_variables),dtype=float)
    # A preferred layout is a tie-breaker, never a frozen solution or waived constraint.
    keys={tuple(b[k] for k in ('h','w','x','y','z','color')) for b in preferred or ()}
    for i,(b,_,_,_) in enumerate(rows):
        if tuple(b[k] for k in ('h','w','x','y','z','color')) in keys:objective[i]-=.05
    best=[]; best_target=original.copy()
    for _ in range(cut_rounds):
        remaining=deadline-time.monotonic()
        if remaining<=0:return result(best,best_target,'time_budget')
        matrix=coo_matrix((data,(ri,ci)),shape=(len(lo),variable_count)).tocsc()
        # SciPy passes threads through to HiGHS; explicitly suppress only that documented warning.
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore',message='Unrecognized options detected.*threads.*')
            solved=milp(objective,integrality=np.ones(variable_count),bounds=Bounds(0,1),
                        constraints=LinearConstraint(matrix,np.array(lo),np.array(hi)),
                        options={'time_limit':remaining,'mip_rel_gap':.01,'threads':1})
        stats['lastSolverStatus']=int(solved.status)
        if solved.x is None:return result(best,best_target,'restricted_candidates_no_incumbent')
        if not np.all(np.abs(solved.x-np.round(solved.x))<1e-5):return result(best,best_target,'noninteger_incumbent_rejected')
        selected=[i for i,v in enumerate(solved.x[:len(rows)]) if v>.5]
        raw=[rows[i][0] for i in selected]; raw.sort(key=lambda b:(b['z'],b['x'],b['y'],b['h'],b['w']))
        target={p:b['color'] for b in raw for p in q.a.Placement(**{k:b[k] for k in ('h','w','x','y','z')}).cells()}
        audit=q.independent_audit(raw,target); repair=m.repair_audit(original,target,ratio)
        stats['integerSolutionsAudited']+=1
        if repair['passed'] and audit['passed']:
            best,best_target=raw,target
            if physics_accept is None or physics_accept(raw,target):return result(raw,target,'independent_geometry_passed')
            stats['physicsFeedbackRejections']+=1
            constraint({i:1 for i in selected},upper=len(selected)-1)
            continue
        if repair['passed'] and not q.independent_audit(best,best_target)['passed']:best,best_target=raw,target
        if not repair['passed']:return result([],original.copy(),'incumbent_quality_rejected')
        labels=q.brick_component_labels(raw)
        groups=defaultdict(set)
        for i in selected:groups[labels[rows[i][1][0]]].add(i)
        if len(groups)>1:
            for ids in groups.values():
                adjacent=set()
                for i in ids:
                    for x,y,z in rows[i][1]:
                        for p in ((x,y,z-1),(x,y,z+1)):
                            adjacent.update(cover.get(p,()))
                adjacent-=ids
                # If all these bricks stay selected, at least one REAL vertical
                # neighbor must be selected. Overlapping alternatives cannot
                # falsely connect because the cover constraints prohibit overlap.
                terms={i:1 for i in ids}; terms.update({i:-1 for i in adjacent})
                constraint(terms,upper=len(ids)-1); stats['connectivityCuts']+=1
        else:
            # Prefix-policy failure: forbid only this layout, not its geometry.
            constraint({i:1 for i in selected},upper=len(selected)-1)
    return result(best,best_target,'bounded_cut_or_physics_feedback_budget')
