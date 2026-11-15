# BrickMore V1.6 修订计划（ReviewBot1，R3）

- 计划文件：`D:\BrickMore\Essay\BrickMore\Plan_V1.6\PLAN_RB1_R3.md`
- 由 `PLAN_RB1_R2.md` 修订。**R0 / R1 / R2 计划文件保持不动。** 本轮答复见 `CRITIQUE_RB1_R3.md`。
- 基稿：`V1.5\main.tex`、`REVIEW_V1.5.md`；对照 `CRITIQUE_RB2_R2.md`、`PLAN_RB2_R2.md` 与项目文件。
- **只做规划。未修改任何论文源文件。**
- 硬约束：GSR-VLM Topic 5 only；AAAI-27 模板；正文（摘要至结论）≤ 7 页（References 可从第 8 页起）；Algorithm 1 留在正文；不虚构数字/文献；不宣称预训练、RL，或生成器是 VLM。
- 截止：**2026-11-20 19:59（UTC+8）**。建议 11-19 提交。找训练清单：**11-17 24:00（UTC+8）**。

本轮目标是**尽量消除与 RB2 的分歧**。可由文件或会场规则裁定的事项不再列入文首。

---

## 须由用户决定的事项（仅此 6 项）

| # | 要问用户的问题 | RB1 推荐 | RB2 立场 |
|---|---|---|---|
| 1 | 标题用哪一句？或保持 `BrickMore`？ | B′：*BrickMore: Learning Spatial Brick Assemblies by Agentic Data Generation and Language-Model Fine-Tuning* | ★A：*…Stud-Connected Brick Assembly from Agentically Generated Voxel Data*；B′ 可接受 |
| 2 | 附录中文历史图如何处理？尤其是 image18？ | 未答复时默认保留（C′：段首加 historical 说明；image14/17/19 中过时的 “require verification” 改为指向已复核的发布报告）。**image18 推荐移除或删去 (a) 栏**（人工判决蓝柱无源文件，见 `CRITIQUE_RB1_R3.md` 第三部分 (b)）。不把删除 13–19 全部当作默认 | 未答复时保留并改图注；★推荐移除 13–19，用英文表替代 14/17/19；image18 单独确认，推荐移除或删 (a) |
| 3 | 是否把 525 条结构诊断写入论文（U12）？若写入，摘要要不要出现 “46 of 525 raw outputs form a single stud-connected component”？ | **写入**（有条件：只用已复算字段；表默认附录；不写 additional / 形状保真 / 空间推理基准；不把权重绑死为 step-79,000）。摘要**可以有这一处计数**，不写 8.8% 或失败中位数 5；引言/贡献/结论只定性。诊断段用 N6 修订句（495 条默认环 + 28 条额外种子 + 2 条 600 s），见下 C9 | ★写入可复算部分；摘要可有 “46 of 525 …” 一处；须同时确认 U10；说明与 114 条部分重叠 |
| 4 | 是否对已有 `scores.csv` 做配对显著性检验并写入附录（会新增 p 值）？ | **做**：符号检验 + Wilcoxon，3×2 比较用 Holm；正文 1–2 句；不检验 $P_{\mathrm{inv}}$；不预填 p 值；不显著则如实写，不改“均值最高”结论 | 同：做，主报 Holm 校正后的符号检验 |
| 5 | 525/114 所用权重是否即 step-79,000 检查点（`eval_630` 标签 `92d1c595` 与 `model.sha256` 前缀 `75f79af1…` 对不上）？ | 请书面确认。未确认则不写 “all evaluated outputs use the step-79,000 checkpoint”；诊断若写入，只可注明标签 `92d1c595` | 同：请确认；无法确认就不写该句 |
| 6 | 能否在 **11-17 24:00（UTC+8）** 前提供训练清单或 `trainer_state.json`？若不能，是否启用拆表兜底？ | 优先用清单。否则拆表：79,301 为发布整合口径，396,610 与 2,228,044,818 为微调语料；中性表注，**不提模型卡、不写日志缺失 / training report** | 同（选项 C′） |

已消除、不再询问的分歧：不写 `max_bricks=200` 与 66/114 stable；“geometric reasoning” 按 Topic 5 用词保留；checklist 不作为 OpenReview 附件；指标定义引用 Deploy 脚本并写全 72/64 与 8 视角聚合；做检验则用 Holm；box TinyTeX 为主、Overleaf 为备份；第 7 页后无正文；不以 `figure*` 改排 Algorithm 1。U13 种子规则已由 `gen_levels2.py` 裁定（与 Algorithm 1 一致、与 README L55 不一致），按第三部分 (a) 写诊断句即可，不再作为用户项。

全体作者仍应**今日**注册或确认 OpenReview profile（公共邮箱可能需最长约 2 周审核）。这是提交风险，不是双方分歧。

---

## Changelog（相对 PLAN_RB1_R2）

1. 文首只保留上述 6 个用户决策；8 项旧分歧中 6 项改为同意并从对立表删除。
2. **N1 / 分歧 3：** 维持不写 `max_bricks` 与 66/114（R2 已改）。
3. **N2 / 分歧 4：** 维持中性表注，不提模型卡与日志缺失。
4. **N3 / 分歧 5：** 明确 Introduction 该句为 Topic 5 用词、保留。
5. **N4：** 去掉 “Overleaf 超时” 理由，改写协作人数与未发表稿上传。
6. **N5 / 分歧 6、N9 / 分歧 7、N10 / 分歧 8：** 维持 R2 已吸收内容（附件栏、Deploy 哈希与完整定义、P0 约束与预算/兜底）。
7. **N6 + U13：** 诊断段改用“默认环 / 28 条额外种子 / 2 条 600 s”的表述；默认种子触发规则以 `gen_levels2.py` 为准，不采用 README L55。
8. **N7：** 正文写明 525 与 114 为不同集合，并可写 caption 重叠 35/114（已复算）。
9. **N8 + image18：** 用户问题 2 中单独推荐移除 image18 或删 (a) 栏；作图脚本未找到。
10. **分歧 2：** 折中为——U12 批准后摘要可写 “46 of 525 …” 一处，不写 8.8% 与中位数 5。

---

## 0. 本轮新增证据（其余见 R1/R2 §0）

- 默认推理脚本：`brickmore48_tools\pipeline\gen_levels2.py` L110–136、L73–78。Recovery：`regen_unsolved.py`（种子 7/2027/555/888）、`regen_one_piano.py`（piano L1V1，种子以 12 起）。与 Algorithm 1（`main.tex` L166、L173–198）相符；与 `eval_630\README.md` L55 不符。
- manifest 复算：attempt 338/134/53；regen 28；600s 2 条（bench L1V5、L2V4）无 regen_seed；495 = 525−28−2。
- image18：仅有 PNG 与 `main.tex` L385–387 图注；无作图脚本；红柱与 jsonl 各级 stable 计数相符；蓝柱无源。

---

## A. 待用户确认（与文首 6 项对应；推荐已列于上表）

实施时在用户圈定前**不动**标题、不删图、不写入 525 数字/p 值、不写检查点等同句、不改 Table 1 的模型数口径。

其余已裁定、可直接执行的确认项：指标定义按脚本写（用户仅需点头即可改表述，属精度修正）；不附 checklist；不新做空间推理基准、不重训。

---

## B. 页数预算

起点约 6.0 页，安全上限 6.6。与 R2 相同：拆表 +0.08–0.15；定义句 +0.05–0.08；协议句（仅 $20^3$/seed 42）+0.02–0.08；转换效益 +0.06–0.10；引言去重与试验床句净约 −0.05；相关工作 +0.08–0.12；525 诊断正文段 +0.10–0.15（表默认附录）；显著性正文 +0.08–0.12。先写口径/定义/转换/去重，编译后再加相关工作、诊断段、检验句。超页：诊断表保持附录并压缩段 → 移 Figure 3 → 下沉 Table 2 → 检验只留一句。**不**改排 Algorithm 1。验收：第 7 页之后无正文。

---

## C. 分节修订要点（相对 R2 的执行差异）

未列出的段落同 R2：主表与 Table 4 数字锁定；Algorithm 1 默认环与 $S$、$T$ 不改逻辑；600 s / $S$ 之外种子保持为 recovery 的既有说明。

**标题 / 匿名：** 见用户项 1。PDF 保持 `[submission]`。检索含 Kyle308666、BuShiGeMenn。论文不提模型卡。

**摘要：** 核心主张与已有数字不动。若用户项 3 批准写入诊断，可加一句 “On 525 diagnostic prompts, 46 raw outputs form a single stud-connected component.” 不写 8.8% 或中位数 5，不写 additional。

**引言：** “geometric reasoning and object assembly” 按 Topic 5 用词保留。加试验床框句。去重 80,000/79,301 的第三次展开；颜色句若从引言删除，必须移到 §4.1。贡献 3 在 U12 批准后只加定性半句。

**相关工作：** 三条已核文献（作者完整，venue 暂 arXiv）；不写提升了 VLM。

**§3：** 表 1 按用户项 6 拆表或按清单改正。转换效益 65,503→79,298（与 79,301 分口径）。Relaxed 体素改动 428,278 / 38,230 若写入须引 `relaxed_assembly_80000\assembly_summary.json`。

**§4 / Algorithm 1：** 留在正文。默认环与 `gen_levels2.py` 一致，不按 README L55 改算法。

**§5.1：** 完整指标定义（Deploy 脚本；72/64；8 视角取最大再平均）。协议句只写 $20^3$ 与 seed 42。

**§5.2：** 数字锁定。若用户项 4 批准，删除 “no significance test is reported”，改为指向附录。

**诊断段（若用户项 3 批准；表默认附录）：**

> We also inspected 525 BrickMore generations from the `brickmore48_eval_630` diagnostic set, a separate collection from the 114-prompt comparison (35 of the 114 captions also appear in the 525). Generation used seeds 42, 104, and 2026 in that order, moving to the next seed when a draft was incomplete or failed the geometry validator, then applied the 12--60--180\,s MILP ladder (the default loop of Algorithm~\ref{alg:inference-retiling}). For 28 prompts a recovery path sampled seeds outside $S$; for two further prompts the solver budget was extended to 600\,s. Raw decoder outputs were stud-connected in 46 cases; after retiling, all 525 assemblies were stud-connected. Among the 479 raw failures, the median number of stud-connected components was 5 (range 2--33). These checks evaluate stud connectivity and in-bounds voxel-union consistency, not prompt-level shape fidelity or spatial reasoning.

**§6 Scope** 锁定。未来工作若写 connectivity-aware decoding，必须 outside the scope，且摘要/贡献不出现 reward/RL。

**附录：** 诊断表、检验表、L1–L5 与（复算后的）105 组等权；转换策略英文表。历史图按用户项 2。image18 按推荐处理。

**参考文献：** 仅增已核三篇，作者完整。

---

## D. 可行性 / E. 日程 / F. 清单 / G. 风险

与 R2 相同，仅作两处收紧：诊断句按上文 C 节；11-15 完成文首 6 项决策并注册 OpenReview profile；11-17 24:00 为清单截止点；11-19 提交，11-20 应急。

**P0 执行：** 标题（若已定）、匿名与今日注册 profile、拆表/中性表注、指标定义、编译与匿名检索、权重句按用户项 5。
**P0 约束：** Algorithm 1 留在正文；不改主表数字与结论方向；不宣称 RL/预训练/VLM。
**P1：** 协议句、转换效益、（批准后）诊断段与附录表、（批准后）Holm 检验、分层附录、引言去重与试验床句、三条相关工作。
**P2：** 中文图按用户项 2；不做新基准与再训练；不更新 `abstract_introduction.md`。

风险仍是：超页、口径误乘、诊断过强、权重未对齐、匿名（含模型卡）、profile 审核、来源虚构、编译器、截止。对策同 R2。
