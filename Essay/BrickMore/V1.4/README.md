# BrickMore LaTeX manuscript (V1.4, AAAI-27 format)

Target: GSR-VLM workshop at AAAI-27 (https://gsr-vlm.org/), long paper (main content <= 7 pages; references and appendices unlimited). Review log: `REVIEW_V1.4.md`.

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
