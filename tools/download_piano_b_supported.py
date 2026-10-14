"""Download regenerated B pianos and verify their actual training/layout files."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import download_dataset as common
ROOT=Path(__file__).resolve().parents[1]

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def inside(root,name):
    p=(root/name).resolve()
    if not p.is_relative_to(root.resolve()):raise ValueError('Unsafe release member')
    return p
def verify(root,manifest):
    for asset in manifest['assets']:
        inventory=json.loads(inside(root,asset['fileHashManifest']).read_bytes())
        for name,expected in inventory.items():
            if sha(inside(root,name))!=expected:raise ValueError('Extracted file SHA differs: '+name)
    source=root/'source_snapshot';config=json.loads((root/'run_plan.json').read_bytes())
    for name,expected in config['sourceCodeSha256'].items():
        if sha(inside(source,name))!=expected:raise ValueError('Frozen audit source differs')
    path=source/'algorithms/voxel_piano_b_support/pipeline.py';sys.path.insert(0,str(path.parent))
    spec=importlib.util.spec_from_file_location('frozen_supported_piano_pipeline',path);audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
    rows=[json.loads(line) for line in (root/'training/passed_model_index.jsonl').read_text(encoding='utf-8').splitlines()]
    if len(rows)!=1905 or len({r['modelId'] for r in rows})!=1905:raise ValueError('Training model population differs')
    for row in rows:
        report=audit.verify(inside(root,row['reportPath']).parent)
        if not report['geometryValidation']['passed'] or any(report['repairAudit'][k] for k in ('addedVoxelCount','removedVoxelCount','recoloredOriginalVoxelCount')):raise ValueError('Non-exact or failed training target')
        if sha(inside(root,row['voxelModelPath']))!=row['voxelFileSha256'] or sha(inside(root,row['reportPath']))!=row['reportSha256']:raise ValueError('Training path/hash association differs')
    prompts=[json.loads(line) for line in (root/'training/passed_prompt_records.jsonl').read_text(encoding='utf-8').splitlines()]
    if len(prompts)!=9525 or len({p['recordId'] for p in prompts})!=9525:raise ValueError('Training record population differs')
    by_id={r['modelId']:r for r in rows};levels={mid:set() for mid in by_id}
    for p in prompts:
        model=by_id[p['modelId']];levels[p['modelId']].add(p['promptLevel'])
        if p['modelJsonPath']!=model['voxelModelPath'] or p['targetOccupancyHash']!=model['occupancyHash'] or p['targetCanonicalGeometryHash']!=model['canonicalGeometryHash']:raise ValueError('Prompt targets wrong geometry')
        if p['assemblyJsonPath']!=model['assemblyJsonPath'] or p['ldrPath']!=model['ldrPath']:raise ValueError('Prompt targets wrong assembly')
    if any(v!={1,2,3,4,5} for v in levels.values()):raise ValueError('Missing prompt level')
    print('VERIFIED 1905 exact B pianos and 9525 correctly paired prompt records',flush=True)
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=Path('piano_b_supported'));parser.add_argument('--extract',action='store_true');parser.add_argument('--verify-only',action='store_true');args=parser.parse_args()
    manifest=json.loads((ROOT/'datasets/piano_b_supported_1905/download_manifest.json').read_bytes());args.output.mkdir(parents=True,exist_ok=True)
    if args.verify_only:verify(args.output,manifest);return
    packages=args.output/'packages';packages.mkdir(exist_ok=True)
    for asset in manifest['assets']:
        path=common.download(asset,packages)
        if args.extract:common.extract(path,args.output)
    if args.extract:verify(args.output,manifest)

if __name__=='__main__':main()
