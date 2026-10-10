"""Download the complete public release, check SHA-256, optionally extract it."""
import argparse,hashlib,json,os,sys,time,urllib.error,urllib.request,zipfile
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
            if partial.stat().st_size!=asset['bytes'] or checksum(partial)!=asset['sha256']:
                raise ValueError('Downloaded file checksum mismatch: '+partial.name)
            os.replace(partial,target);print('Downloaded and verified',target.name,flush=True);return target
        except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,OSError) as exc:
            if isinstance(exc,urllib.error.HTTPError) and exc.code==404:
                raise RuntimeError('The release or asset is unavailable: '+asset['url']) from exc
            if attempt==5:raise
            print('Retry',attempt,target.name,str(exc),flush=True);time.sleep(min(15,attempt*3))

def extract(path,destination):
    root=destination.resolve()
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            name=info.filename.replace('\\','/');target=(destination/name).resolve()
            if not target.is_relative_to(root):raise ValueError('Unsafe archive path: '+name)
            if (info.external_attr>>16)&0o170000==0o120000:raise ValueError('Archive symlink rejected: '+name)
        archive.extractall(destination)
    print('Extracted',path.name,flush=True)

def main():
    parser=argparse.ArgumentParser(description='Download all 40,000 BrickMore AI_A models and 200,000 bilingual records.')
    parser.add_argument('--output',type=Path,default=Path('dataset'));parser.add_argument('--extract',action='store_true')
    args=parser.parse_args();manifest=json.loads((ROOT/'download_manifest.json').read_text(encoding='utf-8'))
    args.output.mkdir(parents=True,exist_ok=True);downloads=args.output/'packages';downloads.mkdir(exist_ok=True)
    print('Files:',len(manifest['assets']),'Total GB:',round(manifest['totalDownloadBytes']/1e9,2),flush=True)
    for asset in manifest['assets']:
        path=download(asset,downloads)
        if args.extract and path.suffix=='.zip':extract(path,args.output)
    if args.extract:
        data=json.loads((args.output/'manifest.json').read_text(encoding='utf-8'))
        assert data['modelCount']==40000 and data['promptRecordCount']==200000
        for row in data['models']:
            folder=(args.output/row['modelJsonPath']).parent
            assert all((folder/name).is_file() for name in ['model.json','model.npz','model.obj','model.mtl','model.vox','preview.png','validation.json','prompts.json'])
        print('Complete dataset extracted: 40000 models / 200000 bilingual records',flush=True)
    else:print('All downloads verified',flush=True)

if __name__=='__main__':main()
