# BrickForma V2

V2 follows the active LaTeX draft in the supplied workshop ZIP. It asks how generators complete geometry from short descriptions and how a compact model can learn from LLM-authored parametric programs. The manuscript develops the voxel-to-brick dataset, Qwen3-1.7B fine-tuning, and exact-cover reconstruction in that order. The evaluation presents the overall comparison, the five description levels, the raw/retiled comparison, the geometry audit, and evaluation boundaries.

## Manuscript and figures

- The abstract and introduction are restored byte-for-byte from the active `abs-xiao.tex` and `intro-xiao.tex` in the supplied ZIP. The source citation key and table label used by Xiao are defined in the V2 project.
- These restored sections retain Xiao's original 114-prompt results and unfinished percentage. The evaluation section and its tables report the newer 265-prompt main comparison.
- Figure 1 spans both columns beneath the title and before the abstract on page 1. The document adds it to the AAAI title block using the LaTeX command hook. The abstract continues on page 2.
- The Figure 1 layout reserves space between the model renders, panel headings, and model labels. The editable source is `figure_tex/figure1_content.tex`.
- Figure 2 on page 4 distinguishes the geometric checks used in dataset construction from the recorded contact-screening status. Its editable TikZ source is `figure_tex/figure2_content.tex`.
- Figure 3 uses the four matched Group B cases B22_L1, B19_L1, B06_L2, and B17_L2 on page 7. Its renders use identical viewpoints and materials across systems.
- Appendix C adds four English figures on pages 16-18. Figures 15-18 show cohort composition, Group B means, empirical cumulative distributions, and the breakdown by description level. The evaluation cites each figure.

## Experiment provenance

- The November 16 evaluation has 1,315 LDraw exports and 10,520 views. Group B contains 265 matched prompts, 53 per description level, with raw Q8_0 outputs for BrickForma. Group A contains 260 matched prompts for BrickGPT and BrickNet. Group B is the three-system comparison.
- The corresponding score snapshot and computations are in `stats/20261116/scores.csv` and `stats/20261116/paper_summary.json`. The source report is under `BrickMore_Comparision/BrickMoreComparison_20261116/BrickMoreComparison_20261116/Results/comparison_full` in the repository.
- Run `python scripts/render_comparison_figures.py` from the local source project with NumPy and Matplotlib to reproduce the four vector charts. The script checks the snapshot hash and prompt pairing. `scripts/update_comparison_20261116.py` takes the source report directory as its argument and regenerates the comparison tables and gallery with Pillow and SciPy.
- The historical 110-pair repair evaluation and geometry audit have their own subsections and denominators. The 525-prompt structure diagnostic includes a recovery procedure and partially overlaps with the candidate pool for the earlier 114-prompt comparison. The old score snapshot is stored in `stats/scores.csv`.

## Build and upload

- Entry point is `main.tex`, using the AAAI-27 anonymous style. Compile with pdfLaTeX via `latexmk -pdf main.tex`. The included figure PDFs support a direct build. Use `scripts/build.ps1` to rebuild both standalone TikZ figures and the manuscript locally.
- `BrickForma_V2_Overleaf.zip` contains the compile dependencies at its root. Select `main.tex` as the main document and use pdfLaTeX.
- Open `BrickForma_V2_revised.pdf` for this revision. It has 18 US Letter pages. The last figure in the main paper and the start of the references are on page 7.

## Training manifest check

The release reports count 79,301 geometrically passing models, which yields 396,505 English records at five per model. Training logs record 396,610 caption--placement pairs. The two counts are presented separately pending reconciliation against the training manifest.
