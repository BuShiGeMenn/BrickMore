"""525 条全新提示词(21类×5级×5变体)新管线批跑:
采样(t0.7@42/104/2026)→ 完整+几何合法双检 → 不合法但写完的走体素并集修复 →
MILP 保形重铺 12s→60s→180s 升级 → raw+stitched 双版本存档。"""
import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
PKG = Path(r'E:\brick_train\BrickGPT_Local_Inference_Source_20261018_154809'
           r'\BrickGPT_Local_Inference_Source_20261018_154809')
sys.path.insert(0, str(PKG / 'local_brickgpt'))

import torch  # noqa: E402
import transformers  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402
import run as local_run  # noqa: E402
import single_stud_cover as single  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / 'BrickGPT' / 'bmore48_levels2'
OUT.mkdir(parents=True, exist_ok=True)
a = single.retile_core.base.q.a
DIMS = local_run.DIMENSIONS

MODEL_DIR = PKG / 'local_brickgpt' / 'model'
tok = AutoTokenizer.from_pretrained(MODEL_DIR, local_files_only=True)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_DIR, torch_dtype=torch.bfloat16, attn_implementation='sdpa',
    local_files_only=True).to('cuda').eval()
print('MODEL READY', flush=True)


def gen(caption, seed):
    transformers.set_seed(seed)
    rendered = tok.apply_chat_template(
        [{'role': 'system', 'content': 'You are a helpful assistant.'},
         {'role': 'user', 'content': local_run.create_instruction(caption)}],
        tokenize=False, add_generation_prompt=True, enable_thinking=False)
    inputs = tok(rendered, return_tensors='pt').to('cuda')
    t0 = time.perf_counter()
    with torch.inference_mode():
        result = model.generate(**inputs, max_new_tokens=8192, use_cache=True, do_sample=True,
                                temperature=0.7, top_p=0.9, pad_token_id=tok.eos_token_id)
    torch.cuda.synchronize()
    el = round(time.perf_counter() - t0, 1)
    g = result[0, inputs.input_ids.shape[1]:].tolist()
    text = tok.decode(g, skip_special_tokens=True)
    eos = model.generation_config.eos_token_id
    eos = eos if isinstance(eos, list) else [eos]
    return text, bool(g and g[-1] in eos), el, len(g)


def union_cells(bricks):
    """白名单+界内砖取体素并集(越界部分自然裁剪);返回 cells 与被跳过的砖数。"""
    cells, dropped = {}, 0
    for b in bricks:
        if (b['h'], b['w']) not in DIMS:
            dropped += 1
            continue
        x0, x1 = max(0, b['x']), min(48, b['x'] + b['h'])
        y0, y1 = max(0, b['y']), min(48, b['y'] + b['w'])
        z = b['z']
        if z < 0 or z >= 48 or x0 >= x1 or y0 >= y1:
            dropped += 1
            continue
        for x in range(x0, x1):
            for y in range(y0, y1):
                cells[(x, y, z)] = 1
    return cells, dropped


def solve_escalate(cells):
    for sec, tag in ((12, '12s'), (60, '60s'), (180, '180s')):
        chosen, det = single.solve(cells, seconds=sec)
        if chosen:
            return chosen, tag
    return None, 'unsolved'


PROMPTS = {}
for f in ['levels2_a.json', 'levels2_b.json', 'levels2_c.json', 'levels2_d.json']:
    PROMPTS.update(json.loads((HERE / f).read_text(encoding='utf-8')))

WORKER = int(sys.argv[1]) if len(sys.argv) > 1 else 0
if len(sys.argv) > 2:  # 显式类别覆盖(负载再平衡用)
    my_cats = sys.argv[2].split(',')
else:
    cats = sorted(PROMPTS)
    half = (len(cats) + 1) // 2
    my_cats = cats[:half] if WORKER == 0 else cats[half:]
manifest_path = OUT / f'manifest_w{WORKER}.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else []
done = {(m['category'], m['level'], m['variant']) for m in manifest}
print(f'worker {WORKER}: {len(my_cats)} cats, done {len(done)}', flush=True)

for cat in my_cats:
    for lvl in range(1, 6):
        for v in range(1, 6):
            if (cat, lvl, v) in done:
                continue
            caption = PROMPTS[cat][lvl - 1][v - 1]
            dest = OUT / cat / f'L{lvl}V{v}'
            dest.mkdir(parents=True, exist_ok=True)
            row = {'category': cat, 'level': lvl, 'variant': v, 'prompt': caption}
            print(f'>>> {cat} L{lvl}V{v}', flush=True)
            try:
                attempts = []
                accepted = None
                for label, seed in [('@42', 42), ('@104', 104), ('@2026', 2026)]:
                    text, completed, el, ntok = gen(caption, seed)
                    rep = local_run.validate(text)
                    attempts.append((label, text, completed, rep, el, ntok))
                    if completed and rep['geometry_valid']:
                        accepted = ('direct', label, text, rep, el, ntok)
                        break
                path_kind = None
                if not accepted:
                    comp = [x for x in attempts if x[2]]
                    if comp:
                        best = min(comp, key=lambda x: len(x[3]['errors']))
                        path_kind = 'union'
                        accepted = ('union', best[0], best[1], best[3], best[4], best[5])
                    else:
                        raise RuntimeError('all attempts incomplete')
                kind, label, text, rep, el, ntok = accepted

                if kind == 'direct':
                    cells, dropped = union_cells(rep['bricks'])
                else:
                    cells, dropped = union_cells(rep['bricks'])
                (dest / 'raw.txt').write_text(text, encoding='utf-8')
                (dest / 'raw_report.json').write_text(
                    json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8')

                chosen, tier = solve_escalate(cells)
                row.update(path=kind, attempt=label, seconds=el, tokens=ntok,
                           raw_bricks=rep['brick_count'], voxels=len(cells),
                           union_dropped_bricks=dropped, solver_tier=tier,
                           stitched=bool(chosen),
                           assembly_bricks=len(chosen) if chosen else None)
                if chosen:
                    geometry = [{k: b[k] for k in ('h', 'w', 'x', 'y', 'z')} for b in chosen]
                    (dest / 'stitched.txt').write_text(
                        ''.join(a.Placement(**b).to_txt() for b in geometry), encoding='utf-8')
                    (dest / 'stitched.ldr').write_text(
                        a.to_ldr({'status': 'success', 'bricks': geometry}, cells), encoding='utf-8')
                    chk = single.audit(chosen, cells)
                    st_v = {(x, y, b['z']) for b in geometry
                            for x in range(b['x'], b['x'] + b['h'])
                            for y in range(b['y'], b['y'] + b['w'])}
                    row['studOK'] = bool(chk['singleComponentPassed'])
                    row['shape_preserved'] = bool(st_v == set(cells))
                print(f"    {kind}{label}: {row['raw_bricks']}砖/{row['voxels']}vox "
                      f"tier={tier} stitch={row['stitched']}", flush=True)
            except Exception as e:
                row['error'] = f'{type(e).__name__}: {str(e)[:150]}'
                print(f'    FAILED: {row["error"]}', flush=True)
            manifest.append(row)
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding='utf-8')
            torch.cuda.empty_cache()

print('WORKER DONE', flush=True)
