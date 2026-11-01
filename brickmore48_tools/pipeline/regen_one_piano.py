"""剩余未解出条目:180s 封顶求解,解不出换新种子重新生成(最多 4 个新种子)。
接受标准:生成合法(或 union)→ 凸点审计可拼(保留原版)或 12/60/180s 内重铺成功。
原 raw 备份为 raw_attempt0.*,账本记录重生成历史。"""
import json
import glob
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

a = single.retile_core.base.q.a
BASE = Path(r'E:\brick_train\brick_infer_5070ti_20261001\BrickGPT\bmore48_levels2')
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


_f = str(BASE / 'manifest_w1.json')  # piano 属 w1;B 路已收工,无写竞争
manifests = {_f: json.load(open(_f, encoding='utf-8'))}
print('single-item mode: piano L1V1', flush=True)
PROMPTS = {}
for f in ['levels2_a.json', 'levels2_b.json', 'levels2_c.json', 'levels2_d.json']:
    PROMPTS.update(json.loads((BASE.parent.parent / f).read_text(encoding='utf-8')))

NEW_SEEDS = [12, 99, 123, 512, 1024, 2048, 4096, 65537]
targets = []
for f, rows in manifests.items():
    for m in rows:
        if m['category'] == 'piano' and m['level'] == 1 and m['variant'] == 1:
            targets.append((f, m))
print(f'{len(targets)} items to regen', flush=True)

for f, m in targets:
    cat, lvl, v = m['category'], m['level'], m['variant']
    caption = PROMPTS[cat][lvl - 1][v - 1]
    d = BASE / cat / f'L{lvl}V{v}'
    print(f'>>> {cat} L{lvl}V{v}', flush=True)
    # 备份原 raw
    for s in ('raw.txt', 'raw_report.json', 'raw.ldr', 'raw.obj'):
        p = d / s
        if p.exists() and not (d / (s + '.bak')).exists():
            p.rename(d / (s + '.bak'))
    history = []
    accepted = None
    for seed in NEW_SEEDS:
        text, completed, el, ntok = gen(caption, seed)
        rep = local_run.validate(text)
        path_kind = None
        if not (completed and rep['geometry_valid']):
            if completed:
                path_kind = 'union'
            else:
                history.append({'seed': seed, 'result': 'incomplete'})
                continue
        else:
            path_kind = 'direct'
        cells, dropped = union_cells(rep['bricks'])
        raw_bricks = [dict(h=b['h'], w=b['w'], x=b['x'], y=b['y'], z=b['z'], color=1) for b in rep['bricks']]
        ok_raw = single.audit(raw_bricks, cells)['singleComponentPassed']
        if ok_raw:
            accepted = ('raw_ok', seed, text, rep, cells, el, ntok, path_kind)
            history.append({'seed': seed, 'result': 'raw_single_component'})
            break
        chosen, tier = None, 'unsolved'
        for sec, tag in ((12, '12s'), (60, '60s'), (180, '180s')):
            chosen, det = single.solve(cells, seconds=sec)
            tier = tag
            if chosen:
                break
        if chosen:
            accepted = ('retiled', seed, text, rep, cells, el, ntok, path_kind, chosen, tier)
            history.append({'seed': seed, 'result': f'retiled@{tier}'})
            break
        history.append({'seed': seed, 'result': f'unsolved@180s'})
    if not accepted:
        # 恢复备份,如实标记
        for s in ('raw.txt', 'raw_report.json', 'raw.ldr', 'raw.obj'):
            b = d / (s + '.bak')
            if b.exists():
                b.rename(d / s)
        m['regen_history'] = history
        m['stitched'] = False
        print(f'    4 seeds all failed: {history}', flush=True)
        json.dump(manifests[f], open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        continue
    kind = accepted[0]
    if kind == 'raw_ok':
        _, seed, text, rep, cells, el, ntok, path_kind = accepted
        m.update(regen_seed=seed, regen_history=history, path=path_kind, seconds=el, tokens=ntok,
                 raw_bricks=rep['brick_count'], voxels=len(cells), raw_single_component=True,
                 stitched=True, assembly_method='original_inference_already_single_component',
                 assembly_bricks=rep['brick_count'], solver_tier='none_needed', studOK=True,
                 shape_preserved=True)
    else:
        _, seed, text, rep, cells, el, ntok, path_kind, chosen, tier = accepted
        geometry = [{k: b[k] for k in ('h', 'w', 'x', 'y', 'z')} for b in chosen]
        (d / 'stitched.txt').write_text(
            ''.join(a.Placement(**b).to_txt() for b in geometry), encoding='utf-8')
        (d / 'stitched.ldr').write_text(
            a.to_ldr({'status': 'success', 'bricks': geometry}, cells), encoding='utf-8')
        chk = single.audit(chosen, cells)
        st_v = {(x, y, b['z']) for b in geometry for x in range(b['x'], b['x'] + b['h'])
                for y in range(b['y'], b['y'] + b['w'])}
        m.update(regen_seed=seed, regen_history=history, path=path_kind, seconds=el, tokens=ntok,
                 raw_bricks=rep['brick_count'], voxels=len(cells), raw_single_component=False,
                 stitched=True, assembly_bricks=len(chosen), solver_tier=tier,
                 studOK=bool(chk['singleComponentPassed']), shape_preserved=bool(st_v == set(cells)))
    # 落盘新 raw + 重建 LDR/OBJ
    (d / 'raw.txt').write_text(text, encoding='utf-8')
    (d / 'raw_report.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8')
    import re
    sys.path.insert(0, str(Path(__file__).resolve().parent / 'BrickGPT' / 'src'))
    from brickgpt.data import Brick, BrickStructure
    lines = [f"{b['h']}x{b['w']} ({b['x']},{b['y']},{b['z']})" for b in rep['bricks']]
    bs = BrickStructure([Brick.from_txt(l) for l in lines], world_dim=48)
    (d / 'raw.ldr').write_text(bs.to_ldr(), encoding='utf-8')
    print(f"    ACCEPTED {kind} seed={m.get('regen_seed')} history={len(history)}", flush=True)
    json.dump(manifests[f], open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    torch.cuda.empty_cache()
print('REGEN DONE', flush=True)
