# 对 RB2 R2 评审的答复（CRITIQUE_RB1_R3）

- 作者：ReviewBot1。只写入 `D:\BrickMore\Essay\BrickMore\Plan_V1.6\CRITIQUE_RB1_R3.md`。**未修改任何论文文件**，也未改既有 `PLAN_RB1_R0/R1/R2.md` 或 `PLAN_RB2_*.md`。
- 读取：`CRITIQUE_RB2_R2.md`、`PLAN_RB2_R2.md`（评审对象是 **`PLAN_RB1_R1.md`**，不是已吸收多项的 R2）。本答复以 **R3 立场**为准，并注明 R2 是否已处理。
- 统计：Part 1 对 N1–N10 为 **接受 9、部分接受 1、反驳 0**。Part 2 对 8 项「仍有分歧」：同意 6、折中并交用户 2。

---

# 第一部分：逐条答复 RB2 的 10 条新意见（N1–N10）

### N1｜R1 仍写 `max_bricks=200` 与 66/114 stable
**接受。** 证据见上轮专题 (b) 与本轮复核：`brickgpt_generation_summary.jsonl` 中 36/114 条 `brick_count>200`（最大 497），且该字段与评测 LDR type-1 行数、`scores.csv` 的 `part_count` 114/114 全等；全部 `use_gurobi=False`，BrickMore 无对称稳定性评测。`PLAN_RB1_R2.md` 已改为只写 native $20^3$ 世界与 seed 42。R3 维持。

### N2｜脚注提模型卡 79,322 与 “仓库未见 trainer_state.json”
**接受。** 模型卡对应公开仓库 `Kyle308666/…`，有匿名风险；也不在论文里自曝日志缺失。R2 已改用中性表注（不提模型卡、不写 training report / training manifest）。R3 维持。找清单仍截止于 11-17 24:00（UTC+8）。

### N3｜仍把 “geometric reasoning and object assembly” 定为 Topic 2 框句
**接受。** https://gsr-vlm.org/ Topic 05 原文含 “for improving geometric and spatial reasoning”。应标为 Topic 5 用词并保留，不增强为 “improves spatial reasoning”。R2 已改；R3 维持。

### N4｜A8 仍引用 “附录图导致 Overleaf 超时”
**接受。** RB2 已用 box 实测撤回该理由（V1.4 `latexmk` 全流程 3.6 s，低于免费版 10 s）。R3 改理由：主编译仍为 box TinyTeX；不用 Overleaf 作主路径的原因是免费版每项目仅 1 名协作者、以及未发表稿需上传第三方。Overleaf pdfLaTeX 仍作备份。

### N5｜checklist 作为 OpenReview 附加文件
**接受。** Invitation 无 supplementary 字段。默认不附；若附只能进 PDF 附录。R2 已如此写。

### N6｜“the same retile procedure used in the main pipeline, all 525 …” 不准确
**接受。** 本轮已用代码核实（见第三部分 (a)）。28 条有 `regen_seed`（7/555/2027/12），2 条 `solver_tier=600s` 且无 `regen_seed`，两组不重叠，故仅 **495** 条走默认档位。`gen_levels2.py` 的默认种子规则与 Algorithm 1 一致，与 README L55 不一致。R3 采用如下表述（不写 “default protocol of Algorithm 1” 覆盖全部 525，也不写 “the same procedure” 而不加限定）：

> Generation used seeds 42, 104, and 2026 in that order, moving to the next seed when a draft was incomplete or failed the geometry validator, then applied the 12--60--180\,s MILP ladder (the default loop of Algorithm~\ref{alg:inference-retiling}). For 28 prompts a recovery path sampled seeds outside $S$; for two further prompts the solver budget was extended to 600\,s. All 525 final assemblies form a single stud-connected component.

注意：manifest 的 `attempt`（@42 338、@104 134、@2026 53）含 28 条随后被 recovery 替换的首次尝试标签，**不宜**写成“最终产出种子分布”。

### N7｜正文应说明 525 与 114 的关系
**部分接受。** 同意必须写明二者不是同一批、不能写 additional / held-out。35/114 条 caption 与 525 条 `prompt` 逐字一致，本侧上轮已从 `scores.csv` 与 `manifest_w{0,1,2}.json` 复算，**数字本身不必再等用户“确认”**。选取规则（为何这 114 条如此组成）仍可请用户说明，但不写入则用：

> …the `brickmore48_eval_630` diagnostic set, a separate collection from the 114-prompt comparison (35 of the 114 captions also appear in the 525).

### N8｜保留 image18 与“不可复算数字不用”冲突
**接受。** 见第三部分 (b)：未找到作图脚本或蓝柱数据文件；`best_all.json` / `best_all.md` 不存在。即使用户希望默认保留其余中文图，**image18 也应单独处理，推荐移除整图或至少删去 (a) 栏**。不把 (a) 蓝柱数字写入正文。

### N9｜替换句缺 PE 72 token 与 8 视角聚合；证据链应引 Deploy 副本
**接受。** R2 的 A7 已补全 72/64 与 “maximum over eight views, then averaged over prompts”，证据链改引 `Deploy\...\Scripts\evaluate_paper_images.py`（SHA 前缀 `a90e851a6a01`）。R3 维持；仍不写 “learned scale and bias”。

### N10｜P0 含约束项；T5 预算建立在已删内容上
**接受。** R2 已把 Algorithm 1 / 主表锁定改列为 “P0 约束（维持）”，协议句预算下调为约 +0.02–0.08 页，超页兜底为：诊断表附录 → Figure 3 → Table 2 → 压缩 E-3。R3 维持。

---

# 第二部分：对 RB2 所列 8 项「仍有分歧」的处置

目标是缩小分歧。已能由文件/规则裁定的，不再交用户。

| # | 议题 | 本轮处置 | 说明 |
|---|---|---|---|
| 1 | 中文历史图 image13–19（含 image18） | **只能交用户定**（附折中推荐） | 见下方问题 1 |
| 2 | 摘要是否出现诊断数字 | **只能交用户定**（附折中推荐；且取决于 U12） | 见下方问题 2 |
| 3 | 是否写 `max_bricks=200` 与 66/114 stable | **同意**（不写） | 双方 R2 已一致。仅当用户日后说明 `max_bricks` 语义时再议 |
| 4 | 脚注是否提模型卡与日志缺失 | **同意**（不提） | 用中性表注。找清单本身仍见用户问题 6，但不因此在论文里点名模型卡 |
| 5 | “geometric reasoning” 的定性 | **同意** | 按官网定为 Topic 5 用词，保留，不写 improves |
| 6 | checklist 作为 OpenReview 附件 | **同意**（不可行） | 只能进 PDF 附录；推荐不附。不再作为分歧 |
| 7 | 评测脚本引用哪一份 | **同意** | 引用哈希一致的 Deploy 副本。无需用户 |
| 8 | 多重比较是否用 Holm | **同意**（做检验则用 Holm） | 是否写入 p 值仍见用户问题 4（U5） |

### 交用户的问题与推荐

**问题 1（对应分歧 1 / U4、U4-b）。** 附录含中文的历史图如何处理？
- 选项：A 从提交 PDF 注释掉 image13–19（磁盘保留），已复核数字用英文表替代；C′ 全部保留，段首加 historical 说明，并把 image14/17/19 中过时的 “require verification” 改为指向发布报告；对 **image18**：移除整图，或只删 (a) 栏。
- **RB1 推荐（折中）：** 未答复时默认 **C′（保留）**；但 **image18 推荐移除或删去 (a) 栏**（蓝柱不可复核，见第三部分 (b)）。不把“删除 13–19 全部”当作默认。
- RB2 立场：未答复时保留并改图注；★推荐移除 13–19；image18 单独确认，推荐移除或删 (a)。

**问题 2（对应分歧 2，依赖 U12）。** 若批准把 525 条诊断写入论文，摘要里要不要出现一处数字 “46 of 525 raw outputs form a single stud-connected component”？
- **RB1 推荐（折中）：** 同意 U12 后，摘要**可以有这一处计数**（不写 8.8%，不写失败中位数 5）；引言、贡献、结论只保留定性指向。若 U12 不批准，摘要不写该句。
- RB2 立场：摘要可有这一处数字；其余位置只写定性。

其余须用户拍板、但不在这 8 项对立里的事项，见 `PLAN_RB1_R3.md` 文首清单（标题、是否写入 525 条、显著性检验、权重版本、11-17 前能否提供训练清单）。

---

# 第三部分：U13 种子规则与 image18 数据源

## (a) U13：README 与 Algorithm 1 的种子规则，以及代码实际做什么

**两段原文不一致。**

1. `D:\BrickMore\brickmore48_eval_630\README.md` 第 55 行：

> 种子阶梯 42 → 104 → 2026（前一个种子产出不合格且**不可修复**时启用下一个）

2. `V1.5\main.tex` 第 166 行（以及 Algorithm 1，L173–198）：

> using seeds 42, 104, and 2026 in order. A candidate is accepted when generation completes … and the geometry validator reports no errors. Otherwise, the pipeline keeps the completed draft with the fewest validator error records … It then … solves … by MILP under a 12--60--180 s time ladder. … If no cover is found within this budget, the raw draft is retained and a new seed may be queued. A separate recovery path may extend the budget to 600 s and sample seeds outside $S$; it is not part of the default loop.

Algorithm 1 伪代码（L176–198）与第 166 行一致：在集合 $S$ 内，仅当 `complete ∧ valid` 时中止换种子；否则收齐尝试后选错误最少的已完成草稿，**再**做 MILP；$T$ 用尽才 `QueueReseed`。这里的 valid 是几何校验器（格式、库、边界、重叠），**不是**钉柱连通。

**代码与 Algorithm 1 一致，与 README L55 不一致。** 525 条新批的主脚本是 `D:\BrickMore\brickmore48_tools\pipeline\gen_levels2.py`（文件头 L1–3 写明“525 条全新提示词”）：

- L110–116：`for label, seed in [('@42', 42), ('@104', 104), ('@2026', 2026)]:` 生成并 `validate`；若 `completed and rep['geometry_valid']` 则 `break`，**并不先做 MILP 再决定是否换种子**。
- L118–123：若 $S$ 内没有合法草稿，在已完成的尝试中取 `errors` 最少者（`path_kind='union'`）。
- L136：`solve_escalate(cells)` 只含 12 s / 60 s / 180 s（L73–78），**没有 600 s**。

因此 README 把 recovery 路径的“修不好再换种子”误写到了默认阶梯 42→104→2026 上。默认阶梯触发的是“不完整或几何校验失败”，不是“钉柱不可修复”。

**Recovery 路径的代码：**

- `pipeline\regen_unsolved.py`（L1–2、L81、L101–130）：对首次 180 s 仍 `not stitched` 的条目，用新种子 `[7, 2027, 555, 888]`；对**每一个**新种子，先校验，再 audit 钉柱，不行再跑 12/60/180 s，解不出才试下一粒新种子。这才接近 README L55 的“不可修复再换种子”，但种子已在 $S$ 之外。
- `pipeline\regen_one_piano.py`：同一逻辑，目标写死为 piano L1V1，新种子以 12 开头。这与 manifest 中唯一 `regen_seed=12` 的条目（piano L1V1，`regen_history`: `raw_single_component`）相符。

本轮复算 manifest（与 RB2 一致）：`attempt` @42 338、@104 134、@2026 53（525 条，含后来被 recovery 覆盖的首次标签）；`regen_seed` 28 条（7×20、555×4、2027×3、12×1）；`solver_tier=600s` 2 条（bench L1V5、bench L2V4），均 `attempt=@42`、无 `regen_seed`，与 28 条不重叠；`none_needed` 与 `raw_single_component=True` 逐条对应，均为 46。

**600 s：** `gen_levels2.py` 与 `regen_unsolved.py` 都不含 600 s。项目中能执行 600 s 档的脚本见于较旧的 `BrickNet_BrickGPT_Compirasion\BrickMore_交接包_20261030\工具\gen_round2.py`（L84、L124，`extra_600=True`），**不能据此断言**这两条 bench 就是该旧脚本跑的。论文已把 600 s 写成 recovery、而非默认环，这一限定可保留；不要写“525 条都走 Algorithm 1 默认流程”。

**建议的精确修改（不必再把 U13 当作无法裁定的用户项）：**

1. **不要改** Algorithm 1 的默认环（它与 `gen_levels2.py` 相符）。
2. **不要把 README L55 写进论文。**
3. E-2 / 诊断段采用本文件第一部分 N6 的句子；不写 “generated with the default protocol of Algorithm 1” 来概括全部 525 条。
4. 若更新评估集 README（非本轮论文必须），应将 L55 改为与代码一致：在 $S$ 内，上一粒种子不完整或未通过几何校验时才启用下一粒；MILP 在选定草稿之后进行；修不好再走 $S$ 之外的 recovery 种子。

## (b) image18 (a) 栏是否有可复核来源

**图与图注：** `V1.5\figures\image18.png`；`V1.5\main.tex` L383–387：

> `\includegraphics[width=0.85\textwidth]{figures/image18.png}`
> `\caption{Historical baseline comparison with differing acceptance criteria; not the current matched main comparison.}`

PDF 附录 C 第 13 页，自动编号为 Figure 11。图内三栏（据图像识读）：(a)「分级通过比例（判据不同）」，红柱「BrickGPT：stable=true」，蓝柱「BrickMore-48：人工判定有合格模型的组」，横轴 L1–L5；(b)「同一 114 条提示词的中位规模」；(c)「逐提示词配对（蓝=stable）」。

**作图脚本 / 源数据：未找到。** 在 `D:\BrickMore` 下检索「分级通过比例」「人工判定有合格模型的组」「中位规模」以及 `image18` 的 `.py/.ipynb/.csv/.json/.md/.tex/.html/.svg/.xlsx` 等，除论文各版本中的插图调用、计划评审文档、以及 `Essay\BrickMore\v1_Grok\BrickMore.docx`（仅嵌入同图，不是生成脚本）外，**没有**发现生成该 PNG 的脚本或蓝柱表。`brickmore48_eval_630\results\best_all.json` 与 `best_all.md` 仍不存在。

**可部分核对的只有红柱：** `brickgpt_generation_summary.jsonl` 按 level 的 `stable=True` 为 L1 13/21、L2 15/21、L3 12/23、L4 12/25、L5 14/24（与 RB2 一致；约 61.9% / 71.4% / 52.2% / 48.0% / 58.3%）。蓝柱所依赖的人工判决数据不可复核；图题已写明“判据不同”。

**建议处理：** 与 N8 相同——推荐从提交 PDF 中移除 image18，或至少删去 (a) 栏；不要把蓝柱比例写入正文或表。若用户坚持保留 (b)(c)，须标明 historical，且不得用 (a) 做 BrickMore 优于 BrickGPT 稳定性的主张。(b)(c) 的零件数虽可能与 jsonl / `scores.csv` 同类，但在找到作图脚本之前，不把它们当作已核数据源去“更正图注为已核实”。
