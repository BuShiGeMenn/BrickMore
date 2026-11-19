import csv
import html
import json
import math
import os
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import ticker
import numpy as np


ROOT = Path(r"D:\BrickMore")
SOURCE = (ROOT / "BrickMore_Comparision" / "BrickMoreComparison_20261116"
          / "BrickMoreComparison_20261116" / "Results" / "comparison_full" / "report")
OUT = ROOT / "output" / "figures" / "comparison_20261116"
OUT.mkdir(parents=True, exist_ok=True)
SYSTEMS = ("BrickMore", "BrickGPT", "BrickNet")
COLORS = dict(zip(SYSTEMS, ("#096b74", "#a85b08", "#6352aa")))
STYLES = dict(zip(SYSTEMS, ("-", "--", "-.")))
MARKERS = dict(zip(SYSTEMS, ("o", "s", "^")))
METRICS = (
    ("pinv", "Invalid placement rate", r"$P_{\mathrm{inv}}$", "Lower is better"),
    ("vqa", "VQAScore", "VQAScore", "Higher is better"),
    ("pe", "PE", "PE", "Higher is better"),
    ("siglip2", "SigLIP2", "SigLIP2", "Higher is better"),
)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11, "axes.titlesize": 13, "axes.labelsize": 10,
    "text.color": "#172b34", "axes.labelcolor": "#314952",
    "xtick.color": "#38525d", "ytick.color": "#38525d",
    "axes.edgecolor": "#cad6db", "axes.spines.top": False,
    "axes.spines.right": False, "axes.unicode_minus": False,
    "figure.facecolor": "white", "savefig.facecolor": "white",
})

with (SOURCE / "scores.csv").open(encoding="utf-8-sig", newline="") as stream:
    rows = list(csv.DictReader(stream))
summary = json.loads((SOURCE / "summary.json").read_text(encoding="utf-8"))
assert len(rows) == summary["samples"] == 1315
assert len({r["sample_id"] for r in rows}) == len(rows)
present = {"A": SYSTEMS[1:], "B": SYSTEMS}
groups = {(b, s): [r for r in rows if r["batch"] == b and r["system"] == s]
          for b, systems in present.items() for s in systems}
assert sum(map(len, groups.values())) == len(rows)
by_prompt = {}
for (b, s), group in groups.items():
    assert len(group) == (260 if b == "A" else 265)
    by_prompt[b, s] = {r["prompt_id"]: r for r in group}
    assert len(by_prompt[b, s]) == len(group)
    assert all(r["structure_status"] == "ok" for r in group)
    for key, _, _, _ in METRICS:
        for row in group:
            row[key] = float(row[key])
        measured = [r[key] for r in group]
        assert all(math.isfinite(x) for x in measured)
        official = summary["by_batch"][b]["systems"][s][key]
        assert official["n"] == len(group) and official["missing"] == 0
        assert math.isclose(float(np.mean(measured)), official["mean"], abs_tol=1e-13)
    micro = sum(int(r["invalid_placements"]) for r in group)/sum(int(r["part_count"]) for r in group)
    assert math.isclose(micro, summary["by_batch"][b]["systems"][s]["pinv_micro"], abs_tol=1e-13)
    assert all(math.isclose(r["pinv"], int(r["invalid_placements"])/int(r["part_count"]))
               for r in group)
for b, systems in present.items():
    prompt_sets = [set(by_prompt[b, s]) for s in systems]
    assert all(p == prompt_sets[0] for p in prompt_sets)
    assert all(len({by_prompt[b, s][p]["caption"] for s in systems}) == 1 for p in prompt_sets[0])


def values(b, s, key):
    return np.array([r[key] for r in groups[b, s]])


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


fig, (ax, counts_ax) = plt.subplots(1, 2, figsize=(10.8, 3.55),
                                    gridspec_kw={"width_ratios": [1, 1.55]})
fig.subplots_adjust(left=.05, right=.92, top=.86, bottom=.20, wspace=.38)
prompt_counts = [len(by_prompt[b, present[b][0]]) for b in ("A", "B")]
cohort_colors = ("#d9a259", "#257882")
ax.pie(prompt_counts, startangle=90, counterclock=False, colors=cohort_colors,
       wedgeprops={"width": .32, "edgecolor": "white", "linewidth": 2})
ax.text(0, .12, f"{sum(prompt_counts)}", ha="center", va="center", fontsize=23, fontweight="bold")
ax.text(0, -.22, "prompts", ha="center", va="center", fontsize=10)
ax.set_title("Prompts by evaluation group", pad=10, fontweight="bold")
ax.legend([f"Group {b}: {n} prompts · {n/sum(prompt_counts):.1%}" for b, n in zip(("A", "B"), prompt_counts)],
          loc="upper center", bbox_to_anchor=(.5, -.02), frameon=False, fontsize=9)
counts_ax.set_title("Evaluated outputs per model", loc="left", fontweight="bold", pad=12)
y = np.arange(3)
left = np.zeros(3)
for b, color in zip(("A", "B"), cohort_colors):
    count = np.array([len(groups.get((b, s), ())) for s in SYSTEMS])
    bars = counts_ax.barh(y, count, left=left, color=color, height=.48, label=f"Group {b}")
    for bar, number in zip(bars, count):
        if number:
            counts_ax.text(bar.get_x()+bar.get_width()/2, bar.get_y()+bar.get_height()/2, str(number),
                           ha="center", va="center", color="#172b34" if b == "A" else "white", fontweight="bold")
    left += count
for i, total in enumerate(left):
    counts_ax.text(total + 13, i, str(int(total)), va="center", fontweight="bold")
counts_ax.set(yticks=y, yticklabels=SYSTEMS, xlim=(0, 585), xlabel="Number of outputs")
counts_ax.invert_yaxis()
counts_ax.spines["left"].set_visible(False)
counts_ax.tick_params(axis="y", length=0)
grid(counts_ax, "x")
save(fig, "01-cohorts.png")

fig, axes = plt.subplots(2, 2, figsize=(10.8, 6.5))
fig.subplots_adjust(left=.14, right=.94, top=.92, bottom=.09, hspace=.65, wspace=.50)
for ax, (key, label, _, direction) in zip(axes.flat, METRICS):
    avgs = [values("B", s, key).mean() for s in SYSTEMS]
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
    max_value = max(values("B", s, key).max() for s in SYSTEMS)
    handles = []
    for s in SYSTEMS:
        x, counts = np.unique(values("B", s, key), return_counts=True)
        xx = np.r_[0, x, max_value * 1.03]
        yy = np.r_[0, np.cumsum(counts)/counts.sum(), 1]
        handles.append(ax.step(xx, yy, where="post", color=COLORS[s], linestyle=STYLES[s],
                               linewidth=2.1)[0])
    if i == 0:
        system_legend(fig, handles)
    metric_title(ax, label, direction)
    ax.set(xlim=(0, max_value*1.03), ylim=(0, 1.035), xlabel=f"{short} threshold", ylabel="Cumulative share of outputs")
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
        per_level = [[r[key] for r in groups["B", s] if int(r["level"]) == lvl]
                     for lvl in range(1, 6)]
        assert all(len(level) == 53 for level in per_level)
        handles.append(ax.plot(range(1, 6), [np.mean(v) for v in per_level], linewidth=2,
                               color=COLORS[s], marker=MARKERS[s], linestyle=STYLES[s])[0])
    if i == 0:
        system_legend(fig, handles)
    metric_title(ax, label, direction)
    ax.set(xticks=range(1, 6), xticklabels=[f"L{i}" for i in range(1, 6)],
           xlim=(.85, 5.15), ylim=(0, ax.get_ylim()[1]*1.04), ylabel="Mean across prompts")
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


def stats_table(batch):
    data = []
    for key, _, short, _ in METRICS:
        for s in present[batch]:
            x = values(batch, s, key)
            q1, med, q3, p90 = np.quantile(x, [.25, .5, .75, .9])
            calc = [np.mean(x), med, np.std(x, ddof=1), np.min(x), q1, q3, p90, np.max(x)]
            data.append((short, s, len(x), *(display(v, key) for v in calc)))
    return table(("指标", "模型", "样本数", "均值", "中位数", "样本标准差", "最小值",
                  "第 25 百分位", "第 75 百分位", "第 90 百分位", "最大值"), data)


pair_rows = []
for key, _, short, _ in METRICS:
    for comparator in SYSTEMS[1:]:
        aligned = sorted(by_prompt["B", "BrickMore"])
        a = np.array([by_prompt["B", "BrickMore"][p][key] for p in aligned])
        b = np.array([by_prompt["B", comparator][p][key] for p in aligned])
        ties = np.isclose(a, b, rtol=0, atol=1e-12)
        win = a < b if key == "pinv" else a > b
        w, t = int((win & ~ties).sum()), int(ties.sum())
        pair_rows.append((short, comparator, w, t, len(a)-w-t,
                          f"{100*(a-b).mean():+.2f} 个百分点" if key == "pinv" else f"{(a-b).mean():+.4f}"))

pinv_rows = []
for s in SYSTEMS:
    x = values("B", s, "pinv")
    nzero = int(np.count_nonzero(x == 0))
    pinv_rows.append((s, f"{nzero}/{len(x)}（{nzero/len(x):.1%}）",
                      display(x.mean(), "pinv"),
                      display(summary["by_batch"]["B"]["systems"][s]["pinv_micro"], "pinv")))

origin = html.escape(os.path.relpath(SOURCE / "report.html", OUT).replace(os.sep, "/"), quote=True)
page = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>积木模型对比评测图表</title>
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
<header><div><h1>积木模型对比评测图表</h1><p>2026 年 11 月 16 日全量评测 · 525 条提示词 · 1,315 条模型记录 · 四项指标均无缺失</p>
<nav aria-label="图表目录"><a href="#cohorts">样本构成</a><a href="#means">总体均值</a><a href="#dist">分布</a><a href="#levels">难度变化</a><a href="#stats">统计量</a></nav></div></header>
<main>
<section id="cohorts"><h2>样本构成</h2><p>B 组的 265 条提示词由三个模型共同评测。A 组有 260 条提示词，由 BrickGPT 和 BrickNet 共同评测。</p>
<figure><img src="01-cohorts.png" alt="环形图显示 A 组 260 条和 B 组 265 条提示词。堆叠柱状图显示 BrickMore 有 265 条、BrickGPT 和 BrickNet 各有 525 条模型记录。"></figure></section>
<section id="means"><h2>B 组四项指标总体均值</h2><p>BrickMore 的三项图文匹配均分最高。BrickGPT 的无效放置比例最低。</p>
<figure><img src="02-means.png" alt="四组水平柱状图显示 BrickMore 的 VQAScore、PE 和 SigLIP2 均值最高，BrickGPT 的 P_inv 最低。"></figure></section>
<section id="dist"><h2>B 组逐样本分布</h2><p>横轴是分数或比例阈值，纵轴是低于或等于该值的样本占比。P_inv 曲线越靠左，表示低无效放置比例的样本越多。图文指标的曲线越靠右，表示高分样本越多。</p>
<figure><img src="03-distributions.png" alt="四项指标的经验累积分布曲线，可比较三种模型的集中区间和尾部。"></figure></section>
<section id="levels"><h2>B 组 L1 至 L5 的均值变化</h2><p>每级有 53 条共同提示词，每个点是对应等级内的模型均值。</p>
<figure><img src="04-by-level.png" alt="按提示词等级 L1 到 L5 展示三种模型各指标的均值曲线。"></figure></section>
<section id="stats"><h2>描述统计与逐题配对</h2>
<h3 class="sub">B 组描述统计</h3>__STATS_B__
<p class="note">标准差描述不同提示词之间的分数波动。每项百分位按样本排序后线性插值。</p>
<h3 class="sub">B 组无效放置的零值与加权统计</h3>__PINV__
<p class="note">模型均值给每条模型记录相同权重。按放置次数加权时，计算全部无效放置次数除以全部放置次数。</p>
<h3 class="sub">B 组 BrickMore 逐题胜平负</h3>__PAIRED__
<p class="note">每行比较相同的 265 条提示词。胜负按指标方向判定，差值列为 BrickMore 减对手。两边相差不超过 10⁻¹² 记为平局。</p>
<details><summary>查看 A 组描述统计（两方对照）</summary>__STATS_A__</details></section>
<section><h2>评分口径</h2><p>P_inv 按 LDraw 文件行顺序统计碰撞判为无效的放置。连通性和承重需独立验证。VQAScore、PE、SigLIP2 均从每个模型的八张固定视角渲染图中取最高分，再对提示词汇总。渲染统一使用黄色，图文评分以形状和语义匹配为主。</p>
<p class="source">数据取自全量报告的 scores.csv，分数均值与 summary.json 对照一致。<a href="__ORIGIN__">查看原始全量报告</a></p></section>
</main></body></html>
"""
replacements = {
    "__STATS_B__": stats_table("B"),
    "__STATS_A__": stats_table("A"),
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
                assert (OUT / target).resolve().is_file()


assert not any(token in page for token in replacements)
ReportLinks().feed(page)
(OUT / "index.html").write_text(page, encoding="utf-8")
print("B-group score ranges:", {key: (min(values("B", s, key).min() for s in SYSTEMS),
                                      max(values("B", s, key).max() for s in SYSTEMS))
                                for key, *_ in METRICS})
print("PINV:", pinv_rows)
print("PAIRED:", pair_rows)
print("OUT:", OUT)
