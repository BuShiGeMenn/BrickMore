# BrickForma V2.1

V2.1 follows the active LaTeX draft in the supplied workshop ZIP. It asks how generators complete geometry from short descriptions and how a compact model can learn from LLM-authored parametric programs. The manuscript develops the voxel-to-brick dataset, Qwen3-1.7B fine-tuning, and exact-cover refinement in that order. The evaluation presents the overall comparison, the five description levels, the raw/refined comparison, the geometry audit, and evaluation boundaries.

## Project layout

- `main.tex` contains the preamble, body, and appendices. The active abstract and introduction are `abs-xiao.tex` and `intro-xiao.tex` at the project root.
- `tables/` holds the standalone LaTeX tables. `data/20261117/` holds the current 525-prompt comparison, `data/20261116/` holds the preceding score snapshot, and `data/level_inputs/` holds files for the historical 114-prompt comparison.
- `figure_tex/` holds the active figure layouts, and `figures/` holds their rendered assets. `figure_data/` contains source assemblies, voxel data, meshes, and provenance for the model renders.
- `figure2_units/` contains the standalone V1.6 workflow panels for editing reference. The current workflow in the paper is built from `figure2.tex` and `figure_tex/figure2_content.tex`.
- `scripts/` contains the manuscript build and figure and table regeneration scripts. `archive/` contains the historical tables.

## Manuscript and figures

- The abstract and introduction retain the Xiao draft's narrative. Their experimental statements, including the relative VQAScore improvement, now use the 525-prompt comparison.
- The paper uses BrickForma, refine, refined, and refinement in its text, captions, and visible figure labels. To regenerate the updated historical figure labels, run `python scripts/render_refinement_labels.py` with Pillow and Matplotlib installed.
- Figure 1 spans both columns beneath the title and before the abstract on page 1. The document adds it to the AAAI title block using the LaTeX command hook. The abstract continues on page 2.
- Figure 1 uses a 7-inch-wide, 4.25-inch-high layout with one triplet for each of the 21 categories. In each triplet, the source voxels retain their original colors, and both LEGO assemblies use the brick-type palette. Edit the TikZ layout in `figure_tex/figure1_content.tex`. The transparent model tiles are in `figures/figure1_models/`. Run `pdflatex figure1.tex` to rebuild the standalone figure PDF before rebuilding the paper.
- The Figure 1 caption explains the source voxel model, its tiled LEGO assembly, and the same-category BrickForma output. The brick-type palette is applied only to the renders and excluded from training targets.
- Model renders in the paper use transparent backgrounds. The two source thumbnails in Figure 2 are spaced so both silhouettes are visible.
- Figure 2 on page 4 names the LLM and distinguishes dataset geometry checks from separately recorded contact screening. Section 3 explains the generator pseudocode and search roles. Appendix A defines the completed-layer screen, tipping margin, and minimum per-stud tensile demand. Its editable TikZ source is `figure_tex/figure2_content.tex`.
- Figure 3 shows four matched prompts from the comparison on page 7. Its renders use identical viewpoints and materials across systems.
- Figures 15-18 appear on pages 16-18. They show the proportion of outputs with zero invalid placements, overall means, empirical cumulative distributions, and means by description level.

## Experiment provenance

- The November 17 comparison has 525 matched prompts, 105 per description level. All three systems provide one output per prompt, for 1,575 LDraw exports and 12,600 renders. BrickForma uses its delivered raw sequences before geometric refinement.
- The scores and recomputed statistics are in `data/20261117/scores.csv` and `data/20261117/paper_summary.json`. The original server scores and the supplemental run use the same render, structure, and alignment scoring settings. The table generator checks these settings, the exact prompt matches, and the score journals before merging.
- Recompute the tables and score snapshot with `python scripts/update_comparison_20261117.py ORIGINAL_PACKAGE SUPPLEMENT_PACKAGE` using SciPy. The package roots are `BrickMore_Comparision/BrickMoreComparison_20261116/BrickMoreComparison_20261116` and `tmp/comparison_20261117_intake/BrickMore_A260_20261117` relative to the repository. Run `python scripts/render_comparison_figures.py` with NumPy and Matplotlib to regenerate the four vector charts.
- The historical 110-pair repair evaluation and geometry audit have their own subsections and denominators. The 525-prompt structure diagnostic includes a recovery procedure and partially overlaps with the candidate pool for the earlier 114-prompt comparison. The old score snapshot is stored in `data/level_inputs/scores.csv`.

## Build and upload

- Entry point is `main.tex`, using the AAAI-27 anonymous style. Compile with pdfLaTeX via `latexmk -pdf main.tex`. The included figure PDFs support a direct build. Use `scripts/build.ps1` to rebuild both standalone TikZ figures and the manuscript locally.
- `BrickForma_V2.1_Overleaf.zip` contains the reorganized project with `main.tex` at the ZIP root. Select `main.tex` as the main document and use pdfLaTeX.
- Open `main.pdf` for the current compiled paper. It has 18 US Letter pages. The last figure in the main paper and the start of the references are on page 7.

## Training manifest check

The release reports count 79,301 geometrically passing models, which yields 396,505 English records at five per model. Training logs record 396,610 caption--placement pairs. The two counts are presented separately pending reconciliation against the training manifest.
