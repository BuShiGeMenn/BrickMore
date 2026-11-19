"""Offline BrickGPT generation with stable prompt IDs and per-model checkpoints."""

import argparse
from contextlib import contextmanager
import importlib
import json
import logging
import os
from pathlib import Path
import shutil
import sys
import tarfile
import threading
import time
import traceback

from checkpoints import (MODEL_ROOT, ROOT, atomic_write, checkpoint_files, download_models,
                         file_hash, locate, progress, read_json, save_json)

DATA = ROOT / 'Data/prompts.json'
SETTINGS = {'world_dim': 20, 'max_bricks': 200, 'max_regenerations': 8, 'use_gurobi': False}


def configure_runtime():
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1')
    sys.path.insert(0, str(ROOT / 'Vendor/src'))
    deps = ROOT / '.runtime/deps'
    if deps.is_dir():
        sys.path.insert(0, str(deps))


def verify_bundle():
    for line in (ROOT / 'CHECKSUMS.sha256').read_text(encoding='utf-8').splitlines():
        digest, name = line.split('  ', 1)
        if file_hash(ROOT / name) != digest:
            raise ValueError(f'Bundle checksum mismatch: {name}')


def preflight(args, checkpoint):
    configure_runtime()
    info = {'python': sys.executable, 'python_version': sys.version.split()[0],
            'weights': {k: str(p) if p else None for k, p in checkpoint.items()}, 'device': args.device,
            'bundle_free_gib': round(shutil.disk_usage(ROOT).free / 1024**3, 2), 'errors': []}
    errors = info['errors']
    for kind, path in checkpoint.items():
        print(f'WEIGHTS {kind:7} {path or "MISSING"}', flush=True)
        if path is None:
            errors.append(f'Missing {kind} weights. Run download on a connected host, or supply a local model path.')
    for name in ['numpy', 'networkx', 'torch', 'transformers', 'safetensors', 'accelerate']:
        try:
            module = importlib.import_module(name)
            info[name] = getattr(module, '__version__', 'installed')
        except Exception as exc:
            errors.append(f'{name}: {type(exc).__name__}: {exc}')
    if 'merged' not in checkpoint:
        try:
            import peft
            info['peft'] = peft.__version__
        except Exception as exc:
            errors.append(f'peft: {type(exc).__name__}: {exc}')
    if 'torch' in info:
        import torch
        try:
            if args.device == 'cuda':
                if not torch.cuda.is_available():
                    raise RuntimeError('CUDA unavailable in this Python environment')
                free, total = torch.cuda.mem_get_info()
                info['gpu'] = {'name': torch.cuda.get_device_name(), 'free_gib': round(free / 1024**3, 2),
                               'total_gib': round(total / 1024**3, 2), 'bf16': torch.cuda.is_bf16_supported()}
        except Exception as exc:
            errors.append(str(exc))
    if all(checkpoint.values()) and 'transformers' in info and 'torch' in info:
        try:
            from brickgpt.models.brickgpt import create_instruction
            from transformers import AutoTokenizer, LlamaForCausalLM
            path = checkpoint.get('merged') or checkpoint['adapter']
            tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True, trust_remote_code=False)
            tokens = tokenizer.apply_chat_template([{'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': create_instruction(read_json(DATA)[0]['caption'])}],
                add_generation_prompt=True, return_tensors='pt')
            if not tokens.shape[-1] or tokenizer.eos_token_id is None:
                raise ValueError('tokenizer did not produce a usable chat input')
            for word in ['x', ' (', ',', ')\n', tokenizer.eos_token] + list(map(str, range(20))):
                if len(tokenizer.tokenize(word)) != 1:
                    raise ValueError(f'BrickGPT constrained decoding requires one token for {word!r}')
            info['tokenizer'] = {'class': type(tokenizer).__name__, 'example_input_tokens': tokens.shape[-1]}
        except Exception as exc:
            errors.append(f'BrickGPT/tokenizer: {type(exc).__name__}: {exc}')
    elif 'numpy' in info and 'networkx' in info:
        try:
            from brickgpt.data import BrickStructure
            example = BrickStructure.from_txt('2x4 (0,0,0)\n')
            if not example.is_connected() or not example.to_ldr().startswith('1 '):
                raise ValueError('LDraw export/connectivity check failed')
        except Exception as exc:
            errors.append(f'BrickGPT code: {type(exc).__name__}: {exc}')
    info['ready'] = not errors
    report = ROOT / '.runtime/environment.json'
    save_json(report, info)
    if 'gpu' in info:
        print('GPU ' + json.dumps(info['gpu'], ensure_ascii=False), flush=True)
    print(f'DISK {info["bundle_free_gib"]:.2f} GiB free on bundle filesystem', flush=True)
    for error in errors:
        print('CHECK FAILED ' + error, flush=True)
    print(('ENVIRONMENT READY' if info['ready'] else 'ENVIRONMENT NOT READY') + f' {report}', flush=True)
    return info


def load_brickgpt(checkpoint, device):
    import torch
    from brickgpt.models import BrickGPT, BrickGPTConfig
    from brickgpt.models.llm import LLM
    from transformers import AutoModelForCausalLM, AutoTokenizer

    dtype = torch.float32 if device == 'cpu' else (torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16)
    model_path = checkpoint.get('merged') or checkpoint['base']
    tokenizer_path = checkpoint.get('merged') or checkpoint['adapter']
    print(f'LOAD {model_path} on {device}, dtype={dtype}', flush=True)
    tokenizer = AutoTokenizer.from_pretrained(str(tokenizer_path), local_files_only=True, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(str(model_path), local_files_only=True, trust_remote_code=False, dtype=dtype)
    if 'adapter' in checkpoint:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, str(checkpoint['adapter']), local_files_only=True).merge_and_unload()
    if len(tokenizer) > model.get_input_embeddings().num_embeddings:
        # The original tokenizer has reserved ids beyond the base vocabulary on some exports.
        required = max(tokenizer.eos_token_id, tokenizer.pad_token_id or 0)
        if required >= model.get_input_embeddings().num_embeddings:
            raise ValueError('Token IDs required by the BrickGPT tokenizer are outside the checkpoint vocabulary')
    llm = LLM(str(model_path), device, tokenizer=tokenizer, model=model.to(device).eval())
    return BrickGPT(BrickGPTConfig(str(model_path), device=device, **SETTINGS), llm=llm)


@contextmanager
def heartbeat(message, every=15):
    stop = threading.Event()
    started = time.monotonic()

    def tick():
        while not stop.wait(every):
            print(f'WORKING {message} elapsed={time.monotonic() - started:.0f}s', flush=True)

    thread = threading.Thread(target=tick, daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join()


@contextmanager
def output_lock(out):
    out.mkdir(parents=True, exist_ok=True)
    if os.name != 'posix':
        yield
        return
    import fcntl
    with (out / '.lock').open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f'Another process is writing {out}. Use status to see progress.') from exc
        yield


def completed(out, row):
    sid = row['prompt_id']
    record = out / 'records' / f'{sid}.json'
    ldr = out / 'ldr' / f'{sid}.ldr'
    txt = out / 'raw' / f'{sid}.txt'
    if not record.is_file():
        return None
    value = read_json(record)
    if not (value.get('prompt') == row and value.get('brick_count', 0) > 0 and ldr.is_file() and txt.is_file()
            and value.get('ldr_sha256') == file_hash(ldr) and value.get('raw_sha256') == file_hash(txt)):
        raise ValueError(f'Invalid saved record for {sid}. Inspect {record} and restore the original files.')
    return value


def write_summary(out, rows):
    records = [record for row in rows if (record := completed(out, row))]
    pending = [r['prompt_id'] for r in rows if not (out / 'records' / f'{r["prompt_id"]}.json').is_file()]
    result = {'expected': len(rows), 'completed': len(records), 'pending': pending,
              'connected_count': sum(r['connected'] for r in records), 'records': records}
    save_json(out / 'summary.json', result)
    return result


def checkpoint_identity(checkpoint):
    result = {}
    for kind, path in checkpoint.items():
        print(f'FINGERPRINT {kind} {path}', flush=True)
        result[kind] = {'path': str(path), 'files': {p.name: file_hash(p) for p in checkpoint_files(path, kind)}}
    return result


def generate_one(out, row, model, first_seed, attempts):
    import torch
    from brickgpt.data import BrickStructure
    from transformers import set_seed

    sid = row['prompt_id']
    attempt_file = out / 'attempts' / f'{sid}.json'
    failures = read_json(attempt_file)['attempts'] if attempt_file.is_file() else []
    start = time.monotonic()
    for seed in range(first_seed, first_seed + attempts):
        set_seed(seed)
        try:
            with heartbeat(f'{sid} seed={seed}'), torch.inference_mode():
                result = model(row['caption'])
            bricks = result['bricks']
            if not len(bricks):
                raise ValueError('Empty BrickGPT output')
            if bricks.has_collisions() or bricks.has_out_of_bounds_bricks():
                raise ValueError('Generated bricks overlap or exceed the generation bounds')
            ldr_text = bricks.to_ldr()
            if BrickStructure.from_ldr(ldr_text) != bricks:
                raise ValueError('LDraw geometry did not round-trip')
            connected = bool(bricks.is_connected())
            txt = out / 'raw' / f'{sid}.txt'
            ldr = out / 'ldr' / f'{sid}.ldr'
            atomic_write(txt, bricks.to_txt().encode('utf-8'))
            atomic_write(ldr, ldr_text.encode('ascii'))
            value = dict(prompt=row, seed=seed, brick_count=len(bricks), connected=connected,
                         n_regenerations=result['n_regenerations'], rejection_reasons=dict(result['rejection_reasons']),
                         seconds=round(time.monotonic() - start, 3), failed_attempts=failures,
                         ldr_sha256=file_hash(ldr), raw_sha256=file_hash(txt))
            save_json(out / 'records' / f'{sid}.json', value)
            return value
        except (ValueError, IndexError) as exc:
            failures.append({'seed': seed, 'error': str(exc)})
            print(f'RETRY {sid} seed={seed}: {exc}', flush=True)
            save_json(attempt_file, {'prompt_id': sid, 'next_seed': seed + 1, 'attempts': failures})
    return None


def generate(args, rows):
    out = args.out.resolve()
    with output_lock(out):
        checkpoint = locate(args, verbose=True)
        env = preflight(args, checkpoint)
        if not env['ready']:
            return 2
        selected = rows[:1] if args.command == 'smoke' else rows
        pending = [row for row in selected if not completed(out, row)]
        start = time.monotonic()
        done = initial = len(selected) - len(pending)
        config_path = out / 'run_config.json'
        with heartbeat('checking model weights'):
            config = {'prompts_sha256': file_hash(DATA), 'bundle_checksums_sha256': file_hash(ROOT / 'CHECKSUMS.sha256'),
                      'device': args.device, 'gpu': env.get('gpu', {}).get('name'), 'checkpoint': checkpoint_identity(checkpoint),
                      'settings': SETTINGS, 'first_seed': args.seed}
        if config_path.is_file():
            if read_json(config_path) != config:
                raise ValueError(f'Generation settings or checkpoint changed. Use a new --out directory: {out}')
        else:
            if any(out.glob('records/*.json')):
                raise ValueError('Output has completion records but no run configuration')
            save_json(config_path, config)

        def state(status, current=None):
            save_json(out / 'progress.json', {'status': status, 'mode': args.command, 'done': done,
                      'total': len(selected), 'current': current, 'elapsed_seconds': round(time.monotonic() - start, 1)})

        try:
            if pending:
                state('loading')
                with heartbeat('loading BrickGPT to ' + args.device):
                    model = load_brickgpt(checkpoint, args.device)
                start = time.monotonic()
                for row in pending:
                    sid = row['prompt_id']
                    state('running', sid)
                    progress(f'START #{row["ordinal"]} {sid}', done, len(selected), start, initial)
                    attempt_file = out / 'attempts' / f'{sid}.json'
                    next_seed = read_json(attempt_file)['next_seed'] if attempt_file.is_file() else args.seed
                    value = generate_one(out, row, model, next_seed, args.attempts)
                    if value:
                        done += 1
                        progress(f'SAVED {sid} ({value["brick_count"]} bricks)', done, len(selected), start, initial)
                    else:
                        print(f'PENDING {sid}: retry budget exhausted for this invocation', flush=True)
                    state('running')
            summary = write_summary(out, rows)
            state('finished' if done == len(selected) else 'incomplete')
            print(f'{"FINISHED" if done == len(selected) else "INCOMPLETE"} {args.command}: '
                  f'{done}/{len(selected)} selected, {summary["completed"]}/{summary["expected"]} total .ldr files in {out / "ldr"}', flush=True)
            return 0 if done == len(selected) else 3
        except BaseException:
            state('interrupted' if isinstance(sys.exc_info()[1], KeyboardInterrupt) else 'error')
            raise


def export(args, rows):
    out = args.out.resolve()
    with output_lock(out):
        bundle = write_summary(out, rows)
        if bundle['pending']:
            raise ValueError(f'{len(bundle["pending"])} inputs are pending. Finish generation before exporting.')
        archive = out.parent / f'{out.name}-results.tar.gz'
        tmp = archive.with_name(f'.{archive.name}.{os.getpid()}.tmp')
        with tarfile.open(tmp, 'w:gz') as tar:
            for row in rows:
                sid = row['prompt_id']
                for folder, suffix in [('ldr', '.ldr'), ('raw', '.txt'), ('records', '.json')]:
                    name = f'{folder}/{sid}{suffix}'
                    tar.add(out / name, arcname=f'{out.name}/{name}')
            for name in ('run_config.json', 'summary.json', 'progress.json'):
                tar.add(out / name, arcname=f'{out.name}/{name}')
        tmp.replace(archive)
        atomic_write(archive.with_name(archive.name + '.sha256'), f'{file_hash(archive)}  {archive.name}\n'.encode('ascii'))
        print('EXPORTED ' + str(archive), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['verify', 'doctor', 'download', 'smoke', 'full', 'status', 'export'])
    parser.add_argument('--merged', help='Explicit local merged BrickGPT directory')
    parser.add_argument('--base', help='Explicit local Llama 3.2 1B Instruct directory')
    parser.add_argument('--adapter', help='Explicit local official BrickGPT adapter directory')
    parser.add_argument('--device', choices=['cuda', 'cpu'], default='cuda')
    parser.add_argument('--out', type=Path, default=ROOT / 'Results/brickgpt_A130_A260')
    parser.add_argument('--attempts', type=int, default=3, help='Maximum seeds for one failed prompt per invocation')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--watch', action='store_true')
    parser.add_argument('--component', choices=['missing', 'all', 'base', 'adapter'], default='missing')
    parser.add_argument('--dest', type=Path, default=MODEL_ROOT)
    args = parser.parse_args()
    if args.attempts < 1 or not 0 <= args.seed < 2**32:
        parser.error('Use a positive retry budget and a seed between 0 and 2^32-1')
    rows = read_json(DATA)
    if [r['ordinal'] for r in rows] != list(range(130, 261)) or len({r['prompt_id'] for r in rows}) != 131:
        raise ValueError('Input must contain the 131 expected sequential prompts')
    if args.command in {'verify', 'doctor', 'smoke', 'full'}:
        verify_bundle()
    if args.command == 'verify':
        print(f'VERIFY OK: {len(rows)} prompts, {rows[0]["prompt_id"]} to {rows[-1]["prompt_id"]}')
    elif args.command == 'doctor':
        return 0 if preflight(args, locate(args, verbose=True))['ready'] else 2
    elif args.command == 'download':
        with output_lock(args.dest.resolve()):
            download_models(args)
    elif args.command in {'smoke', 'full'}:
        return generate(args, rows)
    elif args.command == 'export':
        export(args, rows)
    elif args.command == 'status':
        while True:
            path = args.out / 'progress.json'
            state = read_json(path) if path.is_file() else {'status': 'not_started'}
            print(json.dumps(state, ensure_ascii=False), flush=True)
            if not args.watch or state['status'] not in {'loading', 'running'}:
                break
            time.sleep(5)
    return 0


if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s %(message)s')
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print('INTERRUPTED. Rerun the same command to resume.', file=sys.stderr, flush=True)
        sys.exit(130)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
