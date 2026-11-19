import csv
import hashlib
import html
import json
import math
import os
from html.parser import HTMLParser
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, ticker
import numpy as np


ROOT = Path(r"D:\BrickMore")
OLD_PACKAGE = (ROOT / "BrickMore_Comparision" / "BrickMoreComparison_20261116"
               / "BrickMoreComparison_20261116")
NEW_PACKAGE = ROOT / "tmp" / "comparison_20261117_intake" / "BrickMore_A260_20261117"
OLD_RUN = OLD_PACKAGE / "Results" / "comparison_full"
NEW_RUN = NEW_PACKAGE / "Results" / "brickmore_A260"
FINAL = ROOT / "output" / "figures" / "comparison_20261116"
OUT = ROOT / "tmp" / "comparison_20261117_intake" / "report"
OUT.mkdir(parents=True, exist_ok=True)
SYSTEMS = ("BrickMore", "BrickGPT", "BrickNet")
COLORS = dict(zip(SYSTEMS, ("#096b74", "#a85b08", "#6352aa")))
STYLES = dict(zip(SYSTEMS, ("-", "--", "-.")))
MARKERS = dict(zip(SYSTEMS, ("o", "s", "^")))
METRICS = (
    ("pinv", "P_inv 无效放置比例", "P_inv", "越低越好"),
    ("vqa", "VQAScore", "VQAScore", "越高越好"),
    ("pe", "PE", "PE", "越高越好"),
    ("siglip2", "SigLIP2", "SigLIP2", "越高越好"),
)

font = r"C:\Windows\Fonts\msyh.ttc"
font_manager.fontManager.addfont(font)
plt.rcParams.update({
    "font.family": font_manager.FontProperties(fname=font).get_name(),
    "font.size": 11, "axes.titlesize": 13, "axes.labelsize": 10,
    "text.color": "#172b34", "axes.labelcolor": "#314952",
    "xtick.color": "#38525d", "ytick.color": "#38525d",
    "axes.edgecolor": "#cad6db", "axes.spines.top": False,
    "axes.spines.right": False, "axes.unicode_minus": False,
    "figure.facecolor": "white", "savefig.facecolor": "white",
})

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def confirm_same_settings(name, ignored):
    def settings(run):
        return {key: value for key, value in read_json(run / name).items() if key not in ignored}
    assert settings(OLD_RUN) == settings(NEW_RUN), name


supplement_audit = read_json(NEW_PACKAGE / "Data/input_audit.json")
assert supplement_audit["passed"]
assert supplement_audit["reference_manifest_sha256"] == digest(OLD_PACKAGE / "Data/manifest.jsonl")
for relative in ("Data/scoring_models.json", "Scripts/structure.py", "Scripts/render.py",
                 "Scripts/evaluate_paper_images.py", "Scripts/paper_common.py",
                 "Scripts/prepare_paper_inputs.py"):
    assert digest(OLD_PACKAGE / relative) == digest(NEW_PACKAGE / relative), relative
confirm_same_settings("rendered/render_protocol.json", {"input_sha256", "catalog_sha256"})
confirm_same_settings("structure.config.json", {"input_sha256", "catalog_sha256", "signature"})
for metric in ("vqa", "pe", "siglip2"):
    confirm_same_settings(f"{metric}.config.json",
                          {"samples", "view_evaluations", "input_manifest_sha256", "signature"})
    confirm_same_settings(f"{metric}.model.json", set())
old_parts = read_json(OLD_PACKAGE / "Assets/catalog.json")
new_parts = read_json(NEW_PACKAGE / "Assets/catalog.json")
assert old_parts["bricknet_version"] == new_parts["bricknet_version"]
for part, meta in new_parts["parts"].items():
    for directory, ext, key in (("inset", "ply", "collider_sha256"),
                                ("render_meshes", "npz", "render_sha256")):
        assert digest(NEW_PACKAGE / "Assets" / directory / f"{part}.{ext}") == meta[key]
        assert old_parts["parts"][part][key] == meta[key], (part, key)


def load_scores(run, expected):
    with (run / "report/scores.csv").open(encoding="utf-8-sig", newline="") as stream:
        records = list(csv.DictReader(stream))
    summary = read_json(run / "report/summary.json")
    assert summary["samples"] == len(records) == expected
    indexed = {r["sample_id"]: r for r in records}
    assert len(indexed) == expected
    manifest = {r["sample_id"]: r for r in read_jsonl(run / "selected_manifest.jsonl")}
    assert indexed.keys() == manifest.keys()
    for row in records:
        source = manifest[row["sample_id"]]
        for field in ("system", "prompt_id", "batch", "category", "level", "caption", "part_count"):
            assert str(source[field]) == row[field], (row["sample_id"], field)
        assert row["structure_status"] == "ok"
        row["part_count"] = int(row["part_count"])
        row["invalid_placements"] = int(row["invalid_placements"])
        for key, _, _, _ in METRICS:
            row[key] = float(row[key])
            assert math.isfinite(row[key])
        assert math.isclose(row["pinv"], row["invalid_placements"] / row["part_count"])
    for batch, stats in summary["by_batch"].items():
        for system, system_stats in stats["systems"].items():
            cohort = [r for r in records if (r["batch"], r["system"]) == (batch, system)]
            for metric, *_ in METRICS:
                expected_metric = system_stats[metric]
                assert expected_metric["missing"] == 0 and expected_metric["n"] == len(cohort)
                assert math.isclose(np.mean([r[metric] for r in cohort]), expected_metric["mean"], abs_tol=1e-13)
    plan = read_json(run / "progress.json")
    for stage, count in (("structure", expected), ("render", expected * 8), ("vqa", expected),
                         ("pe", expected), ("siglip2", expected)):
        step = plan["stages"][stage]
        assert step["status"] == "completed" and step["done"] == step["total"] == count
    return records


original = load_scores(OLD_RUN, 1315)
added = load_scores(NEW_RUN, 260)
assert all((r["system"], r["batch"]) == ("BrickMore", "A") for r in added)
for key, journal, value_key in (("pinv", "structure", "pinv"), ("vqa", "vqa", "max_score"),
                                 ("pe", "pe", "max_score"), ("siglip2", "siglip2", "max_score")):
    records = read_jsonl(NEW_RUN / f"{journal}.jsonl")
    journal_rows = {r["sample_id"]: r for r in records}
    assert len(journal_rows) == len(records) == len(added)
    for score in added:
        row = journal_rows[score["sample_id"]]
        assert row["status"] == "ok" and row[value_key] == score[key]
        if key != "pinv":
            assert len(row["scores"]) == 8 and row[value_key] == max(row["scores"])

rows = original + added
assert len({r["sample_id"] for r in rows}) == len(rows) == 1575
groups = {system: [r for r in rows if r["system"] == system] for system in SYSTEMS}
assert all(len(group) == 525 for group in groups.values())
by_prompt = {system: {r["prompt_id"]: r for r in group} for system, group in groups.items()}
prompt_ids = sorted(by_prompt["BrickMore"])
assert all(len(items) == 525 and sorted(items) == prompt_ids for items in by_prompt.values())
for prompt in prompt_ids:
    for field in ("caption", "category", "level"):
        assert len({by_prompt[s][prompt][field] for s in SYSTEMS}) == 1, (prompt, field)

columns = ("prompt_id", "system", "category", "level", "caption", "sample_id",
           "part_count", "invalid_placements", "pinv", "vqa", "pe", "siglip2")
with (OUT / "scores_525_matched.csv").open("w", encoding="utf-8-sig", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(by_prompt[s][prompt] for prompt in prompt_ids for s in SYSTEMS)


def values(s, key):
    return np.array([r[key] for r in groups[s]])


def display(value, key):
    return f"{100 * value:.2f}%" if key == "pinv" else f"{value:.4f}"


def format_axis(axis, key):
    if key == "pinv":
        axis.set_major_formatter(ticker.PercentFormatter(1, decimals=None))


def grid(ax, axis="y"):
    ax.set_axisbelow(True)
    ax.grid(axis=axis, color="#e4ecef", linewidth=0.8)


def save(fig, filename):
    fig.savefig(OUT / filename, dpi=155)
    plt.close(fig)


def metric_title(ax, label, direction):
    ax.set_title(f"{label}  ·  {direction}", loc="left", fontweight="bold", pad=10)


def system_legend(fig, handles):
    fig.legend(handles, SYSTEMS, loc="upper center", ncol=3,
               bbox_to_anchor=(.5, .985), frameon=False, handlelength=2.7)


fig, axes = plt.subplots(1, 3, figsize=(10.8, 3.25))
fig.subplots_adjust(left=.04, right=.96, top=.84, bottom=.21, wspace=.18)
for ax, system in zip(axes, SYSTEMS):
    x = values(system, "pinv")
    zero = int(np.count_nonzero(x == 0))
    ax.pie([zero, len(x) - zero], startangle=90, counterclock=False,
           colors=[COLORS[system], "#e3eaed"],
           wedgeprops={"width": .29, "edgecolor": "white", "linewidth": 1.6})
    ax.text(0, .12, f"{zero/len(x):.1%}", ha="center", va="center", fontsize=20, fontweight="bold")
    ax.text(0, -.22, f"{zero} / {len(x)} 条", ha="center", va="center", fontsize=10)
    ax.set_title(system, pad=9, fontweight="bold")
fig.text(.5, .065, "着色部分为 P_inv = 0 的记录，浅灰部分为 P_inv > 0 的记录。",
         ha="center", va="center", fontsize=10, color="#415961")
save(fig, "01-zero-invalid.png")

y = np.arange(3)
fig, axes = plt.subplots(2, 2, figsize=(10.8, 6.5))
fig.subplots_adjust(left=.14, right=.94, top=.92, bottom=.09, hspace=.65, wspace=.50)
for ax, (key, label, _, direction) in zip(axes.flat, METRICS):
    avgs = [values(s, key).mean() for s in SYSTEMS]
    bars = ax.barh(y, avgs, color=[COLORS[s] for s in SYSTEMS], height=.50)
    upper = max(avgs) * 1.28
    metric_title(ax, label, direction)
    ax.set(yticks=y, yticklabels=SYSTEMS, xlim=(0, upper))
    ax.invert_yaxis()
    ax.tick_params(axis="y", length=0, labelsize=10)
    ax.spines["left"].set_visible(False)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(5))
    grid(ax, "x")
    format_axis(ax.xaxis, key)
    for bar, number in zip(bars, avgs):
        ax.text(number + upper*.016, bar.get_y()+bar.get_height()/2, display(number, key),
                va="center", fontsize=10)
save(fig, "02-means.png")

fig, axes = plt.subplots(2, 2, figsize=(10.8, 6.65))
fig.subplots_adjust(left=.105, right=.96, top=.89, bottom=.10, wspace=.32, hspace=.58)
for i, (ax, (key, label, short, direction)) in enumerate(zip(axes.flat, METRICS)):
    all_values = np.concatenate([values(s, key) for s in SYSTEMS])
    low, high = min(0, all_values.min()), all_values.max() * 1.03
    handles = []
    for s in SYSTEMS:
        x, counts = np.unique(values(s, key), return_counts=True)
        xx = np.r_[low, x, high]
        yy = np.r_[0, np.cumsum(counts)/counts.sum(), 1]
        handles.append(ax.step(xx, yy, where="post", color=COLORS[s], linestyle=STYLES[s],
                               linewidth=2.1)[0])
    if i == 0:
        system_legend(fig, handles)
    metric_title(ax, label, direction)
    ax.set(xlim=(low, high), ylim=(0, 1.035), xlabel=f"{short} 阈值", ylabel="累计样本比例")
    ax.xaxis.set_major_locator(ticker.MaxNLocator(5))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(.25))
    ax.yaxis.set_major_formatter(ticker.PercentFormatter(1, decimals=0))
    format_axis(ax.xaxis, key)
    grid(ax)
save(fig, "03-distributions.png")

fig, axes = plt.subplots(2, 2, figsize=(10.8, 6.5))
fig.subplots_adjust(left=.105, right=.96, top=.89, bottom=.10, hspace=.58, wspace=.32)
for i, (ax, (key, label, _, direction)) in enumerate(zip(axes.flat, METRICS)):
    handles = []
    for s in SYSTEMS:
        per_level = [[r[key] for r in groups[s] if int(r["level"]) == lvl]
                     for lvl in range(1, 6)]
        assert all(len(level) == 105 for level in per_level)
        handles.append(ax.plot(range(1, 6), [np.mean(v) for v in per_level], linewidth=2,
                               color=COLORS[s], marker=MARKERS[s], linestyle=STYLES[s])[0])
    if i == 0:
        system_legend(fig, handles)
    metric_title(ax, label, direction)
    ax.set(xticks=range(1, 6), xticklabels=[f"L{i}" for i in range(1, 6)],
           xlim=(.85, 5.15), ylim=(-.02 * ax.get_ylim()[1], ax.get_ylim()[1]*1.04), ylabel="模型均值")
    ax.yaxis.set_major_locator(ticker.MaxNLocator(5))
    format_axis(ax.yaxis, key)
    grid(ax)
save(fig, "04-by-level.png")


def row_html(values, heading=False):
    tag = "th" if heading else "td"
    scope = ' scope="col"' if heading else ""
    return "<tr>" + "".join(f"<{tag}{scope}>{html.escape(str(x))}</{tag}>" for x in values) + "</tr>"


def table(headers, rows):
    return ('<div class="scroll"><table><thead>' + row_html(headers, True)
            + "</thead><tbody>" + "".join(row_html(r) for r in rows) + "</tbody></table></div>")


def stats_table():
    data = []
    for key, _, short, _ in METRICS:
        for s in SYSTEMS:
            x = values(s, key)
            q1, med, q3, p90 = np.quantile(x, [.25, .5, .75, .9])
            calc = [np.mean(x), med, np.std(x, ddof=1), np.min(x), q1, q3, p90, np.max(x)]
            data.append((short, s, len(x), *(display(v, key) for v in calc)))
    return table(("指标", "模型", "样本数", "均值", "中位数", "样本标准差", "最小值",
                  "第 25 百分位", "第 75 百分位", "第 90 百分位", "最大值"), data)


pair_rows = []
for key, _, short, _ in METRICS:
    for comparator in SYSTEMS[1:]:
        a = np.array([by_prompt["BrickMore"][p][key] for p in prompt_ids])
        b = np.array([by_prompt[comparator][p][key] for p in prompt_ids])
        ties = np.isclose(a, b, rtol=0, atol=1e-12)
        win = a < b if key == "pinv" else a > b
        w, t = int((win & ~ties).sum()), int(ties.sum())
        pair_rows.append((short, comparator, w, t, len(a)-w-t,
                          f"{100*(a-b).mean():+.2f} 个百分点" if key == "pinv" else f"{(a-b).mean():+.4f}"))

pinv_rows = []
for s in SYSTEMS:
    x = values(s, "pinv")
    nzero = int(np.count_nonzero(x == 0))
    weighted = sum(r["invalid_placements"] for r in groups[s]) / sum(r["part_count"] for r in groups[s])
    pinv_rows.append((s, f"{nzero}/{len(x)}（{nzero/len(x):.1%}）",
                      display(x.mean(), "pinv"), display(weighted, "pinv")))

origin = html.escape(os.path.relpath(OLD_RUN / "report/report.html", FINAL).replace(os.sep, "/"), quote=True)
leaders = {key: (min if key == "pinv" else max)(SYSTEMS, key=lambda s: values(s, key).mean())
           for key, *_ in METRICS}
metric_names = {key: short for key, _, short, _ in METRICS}
leader_note = "。".join(
    f"{s} 的 {'、'.join(metric_names[key] for key in ('vqa', 'pe', 'siglip2') if leaders[key] == s)} 均值最高"
    for s in SYSTEMS if any(leaders[key] == s for key in ("vqa", "pe", "siglip2"))
) + f"。{leaders['pinv']} 的无效放置比例均值最低。"
flags = supplement_audit["source_flags"]
assert len({r["category"] for r in groups["BrickMore"]}) == 21
page = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>积木模型全量对比 · 525 条共同提示词</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f5f8f9;color:#172b34;font:16px/1.65 "Microsoft YaHei","Noto Sans CJK SC",sans-serif}
header{background:#e6f0f1;border-bottom:1px solid #cddfe2;padding:42px 20px 30px}header>div,main{max-width:1120px;margin:auto}
h1,h2,h3{line-height:1.3;margin:0 0 10px}h1{font-size:clamp(26px,4.4vw,39px)}h2{font-size:23px}h3{font-size:17px}
p{margin:6px 0 12px}header p{color:#35515c}nav{display:flex;gap:18px;flex-wrap:wrap;padding-top:7px}
a{color:#075d69;text-underline-offset:3px}main{padding:12px 20px 44px}
section{scroll-margin-top:12px;padding:24px 0;border-bottom:1px solid #d8e2e6}
figure{margin:12px 0 0}img{width:100%;height:auto;display:block;border:1px solid #dce7ea;border-radius:10px;background:white}
figcaption,.note{color:#415961;font-size:14px}
.scroll{overflow-x:auto;background:#fff;border:1px solid #dce7ea;border-radius:8px;margin-top:10px}
table{border-collapse:collapse;width:100%;min-width:520px;font-size:14px;font-variant-numeric:tabular-nums}
th,td{padding:8px 11px;white-space:nowrap;border-bottom:1px solid #e3ebee;text-align:right}
th{background:#edf4f5;font-weight:650}th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){text-align:left}
tr:last-child td{border-bottom:0}details{margin:14px 0}summary{cursor:pointer;font-weight:650;color:#164c55}
.sub{margin-top:20px}.source{font-size:14px}
@media print{body,header{background:#fff}nav{display:none}figure,.scroll{break-inside:avoid}}
</style></head><body>
<header><div><h1>积木模型全量对比</h1><p>2026 年 11 月 17 日更新 · 525 条共同提示词 · 21 类 · 1,575 条模型记录 · 四项指标均无缺失</p>
<nav aria-label="图表目录"><a href="#means">总体均值</a><a href="#zero">零无效放置占比</a><a href="#dist">分布</a><a href="#levels">难度变化</a><a href="#stats">统计量</a><a href="scores_525_matched.csv">逐条分数 CSV</a></nav></div></header>
<main>
<section id="means"><h2>四项指标总体均值</h2><p>__LEADERS__ 三种模型各用相同的 525 条提示词，每条等权。</p>
<figure><img src="02-means.png" alt="三个模型在 525 条共同提示词上的四项指标平均值。"></figure></section>
<section id="zero"><h2>无效放置比例为零的样本占比</h2><p>圆环中央显示各模型无效放置次数为零的样本数及占比。</p>
<figure><img src="01-zero-invalid.png" alt="三个环形图分别显示三种模型的 P_inv 为零的样本数和比例。"></figure></section>
<section id="dist"><h2>逐样本累计分布</h2><p>横轴是分数或比例阈值，纵轴是低于或等于该值的样本占比。P_inv 曲线越靠左，低无效放置比例的样本越多。图文指标曲线越靠右，高分样本越多。</p>
<figure><img src="03-distributions.png" alt="四项指标的经验累积分布曲线，可比较三种模型的集中区间和尾部。"></figure></section>
<section id="levels"><h2>L1 至 L5 的均值变化</h2><p>每级有 105 条共同提示词，每个点是对应等级内的模型均值。</p>
<figure><img src="04-by-level.png" alt="按提示词等级 L1 到 L5 展示三种模型各指标的均值曲线。"></figure>
<p class="note">三个模型的 VQAScore 均值从 L3 到 L4 均有下降，同期 PE 均值均有上升。不同指标反映的变化方向不一定相同。</p></section>
<section id="stats"><h2>描述统计与逐题配对</h2>
<h3 class="sub">四项指标描述统计</h3>__STATS__
<p class="note">标准差描述不同提示词之间的分数波动。每项百分位按样本排序后线性插值。</p>
<h3 class="sub">无效放置的零值与加权统计</h3>__PINV__
<p class="note">模型均值给每条模型记录相同权重。按放置次数加权时，计算全部无效放置次数除以全部放置次数。</p>
<h3 class="sub">BrickMore 逐题胜平负</h3>__PAIRED__
<p class="note">每行比较相同的 525 条提示词。胜负按指标方向判定，差值列为 BrickMore 减对手。两边相差不超过 10⁻¹² 记为平局。</p></section>
<section><h2>评分口径</h2><p>P_inv 按 LDraw 文件行顺序统计碰撞判为无效的放置。连通性和承重需独立验证。VQAScore、PE、SigLIP2 均从每个模型的八张固定视角渲染图中取最高分，再对提示词汇总。渲染统一使用黄色，图文评分以形状和语义匹配为主。</p>
<p>补测的 260 条 BrickMore 结果全部纳入，包括源清单标记几何未通过的 __GEOM__ 条与生成未结束的 __INCOMPLETE__ 条，两种标记可能重叠。汇总反映现有交付结果，生成设置随原始运行而异。</p>
<p class="source">数据来自 11 月 16 日已有的 1,315 条评分和 11 月 17 日新增的 260 条评分（BrickMore_A260_20261117.rar）。<a href="__ORIGIN__">查看 11 月 16 日原始报告</a></p></section>
</main></body></html>
"""
replacements = {
    "__STATS__": stats_table(),
    "__LEADERS__": html.escape(leader_note),
    "__GEOM__": str(flags["geometry_valid"]["false"]),
    "__INCOMPLETE__": str(flags["generation_complete"]["false"]),
    "__PINV__": table(("模型", "P_inv 为零", "模型均值", "按放置次数加权"), pinv_rows),
    "__PAIRED__": table(("指标", "对手", "胜", "平", "负", "均值差"), pair_rows),
    "__ORIGIN__": origin,
}
for token, value in replacements.items():
    page = page.replace(token, value)
class ReportLinks(HTMLParser):
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "img":
            assert (OUT / attrs["src"]).is_file() and attrs["alt"]
        if tag == "a":
            target = attrs["href"]
            if target.startswith("#"):
                assert page.count(f'id="{target[1:]}"') == 1
            else:
                site = FINAL if target.startswith("..") else OUT
                assert (site / target).resolve().is_file()


assert not any(token in page for token in replacements)
ReportLinks().feed(page)
(OUT / "index.html").write_text(page, encoding="utf-8")
print("MEANS:", {s: {key: float(values(s, key).mean()) for key, *_ in METRICS} for s in SYSTEMS})
print("PINV:", pinv_rows)
print("PAIRED:", pair_rows)
print("OUT:", OUT)
