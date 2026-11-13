# -*- coding: utf-8 -*-
"""最终装配:把第三轮 7 组的挑选结果并入 112 个已定模型,生成 105 组完整展示。

用法(在本包根目录):
    python 工具/build_final_display.py

前置:编辑本包根目录的 picks_round3.json,为 7 组各填一个候选 ID(或 null 表示不合格)。
输出:最终展示_完成/(页面 + 全部模型) + 最终清单.csv
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "最终展示"
CAND = ROOT / "候选审查_第三轮"
OUT = ROOT / "最终展示_完成"
PICKS = ROOT / "picks_round3.json"

GROUPS = ["basket_L2", "bench_L4", "bench_L5", "mug_L3", "mug_L4", "mug_L5", "table_L5"]


def main():
    if not PICKS.exists():
        sys.exit(f"缺少 {PICKS.name}")
    picks = json.loads(PICKS.read_text(encoding="utf-8-sig"))
    base = json.loads((BASE / "static" / "curated.json").read_text(encoding="utf-8"))
    cands = {e["id"]: e for e in json.loads((CAND / "static" / "round3.json").read_text(encoding="utf-8"))}

    missing = [g for g in GROUPS if g not in picks]
    if missing:
        sys.exit(f"picks_round3.json 缺少这些组: {missing}")

    final = list(base)
    unresolved = []
    for g in GROUPS:
        cid = picks[g]
        if not cid:
            unresolved.append(g)
            continue
        e = cands.get(cid)
        if e is None:
            sys.exit(f"候选 ID 不存在: {g} -> {cid}")
        if f"{e['category']}_L{e['level']}" != g:
            sys.exit(f"候选不属于该组: {g} -> {cid}")
        # 合集页面用 glb 加载原版;候选页的数据字段名是 raw_glb。
        final.append(dict(e, glb=e["raw_glb"], source="round3", source_zh="第三轮补缺", status="raw_ok"))

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copy2(BASE / "server.py", OUT / "server.py")
    shutil.copytree(BASE / "static", OUT / "static")
    shutil.copytree(BASE / "models", OUT / "models")
    for g in GROUPS:
        cid = picks[g]
        if not cid:
            continue
        e = cands[cid]
        for field in ("raw_glb", "stitched_glb"):
            rel = e.get(field)
            if rel:
                shutil.copy2(CAND / rel, OUT / rel)

    (OUT / "static" / "curated.json").write_text(json.dumps(final, ensure_ascii=False, indent=1), encoding="utf-8")

    # 清单 CSV
    lines = ["category,level,id,source,source_zh,prompt_zh"]
    for e in final:
        lines.append(f"{e['category']},{e.get('level') or ''},{e['id']},{e['source']},{e['source_zh']},"
                     f"\"{(e.get('prompt_zh') or '').replace(chr(34), chr(39))}\"")
    (ROOT / "最终清单.csv").write_text("\n".join(lines) + "\n", encoding="utf-8-sig")

    groups = {(e["category"], e["level"]) for e in final if e.get("level") is not None}
    print(f"完成:{len(final)} 个模型,覆盖 {len(groups)} 个类×等级组")
    if unresolved:
        print("以下组未选择(视为不合格,保持空缺):", ", ".join(unresolved))
    print(f"页面: 最终展示_完成/  →  cd 最终展示_完成 && python server.py 8126")
    print("清单: 最终清单.csv")


if __name__ == "__main__":
    main()
