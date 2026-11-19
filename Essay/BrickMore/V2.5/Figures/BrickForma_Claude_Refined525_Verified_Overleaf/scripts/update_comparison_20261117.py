"""Rebuild V2 tables from the two matching November comparison runs."""

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean

from scipy.stats import binomtest, wilcoxon


PAPER = Path(__file__).resolve().parents[1]
METRICS = ("pinv", "vqa", "pe", "siglip2")
SYSTEMS = ("BrickForma", "BrickGPT", "BrickNet")
HEAD = r"System & $P_{\mathrm{inv}}\downarrow$ & VQAScore $\uparrow$ & PE $\uparrow$ & SigLIP2 $\uparrow$"


def jsonl(path):
    with path.open(encoding="utf-8-sig") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def table(name, columns, header, rows, caption, label, wide=False, directory=PAPER / "tables"):
    env = "table*" if wide else "table"
    content = "\n".join(rows)
    (directory / (name + ".tex")).write_text(
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
        cells = list(first_columns if i == 0 else [""] * len(first_columns)) + [system]
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


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_protocol(original, supplement, old_run, new_run):
    audit = read_json(supplement / "Data/input_audit.json")
    assert audit["passed"]
    assert audit["reference_manifest_sha256"] == digest(original / "Data/manifest.jsonl")
    for relative in ("Data/scoring_models.json", "Scripts/structure.py", "Scripts/render.py",
                     "Scripts/evaluate_paper_images.py", "Scripts/paper_common.py",
                     "Scripts/prepare_paper_inputs.py"):
        assert digest(original / relative) == digest(supplement / relative), relative
    checks = {
        "rendered/render_protocol.json": {"input_sha256", "catalog_sha256"},
        "structure.config.json": {"input_sha256", "catalog_sha256", "signature"},
    }
    for metric in METRICS[1:]:
        checks[f"{metric}.config.json"] = {"samples", "view_evaluations", "input_manifest_sha256", "signature"}
        checks[f"{metric}.model.json"] = set()
    for name, ignored in checks.items():
        before, after = (read_json(run / name) for run in (old_run, new_run))
        assert {k: v for k, v in before.items() if k not in ignored} == {
            k: v for k, v in after.items() if k not in ignored}, name
    old_parts, new_parts = (read_json(p / "Assets/catalog.json") for p in (original, supplement))
    assert old_parts["bricknet_version"] == new_parts["bricknet_version"]
    for part, entry in new_parts["parts"].items():
        for directory, suffix, key in (("inset", "ply", "collider_sha256"),
                                       ("render_meshes", "npz", "render_sha256")):
            assert digest(supplement / "Assets" / directory / f"{part}.{suffix}") == entry[key]
            assert old_parts["parts"][part][key] == entry[key], (part, key)
    return audit


def load_run(run, size):
    scores = run / "report/scores.csv"
    with scores.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        fields = reader.fieldnames
        rows = list(reader)
    progress = read_json(run / "progress.json")
    assert progress["current_stage"] == "finished"
    for stage, expected in (("render", size * 8), ("structure", size), *[(m, size) for m in METRICS[1:]]):
        status = progress["stages"][stage]
        assert status["status"] == "completed" and status["done"] == status["total"] == expected
    official = read_json(run / "report/summary.json")
    metadata = {r["sample_id"]: r for r in jsonl(run / "selected_manifest.jsonl")}
    assert len(rows) == len(metadata) == official["samples"] == size
    assert {r["sample_id"] for r in rows} == metadata.keys()
    grouped = defaultdict(list)
    for row in rows:
        ref = metadata[row["sample_id"]]
        assert row["structure_status"] == "ok"
        assert all(str(ref[k]) == row[k] for k in
                   ("system", "prompt_id", "batch", "category", "level", "caption", "part_count"))
        for metric in METRICS:
            row[metric] = float(row[metric])
            assert math.isfinite(row[metric])
        assert math.isclose(row["pinv"], int(row["invalid_placements"]) / int(row["part_count"]))
        grouped[row["batch"], row["system"]].append(row)
    for (cohort, system), group in grouped.items():
        statistics = official["by_batch"][cohort]["systems"][system]
        for metric in METRICS:
            record = statistics[metric]
            assert record["n"] == len(group) and record["missing"] == 0
            assert math.isclose(record["mean"], mean(r[metric] for r in group), abs_tol=1e-13)
    flags = {m: {} for m in ("pe", "siglip2")}
    for metric, journal in zip(METRICS, ("structure", *METRICS[1:])):
        records = jsonl(run / (journal + ".jsonl"))
        by_sample = {r["sample_id"]: r for r in records}
        assert len(by_sample) == len(records) == size
        for row in rows:
            record = by_sample[row["sample_id"]]
            assert record["status"] == "ok"
            if metric == "pinv":
                assert row[metric] == record["pinv"]
            else:
                assert len(record["scores"]) == 8
                assert math.isclose(row[metric], record["max_score"], abs_tol=1e-13)
                assert math.isclose(row[metric], max(record["scores"]), abs_tol=1e-13)
            if metric in flags:
                flags[metric][row["sample_id"]] = any(v["text_truncated"] for v in record["diagnostics"])
    # Validate the original journals before normalizing project-owned records.
    for row in rows:
        if row["system"] in SYSTEMS[1:]:
            continue
        sample = row["sample_id"]
        entry = metadata.pop(sample)
        prefix, separator, suffix = sample.partition("__")
        assert separator and prefix.casefold() == row["system"].casefold()
        assert entry["source_kind"] == "raw_model_output"
        normalized = f"brickforma__{suffix}"
        assert normalized not in metadata
        row.update(system=SYSTEMS[0], sample_id=normalized)
        entry.update(system=SYSTEMS[0], sample_id=normalized)
        metadata[normalized] = entry
        for score_flags in flags.values():
            score_flags[normalized] = score_flags.pop(sample)
    return fields, rows, metadata, flags


def paired_tests(groups):
    tests = []
    ref = groups["BrickForma"]
    for opponent in SYSTEMS[1:]:
        for metric, name in zip(METRICS[1:], ("VQAScore", "PE", "SigLIP2")):
            diff = [r[metric] - groups[opponent][p][metric] for p, r in ref.items()]
            wins, losses = sum(x > 0 for x in diff), sum(x < 0 for x in diff)
            signed = wilcoxon(diff, method="asymptotic", zero_method="wilcox")
            tests.append({"baseline": opponent, "metric": name, "wins": wins, "losses": losses,
                          "ties": len(diff) - wins - losses, "sign_p": binomtest(wins, wins + losses).pvalue,
                          "wilcoxon_w": float(signed.statistic), "wilcoxon_p": float(signed.pvalue)})
    for key in ("sign_p", "wilcoxon_p"):
        for test, value in zip(tests, holm([t[key] for t in tests])):
            test[key + "_holm"] = value
    return tests


def main(original, supplement):
    old_run = original / "Results" / "comparison_full"
    (supplement_summary,) = [
        path for path in (supplement / "Results").glob("*/report/summary.json")
        if read_json(path)["samples"] == 260
    ]
    new_run = supplement_summary.parents[1]
    audit = check_protocol(original, supplement, old_run, new_run)
    fields, original_rows, original_meta, original_flags = load_run(old_run, 1315)
    new_fields, added, paired_meta, paired_flags = load_run(new_run, 260)
    assert fields == new_fields
    assert all((r["system"], r["batch"]) == ("BrickForma", "A") for r in added)
    assert all(m["source_kind"] == "raw_model_output" for m in paired_meta.values())
    assert all((m["source_kind"], m["generation_weights"]) == ("raw_model_output", "Q8_0")
               for m in original_meta.values() if m["system"] == "BrickForma")
    for key in ("geometry_valid", "generation_complete"):
        for value in (True, False):
            assert sum(m[key] is value for m in paired_meta.values()) == audit["source_flags"][key][str(value).lower()]
    rows = sorted(original_rows + added, key=lambda r: (r["prompt_id"], SYSTEMS.index(r["system"])))
    assert len(rows) == len({r["sample_id"] for r in rows}) == 1575
    groups = {s: {r["prompt_id"]: r for r in rows if r["system"] == s} for s in SYSTEMS}
    ref = groups["BrickForma"]
    assert len(ref) == len({r["caption"] for r in ref.values()}) == 525
    for s in SYSTEMS:
        assert groups[s].keys() == ref.keys()
        for p, r in ref.items():
            assert all(groups[s][p][k] == r[k] for k in ("caption", "category", "level", "batch"))

    aggregate = means({s: groups[s].values() for s in SYSTEMS})
    table("main_results_table", "lrrrr", HEAD, score_rows(aggregate),
          "Mean scores on 525 shared prompts. BrickForma uses delivered raw outputs. Bold marks the best mean.",
          "tab:main")
    counts = {s: sum(r["pinv"] == 0 for r in groups[s].values()) for s in SYSTEMS}

    level_rows, levels = [], {}
    for level in range(1, 6):
        group = {s: [r for r in groups[s].values() if int(r["level"]) == level] for s in SYSTEMS}
        assert all(len(seq) == 105 for seq in group.values())
        words = mean(len(r["caption"].split()) for r in group["BrickForma"])
        avg = means(group)
        levels[level] = {"count": 105, "mean_words": words, "means": avg}
        if level > 1:
            level_rows.append(r"\midrule")
        level_rows.extend(score_rows(avg, [f"L{level}", 105, f"{words:.1f}"]))
    table("level_results", "lrrlrrrr", "Level & $n$ & Words & " + HEAD, level_rows,
          "Mean scores by description level. Each level contains 105 prompts per system. Words is the mean English word count. Bold marks the best mean.",
          "tab:level-results", wide=True)

    tests = paired_tests(groups)
    test_rows = [row([t["baseline"] if i % 3 == 0 else "", t["metric"],
                      f"{t['wins']}/{t['losses']}/{t['ties']}", tex_p(t["sign_p_holm"]),
                      tex_p(t["wilcoxon_p_holm"])]) for i, t in enumerate(tests)]
    table("latest_paired_tests", "llrrr",
          r"Baseline & Metric & W/L/T & Sign $p_H$ & Wilc.\ $p_H$", test_rows,
          "Two-sided paired tests on 525 prompts. W/L/T counts BrickForma wins, losses and ties. Each test uses Holm correction across six comparisons.",
          "tab:sig")

    truncation = {}
    for metric in ("pe", "siglip2"):
        values = original_flags[metric] | paired_flags[metric]
        excluded = set()
        for prompt in ref:
            flags = {values[groups[s][prompt]["sample_id"]] for s in SYSTEMS}
            assert len(flags) == 1
            if True in flags:
                excluded.add(prompt)
        truncation[metric] = {
            "truncated_prompt_count": len(excluded),
            "untruncated_means": {s: mean(r[metric] for p, r in groups[s].items() if p not in excluded)
                                  for s in SYSTEMS},
        }

    output = PAPER / "data" / "20261117"
    output.mkdir(parents=True, exist_ok=True)
    snapshot = output / "scores.csv"
    with snapshot.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "source_score_sha256": [digest(run / "report/scores.csv") for run in (old_run, new_run)],
        "source_scores_sha256": digest(snapshot),
        "matched_prompts": 525, "scored_exports": len(rows), "rendered_views": len(rows) * 8,
        "aggregate_means": aggregate, "levels": levels,
        "zero_invalid_outputs": counts, "paired_tests": tests, "truncation": truncation,
        "supplement_source_flags": audit["source_flags"],
        "supplement_glb_coverage": audit["glb_coverage"],
    }
    (output / "paper_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    for item in (aggregate, counts, tests, truncation):
        print(json.dumps(item, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path, help="November 16 comparison package")
    parser.add_argument("supplement", type=Path, help="November 17 BrickForma A260 package")
    args = parser.parse_args()
    main(args.original, args.supplement)

