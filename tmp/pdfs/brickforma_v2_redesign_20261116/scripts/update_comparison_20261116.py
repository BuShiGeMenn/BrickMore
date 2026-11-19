"""Rebuild the November 16 tables and gallery from a completed comparison run."""

import argparse
import csv
import hashlib
import json
import math
import shutil
from collections import defaultdict
from pathlib import Path
from statistics import mean

from PIL import Image, ImageDraw, ImageFont
from scipy.stats import binomtest, wilcoxon


PAPER = Path(__file__).resolve().parents[1]
METRICS = ("pinv", "vqa", "pe", "siglip2")
SYSTEMS = ("BrickMore", "BrickGPT", "BrickNet")
NAMES = dict(zip(SYSTEMS, ("BrickForma", "BrickGPT", "BrickNet")))
CASE_IDS = ("B22_L1", "B19_L1", "B06_L2", "B17_L2")
HEAD = r"System & $P_{\mathrm{inv}}\downarrow$ & VQAScore $\uparrow$ & PE $\uparrow$ & SigLIP2 $\uparrow$"


def jsonl(path):
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def table(name, columns, header, rows, caption, label, wide=False):
    env = "table*" if wide else "table"
    content = "\n".join(rows)
    (PAPER / "sections" / (name + ".tex")).write_text(
        f"\\begin{{{env}}}[t]\n\\centering\\small\n"
        f"\\setlength{{\\tabcolsep}}{{3pt}}\n\\begin{{tabular}}{{{columns}}}\n"
        f"\\toprule\n{header} \\\\\n\\midrule\n{content}\n"
        f"\\bottomrule\n\\end{{tabular}}\n\\caption{{{caption}}}\n"
        f"\\label{{{label}}}\n\\end{{{env}}}\n",
        encoding="utf-8",
    )


def row(cells):
    return " & ".join(str(x) for x in cells) + r" \\"


def means(group):
    return {s: {m: mean(r[m] for r in records) for m in METRICS}
            for s, records in group.items()}


def score_rows(avg, first_columns=()):
    rows = []
    for i, (system, metrics) in enumerate(avg.items()):
        cells = list(first_columns if i == 0 else [""] * len(first_columns)) + [NAMES[system]]
        for m, value in metrics.items():
            best = (min if m == "pinv" else max)(d[m] for d in avg.values())
            text = f"{100 * value:.2f}" + r"\%" if m == "pinv" else f"{value:.4f}"
            cells.append(r"\textbf{" + text + "}" if best == value else text)
        rows.append(row(cells))
    return rows


def holm(values):
    adjusted = [0.0] * len(values)
    largest = 0.0
    for rank, i in enumerate(sorted(range(len(values)), key=values.__getitem__)):
        largest = max(largest, min(1.0, (len(values) - rank) * values[i]))
        adjusted[i] = largest
    return adjusted


def tex_p(p):
    mantissa, exponent = f"{p:.1e}".split("e")
    return "$" + mantissa + rf"\times 10^{{{int(exponent)}}}$"


def build_gallery(run, groups, fonts):
    font = ImageFont.truetype(str(fonts / "arial.ttf"), 39)
    bold = ImageFont.truetype(str(fonts / "arialbd.ttf"), 46)
    panel = Image.new("RGB", (2100, 1600), "white")
    draw = ImageDraw.Draw(panel)
    for i, system in enumerate(SYSTEMS):
        draw.text((15 + 690 * (i + 0.5), 35), NAMES[system], font=bold,
                  fill="#172b34", anchor="mm")
    y = 74
    cases = {}
    for k, prompt in enumerate(CASE_IDS):
        ref = groups["BrickMore"][prompt]
        line = f"({chr(97 + k)}) L{ref['level']}:"
        for word in ref["caption"].split():
            if font.getlength(line + " " + word) > 2030:
                draw.text((20, y), line, font=font, fill="#172b34")
                y += 47
                line = word
            else:
                line += " " + word
        draw.text((20, y), line, font=font, fill="#172b34")
        y += 47
        cases[prompt] = {"caption": ref["caption"], "samples": {}}
        for i, system in enumerate(SYSTEMS):
            sample = groups[system][prompt]
            cases[prompt]["samples"][system] = {m: sample[m] for m in ("sample_id", "vqa")}
            for j, view in enumerate((1, 5)):
                path = run / "rendered" / "views" / sample["sample_id"] / f"{view:02d}.png"
                with Image.open(path) as source:
                    assert source.size == (512, 512)
                    tile = source.convert("RGB").resize((240, 240), Image.Resampling.LANCZOS)
                panel.paste(tile, (100 + i * 690 + j * 260, y))
        y += 256
    assert y <= panel.height
    panel.crop((0, 0, 2100, y)).save(PAPER / "figures" / "matched_short_prompts_20261116.png")
    return cases


def main(run, fonts):
    report = run / "report"
    with (report / "scores.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    official = json.loads((report / "summary.json").read_text(encoding="utf-8"))
    progress = json.loads((run / "progress.json").read_text(encoding="utf-8"))
    assert progress["current_stage"] == "finished"
    assert all(x["status"] == "completed" and x["done"] == x["total"]
               for x in progress["stages"].values())
    assert len(rows) == len({r["sample_id"] for r in rows}) == official["samples"] == 1315
    metadata = {r["sample_id"]: r for r in jsonl(run / "selected_manifest.jsonl")}
    assert len(metadata) == 1315
    groups = defaultdict(dict)
    for r in rows:
        assert r["structure_status"] == "ok"
        meta = metadata[r["sample_id"]]
        assert all(r[k] == meta[k] for k in ("caption", "prompt_id", "batch", "system"))
        if r["system"] == "BrickMore":
            assert (meta["source_kind"], meta["generation_weights"]) == ("raw_model_output", "Q8_0")
        for m in METRICS:
            r[m] = float(r[m])
            assert math.isfinite(r[m])
        assert math.isclose(r["pinv"], int(r["invalid_placements"]) / int(r["part_count"]))
        slot = groups[r["batch"], r["system"]]
        assert r["prompt_id"] not in slot
        slot[r["prompt_id"]] = r
    cohorts = {"A": SYSTEMS[1:], "B": SYSTEMS}
    cohort_means = {}
    for b, systems in cohorts.items():
        ref = groups[b, systems[0]]
        assert len(ref) == (265 if b == "B" else 260)
        for s in systems:
            assert groups[b, s].keys() == ref.keys()
            assert all(groups[b, s][p]["caption"] == ref[p]["caption"] for p in ref)
        cohort_means[b] = means({s: groups[b, s].values() for s in systems})
        for s in systems:
            for m in METRICS:
                recorded = official["by_batch"][b]["systems"][s][m]
                assert recorded["n"] == len(ref) and recorded["missing"] == 0
                assert math.isclose(recorded["mean"], cohort_means[b][s][m], abs_tol=1e-13)
    assert not groups["A", "BrickGPT"].keys() & groups["B", "BrickGPT"].keys()
    latest = {s: groups["B", s] for s in SYSTEMS}
    ref = latest["BrickMore"]
    table("main_results_table", "lrrrr", HEAD, score_rows(cohort_means["B"]),
          "Group B means on 265 matched prompts. BrickForma uses delivered raw outputs. Bold marks the best mean.",
          "tab:main")
    table("batch_a_results", "lrrrr", HEAD, score_rows(cohort_means["A"]),
          "Group A means on 260 matched prompts. This cohort contains BrickGPT and BrickNet.",
          "tab:group-a")

    level_rows, levels = [], {}
    for level in range(1, 6):
        group = {s: [r for r in latest[s].values() if int(r["level"]) == level] for s in SYSTEMS}
        assert all(len(seq) == 53 for seq in group.values())
        words = mean(len(r["caption"].split()) for r in group["BrickMore"])
        avg = means(group)
        levels[level] = {"count": 53, "mean_words": words, "means": avg}
        if level > 1:
            level_rows.append(r"\midrule")
        level_rows.extend(score_rows(avg, [f"L{level}", 53, f"{words:.1f}"]))
    table("level_results", "lrrlrrrr", "Level & $n$ & Words & " + HEAD, level_rows,
          "Group B means by description level. Each level contains 53 prompts per system. Words is the mean English word count. Bold marks the best mean.",
          "tab:levels", wide=True)

    tests = []
    for opponent in SYSTEMS[1:]:
        for metric, name in zip(METRICS[1:], ("VQAScore", "PE", "SigLIP2")):
            diff = [r[metric] - latest[opponent][p][metric] for p, r in ref.items()]
            wins, losses = sum(x > 0 for x in diff), sum(x < 0 for x in diff)
            signed = wilcoxon(diff, method="asymptotic", zero_method="wilcox")
            tests.append({"baseline": opponent, "metric": name, "wins": wins, "losses": losses,
                          "ties": len(diff) - wins - losses, "sign_p": binomtest(wins, wins + losses).pvalue,
                          "wilcoxon_w": float(signed.statistic), "wilcoxon_p": float(signed.pvalue)})
    for key in ("sign_p", "wilcoxon_p"):
        for test, value in zip(tests, holm([t[key] for t in tests])):
            test[key + "_holm"] = value
    test_rows = []
    for i, t in enumerate(tests):
        test_rows.append(row([t["baseline"] if i % 3 == 0 else "", t["metric"],
                              f"{t['wins']}/{t['losses']}/{t['ties']}", tex_p(t["sign_p_holm"]),
                              tex_p(t["wilcoxon_p_holm"])]))
    table("latest_paired_tests", "llrrr",
          r"Baseline & Metric & W/L/T & Sign $p_H$ & Wilc.\ $p_H$", test_rows,
          "Two-sided paired tests on Group B. W/L/T counts BrickForma wins, losses and ties. Each test uses Holm correction across six comparisons.",
          "tab:sig")

    truncation = {}
    for m in ("pe", "siglip2", "vqa"):
        records = jsonl(run / (m + ".jsonl"))
        scores = {r["sample_id"]: r for r in records}
        assert len(records) == len(scores) == 1315
        for r in rows:
            raw = scores[r["sample_id"]]
            assert raw["status"] == "ok" and len(raw["scores"]) == 8
            assert math.isclose(max(raw["scores"]), r[m], abs_tol=1e-13)
        if m == "vqa":
            continue
        flags = {p: any(d["text_truncated"] for d in scores[r["sample_id"]]["diagnostics"])
                 for p, r in ref.items()}
        for system in SYSTEMS:
            assert all(any(d["text_truncated"] for d in scores[r["sample_id"]]["diagnostics"]) == flags[p]
                       for p, r in latest[system].items())
        truncation[m] = {"truncated_prompt_count": sum(flags.values()),
                         "untruncated_means": {s: mean(r[m] for p, r in latest[s].items() if not flags[p])
                                               for s in SYSTEMS}}
    summary = {
        "source_scores_sha256": hashlib.sha256((report / "scores.csv").read_bytes()).hexdigest(),
        "cohort_means": cohort_means, "levels_b": levels,
        "paired_tests_b": tests, "truncation_b": truncation,
        "gallery": build_gallery(run, latest, fonts),
    }
    out = PAPER / "stats" / "20261116"
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(report / "scores.csv", out / "scores.csv")
    (out / "paper_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"truncation": truncation,
                      "worst_holm_p": max(max(t["sign_p_holm"], t["wilcoxon_p_holm"]) for t in tests)},
                     indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="Completed Results/comparison_full folder")
    parser.add_argument("--fonts", type=Path, default=Path("C:/Windows/Fonts"))
    args = parser.parse_args()
    main(args.run, args.fonts)
