# BrickForma V2.2

V2.2 follows the active LaTeX draft in the supplied workshop ZIP. It asks how generators complete geometry from short descriptions and how a compact model can learn from LLM-authored parametric programs. The manuscript develops the voxel-to-brick dataset, Qwen3-1.7B fine-tuning, and exact-cover refinement in that order. The evaluation presents the overall comparison, the five description levels, the raw/refined comparison, the geometry audit, and evaluation boundaries.

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
- The Figure 1 caption explains the source voxel model, its converted LEGO assembly, and the same-category BrickForma output. The brick-type palette is applied only to the renders and excluded from training targets.
- Model renders in the paper use transparent backgrounds. The two source thumbnails in Figure 2 are spaced so both silhouettes are visible.
- Figure 2 on page 4 names the LLM and distinguishes dataset geometry checks from separately recorded contact screening. Section 3 explains the generator pseudocode and search roles. Appendix A defines the completed-layer screen, tipping margin, and minimum per-stud tensile demand. Its editable TikZ source is `figure_tex/figure2_content.tex`.
- Figure 3 shows four matched prompts from the comparison on page 7. Its renders use identical viewpoints and materials across systems.
- Figures 15-18 appear on pages 16-18. They show the proportion of outputs with zero invalid placements, overall means, empirical cumulative distributions, and means by description level.

## Experiment provenance

- The November 17 comparison has 525 matched prompts, 105 per description level. All three systems provide one output per prompt, for 1,575 LDraw exports and 12,600 renders. BrickForma uses its delivered raw sequences before geometric refinement.
- The 525-prompt matched comparison uses the delivered raw exports. Appendix C distinguishes that protocol from the separate 525-prompt refinement diagnostic and records the supplemental completion and geometry flags. The inference description documents exact coverage, stud-contact connectivity, HiGHS time tiers, and the independent audit. The archived inference package is needed to verify the MILP objective and gap tolerance.
- The scores and recomputed statistics are in `data/20261117/scores.csv` and `data/20261117/paper_summary.json`. The original server scores and the supplemental run use the same render, structure, and alignment scoring settings. The table generator checks these settings, the exact prompt matches, and the score journals before merging.
- Recompute the tables and score snapshot with `python scripts/update_comparison_20261117.py ORIGINAL_PACKAGE SUPPLEMENT_PACKAGE` using SciPy. Pass the roots of the archived November 16 package and the November 17 supplemental package. The import validates source IDs before normalizing project-owned labels and sample IDs to BrickForma. Run `python scripts/render_comparison_figures.py` with NumPy and Matplotlib to regenerate the four vector charts.
- The untuned-backbone comparison uses the original Qwen3-1.7B run and its scoreability report. `data/untuned_qwen_260.csv` pairs all 260 prompts with raw BrickForma. It flags 180 outputs assigned zero for VQAScore, PE, and SigLIP2 and preserves the measured base alignment scores for the other 80. The file-order invalid-placement ratio is reported on the 80 scorable pairs, with blank base ratios for outputs that could not be scored.
- The 260-prompt generation report records a local merge of [the official BrickGPT LoRA adapter](https://huggingface.co/AvaLovelace/BrickGPT/blob/main/adapter_config.json) with Llama-3.2-1B-Instruct. The runner supports PEFT merge and premerged loading. A separate checkpoint-merge log was unavailable.
- The archived 260-prompt BrickGPT runner traces to [GitHub commit 9c53c7c](https://github.com/AvaLovelace1/BrickGPT/commit/9c53c7cb65f9de0df89562cc74b2d2e270fbcab4). The [BrickNet GitHub reference snapshot](https://github.com/kulits/BrickNet/commit/283faf73063d3af4eb378b624df68dec683e4695) is a code reference. The delivered BrickNet exports and the other 265 BrickGPT exports lack an exact generation-code commit. The collision-scoring dependency is the [bricknet 0.1.0 wheel](https://pypi.org/project/bricknet/0.1.0/#files).
- Dataset references are the [StableText2Brick data upload](https://huggingface.co/datasets/AvaLovelace/StableText2Brick/commit/1dcf90458f913f9dad12d7c74924520d4357f3f6) and the [BrickNet gated split documentation](https://github.com/kulits/BrickNet/blob/283faf73063d3af4eb378b624df68dec683e4695/DATA.md). The public BrickNet adapter revisions are [PT 0f75d5e5](https://huggingface.co/kulits/BrickNet-1.7B-PT/tree/0f75d5e5922234f129a3bb42307c14c685f098f2) and [SFT 3fe7f4c1](https://huggingface.co/kulits/BrickNet-1.7B-SFT/tree/3fe7f4c1eef21955838a0c5222c0c469b4baf644).
- The level plot reproduces the L1-L5 panel layout in the local 525-prompt web report with English labels and the BrickForma name.
- The historical 110-pair repair evaluation and geometry audit have their own subsections and denominators. The 525-prompt structure diagnostic includes a recovery procedure and partially overlaps with the candidate pool for the earlier 114-prompt comparison. The old score snapshot is stored in `data/level_inputs/scores.csv`.

## Review follow-up

The abstract and introduction now describe the observed pipeline-level evidence, and the introduction distinguishes the 80,000 source models from the 79,301 passing layouts. The paper title is retained for author review. Figure 1, Figure 2, and the body use conversion and refinement terminology.

Historical totals for the refined release, integrated preview, exact hash index, and the 160-model sample were checked against their corresponding records. The historical category chart was checked against the three release summaries at the precision of the plotted image. The historical comparison tables contain missing results and literature entries without a common protocol. The draft retains those tables for author review.

## Build and upload

- Entry point is `main.tex`, using the AAAI-27 anonymous style. Compile with pdfLaTeX via `latexmk -pdf main.tex`. The included figure PDFs support a direct build. Use `scripts/build.ps1` to rebuild both standalone TikZ figures and the manuscript locally.
- `V2.2.zip` contains the reorganized project with `main.tex` at the ZIP root. Select `main.tex` as the main document and use pdfLaTeX.
- Open `main.pdf` for the current compiled paper. It has 18 US Letter pages. The last figure in the main paper and the start of the references are on page 7.

## Training manifest check

The release reports count 79,301 geometrically passing models, which yields 396,505 English records at five per model. Training logs record 396,610 caption--placement pairs. The two counts are presented separately pending reconciliation against the training manifest.
