"""Read back a real B model archive after the new namespaced extraction."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

import download_dataset as d
from github_release import checksum
from merge_shards import ROOT, dump


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error('choose a new output directory')
    with zipfile.ZipFile(args.package) as archive:
        if archive.testzip() is not None:
            raise ValueError('Archive CRC failed')
        original = json.loads(archive.read('manifest.json'))
    d.extract(args.package, args.out, 'model_package', 'B')
    index_path = args.out/'package_indexes'/args.package.stem/'manifest.json'
    index = json.loads(index_path.read_text(encoding='utf8'))
    if index != original or (args.out/'manifest.json').exists():
        raise ValueError('B package root index was overwritten or misplaced')
    records = 0
    record_ids = set()
    for row in index['models']:
        folder = args.out/row['modelPath']
        expected = {'model.json','model.npz','model.obj','model.mtl','model.vox','preview.png','validation.json','prompts.json'}
        if {p.name for p in folder.iterdir()} != expected:
            raise ValueError('Eight-file inventory mismatch')
        model = json.loads((folder/'model.json').read_text(encoding='utf8'))
        points = sorted((v['x'], v['y'], v['z']) for v in model['voxels'])
        digest = hashlib.sha256(';'.join(','.join(map(str, p)) for p in points).encode()).hexdigest()
        if model['modelId'] != row['modelId'] or digest != row['exactOccupancyHash']:
            raise ValueError('Model identity or occupancy changed')
        paired = json.loads((folder/'prompts.json').read_text(encoding='utf8'))
        if len(paired) != 5 or {r['promptLevel'] for r in paired} != {1,2,3,4,5}:
            raise ValueError('Five-level prompt association incomplete')
        for record in paired:
            if record['modelId'] != row['modelId'] or record['recordId'] in record_ids:
                raise ValueError('Prompt identity collision')
            record_ids.add(record['recordId'])
            records += 1
    if len(index['models']) != 1000 or records != 5000:
        raise ValueError('Incomplete real package')
    report = {'passed': True, 'archive': args.package.name, 'archiveSha256': checksum(args.package),
              'crcPassed': True, 'actualExtractedModelCount': 1000, 'actualPromptRecordCount': records,
              'eightFileInventoriesPassed': True, 'exactOccupancyHashesPassed': True,
              'packageIndexNamespaced': True, 'fullMetadataNotOverwritten': True, 'fullPhysics': False}
    dump(ROOT/'datasets'/'AI_B'/'package_smoke_test.json', report)
    print('REAL_B_PACKAGE_VERIFIED', json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
