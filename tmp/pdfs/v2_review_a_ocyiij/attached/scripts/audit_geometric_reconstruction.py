#!/usr/bin/env python3
"""Audit exported rectangular bricks; no solver-success or physical-stability inference.

Uses only Python's standard library and the bundled, hash-verified assemblies.
LDraw coordinates: 20 LDU stud pitch, 24 LDU brick height, upright Y-down.
"""
import collections
import csv
import gzip
import hashlib
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/reconstruction'
FOOTPRINTS = {'2456': (6, 2), '3001': (4, 2), '3002': (3, 2),
              '3003': (2, 2), '3004': (2, 1), '3005': (1, 1),
              '3007': (8, 2), '3008': (8, 1), '3009': (6, 1),
              '3010': (4, 1), '3622': (3, 1)}
TOL = 5e-4

def component_sizes(n, edges):
    parent = list(range(n))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i, j in edges:
        a, b = find(i), find(j)
        parent[b] = a
    return sorted(collections.Counter(find(i) for i in range(n)).values(), reverse=True)

def audit(row):
    raw = gzip.decompress((DATA / 'assemblies' / (row['sample_id'] + '.json.gz')).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == row['assembly_sha256']
    assembly = json.loads(raw)
    bounds = []
    for part in assembly['instances']:
        m = part['matrix_ldu']
        r = [[round(v) for v in line[:3]] for line in m[:3]]
        assert max(abs(m[i][j] - r[i][j]) for i in range(3) for j in range(3)) < TOL
        assert r[1] == [0, 1, 0] and r[0][1] == r[2][1] == 0
        assert all(sum(abs(v) for v in line) == 1 for line in r)
        assert all(sum(abs(r[i][j]) for i in range(3)) == 1 for j in range(3))
        nx, nz = FOOTPRINTS[part['part_stem']]
        sx = abs(r[0][0]) * nx + abs(r[0][2]) * nz
        sz = abs(r[2][0]) * nx + abs(r[2][2]) * nz
        bounds.append((m[0][3] - sx * 10, m[2][3] - sz * 10, m[1][3], sx, sz))
    assert len(bounds) == row['part_count']
    ox, oz = min(b[0] for b in bounds), min(b[1] for b in bounds)
    yt = max(b[2] for b in bounds)
    owner, rects, error = collections.defaultdict(list), [], 0.0
    for i, (x, z, y, sx, sz) in enumerate(bounds):
        grid = ((x - ox) / 20, (z - oz) / 20, (yt - y) / 24)
        residual = max(abs(v - round(v)) for v in grid)
        assert residual < TOL, (row['sample_id'], residual)
        error = max(error, residual)
        x, z, h = map(round, grid)
        rects.append((x, z, h, sx, sz))
        for xx in range(x, x + sx):
            for zz in range(z, z + sz):
                owner[xx, zz, h].append(i)
    edges = [(i, j) for (x, z, h), ids in owner.items()
             for i in ids for j in owner.get((x, z, h + 1), [])]
    sizes = component_sizes(len(bounds), edges)
    # Independent pairwise rectangle intersection check of the same contact rule.
    other_edges = []
    for i, (x, z, h, sx, sz) in enumerate(rects):
        for j, (X, Z, H, SX, SZ) in enumerate(rects[:i]):
            if abs(h-H) == 1 and min(x+sx, X+SX) > max(x, X) and min(z+sz, Z+SZ) > max(z, Z):
                other_edges.append((i, j))
    assert sizes == component_sizes(len(bounds), other_edges)
    result = {k: row[k] for k in ('sample_id', 'model_id', 'prompt_id', 'level', 'variant', 'primary')}
    result.update(parts=len(bounds), occupied_cells=len(owner),
                  overlapping_cells=sum(len(v) > 1 for v in owner.values()),
                  stud_components=len(sizes), component_sizes=sizes,
                  origin_ldu=[ox, oz, -yt-24], max_lattice_residual=error)
    return result, set(owner)

def write_csv(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def main():
    rows = [json.loads(line) for line in (DATA / 'inputs/selected_manifest.jsonl').read_text().splitlines()]
    rows = [r for r in rows if r['system'] == 'BrickMore']
    models, cells = {}, {}
    for r in rows:
        models[r['sample_id']], cells[r['sample_id']] = audit(r)
    pairs = []
    for row in rows:
        if not row['primary'] or row['variant'] != 'stitched':
            continue
        sid = row['sample_id']; rid = sid.rsplit('__', 1)[0] + '__raw'
        source = next(r for r in rows if r['sample_id'] == rid)
        assert source['caption'] == row['caption'] and source['prompt_id'] == row['prompt_id']
        a, b = models[rid], models[sid]
        pairs.append(dict(model_id=row['model_id'], prompt_id=row['prompt_id'], level=row['level'],
                          raw_sample_id=rid, retiled_sample_id=sid,
                          raw_stud_components=a['stud_components'], retiled_stud_components=b['stud_components'],
                          raw_overlapping_cells=a['overlapping_cells'], retiled_overlapping_cells=b['overlapping_cells'],
                          raw_occupied_cells=a['occupied_cells'], retiled_occupied_cells=b['occupied_cells'],
                          raw_parts=a['parts'], retiled_parts=b['parts'],
                          translation_normalized_union_equal=cells[rid] == cells[sid],
                          export_origin_delta_ldu=[b['origin_ldu'][i]-a['origin_ldu'][i] for i in range(3)]))
    extra = [models[r['sample_id']] for r in rows if r['primary'] and r['variant'] == 'raw']
    logs = []
    for path in sorted((DATA / 'inputs').glob('manifest_w*.json')):
        for entry in json.loads(path.read_text()):
            logs.append((path.name, entry))
    joins = []
    for p in pairs:
        row = next(r for r in rows if r['sample_id'] == p['retiled_sample_id'])
        matches = [(name, e) for name, e in logs
                   if f"{e['category']}-L{e['level']}V{e['variant']}" == p['model_id']
                   and e['prompt'] == row['caption']
                   and e.get('raw_bricks') == p['raw_parts']
                   and e.get('assembly_bricks') == p['retiled_parts']]
        joins.append(dict(model_id=p['model_id'], strict_match_count=len(matches),
                          source_logs=[name for name, e in matches],
                          budget_tiers=[e.get('solver_tier') for name, e in matches]))
    collision = {r['sample_id']: r for r in (json.loads(s) for s in
                 (DATA / 'inputs/collision_journal.jsonl').read_text().splitlines())}
    collision_check = []
    for p in pairs:
        for variant in ('raw', 'retiled'):
            sid = p[variant+'_sample_id']
            collision_check.append(dict(sample_id=sid,
                 body_overlap=p[variant+'_overlapping_cells'] > 0,
                 source_invalid_placements=collision[sid]['invalid_placements']))
    (DATA / 'log_coverage.json').write_text(json.dumps(dict(
        historical_batch_records=len(logs), strict_matches=sum(j['strict_match_count']==1 for j in joins),
        join_rule='ID + exact caption + raw part count + retiled part count; not cryptographic lineage.',
        warning='Budget tiers are not solver elapsed times. Batch-wide seconds include other work; no solver-only latency reported.',
        joins=joins, collision_crosscheck=collision_check), indent=2)+'\n')
    summary = dict(repository='BuShiGeMenn/BrickMore', commit='dfe1c94fc86b722247ed5c8208011313f535c5ec',
                   source_archive='Deploy/brickmore-three-models-four-scores-20261110.tar.gz',
                   source_archive_sha256='1ff8858172a9a855ba4cf98be06b88dcebe0d2301979ca33a6b5020aa1dcb575',
                   assemblies_verified=len(models), paired_outputs=len(pairs), primary_raw_only=len(extra),
                   raw_single_stud_component=sum(p['raw_stud_components']==1 for p in pairs),
                   retiled_single_stud_component=sum(p['retiled_stud_components']==1 for p in pairs),
                   raw_mean_stud_components=statistics.mean(p['raw_stud_components'] for p in pairs),
                   retiled_mean_stud_components=statistics.mean(p['retiled_stud_components'] for p in pairs),
                   raw_overlap_free=sum(p['raw_overlapping_cells']==0 for p in pairs),
                   retiled_overlap_free=sum(p['retiled_overlapping_cells']==0 for p in pairs),
                   translation_normalized_union_equal=sum(p['translation_normalized_union_equal'] for p in pairs),
                   max_lattice_residual=max(m['max_lattice_residual'] for m in models.values()),
                   primary_raw_only_results=extra,
                   contact_rule='Different bricks, adjacent 24-LDU layers, >=1 shared 20x20-LDU horizontal cell; side contact alone is not an edge.',
                   normalization='Each export independently translated to minimum occupied x/z and lowest base; no rotations, scaling, clipping or added cells.',
                   limitations=['Selected final-output cohort, not an all-attempt solver success rate.',
                                'Exported voxel unions are audited; original per-run solver targets are not all available.',
                                'Stud contact graph does not establish load-bearing stability or a feasible assembly sequence.'])
    (DATA / 'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    (DATA / 'per_model.json').write_text(json.dumps(list(models.values()), indent=2)+'\n')
    (DATA / 'paired_results.json').write_text(json.dumps(pairs, indent=2)+'\n')
    write_csv(DATA / 'paired_results.csv', pairs)
    n = len(pairs)
    table = [r'\begin{table}[t]', r'\centering\small', r'\begin{tabular}{lrr}',
             r'\toprule', r'Geometric measure & Raw & Retiled \\', r'\midrule',
             f"Single stud component & {summary['raw_single_stud_component']}/{n} & {summary['retiled_single_stud_component']}/{n} " + r'\\',
             f"Mean stud components & {summary['raw_mean_stud_components']:.2f} & {summary['retiled_mean_stud_components']:.2f} " + r'\\',
             f"No body-cell overlaps & {summary['raw_overlap_free']}/{n} & {summary['retiled_overlap_free']}/{n} " + r'\\',
             r'\midrule', r'\multicolumn{3}{l}{Equal voxel unions after translation: ' + f"{summary['translation_normalized_union_equal']}/{n}" + r'} \\',
             r'\bottomrule', r'\end{tabular}',
             r'\caption{Independent export-geometry audit of the 110 matched raw/retiled pairs. Equality compares occupied voxel unions after translation normalization.}',
             r'\label{tab:reconstruction-geometry}', r'\end{table}']
    (ROOT / 'tables/reconstruction_geometry.tex').write_text('\n'.join(table)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('primary_raw_only_results','limitations')}, indent=2))

if __name__ == '__main__':
    main()
