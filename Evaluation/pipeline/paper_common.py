"""Shared, dependency-light I/O and provenance for the paper evaluation runners."""
import hashlib
import json
import lzma
import math
import os
import re
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode()).hexdigest()


def read_jsonl(path):
    rows = []
    opener = lzma.open if Path(path).suffix == '.xz' else open
    with opener(path, mode='rt', encoding='utf-8-sig') as stream:
        for number, line in enumerate(stream, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f'{path}:{number}: invalid JSON; repair incomplete journal before resuming') from exc
    return rows


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    temp.replace(path)


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('w', encoding='utf-8') as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
    temp.replace(path)


def keyed(rows, field='sample_id'):
    result = {}
    for row in rows:
        key = str(row[field])
        if key in result:
            raise ValueError(f'Duplicate {field}: {key}')
        result[key] = row
    return result


def sample_id(row):
    if 'sample_id' in row:
        return str(row['sample_id'])
    if 'id' not in row:
        raise ValueError('Every record needs sample_id or id; line order is not an identity')
    return f'{row["id"]}__sample{row.get("sample", 0)}'


def normalize_ids(rows):
    result = [{**row, 'sample_id': sample_id(row)} for row in rows]
    keyed(result)
    return result


def safe_name(value):
    text = re.sub(r'[^A-Za-z0-9_.-]', '_', str(value))[:100].strip('.') or 'sample'
    return f'{text}_{hashlib.sha256(str(value).encode()).hexdigest()[:12]}'


def packages(names):
    result = {}
    for name in names:
        try:
            result[name] = version(name)
        except PackageNotFoundError:
            result[name] = None
    return result


def source_hashes(*files):
    paths = [Path(__file__), *map(Path, files)]
    return {p.name: sha256(p) for p in paths}


class Journal:
    """Refuse to mix runs or changed inputs. Flush each completed record for resume."""
    def __init__(self, path, config):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path = self.path.with_suffix('.config.json')
        self.signature = fingerprint(config)
        payload = {**config, 'signature': self.signature}
        if self.config_path.exists():
            old = json.loads(self.config_path.read_text(encoding='utf-8'))
            if old != payload:
                raise ValueError(f'Configuration changed: use a new output path ({self.path})')
        elif self.path.exists() and self.path.stat().st_size:
            raise ValueError('Existing output has no config; refusing unverified resume')
        else:
            write_json(self.config_path, payload)
        rows = read_jsonl(self.path) if self.path.exists() else []
        self.done = keyed(rows)
        if any(r.get('config_signature') != self.signature for r in rows):
            raise ValueError('Journal contains results from another configuration')

    def cached(self, sid, input_hash):
        row = self.done.get(str(sid))
        if row is not None and row.get('input_sha256') != input_hash:
            raise ValueError(f'Input changed for {sid}; use a new output path')
        return row

    def append(self, row, input_hash):
        sid = str(row['sample_id'])
        if sid in self.done:
            raise ValueError(f'Refusing duplicate journal entry: {sid}')
        row = {**row, 'input_sha256': input_hash, 'config_signature': self.signature}
        with self.path.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
            stream.flush()
        self.done[sid] = row


def pooled(scores):
    if len(scores) != 8 or not all(math.isfinite(x) for x in scores):
        raise ValueError('Exactly eight finite view scores are required')
    return {'scores': scores, 'max_score': max(scores), 'mean_score': sum(scores) / 8,
            'best_view': max(range(8), key=lambda i: scores[i])}


def load_bricknet(expected='0.1.0'):
    if os.name == 'nt' and not sys.flags.utf8_mode:
        raise RuntimeError('Original BrickNet reads UTF-8 catalogs using the system default encoding. '
                           'On Windows run python -X utf8, or set PYTHONUTF8=1 before starting Python.')
    import bricknet
    actual = bricknet.__version__
    if expected and actual != expected:
        raise RuntimeError(f'Expected bricknet {expected}, imported {actual} from {bricknet.__file__}; '
                           'use the separate paper environment, not the bundled 0.1.1 source')
    return bricknet


def resolve_hf(model, revision=None, offline=False):
    """Resolve before loading; record local weight hashes or a remote immutable commit."""
    path = Path(model)
    if path.is_dir():
        files = sorted(p for p in path.rglob('*') if p.is_file() and
                       p.suffix in {'.json', '.txt', '.model', '.safetensors', '.bin'})
        if not files:
            raise ValueError(f'No model files in {path}')
        return {'model': str(path.resolve()), 'revision': None,
                'local_files': {p.relative_to(path).as_posix(): sha256(p) for p in files}}
    if revision and re.fullmatch('[0-9a-f]{40}', revision):
        commit = revision
    else:
        if offline:
            raise ValueError('--offline requires a local model directory or a full commit revision')
        from huggingface_hub import model_info
        commit = model_info(model, revision=revision).sha
    return {'model': model, 'revision': commit}


def load_causal(model_spec, adapter_specs, dtype, device, offline=False):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    kw = {'revision': model_spec['revision'], 'local_files_only': offline}
    model = AutoModelForCausalLM.from_pretrained(model_spec['model'],
        dtype=getattr(torch, dtype), **kw).to(device)
    if adapter_specs:
        from peft import PeftModel
        for spec in adapter_specs:
            model = PeftModel.from_pretrained(model, spec['model'], revision=spec['revision'],
                                              local_files_only=offline).merge_and_unload()
    tokenizer = AutoTokenizer.from_pretrained(model_spec['model'], **kw)
    return model.eval(), tokenizer
