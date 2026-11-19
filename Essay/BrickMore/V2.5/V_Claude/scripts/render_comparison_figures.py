"""Render the four charts for the full comparison on 525 prompts."""

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
SNAPSHOT = PROJECT / "data" / "20261117"
FIGURES = PROJECT / "figures" / "comparison_20261117"
SYSTEMS = ("BrickForma", "BrickGPT", "BrickNet")
LABELS = SYSTEMS
COLORS = ("#096b74", "#a85b08", "#6352aa")
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
    groups = {system: {} for system in SYSTEMS}
    with scores.open(encoding="utf-8-sig", newline="") as source:
        for record in csv.DictReader(source):
            group = groups[record["system"]]
            prompt = record["prompt_id"]
            if prompt in group:
                raise ValueError(f"Repeated prompt for {record['system']}: {prompt}")
            for key, *_ in METRICS:
                record[key] = float(record[key])
                if not math.isfinite(record[key]):
                    raise ValueError(f"Non-finite {key} score for {prompt}")
            group[prompt] = record
    reference = groups[SYSTEMS[0]]
    for system, group in groups.items():
        levels = Counter(int(record["level"]) for record in group.values())
        if levels != dict.fromkeys(LEVELS, 105) or group.keys() != reference.keys():
            raise ValueError(f"Unmatched prompts or unexpected level counts for {system}")
        if any(record["caption"] != reference[prompt]["caption"] for prompt, record in group.items()):
            raise ValueError(f"Different captions for matching prompts for {system}")
        if len(group) != summary["matched_prompts"]:
            raise ValueError(f"Unexpected total number of prompts for {system}")
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


def draw_zero_invalid(groups):
    fig, axes = plt.subplots(1, 3, figsize=(7, 2.06))
    fig.subplots_adjust(left=.04, right=.96, top=.79, bottom=.08, wspace=.25)
    for ax, group, label, color in zip(axes, groups, LABELS, COLORS):
        total = len(group)
        count = np.count_nonzero(scores_for(group, "pinv") == 0)
        ax.pie([count, total - count], startangle=90, counterclock=False,
               colors=[color, "#e3eaed"], wedgeprops={"width": .25, "edgecolor": "white", "linewidth": 1.2})
        ax.text(0, .13, f"{count/total:.1%}", ha="center", va="center", fontsize=15, fontweight="bold")
        ax.text(0, -.23, f"{count} / {total}", ha="center", va="center")
        ax.set_title(label, pad=4)
    save(fig, "01-zero-invalid.pdf")


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
    fig, axes = plt.subplots(2, 2, figsize=(7, 4.21))
    fig.subplots_adjust(left=.105, right=.96, top=.892, bottom=.10, wspace=.32, hspace=.58)
    # Match the four scales in the 525-prompt web report.
    tick_steps = (.06, .04, .04, .02)
    top_ticks = (.24, .16, .16, .08)
    upper_bounds = (.252, .168, .190, .081)
    for index, (ax, (key, label, _, direction)) in enumerate(zip(axes.flat, METRICS)):
        handles = []
        for group, color, style, marker in zip(groups, COLORS, STYLES, MARKERS):
            means = [np.mean([record[key] for record in group.values() if int(record["level"]) == level])
                     for level in LEVELS]
            handles.append(ax.plot(LEVELS, means, color=color, linestyle=style, marker=marker,
                                   markersize=4.0, linewidth=1.5)[0])
        if index == 0:
            legend(fig, handles)
        title(ax, label, direction)
        step = tick_steps[index]
        ax.set(xticks=list(LEVELS), xticklabels=[f"L{level}" for level in LEVELS],
               xlim=(.85, 5.15), yticks=np.arange(0, top_ticks[index] + step / 2, step),
               ylim=(-step * .08, upper_bounds[index]), ylabel="Mean score")
        if key == "pinv":
            ax.yaxis.set_major_formatter(ticker.PercentFormatter(1, decimals=1))
        else:
            ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.2f"))
        grid(ax)
    save(fig, "04-by-level.pdf")


def main():
    by_system = load_scores()
    groups = [by_system[system] for system in SYSTEMS]
    FIGURES.mkdir(parents=True, exist_ok=True)
    draw_zero_invalid(groups)
    draw_means(groups)
    draw_distributions(groups)
    draw_levels(groups)


if __name__ == "__main__":
    main()
