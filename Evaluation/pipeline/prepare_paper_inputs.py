"""Convert accepted paths to LDR, invoke the official renderer, or pack eight-view tar shards."""
import argparse
import io
import json
import subprocess
import tarfile
from pathlib import Path
from paper_common import (Journal, fingerprint, keyed, load_bricknet, normalize_ids, read_jsonl,
                          safe_name, sha256, source_hashes, write_json, write_jsonl)


def join_captions(args):
    captions = read_jsonl(args.captions)
    caption_index = keyed(captions, 'id')
    results = []
    for row in read_jsonl(args.paths):
        source = str(row.get('source','')).removesuffix('.npz')
        if source not in caption_index:
            raise ValueError(f'No held-out caption for path source: {source}')
        if 'sample_id' in row:
            sid = str(row['sample_id'])
        else:
            required = ['round','component_index','sample_index']
            if any(k not in row for k in required):
                raise ValueError('Path needs sample_id or source/round/component_index/sample_index')
            sid = f'{source}__r{row["round"]}__c{row["component_index"]}__s{row["sample_index"]}'
        if not isinstance(row.get('path',row.get('text')),str):
            raise ValueError('No ground-truth path text')
        results.append({**row,'sample_id':sid,'caption':caption_index[source]['caption']})
    keyed(results)
    write_jsonl(args.out,results)
    write_json(args.out.with_suffix('.join.json'),{'paths_sha256':sha256(args.paths),
        'captions_sha256':sha256(args.captions),'path_records':len(results),
        'models':len({r['source'] for r in results}),
        'selection':'all supplied paths, no collision filtering or per-model subsampling'})


def validated_views(row, base):
    paths = [Path(base)/p for p in row['view_paths']]
    if len(paths) != 8 or len(set(p.resolve() for p in paths)) != 8:
        raise ValueError(f'{row["sample_id"]}: exactly eight distinct view files required')
    hashes = [sha256(p) for p in paths]
    if row.get('view_sha256') is not None and hashes != row['view_sha256']:
        raise ValueError(f'{row["sample_id"]}: render hash mismatch')
    return paths, hashes


def convert(args):
    bricknet = load_bricknet(args.bricknet_version)
    rows = normalize_ids(read_jsonl(args.input))
    args.out.mkdir(parents=True, exist_ok=True)
    results = []
    for row in rows:
        text = row.get('path', row.get('text'))
        if not isinstance(text, str):
            raise ValueError('Input requires original generated path/text')
        parsed = bricknet.parse_sample(text if text.endswith('\n') else text+'\n')
        if parsed.error is not None or not parsed.tree.parts:
            raise ValueError(f'{row["sample_id"]}: cannot render a failed parse: {parsed.error}')
        ldr = bricknet.graph_to_ldr(bricknet.tree_to_graph(parsed.tree))
        path = args.out/(safe_name(row['sample_id'])+'.ldr')
        if path.exists() and path.read_text(encoding='utf-8') != ldr:
            raise ValueError(f'Changed LDR output: {path}')
        path.write_text(ldr, encoding='utf-8')
        results.append({**row, 'ldr_path': str(path.resolve()), 'ldr_sha256': sha256(path),
                        'bricknet_version': bricknet.__version__})
    write_jsonl(args.out/'ldr_manifest.jsonl', results)


def render(args):
    rows = normalize_ids(read_jsonl(args.input))
    if not rows:
        raise ValueError('Empty LDR manifest')
    # Query the renderer interpreter, which can differ from the score interpreter.
    probe = 'import sys,json,importlib.metadata as m; print(json.dumps({"python":list(sys.version_info[:3]),"bricknet-render":m.version("bricknet-render"),"bpy":m.version("bpy")}))'
    runtime = json.loads(subprocess.check_output([args.renderer_python,'-c',probe], text=True))
    if runtime['python'][:2] < [3,13]:
        raise RuntimeError('Official current renderer requires a separate Python 3.13+ interpreter')
    from importlib.metadata import version
    from PIL import Image
    config = {'renderer': 'official bricknet-render CLI --views 8', 'runtime': runtime,
        'pillow_version': version('pillow'), 'input_sha256': sha256(args.input),
        'renderer_python': str(Path(args.renderer_python).resolve()),
        'historical_camera_and_lighting_match': 'not verified; current official renderer defaults',
        'sources': source_hashes(__file__)}
    journal = Journal(args.out/'renders.jsonl', config)
    for row in rows:
        ldr = Path(row['ldr_path'])
        digest = sha256(ldr)
        if digest != row['ldr_sha256']:
            raise ValueError(f'{ldr}: LDR modified')
        ih = fingerprint(row)
        cached = journal.cached(row['sample_id'], ih)
        if cached:
            validated_views(cached, args.out)
            continue
        folder = args.out/'views'/safe_name(row['sample_id'])
        if folder.exists() and any(folder.iterdir()):
            raise ValueError(f'Unjournaled render directory exists: {folder}; inspect/move it before retry')
        folder.mkdir(parents=True, exist_ok=True)
        command = [args.renderer_python,'-m','bricknet_render',str(ldr),str(folder),'--views','8']
        with (args.out/(safe_name(row['sample_id'])+'.render.log')).open('w', encoding='utf-8') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=args.timeout)
        paths = sorted(p for p in folder.rglob('*') if p.suffix.lower() in {'.png','.jpg','.jpeg'})
        if len(paths) != 8:
            raise ValueError(f'Official renderer returned {len(paths)} images, expected eight')
        sizes = []
        for path in paths:
            with Image.open(path) as image:
                sizes.append(list(image.size))
                image.verify()
        result = {**row, 'view_paths': [str(p.relative_to(args.out)) for p in paths],
                  'view_sha256': [sha256(p) for p in paths], 'image_sizes': sizes,
                  'render_protocol': config['renderer']}
        journal.append(result, ih)
        print(row['sample_id'], flush=True)


def pack(args):
    rows = normalize_ids(read_jsonl(args.renders))
    if not rows:
        raise ValueError('No renders')
    keyed(rows)
    if args.out.exists() and any(args.out.iterdir()):
        raise ValueError('Pack output must be new or empty; never overwrite existing shards')
    # Validate all records before creating any output.
    checked = []
    for row in rows:
        if not isinstance(row.get('caption'), str) or not row['caption'].strip():
            raise ValueError('Each render needs its original caption')
        paths, hashes = validated_views(row, args.renders.parent)
        checked.append((row, paths, hashes))
    args.out.mkdir(parents=True, exist_ok=True)
    captions = []
    for start in range(0,len(checked),args.shard_size):
        shard = args.out/f'renders_{start//args.shard_size:05d}.tar'
        with tarfile.open(shard, 'w') as archive:
            for index in range(start, min(start+args.shard_size,len(checked))):
                row, paths, _ = checked[index]
                # Index names keep captions order unambiguous for the released scripts.
                key = f'prompt_{index:04d}'
                for view, path in enumerate(paths):
                    data = path.read_bytes()
                    name = f'{key}/{key}_{view:04d}{path.suffix.lower()}'
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    info.mtime = 0
                    archive.addfile(info, io.BytesIO(data))
                captions.append({'id':row['sample_id'],'caption':row['caption']})
    write_jsonl(args.out/'captions.jsonl', captions)
    write_json(args.out/'packing_manifest.json', {'input_sha256':sha256(args.renders),
        'samples':len(rows),'views':len(rows)*8,
        'view_sha256':{r['sample_id']:h for r,_,h in checked},
        'files':{p.name:sha256(p) for p in sorted(args.out.glob('*.tar'))},
        'captions_sha256':sha256(args.out/'captions.jsonl')})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    c = sub.add_parser('convert')
    c.add_argument('--input', required=True, type=Path)
    c.add_argument('--out', required=True, type=Path)
    c.add_argument('--bricknet-version', choices=['0.1.0','0.1.1'], default='0.1.0')
    c.set_defaults(function=convert)
    r = sub.add_parser('render')
    r.add_argument('--input', required=True, type=Path)
    r.add_argument('--out', required=True, type=Path)
    r.add_argument('--renderer-python', required=True)
    r.add_argument('--timeout', type=int, default=1200)
    r.set_defaults(function=render)
    t = sub.add_parser('pack')
    t.add_argument('--renders', required=True, type=Path)
    t.add_argument('--out', required=True, type=Path)
    t.add_argument('--shard-size', type=int, default=128)
    t.set_defaults(function=pack)
    j = sub.add_parser('join-captions', help='Join official paths_val by source to captions_val by id; accepts .xz')
    j.add_argument('--paths',required=True,type=Path)
    j.add_argument('--captions',required=True,type=Path)
    j.add_argument('--out',required=True,type=Path)
    j.set_defaults(function=join_captions)
    args = p.parse_args()
    if getattr(args,'shard_size',1) < 1:
        p.error('--shard-size must be positive')
    args.function(args)


if __name__ == '__main__':
    main()
