"""BrickMore-48 第二轮重做:tower L3-L5 / train L1-L5 / vessel L2-L5,每组 5 个模型。
提示词来自 round3_prompts.json(严格按 48³ 训练集五级模板与训练词库生成),每组取 5 条:
索引 0,2,4,6,8(L4/L5 覆盖不同比例/配色档位)。
协议:采样 t0.7 种子 42→104→2026 → 完整+几何双检 → union 修复 → MILP 12/60/180s →
仍不可解则换兜底种子 7/2027/555/888(末档 600s)→ raw+stitched 双存档到
BrickGPT/bmore48_round3/<cat>/L<lvl>_R<idx>/。
用法: python gen_round2.py <worker_id 0|1>
"""
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
OUT = HERE / 'BrickGPT' / 'bmore48_round3'
OUT.mkdir(parents=True, exist_ok=True)
a = single.retile_core.base.q.a
DIMS = local_run.DIMENSIONS

MODEL_DIR = PKG / 'local_brickgpt' / 'model'
tok = AutoTokenizer.from_pretrained(MODEL_DIR, local_files_only=True)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_DIR, torch_dtype=torch.bfloat16, attn_implementation='sdpa',
    local_files_only=True).to('cuda').eval()
print('MODEL READY', flush=True)

PLAN = json.loads((HERE / 'round3_prompts.json').read_text(encoding='utf-8'))
PICK = [0, 2, 4, 6, 8]          # 每组 10 条里取 5 条,跨措辞/比例/配色档位
import os
FAST = bool(os.environ.get('R3_FAST'))
SEEDS = [42] if FAST else [42, 104, 2026]
REGEN_SEEDS = [7] if FAST else [7, 2027, 555]
TIERS = [(12, '12s'), (60, '60s'), (180, '180s')]


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


def solve_escalate(cells, extra_600=False):
    tiers = TIERS + ([(600, '600s')] if extra_600 else [])
    for sec, tag in tiers:
        chosen, det = single.solve(cells, seconds=sec)
        if chosen:
            return chosen, tag
    return None, 'unsolved'


def attempt_prompt(caption, dest, row):
    attempts = []
    accepted = None
    for label, seed in [('@42', 42), ('@104', 104), ('@2026', 2026)]:
        text, completed, el, ntok = gen(caption, seed)
        rep = local_run.validate(text)
        attempts.append((label, text, completed, rep, el, ntok))
        if completed and rep['geometry_valid']:
            accepted = ('direct', label, text, rep, el, ntok)
            break
    if not accepted:
        comp = [x for x in attempts if x[2]]
        if not comp:
            raise RuntimeError('all attempts incomplete')
        best = min(comp, key=lambda x: len(x[3]['errors']))
        accepted = ('union', best[0], best[1], best[3], best[4], best[5])

    kind, label, text, rep, el, ntok = accepted
    cells, dropped = union_cells(rep['bricks'])
    (dest / 'raw.txt').write_text(text, encoding='utf-8')
    (dest / 'raw_report.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8')
    raw_geo = [{k: b[k] for k in ('h', 'w', 'x', 'y', 'z')}
               for b in rep['bricks']
               if (b['h'], b['w']) in DIMS and 0 <= b['x'] and b['x'] + b['h'] <= 48
               and 0 <= b['y'] and b['y'] + b['w'] <= 48 and 0 <= b['z'] < 48]
    if raw_geo:
        (dest / 'raw.ldr').write_text(
            a.to_ldr({'status': 'raw', 'bricks': raw_geo}, cells), encoding='utf-8')

    chosen, tier = solve_escalate(cells)
    regen_seed = None
    if not chosen:
        # 换种子重生成,末档允许 600s
        for seed in REGEN_SEEDS:
            text, completed, el, ntok = gen(caption, seed)
            rep = local_run.validate(text)
            if not completed or not rep['bricks']:
                continue
            cells2, dropped2 = union_cells(rep['bricks'])
            chosen, tier = solve_escalate(cells2, extra_600=False)
            if chosen:
                (dest / 'raw.txt').write_text(text, encoding='utf-8')
                (dest / 'raw_report.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8')
                cells, dropped = cells2, dropped2
                raw_geo = [{k: b[k] for k in ('h', 'w', 'x', 'y', 'z')}
                           for b in rep['bricks']
                           if (b['h'], b['w']) in DIMS and 0 <= b['x'] and b['x'] + b['h'] <= 48
                           and 0 <= b['y'] and b['y'] + b['w'] <= 48 and 0 <= b['z'] < 48]
                if raw_geo:
                    (dest / 'raw.ldr').write_text(
                        a.to_ldr({'status': 'raw', 'bricks': raw_geo}, cells), encoding='utf-8')
                regen_seed = seed
                kind, label = 'regen', f'@{seed}'
                break

    row.update(path=kind, attempt=label, seconds=el, tokens=ntok,
               raw_bricks=len(raw_geo), voxels=len(cells), union_dropped_bricks=dropped,
               solver_tier=tier, stitched=bool(chosen),
               assembly_bricks=len(chosen) if chosen else None, regen_seed=regen_seed)
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
    return row


WORKER = int(sys.argv[1]) if len(sys.argv) > 1 else 0
JOBS = []
for key in PLAN["groups"]:
    cat, lv = key.rsplit("_L", 1)
    JOBS.append((cat, int(lv)))
GROUPS = [(c, [l]) for c, l in JOBS]
if os.environ.get('R3_JOB_FILTER'):
    allow = set(os.environ['R3_JOB_FILTER'].split(','))
    JOBS = [j for j in JOBS if f'{j[0]}_L{j[1]}' in allow]
    my_jobs = JOBS
my_jobs = my_jobs if 'my_jobs' in dir() else JOBS[WORKER::2]
suffix = os.environ.get('R3_MANIFEST_SUFFIX', '')
manifest_path = OUT / f'manifest_r3_w{WORKER}{suffix}.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else []
done = {(m['category'], m['level'], m['variant']) for m in manifest}
print(f'worker {WORKER}: {len(my_jobs)} groups, done {len(done)}', flush=True)

for cat, lvl in my_jobs:
    g = PLAN['groups'][f'{cat}_L{lvl}']
    seq = g if isinstance(g, list) else g['prompts']
    for pi in PICK:
        p = seq[pi]
        variant = p['id'].split('-')[-1]
        if (cat, lvl, variant) in done:
            continue
        dest = OUT / cat / f'L{lvl}_{variant}'
        dest.mkdir(parents=True, exist_ok=True)
        row = {'category': cat, 'level': lvl, 'variant': variant,
               'prompt_id': p['id'], 'prompt': p['en'], 'prompt_zh': p['zh']}
        print(f">>> {cat} L{lvl} {variant}", flush=True)
        try:
            row = attempt_prompt(p['en'], dest, row)
            print(f"    {row['path']}{row['attempt']}: {row['raw_bricks']}砖/{row['voxels']}vox "
                  f"tier={row['solver_tier']} stitch={row['stitched']}", flush=True)
        except Exception as e:
            row['error'] = f'{type(e).__name__}: {str(e)[:150]}'
            print(f'    FAILED: {row["error"]}', flush=True)
        (dest / 'prompt.txt').write_text(p['en'] + '\n' + p['zh'] + '\n', encoding='utf-8')
        manifest.append(row)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding='utf-8')
        torch.cuda.empty_cache()

print('WORKER DONE', flush=True)
