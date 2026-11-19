"""Build the Claude manuscript's final-output comparison from the audited snapshots."""

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from PIL import Image, ImageChops

from update_comparison_20261117 import (
    HEAD, METRICS, PAPER, SYSTEMS, digest, jsonl, means, paired_tests, row, score_rows, table, tex_p,
)

RAW = PAPER / "data" / "20261117"
FINAL = PAPER / "data" / "20261119"
TABLES = PAPER / "claude"
MATCH_FIELDS = ("prompt_id", "model_id", "caption", "category", "level", "batch")
GALLERY = (
    ("B22_L1", 140, 340),
    ("B19_L1", 448, 647),
    ("B06_L2", 796, 993),
    ("B17_L2", 1140, 1349),
)


def read_scores(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_snapshot():
    raw_path = RAW / "scores.csv"
    raw_summary = json.loads((RAW / "paper_summary.json").read_text())
    assert digest(raw_path) == raw_summary["source_scores_sha256"]
    raw_rows = read_scores(raw_path)
    raw = {r["prompt_id"]: r for r in raw_rows if r["system"] == "BrickForma"}
    manifest = {m["sample_id"]: m for m in jsonl(FINAL / "selected_manifest.jsonl")}
    refined = read_scores(FINAL / "refined_scores.csv")
    assert len(raw_rows) == 1575 and len(raw) == len(manifest) == len(refined) == 525
    assert {r["prompt_id"] for r in refined} == raw.keys()
    assert {r["sample_id"] for r in refined} == manifest.keys()
    assert Counter(r["level"] for r in refined) == dict.fromkeys("12345", 105)

    journals = {metric: {m["sample_id"]: m for m in jsonl(FINAL / f"{name}.jsonl")}
                for metric, name in zip(METRICS, ("structure", *METRICS[1:]))}
    assert all(journal.keys() == manifest.keys() for journal in journals.values())
    flags = {metric: set() for metric in ("pe", "siglip2")}
    for record in refined:
        sid = record["sample_id"]
        prompt = record["prompt_id"]
        entry = manifest[sid]
        assert entry["raw_baseline_sample_id"].replace("brickmore__", "brickforma__", 1) == raw[prompt]["sample_id"]
        assert all(str(entry[k]) == record[k] == raw[prompt][k] for k in MATCH_FIELDS)
        assert hashlib.sha256(record["caption"].encode()).hexdigest() == entry["caption_sha256"]
        assert record["system"] == "BrickMore" and record["variant"] == "refined"
        assert str(entry["part_count"]) == record["part_count"]
        assert record["primary"] == "True" and record["structure_status"] == "ok"
        structure = journals["pinv"][sid]
        assert structure["status"] == "ok" and structure["n_actions"] == entry["part_count"]
        assert float(record["pinv"]) == structure["pinv"] == 0
        assert int(record["invalid_placements"]) == structure["invalid_placements"] == 0
        for metric in METRICS[1:]:
            result = journals[metric][sid]
            assert result["status"] == "ok" and len(result["scores"]) == 8
            assert float(record[metric]) == result["max_score"] == max(result["scores"])
            if metric in flags and any(d["text_truncated"] for d in result["diagnostics"]):
                flags[metric].add(prompt)
        record.update(system="BrickForma", sample_id=sid.replace("brickmore__", "brickforma__", 1))

    rows = [r for r in raw_rows if r["system"] != "BrickForma"] + refined
    rows.sort(key=lambda r: (r["prompt_id"], SYSTEMS.index(r["system"])))
    score_path = FINAL / "scores.csv"
    with score_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=raw_rows[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    groups = {s: {} for s in SYSTEMS}
    levels = {k: defaultdict(list) for k in range(1, 6)}
    for record in rows:
        record.update({m: float(record[m]) for m in METRICS})
        group = groups[record["system"]]
        assert record["prompt_id"] not in group
        group[record["prompt_id"]] = record
        levels[int(record["level"])][record["system"]].append(record)
    assert all(g.keys() == raw.keys() for g in groups.values())
    assert all(all(g[p]["caption"] == raw[p]["caption"] for p in raw) for g in groups.values())
    summary = {
        "source_scores_sha256": digest(score_path),
        "raw_comparison_sha256": digest(raw_path),
        "refined_source_scores_sha256": digest(FINAL / "refined_scores.csv"),
        "refined_source_manifest_sha256": digest(FINAL / "selected_manifest.jsonl"),
        "matched_prompts": len(raw),
        "scored_exports": len(rows),
        "rendered_views": 8 * len(rows),
        "refined_run_rendered_views": 8 * len(refined),
        "aggregate_means": means({s: g.values() for s, g in groups.items()}),
        "levels": {l: means(by_system) for l, by_system in levels.items()},
        "zero_invalid_outputs": {s: sum(r["pinv"] == 0 for r in g.values()) for s, g in groups.items()},
        "paired_tests": paired_tests(groups),
        "refine_origins": dict(Counter(entry["refine_origin"] for entry in manifest.values())),
        "recorded_voxel_removals": {
            entry["prompt_id"]: entry["removed_voxels"] for entry in manifest.values() if entry["removed_voxels"]
        },
        "truncation": {},
    }
    for metric, excluded in flags.items():
        previous = raw_summary["truncation"][metric]
        assert len(excluded) == previous["truncated_prompt_count"]
        summary["truncation"][metric] = {
            "truncated_prompt_count": len(excluded),
            "untruncated_means": {
                "BrickForma": mean(r[metric] for p, r in groups["BrickForma"].items() if p not in excluded),
                **{s: previous["untruncated_means"][s] for s in SYSTEMS[1:]},
            },
        }
    (FINAL / "paper_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary, levels


def write_tables(summary, levels):
    table("main_results_table-claude", "lrrrr", HEAD, score_rows(summary["aggregate_means"]),
          "Mean scores on 525 shared prompts. BrickForma uses final outputs after refinement and recovery. "
          "Bold marks the best mean, including ties.", "tab:main", directory=TABLES)
    level_rows = []
    for level, by_system in levels.items():
        if level > 1:
            level_rows.append(r"\midrule")
        words = mean(len(record["caption"].split()) for record in by_system["BrickForma"])
        level_rows.extend(score_rows(summary["levels"][level], [f"L{level}", "105", f"{words:.1f}"]))
    table("level_results-claude", "lrrlrrrr", "Level & $n$ & Words & " + HEAD, level_rows,
          "Mean scores by description level. Each level has 105 prompts per system. Words is the mean English "
          "word count. BrickForma uses final outputs after refinement and recovery. Bold marks the best mean.",
          "tab:level-results", wide=True, directory=TABLES)
    rows = [row([test["baseline"] if i % 3 == 0 else "", test["metric"],
                 f'{test["wins"]}/{test["losses"]}/{test["ties"]}',
                 tex_p(test["sign_p_holm"]), tex_p(test["wilcoxon_p_holm"])])
            for i, test in enumerate(summary["paired_tests"])]
    table("latest_paired_tests-claude", "llrrr", r"Baseline & Metric & W/L/T & Sign $p_H$ & Wilc.\ $p_H$", rows,
          "Two-sided paired tests for final BrickForma outputs on 525 prompts. W/L/T counts BrickForma wins, "
          "losses, and ties. Each test applies Holm correction across its six comparisons.",
          "tab:sig", directory=TABLES)


def write_gallery():
    figures = PAPER / "figures"
    composite = Image.open(figures / "matched_short_prompts_20261116.png").convert("RGBA")
    for prompt, top, bottom in GALLERY:
        composite.paste((255, 255, 255, 0), (0, top, 600, bottom))
        renders = []
        for view in (1, 5):
            image = Image.open(figures / "gallery_refined_20261119" / f"{prompt}-{view:02}.png").convert("RGB")
            background = Image.new("RGB", image.size, image.getpixel((0, 0)))
            difference = ImageChops.difference(image, background)
            mask = difference.convert("L").point(lambda value: 255 if value else 0)
            image.putalpha(mask)
            renders.append(image.crop(mask.getbbox()))
        scale = 175 / max(max(im.size) for im in renders)
        for center, image in zip((228, 474), renders):
            width, height = (round(side * scale) for side in image.size)
            tile = image.resize((width, height), Image.Resampling.LANCZOS)
            composite.alpha_composite(tile, (center - width // 2, (top + bottom - height) // 2))
    composite.save(figures / "matched_short_prompts_20261119.png")


if __name__ == "__main__":
    summary, levels = write_snapshot()
    write_tables(summary, levels)
    write_gallery()
