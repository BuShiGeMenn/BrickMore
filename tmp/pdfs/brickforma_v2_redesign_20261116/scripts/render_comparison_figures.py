"""Render the four November 16 comparison charts for the manuscript."""

import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import ticker


PROJECT = Path(__file__).resolve().parents[1]
SNAPSHOT = PROJECT / "stats" / "20261116"
FIGURES = PROJECT / "figures" / "comparison_20261116"
SYSTEMS = ("BrickMore", "BrickGPT", "BrickNet")
LABELS = ("BrickForma", "BrickGPT", "BrickNet")
COLORS = ("#096b74", "#a85b08", "#6352aa")
COHORT_COLORS = ("#d9a259", "#257882")
STYLES = ("-", "--", "-.")
MARKERS = ("o", "s", "^")
LEVELS = range(1, 6)
METRICS = (
    ("pinv", "Invalid placement ratio", r"$P_{\mathrm{inv}}$", "lower"),
    ("vqa", "VQAScore", "VQAScore", "higher"),
    ("pe", "PE", "PE", "higher"),
    ("siglip2", "SigLIP2", "SigLIP2", "higher"),
)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9.5,
    "axes.titlesize": 10,
    "axes.labelsize": 9.5,
    "axes.titleweight": "bold",
    "text.color": "#172b34",
    "axes.labelcolor": "#314952",
    "xtick.color": "#38525d",
    "ytick.color": "#38525d",
    "axes.edgecolor": "#cad6db",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "pdf.fonttype": 42,
})


def load_scores():
    scores = SNAPSHOT / "scores.csv"
    summary = json.loads((SNAPSHOT / "paper_summary.json").read_text(encoding="utf-8"))
    if hashlib.sha256(scores.read_bytes()).hexdigest().lower() != summary["source_scores_sha256"].lower():
        raise ValueError("The score snapshot does not match the manuscript summary.")
    cohorts = {"A": SYSTEMS[1:], "B": SYSTEMS}
    groups = {(cohort, system): {} for cohort, systems in cohorts.items() for system in systems}
    with scores.open(encoding="utf-8-sig", newline="") as source:
        for record in csv.DictReader(source):
            group = groups[record["batch"], record["system"]]
            prompt = record["prompt_id"]
            if prompt in group:
                raise ValueError(f"Repeated prompt for {record['system']}: {prompt}")
            for key, *_ in METRICS:
                record[key] = float(record[key])
                if not math.isfinite(record[key]):
                    raise ValueError(f"Non-finite {key} score for {prompt}")
            group[prompt] = record
    for cohort, systems in cohorts.items():
        reference = groups[cohort, systems[0]]
        level_count = 52 if cohort == "A" else 53
        for system in systems:
            group = groups[cohort, system]
            levels = Counter(int(record["level"]) for record in group.values())
            if levels != {level: level_count for level in LEVELS} or group.keys() != reference.keys():
                raise ValueError(f"Unmatched prompts or unexpected level counts in Group {cohort}")
            if any(record["caption"] != reference[prompt]["caption"] for prompt, record in group.items()):
                raise ValueError(f"Different captions for matching prompts in Group {cohort}")
    return groups


def scores_for(group, key):
    return np.array([record[key] for record in group.values()])


def format_percent(axis, key):
    if key == "pinv":
        axis.set_major_formatter(ticker.PercentFormatter(1))


def grid(ax, axis="y"):
    ax.set_axisbelow(True)
    ax.grid(axis=axis, color="#e4ecef", linewidth=0.8)


def title(ax, label, direction):
    ax.set_title(f"{label} ({direction} is better)", loc="left", pad=5)


def legend(fig, handles):
    fig.legend(handles, LABELS, loc="upper center", ncol=3, frameon=False, handlelength=2.5)


def save(fig, name):
    fig.savefig(FIGURES / name)
    plt.close(fig)


def draw_cohorts(groups):
    fig, (donut, counts) = plt.subplots(1, 2, figsize=(7, 2.35),
                                       gridspec_kw={"width_ratios": [1, 1.48]})
    fig.subplots_adjust(left=.05, right=.98, top=.84, bottom=.23, wspace=.65)
    cohorts = ("A", "B")
    prompts = [len(groups[cohort, "BrickGPT"]) for cohort in cohorts]
    total = sum(prompts)
    wedges, _ = donut.pie(prompts, startangle=90, counterclock=False, colors=COHORT_COLORS,
                          wedgeprops={"width": .28, "edgecolor": "white", "linewidth": 1.2})
    donut.text(0, .13, str(total), ha="center", va="center", fontsize=15, fontweight="bold")
    donut.text(0, -.22, "prompts", ha="center", va="center")
    donut.set_title("Prompts by group", pad=3)
    donut.legend(wedges, [f"Group {cohort}   {n} ({n/total:.1%})"
                         for cohort, n in zip(cohorts, prompts)],
                 loc="upper center", bbox_to_anchor=(.5, .03), frameon=False,
                 handlelength=1.2, borderaxespad=0, labelspacing=.2)
    offsets = np.zeros(len(SYSTEMS))
    for cohort, color in zip(cohorts, COHORT_COLORS):
        values = [len(groups.get((cohort, system), {})) for system in SYSTEMS]
        bars = counts.barh(LABELS, values, height=.5, left=offsets, color=color)
        for bar, value in zip(bars, values):
            if value:
                counts.text(bar.get_x() + value / 2, bar.get_y() + bar.get_height() / 2,
                            str(value), ha="center", va="center", fontweight="bold",
                            color="#172b34" if cohort == "A" else "white")
        offsets += values
    for y, count in enumerate(offsets):
        counts.text(count + 12, y, str(int(count)), va="center", fontweight="bold")
    counts.set_title("Evaluated outputs per model", loc="left", pad=8)
    counts.set(xlim=(0, 600), xlabel="Number of outputs")
    counts.xaxis.set_major_locator(ticker.MultipleLocator(100))
    counts.invert_yaxis()
    counts.tick_params(axis="y", length=0)
    counts.spines["left"].set_visible(False)
    grid(counts, "x")
    save(fig, "01-cohorts.pdf")


def draw_means(groups):
    fig, axes = plt.subplots(2, 2, figsize=(7, 2.85))
    fig.subplots_adjust(left=.15, right=.98, top=.88, bottom=.14, wspace=.56, hspace=.75)
    for ax, (key, label, _, direction) in zip(axes.flat, METRICS):
        means = [scores_for(group, key).mean() for group in groups]
        bars = ax.barh(LABELS, means, height=.52, color=COLORS)
        upper = max(means) * 1.4
        title(ax, label, direction)
        ax.set_xlim(0, upper)
        ax.invert_yaxis()
        ax.tick_params(axis="y", length=0)
        ax.spines["left"].set_visible(False)
        ax.xaxis.set_major_locator(ticker.MaxNLocator(4))
        format_percent(ax.xaxis, key)
        grid(ax, "x")
        for bar, mean in zip(bars, means):
            value = f"{mean:.2%}" if key == "pinv" else f"{mean:.4f}"
            ax.text(mean + upper * .015, bar.get_y() + bar.get_height() / 2, value, va="center")
    save(fig, "02-means.pdf")


def draw_distributions(groups):
    fig, axes = plt.subplots(2, 2, figsize=(7, 3.5))
    fig.subplots_adjust(left=.125, right=.98, top=.80, bottom=.15, wspace=.29, hspace=.90)
    fig.supylabel("Cumulative share of outputs", x=.015)
    for index, (ax, (key, label, short, direction)) in enumerate(zip(axes.flat, METRICS)):
        values = [scores_for(group, key) for group in groups]
        right = max(v.max() for v in values) * 1.03
        left = min(0, min(v.min() for v in values))
        handles = []
        for data, color, style in zip(values, COLORS, STYLES):
            x, counts = np.unique(data, return_counts=True)
            handles.append(ax.step(np.r_[left, x, right], np.r_[0, np.cumsum(counts) / len(data), 1],
                                   where="post", color=color, linestyle=style, linewidth=1.6)[0])
        if index == 0:
            legend(fig, handles)
        title(ax, label, direction)
        ax.set(xlim=(left, right), ylim=(0, 1.05), xlabel=f"{short} threshold")
        ax.xaxis.set_major_locator(ticker.MaxNLocator(4))
        ax.yaxis.set_major_locator(ticker.MultipleLocator(.5))
        ax.yaxis.set_major_formatter(ticker.PercentFormatter(1, decimals=0))
        format_percent(ax.xaxis, key)
        grid(ax)
    save(fig, "03-distributions.pdf")


def draw_levels(groups):
    fig, axes = plt.subplots(2, 2, figsize=(7, 3.2))
    fig.subplots_adjust(left=.125, right=.98, top=.79, bottom=.12, wspace=.29, hspace=.65)
    fig.supylabel("Mean across prompts", x=.015)
    for index, (ax, (key, label, _, direction)) in enumerate(zip(axes.flat, METRICS)):
        handles = []
        for group, color, style, marker in zip(groups, COLORS, STYLES, MARKERS):
            means = [np.mean([record[key] for record in group.values() if int(record["level"]) == level])
                     for level in LEVELS]
            handles.append(ax.plot(LEVELS, means, color=color, linestyle=style, marker=marker,
                                   markersize=3.6, linewidth=1.5)[0])
        if index == 0:
            legend(fig, handles)
        title(ax, label, direction)
        ax.set(xticks=list(LEVELS), xticklabels=[f"L{level}" for level in LEVELS],
               xlim=(.85, 5.15), ylim=(0, ax.get_ylim()[1] * 1.03))
        ax.yaxis.set_major_locator(ticker.MaxNLocator(4))
        format_percent(ax.yaxis, key)
        grid(ax)
    save(fig, "04-by-level.pdf")


def main():
    groups = load_scores()
    group_b = [groups["B", system] for system in SYSTEMS]
    FIGURES.mkdir(parents=True, exist_ok=True)
    draw_cohorts(groups)
    draw_means(group_b)
    draw_distributions(group_b)
    draw_levels(group_b)


if __name__ == "__main__":
    main()
