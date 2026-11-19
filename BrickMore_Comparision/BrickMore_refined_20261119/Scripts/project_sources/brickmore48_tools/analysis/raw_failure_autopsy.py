# -*- coding: utf-8 -*-
"""raw 失败病因解剖:对 bmore48_levels2 的 525 条原始输出量化
  - 重叠:重复涂色体素数
  - stud 咬合断裂:按"上下层重叠"建砖块连通图,统计分量数/孤儿体素/落地性
  - 孤儿与主体空间距离(切比雪夫):1=贴身不咬合
用法: python raw_failure_autopsy.py <bmore48_levels2 根目录> [-o autopsy.json]
"""
import argparse
import json
import statistics
from collections import Counter
from pathlib import Path


def brick_stud_components(bricks):
    """stud 连通图:仅上下层(z 相邻)体素重叠才连边,返回 {root: [bricks]}"""
    owner = {}
    for i, b in enumerate(bricks):
        for x in range(b["x"], b["x"] + b["h"]):
            for y in range(b["y"], b["y"] + b["w"]):
                owner.setdefault((x, y, b["z"]), i)
    parent = list(range(len(bricks)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for (x, y, z), i in owner.items():
        j = owner.get((x, y, z + 1))
        if j is not None and j != i:
            ra, rb = find(i), find(j)
            if ra != rb:
                parent[ra] = rb
    comps = {}
    for i, b in enumerate(bricks):
        comps.setdefault(find(i), []).append(b)
    return comps


def voxels_of(bs):
    return {(x, y, b["z"]) for b in bs
            for x in range(b["x"], b["x"] + b["h"])
            for y in range(b["y"], b["y"] + b["w"])}


def duplicate_voxels(bricks):
    occ = {}
    dup = 0
    for b in bricks:
        for x in range(b["x"], b["x"] + b["h"]):
            for y in range(b["y"], b["y"] + b["w"]):
                p = (x, y, b["z"])
                if p in occ:
                    dup += 1
                else:
                    occ[p] = 1
    return dup


def autopsy(bricks):
    dup = duplicate_voxels(bricks)
    comps = brick_stud_components(bricks)
    vox = {r: voxels_of(bs) for r, bs in comps.items()}
    main = max(vox, key=lambda r: len(vox[r]))
    mset = vox[main]
    orphan_n = len(vox) - 1
    orphan_vox = sum(len(v) for r, v in vox.items() if r != main)
    floating = sum(1 for r, bs in comps.items() if r != main and min(b["z"] for b in bs) > 0)
    # 孤儿→主体最小切比雪夫距离(≤2 内搜索,>2 记 99)
    dists = []
    for r, vs in vox.items():
        if r == main:
            continue
        best = 99
        for (x, y, z) in vs:
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    for dz in range(-2, 3):
                        if (x + dx, y + dy, z + dz) in mset:
                            best = min(best, max(abs(dx), abs(dy), abs(dz)))
        dists.append(best)
    return dict(dup=dup, stud_components=len(comps), main_vox=len(mset),
                orphan_vox=orphan_vox, orphan_chunks=orphan_n,
                floating_chunks=floating, min_dist=[min(dists) if dists else None],
                dist_hist=dict(Counter(dists)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("levels2_root", help="含 manifest_w*.json 与 <category>/L<lvl>V<var>/ 的目录")
    ap.add_argument("-o", "--out", default="raw_failure_autopsy.json")
    args = ap.parse_args()
    root = Path(args.levels2_root)

    rows = []
    for w in sorted(root.glob("manifest_w*.json")):
        rows += json.loads(w.read_text(encoding="utf-8"))

    stats = []
    for r in rows:
        d = root / r["category"] / f"L{r['level']}V{r['variant']}"
        rep = json.loads((d / "raw_report.json").read_text(encoding="utf-8"))
        a = autopsy(rep["bricks"])
        a.update(category=r["category"], level=r["level"], variant=r["variant"],
                 raw_single_component=bool(r.get("raw_single_component")))
        stats.append(a)

    fail = [s for s in stats if not s["raw_single_component"]]
    ok = [s for s in stats if s["raw_single_component"]]
    print(f"总 {len(stats)} | 一遍过 {len(ok)} | 失败 {len(fail)}")
    if fail:
        dups = [s["dup"] for s in fail if s["dup"]]
        print(f"有重叠: {len(dups)} 条, 重复体素中位 {statistics.median(dups) if dups else 0:.0f}")
        nc = [s["stud_components"] for s in fail]
        print(f"stud 分量数: 中位 {statistics.median(nc):.0f} / p90 {sorted(nc)[int(len(nc) * .9)]} / 最大 {max(nc)}")
        touch = sum(1 for s in fail
                    for d in s["dist_hist"]
                    if d <= 1)
        print(f"贴近主体(距离≤1)的孤儿分量: {touch}")
    Path(args.out).write_text(json.dumps(stats, ensure_ascii=False), encoding="utf-8")
    print("明细 →", args.out)


if __name__ == "__main__":
    main()
