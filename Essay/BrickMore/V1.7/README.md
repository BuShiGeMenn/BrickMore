# BrickForma LaTeX manuscript (V1.6, AAAI-27 format)

Title: *BrickForma: Text-to-Brick Generation with Voxel-to-Brick Data Construction and Geometric Reconstruction*.
Target: GSR-VLM workshop at AAAI-27 (https://gsr-vlm.org/), long paper (main content <= 7 pages; references and appendices unlimited). Review log: `REVIEW_V1.6.md`. Plan of record: `..\Plan_V1.6\FINAL_PLAN_V1.6.md`.

The method/system is called **BrickForma** from V1.6 on; the dataset/trained-model name **BrickMore-48** is unchanged.

## Files

- `main.tex`: English manuscript in the official AAAI-27 anonymous-submission format (`\usepackage[submission]{aaai2027}`). Author information is a placeholder.
- `aaai2027.sty`, `aaai2027.bst`: unmodified files from the official AAAI-27 Author Kit (https://aaai.org/authorkit27/ -> AuthorKit27.zip, style dated 2026-10-21).
- `references.bib`: bibliography (natbib + aaai2027.bst).
- `figure1.pdf`, `figure2.pdf` (+ `figure_tex/`, `figure2_units/`): Figures 1 and 2 (standalone TikZ sources; not rebuilt in V1.6).
- `figures/`: raster assets; historical figures are used only in the technical appendix. `figures/image18.png` is kept but excluded from the PDF (`\iffalse`).
- `archive/historical_tables.tex`: transcribed historical tables (appendix; `\input` by `main.tex`).
- `stats/`: paired significance re-analysis (`significance.py`, `significance.json`, `significance_output.txt`) and descriptive robustness tables (`robustness.py`, `robustness.json`, `robustness_output.txt`) computed from the existing `scores.csv`, `pe.jsonl`, `siglip2.jsonl` (copied unchanged).

## Build

Primary build (V1.6): TinyTeX (pdfTeX) + latexmk on the box:

```sh
latexmk -g -pdf -interaction=nonstopmode main.tex
```

Backup: MiKTeX / TeX Live with the same command; Overleaf (pdfLaTeX) as a third option.

Stats (Python 3 with numpy and scipy):

```sh
cd stats && python significance.py scores.csv && python robustness.py
```

## Submission package

Upload only `main.pdf`. If a source zip is needed, include only `main.tex`, `references.bib`, `aaai2027.sty`, `aaai2027.bst`, `archive/historical_tables.tex`, `figure1.pdf`, `figure2.pdf`, and the `figures/*.png` actually referenced. Do not include logs, `*.bak*`, `REVIEW_*.md`, `stats/*.jsonl`, or older zips.
