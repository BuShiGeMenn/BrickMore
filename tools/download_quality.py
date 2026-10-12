"""Download Q4 outcomes; read back actual repair/geometry/physics and original prompts."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

import package_quality as p
import download_dataset as d


def inside(root,name):
    if ':' in name or '\\' in name or name.startswith('/') or '..' in Path(name).parts:raise ValueError('unsafe public Q4 path')
    path=(root/name).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('public Q4 index traversal')
    return path


def verify(directory,shards):
    ids=set();records=set();rows=[]
    for line in (directory/'assembly_index.jsonl').read_text(encoding='utf8').splitlines():
        row=json.loads(line)
        if row['shardId'] not in shards:continue
        if row['modelId'] in ids:raise ValueError('duplicate Q4 model ID')
        ids.add(row['modelId']);folder=inside(directory,row['resultPath'])
        report_data=inside(directory,row['reportPath']).read_bytes()
        if p.q.a.sha(report_data)!=row['reportFileSha256']:raise ValueError('public Q4 report SHA mismatch')
        report=json.loads(report_data)
        files={name:inside(folder,name).read_bytes() for name in report['outputFileSha256']};files['report.json']=report_data
        checked,new_records=p.audit_payload(files)
        if checked['status']!=row['status'] or checked['qualityScreenedSuccess']!=row['qualityScreenedSuccess'] or new_records!=row['sourcePromptRecordIds']:raise ValueError('published Q4 readback disagreement')
        if records.intersection(new_records):raise ValueError('duplicate original prompt record')
        records.update(new_records);rows.append(row)
        if len(ids)%1000==0:print('Q4_PUBLIC_READBACK',len(ids),flush=True)
    if len(ids)!=40000*len(shards) or len(records)!=200000*len(shards):raise ValueError('incomplete extracted census')
    print('Q4_EXTRACTED_VERIFIED',json.dumps(p.counts(rows)),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,default=p.ROOT/'datasets'/'q4_assembly_80000'/'download_manifest.json')
    parser.add_argument('--output',type=Path,default=Path('q4_assembly_80000'))
    parser.add_argument('--shard',choices=('A','B','all'),default='all');parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--extract',action='store_true');args=parser.parse_args()
    if not 1<=args.workers<=8:parser.error('workers must be in 1..8')
    manifest=json.loads(args.manifest.read_bytes());shards=('A','B') if args.shard=='all' else (args.shard,)
    if manifest['repository']!='BuShiGeMenn/BrickMore' or manifest['modelCount']!=80000 or manifest['assetCount']!=81:parser.error('unexpected delivery manifest')
    packages=args.output/'packages';packages.mkdir(parents=True,exist_ok=True)
    def fetch(asset):
        path=d.download(asset,packages)
        if args.extract:d.extract(path,args.output)
    models=[a for a in manifest['assets'] if a['kind']=='assembly_package' and a['shardId'] in shards]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:list(pool.map(fetch,models))
    for asset in manifest['assets']:
        if asset['kind']=='metadata':fetch(asset)
    if args.extract:verify(args.output,shards)
    else:print('Q4_DOWNLOAD_SHA_VERIFIED',len(models)+1,flush=True)


if __name__=='__main__':main()
