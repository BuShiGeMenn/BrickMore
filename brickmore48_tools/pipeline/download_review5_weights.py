"""Resumable HTTP range download of the pinned public BrickMore checkpoint."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
from pathlib import Path
import time
import urllib.request

TOTAL = 3441185608
CHUNK = 8388608
EXPECTED = '75f79af15dd76dd488bb554f86a8d87dba6c36b5129d01cb94b7e489d1438c85'
URL = ('https://huggingface.co/Kyle308666/BrickGPT-Qwen3-1.7B-BrickMore-48/resolve/'
       '92d1c595f5fe076971cc2633d6844f097a84eef3/model.safetensors')
FOLDER = Path(__file__).resolve().parents[2] / 'downloads/BrickGPT-Qwen3-1.7B-BrickMore-48'
PARTS = FOLDER / 'range_parts'
PARTS.mkdir(parents=True, exist_ok=True)


def fetch(i):
    start = i*CHUNK
    end = min(TOTAL,start+CHUNK)-1
    path = PARTS / f'{i:05}.part'
    if path.exists() and path.stat().st_size == end-start+1:
        return end-start+1
    for attempt in range(6):
        try:
            req = urllib.request.Request(URL+f'?download=true&part={i}',
                                         headers={'Range':f'bytes={start}-{end}'})
            with urllib.request.urlopen(req,timeout=45) as response:
                if response.status != 206 or response.headers.get('Content-Range') != f'bytes {start}-{end}/{TOTAL}':
                    raise ValueError('Unexpected Content-Range')
                data = response.read()
            if len(data) != end-start+1:
                raise ValueError('Incorrect range length')
            temp = path.with_suffix('.tmp')
            temp.write_bytes(data)
            temp.replace(path)
            return len(data)
        except Exception as exc:
            if attempt == 5:
                raise
            print('RETRY',i,attempt+1,type(exc).__name__,str(exc)[:200],flush=True)
            time.sleep(min(2**attempt,10))


def main():
    final = FOLDER / 'model.safetensors'
    if final.exists() and final.stat().st_size == TOTAL:
        print('MODEL_ALREADY_PRESENT',flush=True)
        return
    begin = time.monotonic()
    last = begin
    done = 0
    count = (TOTAL+CHUNK-1)//CHUNK
    print('RANGE_DOWNLOAD',count,'chunks',flush=True)
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(fetch,i) for i in range(count)]
        for future in as_completed(futures):
            done += future.result()
            if time.monotonic()-last > 20 or done == TOTAL:
                last = time.monotonic()
                print(f'DOWNLOADED {done/1024**3:.2f}/{TOTAL/1024**3:.2f} GiB '
                      f'({done/TOTAL:.1%}), {done/max(1,last-begin)/1024**2:.1f} MiB/s',flush=True)
    digest = hashlib.sha256()
    merged = FOLDER / 'model.safetensors.verified-partial'
    with merged.open('wb') as output:
        for i in range(count):
            data = (PARTS / f'{i:05}.part').read_bytes()
            digest.update(data)
            output.write(data)
    if digest.hexdigest() != EXPECTED:
        raise RuntimeError('Checkpoint SHA256 mismatch')
    merged.replace(final)
    (FOLDER/'model.sha256').write_text(EXPECTED+'  model.safetensors\n',encoding='ascii')
    print('MODEL_DOWNLOAD_COMPLETE_SHA256_VERIFIED',digest.hexdigest(),flush=True)


if __name__ == '__main__':
    main()
