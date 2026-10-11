"""Download the complete public release, check SHA-256, optionally extract it."""
import argparse,hashlib,json,os,shutil,sys,time,urllib.error,urllib.request,zipfile,zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent

def checksum(path):
    with path.open('rb') as handle:return hashlib.file_digest(handle,'sha256').hexdigest()

def download(asset,directory):
    target=directory/asset['name'];partial=target.with_name(target.name+'.part')
    if target.exists() and target.stat().st_size==asset['bytes'] and checksum(target)==asset['sha256']:
        print('Verified existing',target.name,flush=True);return target
    for attempt in range(1,6):
        try:
            offset=partial.stat().st_size if partial.exists() else 0
            if offset>asset['bytes']:raise ValueError('Partial file exceeds expected size: '+partial.name)
            if offset<asset['bytes']:
                headers={'User-Agent':'BrickMore-dataset-downloader'}
                if offset:headers['Range']=f'bytes={offset}-'
                req=urllib.request.Request(asset['url'],headers=headers)
                with urllib.request.urlopen(req,timeout=120) as response:
                    resumed=bool(offset and response.status==206 and response.headers.get('Content-Range','').startswith(f'bytes {offset}-'))
                    with partial.open('ab' if resumed else 'wb') as handle:
                        while True:
                            chunk=response.read(1024*1024)
                            if not chunk:break
                            handle.write(chunk)
            if partial.stat().st_size<asset['bytes']:
                raise ConnectionError('Truncated download; resume from '+str(partial.stat().st_size)+' bytes: '+partial.name)
            if partial.stat().st_size!=asset['bytes'] or checksum(partial)!=asset['sha256']:
                raise ValueError('Downloaded file checksum mismatch: '+partial.name)
            os.replace(partial,target);print('Downloaded and verified',target.name,flush=True);return target
        except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,OSError) as exc:
            if isinstance(exc,urllib.error.HTTPError) and exc.code==404:
                raise RuntimeError('The release or asset is unavailable: '+asset['url']) from exc
            if attempt==5:raise
            print('Retry',attempt,target.name,str(exc),flush=True);time.sleep(min(15,attempt*3))

def extract(path,destination,kind=None,shard=None):
    root=destination.resolve()
    with zipfile.ZipFile(path) as archive:
        targets=[]
        for info in archive.infolist():
            name=info.filename.replace('\\','/')
            # B archives preserve the original per-package root indexes. Namespace
            # those indexes so none overwrites the full dataset manifest/prompts.
            if shard=='B' and kind=='model_package' and not name.startswith('models/'):
                name='package_indexes/'+path.stem+'/'+name
            if ':' in name or name.startswith('/'):
                raise ValueError('Unsafe archive path: '+name)
            target=(destination/name).resolve()
            if not target.is_relative_to(root):raise ValueError('Unsafe archive path: '+name)
            if (info.external_attr>>16)&0o170000==0o120000:raise ValueError('Archive symlink rejected: '+name)
            targets.append((info,target))
        # Refuse conflicting existing files; do not silently overwrite local data.
        for info,target in targets:
            if info.is_dir():
                if target.exists() and not target.is_dir():raise ValueError('Existing non-directory: '+str(target))
                continue
            if target.exists():
                if not target.is_file() or target.stat().st_size!=info.file_size:
                    raise ValueError('Existing file conflicts with archive: '+str(target))
                crc=0
                with target.open('rb') as stream:
                    for chunk in iter(lambda:stream.read(1024*1024),b''):crc=zlib.crc32(chunk,crc)
                if crc!=info.CRC:raise ValueError('Existing file conflicts with archive: '+str(target))
        for info,target in targets:
            if info.is_dir():target.mkdir(parents=True,exist_ok=True);continue
            if target.exists():continue
            target.parent.mkdir(parents=True,exist_ok=True)
            with archive.open(info) as source,target.open('xb') as output:
                shutil.copyfileobj(source,output,1024*1024)
    print('Extracted',path.name,flush=True)

def verify_extracted(directory,manifest):
    data=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    if data['modelCount']!=manifest['modelCount'] or data['promptRecordCount']!=manifest['promptRecordCount']:
        raise ValueError('Extracted dataset counts disagree with download manifest')
    ids=set()
    for row in data['models']:
        if row['modelId'] in ids:raise ValueError('Duplicate modelId')
        ids.add(row['modelId'])
        relative=row.get('modelJsonPath') or row['modelPath']+'/model.json'
        folder=(directory/relative).resolve().parent
        if not folder.is_relative_to(directory.resolve()):raise ValueError('Unsafe model path')
        if not all((folder/name).is_file() for name in ['model.json','model.npz','model.obj','model.mtl','model.vox','preview.png','validation.json','prompts.json']):
            raise ValueError('Missing model assets: '+row['modelId'])
    if len(ids)!=manifest['modelCount']:raise ValueError('Extracted index is incomplete')
    print('Complete dataset extracted:',data['modelCount'],'models /',data['promptRecordCount'],'bilingual records',flush=True)
    return data

def get_manifest(shard):
    path=ROOT/'download_manifest.json' if shard=='A' else ROOT/'datasets'/'AI_B'/'download_manifest.json'
    return json.loads(path.read_text(encoding='utf-8'))

def run_shard(shard,directory,do_extract,workers=1):
    manifest=get_manifest(shard)
    directory.mkdir(parents=True,exist_ok=True);downloads=directory/'packages';downloads.mkdir(exist_ok=True)
    print('Shard:',shard,'Files:',len(manifest['assets']),'Total GB:',round(manifest['totalDownloadBytes']/1e9,2),flush=True)
    def fetch(asset):
        path=download(asset,downloads)
        if do_extract and path.suffix=='.zip':extract(path,directory,asset['kind'],shard)
    # Model packages have disjoint paths. Finish all of them before extracting
    # authoritative metadata, regardless of concurrent download completion order.
    packages=[row for row in manifest['assets'] if row['kind']!='metadata']
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(fetch,packages))
    for asset in manifest['assets']:
        if asset['kind']=='metadata':fetch(asset)
    return verify_extracted(directory,manifest) if do_extract else None

def join_extracted(directory,shard_data):
    rows=[];ids=set()
    for shard,data in shard_data.items():
        for row in data['models']:
            if row['modelId'] in ids:raise ValueError('Cross-shard modelId collision')
            ids.add(row['modelId'])
            relative=row.get('modelJsonPath') or row['modelPath']+'/model.json'
            model_path='AI_'+shard+'/'+relative.replace('\\','/')
            updated={**row,'shardId':shard,'modelJsonPath':model_path,
                     'modelPath':str(Path(model_path).parent).replace('\\','/')}
            for key in ('modelNpzPath','modelObjPath','modelMtlPath','modelVoxPath','previewPath','promptsPath'):
                if row.get(key):updated[key]='AI_'+shard+'/'+row[key].replace('\\','/')
            rows.append(updated)
    catalog=json.loads((ROOT/'dataset_catalog.json').read_text(encoding='utf8'))
    if len(rows)!=catalog['modelCount']:raise ValueError('Combined model count differs from catalog')
    result={'modelCount':len(rows),'promptRecordCount':sum(d['promptRecordCount'] for d in shard_data.values()),
            'shardId':'A+B','models':rows,'sourcePromptFiles':['AI_A/all_prompts.jsonl','AI_B/all_prompts.jsonl']}
    target=directory/'manifest.json'
    if target.exists():
        if json.loads(target.read_text(encoding='utf8'))!=result:raise ValueError('Existing combined manifest conflicts')
    else:
        with target.open('x',encoding='utf8') as stream:json.dump(result,stream,ensure_ascii=False)
    print('Combined dataset:',len(rows),'models /',result['promptRecordCount'],'records',flush=True)

def main():
    parser=argparse.ArgumentParser(description='Download BrickMore AI_A, AI_B, or all 80,000 models with SHA-256 verification.')
    parser.add_argument('--output',type=Path,default=Path('dataset'));parser.add_argument('--extract',action='store_true')
    parser.add_argument('--shard',choices=('A','B','all'),default='A',help='A keeps the original command behavior; all uses separate shard directories')
    parser.add_argument('--workers',type=int,default=1,help='Concurrent package downloads; authoritative metadata is always extracted last')
    args=parser.parse_args()
    if args.workers<1:parser.error('workers must be positive')
    if args.shard=='all':
        data={shard:run_shard(shard,args.output/('AI_'+shard),args.extract,args.workers) for shard in ('A','B')}
        if args.extract:join_extracted(args.output,data)
    else:run_shard(args.shard,args.output,args.extract,args.workers)
    if not args.extract:print('All downloads verified',flush=True)

if __name__=='__main__':main()
