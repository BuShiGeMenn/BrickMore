# BrickForma LaTeX manuscript (V1.5, AAAI-27 format)

Target: GSR-VLM workshop at AAAI-27 (https://gsr-vlm.org/), long paper (main content <= 7 pages; references and appendices unlimited). Review log: `REVIEW_V1.5.md`.

## Files

- `main.tex`: English manuscript in the official AAAI-27 anonymous-submission format (`\usepackage[submission]{aaai2027}`). Author information is a placeholder.
- `aaai2027.sty`, `aaai2027.bst`: unmodified files from the official AAAI-27 Author Kit (https://aaai.org/authorkit27/ -> AuthorKit27.zip, style dated 2026-10-21).
- `references.bib`: bibliography (natbib + aaai2027.bst).
- `figure1.pdf`, `figure2.pdf` (+ `figure_tex/`, `figure2_units/`): Figures 1 and 2 (standalone TikZ sources).
- `figures/`: raster assets; historical figures are used only in the technical appendix.
- `archive/historical_tables.tex`: transcribed historical tables (appendix).
- `archive/cvpr_template/`: the CVPR 2026 style files used up to V1.3 (no longer used).

## Build

`aaai2027.sty` requires pdfTeX, so Tectonic can no longer build `main.tex`. Use MiKTeX or TeX Live:

```sh
latexmk -pdf -interaction=nonstopmode main.tex
```

or `scripts/build.ps1` (Tectonic for the two standalone figures, latexmk for `main.tex`). Overleaf (pdfLaTeX compiler) also works.

## 2026-11-15 update

Title, Abstract and Introduction now use BrickForma. The five-level comparison is generated from archived GitHub scores by `scripts/build_level_results.py` and included through `tables/level_results.tex`. Data and source provenance are in `data/`. The current `main.pdf` was compiled successfully with pdfLaTeX. See `UPDATE_20261115.txt` and `EXPERIMENT_ALIGNMENT_REVIEW_20261115.txt`.

## Reconstruction audit and short-prompt comparison

Table 6 reports independently recomputed geometry for 110 matched raw/retiled pairs. Figure 3 shows the same four L1/L2 prompts across three systems with two fixed archived views each. See `data/reconstruction/AUDIT_README.txt` for exact definitions, pinned sources and missing evidence. Run `python3 scripts/audit_geometric_reconstruction.py` to rebuild the audit and table offline. The figure is editable in `figure_tex/short_prompt_comparison.tex`; its 96 hash-verified source views and selection manifest are included. `scripts/build_qualitative_comparison.py` regenerates it and the PNG preview (requires Pillow; cached images support offline use). Overleaf uses the generated sources directly.
