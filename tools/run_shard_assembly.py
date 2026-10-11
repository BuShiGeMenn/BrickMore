"""Run all assembly stages in order; any failed check stops before delivery.

No automatic upload. Publication requires both A/B sealed package proofs.
"""
import argparse
from pathlib import Path
import subprocess
import sys
import time
import download_dataset as d
import package_assembly as delivery

ROOT=Path(__file__).resolve().parent.parent
ALGORITHM=ROOT/'algorithms'/'voxel_assembly_b'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--shard',choices=('A','B'),required=True)
    p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--delivery',type=Path,required=True)
    p.add_argument('--workers',type=int,default=16)
    p.add_argument('--package-workers',type=int,default=8)
    p.add_argument('--wait-source',action='store_true',help='Wait for an already-running verified source download to finish')
    args=p.parse_args()
    if min(args.workers,args.package_workers)<1:p.error('workers must be positive')
    manifest=args.dataset/'manifest.json'
    source_manifest=d.get_manifest(args.shard)
    def available():
        return manifest.is_file() and all((args.dataset/'packages'/asset['name']).is_file()
                                         for asset in source_manifest['assets'])
    if args.wait_source:
        print('WAITING_FOR_COMPLETE_SOURCE',args.shard,flush=True)
        while not available():time.sleep(10)
    if not manifest.is_file():p.error('extract and verify the original source dataset first')
    checked=[]
    for asset in source_manifest['assets']:
        path=args.dataset/'packages'/asset['name']
        if not path.is_file() or path.stat().st_size!=asset['bytes'] or d.checksum(path)!=asset['sha256']:
            p.error('original source package missing or SHA mismatch: '+asset['name'])
        checked.append({'name':asset['name'],'bytes':asset['bytes'],'sha256':asset['sha256']})
    d.verify_extracted(args.dataset,source_manifest)
    delivery.a.dump(args.out/'source_input_verification.json',{
        'shardId':args.shard,'modelCount':40000,'promptRecordCount':200000,
        'allSourcePackageSizesAndSha256Passed':True,'allEightOriginalModelFilesPresent':True,
        'sourceManifestSha256':d.checksum(manifest),'assets':checked})
    print('COMPLETE_SOURCE_VERIFIED',args.shard,flush=True)
    base=args.out/'runs'/f'{args.shard}_extended_v3'
    pilot=args.out/'runs'/f'{args.shard}_pilot_v3'
    refinement=args.out/'runs'/f'{args.shard}_layer_refinement_v1'
    def invoke(script,*parameters):
        command=[sys.executable,'-B',str(script),*map(str,parameters)]
        print('ASSEMBLY_STAGE',script.name,' '.join(map(str,parameters[:1])),flush=True)
        subprocess.run(command,cwd=ROOT,check=True)
    common=['--dataset',args.dataset,'--workers',args.workers]
    for action in ('pilot','verify'):
        invoke(ALGORITHM/'assembly_pipeline.py',action,*common,'--out',pilot)
    for action in ('run','verify'):
        invoke(ALGORITHM/'assembly_pipeline.py',action,*common,'--out',base)
    for action in ('run','verify'):
        invoke(ALGORITHM/'layer_cover.py',action,'--base',base,'--out',refinement,'--workers',args.workers)
    invoke(ROOT/'tools'/'package_assembly.py','export','--shard',args.shard,'--base',base,
           '--refinement',refinement,'--out',args.delivery,'--workers',args.package_workers)
    print('SHARD_ASSEMBLY_AND_PUBLIC_READBACK_COMPLETE',args.shard,flush=True)


if __name__=='__main__':main()
