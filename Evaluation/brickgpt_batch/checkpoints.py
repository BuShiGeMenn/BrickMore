"""Find complete local BrickGPT checkpoints and transfer pinned official weights."""

import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
MODEL_ROOT = ROOT / 'Downloads' / 'models'
OLD_ROOT = Path('/mnt/brickmore-data/brickmore-jrd-20261025')
BASE_REPO = 'meta-llama/Llama-3.2-1B-Instruct'
ADAPTER_REPO = 'AvaLovelace/BrickGPT'
REPOS = {'base': BASE_REPO, 'adapter': ADAPTER_REPO}
REVISIONS = {'base': '9213176726f574b556790deb65791e0c5aa438b6',
             'adapter': '19737def7bfe5950b2a466825ad7c6d74b7eafe3'}
COMPONENT_FILES = {
    'base': {'config.json', 'generation_config.json', 'model.safetensors', 'tokenizer.json',
             'tokenizer_config.json', 'special_tokens_map.json', 'LICENSE.txt', 'USE_POLICY.md'},
    'adapter': {'adapter_config.json', 'adapter_model.safetensors', 'tokenizer.json',
                'tokenizer_config.json', 'special_tokens_map.json'},
}


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f'.{path.name}.{os.getpid()}.tmp')
    with temporary.open('wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def save_json(path, value):
    atomic_write(path, (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8'))


def file_hash(path, algorithm='sha256', initial=None):
    digest = hashlib.new(algorithm, initial or b'')
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024**2), b''):
            digest.update(chunk)
    return digest.hexdigest()


def safetensors_header(path):
    size = path.stat().st_size
    with path.open('rb') as stream:
        count, = struct.unpack('<Q', stream.read(8))
        if not 2 <= count <= min(100_000_000, size - 8):
            raise ValueError('invalid safetensors header')
        header = json.loads(stream.read(count))
    offsets = [v['data_offsets'][1] for k, v in header.items() if k != '__metadata__']
    if not offsets or max(offsets) != size - 8 - count:
        raise ValueError('incomplete safetensors payload')
    return header


def checkpoint_files(path, kind):
    tokenizer_files = [p for p in path.iterdir() if p.is_file() and (
        p.name.startswith('tokenizer') or p.name in {'chat_template.jinja', 'special_tokens_map.json', 'generation_config.json'})]
    if not (path / 'tokenizer_config.json').is_file() or not any((path / n).is_file() for n in ('tokenizer.json', 'tokenizer.model')):
        raise ValueError('tokenizer files missing')
    if kind == 'adapter':
        config_file = path / 'adapter_config.json'
        cfg = read_json(config_file)
        if cfg.get('base_model_name_or_path') != BASE_REPO or cfg.get('peft_type') != 'LORA':
            raise ValueError('unexpected adapter base or type')
        model_files = [path / 'adapter_model.safetensors']
        official = '83a85058ec3e023ca41845594a204555cd2576e5436cb701fc475b495c21fd8a'
        if file_hash(model_files[0]) != official:
            raise ValueError('does not match the official BrickGPT adapter weights')
    else:
        config_file = path / 'config.json'
        cfg = read_json(config_file)
        if (cfg.get('model_type'), cfg.get('hidden_size'), cfg.get('num_hidden_layers')) != ('llama', 2048, 16):
            raise ValueError('expected a Llama 3.2 1B checkpoint')
        index = path / 'model.safetensors.index.json'
        if index.is_file():
            shards = sorted(set(read_json(index)['weight_map'].values()))
            if not shards or any(Path(name).name != name for name in shards):
                raise ValueError('invalid shard paths in checkpoint index')
            model_files = [path / name for name in shards] + [index]
        else:
            model_files = [path / 'model.safetensors']
    for weight in model_files:
        if weight.suffix == '.safetensors':
            safetensors_header(weight)
    return sorted(set([config_file] + tokenizer_files + model_files))


def cache_dirs():
    candidates = [os.environ.get('HF_HUB_CACHE'), os.environ.get('HUGGINGFACE_HUB_CACHE'),
                  os.environ.get('TRANSFORMERS_CACHE')]
    if os.environ.get('HF_HOME'):
        candidates.append(Path(os.environ['HF_HOME']) / 'hub')
    candidates.extend([OLD_ROOT / 'runtime/cache/huggingface/hub',
                       ROOT / 'Downloads/huggingface/hub', Path.home() / '.cache/huggingface/hub'])
    return list(dict.fromkeys(Path(p).expanduser() for p in candidates if p))


def snapshots(kind):
    repo_folder = 'models--' + REPOS[kind].replace('/', '--')
    for cache in cache_dirs():
        base = cache / repo_folder
        yield base / 'snapshots' / REVISIONS[kind]
        main_ref = base / 'refs/main'
        if main_ref.is_file():
            revision = main_ref.read_text(encoding='ascii', errors='replace').strip()
            if re.fullmatch(r'[a-f0-9]{40}', revision):
                yield base / 'snapshots' / revision
        yield from sorted((base / 'snapshots').glob('*'))


def merged_candidates():
    for root in [OLD_ROOT / 'runtime/models', OLD_ROOT, Path('/mnt/brickmore-data'), Path('/jrd'), Path.home()]:
        if not root.is_dir():
            continue
        for current, dirs, names in os.walk(root):
            path = Path(current)
            name = path.name.lower()
            context = path.parent.name.lower()
            if 'config.json' in names and ('brickgpt' in name or 'merged' in name and 'brickgpt' in context):
                yield path
            depth = len(path.relative_to(root).parts)
            dirs[:] = [] if depth >= 5 else [d for d in dirs if not d.startswith('.') and d.lower() not in
                                            {'runtime', 'results', 'assets', 'node_modules', 'venv', 'hub', 'blobs', 'data'}]


def locate(args, verbose=False):
    def find(kind, candidates):
        explicit = getattr(args, kind, None) or os.environ.get('BRICKGPT_' + kind.upper())
        locations = [Path(explicit).expanduser()] if explicit else candidates
        for path in dict.fromkeys(locations):
            if not path.is_dir():
                if explicit:
                    raise ValueError(f'{kind} model directory does not exist: {path}')
                continue
            try:
                checkpoint_files(path, kind)
                return path.resolve()
            except (OSError, ValueError, KeyError, TypeError, struct.error) as exc:
                if explicit:
                    raise ValueError(f'Invalid {kind} model at {path}: {exc}') from exc
                if verbose:
                    print(f'SKIP {kind}: {path} ({exc})', flush=True)
        return None

    force_split = any(getattr(args, k, None) or os.environ.get('BRICKGPT_' + k.upper()) for k in ('base', 'adapter'))
    force_merged = getattr(args, 'merged', None) or os.environ.get('BRICKGPT_MERGED')
    if force_split and force_merged:
        raise ValueError('Specify either a merged checkpoint or base/adapter paths')
    merged = None if force_split else find('merged', [MODEL_ROOT / 'merged', ROOT / 'models/brickgpt_merged', *merged_candidates()])
    if merged:
        return {'merged': merged}
    return {kind: find(kind, [MODEL_ROOT / kind, MODEL_ROOT / REPOS[kind].split('/')[-1], *snapshots(kind)])
            for kind in ('base', 'adapter')}


class DownloadAccessError(RuntimeError):
    pass


def authorization():
    secret = os.environ.get('HF_TOKEN') or os.environ.get('HUGGING_FACE_HUB_TOKEN')
    if secret:
        return secret.strip()
    candidates = [os.environ.get('HF_TOKEN_PATH'), Path(os.environ.get('HF_HOME') or Path.home() / '.cache/huggingface') / 'token',
                  Path.home() / '.cache/huggingface/token']
    for value in candidates:
        if value and Path(value).is_file():
            return Path(value).read_text(encoding='ascii').strip()
    return None


def request(url, secret=None, headers=None, method=None):
    req = urllib.request.Request(url, headers=headers or {}, method=method)
    if secret and urllib.parse.urlsplit(url).hostname == 'huggingface.co':
        # Only the Hub needs the credential. The redirected CDN URL is signed.
        req.add_unredirected_header('Authorization', 'Bearer ' + secret)
    return req


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def linked_sha256(url, secret):
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request(url, secret, method='HEAD'), timeout=30) as response:
            headers = response.headers
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            raise DownloadAccessError('Llama access required: https://huggingface.co/' + BASE_REPO) from None
        if error.code not in (301, 302, 303, 307, 308):
            raise
        headers = error.headers
    value = (headers.get('X-Linked-Etag') or headers.get('ETag') or '').strip('"')
    if not re.fullmatch(r'[a-f0-9]{64}', value):
        raise RuntimeError('Hub did not expose the LFS SHA-256 for the pinned file')
    return value


def size_label(n):
    return f'{n / 1024**2:.1f} MiB'


def progress(label, done, total, start, initial=0, bytes_mode=False):
    duration = max(time.monotonic() - start, 0.001)
    rate = max(0, done - initial) / duration
    eta = f'{(total - done) / rate:.0f}s' if rate else '--'
    fill = min(24, int(24 * done / total))
    counters = f'{size_label(done)} / {size_label(total)}' if bytes_mode else f'{done}/{total}'
    speed = f' {size_label(rate)}/s' if bytes_mode else ''
    print(f'[{"#" * fill}{"-" * (24 - fill)}] {done / total:6.1%} {counters} '
          f'elapsed={duration:.0f}s ETA={eta}{speed} {label}', flush=True)


def download_file(url, target, expected_size, checksum, *, secret=None, retries=15):
    """Use persistent contiguous ranges and verify before exposing the final file."""
    algorithm, expected_hash = checksum

    def valid(path):
        if not path.is_file() or path.stat().st_size != expected_size:
            return False
        prefix = f'blob {expected_size}\0'.encode() if algorithm == 'sha1' else None
        print(f'CHECKSUM {path.name} ({size_label(expected_size)})', flush=True)
        return file_hash(path, algorithm, prefix) == expected_hash

    target.parent.mkdir(parents=True, exist_ok=True)
    if valid(target):
        print('CACHED ' + str(target), flush=True)
        return
    part = target.with_name(target.name + '.part')
    identity = part.with_suffix('.part.json')
    plan = {'url': url, 'size': expected_size, 'digest': list(checksum)}
    if part.exists() and (not identity.is_file() or read_json(identity) != plan or part.stat().st_size > expected_size):
        raise ValueError(f'Existing partial file does not match this download: {part}')
    save_json(identity, plan)
    initial = part.stat().st_size if part.exists() else 0
    if shutil.disk_usage(target.parent).free < expected_size - initial:
        raise OSError(f'Insufficient free space for {target}')
    start, last_update = time.monotonic(), 0
    failures = 0
    progress('Download ' + target.name, initial, expected_size, start, initial, bytes_mode=True)
    while not part.exists() or part.stat().st_size < expected_size:
        offset = part.stat().st_size if part.exists() else 0
        end = min(offset + 64 * 1024**2 - 1, expected_size - 1)
        try:
            req = request(url, secret, {'Range': f'bytes={offset}-{end}', 'Accept-Encoding': 'identity'})
            with urllib.request.urlopen(req, timeout=45) as response:
                if response.status == 206:
                    match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', response.headers.get('Content-Range', ''))
                    if not match or int(match[1]) != offset or int(match[3]) != expected_size or not offset <= int(match[2]) <= end:
                        raise ValueError('Unexpected HTTP Content-Range')
                    expected_end = int(match[2]) + 1
                elif response.status == 200 and offset == 0:
                    expected_end = expected_size
                else:
                    raise RuntimeError('Server ignored Range after a partial download. Partial file retained.')
                with part.open('ab') as stream:
                    while stream.tell() < expected_end:
                        chunk = response.read(min(256 * 1024, expected_end - stream.tell()))
                        if not chunk:
                            raise OSError('Connection closed before range finished')
                        stream.write(chunk)
                        if time.monotonic() - last_update >= 2:
                            stream.flush()
                            progress('Download ' + target.name, stream.tell(), expected_size, start, initial, bytes_mode=True)
                            last_update = time.monotonic()
                    stream.flush()
                    os.fsync(stream.fileno())
            failures = 0
        except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as exc:
            if isinstance(exc, urllib.error.HTTPError) and exc.code in (401, 403, 404):
                raise DownloadAccessError(f'HTTP {exc.code} for {target.name}. Check Hugging Face access and HF_TOKEN.') from None
            if isinstance(exc, OSError) and exc.errno in (13, 28):
                raise
            failures += 1
            if failures >= retries:
                raise RuntimeError(f'Download interrupted. Rerun the same command to resume {part.name}.') from None
            wait = min(2 ** failures, 20)
            retained = part.stat().st_size if part.exists() else 0
            print(f'RECONNECT {failures}/{retries} in {wait}s; retained {size_label(retained)} ({type(exc).__name__})', flush=True)
            time.sleep(wait)
    if not valid(part):
        reject = part.with_name(f'{part.name}.checksum-failed-{time.time_ns()}')
        part.replace(reject)
        raise ValueError(f'Checksum mismatch. Saved {reject.name}; rerun to download a clean copy.')
    part.replace(target)
    identity.unlink(missing_ok=True)
    progress('Verified ' + target.name, expected_size, expected_size, start, initial, bytes_mode=True)


def download_models(args):
    args.dest = args.dest.resolve()
    if args.component == 'missing':
        located = locate(args, verbose=True)
        kinds = [kind for kind, path in located.items() if path is None]
        if not kinds:
            print('CACHE READY: ' + ', '.join(f'{k}={v}' for k, v in located.items()))
            return
    else:
        kinds = list(REPOS) if args.component == 'all' else [args.component]
    secret = authorization() if 'base' in kinds else None
    if 'base' in kinds and not secret:
        raise DownloadAccessError('Llama base missing. Obtain access at https://huggingface.co/' + BASE_REPO +
                                  ' and use a read token on the connected host, or supply the existing local checkpoint.')
    for kind in kinds:
        repo, rev = REPOS[kind], REVISIONS[kind]
        url = f'https://huggingface.co/api/models/{repo}/tree/{rev}'
        for attempt in range(4):
            try:
                with urllib.request.urlopen(request(url, secret), timeout=30) as response:
                    tree = json.load(response)
                break
            except (OSError, http.client.HTTPException) as exc:
                if (isinstance(exc, urllib.error.HTTPError) and exc.code in (401, 403, 404)) or attempt == 3:
                    raise DownloadAccessError(f'Cannot read Hugging Face manifest for {repo}: {type(exc).__name__}') from None
                time.sleep(2 ** attempt)
        found = {entry['path']: entry for entry in tree if entry['type'] == 'file' and entry['path'] in COMPONENT_FILES[kind]}
        if set(found) != COMPONENT_FILES[kind]:
            raise ValueError(f'Missing expected files in official manifest: {COMPONENT_FILES[kind] - found.keys()}')
        print(f'MODEL {repo}@{rev} {size_label(sum(x["size"] for x in found.values()))}', flush=True)
        provenance = {}
        for index, (name, entry) in enumerate(sorted(found.items(), key=lambda v: v[1]['size']), 1):
            print(f'FILE {index}/{len(found)} {name}', flush=True)
            source = f'https://huggingface.co/{repo}/resolve/{rev}/{urllib.parse.quote(name)}?download=true'
            if entry.get('lfs'):
                value = entry['lfs']['oid']
                if not re.fullmatch(r'[a-f0-9]{64}', value):
                    value = linked_sha256(source, secret)
                checksum = ('sha256', value)
            else:
                checksum = ('sha1', entry['oid'])
            download_file(source, args.dest / kind / name, entry['size'], checksum, secret=secret)
            provenance[name] = {'size': entry['size'], 'algorithm': checksum[0], 'hash': checksum[1]}
        checkpoint_files(args.dest / kind, kind)
        save_json(args.dest / kind / 'download_provenance.json', {'repo': repo, 'revision': rev, 'files': provenance})
    print('DOWNLOAD COMPLETE ' + str(args.dest), flush=True)
