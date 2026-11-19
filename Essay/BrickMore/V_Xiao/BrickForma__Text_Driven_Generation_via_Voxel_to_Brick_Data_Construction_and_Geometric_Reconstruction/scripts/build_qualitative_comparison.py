#!/usr/bin/env python3
"""Fetch hash-verified archived views and build a native LaTeX qualitative figure."""
import csv, gzip, hashlib, json, textwrap, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SYSTEMS = ("BrickMore", "BrickGPT", "BrickNet")
DISPLAY = {"BrickMore": "BrickForma", "BrickGPT": "BrickGPT", "BrickNet": "BrickNet"}

def sha(content):
    return hashlib.sha256(content).hexdigest()

def esc(text):
    mapping = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
               "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}",
               "^": r"\textasciicircum{}"}
    return "".join(mapping.get(c, c) for c in text)

def main():
    selection = json.loads((ROOT / "data/qualitative/selection.json").read_text())
    rows = [json.loads(s) for s in gzip.decompress(
        (ROOT / "data/qualitative/render_journal.jsonl.gz").read_bytes()).decode().splitlines()]
    render = {r["sample_id"]: r for r in rows}
    manifest = [json.loads(s) for s in
                (ROOT / "data/reconstruction/inputs/selected_manifest.jsonl").read_text().splitlines()]
    with (ROOT / "data/level_inputs/scores.csv").open(encoding="utf-8-sig") as stream:
        scores = {r["sample_id"]: r for r in csv.DictReader(stream)}
    selected, downloads = [], []
    for pid in selection["cases"]:
        cohort = [r for r in manifest if r["primary"] and r["prompt_id"] == pid]
        assert len(cohort) == 3 and {r["system"] for r in cohort} == set(SYSTEMS)
        assert len({r["caption"] for r in cohort}) == 1
        case = {"prompt_id": pid, "prompt": cohort[0]["caption"], "level": cohort[0]["level"], "systems": []}
        for system in SYSTEMS:
            row = next(r for r in cohort if r["system"] == system)
            entry = render[row["sample_id"]]
            assert entry["assembly_sha256"] == row["assembly_sha256"]
            assert entry["caption"] == row["caption"]
            views = []
            # Archive all eight original images, even though the paper displays two fixed views.
            for view, (relative, expected) in enumerate(zip(entry["view_paths"], entry["view_sha256"])):
                url = selection["base_url"] + urllib.parse.quote(relative, safe="/")
                dest = ROOT / "figures/short_prompts/source" / row["sample_id"] / f"{view:02d}.png"
                downloads.append((url, dest, expected))
                if view in selection["display_views"]:
                    views.append({"view": view, "azimuth_degrees": view * 45,
                                  "path": dest.relative_to(ROOT).as_posix(), "sha256": expected, "url": url})
            case["systems"].append({
                "system": DISPLAY[system], "source_system": system, "sample_id": row["sample_id"],
                "model_id": row["model_id"], "variant": row["variant"], "primary": row["primary"],
                "assembly_sha256": row["assembly_sha256"], "views": views,
                "scores": {m: float(scores[row["sample_id"]][m]) for m in ("pinv", "vqa", "pe", "siglip2")},
            })
        selected.append(case)

    def fetch(job):
        url, dest, expected = job
        if dest.exists() and sha(dest.read_bytes()) == expected:
            return
        for attempt in range(4):
            try:
                with urllib.request.urlopen(url, timeout=30) as response:
                    content = response.read()
                assert sha(content) == expected, "Archived view SHA256 mismatch"
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(content)
                return
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(1 + attempt)
    with ThreadPoolExecutor(max_workers=8) as pool:
        for number, future in enumerate(as_completed([pool.submit(fetch, j) for j in downloads]), 1):
            future.result()
            if number % 16 == 0 or number == len(downloads):
                print(f"Verified archived views: {number}/{len(downloads)}", flush=True)

    result = {"selection": selection, "cases": selected, "verified_images": len(downloads)}
    (ROOT / "data/qualitative/case_manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    lines = [r"\begin{figure*}[t]", r"\centering", r"\setlength{\tabcolsep}{3pt}",
             r"\begin{tabular}{@{}ccc@{}}",
             r"\textbf{BrickForma} & \textbf{BrickGPT} & \textbf{BrickNet} \\"]
    for letter, case in zip("abcd", selected):
        label = r"\textbf{(" + letter + ") L" + str(case["level"]) + r":} "
        prompt = label + r"\emph{" + esc(case["prompt"]) + "}"
        lines.append(r"\multicolumn{3}{@{}p{0.96\textwidth}@{}}{\small " + prompt + r"} \\")
        cells = []
        for system in case["systems"]:
            cells.append("".join(r"\includegraphics[width=0.15\textwidth]{" + v["path"] + "}"
                                 for v in system["views"]))
        lines.append(" & ".join(cells) + r" \\[2pt]")
    lines.extend([
        r"\end{tabular}",
        r"\caption{Matched short-prompt examples from the main comparison. Each row uses the same prompt across all three systems and displays the same two archived camera azimuths ($45^\circ$, $225^\circ$), with $25^\circ$ elevation and uniform yellow rendering. BrickForma uses the fixed retiled main-comparison output in these four cases. Chair and bench illustrate higher BrickForma VQAScore; car and camera retain counterexamples where BrickNet has a higher VQAScore. Examples illustrate variation across cases and do not estimate a success rate.}",
        r"\label{fig:short-prompts}", r"\end{figure*}",
    ])
    target = ROOT / "figure_tex/short_prompt_comparison.tex"
    target.write_text("\n".join(lines) + "\n")

    def preview_font(size):
        for name in ("/System/Library/Fonts/Supplemental/Arial.ttf", "DejaVuSans.ttf", "Arial.ttf"):
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                pass
        return ImageFont.load_default(size=size)
    font = preview_font(30)
    header = preview_font(38)
    width, margin, col = 2100, 24, 684
    row_heights = []
    wrapped = []
    for case in selected:
        text = f"L{case['level']} | {case['prompt']}"
        lines_p = textwrap.wrap(text, width=108)
        wrapped.append(lines_p)
        row_heights.append(44 * len(lines_p) + 356 + 18)
    canvas = Image.new("RGB", (width, 78 + sum(row_heights)), "white")
    draw = ImageDraw.Draw(canvas)
    for c, name in enumerate(("BrickForma", "BrickGPT", "BrickNet")):
        draw.text((margin + c * col + 220, 18), name, font=header, fill="black")
    y = 78
    for case, prompt_lines, height in zip(selected, wrapped, row_heights):
        for line in prompt_lines:
            draw.text((margin, y), line, font=font, fill="black")
            y += 44
        for c, system in enumerate(case["systems"]):
            for j, view in enumerate(system["views"]):
                im = Image.open(ROOT / view["path"]).convert("RGB")
                im = im.resize((338, 338), Image.Resampling.LANCZOS)
                canvas.paste(im, (margin + c * col + j * 340, y))
        y += 356 + 18
        draw.line((margin, y - 8, width - margin, y - 8), fill=(210, 210, 210), width=2)
    canvas.save(ROOT / "figures/short_prompts/comparison.png", dpi=(300, 300))
    print("Created native LaTeX figure and comparison preview. No image synthesis or metric-based view selection.")

if __name__ == "__main__":
    main()
