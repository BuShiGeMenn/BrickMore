# BrickForma LaTeX manuscript (V1.6, AAAI-27 format)

Title: *BrickForma: Text-to-Brick Generation with Voxel-to-Brick Data Construction and Geometric Reconstruction*.
Target: GSR-VLM workshop at AAAI-27 (https://gsr-vlm.org/), long paper (main content <= 7 pages; references and appendices unlimited). Review log: `REVIEW_V1.6.md`. Plan of record: `..\Plan_V1.6\FINAL_PLAN_V1.6.md`.

The method/system is called **BrickForma** from V1.6 on; the dataset/trained-model name **BrickMore-48** is unchanged.

## Files

- `main.tex`: English manuscript in the official AAAI-27 anonymous-submission format (`\usepackage[submission]{aaai2027}`). Author information is a placeholder.
- `aaai2027.sty`, `aaai2027.bst`: unmodified files from the official AAAI-27 Author Kit (https://aaai.org/authorkit27/ -> AuthorKit27.zip, style dated 2026-10-21).
- `references.bib`: bibliography (natbib + aaai2027.bst).
- `figure1.pdf`, `figure2.pdf` (+ `figure_tex/`): rebuilt English Figures 1 and 2, with editable TikZ sources. Standalone PNG previews are in `figures/figure1.png` and `figures/figure2.png`.
- `figures/`: English publication assets use the `_en` suffix. Three numerical charts are vector PDFs. Original raster assets remain locally for provenance. The historical `image18` comparison remains excluded from the manuscript (`\iffalse`).
- `figure2_units/`: the eight independent panels from the earlier design. Unit 1 intentionally remains TBD in this separate design set; the paper uses the completed specification pictogram. Unit 8 has been renamed BrickForma and rebuilt.
- `archive/historical_tables.tex`: transcribed historical tables (appendix; `\input` by `main.tex`).
- `stats/`: paired significance re-analysis (`significance.py`, `significance.json`, `significance_output.txt`) and descriptive robustness tables (`robustness.py`, `robustness.json`, `robustness_output.txt`) computed from the existing `scores.csv`, `pe.jsonl`, `siglip2.jsonl` (copied unchanged).

## Build

Primary build (V1.6): TinyTeX (pdfTeX) + latexmk on the box:

```sh
latexmk -g -pdf -interaction=nonstopmode main.tex
```

Backup: MiKTeX / TeX Live with the same command; Overleaf (pdfLaTeX) as a third option.

To also rebuild the two editable TikZ figures on Windows:

```powershell
.\scripts\build.ps1 -RenderPng
```

The script accepts `-TeXBin '<path to the TeX bin directory>'` for a portable installation and only changes PATH during that invocation. PNG preview rendering requires `pdftoppm`. For the manuscript alone, the supplied figure PDFs are sufficient; no Python or shell escape is required on Overleaf.

The local English-asset generators are `scripts/english_figures.py` (Pillow; translates text regions and relabels model galleries) and `scripts/english_charts.py` (Matplotlib; redraws charts from recorded counts in `figure_data/chart_counts.json`). The raster script uses Arial from Windows Fonts. Original model renders and measured counts are retained; no generation or training experiment was rerun.

Stats (Python 3 with numpy and scipy):

```sh
cd stats && python significance.py scores.csv && python robustness.py
```

## Submission package

Upload only `main.pdf`. If a source zip is needed, include only `main.tex`, `references.bib`, `aaai2027.sty`, `aaai2027.bst`, `archive/historical_tables.tex`, `figure1.pdf`, `figure2.pdf`, and the `figures/*.png` actually referenced. Do not include logs, `*.bak*`, `REVIEW_*.md`, `stats/*.jsonl`, or older zips.

For **Overleaf editing**, use `BrickForma_V1.6_Overleaf.zip`. Its root contains `main.tex`; choose **pdfLaTeX** and a current TeX Live version. It includes the compiled figure assets, editable Figure 1/2 sources and their render assets, bibliography, official style files, and this README. The PDF charts in `figures/` are required alongside the PNGs. The package is an editing bundle, not a claim that a particular conference submission form accepts source ZIPs.

To replace an existing Overleaf project, first download a backup of that project, remove its old files, then upload the **contents** of this ZIP at the project root. Merely uploading over the old files can leave obsolete entry points and assets. Set `main.tex` as Main document and recompile from scratch. No Overleaf upload or remote project deletion was performed here.

The local `stats/`, `REVIEW_V1.6.md`, older nested projects/ZIPs and raw provenance files are deliberately absent from this clean package. Keep those local records for audit; do not use an older nested project as the current manuscript.

## Formatting and English-figure revision (2026-11-15)

The user confirmed that GrokBoT's latest changes are authoritative. This pass preserves the BrickForma title and method name, BrickMore-48 dataset/model name, 525-prompt diagnostics, 114-prompt comparison, significance tests, robustness summaries, candidate-selection disclosure, and recorded training counts. The earlier GrokBoT change log remains in `REVIEW_V1.6.md`; the updates below supersede its notes saying that figures were not rebuilt or still contain Chinese labels.

| Area | Implemented change |
| --- | --- |
| Official format | Verified `aaai2027.sty` and `aaai2027.bst` against the downloaded AAAI-27 Author Kit; kept both byte-for-byte unchanged. Kept letter paper, two columns, anonymous submission mode, native fonts and margins. |
| Captions and tables | Removed bold introductory phrases from the Figure 1/2 captions. Replaced the historical table's 7 pt `scriptsize` with 9 pt `small` and wrapped long cells. Set the diagnostic table across both columns. |
| Figure 1 | Updated the method label to BrickForma; retained the 11-color brick-size legend and separate constructed-data / model-output galleries. Enlarged native labels to at least 9.2 pt before full-width inclusion. |
| Figure 2 | Updated the system name; retained the code pictogram; made L1-L5 five outward arrows around one source model. Shortened labels and separated text baselines so the eight units remain readable. The complete captions remain in the text and independent-panel references. |
| English figures | Translated the contact diagram, conversion/category/sample charts and status/failure plots. Updated historical comparison headers to BrickForma. Enlarged category and generated-model labels. |
| Numerical plots | Rebuilt conversion, physical-status and failure plots as vector PDFs with English labels. Physical-status counts were read from the relaxed/retile release reports; every release sums to 80,000. Data and source-field notes are in `figure_data/chart_counts.json`. |
| Compact gallery | Removed unused margins around the same eight generated models and kept raw/retiled labels. Models were neither replaced nor regenerated. |
| Terminology | Clarified that the library has 20 **oriented footprints**, corresponding to 11 brick sizes up to planar rotation. This explains why the teaser has 11 colors. |
| Algorithm 1 | Added the already-valid raw-layout return branch and made successful return conditional on passing the audit. Defined the audit to include library membership, bounds, no overlap, exact coverage and a single stud component. This aligns the pseudocode with the retained raw outputs described in the diagnostics. |
| Appendix layout | Removed intermediate float barriers that created largely empty pages; retained all appendix content and historical-result qualifications. Figures use normal LaTeX floating rather than margin or font-size tricks. |

## Verification

- Final PDF: **15 letter-sized pages**; main text through Conclusion ends on **page 7**. References begin on page 7; the technical appendices begin on page 8.
- Figure 1 is on page 2, Figure 2 on page 3, and Figure 3 on page 5. The two-column AAAI float rules determine this placement; the teaser is not forcibly inserted under the first-page title.
- pdfLaTeX/BibTeX compilation completed. No overfull boxes, undefined references/citations, or missing-character messages. Fonts are embedded, with no Type 3 fonts. A few non-fatal underfull-line messages remain.
- All final pages were rendered and visually checked, including the English raster labels. Text extraction found no Chinese characters in the compiled PDF. Original Chinese source images remain only as local provenance.
- Machine-readable checks: `build_verification.json`; rerun with `python scripts/verify_pdf.py` after changes (requires pypdf). A clean extracted Overleaf bundle was compiled separately to check its dependency completeness.

## Data items still requiring source confirmation

These are evidence gaps, not formatting problems; the approved measurements were not silently changed.

1. **Training accounting:** 79,301 integrated passing models times five captions gives **396,505**, whereas the recorded training corpus is **396,610** (105 more records, equivalent to 21 complete five-caption groups). Its train/validation counts do sum to 396,610. Reconcile the actual training manifest and release identifier before revising Table 1; the recorded 2,228,044,818 tokens are also retained pending the run log.
2. **Evaluated checkpoint:** the released checkpoint is recorded as step 79,000. The manuscript does not newly assert that all 525 diagnostic and 114 comparison outputs used that checkpoint; that needs generation-run evidence.
3. **Historical figures/tables:** category-level and 160-model charts retain their original numerical evidence and verification qualifications. The 57/160 sample rate is 35.625% exactly; the historical chart prints 35.62% while its table prints 35.63%, reflecting different rounding conventions. Historical placeholder entries and differing acceptance criteria are kept visibly separate from current results.
4. **Authors and physical claims:** author/affiliation placeholders remain hidden by anonymous mode. Geometric connectivity, contact screening and physically tested buildability remain distinct; this formatting pass adds no physical-stability claim.
