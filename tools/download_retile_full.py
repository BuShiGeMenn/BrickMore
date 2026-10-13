"""Download and independently verify all 80,000 mixed-version retile outcomes."""
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
_auditors={}

def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def inside(root,relative):
    if ':' in relative or relative.startswith(('/','\\')):raise ValueError('Unsafe release path')
    path=(Path(root)/relative).resolve()
    if not path.is_relative_to(Path(root).resolve()):raise ValueError('Release path traversal')
    return path
def initialize(directory):
    global _auditors
    source=Path(directory)/'source_snapshot'
    config=json.loads((Path(directory)/'run_plan.json').read_bytes())
    for name,expected in config['sourceCodeSha256'].items():
        if digest(inside(source,name))!=expected:raise ValueError('Frozen runtime source differs')
    for name,folder,file in [('previous','voxel_assembly_retile','retile_pipeline.py'),('fresh','voxel_assembly_retile_full','full_pipeline.py')]:
        path=source/'algorithms'/folder/file;sys.path.insert(0,str(path.parent))
        spec=importlib.util.spec_from_file_location('sealed_full_'+name,path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);_auditors[name]=module
def verify_one(item):
    directory,row,original=item
    kept=row['category'] in ('piano','table')
    report=_auditors['previous' if kept else 'fresh'].verify(inside(directory,row['reportRelativePath']).parent)
    if digest(inside(directory,row['reportRelativePath']))!=row['reportSha256']:raise ValueError('Result report SHA differs')
    if report['modelId']!=row['modelId'] or report['sourceFileSha256']!=original['sourceFileSha256']:raise ValueError('Original identity/bytes differ')
    if report['geometryValidation']['passed']!=row['geometryPassed'] or report['qualityScreenedSuccess']!=row['qualityScreenedSuccess']:raise ValueError('Result index flags differ')
    if report['physics']['status']!=row['physicsStatus']:raise ValueError('Physics index differs')
    if row['freshSearchAttempted']==kept:raise ValueError('Rerun/preservation scope differs')
    if not kept:
        decision=report['searchAttempts'][0]
        if decision['stage']!='fresh_retile_before_success_fallback' or not decision['freshSearchAttempted']:raise ValueError('Required fresh search missing')
        if decision['freshGeometryPassed']!=row['freshGeometryPassed']:raise ValueError('Fresh outcome index differs')
    return row['shardId']+'_'+row['category'],row['geometryPassed'],row['baselinePassed'],not kept
def verify(directory,manifest,workers):
    for asset in manifest['assets']:
        inventory=json.loads(inside(directory,asset['fileHashManifest']).read_bytes())
        for name,expected in inventory.items():
            if digest(inside(directory,name))!=expected:raise ValueError('Extracted SHA differs: '+name)
    rows=[json.loads(line) for line in (directory/'assembly_index.jsonl').read_text(encoding='utf-8').splitlines()]
    sources={r['modelId']:r for r in json.loads((directory/'source_index.json').read_bytes())['models']}
    ids={r['modelId'] for r in rows}
    if len(rows)!=80000 or len(ids)!=80000 or ids!=set(sources):raise ValueError('Incomplete or duplicate model population')
    groups=Counter();passed=Counter();baseline=Counter();fresh=0
    with ProcessPoolExecutor(max_workers=workers,initializer=initialize,initargs=(directory,)) as pool:
        for number,(group,success,before,rerun) in enumerate(pool.map(verify_one,[(directory,r,sources[r['modelId']]) for r in rows],chunksize=16),1):
            groups[group]+=1;passed[group]+=success;baseline[group]+=before;fresh+=rerun
            if number%5000==0:print('ACTUAL_FILE_READBACK',number,flush=True)
    summary=json.loads((directory/'summary.json').read_bytes())
    for group,value in summary['categoryCounts'].items():
        if (groups[group],passed[group],baseline[group])!=(value['modelCount'],value['geometryPassed'],value['baselinePassed']):raise ValueError('Actual category counts differ')
    if not summary['complete'] or sum(passed.values())!=summary['geometryPassed'] or fresh!=72380:raise ValueError('Actual summary/scope differs')
    preservation=json.loads((directory/'preserved_categories_verification.json').read_bytes())
    if preservation['modelCount']!=7620 or not preservation['allFileBytesIdentical'] or preservation['reassembled']:raise ValueError('Preservation proof differs')
    print('VERIFIED 80000 models:',sum(passed.values()),'geometry passes; 72380 fresh searches; 7620 preserved',flush=True)
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('retile_full_latest'))
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--extract',action='store_true')
    parser.add_argument('--verify-only',action='store_true')
    args=parser.parse_args()
    if args.workers<1:parser.error('workers must be positive')
    manifest=json.loads((ROOT/'datasets/retile_assembly_80000/download_manifest.json').read_bytes())
    args.output.mkdir(parents=True,exist_ok=True)
    if args.verify_only:verify(args.output,manifest,args.workers);return
    packages=args.output/'packages';packages.mkdir(exist_ok=True)
    def fetch(asset):
        path=download.download(asset,packages)
        if args.extract:download.extract(path,args.output)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(fetch,[a for a in manifest['assets'] if a['kind']=='model_package']))
    for asset in manifest['assets']:
        if asset['kind']=='metadata':fetch(asset)
    if args.extract:verify(args.output,manifest,args.workers)
    else:print('DOWNLOAD_SHA256_VERIFIED',len(manifest['assets']),'assets',flush=True)

if __name__=='__main__':main()
