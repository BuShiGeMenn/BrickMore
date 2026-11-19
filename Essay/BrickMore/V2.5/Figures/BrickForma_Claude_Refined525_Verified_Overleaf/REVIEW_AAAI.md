# AAAI Review — "BrickForma: Crystallizing LLM Geometric Knowledge into Small Models for Text-to-Brick Assembly"

## Summary

The paper studies Text-to-Brick: turning a natural-language description into a set of LEGO brick placements that form one stud-connected assembly. BrickForma has three parts:

1. **Data.** A frontier LLM (GPT-6.1 Sol) helps write parametric generator programs for 21 categories × 40 structural families. The programs produce 80,000 voxel shapes on a 48³ grid, each with five captions (L1–L5) that add more detail at each level.
2. **Conversion.** The shapes are tiled into bricks layer by layer, with MRV, beam-search and MILP fallbacks plus local voxel edits. 79,301 shapes pass the dataset-level geometry checks.
3. **Model.** Qwen3-1.7B is LoRA-fine-tuned to emit absolute brick placements. At inference, an optional MILP step (exact cover plus a single-commodity flow) rebuilds the voxel union of the raw draft as a single stud-connected assembly.

On 525 prompts (21 categories × 5 levels), raw BrickForma outputs get higher mean VQAScore, PE and SigLIP2 than BrickGPT and BrickNet at every level. Its invalid-placement ratio is 0.79%, against 0.00% for BrickGPT and 18.42% for BrickNet.

## Strengths

- **S1. Useful problem and framing.** "Can a language model *construct*, not just answer" is a good question. LEGO gives checkable constraints: coverage, bounds and stud connectivity.
- **S2. Data without curated assets.** Using LLM-written generator programs avoids ShapeNet meshes and hand-built LDraw models. It also gives captions at several levels of detail that are grounded in the same shape plan. The level-wise evaluation (Table 4, Fig. 18) is a good design choice.
- **S3. Clean split of work at inference.** The LM proposes the shape and the MILP enforces stud connectivity. The single-commodity flow formulation (App. C) is standard but suits this use, and the independent audit after solving is good practice.
- **S4. Good reporting habits.** Paired sign and Wilcoxon tests with Holm correction, pinned baseline commits, adapter revisions and software versions, honest notes on truncation, and an explicit "Evaluation Boundaries" section.

## Weaknesses

### W1. The benchmark is in-distribution for BrickForma and out-of-distribution for the baselines (major)
The 525 test prompts come from BrickForma's own caption generator: the same 21 categories and the same L1–L5 templates. L4 and L5 even contain templated ratio phrases such as "Overall width is 1.15 times depth". BrickGPT was trained on StableText2Brick and BrickNet on its own corpus, so neither has seen this prompt style. Under these conditions the alignment lead in Tables 3 and 4 is expected and says little about general Text-to-Brick ability.
- The paper never states that the 525 prompts come from held-out *shapes*. "Zero overlap against the training set" is stated only for the 260 supplemental prompts.
- The 9:1 split is at the model level. Each family has about 95 instances, so test shapes almost certainly have near-twins from the same family in training. There is no analysis of nearest-neighbour or memorization.
- There are no out-of-distribution prompts: no unseen categories, no free-form human prompts, and none of the baselines' own benchmark prompts. Running BrickForma on BrickGPT's StableText2Brick test prompts would be the obvious symmetric check.

### W2. The alignment metrics are near zero, and the measurements don't match the published numbers (major)
- Mean VQAScore is 0.087 for BrickForma and 0.067 for BrickGPT, so the VLM answers "No" almost every time. At L4 and L5 every system is below 0.02.
- The headline "+30.0% VQAScore" is a relative gain on a very small absolute value.
- Table 16 lists a literature VQAScore of 0.593 for BrickNet, but the paper measures 0.0201, about 30× lower. A gap that large points to a problem in the rendering or scoring pipeline (uniform yellow material, orthographic views, 25° elevation, max over views), not to a property of the systems. The authors should reproduce at least one published baseline number under their pipeline.
- The collapse from L3 to L4 (0.118 → 0.019 for BrickForma) happens for every system. It is most likely a metric artifact: L4 adds numeric ratios and L5 names colors (e.g. "red, tan, brown") that a uniform yellow render can never satisfy. As designed, the L4/L5 results don't measure what the paper claims.
- PE truncates 121 prompts and SigLIP2 truncates 209, so the long levels are partly scored on prefixes.
- There is no human evaluation and no simpler semantic check, such as category recognition from the render. Fig. 3 does not support the quantitative claims well: the BrickForma "hatchback" and "camera" are hard to recognise.

### W3. The headline comparison uses unbuildable raw outputs (major)
The main table scores raw BrickForma drafts, yet by the paper's own diagnostics only 46 of 525 raw layouts (8.8%) form a single stud-connected component. The median failing draft has 5 components, with up to 33.
- BrickGPT outputs are physically validated, so its alignment scores carry the cost of buildability. Raw BrickForma outputs are mostly loose, unconnected brick piles.
- Pinv measures only collisions, not connectivity or stability, so it hides this difference. Table 3 needs a connectivity column (single-component %) and ideally a stability column.
- Refinement is the step that makes outputs buildable, but it is evaluated only on an earlier set of 110 pairs (Tables 5 and 6). That set has different provenance and partly human-selected outputs (see W5).
- Refinement more than doubles the brick count (179 → 421) and lowers SigLIP2. No main-benchmark numbers are reported for refined outputs.

### W4. The ablations needed for the central claim are missing (major)
The title and framing are about crystallizing LLM geometric knowledge, but nothing isolates the contribution of the LLM.
- **No comparison with hand-written procedural generators.** The authors acknowledge this as future work, but it is the core claim.
- **No teacher baseline.** There is no test of GPT-6.1 Sol, or another strong LLM, writing a generator or a brick list directly for each test prompt. Without it we can't tell how much is "crystallized" or what the small model loses.
- **Data and backbone are confounded.** BrickGPT uses LLaMA-3.2-1B, BrickForma uses Qwen3-1.7B, and the two differ in grid size, brick library and LoRA settings (Table 9). Training BrickGPT's recipe on BrickForma data, or BrickForma's model on StableText2Brick, would separate these effects.
- **No ablation over caption levels** (e.g. train on L1 only vs. on all levels), even though the multi-level dataset is listed as a contribution.
- The untuned-Qwen comparison is close to trivial: 178 of 260 outputs contain no placements at all.

### W5. Evaluation provenance is mixed and hard to audit (major)
- The 525 outputs combine 265 earlier **Q8_0-quantized** exports, whose decoding flags were not logged and which have no completion or geometry flags, with 260 bf16 exports. Among those 260, 8 are incomplete and 96 fail the geometry check.
- "265 other BrickGPT exports and the BrickNet exports lack a recorded generation-code commit."
- It is unclear how BrickNet samples were obtained for the 525 prompts. In the 114-prompt study BrickNet got up to 30 attempts and BrickGPT one.
- The 114-prompt study that supplies Tables 5 and 6 used **human selection**: 45 outputs were the best of six phrasings, and others came from "colleague", "review_59" and "regeneration" rounds. Results from cherry-picked sets should not appear in the main text as evidence for refinement.
- Per-batch results (265 vs. 260) are needed to show that conclusions hold within each homogeneous subset.

### W6. The training targets are not "physically valid" in the sense the abstract suggests (moderate)
The abstract says voxel models are converted "into physically valid brick targets". However:
- The release check allows several independently grounded components, so it is weaker than the single-component rule used at inference.
- Local refinement **adds 228,582 voxels** to the source shapes, so targets may no longer match captions derived from the pre-edit plan. Is caption–target consistency checked?
- Table 12 and Fig. 8 show that only **220 of 79,298** refined models pass the compression-only gravity equilibrium screen, and only 128 pass with all layer prefixes. Most of the rest need clutch tension, and the paper notes that clutch capacity is uncalibrated.

"Geometrically checked" is accurate. "Physically valid" overclaims.

### W7. Novelty and related work (moderate)
Each component has substantial prior work that is not cited:
- LLM-written procedural or programmatic 3D generation and synthetic data, e.g. 3D-GPT and Infinigen-style procedural generators.
- Shape programs, e.g. ShapeAssembly.
- Text- and LLM-to-CAD code generation.
- Classical LEGO-ization with connectivity optimisation, e.g. Testuz et al. 2013 and Luo et al. 2015 ("Legolization").

The related work section has about 12 references and two paragraphs, which is thin for AAAI. The exact-cover plus connectivity MILP should be placed against the legolization literature, and the novelty of LLM-authored generators against the program-synthesis-for-data literature.

### W8. Presentation (moderate)
The manuscript often reads like an internal project report rather than a paper:
- It uses terms such as "historical", "supplied reference", "release reports", "colleague success set", "review_59", "11-07 delivery manifest", "car_trials", "Piano B" and "revised batch-B piano release".
- Section 3.3 spends a paragraph on 79,298 − 1,902 + 1,905.
- Appendix D has tables that are mostly dashes (Tables 14–16) and figures labelled "historical". These should be removed or consolidated.
- Several sample counts appear without a clear reconciliation: 80,000, 79,301, 400,000, 396,610 and 396,505. The 105-sample "snapshot offset" means the training set includes samples that are not in the stated release, which raises a train/test leakage question.
- (Q2) is posed in the introduction but never explicitly answered.
- Typos and inconsistencies: "BrickFormain the accompanying …" on p. 3 has a missing space or parenthesis; Fig. 2 says "ChatGPT 6.1 Sol" while the text says "GPT-6.1 Sol"; "a 8,192-token" should be "an 8,192-token"; the checkpoint is named "BrickGPT-Qwen3-1.7B-BrickMore-48" but the system is called BrickForma.
- The Fig. 1 caption doesn't say whether the BrickForma outputs shown are raw or refined. Fig. 3 shows only raw outputs, which look clearly blocky.

## Questions for the Authors

1. Are all 525 benchmark prompts captions of shapes held out from training? How close are their nearest training shapes (e.g. voxel IoU to the nearest training shape)?
2. What are the alignment scores on BrickGPT's own test prompts, and on free-form human-written prompts or unseen categories?
3. Why is BrickNet's measured VQAScore (0.020) so far below the literature value (0.593)? Can you reproduce any published baseline number with your pipeline?
4. Please report Table 3 for **refined** BrickForma outputs on all 525 prompts, with single-component % and a stability rate for every system.
5. What do you get if GPT-6.1 Sol answers the test prompts directly (as code or as brick lists)? And what if the generator programs are written by hand?
6. How are captions kept consistent with targets after local refinement adds voxels?
7. How were the BrickNet outputs for the 525 prompts generated: number of attempts, and any filtering?
8. Do the conclusions hold separately for the Q8_0 subset (265) and the bf16 subset (260)?
9. Will the generator programs, dataset and checkpoint be released?

## Ratings

- **Originality:** Medium. Applying LLM-authored procedural data to brick assembly is new, but the parts are known.
- **Technical quality:** Low to medium. The pipeline engineering is solid. The evaluation design (W1–W3, W5) does not support the claims.
- **Clarity:** Low to medium (W8).
- **Significance:** Medium if the claims held. The idea of data without curated assets is attractive.
- **Reproducibility:** Medium. Versions are pinned well, but outputs come from mixed batches, some flags are unlogged, and the data is generated with a proprietary LLM.

**Overall recommendation:** Weak Reject (4/10)
**Reviewer confidence:** 4/5. I'm familiar with text-to-3D, LLM program synthesis and brick-assembly generation.

**Justification:** The direction is promising and the engineering is substantial. But the main empirical claim (best alignment at every level) rests on prompts from the method's own training distribution. The metric values are near zero and don't match the literature, and the outputs scored are mostly not connected. The ablations that would support the "crystallization" thesis are missing. A version with out-of-distribution or human-written prompts, a validated scoring pipeline, refined-output results with connectivity and stability columns, and a hand-written-generator or teacher ablation could be a strong paper.

---

## Author-facing: fixes ranked by impact before submission

1. **Add an evaluation on prompts you didn't write.** Use BrickGPT's StableText2Brick test prompts, plus about 100 free-form human prompts. This addresses W1 directly.
2. **Validate or replace the scoring pipeline.** Reproduce one published baseline VQAScore. Drop color phrases from L5 for scoring, or render with colors. Add a small human study (2-AFC preference or category recognition) on about 100 prompts.
3. **Put refined results and connectivity in the main table.** Report Pinv, single-component %, stability %, VQAScore, PE and SigLIP2 for raw and refined BrickForma.
4. **Run one cheap ablation on generator authorship.** For example, hand-write generators for 3–5 categories, or train on a subset of LLM-authored families, at matched data size.
5. **Rewrite Section 3.3 and the appendices** to remove release-history wording ("historical", "piano B", "colleague", manifests) and the empty historical tables. Present one clean set of dataset numbers.
6. **Tone down the claims.** Change "physically valid" to "geometrically checked", and report absolute differences next to "+30%".
7. **Expand related work** with legolization, shape programs, LLM-procedural 3D and LLM-to-CAD.
8. **Fix the typos** listed in W8.
