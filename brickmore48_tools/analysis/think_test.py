# -*- coding: utf-8 -*-
"""实验:现有 BrickMore-48 检查点直接打开 thinking,完整记录思考输出。"""
import json
import sys
import time
import torch

sys.path.insert(0, r"E:\brick_train\BrickGPT_Local_Inference_Source_20261018_154809\BrickGPT_Local_Inference_Source_20261018_154809\local_brickgpt")
from run import create_instruction, validate  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402
from pathlib import Path

OUT = Path(r"E:\brick_train\brick_infer_5070ti_20261001\think_output.txt")

def log(s):
    OUT.open("a", encoding="utf-8").write(s + "\n")
    print(s, flush=True)

M = Path(r"D:\MODELS\BrickGPT-Qwen3-BrickMore-48")
t0 = time.time()
tok = AutoTokenizer.from_pretrained(M, local_files_only=True)
model = AutoModelForCausalLM.from_pretrained(M, torch_dtype=torch.bfloat16, attn_implementation="sdpa", local_files_only=True).to("cuda").eval()
log(f"[{time.time()-t0:.0f}s] 模型加载完成")

PROMPTS = [
    "A simple wooden table with a rectangular tabletop and four legs.",
    "A round picnic basket.",
    "A coffee mug with a handle.",
]

for i, p in enumerate(PROMPTS, 1):
    rendered = tok.apply_chat_template(
        [{"role": "system", "content": "You are a helpful assistant."},
         {"role": "user", "content": create_instruction(p)}],
        tokenize=False, add_generation_prompt=True, enable_thinking=True)
    inputs = tok(rendered, return_tensors="pt").to("cuda")
    log(f"\n{'='*72}\n[{i}/3] 提示词: {p}")
    log(f"模板尾部(确认思考开关): ...{rendered[-120:]!r}")
    tg0 = time.time()
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=8192, do_sample=True, temperature=0.6, top_p=0.9,
                             pad_token_id=tok.eos_token_id)
    gen = tok.decode(out[0, inputs.input_ids.shape[1]:], skip_special_tokens=False)
    gen_toks = out.shape[1] - inputs.input_ids.shape[1]
    think = gen.split("</think>")[0]
    answer = gen.split("</think>")[-1] if "</think>" in gen else ""
    rep = validate(answer)
    log(f"生成 {gen_toks} tokens,耗时 {time.time()-tg0:.0f}s")
    log(f"是否出现 </think>: {'</think>' in gen}")
    log(f"\n----- 完整思考输出(前 4000 字) -----\n{think[:4000]}")
    log(f"----- 思考输出结束(总长 {len(think)} 字) -----")
    log(f"答案: {rep['brick_count']} 块砖 | 几何合法 {rep['geometry_valid']} | 连通分量 {rep['voxel_components']}")
log("\nDONE")
