"""Resume shape-preserving refinement of the delivered 260 A and 265 B models.

The archived single_stud_cover module is unavailable. This adapter implements
the documented exact cover and single real stud-component flow formulation.
Existing project parsers, exporters, and independent graph auditors are reused.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import time
import warnings

os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'brickmore48_tools/pipeline'))
sys.path.insert(0, str(ROOT / 'brickmore48_tools/analysis'))
import regenerate_review5 as review
from raw_failure_autopsy import brick_stud_components

VERSION = 'comparison_525_exact_cover_single_stud_flow_v1'
DEFAULT_OUT = ROOT / 'BrickMore_Comparision/BrickMore_refined_20261119'
SOURCES = (
    ROOT / 'Deploy/build/brickmore_A260_20261117/BrickMore_A260_20261117',
    ROOT / 'Deploy/build/comparison_20261116/BrickMoreComparison_20261116',
)
GEOMETRY_KEYS = ('h', 'w', 'x', 'y', 'z')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                    allow_nan=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def voxel_hash(cells):
    return hashlib.sha256(json.dumps(sorted(cells), separators=(',', ':')).encode()).hexdigest()


def normalize(bricks):
    """Match the original union_cells whitelist and 48-cube clipping policy."""
    original, cells = set(), set()
    dropped, clipped = [], []
    for index, brick in enumerate(bricks):
        occupied = review.footprint(brick)
        original.update(occupied)
        if (brick['h'], brick['w']) not in review.DIMS:
            dropped.append(index)
            continue
        retained = {p for p in occupied if all(0 <= coordinate < 48 for coordinate in p)}
        cells.update(retained)
        if not retained:
            dropped.append(index)
        elif retained != occupied:
            clipped.append(index)
    return cells, dict(original_voxels=len(original), target_voxels=len(cells),
        duplicate_cell_occupancies=sum(b['h'] * b['w'] for b in bricks) - len(original),
        dropped_brick_indices=dropped, clipped_brick_indices=clipped,
        removed_voxels=len(original - cells), added_voxels=len(cells - original),
        original_voxel_sha256=voxel_hash(original), target_voxel_sha256=voxel_hash(cells))


def voxel_components(cells):
    unseen = set(cells)
    components = []
    while unseen:
        pending = [unseen.pop()]
        size = 0
        while pending:
            x, y, z = pending.pop()
            size += 1
            for point in ((x-1,y,z), (x+1,y,z), (x,y-1,z),
                          (x,y+1,z), (x,y,z-1), (x,y,z+1)):
                if point in unseen:
                    unseen.remove(point)
                    pending.append(point)
        components.append(size)
    return sorted(components, reverse=True)


def independent_audit(bricks, cells):
    counts = Counter(point for brick in bricks for point in review.footprint(brick))
    actual = set(counts)
    components = len(brick_stud_components(bricks)) if bricks else 0
    report, _ = review.audit(bricks)
    good_dimensions = all((b['h'], b['w']) in review.DIMS for b in bricks)
    checks = dict(exact_coverage=actual == set(cells), no_overlaps=all(n == 1 for n in counts.values()),
        allowed_dimensions=good_dimensions, in_bounds=report['out_of_bounds_bricks'] == 0,
        one_stud_component=components == 1, graph_auditors_agree=components == report['stud_components'])
    return dict(passed=bool(bricks) and all(checks.values()), checks=checks,
        brick_count=len(bricks), voxels=len(actual), stud_components=components,
        missing_voxels=len(set(cells)-actual), added_voxels=len(actual-set(cells)),
        duplicate_cell_occupancies=sum(n-1 for n in counts.values()),
        unsupported_from_below=report['unsupported_from_below'],
        target_voxel_sha256=voxel_hash(cells), physical_stability_tested=False)


def solve(cells, seconds):
    """Select exact-cover bricks and connect their real vertical runs by flow.

    Consecutive cells in a vertical column are necessarily stud-connected under
    any exact cover. A selected horizontal brick connects the runs it spans.
    A single root supplies one unit to every other run. No floor union occurs.
    """
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import coo_matrix

    start = time.monotonic()
    labels = {}
    for point in sorted(cells):
        below = (point[0], point[1], point[2]-1)
        labels[point] = labels[below] if below in labels else len(set(labels.values()))
    run_count = len(set(labels.values()))
    if run_count == 1:
        chosen = [dict(h=1, w=1, x=x, y=y, z=z) for x, y, z in sorted(cells)]
        return chosen, dict(method='single_vertical_run', seconds=time.monotonic()-start)

    points = sorted(cells)
    point_index = {p:i for i,p in enumerate(points)}
    candidates = []
    cover = defaultdict(list)
    edges = defaultdict(set)
    for x, y, z in points:
        for h, w in review.DIMS:
            footprint = tuple((xx,yy,z) for xx in range(x,x+h) for yy in range(y,y+w))
            if not all(p in cells for p in footprint):
                continue
            if len(footprint) != len(cells) and not any(
                    (xx,yy,z+dz) in cells for xx,yy,_ in footprint for dz in (-1,1)):
                continue
            index = len(candidates)
            candidates.append(dict(h=h, w=w, x=x, y=y, z=z))
            for point in footprint:
                cover[point_index[point]].append(index)
            runs = sorted({labels[p] for p in footprint})
            for other in runs[1:]:
                edges[runs[0], other].add(index)

    n = len(candidates)
    edge_list = sorted(edges)
    variables = n + 2 * len(edge_list)
    info = dict(method='exact_cover_single_real_stud_run_flow', candidate_count=n,
                run_count=run_count, flow_edges=len(edge_list), budget_seconds=seconds)
    if len(cover) != len(cells):
        return None, dict(info, reason='cell_has_no_brick_with_a_real_vertical_contact',
                          seconds=time.monotonic()-start, certified_infeasible=True)
    root = max(Counter(labels.values()), key=Counter(labels.values()).get)
    row_indices, columns, values, lower, upper = [], [], [], [], []

    def add_row(terms, lo, hi):
        row_index = len(lower)
        for column, value in terms.items():
            row_indices.append(row_index)
            columns.append(column)
            values.append(value)
        lower.append(lo)
        upper.append(hi)

    for i in range(len(cells)):
        add_row({j:1. for j in cover[i]}, 1., 1.)
    balances = [defaultdict(float) for _ in range(run_count)]
    capacity = run_count - 1
    for k, (a, b) in enumerate(edge_list):
        forward, backward = n+2*k, n+2*k+1
        terms = {j:-float(capacity) for j in edges[a,b]}
        terms.update({forward:1., backward:1.})
        add_row(terms, -np.inf, 0.)
        balances[a][forward] -= 1.
        balances[a][backward] += 1.
        balances[b][forward] += 1.
        balances[b][backward] -= 1.
    for i, terms in enumerate(balances):
        demand = -float(capacity) if i == root else 1.
        add_row(terms, demand, demand)
    remaining = seconds - (time.monotonic()-start)
    if remaining <= 0:
        return None, dict(info, reason='matrix_budget_exhausted', seconds=time.monotonic()-start)
    matrix = coo_matrix((values, (row_indices,columns)), shape=(len(lower),variables)).tocsc()
    objective = np.zeros(variables)
    objective[:n] = 1.
    integer = np.zeros(variables)
    integer[:n] = 1.
    bounds_upper = np.full(variables, float(capacity))
    bounds_upper[:n] = 1.
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', message='Unrecognized options detected.*')
        result = milp(objective, integrality=integer, bounds=Bounds(0., bounds_upper),
            constraints=LinearConstraint(matrix, np.asarray(lower), np.asarray(upper)),
            options=dict(time_limit=remaining, mip_rel_gap=.08, threads=1))
    info.update(seconds=time.monotonic()-start, solver_status=int(result.status),
                solver_message=str(result.message), has_incumbent=result.x is not None,
                certified_infeasible=result.status == 2)
    if result.x is None:
        return None, info
    if not np.all(np.abs(result.x[:n]-np.round(result.x[:n])) < 1e-5):
        return None, dict(info, reason='fractional_incumbent')
    chosen = [candidates[i] for i in range(n) if result.x[i] > .5]
    chosen.sort(key=lambda b:tuple(b[k] for k in ('z','x','y','h','w')))
    if not independent_audit(chosen, cells)['passed']:
        return None, dict(info, reason='independent_audit_rejected')
    return chosen, info


def prepare(out):
    manifest = []
    counts = Counter()
    for source in SOURCES:
        for line in (source/'Data/manifest.jsonl').read_text(encoding='utf-8').splitlines():
            row = json.loads(line)
            if row['system'] != 'BrickMore':
                continue
            path = source / row['source_path']
            if sha(path) != row['source_sha256']:
                raise ValueError(f"Changed input: {row['prompt_id']}")
            bricks = review.assembly.parse_ldr(path.read_text(encoding='utf-8-sig'))
            if len(bricks) != row['part_count']:
                raise ValueError(f"Part count differs: {row['prompt_id']}")
            cells, normalization = normalize(bricks)
            source_audit = independent_audit(bricks, cells)
            components = voxel_components(cells)
            directory = out/'records'/row['prompt_id']
            directory.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, directory/'raw.ldr')
            dump(directory/'raw.json', dict(bricks=bricks, normalization=normalization,
                source_audit=source_audit, six_neighbor_component_sizes=components))
            entry = dict(row, absolute_source_path=str(path.resolve()),
                         normalized_target_sha256=voxel_hash(cells))
            manifest.append(entry)
            counts['already_single_stud_component' if source_audit['passed'] else 'requires_refinement'] += 1
            if len(components) != 1:
                counts['disconnected_target'] += 1
    if len(manifest) != 525 or Counter(r['batch'] for r in manifest) != {'A':260,'B':265}:
        raise ValueError('Expected exactly 260 A and 265 B models')
    if len({r['prompt_id'] for r in manifest}) != 525:
        raise ValueError('Duplicate prompt ID')
    dump(out/'input_manifest.json', manifest)
    dump(out/'input_summary.json', dict(total=525, counts=dict(counts)))
    dump(out/'provenance.json', dict(algorithm=VERSION, source_code_sha256=sha(__file__),
        reused_code_sha256={str(p.relative_to(ROOT)):sha(p) for p in (
            ROOT/'brickmore48_tools/pipeline/regenerate_review5.py',
            ROOT/'brickmore48_tools/analysis/raw_failure_autopsy.py',
            ROOT/'Train/algorithms/voxel_assembly_b/assembly_pipeline.py',
            ROOT/'Train/algorithms/voxel_assembly_b/toolkit_snapshot/voxel_assembly.py')},
        implementation_note='Archived single_stud_cover.py unavailable. Documented exact-cover/single-stud flow constraints reimplemented using vertical-run contraction, with existing independent project auditors.',
        regeneration=False, physical_stability_tested=False))
    return manifest


def process_one(job):
    out, row, tiers = job
    out = Path(out)
    pid = row['prompt_id']
    folder = out/'records'/pid
    raw = read(folder/'raw.json')
    bricks = raw['bricks']
    cells, normalization = normalize(bricks)
    started = time.monotonic()
    result = dict(prompt_id=pid, batch=row['batch'], category=row['category'], level=row['level'],
        caption=row['caption'], source_sha256=row['source_sha256'],
        original_geometry_valid=row.get('geometry_valid'),
        original_generation_complete=row.get('generation_complete'),
        raw_bricks=len(bricks), normalization=normalization, raw_audit=raw['source_audit'],
        attempts=[], physical_stability_tested=False)
    try:
        chosen = None
        if raw['source_audit']['passed']:
            chosen = [{k:b[k] for k in GEOMETRY_KEYS} for b in bricks]
            result['method'] = 'retained_original_already_single_stud_component'
        elif len(raw['six_neighbor_component_sizes']) != 1:
            result.update(status='infeasible_preserving_target',
                reason='Target has disconnected six-neighbor components; no exact-cover brick layout can join them.',
                component_sizes=raw['six_neighbor_component_sizes'])
        else:
            for budget in tiers:
                chosen, info = solve(cells, budget)
                result['attempts'].append(info)
                if chosen:
                    result['method'] = info['method']
                    break
                if info.get('certified_infeasible'):
                    break
        if chosen:
            review.export(folder, 'refined', chosen)
            text_bricks = [review.assembly.Placement.parse(line) for line in
                (folder/'refined.txt').read_text(encoding='utf-8').splitlines() if line.strip()]
            ldr_bricks = review.assembly.parse_ldr((folder/'refined.ldr').read_text(encoding='utf-8'))
            reference = [tuple(b[k] for k in GEOMETRY_KEYS) for b in chosen]
            if reference != [tuple(getattr(b,k) for k in GEOMETRY_KEYS) for b in text_bricks]:
                raise ValueError('TXT geometry readback failed')
            if reference != [tuple(b[k] for k in GEOMETRY_KEYS) for b in ldr_bricks]:
                raise ValueError('LDraw geometry readback failed')
            final = independent_audit(ldr_bricks, cells)
            if not final['passed']:
                raise ValueError('Independent exported geometry audit failed')
            destination = out/'refined_ldr'/f'{pid}.ldr'
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(folder/'refined.ldr', destination)
            result.update(status='passed', refined_bricks=len(chosen), validation=final,
                exact_target_preserved=True, original_voxel_union_preserved=normalization['removed_voxels']==0,
                output_sha256={name:sha(folder/name) for name in ('refined.ldr','refined.txt','refined.json')},
                ldr_path=destination.relative_to(out).as_posix())
        elif 'status' not in result:
            certified = any(x.get('certified_infeasible') for x in result['attempts'])
            result['status'] = 'infeasible_preserving_target' if certified else 'solver_budget_exhausted'
    except Exception as exc:
        result.update(status='error', error=f'{type(exc).__name__}: {exc}')
    result['elapsed_seconds'] = round(time.monotonic()-started, 3)
    dump(folder/'result.json', result)
    return result


def summarize(out, manifest, active=None, finished=False):
    results = []
    for row in manifest:
        path = out/'records'/row['prompt_id']/'result.json'
        if path.exists():
            results.append(read(path))
    counts = Counter(r['status'] for r in results)
    summary = dict(total=len(manifest), completed=len(results), finished=finished,
        status_counts=dict(counts), active=active or [],
        by_batch={b:dict(Counter(r['status'] for r in results if r['batch']==b)) for b in 'AB'},
        source_already_passed=sum(r['raw_audit']['passed'] for r in results),
        passed_with_clipped_target=sum(r['status']=='passed' and not r['original_voxel_union_preserved'] for r in results),
        physical_stability_tested=False)
    dump(out/'summary.json', summary)
    dump(out/'results.json', results)
    return summary


def verify(out, manifest):
    for row in manifest:
        pid = row['prompt_id']
        folder = out/'records'/pid
        result = read(folder/'result.json')
        if sha(row['absolute_source_path']) != row['source_sha256'] or sha(folder/'raw.ldr') != row['source_sha256']:
            raise ValueError(f'{pid}: input changed')
        if result['status'] != 'passed':
            continue
        for name, expected in result['output_sha256'].items():
            if sha(folder/name) != expected:
                raise ValueError(f'{pid}: output SHA differs')
        original = review.assembly.parse_ldr((folder/'raw.ldr').read_text(encoding='utf-8'))
        cells, _ = normalize(original)
        final = review.assembly.parse_ldr((out/result['ldr_path']).read_text(encoding='utf-8'))
        check = independent_audit(final, cells)
        if check != result['validation'] or not check['passed']:
            raise ValueError(f'{pid}: independent final audit failed')
    dump(out/'verification.json', dict(passed=True, checked_models=len(manifest),
                                      source_code_sha256=sha(__file__)))


def self_check():
    cases = [
        ({(0,0,0),(1,0,0)}, True),
        ({(0,0,0),(3,0,0)}, False),
        ({(0,0,0),(1,0,0),(0,0,1),(1,0,1)}, True),
        ({(0,0,0),(0,0,1),(1,0,1),(1,0,2)}, True),
    ]
    for cells, expected in cases:
        chosen, _ = solve(cells, 5)
        if bool(chosen) != expected:
            raise AssertionError('Single-component flow regression check failed')
        if chosen and not independent_audit(chosen,cells)['passed']:
            raise AssertionError('Independent check failed')
    print('FLOW_AND_AUDIT_CHECKS_PASSED', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare','run','verify','self-check'])
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--tiers', type=float, nargs='+', default=[12,60,180])
    parser.add_argument('--limit', type=int)
    parser.add_argument('--retry', nargs='*', default=[])
    args = parser.parse_args()
    if args.command == 'self-check':
        self_check()
        return
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    manifest = read(out/'input_manifest.json') if (out/'input_manifest.json').exists() else prepare(out)
    if args.command == 'prepare':
        print(json.dumps(read(out/'input_summary.json'),ensure_ascii=False),flush=True)
        return
    if args.command == 'verify':
        verify(out,manifest)
        print('ALL_OUTPUTS_VERIFIED',flush=True)
        return
    jobs = []
    for row in manifest:
        path = out/'records'/row['prompt_id']/'result.json'
        if not path.exists() or read(path)['status'] in args.retry:
            jobs.append(row)
    if args.limit:
        jobs = jobs[:args.limit]
    started = time.monotonic()
    print('START',len(jobs),'jobs','workers',args.workers,'tiers',args.tiers,flush=True)
    iterator = iter(jobs)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        active = {}
        for _ in range(args.workers):
            row = next(iterator,None)
            if row:
                active[pool.submit(process_one,(str(out),row,args.tiers))] = row['prompt_id']
        while active:
            ready, _ = wait(active,timeout=20,return_when=FIRST_COMPLETED)
            for future in ready:
                pid = active.pop(future)
                result = future.result()
                print('DONE',pid,result['status'],result.get('refined_bricks'),result['elapsed_seconds'],flush=True)
                row = next(iterator,None)
                if row:
                    active[pool.submit(process_one,(str(out),row,args.tiers))] = row['prompt_id']
            status = summarize(out,manifest,list(active.values()))
            print('PROGRESS',status['completed'],'/',len(manifest),status['status_counts'],
                  'active',list(active.values()),'elapsed_s',round(time.monotonic()-started),flush=True)
    summary = summarize(out,manifest,finished=not args.limit)
    if summary['completed'] == len(manifest):
        verify(out,manifest)
    print('FINISHED',json.dumps(summary,ensure_ascii=False),flush=True)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8',errors='replace')
    main()
