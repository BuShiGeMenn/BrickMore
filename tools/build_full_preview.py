"""Build a self-contained, exact-geometry preview of the latest 80,000 models."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('source.model.json', 'target.model.json', 'assembly.json', 'report.json')
PACKAGE = 'BrickMore_full_80000_preview_20261014.zip'


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def cells(model):
    result = {}
    for p in model['voxels']:
        position = p['x'], p['y'], p['z']
        if position in result:
            raise ValueError('Duplicate source/target voxel')
        r, g, b = p['color']
        result[position] = (r << 16) | (g << 8) | b
    return result


def runs_from_cells(value):
    runs = []
    for x, y, z in sorted(value, key=lambda p: (p[1], p[2], p[0])):
        color = value[x, y, z]
        if runs and runs[-1][1:3] == [y, z] and runs[-1][0] + runs[-1][3] == x and runs[-1][4] == color:
            runs[-1][3] += 1
        else:
            runs.append([x, y, z, 1, color])
    return runs


def decode_runs(runs):
    result = {}
    for x, y, z, length, color in runs:
        for offset in range(length):
            position = x + offset, y, z
            if position in result:
                raise ValueError('Overlapping encoded runs')
            result[position] = color
    return result


def build_model(job):
    row, folder, expected = job
    raw = {name: (Path(folder) / name).read_bytes() for name in NAMES}
    hashes = {name: sha(data) for name, data in raw.items()}
    if hashes != expected:
        raise ValueError('Local input differs from published package: ' + row['id'])
    source, target, assembly, report = [json.loads(raw[name]) for name in NAMES]
    if report['modelId'] != row['id'] or report['geometryValidation']['passed'] != row['passed']:
        raise ValueError('Preview index does not match actual report')
    original, goal = cells(source), cells(target)
    runs = runs_from_cells(original)
    decoded = decode_runs(runs)
    if decoded != original:
        raise ValueError('Source encoding changes geometry or colors')
    removed = [list(p) for p, color in original.items() if goal.get(p) != color]
    added = [[*p, color] for p, color in goal.items() if original.get(p) != color]
    for p in removed:
        del decoded[tuple(p)]
    for x, y, z, color in added:
        decoded[x, y, z] = color
    if decoded != goal:
        raise ValueError('Target encoding changes geometry or colors')
    bricks = [[b['x'], b['z'], b['y'], b['h'], 1, b['w'], b['color']] for b in assembly['bricks']]
    if len(bricks) != report['geometryValidation']['brickCount']:
        raise ValueError('Brick population differs')
    is_new = row['shard'] == 'B' and row['category'] == 'piano'
    if is_new and (report['algorithmVersion'] != 'quality_supported_piano_b_exact_delivery_v1' or added or removed):
        raise ValueError('New B piano was not selected exactly')
    compact_report = {k: report[k] for k in ('algorithmVersion', 'optimizerVersion', 'modelId', 'sourceFileSha256', 'geometryValidation', 'repairAudit', 'qualityScreenedSuccess', 'fullPhysics')}
    compact_report['physics'] = {'status': report['physics']['status']}
    value = dict(id=row['id'], sourceRuns=runs, targetRemoved=removed, targetAdded=added,
                 bricks=bricks, report=compact_report, publishedInputSha256=hashes)
    return row['previewPath'], encode(value), len(original), len(goal), len(bricks), is_new


def catalog(directory):
    manifest = json.loads((directory / 'download_manifest.json').read_bytes())
    result = {}
    for asset in manifest['assets']:
        if asset['kind'] != 'model_package':
            continue
        inventory_path = directory / asset['fileHashManifest']
        if inventory_path.is_file():
            inventory = json.loads(inventory_path.read_bytes())
        else:
            with zipfile.ZipFile(directory / 'packages' / asset['name']) as archive:
                inventory = json.loads(archive.read(asset['fileHashManifest']))
        for path in inventory:
            if path.startswith('results/') and path.endswith('/report.json'):
                folder = path.rsplit('/', 1)[0]
                if folder in result:
                    raise ValueError('Duplicate package model')
                result[folder] = (asset['url'], {name: inventory[folder + '/' + name] for name in NAMES})
    return manifest, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--replacement', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error('workers must be positive')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    package_path = output / PACKAGE
    if package_path.exists():
        parser.error('Refuse to replace an existing preview package; choose a fresh output.')
    base = args.base.resolve()
    replacement = args.replacement.resolve()
    base_manifest, old = catalog(base)
    replacement_manifest, new = catalog(replacement)
    if len(old) != 80000 or len(new) != 1905:
        raise ValueError('Release populations differ')
    rows = json.loads((replacement / 'current_preview/preview_index.json').read_bytes())
    if len(rows) != 80000 or len({row['id'] for row in rows}) != 80000:
        raise ValueError('Incomplete or duplicate preview population')
    jobs = []
    for row in rows:
        is_new = row['shard'] == 'B' and row['category'] == 'piano'
        entry = (new if is_new else old)[row['path']]
        row['previewPath'] = f"model_data/{row['shard']}/{row['category']}/{row['id']}.json"
        row['downloadUrl'] = entry[0]
        jobs.append((row, str((replacement if is_new else base) / row['path']), entry[1]))
    groups = Counter(row['shard'] + '_' + row['category'] for row in rows)
    passed = sum(row['passed'] for row in rows)
    if len(groups) != 42 or passed != 79301:
        raise ValueError('Category coverage or updated status differs')
    inventory = {}
    total_source = total_target = total_bricks = replacements = 0
    with zipfile.ZipFile(package_path, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
        def write(name, data):
            if name in inventory:
                raise ValueError('Duplicate package path')
            inventory[name] = sha(data)
            archive.writestr(name, data)
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            for count, (name, data, source_count, target_count, brick_count, is_new) in enumerate(pool.map(build_model, jobs, chunksize=20, buffersize=8), 1):
                write(name, data)
                total_source += source_count
                total_target += target_count
                total_bricks += brick_count
                replacements += is_new
                if count % 2000 == 0:
                    print('EXACT PREVIEW MODELS PACKAGED', count, '/ 80000', flush=True)
        if replacements != 1905:
            raise ValueError('Replacement scope differs')
        summary = dict(modelCount=80000, categoryCount=21, shardIds=['A', 'B'], geometryPassed=passed,
                       geometryFailed=80000-passed, regeneratedPianoBCount=replacements, unchangedBaseCount=80000-replacements,
                       sourceVoxelCount=total_source, targetVoxelCount=total_target, brickCount=total_bricks,
                       baseRelease=base_manifest['releaseTag'], pianoBRelease=replacement_manifest['releaseTag'],
                       renderer='webgl_per_pixel_depth_v2', allPreviewSourceTargetCoordinatesAndRgbExact=True,
                       allFourInputsPerModelMatchPublishedSha256=True, previewOnly=True,
                       groups=dict(groups))
        for name in ('index.html', 'launch_preview.py', 'start_preview.cmd', 'README.md'):
            write(name, (ROOT / 'preview/full_80000' / name).read_bytes())
        write('preview_index.json', encode(rows))
        write('summary.json', encode(summary))
        write('results.csv', (replacement / 'current_preview/results.csv').read_bytes())
        (output / 'summary.json').write_bytes(encode(summary))
        (output / 'preview_index.json').write_bytes(encode(rows))
        # Validation is part of the ZIP; browser validation is published separately.
        proof = dict(**summary, checkedModelCount=80000, previewSourceMismatchCount=0,
                     previewTargetMismatchCount=0, publishedInputHashMismatchCount=0,
                     browserValidationFile='browser_verification.json')
        write('preview_verification.json', encode(proof))
        (output / 'preview_verification.json').write_bytes(encode(proof))
        archive.writestr('preview_files_sha256.json', encode(inventory))
    with zipfile.ZipFile(package_path) as archive:
        expected_names = set(inventory) | {'preview_files_sha256.json'}
        if set(archive.namelist()) != expected_names or len(archive.namelist()) != len(expected_names):
            raise ValueError('ZIP population differs')
        for name, expected in inventory.items():
            if sha(archive.read(name)) != expected:
                raise ValueError('ZIP CRC/SHA readback differs: ' + name)
    with package_path.open('rb') as stream:
        package_sha = hashlib.file_digest(stream, 'sha256').hexdigest()
    delivery = dict(**summary, fileName=PACKAGE, bytes=package_path.stat().st_size, sha256=package_sha,
                    allZipMembersCrcAndSha256Verified=True, packageFileCount=len(inventory)+1,
                    url=f"https://github.com/BuShiGeMenn/BrickMore/releases/download/{replacement_manifest['releaseTag']}/{PACKAGE}")
    (output / 'full_preview_manifest.json').write_bytes(encode(delivery))
    (output / 'FULL_PREVIEW_SHA256SUMS.txt').write_text(f'{package_sha}  {PACKAGE}\n', encoding='ascii')
    print('COMPLETE SELF-CONTAINED PREVIEW', package_path, package_path.stat().st_size, flush=True)


if __name__ == '__main__':
    main()
