# BrickMore V1.6 修订计划（ReviewBot1，R2）

- 计划文件：`D:\BrickMore\Essay\BrickMore\Plan_V1.6\PLAN_RB1_R2.md`
- 由 `PLAN_RB1_R1.md` 修订。**`PLAN_RB1_R0.md` 与 `PLAN_RB1_R1.md` 保持不动。** 本轮答复见 `CRITIQUE_RB1_R2.md`。
- 基稿：`V1.5\main.tex`（2026-11-14 23:36 UTC+8）、`REVIEW_V1.5.md`；对照 `CRITIQUE_RB2_R1.md`、`PLAN_RB2_R1.md` 与项目 `D:\BrickMore`。
- **只做规划。未修改任何论文源文件。**
- 目标：[GSR-VLM](https://gsr-vlm.org/) Topic 5 only。AAAI-27 模板；正文（摘要至结论）≤ 7 页（References 可从第 8 页起）；Algorithm 1 留在正文；不虚构数字/文献；不宣称预训练、RL，或生成器是 VLM。
- 截止：**2026-11-20 19:59（UTC+8）**。建议 **11-19（UTC+8）** 提交。找训练清单的截止点：**11-17 24:00（UTC+8）**。

---

## 仍有分歧（须用户拍板）

| 项 | RB1 立场 | RB2 立场 | 证据 | 用户必须决定 |
|---|---|---|---|---|
| 1. 附录中文历史图（image13–19） | 默认保留（可加 “historical, not used for claims”）；删除须明确同意，用 `\iffalse`、磁盘保留 | 推荐从提交 PDF 移除，C′ 仅作不同意时的备选 | 全部在附录（PDF 第 7–10、13 页，Figure 6–12），正文 +0 页；图内中文与 “require verification” 见 `CRITIQUE_RB1_R2.md` 专题 (d) | **选 A 删除 / C 保持 / C′ 保留并加说明**（或 B 重绘，不推荐赶工） |
| 2. 525 条结构诊断写入方式 | 批准后作为独立几何探针写入：正文一段 + **表默认附录**；不写 additional、不写 114 出自 525、不写“懂体素形状” | 推荐写入正文新小节+表（约 +0.35 页），并在摘要/引言/贡献重复 8.8%；U12 仍写 114 出自这批 | `selected_manifest.jsonl` 的 114 条来自 `BrickMore_汇总交付_20261107`，0 条指向 `eval_630`；caption 与 525 重叠仅 35/114；见专题 (a) | **是否批准写入**；若批准，表放正文还是附录 |
| 3. 标题 | 推荐 B′：*…by Agentic Data Generation and Language-Model Fine-Tuning* | 推荐 A：*…Stud-Connected Brick Assembly from Agentically Generated Voxel Data*；B′ 可接受 | 均不引入虚假主张；A 更强调钉柱连通，B′ 更贴近 Topic 5 用词 | **圈定最终标题字符串**，或保持 `BrickMore` |
| 4. 显著性检验 | 批准后做；符号检验 + Wilcoxon，6 次比较用 Holm；结果放附录；不预填 p 值；不显著则如实写 | 同样做，主报 Holm 校正后的符号检验 | `scores.csv` 114 条可配对；vs BrickGPT 91/0/23 等已复算 | **是否批准写入新 p 值** |
| 5. 评测权重是否即 step-79,000（U10） | 未确认前不写等同 | 同：请用户确认 92d1c595 与下载模型 / step-79,000 的关系 | `eval_630\README.md` 写 `92d1c595`；`downloads\...\model.sha256` 为 `75f79af15dd7…`，标识体系不同 | **书面确认或选择不写该句** |
| 6. 79,301 vs 396,610 / token | 11-17 24:00 前找清单；否则拆表并存两口径，不提模型卡、不写虚假 training report，不把 79,322 填进表 | 同方向（其 C′）；仍优先找实测 | `CURRENT_DATASET_STATUS.md`；模型卡仅在下载 README；仓库无 `trainer_state.json` | **能否在 11-17 24:00 前提供训练清单或日志**；若不能，确认启用拆表兜底 |

已缩小、不再作为对立项（除非用户另有指示）：不写 `max_bricks=200` 与 66/114 stable；box TinyTeX 为主、Overleaf 为备份；不把 checklist 当作 OpenReview 附件；论文不提模型卡；不虚构 training report；新文献三条（作者补全，venue 暂 arXiv）；L1–L5 / 105 组等权放附录。

---

## Changelog（相对 PLAN_RB1_R1）

### 从 RB2 R1 / 其 CRITIQUE 新吸收

1. **A-1 / E-8：** 正文协议句删除 `max_bricks=200`。本轮确认 `brick_count`＝评测 LDR 的 type-1 行数＝`scores.csv` `part_count`（114/114），且 36 条超过 200（其中 6 条 `stable=True`）。只写 $20^3$ 世界与 seed 42。
2. **A-2：** 正文不写 66/114 stable。
3. **A-3：** 指标定义的证据链改引 Deploy 脚本（SHA 前缀 `a90e851a6a01`）。
4. **A-4：** 定义句补回 PE 72 token 上限与 “8 视角取最大、再对 prompt 平均”。
5. **A-5：** 确认 OpenReview 无附件栏；checklist 默认不附，若附只进 PDF 附录。
6. **A-6：** 承认 “geometric reasoning” 亦属 Topic 5 用语；保留该词并补 Topic 5 证据，不写 improves。
7. **A-10：** 若报道 p 值，采用 Holm（3×2）。
8. **B-1：** P0 区分为“执行项”与“约束（维持）”。
9. **B-4：** L1–L5 明确为 P1（附录）。
10. **C-3：** 找清单截止 11-17 24:00 UTC+8。
11. **D-1 / D-2：** 表注不用 “training report / released model card”。
12. **C-1：** 维持并强调 11-15 注册 profile（官方文档：公共邮箱最长约 2 周）。

### 相对 R1 的自身更正（含对 RB2 仍不接受的部分）

- **525 vs 114：** 用本轮核对结果改写 A11 条件：114 不是 525 的子集；禁止 “additional / 114 taken from 525 / 懂体素形状”。
- **中文图：** 默认仍保留；不改推荐删除。
- **E-2 版式：** 表默认附录，不把 +0.35 的正文表当作必选项。
- **页面规则 / Algorithm 1：** 维持“第 7 页后无正文”；不以 `figure*` 改排算法为兜底。
- **SigLIP2：** 仍不写 “learned scale and bias”。
- 页数预算按删减协议句、诊断表下沉后重估，目标仍 ≤ 6.6 页。

---

## 0. 证据摘要（R2 增补；R1 §0 仍有效）

### 0.1 525 诊断与 114 主对比（新）

见 `CRITIQUE_RB1_R2.md` 专题 (a)。可写字段上轮已复算：46/525 raw 单一钉柱连通；479 失败中位 5 个分量（2–33）；档位 326/133/18/2；`none_needed` 46；`regen_seed` 28；`studOK`/`shape_preserved` 525；`union_dropped_bricks>0`＝0 等。

### 0.2 BrickGPT 零件数（新）

见专题 (b)。`brick_count`＝LDR type-1 行数＝主表零件口径；36/114 > 200。不写 `max_bricks=200`，不写 66/114 stable。

### 0.3 OpenReview 注册（新）

会场页未写审核周期。docs.openreview.net：“Signing up with a public domain may take up to 2 weeks in moderation.” **今天完成注册。**

### 0.4 指标定义（补全）

证据脚本：`Deploy\build\comparison_20261110\BrickMoreComparison\Scripts\evaluate_paper_images.py`（`a90e851a6a01`，与 `comparison_full\*.config.json` 的 sources 一致）。PE：余弦，文本上限 72（`pe.model.json`）；SigLIP2：logit 的 sigmoid，上限 64；VQAScore：全词表 softmax。聚合：8 视角取最大，再对 prompt 平均。

---

## A. 「待用户确认」（含推荐）

### A1 标题（P0 决策）
推荐 B′（Topic 5 用词直接）。A 亦可，若用户更强调钉柱连通。须圈定后再改 `\title` 与 OpenReview title。

### A2 匿名与 profile（P0）
PDF 保持 `[submission]`。作者只进 OpenReview。按字段限制按匿名审稿准备，但论文不写“官方宣布双盲”。**全体作者今日注册/确认 profile**，优先机构邮箱并完成验证。可选：用户本人发信 `li.li02@usc.edu` 询问政策，不等回复。

### A3 模型数与 token（P0；11-17 24:00 截止）
优先用训练清单（选项 A）。否则拆表：Release reports 写 79,301（保留算式与非全量重跑限定）；Fine-tuning corpus 写 396,610（356,955/39,655）与 2,228,044,818 tokens。表注中性、不提模型卡、不写 training report / training manifest，不用 24,448×25.3 h 替换，不写“21 个额外模型”。正文称 validation；脚注可写 held-out split 用于 checkpoint 选择。若清单与 “fine-tuning uses only geometrically passing models” 冲突，再改该句。

### A4 中文历史图（P2 / 用户决策）
**推荐 C′：保留并在附录段首加一句 historical、不支撑主结论。** 选项见「仍有分歧」第 1 行与专题 (d)。

### A5 显著性（P1）
推荐做：114 条配对；VQA/PE/SigLIP2 × vs BrickGPT / vs BrickNet；符号检验 + Wilcoxon，Holm 校正。附录出表，正文 1–2 句。不检验 $P_{\mathrm{inv}}$（两边已为 0）。不预填 p 值。写成 re-analysis of existing scores。

### A6 不做新基准、不重训
维持。转换对比称 conversion/repair analysis，不叫 model ablation。

### A7 指标定义（P0 表述，不必新实验）
完整替换句（保留原聚合与 72/64）：

> VQAScore is the full-vocabulary softmax probability that Qwen2.5-VL-7B-Instruct generates the single token “Yes” as its first answer token. PE is the cosine similarity between L2-normalized image and text embeddings of PE-Core-bigG-14-448, and SigLIP2 is the sigmoid of the image–text logit of SigLIP2 giant-opt-patch16-384; their text encoders read at most 72 and 64 tokens, respectively. For each metric, a model's score is the maximum over its eight views, averaged over prompts. The three metrics live on different scales and are compared only within a metric.

### A8 编译（P0 流程）
主编译：已验证的 box TinyTeX + `latexmk -pdf`。备份：本机 MiKTeX/TeX Live，以及 Overleaf（显式选 pdfLaTeX）。不用 Tectonic。11-16 前至少一次复现编译。

### A9 checklist 与过时 md
默认不附 checklist。`abstract_introduction.md` 不作本轮工作。

### A10 评测权重（P0 决策）
见「仍有分歧」第 5 行。未确认则不写 “all evaluated outputs use the step-79,000 checkpoint”。525 诊断若写入，可注明权重标签 `92d1c595`，不与 step-79,000 强制等同。

### A11 525 诊断（P1，有条件）
**推荐批准写入**，条件比 R1 更严：

1. 只用 manifest / autopsy 已复算字段（见 R1 §0.5 与专题 (a)）；
2. 正文一段 + **表默认附录**（仅当编译后仍有余量且用户要求，才把极简表放正文）；
3. 称 “525 prompts from the `brickmore48_eval_630` diagnostic set (21 categories × 5 levels × 5 phrasings)”；**不写 additional / held-out / taken from the 114**；
4. 不写形状保真、空间推理基准、“懂体素形状”；`shape_preserved` 只可写 in-bounds voxel union；
5. 数字只在 §5.x 或附录展开；摘要/引言/结论至多一句定性指向；
6. 遵守 A10：不把诊断绑死到 step-79,000。

建议正文段（数字均已复算）：

> We also inspected 525 BrickMore generations from the `brickmore48_eval_630` diagnostic set, which is a separate prompt collection from the 114-prompt comparison. Raw decoder outputs were stud-connected in 46 cases (8.8\%); after the same retile procedure used in the main pipeline, all 525 assemblies were stud-connected. Among the 479 raw failures, the median number of stud-connected components was 5 (range 2--33). The MILP exact-cover solver was not required for the 46 already-connected outputs; 326 / 133 / 18 / 2 cases finished within the 12 s / 60 s / 180 s / 600 s tiers. These checks evaluate stud connectivity and in-bounds voxel-union consistency, not prompt-level shape fidelity or spatial reasoning.

### A12 三篇相关工作（P1）
批准则写入，作者必须完整：MeshGPT arXiv:2311.15475（8 人，含 Angela Dai、Matthias Nießner）；LLaMA-Mesh arXiv:2411.09595（7 人，含 Xiaohui Zeng）；SpatialVLM arXiv:2401.12168（9 人，含 Dorsa Sadigh、Leonidas Guibas、Fei Xia）。venue 暂只写 arXiv。生成器不是 VLM 的限定句保留。

---

## B. 页数预算

起点约 6.00 页。安全上限 6.6。

| 项 | 优先级 | 正文增量 | 备注 |
|---|---|---|---|
| 标题、匿名 | P0 | 0–0.03 | |
| 拆表 + 口径（A3） | P0 | +0.08–0.15 | |
| 指标定义补全（A7） | P0 | +0.05–0.08 | 替换原句，净增有限 |
| BrickGPT $20^3$ / seed 42（不含 max_bricks、stable） | P1 | +0.02–0.08 | 较 R0 下调 |
| 转换效益 65,503→79,298 | P1 | +0.06–0.10 | 与 79,301 分口径 |
| 引言去重 − 试验床句 | P1 | 净约 −0.05 | 颜色句须移到 §4.1 |
| 相关工作三篇 | P1 | +0.08–0.12 | |
| 525 诊断正文段（表在附录） | P1 | +0.10–0.15 | 不上正文表则远低于 +0.35 |
| 显著性正文 1–2 句 | P1 | +0.08–0.12 | 表在附录 |
| L1–L5 / 105 组 / 未截断子集 | P1 | 0～+0.04 | 表在附录；未截断子集须先复算截断标记 |

执行顺序：先 T 口径/定义/拆表/转换句/引言去重；编译量页后再加入相关工作、诊断段、显著性句。超页下沉顺序：（1）诊断表保持附录并压缩正文段；（2）移动 Figure 3；（3）下沉微调配置表；（4）显著性只留一句。**禁止**移动或改排 Algorithm 1，禁止删主表。

验收：`latexmk -pdf` 成功；无未定义引用；letter；无 Type 3；首页 Anonymous submission；**第 7 页之后无正文**（References 可从第 8 页起）。

---

## C. 分节修订（相对 R1 的执行要点）

未列出的段落同 R1：默认不动；主表与 Table 4 数字锁定；Algorithm 1 逻辑与超时阶梯不动。

**导言区：** 标题见 A1。匿名检索含 Kyle308666、BuShiGeMenn、`D:\`、huggingface、github。

**摘要：** 核心主张与已有数字不动。若 A11 批准，最多半句定性（diagnostic checks of stud-connectivity on a separate 525-prompt set），不写 8.8% 全表，不写 additional。

**引言：** 保留 “geometric reasoning and object assembly”，不再按 Topic 2 扩写。P1：试验床框句（可精确检查的离散空间表示）。P1：去重 80,000/79,301 的第三次复述；若删颜色句，必须移到 §4.1。贡献 1 保持 79,301 为几何通过。若 A11 批准，贡献 3 可加定性半句，不堆数字。

**相关工作：** 批准后加入三条已核文献；Brick-by-Brick 的 RL 保持第三者表述。

**§3 数据：** 表 1 按 A3 拆表。§3.2 加转换效益句（65,503→79,298，+228,582/−125，31,532 零体素改动）；只引用 retile 发布数，不写成 79,301。附录可列 relaxed 体素改动 428,278 / 38,230（`relaxed_assembly_80000\assembly_summary.json`）。

**§4 / Algorithm 1：** 留在正文。不改种子与档位设计。若 A11 批准，算法后可交叉引用诊断附录，不在此重复全表。

**§5.1：** 用 A7 完整定义。协议句：

> BrickGPT outputs were generated in its native $20^3$ world (seed 42), whereas BrickMore places bricks in a $48^3$ workspace, which partly explains the difference in part counts.

不写 `max_bricks` 与 stable 计数。

**§5.2 主表数字锁定。** 若 A5 批准，删除 “no significance test is reported”，改为指向附录。方向冲突则先汇报，不得自行改结论。

**§5.x 诊断：** 见 A11。建议放在 raw vs retiled 之前或作为其引导段，表在附录。

**§5.3 / §5.4：** raw vs retiled 数字不动；`shape_preserved` 用语改为 same in-bounds voxel union。Boundaries 保持非空间推理基准限定。

**§6 Scope：** 锁定无预训练/RL、生成器为文本 LM。不把 Scope 改写当 P0。若写未来工作，connectivity-based rewards 必须 outside the scope，且不出现在摘要/贡献。

**结论：** 不改“对齐最高、$P_{\mathrm{inv}}$ 与 BrickGPT 持平”。诊断至多一句定性。

**附录：** 诊断表、检验表、L1–L5 与（复算后的）105 组等权 / 未截断子集；转换策略英文表（可部分替代 image14 的已核数字）。历史图按 A4。

**参考文献：** 仅增 A12 三条，作者完整。

---

## D. 新实验 / 新数据可行性

与 R1 相同：改定义、拆表、转换效益、525 已有诊断、配对检验、分层分析、BrickGPT 网格句——均为已有产物，截止前可行。新空间推理基准与再训练不可行。评测权重对齐取决于用户。未截断子集须先找到 `text_truncated`（或同等）记录再写数字，本轮不采用未复算单元格。

---

## E. 日程（UTC+8）

| 时段 | 工作 |
|---|---|
| **11-15** | 用户圈定「仍有分歧」1–6 与 A1–A12。**全体作者注册 OpenReview profile**（公共邮箱尤须立刻完成并尽量验证机构邮箱）。开始找 U3 清单。确认主编译路径。 |
| **11-15 晚–11-16** | 实施 P0 执行项：标题（若已定）、指标定义、拆表结构、匿名检索、第一次编译。 |
| **11-16** | 若批准：转换句、引言去重、协议句、诊断段与附录表草稿、检验与分层草稿。二次编译量页。 |
| **11-17** | 附录与相关工作；本机或 Overleaf 复现。**24:00 为找清单截止点**；否则启用拆表兜底。 |
| **11-18** | 按 U3 结果定稿 Table 1；通读、术语、数字核对、页数终检；内容冻结。准备表单（TLDR 不用 79k）。 |
| **11-19** | 最终编译并提交完整稿。 |
| **11-20 12:00 前** | 仅应急。截止 19:59 UTC+8，不依赖最后一小时。 |

---

## F. 优先级清单

### P0 执行项
1. 用户确定标题后改 `\title`。
2. 匿名 PDF；作者进 OpenReview；**今日完成 profile**。
3. 拆表写 79,301 与 396,610；token 保留并中性加注（A3）。
4. 按 A7 写全指标定义（Deploy 脚本哈希）。
5. pdfTeX 编译通过；匿名检索含新用户名。
6. 用户确认或搁置评测权重（A10）。

### P0 约束（维持，不是新写作任务）
7. Algorithm 1 留在正文，不以 `figure*` 改排为兜底。
8. 不改主表 / Table 4 已核数字，不改结论方向。
9. 不宣称 RL / 预训练 / 生成器是 VLM；不写 improves spatial reasoning。

### P1（部分须批准）
10. BrickGPT $20^3$ + seed 42 协议句（不含 max_bricks、stable）。
11. 转换效益句（与 79,301 分口径）。
12. 若批准：525 诊断正文段 + 附录表（A11 全部条件）。
13. 若批准：配对检验（Holm），附录出表。
14. L1–L5 等附录分层（写入前重算）；未截断子集仅在复算后写。
15. 引言去重、颜色句移位、试验床框句。
16. 若批准：三条相关工作（完整作者）。
17. validation 脚注。

### P2
18. 中文历史图按 A4（默认保留）。
19. 不新建空间推理基准、不重训。
20. 不更新 `abstract_introduction.md`。
21. VQAScore 用语与 P_inv 小数位；Underfull；checklist 仅当用户要且放附录。

---

## G. 风险

- **超页：** 诊断表进正文并在摘要/引言重复，最容易把结论推出第 7 页。对策：表默认附录；先移 Figure 3；每次编译量页。
- **口径：** 79,301 与 396,610 被误乘；65,503→79,298 被写成 79,301。拆表、分句。
- **诊断过强：** additional、114 出自 525、形状保真、空间推理基准。按 A11。
- **权重未对齐：** A10。
- **匿名：** 不提模型卡；11-18 再 grep 用户名与路径。
- **profile 审核：** 今日注册，公共邮箱风险最高。
- **来源虚构：** 不用 training report / training manifest / 模型卡字样。
- **编译：** 不用 Tectonic；box 为主。
- **截止：** 11-19 提交，11-20 应急。
