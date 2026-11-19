"""Build the 2026-11-16 LDraw comparison from the supplied A/B deliveries."""

import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tarfile
import zipfile

import numpy as np

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / 'comparison'))
from assemblies import parse_ldr
from assemble_bundle import pack, stage
from common import Progress, dump, sha, write_rows

SCORING_MODELS = {
    'vqa': {'repo': 'Qwen/Qwen2.5-VL-7B-Instruct', 'revision': 'cc594898137f460bfe9f0759e9844b3ce807cfb5'},
    'pe': {'repo': 'timm/PE-Core-bigG-14-448', 'revision': '17aa0c25addfa14198fa2ff73d845a22d433432e'},
    'siglip2': {'repo': 'google/siglip2-giant-opt-patch16-384', 'revision': 'a713301b217d38485fb2204c808367d10bc3cc40'},
}


def one(paths):
    paths = list(paths)
    if len(paths) != 1:
        raise ValueError(f'Expected one matching source, found {paths}')
    return paths[0]


def parse_prompt_markdown(path, batch, expected):
    rows = {}
    category = None
    object_num = None
    for line_no, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
        if match := re.match(r'^##\s+([a-z]+)\s*（', line):
            category = match[1]
        if match := re.match(r'^\*\*([AB])(\d+)\s*·\s*(.*?)\*\*', line):
            if match[1] != batch:
                raise ValueError(f'Unexpected batch on {path}:{line_no}')
            object_num, name = int(match[2]), match[3]
        if match := re.fullmatch(r'-\s*`L([1-5])`[：:][ \t]*(.+)', line):
            level = int(match[1])
            if not category or object_num is None or (object_num - 1) * 5 + level != len(rows) + 1:
                raise ValueError(f'Unexpected prompt order on {path}:{line_no}')
            pid = f'{batch}{object_num:02d}_L{level}'
            rows[pid] = dict(prompt_id=pid, batch=batch, category=category, level=level, caption=match[2],
                             object_name=name, source_line=line_no, ordinal=len(rows) + 1)
    if len(rows) != expected:
        raise ValueError(f'{path} has {len(rows)} prompts, expected {expected}')
    return rows


def normalize_prompt_id(pid):
    match = re.fullmatch(r'([AB])(\d+)_L([1-5])', pid)
    if not match:
        raise ValueError(f'Unexpected prompt ID {pid}')
    return f'{match[1]}{int(match[2]):02d}_L{match[3]}'


def compare_duplicate_archive(archive, extracted, expected):
    """Prove the ZIP copies duplicate the extracted source LDRs."""
    with zipfile.ZipFile(archive) as stream:
        names = [n for n in stream.namelist() if n.lower().endswith('.ldr')]
        if len(names) != expected or len(names) != len(set(names)):
            raise ValueError(f'Unexpected archive LDR count {archive}')
        for name in names:
            if stream.read(name) != (extracted / name).read_bytes():
                raise ValueError(f'ZIP and extracted LDR differ: {name}')


def scan_inputs(source, b_markdown, out):
    from bricknet.data import load_aliases, load_catalog

    catalog, aliases = load_catalog(), load_aliases()
    a_folder = source / 'BrickGPT_A组260条'
    b_folder = source / 'BrickGPT_B组265条'
    a_md = one(a_folder.glob('*/inputs/*.md'))
    a_json = one(a_folder.glob('*/inputs/*.json'))
    b_jsonl = one(b_folder.glob('*/summary.jsonl'))
    a_prompts = parse_prompt_markdown(a_md, 'A', 260)
    b_prompts = parse_prompt_markdown(b_markdown, 'B', 265)
    prompts = {**a_prompts, **b_prompts}
    source_a = json.loads(a_json.read_text(encoding='utf-8-sig'))
    source_b = [json.loads(line) for line in b_jsonl.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    if [normalize_prompt_id(r['prompt_id']) for r in source_a] != list(a_prompts):
        raise ValueError('A BrickGPT JSON order differs from source Markdown')
    if {normalize_prompt_id(r['prompt_id']) for r in source_b} != set(b_prompts) or len(source_b) != 265:
        raise ValueError('B BrickGPT summary coverage differs from source Markdown')
    files = []
    brickmore_ids = set()
    for f in sorted((source / 'BrickMore').glob('*.ldr')):
        match = re.fullmatch(r'(B\d+)_(\w+)_L([1-5])', f.stem)
        if not match:
            raise ValueError(f'Unexpected BrickMore file name: {f}')
        pid = normalize_prompt_id(f'{match[1]}_L{match[3]}')
        prompt = b_prompts[pid]
        if prompt['category'] != match[2] or pid in brickmore_ids:
            raise ValueError(f'Unexpected BrickMore join for {f}')
        comments = f.read_text(encoding='utf-8-sig').splitlines()
        prefix = '0 !BRICKMORE '
        header = dict(line[len(prefix):].split(' ', 1) for line in comments if line.startswith(prefix))
        if header['PROMPT'] != prompt['caption'] or int(header['SOURCE_INDEX']) != prompt['ordinal'] - 1:
            raise ValueError(f'BrickMore caption or index mismatch: {f}')
        status = one(line.removeprefix('0 STATUS ') for line in comments if line.startswith('0 STATUS '))
        files.append(('BrickMore', pid, f, {'source_kind': status, 'source_index': int(header['SOURCE_INDEX']),
                                             'generation_revision': header['REVISION'], 'generation_weights': header['WEIGHTS']}))
        brickmore_ids.add(pid)
    if brickmore_ids != set(b_prompts):
        raise ValueError('BrickMore B coverage does not match B prompts')

    for row in source_a:
        original_id = row['prompt_id']
        pid = normalize_prompt_id(original_id)
        case = a_json.parent.parent / 'results' / original_id
        report = json.loads((case / 'report.json').read_text(encoding='utf-8-sig'))
        if not row['prompt'] == report['prompt'] == prompts[pid]['caption'] or report['prompt_id'] != original_id:
            raise ValueError(f'BrickGPT A caption mismatch: {pid}')
        files.append(('BrickGPT', pid, case / 'output.ldr', {'generation_regenerations': report.get('n_regenerations'),
                                                            'reported_part_count': report['n_bricks'],
                                                            'generation_voxel_components': report.get('voxel_components')}))
    for row in source_b:
        pid = normalize_prompt_id(row['prompt_id'])
        case = b_jsonl.parent / row['prompt_id']
        report = json.loads((case / 'report.json').read_text(encoding='utf-8-sig'))
        if not row['caption'] == report['caption'] == prompts[pid]['caption'] or row['category'] != prompts[pid]['category']:
            raise ValueError(f'BrickGPT B caption or category mismatch: {pid}')
        files.append(('BrickGPT', pid, case / 'bricks.ldr', {'generation_regenerations': row.get('n_regenerations'),
                                                           'generation_stable': row.get('stable'),
                                                           'reported_part_count': row['brick_count']}))

    # User confirmed the original BrickNet run used A then B in the source Markdown order.
    indexes = {}
    for f in (source / 'beicknet').glob('*.ldr'):
        match = re.fullmatch(r'(\d+)-0-attempt-(\d+)', f.stem)
        if not match or int(match[1]) in indexes:
            raise ValueError(f'Unexpected BrickNet output ID: {f}')
        indexes[int(match[1])] = (f, int(match[2]))
    if set(indexes) != set(range(525)):
        raise ValueError('BrickNet index coverage must be 0–524')
    matches = []
    for index, (pid, prompt) in enumerate(prompts.items()):
        f, attempt = indexes[index]
        files.append(('BrickNet', pid, f, {'source_index': index, 'generation_attempt': attempt}))
        matches.append({'bricknet_index': index, 'source_file': f.name, **prompt})

    for archive, extracted, count in [(source / 'beicknet.zip', source / 'beicknet', 525),
                                      (source / 'BrickGPT_A组260条.zip', a_folder, 260),
                                      (source / 'BrickGPT_B组265条.zip', b_folder, 265)]:
        compare_duplicate_archive(archive, extracted, count)

    all_records = []
    needed = set()
    bar = Progress('Validate LDraw inputs', len(files))
    for index, (system, pid, f, extra) in enumerate(files, 1):
        prompt = prompts[pid]
        sid = f'{system.lower()}__{pid}__generated'
        data = f.read_bytes()
        try:
            assembly = parse_ldr(data.decode('utf-8-sig'), catalog, aliases)
        except (ValueError, AssertionError) as exc:
            raise ValueError(f'{f}: {exc}') from exc
        part_count = len(assembly['instances'])
        if part_count != extra.get('reported_part_count', part_count):
            raise ValueError(f'Model and generation report part counts differ for {f}')
        needed.update(p['part_stem'] for p in assembly['instances'])
        ldr = out / f'Data/original/{system}/{sid}.ldr'
        ldr.parent.mkdir(parents=True, exist_ok=True)
        ldr.write_bytes(data)
        assembled = out / f'Data/assemblies/{sid}.json'
        dump(assembled, assembly)
        all_records.append(dict(sample_id=sid, system=system, model_id=pid, variant='generated',
                                caption=prompt['caption'], caption_sha256=hashlib.sha256(prompt['caption'].encode()).hexdigest(),
                                category=prompt['category'], level=prompt['level'], prompt_id=pid, batch=prompt['batch'],
                                primary=prompt['batch'] == 'B', part_count=part_count, order_provenance=assembly['order_provenance'],
                                original_source=f.relative_to(source).as_posix(), source_path=ldr.relative_to(out).as_posix(),
                                source_sha256=sha(ldr), assembly_path=assembled.relative_to(out).as_posix(),
                                assembly_sha256=sha(assembled), **extra))
        bar.update(index, sid)

    joined = collections.defaultdict(dict)
    for row in all_records:
        group = joined[row['prompt_id']]
        if row['system'] in group:
            raise ValueError(f'Duplicate system and prompt {row["sample_id"]}')
        group[row['system']] = row['caption_sha256']
    counts = collections.Counter(row['system'] for row in all_records)
    if counts != {'BrickMore': 265, 'BrickGPT': 525, 'BrickNet': 525}:
        raise ValueError(f'Unexpected cohort counts: {counts}')
    for pid, group in joined.items():
        systems = {'BrickGPT', 'BrickNet'} | ({'BrickMore'} if pid.startswith('B') else set())
        if set(group) != systems or len(set(group.values())) != 1:
            raise ValueError(f'Nonmatching prompt cohort {pid}')
    prov = out / 'Provenance'
    prov.mkdir(exist_ok=True)
    for data, name in [(a_md, 'A_prompts.md'), (b_markdown, 'B_prompts.md'), (a_json, 'brickgpt_A_prompts.json'),
                       (b_jsonl, 'brickgpt_B_generation.jsonl'), (a_json.parent.parent / 'summary.md', 'brickgpt_A_generation.md')]:
        shutil.copyfile(data, prov / name)
    write_rows(prov / 'bricknet_index_to_prompt.jsonl', matches)
    write_rows(out / 'Data/manifest.jsonl', all_records)
    primary = [r for r in all_records if r['primary']]
    write_rows(out / 'Data/primary_manifest.jsonl', primary)
    audit = dict(passed=True, dataset='comparison_20261116', total_records=len(all_records),
                 source_root=str(source), all_counts=dict(counts), primary_records=len(primary),
                 primary_counts=dict(collections.Counter(r['system'] for r in primary)), matched_prompts=265,
                 cohorts={'A': {'prompts': 260, 'systems': ['BrickGPT', 'BrickNet']},
                          'B': {'prompts': 265, 'systems': ['BrickMore', 'BrickGPT', 'BrickNet']}},
                 formal_groups=len({(r['category'], r['level']) for r in primary}), part_types=len(needed),
                 bricknet_order='User confirmed A 260 then B 265 in Markdown order; 0-based file index.',
                 bricknet_boundaries={'0': 'A01_L1', '259': 'A52_L5', '260': 'B01_L1', '524': 'B53_L5'},
                 original_prompt_checks={'BrickMore_embedded_B': 265, 'BrickGPT_reports_A': 260, 'BrickGPT_reports_B': 265},
                 duplicate_zip_ldr_checks=1050,
                 primary_policy='B: 265 identical prompts x BrickMore, BrickGPT and BrickNet. A: 260 identical prompts x BrickGPT and BrickNet.',
                 smoke_prompt_ids=['A01_L1', 'B01_L1'])
    dump(out / 'Data/input_audit.json', audit)
    dump(out / 'Data/scoring_models.json', SCORING_MODELS)
    return needed, audit


def build_assets(out, needed, mesh_archive):
    from bricknet.data import load_catalog
    import meshlib.mrmeshpy as mm
    import meshlib.mrmeshnumpy as mn

    catalog = load_catalog()
    assets = out / 'Assets'
    inset, render = assets / 'inset', assets / 'render_meshes'
    inset.mkdir(parents=True, exist_ok=True)
    render.mkdir(exist_ok=True)
    previous = WORKSPACE / 'Deploy/build/comparison_20261110/BrickMoreComparison/Assets'
    previous_index = json.loads((previous / 'catalog.json').read_text(encoding='utf-8'))
    if sha(mesh_archive) != previous_index['source_archive_sha256']:
        raise ValueError('Mesh archive differs from the previous run')
    old_parts = previous_index['parts']
    parts = {}
    for stem in sorted(set(old_parts) & needed):
        collider, mesh = f'{stem}.ply', f'{stem}.npz'
        item = old_parts[stem]
        if sha(previous / 'inset' / collider) != item['collider_sha256'] or sha(previous / 'render_meshes' / mesh) != item['render_sha256']:
            raise ValueError(f'Previous scoring mesh changed: {stem}')
        shutil.copyfile(previous / 'inset' / collider, inset / collider)
        shutil.copyfile(previous / 'render_meshes' / mesh, render / mesh)
        parts[stem] = item
    missing = needed - parts.keys()
    if missing:
        todo = set(missing)
        bar = Progress('Extract missing pinned meshes', len(todo))
        with tarfile.open(mesh_archive, mode='r|xz') as stream:
            for member in stream:
                stem = Path(member.name).stem
                if member.isfile() and stem in todo:
                    (inset / f'{stem}.ply').write_bytes(stream.extractfile(member).read())
                    todo.remove(stem)
                    bar.update(len(missing) - len(todo), stem)
                    if not todo:
                        break
        if todo:
            raise ValueError(f'Pinned mesh archive lacks parts {sorted(todo)}')
    for stem in sorted(missing):
        collider, proto = inset / f'{stem}.ply', render / f'{stem}.npz'
        mesh = mm.loadMesh(str(collider))
        verts, faces = mn.getNumpyVerts(mesh).copy(), mn.getNumpyFaces(mesh.topology).copy()
        verts[:, 2] *= -1
        np.savez_compressed(proto, vertices=verts.astype(np.float32), faces=faces.astype(np.int32))
        parts[stem] = dict(part_id=catalog.stem_to_id[stem], vertices=len(verts), faces=len(faces),
                           bounds=[verts.min(0).tolist(), verts.max(0).tolist()], collider_sha256=sha(collider),
                           render_sha256=sha(proto))
    dump(assets / 'catalog.json', {**previous_index, 'parts': parts})
    return len(parts), len(missing)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=WORKSPACE / 'BrickMore_Comparision')
    parser.add_argument('--b-prompts', type=Path, required=True)
    parser.add_argument('--mesh-archive', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    needed, audit = scan_inputs(args.source.resolve(), args.b_prompts, out)
    meshes, new_meshes = build_assets(out, needed, args.mesh_archive)
    audit.update(part_types=meshes, new_meshes_extracted=new_meshes)
    dump(out / 'Data/input_audit.json', audit)
    stage(out)
    shutil.copyfile(HERE / 'README_服务器运行.md', out / 'README_服务器运行.md')
    if not args.prepare_only:
        pack(out, WORKSPACE / 'Deploy/brickmore-three-models-four-scores-20261116.tar.gz',
             WORKSPACE / 'Deploy/README_三模型四项测评_20261116.md')
    print(json.dumps(audit, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
