"""Prepare AI_B release and join immutable A/B model indexes without altering models."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import zipfile

from github_release import checksum

ROOT = Path(__file__).resolve().parent.parent
TAG = 'ai-b-40000-20261010-v1'


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    temporary.replace(path)


def prepare_b(source):
    manifest = json.loads((source/'manifest.json').read_text(encoding='utf8'))
    delivery = json.loads((source/'delivery_verification.json').read_text(encoding='utf8'))
    independent = json.loads((source/'independent_verification.json').read_text(encoding='utf8'))
    if not delivery['passed'] or manifest['modelCount'] != 40000 or manifest['promptRecordCount'] != 200000:
        raise ValueError('B dataset delivery incomplete')
    if independent['failureCount'] or independent['verifiedModelCount'] != 40000:
        raise ValueError('B independent verification incomplete')
    sums = {}
    for line in (source/'SHA256SUMS').read_text(encoding='utf8').splitlines():
        digest, relative = line.split('  ', 1)
        if relative in sums:
            raise ValueError('Duplicate checksum path')
        sums[relative] = digest
    expected = {p.relative_to(source).as_posix() for p in (source/'packages').glob('*.zip')}
    if set(sums) != expected or len(sums) != 41:
        raise ValueError('B archive/checksum inventory mismatch')
    assets = []
    # Full metadata must be extracted AFTER the model packages' per-package root indexes.
    for relative in sorted(sums, key=lambda name: ('metadata' in name.lower(), name)):
        path = source/relative
        if checksum(path) != sums[relative]:
            raise ValueError('Sealed B archive changed: ' + path.name)
        model_package = path.name.startswith('B_models_')
        row = {'name': path.name, 'bytes': path.stat().st_size, 'sha256': sums[relative],
               'url': f'https://github.com/BuShiGeMenn/BrickMore/releases/download/{TAG}/{path.name}',
               'kind': 'model_package' if model_package else 'metadata',
               'sourceRelativePath': relative}
        if model_package:
            row.update(modelCount=1000, promptRecordCount=5000)
        assets.append(row)
        print('B_ARCHIVE_SHA256', len(assets), '/41', path.name, flush=True)
    download = {'schemaVersion': 2, 'repository': 'BuShiGeMenn/BrickMore', 'shardId': 'B',
        'releaseTag': TAG, 'modelCount': 40000, 'promptRecordCount': 200000,
        'gridSize': [48, 48, 48], 'voxelCountRange': [750, 1250], 'modelPackageCount': 40,
        'totalDownloadBytes': sum(row['bytes'] for row in assets), 'assets': assets,
        'extractionOrder': 'model_package first, metadata last; use separate AI_A and AI_B roots'}
    target = ROOT/'datasets'/'AI_B'
    dump(target/'download_manifest.json', download)
    dump(target/'verification.json', {
        'sourceModelCount': 40000, 'sourcePromptRecordCount': 200000,
        'independentVerifiedModelCount': independent['verifiedModelCount'],
        'independentFailureCount': independent['failureCount'],
        'internalExactDuplicateCount': independent['exactDuplicateCount'],
        'internalCanonicalDuplicateCount': independent['canonicalDuplicateCount'],
        'archiveSha256VerifiedCount': len(assets),
        'archiveCrcVerification': 'prior complete readback bound to unchanged SHA-256 archives',
        'deliveryReportSha256': checksum(source/'delivery_verification.json'),
        'independentReportSha256': checksum(source/'independent_verification.json'),
        'historicalDedupStatus': 'original B evidence pending; see separate merge report',
        'fullPhysics': False})
    chosen = {}
    for row in manifest['models']:
        chosen.setdefault(row['category'], row)
    for category, row in chosen.items():
        folder = source/row['modelPath']
        destination = target/'samples'/row['modelPath']
        if destination.exists():
            for name in ('model.json','model.npz','model.obj','model.mtl','model.vox','preview.png','validation.json','prompts.json'):
                if checksum(folder/name) != checksum(destination/name):
                    raise ValueError('Existing sample differs: ' + row['modelId'])
        else:
            shutil.copytree(folder, destination)
    shutil.copyfile(source/'final_gallery.png', target/'preview_21_categories.png')
    print('B_RELEASE_PREPARED', len(manifest['models']), 'models', len(chosen), 'sample categories', flush=True)


def safe_relative(value):
    path = PurePosixPath(value.replace('\\', '/'))
    if path.is_absolute() or '..' in path.parts or ':' in str(path):
        raise ValueError('Unsafe model relative path')
    return path.as_posix()


def combined_index(a_rows, b_rows):
    result = []
    ids = set()
    for shard, rows in (('A', a_rows), ('B', b_rows)):
        for row in rows:
            mid = row['modelId']
            if mid in ids or f'_20261010_{shard}_' not in mid:
                raise ValueError('Duplicate or misassigned modelId: ' + mid)
            ids.add(mid)
            model_json = row.get('modelJsonPath') or row['modelPath'].rstrip('/') + '/model.json'
            model_json = 'AI_' + shard + '/' + safe_relative(model_json)
            result.append({k: row[k] for k in ('modelId', 'category', 'globalOrdinal', 'modelSeed',
                'actualVoxelCount', 'exactOccupancyHash', 'canonicalGeometryHash')})
            result[-1].update(shardId=shard, modelJsonPath=model_json,
                modelPath=str(PurePosixPath(model_json).parent),
                pairedPromptsPath=str(PurePosixPath(model_json).parent/'prompts.json'), promptRecordCount=5)
    return result


def verify_prompt_stream(stream, shard, rows, seen_record_ids):
    models = {row['modelId']: row for row in rows}
    masks = {}
    levels = Counter()
    digest = hashlib.sha256()
    count = 0
    for line in stream:
        digest.update(line)
        record = json.loads(line)
        mid, rid, level = record['modelId'], record['recordId'], record['promptLevel']
        if mid not in models or rid in seen_record_ids or record['shardId'] != shard or type(level) is not int or level not in (1,2,3,4,5):
            raise ValueError('Invalid or colliding prompt identity')
        row = models[mid]
        path = row.get('modelJsonPath') or row['modelPath'].rstrip('/') + '/model.json'
        if record['modelSeed'] != row['modelSeed'] or record['targetOccupancyHash'] != row['exactOccupancyHash'] or \
           record['targetCanonicalGeometryHash'] != row['canonicalGeometryHash'] or safe_relative(record['modelJsonPath']) != safe_relative(path):
            raise ValueError('Prompt references a different source geometry')
        if not record['sharesGeometryAcrossLevels'] or record['expectedIndependentGeometryAcrossLevels']:
            raise ValueError('Five levels do not declare shared geometry')
        if not all(isinstance(record[k], str) and record[k].strip() for k in ('captionZh','captionEn')):
            raise ValueError('Missing bilingual caption')
        bit = 1 << (level-1)
        if masks.get(mid, 0) & bit:
            raise ValueError('Duplicate prompt level for one model')
        masks[mid] = masks.get(mid, 0) | bit
        seen_record_ids.add(rid)
        levels[level] += 1
        count += 1
        if count % 50000 == 0:
            print('PROMPT_ASSOCIATION_READBACK', shard, count, flush=True)
    if set(masks) != set(models) or any(mask != 31 for mask in masks.values()):
        raise ValueError('Missing five-level prompt group')
    return {'recordCount': count, 'modelCount': len(models), 'levelCounts': dict(levels),
            'sourceJsonlSha256': digest.hexdigest(), 'allSourceGeometryAssociationsPassed': True}


def merge(source, a_metadata):
    a_release = json.loads((ROOT/'download_manifest.json').read_text(encoding='utf8'))
    a_asset = next(row for row in a_release['assets'] if row['name'] == 'metadata.zip')
    if checksum(a_metadata) != a_asset['sha256']:
        raise ValueError('A metadata does not match the published release SHA-256')
    with zipfile.ZipFile(a_metadata) as archive:
        with archive.open('dedup_index.jsonl') as stream:
            a_rows = [json.loads(line) for line in stream]
        a_manifest = json.loads(archive.read('manifest.json'))
    b_manifest = json.loads((source/'manifest.json').read_text(encoding='utf8'))
    with (source/'dedup_index.jsonl').open(encoding='utf8') as stream:
        b_rows = [json.loads(line) for line in stream]
    for rows, manifest in ((a_rows, a_manifest), (b_rows, b_manifest)):
        if len(rows) != 40000 or manifest['modelCount'] != 40000 or manifest['promptRecordCount'] != 200000:
            raise ValueError('Expected 40,000 models / 200,000 paired records in each shard')
        actual = {row['modelId']: row for row in rows}
        if len(actual) != 40000 or any(actual[row['modelId']] != row for row in manifest['models']):
            raise ValueError('Dedup index differs from model manifest')
    joined = combined_index(a_rows, b_rows)
    record_ids = set()
    with zipfile.ZipFile(a_metadata) as archive:
        with archive.open('all_prompts.jsonl') as stream:
            a_prompts = verify_prompt_stream(stream, 'A', a_rows, record_ids)
        historical_raw = archive.read('historical_models_55255.jsonl') if 'historical_models_55255.jsonl' in archive.namelist() else None
    b_zip = source/'packages'/'B_metadata.zip'
    with zipfile.ZipFile(b_zip) as archive:
        if hashlib.sha256(archive.read('dedup_index.jsonl')).hexdigest() != checksum(source/'dedup_index.jsonl'):
            raise ValueError('B source index differs from the sealed delivery archive')
        with archive.open('all_prompts.jsonl') as stream:
            b_prompts = verify_prompt_stream(stream, 'B', b_rows, record_ids)
    if len(record_ids) != 400000 or a_prompts['recordCount'] != 200000 or b_prompts['recordCount'] != 200000:
        raise ValueError('Incomplete merged prompt inventory')
    overlap = {}
    for field in ('exactOccupancyHash', 'canonicalGeometryHash'):
        left = {row[field]: row['modelId'] for row in a_rows}
        right = {row[field]: row['modelId'] for row in b_rows}
        both = sorted(set(left) & set(right))
        overlap[field] = {'crossShardDuplicateHashCount': len(both),
            'mergedUniqueHashCount': len(set(left) | set(right)),
            'examples': [{'AI_A': left[h], 'AI_B': right[h], 'hash': h} for h in both[:20]]}
    report = {'modelCount': len(joined), 'uniqueModelIdCount': len({r['modelId'] for r in joined}),
        'promptRecordCount': len(record_ids), 'uniqueRecordIdCount': len(record_ids),
        'sourcePromptReadback': {'A': a_prompts, 'B': b_prompts},
        'shardModelCounts': {'A': 40000, 'B': 40000},
        'modelIdCollisionCount': 0, 'sourceFileOverwrites': 0,
        'categoryModelCounts': dict(Counter(row['category'] for row in joined)),
        'aPublishedMetadataSha256': a_asset['sha256'], 'bDedupIndexSha256': checksum(source/'dedup_index.jsonl'),
        'hashAlgorithm': 'sha256 sorted x,y,z semicolon; canonical minimum over 48 axis/sign transforms normalized to minima',
        'crossShardHashChecks': overlap,
        'crossShardExactAndCanonicalDedupPassed': all(v['crossShardDuplicateHashCount'] == 0 for v in overlap.values()),
        'scope': 'Full A/B model indexes; immutable source models preserved; near-shape/historical checks not implied',
        'crossShardNearDuplicateStatus': 'not_run', 'historicalCanonicalDedupStatus': 'unavailable_coordinates',
        'fullPhysics': False}
    if historical_raw is not None:
        historic = [json.loads(line) for line in historical_raw.splitlines()]
        historic_hashes = {row['exactOccupancyHash'] for row in historic}
        current_hashes = {row['exactOccupancyHash'] for row in joined}
        report['historicalExactDedup'] = {
            'indexRecordCount': len(historic), 'indexSha256': hashlib.sha256(historical_raw).hexdigest(),
            'overlappingHashCount': len(historic_hashes & current_hashes),
            'passed': not (historic_hashes & current_hashes),
            'scope': 'Exact occupancy only; historical coordinates unavailable for canonical/near-shape comparisons'}
    destination = ROOT/'datasets'/'model_index.jsonl'
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix('.jsonl.tmp')
    with temporary.open('w', encoding='utf8', newline='\n') as stream:
        for row in joined:
            stream.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
    temporary.replace(destination)
    report['mergedIndexSha256'] = checksum(destination)
    dump(ROOT/'datasets'/'merge_report.json', report)
    b_release = json.loads((ROOT/'datasets'/'AI_B'/'download_manifest.json').read_text(encoding='utf8'))
    catalog = {'schemaVersion': 1, 'repository': 'BuShiGeMenn/BrickMore', 'modelCount': 80000,
        'promptRecordCount': 400000, 'modelIndexPath': 'datasets/model_index.jsonl',
        'mergeReportPath': 'datasets/merge_report.json',
        'totalDownloadBytes': a_release['totalDownloadBytes'] + b_release['totalDownloadBytes'],
        'shards': [{'shardId': 'A', 'rootDirectory': 'AI_A', 'manifestPath': 'download_manifest.json',
                    'modelCount': 40000, 'promptRecordCount': 200000},
                   {'shardId': 'B', 'rootDirectory': 'AI_B', 'manifestPath': 'datasets/AI_B/download_manifest.json',
                    'modelCount': 40000, 'promptRecordCount': 200000}]}
    dump(ROOT/'dataset_catalog.json', catalog)
    print('MERGE_INDEX_VERIFIED', json.dumps({k: report[k] for k in ('modelCount', 'promptRecordCount',
          'modelIdCollisionCount', 'crossShardExactAndCanonicalDedupPassed', 'crossShardHashChecks')}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare-b', 'merge'))
    parser.add_argument('--b', type=Path, required=True)
    parser.add_argument('--a-metadata', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare-b':
        prepare_b(args.b)
    else:
        if args.a_metadata is None:
            parser.error('--a-metadata required')
        merge(args.b, args.a_metadata)


if __name__ == '__main__':
    main()
