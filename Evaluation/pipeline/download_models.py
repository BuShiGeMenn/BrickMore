"""Download pinned official model files outside the project, with resumable ranges."""
import argparse
import hashlib
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from huggingface_hub import HfApi

MODELS = [
    ('google/siglip2-base-patch16-224', '75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2', 'siglip2-base'),
    ('timm/PE-Core-B-16', '0038414f37721c5eafc1a5e0da802d291c909de3', 'pe-base'),
]
CHUNK = 8 * 1024 * 1024


def save_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2), encoding='utf-8')
    temporary.replace(path)


def verify(path, file):
    if not path.is_file() or path.stat().st_size != file.size:
        return False
    with path.open('rb') as stream:
        if file.lfs:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            return digest == file.lfs.sha256
        digest = hashlib.sha1(f'blob {file.size}\0'.encode())
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
        return digest.hexdigest() == file.blob_id


def download(url, target, file):
    if verify(target, file):
        print('Cached and verified:', target.name, flush=True)
        return
    if file.size < CHUNK:
        for attempt in range(4):
            try:
                with urllib.request.urlopen(url, timeout=45) as response:
                    data = response.read()
                temporary = target.with_suffix(target.suffix + '.part')
                temporary.write_bytes(data)
                assert verify(temporary, file), f'Hash mismatch: {target.name}'
                temporary.replace(target)
                print('Downloaded and verified:', target.name, flush=True)
                return
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(attempt + 1)
    part = target.with_suffix(target.suffix + '.part')
    state_path = target.with_suffix(target.suffix + '.ranges.json')
    if state_path.exists():
        state = json.loads(state_path.read_text())
        assert state['url'] == url and state['size'] == file.size
    else:
        assert not part.exists(), f'Untracked partial file: {part}'
        part.touch()
        state = {'url': url, 'size': file.size, 'done': []}
        save_json(state_path, state)
    done = set(state['done'])
    ranges = [(start, min(start + CHUNK, file.size) - 1) for start in range(0, file.size, CHUNK)]

    def fetch(bounds):
        start, end = bounds
        for attempt in range(5):
            try:
                request = urllib.request.Request(url, headers={'Range': f'bytes={start}-{end}'})
                with urllib.request.urlopen(request, timeout=60) as response:
                    assert response.status == 206, f'Range HTTP {response.status}'
                    assert response.headers.get('Content-Range') == f'bytes {start}-{end}/{file.size}'
                    data = response.read(end - start + 2)
                assert len(data) == end - start + 1
                return start, data
            except Exception:
                if attempt == 4:
                    raise
                time.sleep(attempt + 1)

    completed = sum(end - start + 1 for start, end in ranges if start in done)
    last_report = completed
    print(f'{target.name}: {completed/1048576:.1f}/{file.size/1048576:.1f} MiB', flush=True)
    with part.open('r+b') as output, ThreadPoolExecutor(max_workers=16) as pool:
        jobs = [pool.submit(fetch, bounds) for bounds in ranges if bounds[0] not in done]
        for job in as_completed(jobs):
            start, data = job.result()
            output.seek(start)
            output.write(data)
            output.flush()
            done.add(start)
            state['done'] = sorted(done)
            save_json(state_path, state)
            completed += len(data)
            if completed - last_report >= 64 * 1024 * 1024 or completed == file.size:
                print(f'{target.name}: {completed/file.size:.1%} ({completed/1048576:.0f} MiB)', flush=True)
                last_report = completed
    assert verify(part, file), f'Final SHA-256 mismatch: {target}'
    part.replace(target)
    state_path.unlink(missing_ok=True)
    print('SHA-256 verified:', target.name, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    for repo, revision, folder in MODELS:
        destination = args.output / folder
        destination.mkdir(parents=True, exist_ok=True)
        info = HfApi().model_info(repo, revision=revision, files_metadata=True)
        files = [file for file in info.siblings if file.rfilename.endswith(('.json', '.txt', '.model', '.safetensors'))]
        files.sort(key=lambda file: file.size)
        provenance = {'repository': repo, 'revision': info.sha, 'files': []}
        for file in files:
            assert '/' not in file.rfilename
            provenance['files'].append({'name': file.rfilename, 'size': file.size,
                                        'sha256': file.lfs.sha256 if file.lfs else None,
                                        'git_blob_sha1': file.blob_id})
        save_json(destination / 'download_manifest.json', provenance)
        print('Downloading', repo, revision, flush=True)
        for file in files:
            url = f'https://huggingface.co/{repo}/resolve/{revision}/{file.rfilename}?download=true'
            download(url, destination / file.rfilename, file)
    print('Both model downloads completed and verified.', flush=True)


if __name__ == '__main__':
    main()
