"""Independent seam/anchor heuristics. No Ocean source or force solver."""


def edge(a,b):
    return (a,b) if a < b else (b,a)


def seam_metrics(brick,state):
    """Compare actual internal brick edges on the SAME XY projection.

    Outer silhouettes and empty cells are not seams. Ground is not a brick.
    Crossed lower seams are rewarded; coincident candidate edges are penalized.
    """
    own = {(x,y) for x,y,_ in brick.cells()}
    crossed,aligned = set(),set()
    support_owners = set()
    support_cells = []
    for p in own:
        owner = state.occupied.get((*p,brick.z-1))
        if owner is None:
            continue
        support_owners.add(owner)
        support_cells.append(p)
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            q=(p[0]+dx,p[1]+dy)
            other = state.occupied.get((*q,brick.z-1))
            if other is None or other == owner:
                continue
            (crossed if q in own else aligned).add(edge(p,q))
    center=(brick.x+(brick.h-1)/2,brick.y+(brick.w-1)/2)
    offset = 0.0
    if support_cells:
        support_center = (sum(p[0] for p in support_cells)/len(support_cells),
                          sum(p[1] for p in support_cells)/len(support_cells))
        offset = abs(center[0]-support_center[0])+abs(center[1]-support_center[1])
    return {'crossed_seams':len(crossed), 'aligned_seams':len(aligned),
            'support_bricks':len(support_owners),'support_center_offset':offset}


def preserves_support_anchors(brick,remaining,colors,state,scan_cap=256):
    """Safe necessary look-ahead: do not strand a same-color layer region.

    A region lacking ANY lower support cannot receive a legal same-color tile.
    Only regions adjacent to the removed tile can change. Large scans return
    'unknown/keep' at the cap, never falsely reject on truncated traversal.
    """
    if brick.z == 0:
        return True
    removed = set(brick.cells())
    roots = sorted({(x+dx,y+dy,z) for x,y,z in removed
                    for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))
                    if (x+dx,y+dy,z) in remaining and (x+dx,y+dy,z) not in removed})
    visited = set()
    for start in roots:
        if start in visited:
            continue
        stack=[start]
        region={start}
        has_anchor=False
        unknown=False
        while stack:
            x,y,z=stack.pop()
            if (x,y,z-1) in state.occupied:
                has_anchor=True
            if len(region) > scan_cap:
                unknown=True
                break
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                q=(x+dx,y+dy,z)
                if q in remaining and q not in removed and q not in region and colors[q]==colors[start]:
                    region.add(q)
                    stack.append(q)
        # Do not mark a truncated region visited: another boundary seed may
        # belong to a distinct unsupported branch beyond the incomplete scan.
        if not unknown:
            visited.update(region)
        if not has_anchor and not unknown:
            return False
    return True


def layout_metrics(state):
    """Global seams use brick IDs, not connected-component IDs."""
    aligned,crossed,comparable=0,0,0
    for (x,y,z),upper in state.occupied.items():
        if z == 0:
            continue
        lower=state.occupied.get((x,y,z-1))
        if lower is None:
            continue
        for dx,dy in ((1,0),(0,1)):
            upper_other=state.occupied.get((x+dx,y+dy,z))
            lower_other=state.occupied.get((x+dx,y+dy,z-1))
            if upper_other is None or lower_other is None or lower_other == lower:
                continue
            comparable+=1
            if upper_other == upper:
                crossed+=1
            else:
                aligned+=1
    return {'aligned_internal_seams':aligned,'crossed_internal_seams':crossed,
            'comparable_lower_seams':comparable,
            'aligned_seam_ratio':aligned/comparable if comparable else 0.0,
            'max_cantilever_distance':max((d for d in state.support_distances if d is not None),default=0),
            'mean_support_fraction':sum(state.support_fractions)/len(state.bricks) if state.bricks else 0.0,
            'brick_count':len(state.bricks), 'heuristic_only':True}


def solution_quality(state):
    metrics=layout_metrics(state)
    # All solutions must FIRST pass exact coverage + independent validation.
    # Prefer short cantilevers, fewer aligned joints, then fewer parts/support.
    return (-metrics['max_cantilever_distance'], -metrics['aligned_seam_ratio'],
            -metrics['brick_count'],metrics['mean_support_fraction'])
