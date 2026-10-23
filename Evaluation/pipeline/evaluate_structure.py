"""Score original generated paths and report placement rates and Table-2 prefix survival."""
import argparse
import json
import os
import statistics
from collections import Counter
from pathlib import Path
from paper_common import (Journal, fingerprint, load_bricknet, normalize_ids, packages,
                          read_jsonl, sha256, source_hashes, write_json)


def aggregate(rows, policy='both'):
    """Unparsed suffixes and unavailable collisions are censored, never fabricated."""
    n = len(rows)
    if not n:
        raise ValueError('No structure records')
    parsed = [r for r in rows if r.get('parse_ok')]
    covered = [r for r in rows if r.get('collisions') is not None]
    eligible = [r for r in parsed if r.get('collisions') is not None and r['parsed_parts'] > 0]
    invalid = sum(len(set(r['collisions'])) for r in eligible)
    actions = sum(r['parsed_parts'] for r in eligible)
    micro = invalid/actions if actions else None
    macro = statistics.mean(len(set(r['collisions']))/r['parsed_parts'] for r in eligible) if eligible else None
    def prefix(r):
        return r['parsed_parts'] if r['parse_ok'] else r['first_invalid']
    known_prefix = [r for r in rows if r.get('parsed_parts') is not None]
    max_steps = max((r['attempted_actions'] or 0 for r in known_prefix), default=0)
    survival = []
    for step in range(max_steps + 1):
        survival.append({'step': step,
            'connectivity_survival': sum(prefix(r) >= step for r in known_prefix)/n,
            'collision_survival_observed': (
                sum(min([prefix(r), *r['collisions']]) >= step for r in covered)/len(covered)
                if covered else None)})
    clean = sum(r['parse_ok'] and not r['collisions'] for r in covered)
    return {'samples': n, 'parseable_samples': len(parsed), 'parseable_rate': len(parsed)/n,
        'collision_observed_samples': len(covered), 'collision_coverage': len(covered)/n,
        'pinv_eligible_samples': len(eligible), 'pinv_eligible_actions': actions,
        'invalid_placements': invalid, 'pinv_macro': macro, 'pinv_micro': micro,
        'selected_aggregation': policy, 'pinv': {'macro': macro, 'micro': micro}.get(policy),
        'pinv_aggregation_matches_published_table': 'unverified; original aggregation code not released',
        'parseable_and_collision_free_rate_observed': clean/len(covered) if covered else None,
        'mean_steps_before_connectivity_failure': statistics.mean(prefix(r) for r in known_prefix)
            if known_prefix else None,
        'mean_steps_before_collision_or_parse_failure_observed': statistics.mean(
            min([prefix(r), *r['collisions']]) for r in covered) if covered else None,
        'statuses': dict(Counter(r['status'] for r in rows)), 'survival': survival}


def score_one(row, bricknet, collision=True):
    text = row.get('path', row.get('text'))
    if not isinstance(text, str):
        raise ValueError(f'{row["sample_id"]}: needs original BrickNet path/text, not GLB')
    normalized = text if text.endswith('\n') else text+'\n'
    result = bricknet.parse_sample(normalized)
    parts = len(result.tree.parts)
    ok = result.error is None and parts > 0
    collisions = None
    error = None
    if collision and parts:
        try:
            from bricknet.score import check_tree
            collisions = check_tree(result.tree)
            if collisions is None:
                error = 'Collider unavailable'
        except FileNotFoundError as exc:
            error = str(exc)
    status = 'ok' if ok else 'parse_failed'
    if collision and parts and collisions is None:
        status = 'collision_unknown' if ok else 'parse_failed_collision_unknown'
    if not collision and ok:
        status = 'parse_only'
    return {**row, 'status': status, 'parse_ok': ok, 'parse_error': result.error,
        'attempted_actions': (normalized.count('\n')+2)//2 if text.strip() else 0,
        'parsed_parts': parts, 'first_invalid': None if ok else parts,
        'collisions': collisions, 'collision_error': error,
        'pinv': len(set(collisions))/parts if ok and collisions is not None else None}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--bricknet-version', default='0.1.0', choices=['0.1.0','0.1.1'])
    p.add_argument('--data-dir', required=True, type=Path, help='inset/ (0.1.0) or cvx/ (0.1.1) parent')
    p.add_argument('--parse-only', action='store_true')
    p.add_argument('--pinv-aggregation', choices=['both','macro','micro'], default='both')
    args = p.parse_args()
    os.environ['BRICKNET_DATA'] = str(args.data_dir.resolve())
    bricknet = load_bricknet(args.bricknet_version)
    rows = normalize_ids(read_jsonl(args.input))
    if not rows:
        raise ValueError('No generated paths')
    root = Path(bricknet.__file__).parent
    mesh_dir = args.data_dir/('inset' if args.bricknet_version == '0.1.0' else 'cvx')
    # Hash actual files, not just the data directory name; replacement invalidates resume.
    meshes = {str(f.relative_to(args.data_dir)): sha256(f) for f in sorted(mesh_dir.glob('*'))
              if f.is_file()} if not args.parse_only else {}
    if not args.parse_only and not meshes:
        raise FileNotFoundError(f'No collision meshes in {mesh_dir}; run bricknet fetch-meshes')
    config = {'metric': 'placement_invalidity', 'bricknet_version': bricknet.__version__,
        'backend': 'paper-inset-triangle' if args.bricknet_version=='0.1.0' else 'updated-convex-1LDU',
        'parse_only': args.parse_only, 'pinv_aggregation': args.pinv_aggregation,
        'input_file_sha256': sha256(args.input), 'data_dir': str(args.data_dir.resolve()),
        'mesh_sha256': meshes, 'packages': packages(['bricknet','meshlib','numpy','scipy','pybullet']),
        'bricknet_source_sha256': {str(f.relative_to(root)): sha256(f) for f in sorted(root.rglob('*'))
                                  if f.is_file() and f.suffix in {'.py','.json','.xz'}},
        'sources': source_hashes(__file__)}
    journal = Journal(args.out, config)
    for i, row in enumerate(rows):
        ih = fingerprint(row)
        if journal.cached(row['sample_id'], ih) is None:
            result = score_one(row, bricknet, collision=not args.parse_only)
            journal.append(result, ih)
        print(f'{i+1}/{len(rows)} {row["sample_id"]}', flush=True)
    summary = aggregate([journal.done[r['sample_id']] for r in rows], args.pinv_aggregation)
    summary.update({'backend': config['backend'], 'config_signature': journal.signature})
    write_json(args.out.with_suffix('.summary.json'), summary)
    print(json.dumps({k:v for k,v in summary.items() if k!='survival'}, indent=2))


if __name__ == '__main__':
    main()
