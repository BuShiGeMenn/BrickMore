"""Download the latest two-category assembly release with exact-file checks."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor,ThreadPoolExecutor
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import download_dataset as download

ROOT=Path(__file__).resolve().parent.parent
_pipeline=None

def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def inside(root,relative):
    if ':' in relative or relative.startswith(('/','\\')):raise ValueError('Unsafe release path')
    path=(Path(root)/relative).resolve()
    if not path.is_relative_to(Path(root).resolve()):raise ValueError('Release path traversal')
    return path

def check_files(directory,manifest):
    for asset in manifest['assets']:
        inventory=json.loads(inside(directory,asset['fileHashManifest']).read_bytes())
        for name,sha in inventory.items():
            if digest(inside(directory,name))!=sha:raise ValueError('Extracted file SHA differs: '+name)

def initialize(directory):
    global _pipeline
    directory=Path(directory);source=directory/'source_snapshot'
    config=json.loads((directory/'run_plan.json').read_bytes())
    for name,expected in config['sourceCodeSha256'].items():
        if digest(inside(source,name))!=expected:raise ValueError('Frozen audit source differs')
    module_path=source/'algorithms'/'voxel_assembly_retile'/'retile_pipeline.py'
    sys.path.insert(0,str(module_path.parent))
    spec=importlib.util.spec_from_file_location('sealed_retile_pipeline',module_path)
    _pipeline=importlib.util.module_from_spec(spec);spec.loader.exec_module(_pipeline)

def verify_one(item):
    directory,row,source_row=item
    report=_pipeline.verify(inside(directory,row['reportRelativePath']).parent)
    if digest(inside(directory,row['reportRelativePath']))!=row['reportSha256']:raise ValueError('Result report SHA differs')
    if report['sourceFileSha256']!=source_row['sourceFileSha256']:raise ValueError('Original published model association differs')
    if report['geometryValidation']['passed']!=row['geometryPassed'] or report['qualityScreenedSuccess']!=row['qualityScreenedSuccess']:raise ValueError('Result index flags differ')
    if report['physics']['status']!=row['physicsStatus']:raise ValueError('Physical result index differs')
    return (row['shardId']+'_'+row['category'],row['geometryPassed'],row['baselinePassed'])

def verify(directory,manifest,workers):
    check_files(directory,manifest)
    rows=[json.loads(line) for line in (directory/'assembly_index.jsonl').read_text(encoding='utf-8').splitlines()]
    sources={r['modelId']:r for r in json.loads((directory/'source_index.json').read_bytes())['models']}
    if len(rows)!=7620 or len({r['modelId'] for r in rows})!=7620 or set(sources)!={r['modelId'] for r in rows}:raise ValueError('Incomplete or duplicate model identities')
    groups=Counter();passed=Counter();baseline=Counter()
    with ProcessPoolExecutor(max_workers=workers,initializer=initialize,initargs=(directory,)) as pool:
        for number,(group,success,before) in enumerate(pool.map(verify_one,[(directory,r,sources[r['modelId']]) for r in rows],chunksize=16),1):
            groups[group]+=1;passed[group]+=success;baseline[group]+=before
            if number%1000==0:print('ACTUAL_FILE_READBACK',number,flush=True)
    summary=json.loads((directory/'summary.json').read_bytes())
    for group,value in summary['categoryCounts'].items():
        if (groups[group],passed[group],baseline[group])!=(value['modelCount'],value['geometryPassed'],value['baselinePassed']):raise ValueError('Actual category counts differ')
    if sum(passed.values())!=7485 or summary['geometryPassed']!=7485:raise ValueError('Actual geometry success count differs')
    print('VERIFIED',len(rows),'models;',sum(passed.values()),'geometry successes;',len(rows)-sum(passed.values()),'explicit drafts',flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('piano_table_latest'))
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--extract',action='store_true')
    parser.add_argument('--verify-only',action='store_true',help='Verify an already extracted complete delivery')
    args=parser.parse_args()
    if args.workers<1:parser.error('workers must be positive')
    manifest=json.loads((ROOT/'datasets'/'piano_table_retile_7620'/'download_manifest.json').read_bytes())
    args.output.mkdir(parents=True,exist_ok=True)
    if args.verify_only:verify(args.output,manifest,args.workers);return
    packages=args.output/'packages';packages.mkdir(exist_ok=True)
    def fetch(asset):
        path=download.download(asset,packages)
        if args.extract:download.extract(path,args.output)
    models=[a for a in manifest['assets'] if a['kind']=='model_package']
    with ThreadPoolExecutor(max_workers=args.workers) as pool:list(pool.map(fetch,models))
    for asset in manifest['assets']:
        if asset['kind']=='metadata':fetch(asset)
    if args.extract:verify(args.output,manifest,args.workers)
    else:print('DOWNLOAD_SHA256_VERIFIED',len(manifest['assets']),'assets',flush=True)

if __name__=='__main__':main()
