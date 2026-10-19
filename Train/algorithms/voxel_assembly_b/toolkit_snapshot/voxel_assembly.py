"""Bounded exact-shape, exact-color voxel tiling with per-brick validation."""
from collections import Counter
from dataclasses import asdict
import hashlib
import heapq
import json
import math
import random
import time
from optimized_geometry import GeometryConfig, GeometryState, Placement, completion_check
from brick_catalog import EXTENDED_PARTS
from interlocking import seam_metrics, preserves_support_anchors, layout_metrics, solution_quality

PARTS = EXTENDED_PARTS
ALGORITHM_VERSION = 'exact_interlocking_v2'


def audit_bricks(bricks, cfg=None, caption='', require_shape=False):
    cfg = cfg or GeometryConfig(world_dim=128, min_bricks=1)
    state = GeometryState(cfg)
    issues = []
    for index, b in enumerate(bricks):
        if any(type(getattr(b, k, None)) is not int for k in ('h','w','x','y','z')):
            issues.append({'index':index, 'reason':'non_integer_brick'})
            continue
        reason = state.check(b)
        if reason != 'success':
            issues.append({'index':index, 'reason':reason})
        try:
            state.add(b, enforce_policy=False)
        except ValueError:
            pass
    check = completion_check(state, caption, require_shape)
    check.update(prefix_issues=issues, collision_free=not any(i['reason']=='collision' for i in issues),
                 format_valid=not any(i['reason'] in ('non_integer_brick','not_in_library','out_of_bounds') for i in issues))
    check['pass'] = check['pass'] and not issues
    return check


def candidate_tiles(state, remaining, colors, rng, limit, stats=None):
    z = min(p[2] for p in remaining)
    layer = [p for p in remaining if p[2] == z]
    # Unsupported cells first: they must be covered by a brick reaching an anchor.
    # Taking all anchors with smaller bricks first can strand a cantilever.
    anchor = min(layer, key=lambda p: (
        (p[0],p[1],z-1) in state.occupied,
        sum((p[0]+dx,p[1]+dy,z) in remaining for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))), p))
    choices = []
    for h,w in state.cfg.dimensions:
        for dx in range(h):
            for dy in range(w):
                b = Placement(h,w,anchor[0]-dx,anchor[1]-dy,z)
                cells = tuple(b.cells())
                if not all(p in remaining and colors[p] == colors[anchor] for p in cells):
                    continue
                reason = state.check(b)
                if reason != 'success':
                    if stats is not None:
                        stats['rejected:'+reason] += 1
                    continue
                if not preserves_support_anchors(b,remaining,colors,state):
                    if stats is not None:
                        stats['anchor_preservation_pruned'] += 1
                    continue
                support, neighbours = state.contact(b)
                roots = {state.find(i) for i in neighbours}
                seams = seam_metrics(b,state)
                distance = state.support_distance(b)
                score = (max(0,len(roots)-1)*100 + h*w*2 + support*2
                         + seams['crossed_seams']*4 - seams['aligned_seams']*3
                         + max(0,seams['support_bricks']-1)*2
                         - seams['support_center_offset'] - (distance or 0)*.5
                         + .2 * ((h>w) == (z%2 == 0)) + rng.random()*.01)
                choices.append((score,b,cells,seams,support,distance or 0))
    if stats is not None:
        stats['legal_candidate_tiles'] += len(choices)
    ranked = sorted(choices,key=lambda item:item[0],reverse=True)
    # Diverse candidate portfolio: structural, seam-crossing, well-supported,
    # medium and detail parts. Do not fill a beam with near-identical big bricks.
    selected=[]
    seen=set()
    def add(item):
        if item is not None and item[1] not in seen and len(selected)<limit:
            selected.append(item[:3])
            seen.add(item[1])
    for item in ranked[:2]:
        add(item)
    if choices:
        add(max(choices,key=lambda item:(item[3]['crossed_seams'],-item[3]['aligned_seams'],item[0])))
        add(max(choices,key=lambda item:(item[4],-item[5],item[0])))
        medium=[item for item in choices if 2 <= len(item[2]) <= 6]
        if medium:
            add(max(medium,key=lambda item:item[0]))
        add(min(choices,key=lambda item:(len(item[2]),-item[0])))
    for item in ranked:
        add(item)
    return selected


def assemble(model, cfg=None, max_nodes=4000, beam_width=12, branching=6, seed=42,
             caption='', require_shape=False, static_validator=None,
             solution_limit=3, improve_nodes=128, max_seconds=30):
    """No added/deleted/recolored voxels. Failed searches return labelled drafts.

    Geometry callbacks are invoked before EVERY commit. A supplied static
    validator is also invoked before each commit and on the final structure.
    Callback failure/exception cannot silently become a geometry-only success.
    The bounded search is not complete: exhausted search != impossible geometry.
    """
    cfg = cfg or GeometryConfig(world_dim=128, min_bricks=1, max_cantilever_distance=2)
    if any(type(v) is not int for v in (max_nodes,beam_width,branching,solution_limit,improve_nodes)):
        raise ValueError('search counts must be integers')
    if min(max_nodes,beam_width,branching,solution_limit) < 1 or improve_nodes < 0:
        raise ValueError('positive search budgets required')
    if not isinstance(max_seconds,(int,float)) or not math.isfinite(max_seconds) or max_seconds<=0:
        raise ValueError('max_seconds must be positive and finite')
    if not cfg.bottom_up or not cfg.require_lower_support:
        raise ValueError('exact tiler requires bottom_up and lower_support policies')
    model = model.normalized(False, cfg.world_dim)
    rng = random.Random(seed)
    state = GeometryState(cfg)
    # Same-layer brick permutations have identical geometric futures. Keep their
    # distinct order only when an external validator could be order-dependent.
    def layout_key(s):
        return tuple(s.bricks) if static_validator is not None else frozenset(s.bricks)
    queue = [(len(model.cells),0,0,state,set(model.cells),layout_key(state))]
    component_debt_weight=max(h*w for h,w in cfg.dimensions)
    best, best_remaining = state, set(model.cells)
    visited,queued = set(),{layout_key(state)}
    nodes, serial, static_calls = 0,0,0
    solutions,first_solution_node,selected_quality = 0,None,None
    stats=Counter()
    stop='search_exhausted'
    started=time.monotonic()
    deadline=started+max_seconds
    while queue and nodes < max_nodes:
        if time.monotonic()>=deadline:
            stop='time_budget'
            break
        if first_solution_node is not None and nodes >= first_solution_node+improve_nodes:
            stop='improvement_budget'
            break
        _,_,_,current,remaining,fingerprint = heapq.heappop(queue)
        queued.discard(fingerprint)
        if fingerprint in visited:
            continue
        visited.add(fingerprint)
        nodes += 1
        check = completion_check(current,caption,require_shape)
        if not solutions and (len(remaining)<len(best_remaining) or (
                len(remaining)==len(best_remaining) and current.components<best.components)):
            best,best_remaining=current,remaining
        if not remaining:
            if check['pass']:
                if static_validator is not None:
                    static_calls += 1
                    if not static_validator(tuple(current.bricks)):
                        continue
                # Only independently validated candidates enter solution ranking.
                audited = audit_bricks(current.bricks,cfg,caption,require_shape)
                if not audited['pass']:
                    stats['independent_audit_rejections']+=1
                    continue
                solutions+=1
                if first_solution_node is None:
                    first_solution_node=nodes
                quality=solution_quality(current)
                if selected_quality is None or quality>selected_quality:
                    best,best_remaining,selected_quality=current,remaining,quality
                if solutions>=solution_limit:
                    stop='solution_limit'
                    break
            continue
        for _,b,cells in candidate_tiles(current,remaining,model.cells,rng,branching,stats):
            if time.monotonic()>=deadline:
                stop='time_budget'
                break
            child = current.clone()
            child.add(b)  # Independent check before ANY candidate is committed.
            child_key=layout_key(child)
            if child_key in visited or child_key in queued:
                stats['duplicate_layouts_pruned']+=1
                continue
            if static_validator is not None:
                static_calls += 1
                if not static_validator(tuple(current.bricks)+(b,)):
                    stats['static_rejections']+=1
                    continue
            uncovered = remaining.difference(cells)
            if not solutions and (len(uncovered)<len(best_remaining) or (
                    len(uncovered)==len(best_remaining) and child.components<best.components)):
                best,best_remaining=child,uncovered
            # A finished disconnected tiling has no future additions. Keep it
            # as a labelled draft, but do not let it evict reparable prefixes.
            if not uncovered and not completion_check(child,caption,require_shape)['pass']:
                stats['completed_drafts_pruned']+=1
                continue
            serial += 1
            priority=len(uncovered)+max(0,child.components-1)*component_debt_weight
            heapq.heappush(queue,(priority,child.components,serial,child,uncovered,child_key))
            queued.add(child_key)
        if len(queue) > beam_width:
            queue = heapq.nsmallest(beam_width,queue)
            heapq.heapify(queue)
            queued={item[5] for item in queue}
    if nodes>=max_nodes:
        stop='node_budget'
    # Independent audit of the selected output, not the candidate score.
    final = audit_bricks(best.bricks,cfg,caption,require_shape)
    output_cells = {p for b in best.bricks for p in b.cells()}
    missing = set(model.cells)-output_cells
    extra = output_cells-set(model.cells)
    recolored=sum(model.cells[p] != model.cells[(b.x,b.y,b.z)]
                  for b in best.bricks for p in b.cells())
    success = solutions>0 and final['pass'] and not missing and not extra and recolored==0
    return {'status':'success' if success else 'draft', 'termination':'complete' if success else stop,
            'algorithm_version':ALGORITHM_VERSION,'search_stop':stop,
            'bricks':[asdict(b) for b in best.bricks], 'validation':final,
            'input_voxels':len(model.cells), 'output_voxels':len(output_cells),
            'missing_voxels':len(missing), 'added_voxels':len(extra), 'recolored_voxels':recolored,
            'exact_coverage':not missing and not extra, 'color_preserved':recolored==0,
            'layout_quality':layout_metrics(best), 'solutions_compared':solutions,
            'search_stats':dict(stats), 'search_seconds':time.monotonic()-started,
            'input_voxel_sha256':hashlib.sha256(json.dumps(sorted(model.cells.items())).encode()).hexdigest(),
            'search_config':{'max_nodes':max_nodes,'beam_width':beam_width,'branching':branching,
                             'solution_limit':solution_limit,'improve_nodes':improve_nodes,'max_seconds':max_seconds,
                             'frontier_priority':'coverage_plus_component_debt'},
            'nodes':nodes, 'seed':seed, 'static_solver_calls':static_calls,
            'static_verified':True if success and static_validator is not None else None,
            'full_physics':bool(success and static_validator is not None), 'semantic_verified':False,
            'metadata':model.metadata, 'config':asdict(cfg)}


def to_ldr(result, cells):
    """Standard BrickGPT/extended parts, stud=20 / brick-height=24 LDraw units."""
    lines = ['0 Model-independent voxel assembly',f"0 STATUS {result['status']}",
             '0 Geometry validation is not static or semantic proof.']
    for raw in result['bricks']:
        b = Placement(**raw)
        part = PARTS[tuple(sorted((b.h,b.w)))]
        c = cells[(b.x,b.y,b.z)]
        color = f'0x2{c:06X}'
        matrix = '0 0 1 0 1 0 -1 0 0' if b.h <= b.w else '-1 0 0 0 1 0 0 0 -1'
        lines.append(f'1 {color} {(b.x+b.h*.5)*20:g} {-b.z*24:g} {(b.y+b.w*.5)*20:g} {matrix} {part}')
        lines.append('0 STEP')
    return '\n'.join(lines)+'\n'
