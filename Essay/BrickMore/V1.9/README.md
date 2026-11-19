# BrickForma V1.9 — Xiao workshop revision

V1.9 is an editable AAAI-27 manuscript based on the user-supplied Xiao workshop draft and the V1.8 repository manuscript. The V1.6 English figure assets supply Figures 1 and 2 and the appendix illustrations.

## November 16 experiment update

- The main comparison uses the 265 matched Group B prompts (53 per description level). All 265 evaluated BrickForma inputs are raw outputs with Q8_0 weights. Group A is an appendix comparison between BrickGPT and BrickNet on 260 matched prompts. The completed run has four scores for each of 1,315 exports and rendered eight views per export.
- The aggregate and L1–L5 tables were recalculated from the delivered report. BrickForma leads the aggregate VQAScore, PE, and SigLIP2 means. BrickGPT leads L1 VQAScore and has the lowest mean invalid-placement ratio. The Xiao introduction's `by %` placeholder now reports the 16.5% relative increase in aggregate VQAScore over BrickGPT, computed from the unrounded Group B means.
- Figure 3 keeps the matched-prompt layout and uses archived Group B renders for B22_L1, B19_L1, B06_L2, and B17_L2. The caption identifies the highest VQAScore in each case. The earlier Xiao Figure 3 remains under `figures/matched_short_prompts.png` as a local reference.
- Recomputed the Group B paired sign and Wilcoxon tests with Holm correction and audited the PE and SigLIP2 truncation flags. The 110-pair repair analysis and the 525-prompt geometry diagnosis retain their earlier cohorts and results.
- Source: `BrickMore_Comparision/BrickMoreComparison_20261116/BrickMoreComparison_20261116/Results/comparison_full`. The table/gallery generator is `scripts/update_comparison_20261116.py`. Run it with that `comparison_full` directory as the argument, using Python with Pillow and SciPy. It checks pairing, run completeness, and score agreement against the report and per-view records.
- The score snapshot and analysis are in `stats/20261116/scores.csv` and `stats/20261116/paper_summary.json`. The older `stats/scores.csv` and companion analyses belong to the earlier 114-prompt run.

## Xiao revision record

- The title and narrative follow the Xiao PDF. The abstract and introduction were initially transcribed from Xiao. The November 16 update replaces the result statements in both sections with the new cohort's findings.
- The body follows the two questions in the introduction. It explains parametric program authoring and voxel-to-brick conversion, then LoRA fine-tuning and exact-cover reconstruction. The evaluation leads with the five description levels before the aggregate comparison and geometry analysis.
- The former BrickForma-only gallery from the earlier comparison is included in the appendix.
- The 110-pair export audit is transcribed from the Xiao PDF, Section 5.5 and Table 6. It compares the occupied voxel unions after translation normalization and uses adjacent-layer footprint overlap for stud connectivity. This revision did not rerun the underlying export audit.
- Appendix C documents the 45 human-selected cases and 69 later cases for the earlier comparison, alongside the new cohort settings. Algorithm 1 retains the V1.8 early return for a valid connected raw draft.
- The two spatial-reasoning references added by Xiao use the [AAAI proceedings record](https://ojs.aaai.org/index.php/AAAI/article/view/38364) and the [ICLR proceedings record](https://proceedings.iclr.cc/paper_files/paper/2026/hash/f030c22135eb94ede7043a39878e1842-Abstract-Conference.html).

## Build and upload

- Main entry point: `main.tex`. The paper uses the official AAAI-27 anonymous submission style and pdfLaTeX. Build locally with `latexmk -pdf main.tex`. The included figure PDFs allow compilation without running a figure-generation step.
- Edit `sections/xiao_abstract.tex` and `sections/xiao_introduction.tex` for the two imported sections. Other body text is in `sections/method.tex` and `sections/evaluation.tex`.
- `BrickForma_V1.9_Overleaf.zip` contains the compile dependencies at the project root, editable TikZ sources for Figures 1 and 2, and English figure assets. Set the main document to `main.tex` and the compiler to pdfLaTeX.

The compiled PDF has 16 pages on US Letter. The conclusion is on page 6, Algorithm 1 appears on page 7 before the references, and the matched gallery appears on page 5. Figure 1 uses the standard AAAI double-column float and appears on page 2.

## Items to confirm before submission

- The manuscript keeps the recorded 396,610 English caption/placement pairs. The release count of 79,301 passing models yields 396,505 records at five per model, a difference of 105. Reconcile the training manifest before changing these figures.
- The main results describe the delivered Group B cohort. The earlier matched export audit and 525-prompt diagnostic cohort use different denominators. The diagnostic cohort includes recovery attempts and partly overlaps with the candidate pool for the earlier 114-prompt comparison.
