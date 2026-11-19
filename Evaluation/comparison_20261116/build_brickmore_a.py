"""Verify the BrickMore A sequences against their GLBs and build the A supplement."""

import argparse
import collections
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

from build import WORKSPACE, build_assets, pack, parse_prompt_markdown, stage
from assemblies import PARTS, parse_ldr, recover_procedural_glb
from common import Progress, dump, rows, sha, write_rows

import numpy as np

PREVIOUS = WORKSPACE / 'Deploy/build/comparison_20261116/BrickMoreComparison_20261116'
STEM = 'brickmore-A260-four-scores-20261117'
ROTATION_STRAIGHT = (0, 0, 1, 0, 1, 0, -1, 0, 0)
ROTATION_TURNED = (-1, 0, 0, 0, 1, 0, 0, 0, -1)
BRICK = re.compile(r'(\d+)x(\d+)\s*\(\s*(-?\d+),\s*(-?\d+),\s*(-?\d+)\s*\)')


def input_path(source, name):
    path = (source / name).resolve()
    if not path.is_relative_to(source) or not path.is_file():
        raise ValueError(f'Invalid delivery path: {name}')
    return path


def make_ldraw(text, pid, title='BrickMore A group'):
    ldr = [f'0 {title} {pid}', '0 Exported from supplied brick sequence in sequence order']
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        match = BRICK.fullmatch(line.strip())
        if not match:
            raise ValueError(f'{pid}: unexpected brick sequence line {number}')
        height, width, x, y, z = map(int, match.groups())
        stem = PARTS[tuple(sorted((height, width)))]
        rotation = ROTATION_STRAIGHT if height <= width else ROTATION_TURNED
        pos = (20 * x + 10 * height, -24 * z, 20 * y + 10 * width)
        transform = ' '.join(map(str, (*pos, *rotation)))
        ldr.extend([f'1 0x2E8B42B {transform} {stem}.dat', '0 STEP'])
    return '\n'.join(ldr) + '\n'


def check_glb(assembly, other, path):
    right = other['instances']
    left = assembly['instances'][:len(right)]
    if [p['part_stem'] for p in left] != [p['part_stem'] for p in right]:
        raise ValueError(f'{path.name}: LDraw and GLB brick type or order mismatch')
    lm, rm = (np.asarray([p['matrix_ldu'] for p in parts]) for parts in (left, right))
    if not np.array_equal(lm[:, :3, :3], rm[:, :3, :3]):
        raise ValueError(f'{path.name}: LDraw and GLB rotations differ')
    delta = rm[:, :3, 3] - lm[:, :3, 3]
    offset = np.median(delta, axis=0)
    error = float(np.abs(delta - offset).max())
    if error > 0.001:
        raise ValueError(f'{path.name}: LDraw and GLB positions differ after translation ({error} LDU)')
    return dict(glb_bricks=len(right), sequence_bricks=len(assembly['instances']),
                status='full' if len(right)==len(assembly['instances']) else 'matching_prefix',
                glb_viewer_vertical_scale=other['reconstruction']['source_vertical_scale'],
                glb_translation_ldu=offset.tolist(), maximum_position_error_ldu=error)


def stage_inputs(source, out, workers):
    from bricknet.data import load_aliases, load_catalog

    reference_md = PREVIOUS / 'Provenance/A_prompts.md'
    reference = parse_prompt_markdown(reference_md, 'A', 260)
    previous_rows = [r for r in rows(PREVIOUS / 'Data/manifest.jsonl') if r['batch'] == 'A']
    paired = collections.defaultdict(dict)
    for row in previous_rows:
        paired[row['prompt_id']][row['system']] = row['caption']
    if len(previous_rows) != 520 or set(paired) != set(reference):
        raise ValueError('Previous A coverage differs from the reference prompt file')

    delivery = json.loads((source / 'manifest.json').read_text(encoding='utf-8-sig'))
    if [r['index'] for r in delivery] != list(range(1, 261)):
        raise ValueError('BrickMore A manifest must list source indices 1 through 260')
    catalog, aliases = load_catalog(), load_aliases()
    originals = out / 'Data/original/BrickMore'
    originals.mkdir(parents=True, exist_ok=True)
    prov = out / 'Provenance'
    sequences = prov / 'sequences'
    sequences.mkdir(parents=True, exist_ok=True)
    (out / 'Data/assemblies').mkdir(exist_ok=True)
    manifest, geometry, needed = [], [], set()
    progress = Progress('Match prompts and verify GLB bricks', 260)
    glb_paths = [input_path(source, row['model']) for row in delivery]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        recovered = pool.map(recover_procedural_glb, glb_paths)
        for row, (pid, prompt), glb, other in zip(delivery, reference.items(), glb_paths, recovered):
            record, audit_row, parts = stage_record(row, pid, prompt, paired, source, out, catalog, aliases,
                                                   originals, sequences, glb, other)
            manifest.append(record)
            geometry.append(audit_row)
            needed.update(parts)
            progress.update(row['index'], pid)

    for file, name in [(reference_md, 'A_prompts.md'), (source / 'manifest.json', 'brickmore_A_source_manifest.json'),
                       (source / 'README.md', 'brickmore_A_source_readme.md')]:
        shutil.copyfile(file, prov / name)
    write_rows(prov / 'glb_geometry_verification.jsonl', geometry)
    write_rows(out / 'Data/manifest.jsonl', manifest)
    write_rows(out / 'Data/primary_manifest.jsonl', manifest)
    flags = {key: dict(collections.Counter(str(r[key]).lower() for r in manifest))
             for key in ('geometry_valid', 'generation_complete')}
    smoke = list(dict.fromkeys([manifest[0]['prompt_id'],
                 next((r['prompt_id'] for r in manifest if not r['geometry_valid']), manifest[1]['prompt_id']),
                 next((r['prompt_id'] for r in manifest if not r['generation_complete']), manifest[-1]['prompt_id'])]))
    audit = dict(passed=True, dataset='brickmore_A260_supplement_20261117', total_records=260, primary_records=260,
        all_counts={'BrickMore': 260}, source_root=str(source), reference_manifest_sha256=sha(PREVIOUS/'Data/manifest.jsonl'),
        cohorts={'A': {'prompts': 260, 'systems': ['BrickMore']}}, smoke_prompt_ids=smoke,
        primary_policy='BrickMore A supplement: 260 prompts also present in the previous BrickGPT and BrickNet A results.',
        formal_groups=len({(r['category'], r['level']) for r in manifest}), source_flags=flags,
        caption_matches=260, glbs_verified=260, glb_coverage=dict(collections.Counter(r['status'] for r in geometry)),
        total_sequence_bricks=sum(r['sequence_bricks'] for r in geometry),
        brick_instances_verified_in_glb=sum(r['glb_bricks'] for r in geometry),
        maximum_glb_position_error_ldu=max(r['maximum_position_error_ldu'] for r in geometry))
    return needed, audit


def stage_record(row, pid, prompt, paired, source, out, catalog, aliases, originals, sequences, glb, other):
        caption = prompt['caption']
        if paired[pid] != {'BrickGPT': caption, 'BrickNet': caption}:
            raise ValueError(f'{pid}: prior systems have different captions')
        prompt_text = input_path(source, row['prompt_file']).read_text(encoding='utf-8-sig').rstrip('\r\n')
        if caption != row['prompt'] or caption != prompt_text or (row['category'], row['level']) != (prompt['category'], prompt['level']):
            raise ValueError(f'{pid}: source prompt text, category, or level mismatch')
        seq = input_path(source, row['sequence'])
        ldr_text = make_ldraw(seq.read_text(encoding='utf-8-sig'), pid)
        assembly = parse_ldr(ldr_text, catalog, aliases)
        part_count = len(assembly['instances'])
        if part_count != row['brick_count']:
            raise ValueError(f'{pid}: sequence count differs from source manifest')
        matched = check_glb(assembly, other, glb)
        sid = f'brickmore__{pid}__generated'
        ldr, ap = originals / (sid + '.ldr'), out / 'Data/assemblies' / (sid + '.json')
        ldr.write_bytes(ldr_text.encode('ascii'))
        assembly['order_provenance'] = 'Supplied canonical brick sequence order; GLB body order verified for exported bricks'
        dump(ap, assembly)
        copied_seq = sequences / (pid + '.txt')
        shutil.copyfile(seq, copied_seq)
        record = dict(sample_id=sid, system='BrickMore', model_id=pid, variant='generated', batch='A',
            primary=True, prompt_id=pid, category=prompt['category'], level=prompt['level'], caption=caption,
            caption_sha256=hashlib.sha256(caption.encode()).hexdigest(), part_count=part_count,
            order_provenance=assembly['order_provenance'], source_kind='raw_model_output',
            generation_complete=row['generation_complete'], geometry_valid=row['geometry_valid'],
            original_source=row['model'], original_glb_sha256=sha(glb), sequence_path=copied_seq.relative_to(out).as_posix(),
            sequence_sha256=sha(copied_seq), source_path=ldr.relative_to(out).as_posix(), source_sha256=sha(ldr),
            assembly_path=ap.relative_to(out).as_posix(), assembly_sha256=sha(ap),
            glb_coverage=matched['status'])
        return record, dict(prompt_id=pid, **matched), {p['part_stem'] for p in assembly['instances']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--mesh-archive', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=min(6, os.cpu_count() or 1))
    args = parser.parse_args()
    out = args.out.resolve()
    needed, audit = stage_inputs(args.source.resolve(), out, args.workers)
    parts, extracted = build_assets(out, needed, args.mesh_archive)
    audit.update(part_types=parts, new_meshes_extracted=extracted)
    dump(out / 'Data/input_audit.json', audit)
    shutil.copyfile(PREVIOUS/'Data/scoring_models.json', out/'Data/scoring_models.json')
    stage(out)
    for name in ['structure.py', 'render.py', 'evaluate_paper_images.py', 'paper_common.py', 'prepare_paper_inputs.py']:
        if sha(out/'Scripts'/name) != sha(PREVIOUS/'Scripts'/name):
            raise ValueError(f'Scoring implementation differs from last run: {name}')
    shutil.copyfile(Path(__file__).with_name('README_BrickMore_A260.md'), out/'README_服务器运行.md')
    pack(out, WORKSPACE / 'Deploy' / (STEM+'.tar.gz'), WORKSPACE / 'Deploy/README_BrickMore_A260_四项补测.md')
    print(json.dumps(audit, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
