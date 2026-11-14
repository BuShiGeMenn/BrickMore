# BrickMore LaTeX working manuscript

## Files

- `main.tex`: English two-column working manuscript, using the CVPR 2026 author-kit style.
- `cvpr.sty` and `ieeenat_fullname.bst`: official CVPR 2026 author-kit files. Source: https://github.com/cvpr-org/author-kit/tree/CVPR2026-v1%28latex%29
- `figures/`: all 30 extracted original PNG assets, the first-page montage made from the supplied reference, the original qualitative-comparison montage, and the additional BrickMore evaluation gallery.
- `archive/historical_tables.tex`: English transcriptions of the five data tables from the supplied Word reference. Several tables represent older versions, different evaluation criteria, or incomplete placeholders; they are not the current main comparison.
- `archive/reference_table_extraction.json`: literal extraction of all 14 source Word tables for traceability, including figure-layout tables and TODO boxes. This source-data file retains the original Chinese and is not rendered as a translation in the paper.
- `archive/reference_equation.xml`: original Office Math markup from the reference, retained for later equation review.

The manuscript body is in English. Several preserved source figures still contain Chinese text inside the images; translating or rebuilding those labels requires a separate figure-editing pass. The paper title and author information remain placeholders. Training hyperparameters, train/test split, the exact training data version, historical figures, and physical-screening counts require verification. This is not a submission-ready PDF and no target venue has been chosen.

## Build

Using a TeX Live installation with `latexmk`:

```sh
latexmk -pdf -interaction=nonstopmode main.tex
```

Or with Tectonic:

```sh
tectonic main.tex
```

Compile from this folder so the relative figure paths resolve. The first compilation may download LaTeX packages. Bibliography entries are currently written in `main.tex`; check completeness before submission.
