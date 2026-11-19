Reconstruction audit and matched qualitative comparison (2026-11-15)

Source snapshot: BuShiGeMenn/BrickMore @ dfe1c94fc86b722247ed5c8208011313f535c5ec
Archive: Deploy/brickmore-three-models-four-scores-20261110.tar.gz
SHA256: 1ff8858172a9a855ba4cf98be06b88dcebe0d2301979ca33a6b5020aa1dcb575
The downloaded archive was checked against its repository .sha256 file. All 462
canonical assemblies and 462 original assets were checked against their manifest.
The manuscript package includes the 234 BrickMore canonical assemblies (gzip,
original decompressed bytes), sufficient for offline recomputation of the audit.
The original 46 MB archive is not needed by Overleaf and is not redistributed here.

Inputs relative to repository root:
- Results/three_model_comparison_20261111/intake/Results/comparison_full/selected_manifest.jsonl
- Results/three_model_comparison_20261111/intake/Results/comparison_full/structure.jsonl
- brickmore48_eval_630/manifests/manifest_w0.json (225 rows)
- brickmore48_eval_630/manifests/manifest_w1.json (250 rows)
- brickmore48_eval_630/manifests/manifest_w2.json (50 rows)
- BrickNet_BrickGPT_Compirasion/BrickMore_汇总交付_20261107/资料与记录/collab_verified.json

Recompute: python3 scripts/audit_geometric_reconstruction.py (standard library).
Outputs: summary.json, per_model.json, paired_results.json/.csv,
log_coverage.json, and tables/reconstruction_geometry.tex.
Two implementations of the stud-contact graph are cross-checked: adjacent-layer
voxel ownership and pairwise rectangle intersection. All 234 assemblies conform
to the supported upright rectangular-brick library and a common 20/24-LDU grid
within tolerance 0.0005 grid cells; maximum observed residual is 0.00000381.
Body-cell overlap presence agrees with the existing collision journal for all
220 paired exports, although overlap-cell counts and P_inv are different metrics.

Results for 110 main-comparison raw/retiled pairs:
- Single stud-connected component: 18/110 -> 110/110.
- Mean stud components: 4.290909... -> 1.0.
- No body-cell overlaps: 100/110 -> 110/110.
- Occupied voxel unions equal after independent translation: 110/110.
- Four raw-only primary outputs (bottle-L2V4, chair-L2V5, guitar-L3V1,
  sofa-L2V3) are excluded from paired statistics; each is connected and overlap-free.

The voxel equality compares exported unions after translating their minimum
occupied x/z and lowest base to a common origin. It does not compare every run
against an archived solver target. Original origins and deltas are retained in
the detailed results, including small floating/export translation offsets.
No rotations, scaling, cell deletion or shape changes are used in this comparison.

Log coverage and unavailable evidence:
Only 31/110 pairs strictly match the 525-row historical batch by ID, exact prompt,
raw part count and retiled part count. This is metadata matching, not a hash-based
run lineage. Their budget tiers are 12s:19, 60s:8, 180s:2, 600s:2. These tiers are
not observed solver times. Other candidate batches and collab metadata cannot be
pooled to create a success-rate denominator for the selected 114 prompts.
Still needed for full pipeline statistics:
1. Per-attempt run IDs, failure/timeout status and reseed/retry records covering
   every selected prompt and all candidates considered before selection.
2. Solver-only wall-clock times, timeout budgets, solver status and target hashes.
3. Original post-filtering solver voxel targets for each matched reconstruction.
Until those are available, no all-attempt success rate, mean solver latency,
retry distribution or exact original-target coverage rate is reported.
Stud connectivity and overlap-free voxel geometry do not establish mechanical
stability, clutch strength, or a feasible assembly sequence.

Qualitative comparison:
See data/qualitative/selection.json and case_manifest.json. Four prompts are taken
verbatim from the main manifest: chair/car L1 and bench/camera L2. All three
systems use the primary output for that prompt. All 96 original archived images
(12 outputs x 8 views) are retained and SHA256 checked; the paper displays fixed
views 45 and 225 degrees at elevation 25, not the metric-maximizing views. Uniform
yellow rendering does not test color fidelity. Chair/bench favor BrickForma on
VQAScore; car/camera retain counterexamples favoring BrickNet. Selection is
illustrative, not a success-rate estimate, and visual superiority is not inferred
solely from a score. No model inference, new scoring or image synthesis was run.
The figure's prompt text, panel ordering and caption are editable native LaTeX.
Regenerate with python3 scripts/build_qualitative_comparison.py (Pillow needed for
the optional PNG preview; verified cached images make reruns offline).
