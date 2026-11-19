"""Package the final BrickMore AB LDraw files for the existing four-score runner."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

from build import WORKSPACE, pack, parse_ldr
from common import Progress, dump, rows, sha, write_rows


BUILD = WORKSPACE / 'Deploy/build'
SOURCE = WORKSPACE / 'BrickMore_Comparision/BrickMore_refined_20261119'
TEMPLATE = BUILD / 'brickmore_A260_20261117/BrickMore_A260_20261117'
B_TEMPLATE = BUILD / 'comparison_20261116/BrickMoreComparison_20261116'
RAW_RUNS = {
    'A': WORKSPACE / 'Results/qwen_analysis_20261117/intake/BrickMore_A260_20261117/Results/brickmore_A260',
    'B': WORKSPACE / 'BrickMore_Comparision/BrickMoreComparison_20261116/BrickMoreComparison_20261116/Results/comparison_full',
}
RUN_NAME = 'BrickMore_Refined525_20261119'
ARCHIVE_NAME = 'brickmore-refined525-four-scores-20261119.tar.gz'
README = Path(__file__).with_name('README_BrickMore_Refined525.md')
METRICS = ('vqa', 'pe', 'siglip2')
EXPECTED_BATCH = {'A': 260, 'B': 265}


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def verify_previous_protocol():
    models = read(TEMPLATE / 'Data/scoring_models.json')
    if models != read(B_TEMPLATE / 'Data/scoring_models.json'):
        raise ValueError('Original A and B scoring snapshots differ')

    raw = {}
    configs = {}
    for batch, run in RAW_RUNS.items():
        originals = [
            row for row in rows(run / 'selected_manifest.jsonl')
            if row['system'] == 'BrickMore' and row['batch'] == batch and row['primary']
        ]
        if len(originals) != EXPECTED_BATCH[batch]:
            raise ValueError(f'Unexpected original {batch} coverage')
        for row in originals:
            if row['prompt_id'] in raw or row['source_kind'] != 'raw_model_output':
                raise ValueError(f"Unexpected original record: {row['prompt_id']}")
            raw[row['prompt_id']] = row

        structure = read(run / 'structure.config.json')
        render = read(run / 'rendered/renders.config.json')
        if structure['source_sha256'] != sha(TEMPLATE / 'Scripts/structure.py'):
            raise ValueError(f'Original {batch} structure implementation changed')
        if render['source_sha256'] != sha(TEMPLATE / 'Scripts/render.py'):
            raise ValueError(f'Original {batch} rendering implementation changed')
        configs[batch] = {
            key: value for key, value in render.items()
            if key not in ('input_sha256', 'catalog_sha256', 'signature')
        }
        for metric in METRICS:
            config = read(run / (metric + '.config.json'))
            revision = models[metric]['revision']
            if config['preset'] != 'paper-text' or not config['resolved_model']['model'].endswith('/' + revision):
                raise ValueError(f'Original {batch} {metric} profile differs')
            for name, expected in config['sources'].items():
                if sha(TEMPLATE / 'Scripts' / name) != expected:
                    raise ValueError(f'Original {batch} {metric} implementation changed: {name}')
    if configs['A'] != configs['B'] or configs['A']['views'] != 8 or configs['A']['size'] != 512:
        raise ValueError('Unexpected original render configuration')
    return raw, configs['A']


def stage_runtime(out):
    scripts = out / 'Scripts'
    scripts.mkdir()
    for path in (TEMPLATE / 'Scripts').iterdir():
        if path.is_file() and path.name not in ('audit_returned_results.py', 'self_test.py'):
            shutil.copyfile(path, scripts / path.name)
    for name in ('run.sh', 'setup.sh', 'environment.local.sh.example', 'requirements-cpu.txt', 'requirements-gpu.txt'):
        shutil.copyfile(TEMPLATE / name, out / name)
    shutil.copyfile(TEMPLATE / 'Data/scoring_models.json', out / 'Data/scoring_models.json')
    shutil.copyfile(README, out / 'README_服务器运行.md')


def stage_assets(out, stems):
    old_a = read(TEMPLATE / 'Assets/catalog.json')
    old_b = read(B_TEMPLATE / 'Assets/catalog.json')
    if old_a['source_archive_sha256'] != old_b['source_archive_sha256']:
        raise ValueError('Original mesh source archives differ')
    index = {}
    out_assets = out / 'Assets'
    for directory in ('inset', 'render_meshes'):
        (out_assets / directory).mkdir(parents=True)
    for stem in sorted(stems):
        a = old_a['parts'][stem]
        b = old_b['parts'][stem]
        for key, filename in (('collider_sha256', f'inset/{stem}.ply'), ('render_sha256', f'render_meshes/{stem}.npz')):
            if a[key] != b[key]:
                raise ValueError(f'Original mesh hashes differ: {filename}')
            source = TEMPLATE / 'Assets' / filename
            if sha(source) != a[key] or sha(B_TEMPLATE / 'Assets' / filename) != a[key]:
                raise ValueError(f'Prior mesh payload differs from the catalog: {filename}')
            shutil.copyfile(source, out_assets / filename)
        index[stem] = a
    dump(out_assets / 'catalog.json', {**old_a, 'parts': index})


def stage_inputs(source, out, raw):
    from bricknet.data import load_aliases, load_catalog

    final = read(source / 'final_results.json')
    verification = read(source / 'final_verification.json')
    expected = {f'{batch}{number:02d}_L{level}' for batch, count in EXPECTED_BATCH.items()
                for number in range(1, count // 5 + 1) for level in range(1, 6)}
    source_ldr = {f.stem for f in (source / 'final_ldr').glob('*.ldr')}
    if (len(final) != 525 or {r['prompt_id'] for r in final} != expected
            or source_ldr != expected or set(raw) != expected
            or not verification['passed'] or verification['verified_final_models'] != 525):
        raise ValueError('Input must cover each of the 525 verified A/B prompts once')

    catalog, aliases = load_catalog(), load_aliases()
    ldr_dir = out / 'Data/original/BrickMore'
    assembly_dir = out / 'Data/assemblies'
    ldr_dir.mkdir(parents=True)
    assembly_dir.mkdir()
    manifest, stems = [], set()
    progress = Progress('Verify and stage final LDraw files', len(final))

    for index, model in enumerate(final, 1):
        pid = model['prompt_id']
        original = raw[pid]
        for field in ('batch', 'category', 'level', 'caption'):
            if model[field] != original[field]:
                raise ValueError(f'{pid}: original and refined {field} differ')
        if (model['ldr_path'] != f'final_ldr/{pid}.ldr' or not model['validation']['passed']
                or not all(model['validation']['checks'].values())):
            raise ValueError(f'{pid}: invalid final LDR reference or geometry audit')

        path = source / model['ldr_path']
        payload = path.read_bytes()
        checksum = hashlib.sha256(payload).hexdigest()
        ldr_text = payload.decode('utf-8-sig')
        lines = ldr_text.splitlines()
        caption = model['caption']
        seed = model['seed']
        if checksum != model['ldr_sha256'] or any(line not in lines for line in (
                f'0 !BRICKMORE PROMPT_ID {pid}', f'0 !BRICKMORE PROMPT {caption}',
                f"0 !BRICKMORE ORIGIN {model['origin']}", f"0 !BRICKMORE SEED {seed if seed is not None else 'original'}")):
            raise ValueError(f'{pid}: model hash or LDraw metadata differs')

        assembly = parse_ldr(ldr_text, catalog, aliases)
        if len(assembly['instances']) != model['refined_bricks']:
            raise ValueError(f'{pid}: final part count differs')
        stems.update(part['part_stem'] for part in assembly['instances'])
        sid = f'brickmore__{pid}__refined'
        ldr_path = ldr_dir / (sid + '.ldr')
        assembly_path = assembly_dir / (sid + '.json')
        ldr_path.write_bytes(payload)
        dump(assembly_path, assembly)
        manifest.append(dict(
            sample_id=sid, system='BrickMore', model_id=pid, variant='refined', primary=True,
            prompt_id=pid, batch=model['batch'], category=model['category'], level=model['level'],
            caption=caption, caption_sha256=hashlib.sha256(caption.encode()).hexdigest(),
            part_count=model['refined_bricks'], source_kind='final_refined_output',
            refine_origin=model['origin'], regeneration_seed=seed,
            removed_voxels=model['normalization']['removed_voxels'],
            order_provenance=assembly['order_provenance'],
            original_source=model['ldr_path'], raw_baseline_sample_id=original['sample_id'],
            raw_baseline_source_sha256=original['source_sha256'],
            source_path=ldr_path.relative_to(out).as_posix(), source_sha256=checksum,
            assembly_path=assembly_path.relative_to(out).as_posix(), assembly_sha256=sha(assembly_path),
        ))
        progress.update(index, pid)

    write_rows(out / 'Data/manifest.jsonl', manifest)
    write_rows(out / 'Data/primary_manifest.jsonl', manifest)
    return manifest, stems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--out', type=Path, default=BUILD / 'brickmore_refined525_20261119' / RUN_NAME)
    args = parser.parse_args()
    source, out = args.source.resolve(), args.out.resolve()
    if out == source or out.is_relative_to(source):
        raise ValueError('Keep the evaluation staging directory outside the refine result directory')
    raw, render_protocol = verify_previous_protocol()
    out.mkdir(parents=True, exist_ok=False)
    manifest, stems = stage_inputs(source, out, raw)
    stage_assets(out, stems)
    stage_runtime(out)
    provenance = out / 'Provenance'
    provenance.mkdir()
    for name in ('final_results.json', 'final_summary.json', 'final_verification.json'):
        shutil.copyfile(source / name, provenance / name)
    smoke = [
        next(r['prompt_id'] for r in manifest if r['batch'] == batch and r['refine_origin'] == origin)
        for batch in 'AB' for origin in ('original_retained', 'original_refined', 'regenerated')
    ]
    audit = dict(
        passed=True, dataset='brickmore_refined525_20261119', total_records=len(manifest),
        primary_records=len(manifest), all_counts={'BrickMore': len(manifest)},
        cohorts={b: {'prompts': n, 'systems': ['BrickMore']} for b, n in EXPECTED_BATCH.items()},
        primary_policy='All 525 final BrickMore LDRs. Compare to previous raw results by prompt_id and caption. P_inv follows delivered file order.',
        final_refinement_origins=dict(Counter(r['refine_origin'] for r in manifest)),
        source_root=str(source), caption_matches_to_scored_raw=len(raw),
        verified_final_ldr_hashes=len(manifest), part_types=len(stems),
        render_protocol=render_protocol, smoke_prompt_ids=smoke,
        previous_run_manifest_sha256={
            batch: sha(run / 'selected_manifest.jsonl') for batch, run in RAW_RUNS.items()
        },
    )
    dump(out / 'Data/input_audit.json', audit)
    pack(out, WORKSPACE / 'Deploy' / ARCHIVE_NAME, WORKSPACE / 'Deploy/README_BrickMore_Refined525_四项测评.md')
    print(json.dumps(audit, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
