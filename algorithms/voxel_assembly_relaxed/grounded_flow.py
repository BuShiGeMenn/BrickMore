"""Exact monochrome cover with REAL vertical-run-to-ground reachability flow."""
from collections import defaultdict
import math
import time

import relaxed_core as r
q=r.q
VERSION='actual_stud_grounded_run_flow_v2_reduced_feasibility'


def solve(cells,seconds=4.):
    import numpy as np
    from scipy.optimize import Bounds,LinearConstraint,milp
    from scipy.sparse import coo_matrix
    import warnings
    started=time.monotonic();deadline=started+seconds
    remaining=set(cells);labels={};floor=set();count=0
    while remaining:
        p=min(remaining);remaining.remove(p);pending=[p];labels[p]=count
        while pending:
            p=pending.pop()
            if p[2]==0:floor.add(count)
            for dz in (-1,1):
                nxt=(p[0],p[1],p[2]+dz)
                if nxt in remaining:remaining.remove(nxt);labels[nxt]=count;pending.append(nxt)
        count+=1
    if not floor:return [],dict(reason='no_original_ground_contact',completeSearch=True,elapsedSeconds=time.monotonic()-started)
    original_run_count=count;original_floor_count=len(floor)
    # Grounded vertical runs need no connection to ONE ANOTHER. Collapsing their
    # reachability sources only shrinks this proof graph; physical components
    # remain separate in r.audit, which never unions the floor.
    remap={group:0 for group in floor}
    remap.update({group:i+1 for i,group in enumerate(g for g in range(count) if g not in floor)})
    labels={p:remap[group] for p,group in labels.items()};count=len(set(remap.values()));floor={0} if floor else set()
    candidates=[];cover=defaultdict(list);edges=defaultdict(set)
    for x,y,z in sorted(cells):
        if time.monotonic()>deadline:return [],dict(reason='candidate_enumeration_time_budget',completeSearch=False,elapsedSeconds=time.monotonic()-started)
        for h,w in q.a.dimensions_for_library('extended'):
            footprint=tuple((xx,yy,z) for xx in range(x,x+h) for yy in range(y,y+w))
            if not all(p in cells and cells[p]==cells[(x,y,z)] for p in footprint):continue
            if z and not any((p[0],p[1],z-1) in cells or (p[0],p[1],z+1) in cells for p in footprint):continue
            groups=sorted({labels[p] for p in footprint})
            # A brick only between already-grounded runs can be replaced with
            # 1x1 columns without losing ANY required reachability or coverage.
            if h*w>1 and groups==[0]:continue
            i=len(candidates);candidates.append(dict(h=h,w=w,x=x,y=y,z=z,color=cells[(x,y,z)]))
            for p in footprint:cover[p].append(i)
            # Every covered run is connected through this ONE real brick. A star
            # is an exact connectivity representation, not a fictitious side stud.
            for other in groups[1:]:edges[(groups[0],other)].add(i)
    def fail(reason):return [],dict(reason=reason,completeSearch=False,candidateCount=len(candidates),verticalRunCount=count,
                                   groundedRunCount=len(floor),elapsedSeconds=time.monotonic()-started,algorithmVersion=VERSION)
    if not floor or any(p not in cover for p in cells):return fail('no_ground_or_uncoverable_original_cell')
    n=len(candidates);edge_list=sorted(edges);sources=sorted(floor);variables=n+2*len(edge_list)+len(sources)
    ri=[];ci=[];data=[];lo=[];hi=[]
    def row(terms,lower,upper):
        index=len(lo)
        for j,value in terms.items():
            if value:ri.append(index);ci.append(j);data.append(value)
        lo.append(lower);hi.append(upper)
    for p in sorted(cells):row({i:1 for i in cover[p]},1,1)
    balances=[defaultdict(float) for _ in range(count)]
    for k,(a,b) in enumerate(edge_list):
        ab=n+2*k;ba=ab+1
        terms={i:-count for i in edges[(a,b)]};terms[ab]=1;terms[ba]=1
        row(terms,-np.inf,0)
        balances[a][ab]-=1;balances[a][ba]+=1;balances[b][ab]+=1;balances[b][ba]-=1
    for k,group in enumerate(sources):balances[group][n+2*len(edge_list)+k]+=1
    for group,balance in enumerate(balances):row(balance,0 if group in floor else 1,0 if group in floor else 1)
    remaining_seconds=deadline-time.monotonic()
    if remaining_seconds<=0:return fail('flow_matrix_time_budget')
    matrix=coo_matrix((data,(ri,ci)),shape=(len(lo),variables)).tocsc()
    objective=np.zeros(variables)  # seek a valid assembly, not an optimal brick count
    integrality=np.zeros(variables);integrality[:n]=1
    upper=np.ones(variables)*count;upper[:n]=1
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore',message='Unrecognized options detected.*threads.*')
        result=milp(objective,integrality=integrality,bounds=Bounds(0,upper),
                    constraints=LinearConstraint(matrix,np.array(lo),np.array(hi)),
                    options={'time_limit':remaining_seconds,'mip_rel_gap':.5,'threads':1})
    if result.x is None:return fail('bounded_ground_flow_no_incumbent')
    if not np.all(np.abs(result.x[:n]-np.round(result.x[:n]))<1e-5):return fail('noninteger_cover_rejected')
    raw=[candidates[i] for i in range(n) if result.x[i]>.5];raw.sort(key=lambda b:(b['z'],b['x'],b['y'],b['h'],b['w']))
    if not r.audit(raw,cells)['passed']:return fail('independent_grounded_geometry_rejected')
    return raw,dict(reason='independent_grounded_geometry_passed',completeSearch=False,candidateCount=n,
                    verticalRunCount=original_run_count,groundedRunCount=original_floor_count,solverStatus=int(result.status),
                    elapsedSeconds=time.monotonic()-started,algorithmVersion=VERSION,
                    floorSourcesAreReachabilityOnlyNotPhysicalConnections=True)
