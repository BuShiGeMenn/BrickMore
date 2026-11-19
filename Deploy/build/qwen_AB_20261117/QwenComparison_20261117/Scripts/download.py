"""Persistent .part downloads, HTTP Range reconnects and cryptographic verification."""
import hashlib,http.client,json,time,urllib.error,urllib.request
from pathlib import Path
from common import Progress,sha

def fetch(url,target,size=None,sha256=None,git_sha1=None,retries=20,timeout=40):
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    def valid(path):
        if not path.exists() or size is not None and path.stat().st_size!=size:return False
        if sha256:return sha(path)==sha256
        if git_sha1:
            h=hashlib.sha1(f'blob {path.stat().st_size}\0'.encode());h.update(path.read_bytes());return h.hexdigest()==git_sha1
        return size is not None
    if valid(target):print('CACHED '+str(target),flush=True);return target
    if target.exists():target.rename(target.with_name(target.name+f'.unverified-{time.time_ns()}'))
    part=target.with_name(target.name+'.part');failures=0;initial=part.stat().st_size if part.exists() else 0
    bar=Progress('Download '+target.name,size or 1,initial,unit='bytes')
    while True:
        offset=part.stat().st_size if part.exists() else 0
        if size is not None and offset==size:
            if valid(part):part.replace(target);bar.update(size,force=True);return target
            failures+=1
            part.rename(part.with_name(part.name+f'.checksum-failed-{time.time_ns()}'))
            print('Checksum failed; retained corrupt partial and restarting',flush=True)
        if failures>=retries:raise RuntimeError(f'Download failed after {retries} reconnects: {target}; .part retained')
        offset=part.stat().st_size if part.exists() else 0
        try:
            end=min(offset+32*1024**2-1,size-1) if size is not None else offset+32*1024**2-1
            headers={'User-Agent':'BrickMore-evaluation-resumable/1.0','Range':f'bytes={offset}-{end}'}
            with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=timeout) as response:
                mode='ab'
                if offset and response.status!=206:
                    print('Server ignored Range; safely restarting this file',flush=True);offset=0;mode='wb'
                if response.status==206 and not response.headers.get('Content-Range','').startswith(f'bytes {offset}-'):raise ValueError('Mismatched Content-Range')
                if size is None:
                    size=int(response.headers.get('Content-Range','').split('/')[-1]) if response.status==206 else int(response.headers['Content-Length'])
                    bar.total=size
                with part.open(mode) as output:
                    while True:
                        chunk=response.read(256*1024)
                        if not chunk:break
                        output.write(chunk);output.flush();bar.update(output.tell())
            actual=part.stat().st_size
            if actual!=size:
                content_range=response.headers.get('Content-Range','')
                served_end=int(content_range.split(' ')[1].split('/')[0].split('-')[1]) if content_range.startswith('bytes ') else size-1
                if actual==served_end+1:continue
                raise IOError(f'Connection ended at {actual}/{size} bytes')
        except (urllib.error.URLError,TimeoutError,OSError,ValueError,http.client.HTTPException) as exc:
            failures+=1;wait=min(2**min(failures,4),15)
            print(f'RECONNECT {failures}/{retries} in {wait}s, retained={part.stat().st_size if part.exists() else 0}: {type(exc).__name__}',flush=True)
            time.sleep(wait)

def api(url,retries=8):
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url,timeout=30) as r:return json.load(r)
        except (urllib.error.URLError,TimeoutError,OSError):
            if attempt==retries-1:raise
            time.sleep(min(2**attempt,10))
