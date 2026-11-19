"""Stage the supplied Qwen A text and B LDraw outputs for the four-score runner."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

from build import WORKSPACE, build_assets, normalize_prompt_id, pack, parse_prompt_markdown, stage
from build_brickmore_a import PREVIOUS, make_ldraw
from assemblies import PARTS, parse_ldr
from common import Progress, dump, sha, write_rows

STEM = 'qwen-A-B-four-scores-20261117'
SYSTEM_A = 'Qwen3-1.7B-base'
SYSTEM_B = 'Qwen1.7b B LDR'
BRICK_LINE = re.compile(r'\s*(\d+)\s*[xX×]\s*(\d+)\s*\(\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\)\s*')


def ldr_row(out, prompt, system, sample_id, payload, catalog, aliases, source, extra):
    assembly = parse_ldr(payload.decode('utf-8-sig'), catalog, aliases)
    ldr = out / 'Data/original' / system / (sample_id + '.ldr')
    assembled = out / 'Data/assemblies' / (sample_id + '.json')
    ldr.parent.mkdir(parents=True, exist_ok=True)
    ldr.write_bytes(payload)
    dump(assembled, assembly)
    row = {**prompt, 'system': system, 'sample_id': sample_id, 'model_id': prompt['prompt_id'],
           'primary': True, 'variant': 'parsed_partial' if prompt['batch'] == 'A' else 'delivered_ldr',
           'part_count': len(assembly['instances']), 'order_provenance': assembly['order_provenance'],
           'original_source': source, 'source_path': ldr.relative_to(out).as_posix(), 'source_sha256': sha(ldr),
           'assembly_path': assembled.relative_to(out).as_posix(), 'assembly_sha256': sha(assembled),
           'caption_sha256': hashlib.sha256(prompt['caption'].encode()).hexdigest(), **extra}
    return row, {part['part_stem'] for part in assembly['instances']}


def coverage_row(prompt, system, sample_id, status, reason, part_count, source):
    return {**{k: prompt[k] for k in ('prompt_id', 'batch', 'category', 'level', 'caption')},
            'system': system, 'sample_id': sample_id, 'input_status': status, 'input_reason': reason,
            'reported_or_ldr_bricks': part_count, 'original_source': source}


def base_a_inputs(archive, prompts, out, catalog, aliases, progress):
    with zipfile.ZipFile(archive) as z:
        paths = [n for n in z.namelist() if re.fullmatch(r'[^/]+/results/A\d+_L[1-5]/report\.json', n)]
        reports = {normalize_prompt_id(Path(n).parent.name): n for n in paths}
        if len(paths) != 260 or set(reports) != set(prompts):
            raise ValueError('Base Qwen A reports do not match the 260 canonical prompt IDs')
        for index, (pid, prompt) in enumerate(prompts.items(), start=1):
            folder = reports[pid].rsplit('/', 1)[0] + '/'
            report = json.loads(z.read(reports[pid]))
            caption = z.read(folder+'prompt.txt').decode('utf-8-sig').rstrip('\r\n')
            if caption != report['prompt'] or caption != prompt['caption'] or report['model'] != 'Qwen/Qwen3-1.7B (base, no fine-tune)':
                raise ValueError(f'{pid}: Base Qwen caption or checkpoint label differs')
            text = z.read(folder + 'output.txt').decode('utf-8-sig')
            bricks = [tuple(map(int, matched.groups())) for line in text.splitlines()
                      if (matched := BRICK_LINE.fullmatch(line))]
            if len(bricks) != report['brick_count'] or report['geometry_valid']:
                raise ValueError(f'{pid}: Raw-output parse differs from the original report')
            unsupported = sorted({tuple(sorted((h, w))) for h, w, *_ in bricks} - PARTS.keys())
            sample_id = f'qwen_base__{pid}__parsed_partial'
            source = archive.name + ':' + folder + 'output.txt'
            if not bricks:
                status, reason = 'no_placement', 'Original report and strict line parser both found zero brick placements.'
                result, parts = None, set()
            elif unsupported:
                status = 'unsupported_part'
                reason = 'Part dimensions outside the shared measured catalogue: ' + ', '.join(f'{h}x{w}' for h,w in unsupported)
                result, parts = None, set()
            else:
                status, reason = 'scoreable_partial', 'Strictly parsed placements only. Original output did not pass geometry validation.'
                sequence = '\n'.join(f'{h}x{w} ({x},{y},{z})' for h,w,x,y,z in bricks)
                data = make_ldraw(sequence, pid, title='Base Qwen A parsed placements').encode('ascii')
                result, parts = ldr_row(out, prompt, SYSTEM_A, sample_id, data, catalog, aliases, source,
                    {'geometry_valid': False, 'generation_complete': report['completed'], 'source_kind': status,
                     'original_output_sha256': hashlib.sha256(z.read(folder+'output.txt')).hexdigest()})
                if result['part_count'] != report['brick_count']:
                    raise ValueError(f'{pid}: LDraw export dropped placements')
            progress.update(index, f'{pid} {status}')
            yield result, parts, coverage_row(prompt, SYSTEM_A, sample_id, status, reason, len(bricks), source)


def delivered_b_inputs(archive, prompts, out, catalog, aliases, progress):
    with zipfile.ZipFile(archive) as z:
        entries = [i.filename for i in z.infolist() if not i.is_dir()]
        filenames = {}
        for name in entries:
            m = re.fullmatch(r'(\d{3})_([a-z0-9_]+)_L([1-5])\.ldr', name)
            if not m or int(m[1]) in filenames:
                raise ValueError(f'Unexpected or duplicate B LDraw entry {name}')
            filenames[int(m[1])] = (name, m[2], int(m[3]))
        if set(filenames) != set(range(265)):
            raise ValueError('B LDraw indices must be 0–264')
        for index, (pid, prompt) in enumerate(prompts.items()):
            name, obj, level = filenames[index]
            expected = prompt['object_name'].split('（', 1)[0].strip().lower().replace(' ', '_')
            if level != prompt['level'] or obj != expected:
                raise ValueError(f'{pid}: B LDraw file name and canonical object/level differ')
            sample_id = f'qwen_ldr__{pid}__delivered'
            source = archive.name + ':' + name
            result, parts = ldr_row(out, prompt, SYSTEM_B, sample_id, z.read(name), catalog, aliases, source,
                                   {'source_kind': 'indexed_ldr', 'source_index': index, 'checkpoint_in_ldr': None})
            progress.update(261+index, pid)
            yield result, parts, coverage_row(prompt, SYSTEM_B, sample_id, 'scoreable_ldr',
                 'Confirmed by index, object name and Level. Checkpoint is not stated in the archive.', result['part_count'], source)


def duplicate_check(source):
    prior = WORKSPACE / 'BrickMore_Comparision/BrickGPT_A组260条/official_A260_package_20261110/results'
    with zipfile.ZipFile(source/'A260_对照包_20261117.zip') as combined, zipfile.ZipFile(source/'base_qwen_A260_results.zip') as base:
        ldrs = [n for n in combined.namelist() if '/finetuned_A260/' in n and n.endswith('/output.ldr')]
        if len(ldrs) != 260 or any(combined.read(n) != (prior/Path(n).parent.name/'output.ldr').read_bytes() for n in ldrs):
            raise ValueError('Comparison ZIP contains different BrickGPT A LDRs')
        prefix = '/base_qwen_A260/'
        bundled = {n.split(prefix,1)[1]: n for n in combined.namelist()
                   if prefix in n and Path(n).name in ('output.txt','prompt.txt','report.json')}
        original = {n.split('/results/',1)[1]: n for n in base.namelist()
                    if '/results/' in n and Path(n).name in ('output.txt','prompt.txt','report.json')}
        if len(original) != 780 or bundled.keys() != original.keys() or any(combined.read(bundled[k])!=base.read(original[k]) for k in original):
            raise ValueError('Comparison ZIP contains different Base Qwen A records')
        return len(ldrs), len(original)


def main():
    from bricknet.data import load_aliases, load_catalog

    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--mesh-archive', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out, source = args.out.resolve(), args.source.resolve()
    prov = out/'Provenance'
    prov.mkdir(parents=True, exist_ok=True)
    catalog, aliases = load_catalog(), load_aliases()
    prompts_a = parse_prompt_markdown(PREVIOUS/'Provenance/A_prompts.md', 'A', 260)
    prompts_b = parse_prompt_markdown(PREVIOUS/'Provenance/B_prompts.md', 'B', 265)
    a_archive = source/'base_qwen_A260_results.zip'
    b_archive = source/'Qwen1.7b.zip'
    duplicate_ldrs, duplicate_base = duplicate_check(source)
    bar = Progress('Match Qwen inputs', 525)
    manifest, coverage, needed = [], [], set()
    for seq in [base_a_inputs(a_archive, prompts_a, out, catalog, aliases, bar),
                delivered_b_inputs(b_archive, prompts_b, out, catalog, aliases, bar)]:
        for row, parts, entry in seq:
            if row is not None:
                manifest.append(row)
                needed.update(parts)
            coverage.append(entry)
    counts = Counter(r['input_status'] for r in coverage)
    expected = {'scoreable_partial': 80, 'no_placement': 178, 'unsupported_part': 2, 'scoreable_ldr': 265}
    if counts != expected or len(manifest) != 345 or len({r['sample_id'] for r in coverage}) != 525:
        raise ValueError(f'Unexpected input counts {counts}')
    parts, extracted = build_assets(out, needed, args.mesh_archive)
    for name in ['A_prompts.md','B_prompts.md']:
        shutil.copyfile(PREVIOUS/'Provenance'/name, prov/name)
    shutil.copyfile(a_archive,prov/a_archive.name)
    write_rows(out/'Data/manifest.jsonl',manifest)
    write_rows(out/'Data/primary_manifest.jsonl',manifest)
    write_rows(out/'Data/prompt_coverage.jsonl',coverage)
    first_a = next(r for r in manifest if r['batch']=='A')
    most_a = max((r for r in manifest if r['batch']=='A'),key=lambda r:r['part_count'])
    audit = dict(passed=True, dataset='qwen_A_B_supplement_20261117', total_records=len(manifest),
        all_counts=dict(Counter(r['system'] for r in manifest)), expected_inputs=525, coverage=dict(counts),
        cohorts={'A': {'prompts': 260, 'systems': [SYSTEM_A]}, 'B': {'prompts': 265, 'systems': [SYSTEM_B]}},
        primary_policy='A scores are limited to strictly parsed placements from 80 incomplete representations. B scores cover all 265 supplied LDRs.',
        smoke_prompt_ids=[first_a['prompt_id'],most_a['prompt_id'],'B01_L1'], part_types=parts, new_meshes_extracted=extracted,
        original_archives={p.name:sha(p) for p in source.glob('*.zip')}, excluded_duplicate_brickgpt_ldrs=duplicate_ldrs,
        duplicate_base_files_in_comparison_zip=duplicate_base, reference_manifest_sha256=sha(PREVIOUS/'Data/manifest.jsonl'))
    dump(out/'Data/input_audit.json',audit)
    shutil.copyfile(PREVIOUS/'Data/scoring_models.json',out/'Data/scoring_models.json')
    stage(out)
    for name in ['structure.py','render.py','evaluate_paper_images.py','paper_common.py','prepare_paper_inputs.py']:
        if sha(out/'Scripts'/name)!=sha(PREVIOUS/'Scripts'/name):
            raise ValueError(f'Scoring implementation differs from the previous run: {name}')
    shutil.copyfile(Path(__file__).with_name('README_Qwen_AB.md'),out/'README_服务器运行.md')
    pack(out,WORKSPACE/'Deploy'/(STEM+'.tar.gz'),WORKSPACE/'Deploy/README_Qwen_AB_四项测评.md')
    print(json.dumps(audit,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    main()
