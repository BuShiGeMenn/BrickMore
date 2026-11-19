from pathlib import Path
import hashlib
import json
import shutil
import zipfile

live = Path("D:/BrickMore/Essay/BrickMore/V2.2")
job = Path(__file__).resolve().parent
stage = job / "source"
stage.mkdir(exist_ok=False)
with zipfile.ZipFile(live / "V2.2.zip") as bundle:
    names = [n for n in bundle.namelist() if not n.endswith('/')]
snapshot = {}
for name in names + ["V2.2.zip", "main.pdf"]:
    data = (live / name).read_bytes()
    snapshot[name] = hashlib.sha256(data).hexdigest()
    if name in names:
        target = stage / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
(job / "snapshot.json").write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

def edits(name, replacements):
    path = stage / name
    original = path.read_bytes()
    text = original.decode("utf-8").replace("\r\n", "\n")
    for old, new in replacements:
        assert text.count(old) == 1, (name, old, text.count(old))
        text = text.replace(old, new)
    if b"\r\n" in original:
        text = text.replace("\n", "\r\n")
    path.write_bytes(text.encode("utf-8"))

edits("abs-xiao.tex", [
    ("a framework that crystallizes the geometric knowledge of large language models into a compact model for this task",
     "a framework that builds training data for a compact model using LLM-assisted parametric programs"),
    ("These results suggest that executable programs and checked geometric data are an effective route for carrying spatial knowledge from large models into small models without the need of human-verified input for training.",
     "These results support using executable generators and geometric checks to train compact text-to-brick models.")
])
edits("intro-xiao.tex", [
    ("Large models hold broad knowledge of object proportions and part structure, but that knowledge is implicit and their outputs carry no structural guarantee. Whether it can be transferred to a compact model in a form that can be inspected and checked has received limited attention.",
     "Can LLM-assisted programs encode object proportions and part structure in a form that can be inspected and used to train a compact model?"),
    (r"We present BrickForma, which addresses both questions by \emph{crystallizing} large-model geometric knowledge into a small model through executable programs rather than through the large model's direct outputs.",
     "We present BrickForma, which uses executable programs to generate training examples for a compact text-to-brick model."),
    ("In this form, what a large model knows about a category becomes explicit and executable: each program fixes the structure of an object family and exposes its geometric degrees of freedom as parameters, so every generated shape is exact by construction.",
     "Each program specifies the structure of an object family and exposes its geometric degrees of freedom as parameters."),
    ("to shared geometry, so that a model trained on them learns to supply at the shortest level the geometric details that the longest level states outright.",
     "to shared geometry, providing supervision for prompts with different amounts of geometric detail."),
    ("A connected voxel volume can be tiled by pieces that touch side by side without connecting through studs. Our conversion pipeline combines same-color tiling,",
     "Pieces can cover a connected voxel volume and touch side by side without forming stud connections. Our conversion pipeline combines same-color brick placement,"),
    (" The knowledge transfer therefore passes through three inspectable stages, from programs to checked brick layouts to a 1.7B-parameter generator, and the small model never trains on an unverified large-model output.", ""),
    ("% TODO (optional, strengthens the framing): report the fine-tuned model's raw placements\n% before refinement, and the un-tuned Qwen3-1.7B, to isolate what crystallization contributes.\n", ""),
    (r"""\textbf{Crystallizing large-model geometric knowledge into a small model 
without human-verified data.}
We propose a data generation pipeline for transferring geometric and 
spatial knowledge from large language models to a compact model: the 
large model's knowledge is externalized as executable parametric programs, 
converted into geometrically validated training data, and distilled into 
a 1.7B-parameter model without relying on human verification. """,
     r"""\textbf{LLM-assisted construction of training data for a compact model.}
We use executable parametric programs to generate voxel shapes and descriptions, convert the shapes into geometrically checked brick layouts, and fine-tune a 1.7B-parameter model on the resulting caption--placement pairs."""),
    ("source voxel models. Each voxel model is paired with five levels of textual description \nand geometrically validated brick targets. We fine-tuned Qwen3-1.7B on this dataset and carried out level-wise evaluation ",
     "source voxel models with five description levels each. In the integrated release, 79,301 of the 80,000 source models yielded brick layouts that passed the geometric checks. We fine-tuned Qwen3-1.7B on caption--placement pairs and carried out level-wise evaluation "),
])
edits("figure_tex/teaser.tex", [
    ("the LEGO assembly tiled from it", "the resulting LEGO assembly")
])
edits("figure_tex/figure2_content.tex", [
    ("5/Tiling + refinement", "5/Brick conversion"),
    ("% 5. Tiling and repair: actual before/after geometry.", "% 5. Voxel-to-brick conversion and local refinement."),
    (r"{Text $\rightarrow$ bricks + repair}", r"{Text $\rightarrow$ bricks + refinement}")
])
edits("main.tex", [
    ("The shapes are deduplicated, tiled, repaired, and checked before export for fine-tuning.",
     "After deduplication, the shapes are converted to bricks, refined, and checked before export."),
    ("The geometry is shared by all five levels, so the same target provides supervision for both concise and detailed requests.",
     "All five levels describe the same source geometry."),
    ("The conversion tiles each layer with same-color rectangular footprints",
     "The conversion covers each layer with same-color rectangular bricks"),
    ("It tries seeds 42, 104, and 2026, keeping the first completed draft that passes the geometry validator or the completed draft with the fewest format, library, bounds, and overlap errors.",
     "It tries seeds 42, 104, and 2026. Completion means reaching an end-of-sequence token. It keeps the first completed draft that passes the geometry validator or the completed draft with the fewest reported errors."),
    (r"We call the drafts \emph{raw} and the accepted refined layouts \emph{refined}.",
     r"We call the drafts \emph{raw} and the accepted layouts \emph{refined}. Appendix~\ref{app:eval} details the exact-cover constraints."),
    ("All BrickForma exports are raw generations before geometric refinement.",
     "We retain all delivered raw BrickForma exports, including incomplete drafts. Appendix~\\ref{app:eval} distinguishes these exports from the refinement diagnostic."),
    ("The program-based transfer combines generator design, geometric validation, and supervised fine-tuning. Isolating the contribution of large-model authoring would require an alternative generator evaluated under a matched training budget.",
     "The experiments assess the combined data-construction and fine-tuning pipeline. Isolating the effect of LLM assistance would require a comparison with an alternative generator under a matched training budget."),
    ("Historical results on a uniform 160-model sample. Version and numerical labels require verification.",
     "Geometric pass counts for the original rules, Q3, and two Q4 variants on the same 160-model sample (seed 38177). The Q4 rounds reuse this sample for tuning."),
    (r"""The evaluation covers 1,575 exports and 12,600 rendered views. All four metrics are available for every export. We score every delivered raw BrickForma sequence, including drafts with incomplete generation or failed source geometry checks. Three supplied GLB previews contain only a prefix of the corresponding sequence. Scoring uses the delivered sequence in each case. BrickGPT uses a $20^3$ world and seed 42, with recorded regeneration budgets of 8 or 100 across its delivered exports.""",
     r"""The 525 matched prompts combine 265 previously delivered BrickForma Q8\_0 exports with 260 supplemental exports. We score the single raw export supplied for each prompt. This protocol measures the delivered drafts without filtering on completion or geometry, rerunning Algorithm~\ref{alg:inference-refinement}, or choosing a candidate by its scores. The supplemental records flag 8 incomplete generations and 96 failures of the source geometry check out of 260, with potential overlap. The 265 earlier exports lack corresponding completion and geometry flags. We score all 1,575 LDraw exports on all four metrics, using 12,600 rendered views for alignment. Three supplied GLB previews contain only a prefix, so we render from the delivered LDraw sequences in all cases. BrickGPT uses a $20^3$ world and seed 42, with recorded regeneration budgets of 8 or 100."""),
    (r"""The archived 260-prompt BrickGPT runner is based on GitHub commit \texttt{9c53c7c} of \url{https://github.com/AvaLovelace1/BrickGPT} and uses the official merged \texttt{AvaLovelace/BrickGPT} checkpoint.""",
     r"""The archived 260-prompt BrickGPT runner is based on GitHub commit \texttt{9c53c7c} of \url{https://github.com/AvaLovelace1/BrickGPT}. The generation report records a local checkpoint combining \texttt{meta-llama/Llama-3.2-1B-Instruct} and the public \texttt{AvaLovelace/BrickGPT} LoRA adapter. The runner can load a premerged checkpoint or merge those weights through PEFT's \texttt{merge\_and\_unload}. The report identifies the merged checkpoint used, with no separate merge log."""),
    (r"\paragraph{Diagnostic cohort.}",
     r"""\paragraph{Inference refinement.}
For the clipped voxel union $C$, let $\mathcal{B}(v)$ index candidate placements from the oriented footprint library that cover $v$ and stay entirely within $C$. With binary placement variables $x_b$, exact coverage requires $\sum_{b\in\mathcal{B}(v)}x_b=1$ for each $v\in C$. This preserves the union and excludes overlaps. A flow constraint connects the selected placements through stud contacts, defined by footprint overlap on adjacent layers. SciPy's HiGHS MILP interface uses the time tiers in Algorithm~\ref{alg:inference-refinement}. A feasible cover must also pass the independent placement, coverage, and connectivity audit. The run records specify the time tiers and acceptance tests. They do not record the solver's objective coefficients or gap tolerance. Contact-based self-weight screening uses a separate LP (Appendix~\ref{app:dataset}).

\paragraph{Diagnostic cohort.}"""),
    (r"""Generation used seeds 42, 104, and 2026 in that order, moving to the next seed when a draft was incomplete or failed the geometry validator, then applied the 12--60--180\,s MILP ladder (the default loop of Algorithm~\ref{alg:inference-refinement}); raw drafts that already formed a single stud-connected component were kept unchanged.""",
     r"""Algorithm~\ref{alg:inference-refinement} describes the default candidate-selection and refinement rules. The diagnostic manifests record either a refinement tier or a raw layout kept unchanged."""),
    ("Dashes indicate missing entries in the supplied source.",
     "Dashes indicate values unavailable in the supplied historical records.")
])
edits("archive/historical_tables.tex", [
    ("80,000 unique; 0 A/B duplicates", "80,000 unique across both shards"),
    ("Overlap with historical hashes", "Exact overlap with historical hashes"),
    ("Bricks in full preview", "Bricks in integrated preview"),
    ("Historical dataset statistics transcribed from the supplied reference. The geometry count refers to the old refined release, not the later integrated count. Verify the preview and physical-screening totals against version-matched reports.",
     "Historical dataset statistics. The historical index comparison uses exact occupancy hashes. The geometry and self-weight counts refer to the October 13 refined release. The brick total comes from the integrated preview manifest, which includes the revised piano layouts."),
    ("Historical baseline table in the source reference. These criteria differ, and missing BrickForma-48 entries were marked TODO. This is not the current matched four-metric main table.",
     "Historical baseline table for 114 prompts. The stability and parsing columns use different criteria. The historical record does not report corresponding BrickForma-48 values."),
    ("BrickGPT (114 prompts, historical placeholder)", "BrickGPT (114 historical prompts)"),
    ("BrickNet (114 prompts, historical placeholder)", "BrickNet (114 historical prompts)"),
    ("BrickForma-48 (114 prompts, historical placeholder)", "BrickForma-48 (114 historical prompts)"),
    (r"""Original reference table with literature values and historical placeholders. Literature values use another evaluation set and must not be directly compared with the current 525-prompt results; the precise $P_{\mathrm{inv}}$ definition and direction require checking against the original publication.""",
     r"""Transcribed literature values and unavailable historical scores. The literature entries use separate evaluation sets, and the source does not specify a common definition for $P_{\mathrm{inv}}$."""),
])
edits("README.md", [
    ("its tiled LEGO assembly", "its converted LEGO assembly"),
    ("- The scores and recomputed statistics", """- The 525-prompt matched comparison uses the delivered raw exports. Appendix C distinguishes that protocol from the separate 525-prompt refinement diagnostic and records the supplemental completion and geometry flags. The inference description documents exact coverage, stud-contact connectivity, HiGHS time tiers, and the independent audit. The archived inference package is needed to verify the MILP objective and gap tolerance.
- The scores and recomputed statistics"""),
    ("- The archived 260-prompt BrickGPT runner traces to", """- The 260-prompt generation report records a local merge of [the official BrickGPT LoRA adapter](https://huggingface.co/AvaLovelace/BrickGPT/blob/main/adapter_config.json) with Llama-3.2-1B-Instruct. The runner supports PEFT merge and premerged loading. A separate checkpoint-merge log was unavailable.
- The archived 260-prompt BrickGPT runner traces to"""),
    ("## Build and upload", """## Review follow-up

The abstract and introduction now describe the observed pipeline-level evidence, and the introduction distinguishes the 80,000 source models from the 79,301 passing layouts. The paper title is retained for author review. Figure 1, Figure 2, and the body use conversion and refinement terminology.

Historical totals for the refined release, integrated preview, exact hash index, and the 160-model sample were checked against their corresponding records. The historical category chart has no per-bar data file attached to the figure, and the comparison tables contain missing results and literature entries without a common protocol. These materials remain in the project and in the draft for the author to review.

## Build and upload""")
])

