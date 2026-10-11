"""Download sealed assembly outcomes and optionally verify every extracted model."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

import download_dataset as d
import package_assembly as p


def inside(root,relative):
    if ':' in relative or relative.startswith(('/', '\\')):
        raise ValueError('unsafe published index path')
    path=(root/relative).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('published index traversal')
    return path


def verify(directory,shards):
    counts=Counter();ids=set();record_ids=set()
    with (directory/'assembly_index.jsonl').open(encoding='utf8') as stream:
        for line in stream:
            row=json.loads(line)
            if row['shardId'] not in shards:continue
            if row['modelId'] in ids:raise ValueError('duplicate model ID')
            ids.add(row['modelId'])
            report_path=inside(directory,row['reportPath'])
            if p.digest(report_path)!=row['reportFileSha256']:raise ValueError('published report SHA mismatch')
            report=json.loads(report_path.read_bytes())
            folder=inside(directory,row['resultPath'])
            files={name:inside(folder,name).read_bytes() for name in report['outputFileSha256']}
            if not all(p.a.sha(files[n])==h for n,h in report['outputFileSha256'].items()):raise ValueError('published output/source SHA mismatch')
            if report['sourceExactOccupancyHash']!=row['sourceExactOccupancyHash'] or report['sourceCanonicalGeometryHash']!=row['sourceCanonicalGeometryHash']:
                raise ValueError('published target association mismatch')
            prompts=p.check_prompts(files['source.prompts.json'],{'modelId':row['modelId'],
                'exactOccupancyHash':row['sourceExactOccupancyHash'],'canonicalGeometryHash':row['sourceCanonicalGeometryHash']})
            if set(prompts)&record_ids:raise ValueError('duplicate prompt record ID')
            record_ids.update(prompts)
            result=p.payload_audit(files)
            if result!=report['validation'] or result!=json.loads(files['validation.json']) or result['passed']!=row['geometryPassed']:
                raise ValueError('extracted independent readback mismatch')
            if not result['txtReadbackMatches'] or not result['ldrReadbackMatches']:
                raise ValueError('draft export mismatch')
            counts[row['status']]+=1
            if len(ids)%1000==0:print('ASSEMBLY_READBACK',len(ids),flush=True)
    if len(ids)!=40000*len(shards) or len(record_ids)!=200000*len(shards):
        raise ValueError('extracted shard/model/prompt count mismatch')
    print('ASSEMBLY_VERIFIED',len(ids),'models',len(record_ids),'records',dict(counts),flush=True)
    return dict(counts)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shard',choices=('A','B','all'),default='all')
    parser.add_argument('--output',type=Path,default=Path('assembly_80000'))
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--extract',action='store_true',help='Safe extraction and independent actual-file readback for all selected models')
    args=parser.parse_args()
    if args.workers<1:parser.error('workers must be positive')
    manifest=json.loads((p.ROOT/'datasets'/'assembly_80000'/'download_manifest.json').read_bytes())
    shards=('A','B') if args.shard=='all' else (args.shard,)
    packages=args.output/'packages';packages.mkdir(parents=True,exist_ok=True)
    def fetch(asset):
        path=d.download(asset,packages)
        if args.extract:d.extract(path,args.output)
    models=[r for r in manifest['assets'] if r['kind']=='assembly_package' and r['shardId'] in shards]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:list(pool.map(fetch,models))
    for asset in manifest['assets']:
        if asset['kind']=='metadata':fetch(asset)
    if args.extract:verify(args.output,shards)
    else:print('ASSEMBLY_DOWNLOAD_SHA256_VERIFIED',len(models)+1,'assets',flush=True)


if __name__=='__main__':main()
