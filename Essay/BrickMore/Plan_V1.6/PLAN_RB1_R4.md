# BrickMore V1.6 修订计划（ReviewBot1，R4）

- 计划文件：`D:\BrickMore\Essay\BrickMore\Plan_V1.6\PLAN_RB1_R4.md`
- 由 `PLAN_RB1_R3.md` 修订。**R0–R3 及全部 RB2 文件保持不动。** 本轮答复见 `CRITIQUE_RB1_R4.md`。
- 基稿：`V1.5\main.tex`（33,614 字节，2026-11-14 23:36:55 UTC+8，SHA256 `A1EEF7D8…`）。只做规划，**未修改任何论文源文件**。
- 硬约束不变：GSR-VLM Topic 5 only；AAAI-27 模板；正文（摘要至结论）≤ 7 页；Algorithm 1 留在正文；不虚构数字；不宣称预训练、RL，或生成器是 VLM。
- 截止：**2026-11-20 19:59（UTC+8）**。建议 11-19 提交。找训练清单：**11-17 24:00（UTC+8）**。

目标是把双方仍须对质的分歧减到最少。本轮已用文件裁定 525/114 关系与 E-9 事实；**审稿人之间只剩标题一项需要并列候选**。

---

## 须由用户决定的事项

| # | 要问用户的问题 | RB1 推荐 | RB2 立场 |
|---|---|---|---|
| 1 | **标题用哪一句？** 这是双方之间仅剩的需并列候选的分歧。 | **B′**：`BrickMore: Learning Spatial Brick Assemblies by Agentic Data Generation and Language-Model Fine-Tuning`（也接受 A） | **A**（略偏好）：`BrickMore: Learning Stud-Connected Brick Assembly from Agentically Generated Voxel Data`（也接受 B′）。也可保持 `BrickMore`（C） |
| 2 | 附录中文历史图如何处理？ | 未答复时默认 **C′**（保留；段首加 historical 说明；image14/17/19 的过时 “require verification” 改为指向已复核的发布报告）。**image18 改为保留**，图注补判据不同说明（蓝柱已可从 `best_all.json` 复核）。A（移出 PDF）仅作选项 | 同：默认 C′；A 不标 ★；image18 保留并补 “criteria differ” 图注 |
| 3 | 是否把 525 条结构诊断写入论文（U12）？ | **写入**（只用可复算字段；表默认附录；摘要**不放数字**；不写 additional / 独立运行 / 形状保真 / 空间推理基准）。与 114 的关系用统一句，并必须与 E-9 同时出现 | 同 |
| 4 | 是否对已有 `scores.csv` 做配对显著性检验并写入附录（会新增 p 值）？ | **做**：符号检验 + Wilcoxon，6 次比较，Holm；不检验 $P_{\mathrm{inv}}$；不预填 p 值；结果只解释为这批**交付输出**的差异（因 E-9） | 同 |
| 5 | 评测权重是否即 step-79,000（U10）？其余 64 条来自哪个版本？ | 请书面确认。未确认则不写 “all evaluated outputs use the step-79,000 checkpoint”。45 条 judged 可注明标签 `92d1c595`（提交号，与文件哈希不是同一体系） | 同 |
| 6 | 能否在 **11-17 24:00（UTC+8）** 前提供训练清单或 `trainer_state.json`？否则是否启用拆表 C′？ | 优先用清单；否则拆表，中性表注，**不提模型卡、不写日志缺失** | 同 |
| 7 | BrickGPT 运行配置是否在附录披露（U14）？记录值为 `max_regen=8`、`use_gurobi=False`，与论文（100 次物理 rollback、Gurobi）及官方仓库默认（`max_regenerations=100`、`use_gurobi=True`）都不同。 | **推荐 B**：主文只写 $20^3$ 与 seed 42；附录如实写出记录值并注明并非作者默认配置（建议句见 `CRITIQUE_RB1_R4.md` U14）。不批准则主文保持短句，仍**禁止**写 “authors' default configuration” | ★A：主文不写这些参数；B/C 为备选 |

已由文件裁定、不再询问的事项：E-9 的 45/69 事实与 §5.1 披露本身（P0，建议句已写出，用户只需改英文概括则告知）；525/114 为同一候选池中的同一输出（35+10=45）；不写 `max_bricks=200` 与 66/114 stable；摘要不放诊断数字；“geometric reasoning” 按 Topic 5 用词保留；checklist 不作为 OpenReview 附件；指标定义引用 Deploy 脚本（72/64，8 视角聚合）；做检验则用 Holm；box TinyTeX 为主；第 7 页后无正文；不以 `figure*` 改排 Algorithm 1；image18(a) 可复核，默认保留并改图注。全体作者仍应**今日**注册或确认 OpenReview profile。

---

## Changelog（相对 PLAN_RB1_R3）

1. **E-9（P0，新）**：接受必须在 §5.1 披露选择效应。独立复核确认 45 judged = 6 选 1 获胜者；69 条按 `source_kind` 计数；其中 35 条替换了已有获胜者、34 条补入 26 个全不合格组。建议句写入替换 + 来源脚注，不只写“后续补缺”。
2. **F2 / image18**：撤回“蓝柱无源、建议删图”。`best_all.json` 在 11-07 交付目录（三份副本同哈希）。默认保留 image18 并补判据图注。用户项 2 同步修改。
3. **525/114 关系**：撤回“不能推断同一批生成”。采用与 RB2 一致的候选池表述（统一句见用户项 3 / 下文 C 节）。此项不再列入分歧。
4. **摘要**：接受 RB2，**不放** “46 of 525 …” 数字；取消 R3 的摘要折中。
5. **U14（新）**：核实项目记录、论文第 8 页与官方仓库默认；推荐附录披露；禁止“作者默认配置”。列为用户项 7。
6. **匿名性**：V1.5 将提交的 tex/bbl/PDF/图未检出用户名；泄漏在非投稿 jsonl / provenance / `collab_verified.json`（`D:\Users\15778\...`、`E:\brick_train\...`、`Kyle308666/...`）。G-2 增加检查命令，且不要把 log/fls/bak/历史 zip 打进投稿包。
7. **U10 / U13**：吸收 provenance 提交号与主对比中 3 条 600 s / regen 特例；U13 不再作为用户项。
8. 文首用户项改为 7 条；双方之间仅标题仍并列两套候选。

---

## 0. 本轮新增证据（其余见 R1–R3 §0）

- `best_all.json` 三份副本，sha256 `1003CBF4377D1508…`，105 条，79 个 `choice_id≠NONE`。
- 45 judged：`choice_id`、caption、`prompt.txt`、LDR type-1 行数与 `part_count` 均为 45/45。
- `items_index.json` 与模型目录：105 组均为 {V1–V5, 首批} 共 6 个候选。
- image18(a) 蓝柱 18/21…13/21 与 79 个获胜组按级计数一致。
- BrickGPT 官方 `BrickGPTConfig`：`max_regenerations=100`、`use_gurobi=True`、`max_bricks=2000`（读取自 GitHub 源码，2026-11-15）。
- `main.pdf` 无 Author/Title；jsonl 的 `model` 路径含 `D:\Users\15778\Desktop\...`。

---

## A. 待用户确认

实施时，在用户圈定前**不动**标题、不删图、不写入 525 数字或 p 值、不写检查点等同句、不改 Table 1 口径、不把 `max_regen` / `use_gurobi` 写入附录以外的正文。E-9 的披露本身是 P0：事实已定，按建议句写入（用户若要改 69 条的英文名称，执行前告知）。

---

## B. 页数预算

与 R3 相同起点（约 6.0 页，安全上限 6.6），增补：E-9 +0.05–0.08；U14 附录 +0–0.05；摘要不再因诊断数字加行。超页兜底仍为：诊断表保持附录 → Figure 3 → Table 2 → 压缩 E-3。**不**改排 Algorithm 1。验收：第 7 页之后无正文。

---

## C. 分节修订要点（相对 R3 的执行差异）

未列出的段落同 R3。

**标题 / 匿名：** 用户项 1。PDF 保持 `[submission]`。投稿前执行扩写后的 G-2（见 `CRITIQUE_RB1_R4.md` 第三节 (c)）。论文与任何附件不出现 Kyle308666、本地用户路径、模型卡。

**摘要：** 核心主张与已有数字不动。U12 批准后最多半句定性指向诊断，**不放** 46/525、8.8% 或中位数 5。

**§5.1（P0，E-9）：** 用 `CRITIQUE_RB1_R4.md` 的建议句替换 L215。协议句仍只写 BrickGPT 的 $20^3$ 与 seed 42。指标定义（Deploy 脚本；PE 72 / SigLIP2 64；8 视角取最大再平均）同 R3。

**诊断段（若 U12 批准；表默认附录）：** 开头用第二部分 (i) 的统一句，并指向 §5.1。其余保持 R3 的默认环 / 28 条额外种子 / 2 条 600 s / 46 raw 连通等可复算字段；数字只出现这一次。

**附录：** 历史图按用户项 2（image18 补图注，不再删除）。U14 若批准，在评测协议附录加入记录值对照句。显著性表按用户项 4。

**§6 / 检验解释：** 若做 U5，p 值解释为交付输出之间的差异，不写成孤立的模型能力。

---

## D–G. 可行性、日程、清单、风险

与 R3 相同，收紧如下：11-15 完成文首 7 项决策（标题优先）并注册 OpenReview profile；同日写入 E-9；11-17 24:00 为清单截止；11-19 提交，11-20 应急。

**P0 执行：** 标题（若已定）、匿名与今日注册 profile、E-9、拆表/中性表注、指标定义、编译与扩写后的匿名检索、权重句按用户项 5。
**P0 约束：** Algorithm 1 留在正文；不改主表数字与结论方向；不宣称 RL/预训练/VLM。
**P1：** 协议句、转换效益、（批准后）诊断段、（批准后）Holm 检验、分层附录、引言去重与试验床句、三条相关工作、（批准后）U14 附录句。
**P2：** 中文图按用户项 2；不做新基准与再训练。

风险新增：E-9 披露会削弱“对齐最高”的观感（结论本已限定为 delivered outputs，不改主表）；遗漏选择效应或把 69 条写成单纯补缺，会被视为不完整披露；把含 `D:\Users\15778` 或 `Kyle308666` 的 jsonl / 模型卡打进附件。对策见 E-9 建议句与匿名清单。
