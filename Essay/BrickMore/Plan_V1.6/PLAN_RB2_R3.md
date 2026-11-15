# BrickMore V1.6 修订计划（RB2 · R3）

- 作者：ReviewBot2（RB2）。本文件**只是计划**：本轮没有修改任何论文文件，只写了本文件与 `CRITIQUE_RB2_R3.md`。
- 依据：本轮重新读取的 `D:\BrickMore\Essay\BrickMore\V1.5\main.tex`（33,614 字节，2026-11-14 23:36）和 `V1.5\REVIEW_V1.5.md`。R0 阶段按要求没有读 RB1 的任何文件；R1 阶段按 PRTS 交叉评审要求读取了 `PLAN_RB1_R0.md`（评审意见见 `CRITIQUE_RB2_R1.md`）。
- 评审口径：GSR-VLM workshop **只看 Topic 5**「Learning spatial representations: Pretraining, fine-tuning, reinforcement learning, and data generation for improving geometric and spatial reasoning」，不考虑 Topic 2。
- 硬约束：
  - AAAI-27 模板（`aaai2027.sty` 2027.1，`[submission]`）；
  - 正文 ≤ 7 页（参考文献、附录不限）；
  - 截止 **2026-11-20 19:59（UTC+8）**。OpenReview Submission invitation 的 `duedate`＝1795175940000 ms，换算后正是 2026-11-20 19:59 UTC+8（11:59 UTC）。
- 铁律：
  - 不编造数字或文献。本计划中每个建议写入论文的数字都标了**项目文件路径**；新增文献都经 arXiv API 核对。
  - 不把模型称为 VLM，不宣称做过预训练或 RL。
  - 没有用户同意，不改核心结论、不删整节、不做新实验。
- 写作时间：R0 2026-11-15 00:40（UTC+8）；R1 约 00:56；R2 约 01:06；R3 约 01:25（UTC+8）。R2 阶段读取了 `CRITIQUE_RB1_R1.md` 与 `PLAN_RB1_R1.md`，评审意见见 `CRITIQUE_RB2_R2.md`。R3 阶段读取了 `CRITIQUE_RB1_R2.md` 与 `PLAN_RB1_R2.md`，评审意见见 `CRITIQUE_RB2_R3.md`。R0–R2 文件保持不变。

---

## 仍有分歧（R3 更新：RB1 R2 与 RB2 R3）

### A. RB1 与 RB2 之间仍存在的分歧（2 项）

| # | 议题 | RB1 立场（PLAN_RB1_R2 / CRITIQUE_RB1_R2） | RB2 立场（本文件） | 证据 | 由什么裁定 |
|---|---|---|---|---|---|
| 1 | 525 条诊断与 114 条主对比的关系怎么写 | “不同交付、不同来源目录的两套评测……不能推断同一批生成”（CRITIQUE_RB1_R2 N1、专题 (a)） | 来源目录确实不同，但 35 条重叠就是同一批生成的同一输出（连同首批共 45 条），并且是人工判决挑出的最佳；正文写 “the 525-prompt diagnostic batch is part of the candidate pool from which 35 of the 114 comparison outputs were selected”，不写 additional、separate 或 taken from | `selected_manifest.jsonl`（`source_kind=judged` 45 条）；`汇总交付\资料与记录\best_all.json`（`choice_id` 45/45 命中）；eval_630 输出 LDR 的零件行数与 `part_count` 45/45 相同；`eval_630\README.md` L14、L91–94（详见 CRITIQUE_RB2_R3 核对 (a)） | **由文件裁定，无需用户**；是否写入诊断本身仍是 U12 |
| 2 | 标题 | 推荐 B′ | 略偏好 A，也接受 B′；R3 起两者并列，不再论证 | 两者都不含虚假主张 | **只有用户能决定**（U1） |

### B. 双方立场已一致、只等用户拍板的事项

| # | 议题 | 一致立场 | 用户须做 |
|---|---|---|---|
| 3 | 中文历史图 image13–19（U4） | 默认 C′（保留，附录段首加说明，image14/17/19 的图注改指发布报告，image18 加 “criteria differ” 图注）；A（移出 PDF）作为可选项，**不再标 ★** | 选 A / C / C′ / B |
| 4 | 525 条诊断是否写入（U12） | 正文一段，**表默认放附录**；摘要不放数字；数字只出现一次 | 是否批准 |
| 5 | 显著性检验（U5） | 符号检验 + Wilcoxon，6 次比较，Holm 校正，不预填 p 值 | 是否批准写入新 p 值 |
| 6 | 评测权重（U10） | 未确认前不写 “all evaluated outputs use this checkpoint” | 确认其余 64 条 BrickMore 输出的权重 |
| 7 | 79,301 vs 396,610 / token（U3） | 11-17 24:00 前找清单，找不到就用 C′ 拆表 | 能否提供清单 |
| 8 | 种子 / 档位规则（U13） | 只陈述字段计数，不写 “default protocol of Algorithm 1” | 说明实际规则，以及 600 s 档的来历 |

### C. R3 新增、等 RB1 评议的条目（目前不是分歧）

| # | 条目 | 内容 | 证据 |
|---|---|---|---|
| 9 | **E-9（P0）** 选择效应披露 | §5.1 写明：45/114 条 BrickMore 输出连同其提示词，是从同组 6 个候选中人工判为最佳者；其余 69 条来自后续的补缺、重生成和复审轮次 | `selected_manifest.jsonl` 的 `source_kind`；`best_all.json`；`eval_630\README.md` L14、L91–94 |
| 10 | **U14** BrickGPT 运行配置 | 记录值 `max_regen=8`、`use_gurobi=False` 与 BrickGPT 论文的“最多 100 次 rollback、Gurobi”不同；默认不写，由用户确认后再决定 | `brickgpt_generation_summary.jsonl`；`Essay\brickGPT\2505.05469v3.pdf` 第 6、8 页 |

已经消除的分歧（R3 新增的消除项打 ✓，不再列入上表）：
- ✓ 摘要中的诊断数字：RB2 采纳 RB1，摘要不放数字（R2 分歧 #2）；
- ✓ `max_bricks` 与 66/114 stable：双方都不写；核对 (b) 确认项目中没有任何定义（R2 分歧 #3）；
- ✓ 模型卡脚注：双方都不提（RB1 接受 D-2；R2 分歧 #4）；
- ✓ “geometric reasoning” 属于 Topic 5 用语：RB1 接受 A-6（R2 分歧 #5）；
- ✓ checklist 不作 OpenReview 附件：RB1 接受 A-5（R2 分歧 #6）；
- ✓ 评测脚本引用 Deploy 副本（a90e851a6a01）：RB1 接受 A-3（R2 分歧 #7）；
- ✓ Holm 校正：RB1 接受 A-10（R2 分歧 #8）；
- ✓ 中文图的默认动作：RB2 接受默认 C′（RB1 B-2 反驳）；
- 编译路径、References 规则、Algorithm 1 不改排、A-2/L-1/I-2 的优先级：R2 已消除。

---

## R3 变更记录（相对 PLAN_RB2_R2.md）

R2 保持不变。逐条依据见 `CRITIQUE_RB2_R3.md`（Part 1 共 15 条：接受 13、部分接受 2、反驳 0）。

1. **新增 E-9（P0）**：主对比的选择效应披露（核对 (a) 的推论）。P0 从 6 条增为 **7 条**。
2. **新增 U14**：BrickGPT 运行配置（`max_regen=8`、`use_gurobi=False`）与其论文配置不同。默认不写进论文。U 从 13 条增为 **14 条**。
3. **525/114 关系（N1）**：全文改为“候选池”表述，删除 “separate diagnostic run”；U12 第 3 点、E-2 正文和风险栏同步修改。
4. **摘要（N4、N9；R2 分歧 #2）**：删去含 46/525 的【】句，改为可选的定性半句；8.8% 等诊断数字只出现在 E-2。
5. **E-2 版式（RB1 R2）**：诊断表默认放附录 C，正文只留一段；页面预算从 +0.35 改为 +0.20；兜底顺序相应调整。
6. **M-4（N9）**：改为指向 E-2 的引用型条目，不再单列档位数字；P1 从 22 条减为 **21 条**。
7. **§0.2、§0.3（N2）**：删去“懂体素形状”和“体素形状 vs 钉柱咬合”。
8. **U3（N13）**：删去含 “sample counts are taken from the training manifest” 的旧兜底段，只保留选项 C′。
9. **U4（B-2）**：默认 C′，A 不再标 ★。撤回“image18(a) 不可复核”：`best_all.json` 实际在 `BrickMore_汇总交付_20261107\资料与记录\`，蓝柱和红柱都已复算，与图一致。image18 加 “criteria differ” 图注。
10. **U8（N7 残留）**：证据栏删去 “logit scale/bias” 的说法。
11. **U10**：补 `provenance.json` L3 的 revision `92d1c595f5fe…`，并写明 `92d1c595`（提交号）与 `75f79af15dd7…`（文件哈希）属于不同的标识体系。
12. **U12**：79/105 人工判决改为“可从 `best_all.json` 复算，但正文不用”。
13. **U13**：补主对比中的 3 个特例（bench-L1V5、bench-L2V4 用 600 s 档；basket-L3V1 带 `regen_seed` 2027）。
14. **D-1、U7、APP-2（D-1 附注）**：直接引用 relaxed 与 strict 的 summary 行号，不再写“执行时核实”。APP-2 补出 Strict v3 行和 Relaxed 行的体素变化。
15. **I-3（N5）**：删去对 “side by side” 原句的引用，改为写进 §4 不做清单。
16. **B-1、§5（N14 残留）**：作者名单已补全，删去“执行时补全”“前 6 位”。
17. **§4、§5、§6、§7、§8**：同步上述各项修改（不做清单、来源表、风险、时间线、计数）。
18. **条目数**：P0 7，P1 21，P2 10，U 14，合计 **52**。

---

## R2 变更记录（相对 PLAN_RB2_R1.md）

R1 保持不变。逐条依据见 `CRITIQUE_RB2_R2.md` Part 1（C1–C15，接受 12、部分接受 3、反驳 0）。

1. **优先级（C6）**：A-2 摘要重写、L-1 Scope 改写、I-2 引言去重由 P0 降为 P1（I-2 一并调整，与 RB1 R1 吸收时的定级一致）。P0 从 9 条降为 **6 条**，P1 从 19 条增为 **22 条**。
2. **页面规则（C11）**：§1 与 G-1 的验收标准改为“第 7 页之后没有正文（摘要到结论）”，References 可以从第 8 页开始。依据 gsr-vlm.org 原文与 AuthorKit27 L391（原文见 CRITIQUE §K-c）。
3. **兜底（C12）**：删除 “Algorithm 1 改为 `figure*`”（违反 AuthorKit27 L617 的算法图注格式）。新的兜底顺序：E-2 诊断表移到附录 → Figure 3 移到附录 → Table 2 并入附录 B → E-3 只留一句。
4. **525 条诊断（C8、C9、§K-b）**：
   - 全文删去 “additional” 与 “reproduces voxel-level shape well”；
   - E-2 不再写 “default protocol of Algorithm 1”，改写为：默认种子阶梯 495 条，recovery path 30 条（28 条 regen 加 2 条 600 s，两组不重叠，已复核）；
   - 补充 manifest `attempt` 分布：@42 338、@104 134、@2026 53；
   - 补充 525 条与 114 条主对比的 caption 重叠：35 条；
   - 新增 **U13**：README L55 的种子阶梯触发规则与 Algorithm 1 不一致，需要用户说明哪个是实际运行的规则。
5. **E-1（C10）**：删去 “with the model's learned scale and bias”。
6. **L-1（C13）**：删去 “connectivity-based rewards”，改为 “connectivity-aware decoding … outside the scope of this work”。
7. **G-3（C14）**：TLDR 不再使用 79k。
8. **B-1（C15）**：三篇文献的 bib 补全作者（已在 arxiv.org 摘要页核对）。
9. **U2（C1）**：结论改为“按 OpenReview authors 字段的读者限制，审稿人看不到作者”，不说“官方双盲”。
10. **U3（C2）**：“自洽”改为“量级一致、不可替代”；旧兜底中的截止日 “11-18” 统一为 11-17 24:00。
11. **U4（C4、§K-a）**：新增逐图核对结果；未答复时的默认动作改为“保留并更正图注”；新增子项 U4-b（image18）。
12. **条目数**：P0 6，P1 22，P2 10，U 13，合计 **51**。

---

## R1 变更记录（相对 PLAN_RB2_R0.md）

R1 于 2026-11-15 约 00:56（UTC+8）完成。它是在阅读 `PLAN_RB1_R0.md` 并写出 `CRITIQUE_RB2_R1.md` 之后修订的。`PLAN_RB2_R0.md` 保持不变。

**吸收自 RB1 的条目**（括号内为 RB1 原编号，对应 CRITIQUE 的 E-x）：
1. U3 新增兜底选项 C′：79,301 与 396,610 分开写，不把 79,322 填进表格（RB1 A3-1–3、C5.3；E-1）。措辞已去掉 “released model card” 和 “training report”（理由见 CRITIQUE D-1、D-2）。
2. U3 与 §4：不用 24,448 × 25.3 h 的乘积替换 token 数（RB1 §0.2、A3-4；E-2）。
3. 新增 **D-7（P2）**：validation 与 test 的命名脚注（RB1 A3-5、C6.2；E-3）。
4. U5：$P_{\mathrm{inv}}$ 不做检验（RB1 A5；E-4）。
5. E-8 重写：只写 BrickGPT 原生 $20^3$ 世界与 seed 42（RB1 C9.1 的一部分；E-5）。
6. E-3：105 组等权与 L1–L5 数字已用 `scores.csv` 复算（RB1 D 表；E-6）。
7. G-1：增加 letter 纸张与 “Anonymous submission” 两项检查（RB1 E 编译检查；E-7）。
8. U2：增加可选的“向组委会询问双盲”，由用户发送（RB1 A2-3；E-8）。
9. U1：增加 RB1 的标题候选，作为选项 B′（RB1 A1；E-9）。
10. §4：`abstract_introduction.md` 不在范围内（RB1 A9-3；E-10）。
11. U5、E-3：措辞写成 “re-analysis”，不写 “new evaluation”（RB1 G；E-11）。
12. §4：锁定主表与 Table 4 数字，并已复核（RB1 C9.2；E-12）。
13. U4：增加 RB1 的“保留中文图并加说明”，作为用户不同意删除时的备选 C′（RB1 A4；CRITIQUE B-2）。

**交叉核对引出的自我更正**：
- U9：删去 R0 中“Overleaf 免费版可能编译超时”的说法。实测 V1.4 在 box 上 `latexmk` 全流程 3.6 s，低于免费版 10 s 上限。改为写明真正的限制：免费版每个项目只能有 1 名协作者，且需要上传未发表稿件。
- E-8：R0 曾打算写 `max_bricks=200`。复核发现 36/114 条 BrickGPT 输出的 `brick_count` 超过 200，因此删去（CRITIQUE A-1）。
- U11：确认 OpenReview 表单没有附加文件字段（CRITIQUE A-5）。
- U3、§7：设定找证据的截止点为 11-17 24:00（CRITIQUE C-3）。
- U2、§6：引用 OpenReview 官方文档，注明公共邮箱注册的审核期“最长 2 周”（CRITIQUE C-1）。

**未吸收（分歧）**，见 CRITIQUE：
- A-6、B-3：引言、贡献、结论保持“不动”；
- A-9：以 Overleaf 为主编译路径；
- A-1、A-2：正文写 `max_bricks=200` 和 66/114 stable；
- A-10：显著性检验不做多重比较校正；
- B-2：中文图默认保留；
- C-1：作者 profile 拖到 11-18 才准备。

**条目数变化**：P2 从 9 增至 10（新增 D-7），合计从 49 增至 **50**。

---

## 0. 速览

### 0.1 现状（V1.5）
- **结构**：§1 Introduction，§2 Related Work，§3 Dataset Construction，§4 BrickMore Text-to-Brick Model（含 Algorithm 1、Table 2、Figure 3 拼图），§5 Comparative Evaluation（Table 3 主表、Table 4 raw/retiled），§6 Limitations，§7 Conclusion，References，附录 A–D。
- **页数**：正文在第 6 页左栏结束，**还有约 1–1.3 页余量**可用于加强 Topic 5 论证。
- **已经做好的**：模板合规、匿名、主表数字核对、BrickGPT 配方表已对照原文（V1.5 P1）、Scope 句（不做预训练/RL、生成器是纯文本 LM）。

### 0.2 Topic 5 视角下的最大短板（按重要性）
1. **缺少能说明“模型学到了什么空间表示”的证据。** 现有评测只有文本–图像对齐和 P_inv，不能回答 Topic 5 关心的“数据生成和微调如何影响几何/空间推理”。
   - **关键发现**：项目里已经有一份**未写进论文**的诊断结果：`D:\BrickMore\brickmore48_eval_630\`（525 条提示词的生成账本和 raw 失败解剖；其中 35 条输出经人工判决进入主对比，见 E-9）。它直接显示：微调模型的 raw 输出大多**不能跨层咬合成单一钉柱连通件**（只统计可复算字段，不对形状保真下结论；R3 按 N2 修改）。这是本轮性价比最高的补强点，**不需要新实验**（见 E-2）。
2. **指标定义还不够精确。** V1.4/V1.5 都把 PE/SigLIP2 写成笼统的 “matching scores”。本轮已从实际评测脚本确认了精确定义（见 E-1、U8）。
3. **数据生成环节缺少“质量 / 效益”数字。** 例如重铺把通过数从 65,503 提到 79,298，`summary.json` 里有现成数字（见 D-1）。
4. 摘要、引言、贡献三处重复同一组数字（80,000 / 21 / 48³ / 79,301 出现 4 次以上），占篇幅又没有推进论证（见 I-2）。
5. 附录里含中文标注、口径为“历史”的图，对英文评审不友好（见 U4；R3：image14/17/18/19 的数字已能复核）。

### 0.3 核心策略（一句话）
把论文从“一个 text-to-brick 系统 + 对齐分数领先”，改写成：

> “用程序化生成的、经几何检查的数据去**微调学习积木装配的空间表示**，并**诊断**这种表示学到了什么、缺了什么（例如 raw 输出能否跨层咬合），再用几何修复补上缺口。”（R3：不写“学会体素形状”，见 N2）

所有支撑都来自项目已有文件；结论（对齐分数最高、P_inv 与 BrickGPT 持平）不变。

### 0.4 条目统计

| 优先级 | 含义 | 条数 |
|---|---|---|
| **P0** | 投稿前必须完成，否则有合规风险或明显错误 | 7 |
| **P1** | 强烈建议，显著提升 Topic 5 契合度或审稿观感 | 21 |
| **P2** | 有余力再做 | 10 |
| **U（待用户确认）** | 需要用户拍板；每条都给了推荐选项和理由 | 14 |
| 合计 | | **52** |

（逐条编号见 §2–§3，统计核对见 §8。）

---

## 1. 页面预算（正文 ≤ 7 页）

V1.5 正文约 5.5–6 页（第 6 页左栏结束）。每完成一批修改就重新编译，并用以下命令核对正文结束位置：

```
pdftotext -f N -l N main.pdf -   # 查找 "References" 所在页
```

**验收标准（R2 更正）：第 7 页之后不能有正文（摘要到结论）的文字**，References 可以从第 8 页开始。依据：gsr-vlm.org 原文 “Up to 7 pages of main content, with no page limit for references and appendices”；AuthorKit27 L391 “References must flow directly after the text without breaks”。用 `pdftotext` 找到 “Conclusion” 段的最后一行，确认它在第 7 页或更早。

| 变化 | 条目 | 估计页面影响 |
|---|---|---|
| 摘要压缩 | A-2 | −0.05 |
| 引言去重 | I-2 | −0.15 |
| 新增 Topic 5 研究问题段 | I-3 | +0.10 |
| 相关工作新增一段（3 篇文献） | R-1/R-2 | +0.12 |
| 数据集：转换效益句 + Table 1 两行 | D-1/D-2 | +0.08 |
| 指标精确定义（替换原句，净增少） | E-1 | +0.03 |
| **新增 §5.x 生成诊断（R3：一段，表默认放附录）** | E-2 | +0.20 |
| 选择效应披露（R3 新增） | E-9 | +0.04 |
| 分级别 / 稳健性两句 | E-3/E-4 | +0.08 |
| 局限性与结论改写 | L-1/C-1 | +0.05 |
| 显著性检验一句（若 U5 同意） | U5 | +0.03 |
| **合计** | | **约 +0.54 页 → 正文约 6.1–6.5 页，仍 ≤ 7** |

兜底（R2 更正）：如果超出，按以下顺序处理：
（R3：E-2 诊断表已默认放附录 C，采纳 RB1。如果编译后余量 ≥ 0.2 页，可由作者决定把表放回正文。）
1. Figure 3 拼图移到附录 C（约 −0.35 页）；
2. Table 2 微调配置并入附录 B（约 −0.2 页）；
3. E-3 只留一句。

**Algorithm 1 不改排、不移出**：AuthorKit27 L617 要求算法 “caption should appear in the header, left-justified and enclosed between horizontal lines”，改成 `figure*` 会破坏这一格式；`REVIEW_V1.5.md` L6 也约定 “Algorithm 1 保留在正文”。

---

## 2. 待用户确认（U1–U14）：推荐选项与理由

> 这些条目没有用户同意前**不动正文**。每条给出推荐选项（★）。

### U1 标题（当前 `\title{BrickMore}`）
- **问题**：AAAI 要求描述性、mixed case 的标题。只有一个系统名，看不出与 Topic 5 的关系。
- **选项**：
  - A（RB2 略偏好）：`BrickMore: Learning Stud-Connected Brick Assembly from Agentically Generated Voxel Data`
  - B：`BrickMore: Fine-Tuning Language Models on Programmatically Generated Data for Text-to-Brick Assembly`
  - B′（RB1 A1 推荐）：`BrickMore: Learning Spatial Brick Assemblies by Agentic Data Generation and Language-Model Fine-Tuning`。它直接对应 Topic 5 的 “fine-tuning … data generation” 用词，也可以接受；缺点是 “Spatial Brick Assemblies” 略显生硬，并且没有点出钉柱连通这一区别；
  - C：保持 `BrickMore`。
- **R3**：A 与 B′ 并列，由用户圈定，RB2 不再论证。A 的理由：
  - 同时点出 Topic 5 的两个关键词：learning（微调）和 generated data（数据生成）；
  - “Stud-Connected” 点明几何约束，是本文和 BrickGPT/BrickNet 的区别；
  - 不含 VLM、RL 等不实字样；
  - 符合 AAAI 大小写规则（介词 from 小写，连字符两侧都大写：Stud-Connected）。
- **怎么改**：`\title{BrickMore: Learning Stud-Connected Brick Assembly from Agentically Generated Voxel Data}`。OpenReview 的 title 字段同步修改。
- 工作量 5 分钟；页面影响约 +1 行（标题可能折行）；不需要新实验；风险是标题过长时折成两行，可以接受。

### U2 作者信息，以及是否双盲
- **核实结果**（2026-11-15 00:45 UTC+8）：
  - 官网 https://gsr-vlm.org/ 没有写“double-blind”字样；
  - OpenReview `AAAI.org/2027/Workshop/GSR-VLM/-/Submission` 的配置显示，`authors` 字段的 readers 只有 `GSR-VLM`（程序委员会）和 `Submission{n}/Authors`，**审稿人看不到作者**；审稿人匿名名称为 `Reviewer_`；
  - 表单含 `data_release`：“accepted submissions, along with their author names, will be released to the public after the conference”；
  - **所有作者必须先有 OpenReview profile**：“All authors must have an OpenReview profile prior to submitting a paper”。
- **结论（R2 措辞）**：按 OpenReview 对 `authors` 字段的读者限制，审稿人看不到作者，因此按匿名审稿准备。官网没有写 “double-blind”，论文和表单中都不写“官方双盲”。
- **推荐 ★**：
  - 保持 `\usepackage[submission]{aaai2027}`，PDF 中不出现作者；
  - 作者姓名只填在 OpenReview 表单里；
  - **今天（11-15）就让所有作者注册或确认已有 OpenReview profile**。OpenReview 官方文档（docs.openreview.net “Signing up for OpenReview”）写明，用公共邮箱域名注册 “may take up to 2 weeks in moderation”；添加并验证机构邮箱可以加速。这是**截止前最大的非写作风险**；
  - 可选（吸收自 RB1 A2）：若要百分之百确认双盲，由**用户本人**向组委会联系邮箱 `li.li02@usc.edu`（见 OpenReview group 资料）发一封短邮件询问。不必等回复，先按匿名准备；
  - 源码中的 `Author Name(s) to Be Added` 占位符保持不变，录用后再换成 camera-ready。
- **附带检查（P0，见 G-2）**：正文、附录、图片里不能出现 HuggingFace 仓库名或 GitHub 用户名。项目文件中有：
  - `Kyle308666/BrickGPT-Qwen3-1.7B-BrickMore-48`，见 `D:\BrickMore\downloads\BrickGPT-Qwen3-1.7B-BrickMore-48\README.md`；
  - `BuShiGeMenn/BrickMore`，见 `D:\BrickMore\Train\datasets\piano_table_retile_7620\download_manifest.json`；
  - V1.5 的 `main.tex` 目前没有这两个名字。**投稿前必须再 grep 一次，也要检查图片内文字**。
- 工作量：注册由用户完成；论文侧 0。

### U3 79,301 还是 79,322 个模型；2,228,044,818 还是约 2.19B tokens
- **证据**：
  - `D:\BrickMore\Train\datasets\CURRENT_DATASET_STATUS.md`、`README.md`：整合口径 79,301（=79,298−1,902+1,905）；
  - `D:\BrickMore\Train\datasets\retile_assembly_80000\summary.json`：`geometryPassed=79298`；
  - `D:\BrickMore\downloads\BrickGPT-Qwen3-1.7B-BrickMore-48\README.md`（模型卡）：“79,322 models × 5 captions = 396,610 samples (356,955 train / 39,655 test …)”和“~2.19B tokens total”；
  - 论文 Table 1：79,301 / 396,610 / 2,228,044,818。79,301×5＝396,505，与 396,610 差 105；79,322×5＝396,610，自洽；
  - token：论文的 24,448 tokens/s × 25.3 h 精确为 2,226,723,840，与 2,228,044,818 差 1,320,978。只能说量级一致（25.3 h 是约数），**不能**算同一观测，也不能替代表中数字；与 “~2.19B” 不一致（差约 1.7%）；
  - 训练日志 `trainer_state.json`、`build_stats.json` 在 `D:\BrickMore` 下**找不到**（V1.4 已全盘搜索）。
- **选项**：
  - ★A：请用户去训练服务器找到训练清单或日志（`trainer_state.json`、训练集 jsonl 行数、`train_brickmore.log`），以实测为准修正 Table 1 和附录配方表；
  - B：找不到实测证据时，正文改为只写“about 396.6k samples from the integrated corpus”这类不暗示精确模型数的写法——**不推荐**，会削弱可复现性；
  - C：维持现状（79,301 与 396,610 并存），审稿人一算就会发现乘不上——**不推荐**。
  - **C′（兜底，吸收自 RB1 A3，措辞已修正）**：若 **11-17 24:00（UTC+8）** 前仍找不到清单，就把两种口径分开写，不新增数字，也不提模型卡：
    - Table 1 用 `\midrule` 分成 “Dataset (release reports)” 与 “Fine-tuning corpus” 两块。79,301 只出现在前一块，并保留 “79,298−1,902+1,905, not a new full verification” 的限定；
    - 后一块写 396,610（356,955 / 39,655, split by model）和 2,228,044,818 tokens，表注写：“Corpus counts are as recorded in our training run; their per-model reconciliation with the integrated release count is being re-checked.”；
    - **不**写 “released model card” 或 “training report”（理由：匿名线索和无出处的来源声明，见 CRITIQUE D-1、D-2）；**不**用 24,448 × 25.3 h 的乘积（2,226,723,840）替换 token 数；**不**写“21 个额外模型”（105/5 只是算术）。
- **推荐 A 的理由**：只有实测清单能裁定。若实测是 79,322，需要在 §3.3 解释它与 79,301 的差别（例如训练清单构建时间早于钢琴替换），但这个解释**必须由用户提供证据**，不能代写。
- （R3 按 N13 删除 R2 的旧兜底段：它含 “sample counts are taken from the training manifest”，与选项 C′ 矛盾。兜底只用 C′。）
- 工作量：找证据由用户完成；改稿 20 分钟。页面影响 0。不需要新实验。风险：若实测是 79,322，§3.3 “Fine-tuning uses only geometrically passing models”是否仍然成立，也需要用户核实。

### U4 附录中含中文标注的历史图（R2 重写）
- **规则**：删除或重绘必须用户同意（`V1.5\REVIEW_V1.5.md` L6；`V1.4\REVIEW_V1.4.md` L101）。
- **R2 逐图核对**（V1.5 `figures\image13–19.png`）：

| 图 | 内容 | 数字能否复核 |
|---|---|---|
| image13 | 接触重力筛查示意图（中文标注） | 示意图，无统计数字 |
| image14 | 7,902 / 65,503 / 79,298 / 79,301；2,650 / 478；220 / 128 | 能（220 / 128 本轮未逐个复核）。来源：retile `summary.json`、relaxed `assembly_summary.json` L8–L10、L75、`CURRENT_DATASET_STATUS.md` |
| image15 | 21 类的几何通过率 | 未逐类复核 |
| image16 | 160 模型抽样 22 / 55 / 56 / 57 | 未找到来源，不能复核 |
| image17 | 63,808 / 14,574；2,650 / 45,490 / 17,024 / 14,497 | 能。来源同 image14 |
| image18 | (a) BrickGPT stable 对比 BrickMore “人工判定”；(b)(c) 零件规模 | **R3 更正：(a) 能复核**。蓝柱＝`BrickMore_汇总交付_20261107\资料与记录\best_all.json` 各级 `choice_id≠NONE` 的组数 / 21：18、16、17、15、13，即 85.7 / 76.2 / 81.0 / 71.4 / 61.9%；红柱＝`brickgpt_generation_summary.jsonl` 各级 `stable=True` 的比例：13/21、15/21、12/23、12/25、14/24，即 61.9 / 71.4 / 52.2 / 48.0 / 58.3%。与图一致。但两者**判据不同**（组级人工“6 选 1”对单样本自动稳定标记），图题本身也写了“判据不同”。(b)(c) 未逐个复核 |
| image19 | BrickGPT 拒绝原因 8,207 / 2,757 / 8 / 4；BrickNet 失败类型 24 / 10 / 10 / 6 / 3 | 能。来源：jsonl、`bricknet_generation_summary.md` |

- **选项**：
  - A（可选，R3 不再标 ★）：从提交 PDF 中移除 image13–19（用 `\iffalse … \fi` 注释，文件保留）。image14、17 用 APP-2 英文表替代（数字已复核）；image19 用一张英文小表替代（来源同上）；
  - B：重绘英文版，共 7 张，约 8–12 小时，不推荐；
  - ★C′（RB1 方案，双方一致的**默认动作**）：全部保留；附录段首加 “Historical material with Chinese labels; not used for any claim.”；把 image14、17、19 图注中的 “require verification” 改为 “values as in the corresponding release reports”（这些数字已复核）；
  - **U4-b（R3 重写）**：image18 保留，图注补一句：“Panel (a) compares different criteria—BrickGPT's per-prompt stability flag versus whether human review found an acceptable BrickMore output among six candidates per category–level group—and is not a like-for-like comparison.” R2 的“不可复核”理由撤回（见上表）。用户若选 A，image18 一并移出。
- **A 的理由（供用户参考，R3 不作为推荐）**：英文投稿中出现中文图观感差；image14/17/19 的数字可以用英文表无损替代。
- **C′ 的理由（R3 采纳为默认）**：这些图全部在附录，正文页数影响为 0（RB1 专题 (d)：PDF 第 7、8、9、10、13 页）；删除必须经用户同意（`V1.5\REVIEW_V1.5.md` L6）；除 image15、16 外，数字均已复核。
- 工作量：A 约 45 分钟（含两张英文表）；C′ 约 10 分钟。正文页面影响 0；选 A 时附录约减少 4–5 页。

### U5 是否补显著性检验
- **数据**：`D:\BrickMore\Results\three_model_comparison_20261111\intake\Results\comparison_full\report\scores.csv`（462 行，含逐 prompt 的 vqa/pe/siglip2/pinv）。胜/平/负已在 `...\analysis\三模型测评结果分析.md` 中给出：91/0/23、95/0/19、91/0/23。
- **推荐 ★：做**。在 114 条配对上做**双侧符号检验**（只用胜负数，最透明）和 **Wilcoxon 符号秩检验**，3 个指标 × 2 个对手（BrickGPT、BrickNet），Holm 校正。
- **补充（R1）**：
  - $P_{\mathrm{inv}}$ 不做检验：BrickMore 与 BrickGPT 都是 0.00%，没有区分度（同意 RB1 A5）；
  - 对 BrickNet 的胜场本轮从 `scores.csv` 复算为 97 / 98 / 102（VQA / PE / SigLIP2，无平局），仅作为计划依据；
  - 共 3 × 2 = 6 次检验，用 Holm 校正（不同意 RB1 A5 的“不校正”）；bootstrap 95% CI 可选，放附录；
  - 文字写成 “re-analysis of the existing per-prompt scores”，不写 “new evaluation”。
- **理由**：
  - 不需要新数据或新实验，只是对已有逐条记录的统计；
  - 审稿人几乎一定会问；
  - 当前正文写着“no significance test is reported”，属于自曝短板。
- **约束**：这会产生**新数字**（p 值），需要用户同意，并把计算脚本和输出存进项目（建议 `V1.6\analysis\significance.py` 和 `significance.json`），论文引用该文件。**本计划不预先给出任何 p 值。**
- **建议正文句子**（数值待计算后填写，`[p]` 为占位）：
  ```latex
  Against BrickGPT, two-sided sign tests over the 114 paired prompts give
  $p=[p_{\mathrm{VQA}}]$, $[p_{\mathrm{PE}}]$, and $[p_{\mathrm{SigLIP2}}]$ (Holm-corrected; Wilcoxon signed-rank tests agree, Appendix~\ref{app:eval}).
  ```
- 工作量约 1 小时（脚本、复核、写句）；页面影响 +2 行。风险：若某项不显著，就如实写；结论“均值最高”不变，不能改写成“显著优于”。

### U6 是否补空间推理评测
- **推荐 ★：截止前不补新的空间推理基准**；改为把 E-2 的**结构诊断**（raw 输出是否单一钉柱连通、钉柱分量数、悬空碎片比例）明确表述为“对学到的空间表示的直接几何探针”。
- **理由**：
  - 正规空间推理评测（空间关系问答、装配规划）需要设计协议、生成和打分，5 天内做不扎实；
  - 而 E-2 的诊断数字已经在项目文件里，而且正是 Topic 5 想看的“学到的几何约束”。
- **备选**（需用户批准，属新实验）：在现有 114/525 输出上做“尺寸遵从”检查——L4/L5 提示词含明确尺寸（见 `brickmore48_eval_630\README.md` §1），可以比对 bounding box 与提示中的尺寸。约 4–6 小时，有解析提示词的风险。**不建议在本轮做。**
- 页面影响 0（若采用推荐方案）。

### U7 是否补消融
- **推荐 ★：不新训模型**。单次训练 25.3 h × 8 GPU（论文 Table 2 与模型卡），重跑数据规模、描述层级、序列化方式等消融，5 天内不现实。
- **零成本的“类消融”证据（P1，可直接做）**：
  1. **数据侧**（D-1）：同一批 80,000 个模型，转换策略从 relaxed 到 retile，几何通过数从 **65,503** 变为 **79,298**；救回 **13,795** 个；新增体素 **228,582**、删除 **125**；**31,532** 个成功模型零体素改动。来源：`D:\BrickMore\Train\datasets\retile_assembly_80000\summary.json`（字段 `baselinePassed`、`geometryPassed`、`recoveredFailures`、`addedVoxelCount`、`removedVoxelCount`、`zeroVoxelChangeSuccessfulModels`）。strict v3 = 7,902 已复核：`D:\BrickMore\Train\datasets\assembly_80000\assembly_summary.json` L9 `"success": 7902`，与 relaxed summary L75 `"originalPublishedGeometryPassed": 7902` 一致（R3）。
  2. **推理侧**：raw vs retiled（Table 4，已在正文），加上 E-2 的 MILP 档位分布。
- **约束**：表述为“conversion-strategy comparison / repair analysis”，**不要叫 ablation of the learned model**。

### U8 PE / SigLIP2 分数：余弦相似度还是 sigmoid 概率
- **已用项目文件确认（推荐 ★：按脚本如实写）**。评测脚本 `D:\BrickMore\Deploy\build\comparison_20261110\BrickMoreComparison\Scripts\evaluate_paper_images.py` 的 SHA-256 前缀 `a90e851a6a01`，与 `...\three_model_comparison_20261111\intake\Results\comparison_full\{vqa,pe,siglip2}.config.json` 中 `sources.evaluate_paper_images.py` 记录的 `a90e851a6a0189d9…` 一致，可以确认是本次评测实际使用的版本：
  - **PE**：`encode_image(normalize=True)`、`encode_text(normalize=True)`，再 L2 归一化后点积 → **余弦相似度**（取值 [−1, 1]）；
  - **SigLIP2**：`model(**inputs).logits_per_image[:,0].float().sigmoid()` → `logits_per_image` 的 **sigmoid 概率**（取值 (0, 1)；正文不描述 logit 的内部构成，见 N7）；
  - **VQAScore**：`logits.float().softmax(dim=-1)[..., yes_id]`，注释“Full-vocabulary softmax, not Yes/No renormalization”→ 首个生成位置上，单 token “Yes” 的**全词表 softmax 概率**；
  - 聚合：8 视角取最大，再对 prompt 平均（config `pooling: "max-of-8 then mean-over-models"`）。
- **需要用户确认的只是**：同意按上述定义写入论文（见 E-1）。

### U9 编译环境：MiKTeX 还是 Overleaf
- **事实**：`aaai2027.sty` 必须用 pdfTeX，原来的 Tectonic 用不了。用户 Windows 机器没有 pdflatex/latexmk（V1.4 已核实）。V1.4/V1.5 都在 Grok Bot box 上用 TinyTeX（TeX Live 2026，pdfTeX 1.40.29）编译成功。
- **选项**：
  - ★A：**box 上的 TinyTeX 作为主编译，用户本机装 MiKTeX 作为本地备份**；
  - B：Overleaf；
  - C：只用 box。
- **推荐 A 的理由**：
  - box 环境已验证可以产出合规 PDF（Type 1 字体、无错误）；
  - MiKTeX 能按需自动装宏包（newtx、algorithms 等），用户离线也能自己编；
  - 未发表稿件不必上传第三方平台；
  - （R1 更正）编译时间不是问题：本轮在 box 上实测，V1.4（16 页，同结构）`latexmk -pdf` 全流程 3.6 s、单次 pdflatex 0.8 s，低于 Overleaf 免费版 10 s 上限（docs.overleaf.com plan limits）。Overleaf 免费版真正的限制是**每个项目只能有 1 名协作者**。所以 Overleaf（pdfLaTeX）可以作为第三备选，但不适合作为“多人共同检查”的主路径（与 RB1 A8 的分歧）。
- **MiKTeX 步骤**（用户执行，约 20 分钟）：
  1. 从 miktex.org 下载安装（Install missing packages: Yes）；
  2. 在 `V1.6` 目录运行 `latexmk -pdf -interaction=nonstopmode main.tex`；latexmk 需要 Perl，MiKTeX 会提示安装 Strawberry Perl，否则改用 `pdflatex` → `bibtex` → `pdflatex` ×2；
  3. 用 `scripts\build.ps1`（V1.4 已改为 latexmk）。

### U10 评测所用权重与“发布的 step-79,000 权重”是否同一版本（新增）
- **证据**：
  - `D:\BrickMore\brickmore48_eval_630\README.md` 写的是 “权重版本 `92d1c595`”；
  - `D:\BrickMore\downloads\BrickGPT-Qwen3-1.7B-BrickMore-48\model.sha256` 是 `75f79af15dd7…`；
  - 两者标识体系不同，无法直接判断是否同一份权重；
  - 主对比的 BrickMore 样本 `original_source` 指向 `...\BrickMore_汇总交付_20261107\展示\models\judged_*.glb`，见 `selected_manifest.jsonl`。
  - **R3 新证据**：
    - `D:\BrickMore\BrickNet_BrickGPT_Compirasion\BrickMore_汇总交付_20261107\资料与记录\provenance.json` L3：`"revision": "92d1c595f5fe076971cc2633d6844f097a84eef3"`。这是 Git 提交号，与 eval_630 README L5 的 `92d1c595` 一致；`75f79af15dd7…` 则是文件 sha256，两者标识体系不同；
    - 主对比 45 条 `judged` 输出就是 eval_630 的输出（CRITIQUE_RB2_R3 核对 (a)），所以属于 `92d1c595`；5 条 `regenerated` 应当对应 provenance 所记录的 11-07 重生成包（按交付说明推断）；
    - 其余 64 条（review_59 21、成功的模型 16、round2 12、round3 7、nine_ldr 7、car_trials 1）在项目里**没有找到**权重记录；
    - provenance.json 中的仓库名含账号名，属于匿名风险，任何形式都不能进论文。
- **推荐 ★**：请用户确认 `92d1c595` 就是 step-79,000 的那份权重，并确认上述 64 条输出也来自它（或者说明来自哪个版本）。若能确认 525/114 条输出都来自 step-79,000（`load_best_model_at_end`）的那份权重。确认后，§4.1 可以写“all evaluated outputs are generated with this checkpoint”；无法确认就不写这句（V1.4 已删除过这句未核实的话）。
- 页面影响 0。

### U11 是否附 AAAI Reproducibility Checklist（新增）
- AuthorKit27 附有 `ReproducibilityChecklist.tex`，模板注释写“Check whether the conference requires…”；工作坊官网和 OpenReview 表单都**没有要求**。
- R1 补充：OpenReview Submission 表单**没有**附加文件（supplementary）字段，checklist 只能进 PDF 附录。RB1 A9 “作为 OpenReview 附加文件”不可行。
- **推荐 ★：不附**。理由：不是硬性要求，填写需要逐项表态，有出错风险；时间优先给正文。若用户希望显得规范，可以放在附录最后（不计页），约 1 小时。

### U13 525 条诊断的种子阶梯触发规则（R2 新增）
- **证据**：
  - `brickmore48_eval_630\README.md` L55：“种子阶梯 42 → 104 → 2026（前一个种子产出不合格且不可修复时启用下一个）”；
  - V1.5 `main.tex` L166 与 Algorithm 1：先依次试种子，直到出现 complete 且 valid 的候选，再进入 MILP；
  - manifest 的 `attempt` 分布：@42 338、@104 134、@2026 53；`regen_seed`（S 之外的种子 7 / 555 / 2027 / 12）28 条；600 s 档 2 条（两组不重叠）。
- **R3 补充（主对比中的特例）**：主对比 35 条与 eval_630 重叠的输出中，bench-L1V5、bench-L2V4 用的是 600 s 档（`manifests\manifest_w0.json` L1074、L1150），basket-L3V1 带 `regen_seed` 2027。V1.5 Algorithm 1 的 $T=(12,60,180)$ s 中没有 600 s 档；seed 2027 可以视为 `QueueReseed`。
- **需要用户说明**：哪一种是 525 条诊断实际使用的规则；600 s 档在什么条件下启用。
- **R3 建议**：用户说明后，在 §4.2 末尾加一句如实描述，例如 “Unsolved cases may be retried with a 600\,s tier or a new seed”（措辞以用户说明为准），使 Algorithm 1 覆盖主对比中实际出现的路径；用户不说明就不加，只在 E-2 陈述字段计数。
- **推荐 ★**：E-2 只陈述字段计数（attempt 分布、默认 495 条、recovery 30 条），不写 “generated with the default protocol of Algorithm 1”。如果实际规则与 Algorithm 1 不同，在 E-2 加一句 “the diagnostic run escalates seeds when a draft cannot be repaired”。
- 页面影响 +1 行，不需要新实验。

### U12 是否在正文使用 525 条诊断数据（新增，与 E-2 绑定）
- **推荐 ★：使用，但只用能从原始文件复算的部分**（`manifests\manifest_w{0,1,2}.json`、`results\raw_failure_autopsy.json`）。
- **不用**（无法核实）：
  - README 中的人工判决 79/105 组：R3 更正，`best_all.json` 实际在 `BrickMore_汇总交付_20261107\资料与记录\`（另有两份相同副本），79 可以复算（`choice_id≠NONE`）。但它是组级的人工 6 选 1 结果，**正文不用**，只在 E-9 用于说明 45 条的来历；
  - “与训练集零重叠”：没有对照文件；
  - “82% 碎片紧贴主体（≤1 格）”：autopsy 没有距离字段；
  - README 写的“108–124 s/条”：manifest 实测中位数 93.9 s，范围 22.9–401.6 s，两者矛盾。
- 需要用户确认：
  1. 同意把这批诊断写入正文；
  2. U10 的权重版本；
  3. 这 525 条提示词与主对比 114 条的关系（R3 已由文件确定，无需用户说明）：525 条加 105 条首批构成人工判决的候选池；主对比中 45 条 BrickMore 输出是从这个池中选出的同一文件（其中 35 条在 525 内），其余 69 条来自后续轮次。正文不写 “additional”、“held-out”、“separate” 或 “114 taken from the 525”，表述见 E-2 与 E-9。

### U14 BrickGPT 运行配置是否披露（R3 新增）
- **证据**：
  - `D:\BrickMore\Deploy\build\comparison_20261110\BrickMoreComparison\Provenance\brickgpt_generation_summary.jsonl`：114 条全部是 `max_regen=8`、`use_gurobi=False`、`world_dim=20`、`seed=42`；
  - BrickGPT 论文（项目内 `D:\BrickMore\Essay\brickGPT\2505.05469v3.pdf`）第 8 页：“We allow up to 100 physics-aware rollbacks”；稳定性优化 “is solved using Gurobi”；
  - `max_regen` 是否等同于论文的 rollback 次数，项目里**没有定义**（与 `max_bricks` 相同，见 CRITIQUE_RB2_R3 核对 (b)）。
- **选项**：
  - ★A（默认）：正文不写这些参数，只保留 E-8 的 “native $20^3$ world (seed 42)”；
  - B：用户确认参数语义后，在附录协议里如实写出 BrickGPT 的运行设置，并注明与原文配置不同；
  - C：用户提供事实（例如“使用官方推理脚本的默认参数”）后，在 §6 Evaluation 段写一句“we did not tune BrickGPT's inference settings”。没有用户证据就不写。
- 页面影响 0 到 +1 行。不需要新实验。**禁止**写 “BrickGPT was run with its authors' default configuration”，因为项目文件不支持这句话。

---

## 3. 逐节修改条目

> 格式：**编号｜优先级｜标题**，然后依次是：改什么 / 为什么 / 怎么改（建议文本或 LaTeX）/ 工作量 / 页面影响 / 是否需新实验或新数据 / 风险。

### 3.G 全局与合规

**G-1｜P0｜每批修改后的编译与页数验收**
- 改什么：建立固定的验收流程。
- 为什么：正文 ≤ 7 页是硬约束，新增 E-2 等内容后必须实测。
- 怎么改：在 box 上
  1. `latexmk -g -pdf -interaction=nonstopmode main.tex`；
  2. `grep -n "^!\|Overfull\|undefined" main.log` 必须为空；
  3. 逐页 `pdftotext` 找到结论的最后一行，确认在第 7 页或更早，且第 7 页之后没有正文（References 可以从第 8 页开始，见 §1）；
  4. `pdffonts main.pdf` 全部 Type 1 且已嵌入，没有 Type 3；
  5. `pdfinfo main.pdf` 没有 Title/Author 元数据，且 Page size 为 letter（612 × 792 pts）；
  6. 第 1 页 `pdftotext` 含 “Anonymous submission”（吸收自 RB1 E）。
- 工作量每次 5 分钟。页面影响 0。不需要新实验。风险：无。

**G-2｜P0｜匿名合规复查（PDF 文字、图片内文字、元数据）**
- 改什么：投稿前全文检查。
- 为什么：OpenReview 配置是对审稿人隐藏作者（见 U2）。
- 怎么改：
  - `pdftotext main.pdf - | grep -i -E "kyle|bushigemenn|huggingface|github|D:\\\\|Administrator|CHINAMI"` 应无结果；
  - 用肉眼检查 Figure 1–3 和附录图里没有用户名或路径；
  - 不加 `\begin{links}` 代码/数据链接。如果要给链接，用匿名仓库（如 anonymous.4open.science），**需用户决定**。
- 工作量 15 分钟。页面影响 0。不需要新实验。风险：图片中的小字容易漏看。

**G-3｜P0｜OpenReview 表单素材**
- 改什么：准备表单字段（不是论文文件）。
- 为什么：Submission invitation 要求 title、authors（profile ID）、paper_type（Long Paper / Short Paper）、keywords、TLDR、abstract、pdf（≤ 50 MB）、email_sharing、data_release。
- 怎么改：
  - paper_type 选 **Long Paper**；
  - keywords 建议：`text-to-brick generation; spatial representation learning; procedural data generation; LoRA fine-tuning; geometric assembly; exact cover`；
  - TLDR 建议（R2，不含未裁定的数字）：“We fine-tune a 1.7B language model on agentically generated, geometrically checked brick layouts and diagnose which spatial constraints it learns before MILP retiling enforces stud connectivity.”；
  - abstract 与 PDF 一致（纯文本，去掉 LaTeX）。
- 工作量 20 分钟。页面影响 0。不需要新实验。风险：作者 profile 未通过审核（见 U2）。

**G-4｜P2｜英式 / 美式拼写统一**
- 改什么：正文同时出现 “six-neighbour”（英式）和 “color”（美式）。
- 为什么：AAAI 用美式英语，拼写不统一显得粗糙。
- 怎么改：全部 `neighbour` → `neighbor`（§3.2、§6 各一处）。
- 工作量 2 分钟。页面影响 0。不需要新实验。风险：无。

**G-5｜P1｜术语表统一**
- 改什么：
  - BrickMore = 整个框架 / 系统；
  - BrickMore-48 = 数据集与训练语料；
  - raw / retiled（正文不再出现 stitched，文件名说明保留一次）；
  - “stud-connected component” vs “six-neighbor connected component”；
  - caption levels “L1 (concise) to L5 (detailed)”。
- 为什么：V1.5 §4 标题是 “BrickMore Text-to-Brick Model”，Algorithm 1 输入写 “fine-tuned model θ”，Table 1 caption 写 “fine-tuning corpus”，各处统一后更清楚。
- 怎么改：用 grep 逐个检查；在 §3 首段加一句定义：“We refer to the dataset and training corpus as BrickMore-48 and to the overall framework as BrickMore.”
- 工作量 20 分钟。页面影响 +1 行。不需要新实验。风险：无。

**G-6｜P1｜数字一致性核对表**
- 改什么：把正文出现的每个数字列成表，与来源文件逐一核对（见 §5），提交前跑一遍。
- 为什么：前几轮已多次出现数字口径问题。
- 怎么改：新建 `V1.6\NUMBERS_V1.6.md`（这是 V1.6 执行时的产物，本轮不建）。
- 工作量 40 分钟。页面影响 0。不需要新实验。风险：无。

**G-7｜P2｜Underfull 排版**
- V1.5 P7 遗留，不影响合规。只在最终版还有余量时微调措辞。约 10 分钟。

### 3.A 标题与摘要

**A-1｜U1｜标题**：见 U1。

**A-2｜P1（R2 由 P0 降级）｜摘要重写：突出 Topic 5 学习表示的主线，去掉冗余，加入一句诊断发现**
- 改什么：V1.5 摘要约 260 词，句子 3–4（GPT-6.1 Sol 流程细节）和句子 6–7（修复流程细节）偏长，没有“模型学到了什么”这一句。
- 为什么：Topic 5 审稿人首先看“数据生成 / 微调是否改进了几何空间推理，以及证据是什么”。
- 怎么改（建议全文，约 215 词。【】为条件句：E-2 / U12 同意才保留；数字来源见 §5）：

```latex
\begin{abstract}
Generating brick structures from text requires geometric assembly: bricks must fit in a bounded grid, avoid overlaps, and interlock through studs, not merely resemble the described shape. We study how far a language model can learn such a spatial representation from programmatically generated data. Using GPT-6.1 Sol, an agentic batch-generation pipeline writes parametric generator programs that emit 80,000 voxel models across 21 categories on a $48^3$ grid, each with five bilingual captions of increasing detail. Same-color tiling, connectivity analysis, and local bridging and retiling convert the shapes into brick layouts, and 79,301 models pass the specified geometric checks. We fine-tune Qwen3-1.7B with LoRA on English captions and serialized brick placements, and repair its predictions by solving a shape-preserving exact cover with a single stud-connected component via mixed-integer linear programming (MILP). 【A structural analysis of raw outputs shows that interlocking across layers is the constraint the learned representation most often misses.】 On 114 shared prompts under a common rendering protocol, the evaluated BrickMore outputs (110 retiled, 4 raw) obtain the highest mean scores on three text--image alignment metrics and a mean invalid-placement ratio of 0.00\%, matching BrickGPT.
\end{abstract}
```

- 注意（R3，采纳 RB1，解决 R2 分歧 #2）：摘要**不放诊断数字**。上面的【】句是定性半句，仅在 U12 获批时保留，否则删除。
  - 禁写：“reproduces voxel-level shape well”，以及任何形状保真的说法（autopsy 没有这一度量）；
  - 8.8%、中位数 5 等数字只出现在 E-2（N9）。
- 工作量 20 分钟。页面影响约 −0.05。不需要新实验（数据已有）。风险：U12 未获批就删掉【】句。

**A-3｜P2｜摘要中 “GPT-6.1 Sol”**
- 保持原名（用户给定的事实），不改。只确认全文写法一致（V1.5 一致）。0 分钟。

### 3.I Introduction（§1，V1.5 共 7 段 + 贡献列表）

**I-1｜P1｜第 1 段：加一句空间表示框句**
- 改什么：第 1 段末尾 “…not only whether the overall shape resembles the described object.” 之后。
- 为什么：把问题放进 Topic 5 的“学习空间表示”语境。
- 怎么改（新增句）：
  > “This makes text-to-brick generation a useful testbed for learning spatial representations: the target is discrete, the constraints are exactly checkable, and a model's errors can be measured geometrically rather than only perceptually.”
- 工作量 5 分钟。页面影响 +2 行。不需要新实验。风险：无（是框句，不是结论）。

**I-2｜P1（R2 由 P0 降级）｜第 4–5 段去重**
- 改什么：
  - 第 4 段（“We present BrickMore to study this problem…”）复述了摘要里的 80,000 / 21 / 48³ / 79,301；
  - 第 5 段复述了修复流程；
  - 贡献 1–3 又复述了一遍。
- 为什么：腾出约 0.15 页给 E-2；评审读到第三遍相同数字会扣“写作”分。
- 怎么改：第 4、5 段合并为一段，只保留机制，数字只在贡献列表出现一次：

```latex
We present BrickMore to study this problem. GPT-6.1 Sol writes parametric generator programs that emit voxel models in batches; a conversion pipeline tiles them with same-color bricks and uses local bridging and retiling to address ungrounded components, recording any change to the source voxels. We then fine-tune Qwen3-1.7B~\cite{qwen3} with LoRA~\cite{lora} on English captions and brick-placement sequences, so that the $48^3$ workspace, multi-level captions, and fixed spatial serialization define the representation being learned. Because the model's raw layouts may still overlap or fall apart into stud-disconnected pieces, a post-generation stage forms the voxel union of supported placements, seeks an exact cover with a single stud-connected component by MILP, and queues a new sampling seed when no cover is found within the solver budget. The connectivity check is geometric; physical stability and assembly-order feasibility require separate evaluation.
```

- 工作量 20 分钟。页面影响约 −0.15。不需要新实验。风险：删掉的 “the current output does not include color” 必须在 §4.1 保留（V1.5 §4.1 没有这句，§1 有）→ **把这句移到 §4.1 第 1 段末尾**。

**I-3｜P1｜新增 Topic 5 研究问题与发现预告段（放在原第 6 段“We compare…”之前）**
- 为什么：明确“我们研究什么学习问题、学到了什么”，这是 Topic 5 的核心。
- 怎么改（【】句依赖 U12）：

```latex
Our analysis asks what such a model actually learns from generated data. 【A diagnostic analysis of raw outputs (Section~\ref{sec:diagnostics}) shows that the model's layouts usually fail to interlock across layers and fall apart into several stud-connected pieces.】（R2：引言只写定性，数字只在 §5.x 出现） We therefore treat geometric repair as a complement to, not a substitute for, the learned representation, and we report both raw and retiled results.
```

- **注意**（R3，N5）：引言只写定性。若作者要补一个可核实的细节，只能用 autopsy 字段，例如 “most detached fragments are not grounded”（`raw_failure_autopsy.json`：`orphan_air` 合计 1,320 / `orphan_n` 合计 2,240），而且只能写在 E-2，不写在引言。禁写的 README 定性语句见 §4。
- 工作量 15 分钟。页面影响 +0.10。不需要新实验（数据已有）。风险：依赖 U10/U12。

**I-4｜P1｜贡献列表改写，对齐 Topic 5 的三个环节**
- 为什么：现在三条是“数据管线 / 转换管线 / 微调 + 修复”，数据生成被拆成两条，学习与诊断不突出。
- 怎么改：

```latex
\begin{enumerate}
\item \textbf{Data generation for spatial learning.} An agentic batch-generation pipeline in which GPT-6.1 Sol writes parametric generator programs, producing 80,000 $48^3$ voxel models across 21 categories with five bilingual captions each, and a voxel-to-brick conversion that targets stud-connected layouts rather than voxel adjacency; 79,301 models pass the specified geometric checks.
\item \textbf{Fine-tuned text-to-brick representation.} LoRA fine-tuning of Qwen3-1.7B on serialized placements over a 20-type library in a $48^3$ workspace, with post-generation MILP retiling that enforces a single stud-connected component.
\item \textbf{Geometric diagnosis and evaluation.} 【A structural analysis of raw outputs on 525 prompts showing which spatial constraints the model learns and which it misses,】 and a matched comparison with BrickGPT and BrickNet on 114 prompts under a common rendering protocol.
\end{enumerate}
```

- 工作量 15 分钟。页面影响 0。不需要新实验。风险：第 3 条的【】依赖 U12；不同意时只保留后半句。

**I-5｜P2｜原第 6 段（结果预告）加一句分级别一致性**
- 怎么改（新增）：
  > “The ordering holds at every description level from L1 to L5 (Appendix~\ref{app:eval}).”
- 来源：`D:\BrickMore\Results\three_model_comparison_20261111\analysis\三模型测评结果分析.md`“按 Level 对比”的 VQAScore、PE、SigLIP2 三张表。BrickMore 在 L1–L5 各级三项均为最高，例如 VQAScore L5：0.096763 / 0.074845 / 0.036335。
- 工作量 5 分钟。页面影响 +1 行。不需要新实验。风险：无（已核对 15 个格子都是 BrickMore 最高）。

### 3.R Related Work（§2）

**R-1｜P1｜新增 “Language models for serialized 3D generation” 段**
- 为什么：本文本质是“把 3D 结构序列化成文本，让 LM 微调学习”。这条主线有直接相关工作，审稿人会期待看到。
- 怎么改（文献均已用 arXiv API 核对：标题与作者一致）：

```latex
\paragraph{Language models for serialized 3D structure.}
Autoregressive transformers can generate 3D geometry as token sequences, e.g., triangle meshes in MeshGPT~\cite{meshgpt}; LLaMA-Mesh fine-tunes a pretrained language model to emit meshes as plain text~\cite{llamamesh}. BrickGPT and BrickMore apply the same idea to discrete brick placements, where validity can be checked exactly.
```

- bib 条目（venue 只写 arXiv，避免写错会议；MeshGPT 的 CVPR 2024 需另行核实后才能加）：

```bibtex
@misc{meshgpt,
  author = {Siddiqui, Yawar and Alliegro, Antonio and Artemov, Alexey and Tommasi, Tatiana and Sirigatti, Daniele and Rosov, Vladislav and Dai, Angela and Nie{\ss}ner, Matthias},
  title = {{MeshGPT}: Generating Triangle Meshes with Decoder-Only Transformers},
  howpublished = {arXiv:2311.15475}, year = {2023}}
@misc{llamamesh,
  author = {Wang, Zhengyi and Lorraine, Jonathan and Wang, Yikai and Su, Hang and Zhu, Jun and Fidler, Sanja and Zeng, Xiaohui},
  title = {{LLaMA-Mesh}: Unifying {3D} Mesh Generation with Language Models},
  howpublished = {arXiv:2411.09595}, year = {2024}}
```

- 核对记录：
  - arXiv:2311.15475 “MeshGPT: Generating Triangle Meshes with Decoder-Only Transformers”，前 6 位作者 Siddiqui, Alliegro, Artemov, Tommasi, Sirigatti, Rosov，共 8 人；
  - arXiv:2411.09595 “LLaMA-Mesh: Unifying 3D Mesh Generation with Language Models”，Wang, Lorraine, Wang, Su, Zhu, Fidler，共 7 人。
  - R2：作者已按 arxiv.org 摘要页的 `citation_author` 元数据补全，共 8 人和 7 人。三篇的 comments 中都没有会议录用信息，venue 只写 arXiv。
- 工作量 20 分钟。页面影响约 +0.08。不需要新实验。风险：作者列表要完整核对。

**R-2｜P1｜在 Related Work 中点明与工作坊 VLM 主题的关系（不把本文说成 VLM）**
- 为什么：工作坊叫 “…in Vision-Language Models”。Topic 5 下常见的工作是“合成空间数据 + 微调 VLM”。点明这种关系能让审稿人理解本文的定位，同时如实说明本文生成器不是 VLM。
- 怎么改（追加在 R-1 段末或 “Procedural data…” 段末）：

```latex
Synthetic spatial data is also used to teach vision--language models spatial relations, e.g., SpatialVLM~\cite{spatialvlm}; BrickMore instead trains a text-only generator on programmatically generated assembly data and uses vision--language models only for evaluation.
```

- bib（arXiv:2401.12168 已核对，“SpatialVLM: Endowing Vision-Language Models with Spatial Reasoning Capabilities”，Chen, Xu, Kirmani, Ichter, Driess, Florence 等 9 人）：

```bibtex
@misc{spatialvlm,
  author = {Chen, Boyuan and Xu, Zhuo and Kirmani, Sean and Ichter, Brian and Driess, Danny and Florence, Pete and Sadigh, Dorsa and Guibas, Leonidas and Xia, Fei},
  title = {{SpatialVLM}: Endowing Vision-Language Models with Spatial Reasoning Capabilities},
  howpublished = {arXiv:2401.12168}, year = {2024}}
```

- 工作量 10 分钟。页面影响约 +0.04。不需要新实验。风险：不要写“我们也提升了 VLM 空间推理”。

**R-3｜P2｜“Brick assembly and generation” 段压缩**
- 把 BrickGPT/BrickNet 的描述与 §1 第 2 段去重（§1 已有同样两句）。§1 第 2 段保留一句总述，细节留在 §2。约 −0.05 页，10 分钟。

### 3.D Dataset Construction（§3）

**D-1｜P1｜§3.2 加入转换效益数字（数据生成的质量证据）**
- 为什么：Topic 5 的 data generation 需要说明“生成和转换管线带来了什么”。现在 §3.2 只有定性描述。
- 怎么改（追加在 §3.2 第一句之后）：

```latex
Relative to the earlier relaxed release, the local bridging-and-retiling stage raises the number of geometrically passing models from 65,503 to 79,298 (13,795 recovered failures) while adding 228,582 and removing 125 voxels in total across the corpus; 31,532 passing models require no voxel change at all.
```

- 来源：`D:\BrickMore\Train\datasets\retile_assembly_80000\summary.json`（`baselinePassed=65503`、`geometryPassed=79298`、`recoveredFailures=13795`、`addedVoxelCount=228582`、`removedVoxelCount=125`、`zeroVoxelChangeSuccessfulModels=31532`）。V1.5 附录历史表 “Relaxed 65,503 / Retile 79,298, +228,582 / −125” 与之一致。
- **注意**：
  - 65,503 是 `baselinePassed`。R3 已复核它对应 relaxed release：`D:\BrickMore\Train\datasets\relaxed_assembly_80000\assembly_summary.json` L8 `"geometryPassed": 65503`（同文件 L5 `"success": 65503`）；
  - “31,532” 是整个 retile 运行的统计，与“整合版 79,301”口径不同，句中只说 “passing models” 不说“of the 79,301”。
- 工作量 20 分钟。页面影响 +0.06。不需要新实验。风险：口径表述。

**D-2｜P1｜Table 1 拆成“数据集”和“微调语料”两块**
- 为什么：V1.5 Table 1 把 79,301 与 396,610 上下相邻，读者会自然相乘发现 105 的差（见 U3）。拆开可以避免误导，同时如实保留。
- 怎么改：用 `\midrule` 分为 “Dataset (release reports)” 与 “Fine-tuning corpus” 两组，表注措辞与 U3 选项 C′ 一致（R1：项目中尚未找到训练清单，因此不写 “training manifest”）。
- **按 U3 结果再定稿**；若 U3 选 A 并得到实测值，直接改为实测数字。
- 工作量 15 分钟。页面影响 +1 行。不需要新实验。风险：U3 未决前只做结构，不改数字。

**D-3｜U3｜样本数 / token 冲突**：见 U3。

**D-4｜P1｜§3.1 加一个五级描述示例**
- 为什么：五级描述（L1 简洁 → L5 详细，L4/L5 含明确尺寸）是本文语言条件的关键设计，Topic 5 的“学习表示”需要读者理解输入侧的粒度。
- 怎么改：从 `D:\BrickMore\Essay\BrickMore\V1.5\figure2_units\references\birdhouse_prompts_L1_L5.json` 原样摘取 L1 和 L5 两条英文描述（**执行时读取原文，不要改写**），作为正文一行短例或脚注：

```latex
For example, a birdhouse is described at L1 as ``[L1 text from birdhouse_prompts_L1_L5.json]'' and at L5 as ``[L5 text]''.
```

- 工作量 10 分钟。页面影响 +0.05（L5 文字长时放到附录 A，正文只放 L1）。不需要新实验。风险：需确认该 JSON 是训练集中的真实描述，而不是示意图专用文本（看文件内的 `modelId` 字段）。

**D-5｜P2｜§3.1 “40 structural families per category”**
- `archive\historical_tables.tex` 写有 “Categories / structural families: 21 / 40 per category”，Figure 2 也写了 “21 classes · 40 families each”。可在 §3.1 写 “each category is generated by 40 parametric families”，以说明多样性。
- **必须先在 `D:\BrickMore\Train\programs\` 或生成报告里核实**；核实不了就不写。约 20 分钟，+1 行。

**D-6｜P2｜§3.2 最后一句语序**
- 现句：“…rather than proof of physical stability (Appendix~\ref{app:dataset}); training-data selection uses the geometric checks.” 分号后的句子突兀。
- 改为：
  > “Training data are selected by the geometric checks only; the screening results (Appendix~\ref{app:dataset}) are reported under their stated assumptions and are not proof of physical stability.”
- 5 分钟，页面影响 0。

**D-7｜P2｜validation 与 test 命名（R1 新增，吸收自 RB1 A3-5、C6.2）**
- 改什么：正文和表一律称 “validation”，与 `load_best_model_at_end` 以及附录中的 “2,000-sample validation subset” 一致。模型卡称这一份为 test，但论文不提模型卡（CRITIQUE D-2），所以只需在 Table 1 表注写 “the held-out split is used for checkpoint selection (validation)”。
- 为什么：避免审稿人把 39,655 误读为独立的测试集。
- 5 分钟，页面影响 0，不需要新实验，风险无。

### 3.M BrickMore Text-to-Brick Model（§4）

**M-1｜P1｜§4.1 写清“学到的表示是什么”**
- 为什么：Topic 5 读者需要知道输入、输出和序列化的具体形式。现在分散在三段里，而且“fixed spatial serialization”的**排序规则没有写**（是按层自下而上、还是其他顺序）。
- 怎么改：在 §4.1 第 2 段加一句：
  > “Each assistant reply lists one placement per line as $h{\times}w\ (x,y,z)$ in a fixed order [ordering rule].”
- **排序规则必须从数据准备脚本或训练 jsonl 样例核实**，例如 `V1.5\figure2_units\references\generation_excerpt.py`，或训练数据转换代码。核实不了就**不写排序规则**，只写 “in the order produced by the conversion pipeline”。
- 另外把 I-2 删掉的 “the current output does not include color” 移到本段末。
- 工作量 30 分钟。页面影响 +2 行。不需要新实验。风险：规则核实失败时只能写弱化版。

**M-2｜U10｜检查点一致性**：见 U10。

**M-3｜P2｜Figure 3（拼图）放置**
- 现在在 §4.1 与 §4.2 之间，实际排在第 5 页，与 §5 评测内容在一起。源码位置移到 `\section{Comparative Evaluation}` 之前即可，内容不变。
- 5 分钟，页面影响 0（浮动位置可能变化，编译后确认）。

**M-4｜引用型（R3 由 P1 改为引用，不单独计数，N9）｜§4.2 末尾指向诊断**
- 只加半句：“Section~\ref{sec:diagnostics} reports how often each repair tier is reached.” 档位数字只在 E-2 和附录表中出现一次。
- 若 U13 得到用户说明，600 s 档或补种子的描述句放在这里（见 U13）。
- 5 分钟，+1 行。

### 3.E Comparative Evaluation（§5）

**E-1｜P0｜§5.1 指标精确定义（U8 已有脚本证据）**
- 改什么：替换 “PE and SigLIP2 are image--text matching scores from …”。
- 为什么：VQAScore 当前写成 “probability that … answers Yes”，没说明是全词表 softmax；PE/SigLIP2 定义含糊，影响分数的可解释性（SigLIP2 的 0.12 vs PE 的 0.19 尺度不同）。
- 怎么改：

```latex
\emph{Text--image alignment.} VQAScore~\cite{vqascore} is the full-vocabulary softmax probability that Qwen2.5-VL-7B-Instruct~\cite{qwen25vl} generates the single token ``Yes'' as its first answer token when asked whether a rendered view shows the prompt. PE is the cosine similarity between L2-normalized image and text embeddings of PE-Core-bigG-14-448~\cite{pe}, and SigLIP2 is the sigmoid of the image--text logit of SigLIP2 giant-opt-patch16-384~\cite{siglip2}; their text encoders read at most 72 and 64 tokens, respectively. For each metric, a model's score is the maximum over its eight views, averaged over prompts. The three metrics therefore live on different scales and are compared only within a metric.
```

- 来源：`D:\BrickMore\Deploy\build\comparison_20261110\BrickMoreComparison\Scripts\evaluate_paper_images.py`（SHA-256 前缀 a90e851a6a01，与 `comparison_full\*.config.json` 的 `sources` 一致）；`pe.model.json`（text_context_length 72）、`siglip2.model.json`（64）。
- 工作量 15 分钟。页面影响 +0.03。不需要新实验。风险：无（定义直接来自实际脚本）。

**E-2｜P1（依赖 U12）｜新增 §5.x “Structural Diagnostics of Raw Outputs”（Topic 5 核心补强）**
- 为什么：这是唯一能回答“微调学到了什么空间表示”的已有证据。几何探针比对齐分数更贴近 geometric/spatial reasoning。
- 放置：§5.2 Main Results 之前或之后均可。建议放在 §5.3 Raw vs Retiled **之前**，作为 §5.3，原 §5.3 顺延为 §5.4，因为 Raw vs Retiled 正好承接诊断。
- 怎么改（全部数字已在本轮从原始文件复算，见 §5）：

```latex
\subsection{Structural Diagnostics of Raw Outputs}
\label{sec:diagnostics}
To probe what the fine-tuned model learns, we analyze the raw outputs of a 525-prompt diagnostic batch (21 categories $\times$ five levels $\times$ five phrasings); this batch is part of the candidate pool from which 35 of the 114 comparison outputs were selected (Section~\ref{sec:setup}). Final drafts come from seeds 42, 104, and 2026 in 338, 134, and 53 cases; 28 cases use the recovery path with seeds outside $S$. Only 46 raw layouts (8.8\%) form a single stud-connected component without retiling; this rate shows no clear trend across levels (13, 9, 9, 7, and 8 for L1--L5) but varies strongly by category (e.g., 8/25 for sofa, 0/25 for basket and camera). All 479 failing raw layouts split into at least two stud components (median 5, maximum 33). Overlaps are a minor cause: 50 failing layouts contain duplicated voxels, 41 of them with at most five (median 2), and 429 contain none. The 2,240 detached fragments are mostly not grounded (1,320 airborne versus 920 grounded). The learned representation thus places bricks whose in-bounds voxel union is retained by retiling but that often fail to interlock across layers; retiling yields a single stud-connected component for all 525 cases without changing that union (Table~\ref{tab:diag} in Appendix~\ref{app:eval}).

% R3：此表默认放附录 C（采纳 RB1）；余量足够时可由作者移回正文
\begin{table}[t]
\centering\small
\begin{tabular}{lr}
\toprule
Statistic (525 prompts) & Value \\
\midrule
Raw single stud component & 46 (8.8\%) \\
Failing raw: stud components (median / max) & 5 / 33 \\
Failing raw with overlapping voxels & 50 / 479 \\
Detached fragments: airborne / grounded & 1,320 / 920 \\
Resolved at 12 / 60 / 180 / 600\,s tier & 326 / 133 / 18 / 2 \\
Regenerated with a new seed & 28 \\
Final single stud component, shape preserved & 525 / 525 \\
Raw bricks, median (min--max) & 183 (77--623) \\
Retiled bricks, median & 452 \\
\bottomrule
\end{tabular}
\caption{Structural diagnostics of raw and retiled outputs.}
\label{tab:diag}
\end{table}
```

- R3 来源补充：`attempt` 分布与 `regen_seed` 来自 manifest。“35 of the 114 comparison outputs were selected” 的依据是：`selected_manifest.jsonl` 中 `source_kind=judged` 且 id 为 V 系列的 35 条，`best_all.json` 的 `choice_id` 命中，零件数与 eval_630 输出 LDR 一致（CRITIQUE_RB2_R3 核对 (a)）。`\label{sec:setup}` 指 §5.1（执行时确认标签名）。种子规则见 U13。
- 来源：
  - `D:\BrickMore\brickmore48_eval_630\results\raw_failure_autopsy.json`（525 条；`ok`=46；失败 479 条 `ncomp` 最小 2、中位 5、最大 33；`dup>0`=50，其中 ≤5 的 41 条、中位 2；`dup==0`=429；`orphan_n` 合计 2,240，`orphan_air` 合计 1,320，`orphan_ground` 合计 920）；
  - `...\manifests\manifest_w{0,1,2}.json`（`solver_tier` 分布；分级别 none_needed 13/9/9/7/8；分类别 sofa 8、guitar 6、vessel 4…，basket/camera 0；`raw_bricks` 中位 183、最小 77、最大 623；`assembly_bricks` 中位 452；`regen_seed` 28；`studOK` 525；`shape_preserved` 525）；
  - `...\README.md`（21 类 × 5 级 × 5 变体的构成；它与 `prompts\items_index.json` 一致，但执行时应再数一遍 batch=2 的条目数）。
- **必须修改或删除的措辞**：
  - 上面片段已避免 “cover the intended shape” 一类说法：没有形状保真的直接度量，`shape_preserved` 只说明**重铺前后**体素一致，不说明 raw 与提示的匹配。
  - “0/25 for basket and camera”：从 manifest 复算时，basket、camera 没有出现在 none_needed 分组中（即 0），与 README 一致。
- 工作量 1.5 小时（写作 + 复核 + 表格排版）。页面影响约 +0.20（R3：表默认放附录；放回正文时约 +0.35）。**不需要新实验**（数据已有），但这是新进入论文的数字，需要 U12 同意。风险：
  1. U10 权重版本；
  2. 525 条与 114 条的关系（R3 已由文件确定）：用“候选池”表述，不写 additional、separate、independent 或 taken from；必须与 E-9 同时写入，否则读者无法理解“selected”的含义；
  3. 不能写成 “spatial reasoning benchmark”。

**E-3｜P1｜§5.2 加分级别一致性与稳健性两句**
- 怎么改（接在 “…no significance test is reported.” 之前或替换该句，取决于 U5）：

```latex
The ordering is unchanged when each of the 105 category--level groups is weighted equally (BrickMore 0.2347 / 0.1840 / 0.1257 versus BrickGPT 0.1511 / 0.1459 / 0.0318 for VQAScore / PE / SigLIP2) and when truncated prompts are removed (PE on 89 prompts: 0.1821 vs.\ 0.1445; SigLIP2 on 85 prompts: 0.1088 vs.\ 0.0301), and BrickMore has the highest mean at every description level (Appendix~\ref{app:eval}).
```

- R1 复算（2026-11-15，读 `...\comparison_full\report\scores.csv`，primary=True，按 category×level 分 105 组等权）：BrickMore 0.2347 / 0.1840 / 0.1257，BrickGPT 0.1511 / 0.1459 / 0.0318，BrickNet 0.0674 / 0.1291 / 0.0107，与分析文档一致。L1–L5 各级三项 BrickMore 都最高（15/15），例如 VQAScore L5 为 0.0968 / 0.0748 / 0.0363。**“未截断子集”**（PE 89 条、SigLIP2 85 条）的数字 `scores.csv` 中没有截断标记列，本轮未复算，执行前要从 `comparison_full` 的逐条 `text_truncated` 记录复算后才能用。
- 来源：`D:\BrickMore\Results\three_model_comparison_20261111\analysis\三模型测评结果分析.md`：“105 个类别×Level 等权的补充口径”表（BrickMore 0.234664 / 0.183975 / 0.125722；BrickGPT 0.151097 / 0.145909 / 0.031840）；“未截断子集的补充检查”表（PE 89：0.182061 / 0.144490；SigLIP2 85：0.108762 / 0.030068）；“按 Level 对比”各表。四舍五入到 4 位。
- 工作量 20 分钟。页面影响 +0.06。不需要新实验（分析已存在于项目文件）。风险：这些属于“已有分析中的补充口径”，引用时注明是补充口径、不替代主表。

**E-4｜P1｜附录 C 增加分级别结果表（L1–L5 × 3 系统 × 3 指标）**
- 来源同 E-3 “按 Level 对比”（P_inv、VQAScore、PE、SigLIP2 四张表，每级 21/21/23/25/24 条）。
- 怎么改：一个 `table*`，四个指标块。正文 E-3 引用它。
- 工作量 30 分钟。页面影响：正文 0，附录 +0.3。不需要新实验。风险：无。

**E-5｜U5｜显著性检验**：见 U5。

**E-6｜P1｜§5.3（Raw vs Retiled）加一句解释边界**
- 为什么：SigLIP2 下降、零件数翻倍，审稿人可能质疑“修复让模型变差”。
- 怎么改（追加）：
  > “Because retiling replaces the raw bricks with a different decomposition of the same voxel union, the renders change in brick boundaries but not in occupied volume, which bounds how much the alignment metrics can move.”
- **核实**：“not in occupied volume”的依据是 Algorithm 1 的 Audit（voxels(B*)=C），以及 manifest 的 `shape_preserved=525/525`。但 C 是去重和裁剪后的并集，与 raw 渲染的体素不完全相同（raw 中重叠只渲染一次；越界部分 raw 渲染中可能存在）。所以措辞改为 “…of the same in-bounds voxel union…”。
- 工作量 10 分钟。页面影响 +2 行。不需要新实验。风险：措辞要准确。

**E-7｜P2｜表格数字格式统一**
- Table 4 中 “0.0000%” 与 Table 3 的 “0.00%” 精度不一。Table 4 要显示 0.1897%，保留 4 位小数合理；改为 Table 3 也用 “0.00%”，Table 4 用 “0.1897% / 0.00%”。另外 Table 3 表头 “VQA” 与正文 “VQAScore” 统一。10 分钟。

**E-8｜U（并入 #13）｜BrickGPT 侧生成限制（R1 重写）**
- 证据（本轮从 `D:\BrickMore\Deploy\build\comparison_20261110\BrickMoreComparison\Provenance\brickgpt_generation_summary.jsonl` 复算，114 条）：
  - `world_dim=20`、`seed=42`、`max_regen=8`、`use_gurobi=False`，114 条全部一致；
  - `max_bricks=200` 也全部一致，**但** `brick_count` 超过 200 的有 36 条（最大 497；其中 30 条 `n_regenerations=8` 且 `stable=False`），等于 200 的 3 条；
  - `brick_count` 均值 152.29，即主表的 152.3；
  - `stable` True 66 / False 48。
- 推荐 ★：在 §5.1 “The systems differ in candidate selection…” 句前加半句：

```latex
BrickGPT outputs were generated in its native $20^3$ world (seed 42), whereas BrickMore places bricks in a $48^3$ workspace, which partly explains the difference in part counts.
```

- **不写** `max_bricks=200`：与 36 条超过 200 的零件数冲突，而其语义无法从项目文件确定。**不写** 66/114 stable：BrickMore 没有对应的稳定性评测，写了会造成不对称，且 `use_gurobi=False` 的判定是否与 BrickGPT 论文的配置相同需查证（CRITIQUE A-1、A-2）。
- 工作量 10 分钟，+1 行，不需要新实验。需要用户同意（上一轮遗留 #13）。

**E-9｜P0（R3 新增）｜§5.1 具体披露 BrickMore 一侧的选择效应**
- 改什么：V1.5 §5.1 只有一句泛泛的 “The systems differ in candidate selection, filtering, and post-processing; the comparison characterizes these delivered outputs rather than isolated model capability.”（`V1.5\main.tex` L216）。没有说明 BrickMore 一侧经过了人工挑选。
- 为什么：
  - 主对比 114 条中，有 45 条 BrickMore 输出连同其提示词，是在“每个类别 × 等级 6 个候选（6 种措辞）”中由人工判为最佳者；
  - 其余 69 条来自后续的补缺、重生成和复审轮次；
  - BrickGPT 和 BrickNet 则是在这些已选定的 caption 上各生成一次（BrickGPT seed 42）；
  - 这种选择对 BrickMore 有利。审稿人若从附录或数据发布中发现，而正文没有写，会被视为不诚实。这是防虚构 / 防误导的合规项，所以定为 P0。
- 怎么改（替换 L216 那句，数字全部来自项目文件）：

```latex
The systems differ in candidate selection, filtering, and post-processing. On the BrickMore side, 45 of the 114 prompts and their outputs were chosen by human review as the best of six candidate phrasings generated for the same category and level, and the remaining 69 come from later gap-filling, regeneration, and review rounds; BrickGPT and BrickNet were then run once on the selected prompts. The comparison therefore characterizes these delivered outputs rather than isolated model capability.
```

- 来源：
  - `D:\BrickMore\Results\three_model_comparison_20261111\intake\Results\comparison_full\selected_manifest.jsonl`：BrickMore `primary=True` 114 条，`source_kind` 中 judged 45，其余 69；
  - `D:\BrickMore\BrickNet_BrickGPT_Compirasion\BrickMore_汇总交付_20261107\资料与记录\best_all.json`：105 组的人工判决记录，45 条 judged 的 `model_id` 全部命中 `choice_id`；
  - `D:\BrickMore\brickmore48_eval_630\README.md` L14（每组 6 个候选）、L91–94（人工判决方法）；
  - BrickGPT 生成于 2026-11-09（`BrickGPT原版_AB对照实验_20261109`），晚于 BrickMore 的 11-07 汇总交付。“run once on the selected prompts” 中，BrickGPT 部分依据 `brickgpt_generation_summary.jsonl`（每条 1 个输出，seed 42）；BrickNet 部分依据 `总结_AB对照_20261109.md` L5（“每条 prompt 取 1 个可行样本、最多 30 次尝试”）。所以 BrickNet 要写成 “one accepted sample per prompt (up to 30 attempts)”，**执行时二选一**：要么把句子改得更精确，要么把 BrickNet 的细节放进附录。
- **需要用户确认的只有措辞**，事实已由文件确定。“gap-filling, regeneration, and review rounds” 概括了 round2/round3（补缺）、regenerated、review_59、成功的模型、nine_ldr、car_trials 这些来源；如果用户对这些轮次有更准确的英文描述，以用户为准。
- 工作量 15 分钟。页面影响 +0.04。不需要新实验。风险：会削弱“对齐最高”的观感，但不改变数字和结论（结论本来就限定为 “delivered outputs”）。U5 的检验结果也应按这个口径解释。

### 3.L Limitations and Discussion（§6）

**L-1｜P1（R2 由 P0 降级）｜Scope 段改写，明确 Topic 5 定位和未来方向（不宣称已做）**
- 怎么改（替换 V1.5 的 Scope 段）：

```latex
\emph{Scope.} BrickMore studies spatial representation learning through data generation and supervised fine-tuning only; it performs no pretraining or reinforcement learning, and its generator is a text-only language model, with vision--language models used solely as evaluation metrics. Our evidence about the learned representation is geometric (stud connectivity of raw outputs) and perceptual (text--image alignment of renders); we do not evaluate it on a dedicated spatial-reasoning benchmark. 【The diagnostics suggest that the interlocking rule is the main missing constraint; connectivity-aware decoding is a natural direction outside the scope of this work.】
```

- 注意（R2）：已删去 “rewards”，以免与同段的 “no reinforcement learning” 产生误读。摘要和贡献中不出现 reward 或 RL。
- 工作量 15 分钟。页面影响 +0.03。不需要新实验。风险：【】句依赖 U12。

**L-2｜P1｜Data accounting 段按 U3 结果更新**
- 若 U3 得到实测值，在此用一句话说明 79,301（release accounting）与训练清单的关系。否则保持现状。10 分钟。

**L-3｜P1｜Evaluation 段按 U5 结果更新**
- 若 U5 同意：删除 “Paired uncertainty analysis can be conducted on the existing per-prompt records.”，改为引用检验结果。若不同意：保留。5 分钟。

### 3.C Conclusion（§7）

**C-1｜P1｜结论改写，加入“学到了什么”**

```latex
We presented BrickMore, which learns text-to-brick assembly from agentically generated, geometrically checked data by fine-tuning a language model, and repairs its predictions with stud-connected exact-cover retiling. 【Structural diagnostics show that the fine-tuned model's raw layouts usually fail to interlock across layers, which retiling resolves while preserving the voxel union.】 On 114 shared prompts, the evaluated BrickMore outputs achieve the highest means on three text--image metrics while matching BrickGPT on mean invalid-placement ratio. These results should be read within the stated evaluation and physical-screening boundaries.
```

- 工作量 10 分钟。页面影响 0。不需要新实验。风险：【】依赖 U12。核心结论（对齐最高、P_inv 持平）不变。

### 3.APP 附录

**APP-1｜U4｜中文历史图**：见 U4。R3 默认 C′（保留并更正图注），A 由用户选择。

**APP-2｜P1｜附录 A 新增英文“转换策略对比”表，替代被移除的 image14**

| Release | Rule | Passing | Voxel changes |
|---|---|---|---|
| Strict v3 (original release) | — | 7,902 | — |
| Relaxed | each component grounded | 65,503 | +428,278 / −38,230 |
| Retile | each component grounded | 79,298 | +228,582 / −125 |

- 来源（R3 已全部复核）：Retile 行来自 `retile_assembly_80000\summary.json`；Relaxed 行来自 `relaxed_assembly_80000\assembly_summary.json` L8（65503）、L21（428278）、L22（38230）；Strict v3 来自 `assembly_80000\assembly_summary.json` L9（7902）。Strict 行的 Rule 栏按 V1.5 附录历史表原文填写，不新拟。
- 工作量 30 分钟。附录 +0.2 页。不需要新实验。风险：核实失败的行就不列。

**APP-3｜P1｜附录 C 新增分级别表（E-4）和分类别一遍过率表（E-2 延伸）**
- 分类别 none_needed 计数来自 manifest（sofa 8、guitar 6、vessel 4、bottle 3、birdhouse 3、bookshelf 3、train 2、pot 2、jar 2、mug 2、bus 2、bowl 2、car / chair / tower / bed / bench / table / piano 各 1，basket / camera 0），每类 25 条。
- 30 分钟。附录 +0.2 页。

**APP-4｜P2｜附录 D 历史表格的定位说明**
- 在 D 节首句后加：
  > “Where a value is superseded by a verified number in the main text (e.g., Table~\ref{tab:training-data} and Appendix~A), the main text takes precedence.”
- 5 分钟。

**APP-5｜P2｜附录 B 加训练语料构造细节（等 U3 确定后）**
- 例如 split seed 42：模型卡写 “90/10 split by model, seed 42”。U3 解决后再决定是否写入。5 分钟。

### 3.B 参考文献

**B-1｜引用型｜新增 3 条已核实文献**（meshgpt、llamamesh、spatialvlm，见 R-1/R-2）。作者全名单（8 / 7 / 9 人）已写在 R-1/R-2 的 bib 中，执行时原样使用（R3，N14）。10 分钟。

**B-2｜P2｜venue 核对**
- 现有条目中 BrickNet 写的是 CVPR 2026，V1.3 起沿用。arXiv:2604.22984 的作者和标题已核对，但 **CVPR 2026 录用信息尚未独立核实**。建议执行时查 arXiv 的 comments / journal-ref 或 CVPR 2026 官方论文列表；核实不了就改为只写 arXiv。15 分钟，页面影响 0。

### 3.S 源码、编译与交付

**S-1｜U9｜编译环境**：见 U9。

**S-2｜P0｜V1.6 目录与交付物**
- 执行时：
  - 由 V1.5 完整复制到 `D:\BrickMore\Essay\BrickMore\V1.6`，V1.5 及以前版本不动；
  - 交付 `main.pdf`、`main.tex`、`references.bib`、`REVIEW_V1.6.md`、`NUMBERS_V1.6.md`（G-6），若 U5 同意再加 `analysis\significance.*`。
- 30 分钟。

**S-3｜P0｜最终提交前清单**：见 §7。

**S-4｜P1｜`README.md` 与 `REVIEW_V1.6.md`**
- README 更新为 V1.6 标题和编译方法；REVIEW 记录每个条目的执行结果。30 分钟。

---

## 4. 不做清单（本轮明确不做）

- 不新训模型、不做数据规模 / 描述层级 / 序列化消融（U7）。
- 不新建空间推理基准（U6）。
- 不把模型称为 VLM；不写“improves spatial reasoning”，只写“learns / probes / diagnoses”。
- 不宣称预训练或 RL；RL 只能作为未来方向（L-1）。
- 不使用无法从原始文件复算的数字：零训练重叠、82% 紧贴、108–124 s/条、45 条 union 修复（manifest 中 `union_dropped_bricks>0` 为 0 条，与 README 的 45 不一致，不用）。
- （R3）人工判决 79/105 可以从 `best_all.json` 复算，但正文不用；只在 E-9 中用 45 这个数说明主对比的来源。
- （R3）不写 README §6 的定性语句（“并排贴合却从不跨层交错”“side by side without crossing layer boundaries”），也不写“懂体素形状 / reproduces voxel-level shape”。
- （R3）不把 525 条诊断写成 “additional”、“held-out”、“separate / independent run”，也不写 “114 taken from the 525”。
- （R3）不写 “BrickGPT was run with its authors' default configuration”（见 U14）；不写 `max_regen`、`use_gurobi`，除非用户同意 U14-B。
- 不改主表、Table 4 的任何数值；不改“对齐最高 / P_inv 持平”的结论。
- 不在 PDF 中放作者、GitHub/HF 仓库名或本地路径。
- 不改 `aaai2027.sty` / `.bst`；不用禁用宏包（hyperref 等）或禁用命令（`\clearpage` 等）。
- （R1）不写 BrickGPT 的 `max_bricks=200` 和 66/114 stable（见 E-8）。
- （R1）不在论文中提及模型卡、HuggingFace 仓库，或 “training report” 一类无出处的来源。
- （R1）不用 24,448 × 25.3 h 的乘积替换 token 数，也不写“21 个额外模型”。
- （R1）不更新 `D:\BrickMore\Essay\BrickMore\abstract_introduction.md`（不在 V1.6 范围）。
- （R1）“Algorithm 1 留在正文”“主表 / Table 4 数字锁定”“不宣称 RL / 预训练 / VLM”属于约束，不作为 P0 任务计数。

---

## 5. 新增 / 改动数字的来源对照表

| 数字 | 用于 | 来源文件（字段） |
|---|---|---|
| 65,503 → 79,298；13,795；+228,582 / −125；31,532 | D-1、APP-2 | `D:\BrickMore\Train\datasets\retile_assembly_80000\summary.json`（baselinePassed, geometryPassed, recoveredFailures, addedVoxelCount, removedVoxelCount, zeroVoxelChangeSuccessfulModels） |
| 79,301＝79,298−1,902+1,905 | 现有 | `D:\BrickMore\Train\datasets\CURRENT_DATASET_STATUS.md` |
| 79,322×5＝396,610；~2.19B tokens | U3 | `D:\BrickMore\downloads\BrickGPT-Qwen3-1.7B-BrickMore-48\README.md` |
| 525 prompts；46（8.8%）；13/9/9/7/8；sofa 8/25、basket 0/25、camera 0/25 | E-2、APP-3（R3：摘要和引言不再使用这些数字） | `D:\BrickMore\brickmore48_eval_630\manifests\manifest_w{0,1,2}.json`（solver_tier, level, category） |
| 479 失败；ncomp 中位 5、最小 2、最大 33；dup>0 50 条（≤5 的 41 条、中位 2）；dup=0 429 条；碎片 2,240（悬空 1,320 / 落地 920） | E-2 | `D:\BrickMore\brickmore48_eval_630\results\raw_failure_autopsy.json` |
| 档位 326/133/18/2；none_needed 46；regen 28；studOK 525；shape_preserved 525；raw_bricks 中位 183（77–623）；assembly_bricks 中位 452 | M-4、E-2 | 同上 manifest |
| 105 组等权 0.2347/0.1840/0.1257 vs 0.1511/0.1459/0.0318；未截断 PE 89 条 0.1821 vs 0.1445、SigLIP2 85 条 0.1088 vs 0.0301；分级别各表 | E-3、E-4 | `D:\BrickMore\Results\three_model_comparison_20261111\analysis\三模型测评结果分析.md` |
| PE＝余弦；SigLIP2＝sigmoid；VQAScore＝全词表 softmax 下 “Yes” 的概率 | E-1、U8 | `D:\BrickMore\Deploy\build\comparison_20261110\BrickMoreComparison\Scripts\evaluate_paper_images.py`（sha256 a90e851a6a01…，与 `comparison_full\{vqa,pe,siglip2}.config.json` 的 sources 一致） |
| 72 / 64 文本 token 上限 | 现有 | `comparison_full\pe.model.json`、`siglip2.model.json` |
| 胜 / 负 91/23、95/19、91/23 | U5 | `...\analysis\三模型测评结果分析.md`；逐条数据 `...\comparison_full\report\scores.csv` |
| 45 / 69（主对比 BrickMore 的人工判决入选数 / 其余）；judged 45、review_59 21、成功的模型 16、round2 12、round3 7、nine_ldr 7、regenerated 5、car_trials 1 | E-9 | `D:\BrickMore\Results\three_model_comparison_20261111\intake\Results\comparison_full\selected_manifest.jsonl`（`source_kind`，sha256 BC3962358139DE93…） |
| 每组 6 个候选；105 组；79 组有最佳 | E-9、U12、U4 | `D:\BrickMore\brickmore48_eval_630\README.md` L14、L91–94；`D:\BrickMore\BrickNet_BrickGPT_Compirasion\BrickMore_汇总交付_20261107\资料与记录\best_all.json`（sha256 1003CBF4377D1508…） |
| image18(a)：蓝 85.7/76.2/81.0/71.4/61.9%；红 61.9/71.4/52.2/48.0/58.3% | U4-b（仅核对，不写新数字） | 同上 `best_all.json`；`brickgpt_generation_summary.jsonl`（`level`、`stable`） |
| 7,902；65,503；+428,278 / −38,230；2,650；478；45,490 / 17,024 / 14,497 | D-1、APP-2、U4 | `D:\BrickMore\Train\datasets\relaxed_assembly_80000\assembly_summary.json` L5、L8–L10、L13–L15、L21–L22、L75；`assembly_80000\assembly_summary.json` L9 |
| 权重 revision `92d1c595f5fe…` | U10 | `BrickMore_汇总交付_20261107\资料与记录\provenance.json` L3；`eval_630\README.md` L5 |
| BrickGPT 论文：最多 100 次 rollback、Gurobi | U14（默认不写） | `D:\BrickMore\Essay\brickGPT\2505.05469v3.pdf` 第 6、8 页 |
| BrickGPT `world_dim=20`、seed 42、`max_regen=8`、`use_gurobi=False`；`brick_count` 超过 200 的 36 条、均值 152.29；stable 66/48 | E-8 | `D:\BrickMore\Deploy\build\comparison_20261110\BrickMoreComparison\Provenance\brickgpt_generation_summary.jsonl` |
| 105 组等权、L1–L5 均值（R1 复算）；对 BrickNet 胜 97/98/102 | E-3、U5 | `...\comparison_full\report\scores.csv`（primary=True） |
| Overleaf 免费版 10 s 编译超时、每个项目 1 名协作者；box 上 latexmk 3.6 s | U9 | docs.overleaf.com plan limits；box 实测（V1.4） |
| OpenReview 公共邮箱注册审核“最长 2 周” | U2、§6 | docs.openreview.net “Signing up for OpenReview” |
| OpenReview 截止 2026-11-20 19:59 UTC+8；作者对审稿人隐藏；需要 OpenReview profile | U2、时间线 | OpenReview API `AAAI.org/2027/Workshop/GSR-VLM/-/Submission`（duedate 1795175940000；authors.readers） |

新增文献核对（arXiv API，2026-11-15）：
- arXiv:2311.15475 MeshGPT；
- arXiv:2411.09595 LLaMA-Mesh；
- arXiv:2401.12168 SpatialVLM。

标题与全部作者已按 arxiv.org 摘要页的 `citation_author` 元数据核对（8 / 7 / 9 人）。会议 venue 未核实，一律只写 arXiv。

---

## 6. 风险登记

| 风险 | 影响 | 缓解 |
|---|---|---|
| 作者 OpenReview profile 审核来不及（公共邮箱最长 2 周） | 无法提交 | **11-15 当天**全部注册，添加并验证机构邮箱 |
| U3 找不到训练清单 | 数字自相矛盾 | 11-17 24:00 为截止点；之后启用 U3 选项 C′（拆表 + 中性措辞） |
| U10 权重版本不一致 | E-2 不能写进正文 | E-2 改为附录，并注明权重版本 `92d1c595`，或者整体不用 |
| E-9 披露削弱对比观感 | 审稿人质疑公平性 | 如实写出，结论本来就限定为 “delivered outputs”；不改主表；U5 的检验结果按同一口径解释 |
| 新增内容让正文超过 7 页 | 违规 | §1 的兜底顺序：诊断表 → Figure 3 → Table 2 → E-3；Algorithm 1 不动 |
| 显著性检验有项目不显著 | 削弱表述 | 如实报告；结论保持“均值最高” |
| box 编译环境不可用 | 无法出 PDF | 用户本机 MiKTeX（U9），11-17 前装好并试编一次 |
| 时间不够 | 漏交 | 11-19 提交一版完整稿到 OpenReview（截止前可以修改），11-20 只做替换 |

---

## 7. 时间线（现在 2026-11-15 00:40 UTC+8 → 截止 2026-11-20 19:59 UTC+8）

| 时间（UTC+8） | 任务 | 负责 | 产出 / 验收 |
|---|---|---|---|
| 11-15（日）上午 | **用户决策 U1–U14**（逐条选 ★ 或替代项）；**所有作者注册 OpenReview profile**；用户开始在训练服务器找 U3 证据（`trainer_state.json`、训练 jsonl 行数） | 用户 | 决策清单；profile ID |
| 11-15 下午 | 复制 V1.5 → V1.6；执行 P0：E-1、E-9、G-2 初查；P1：A-2（定性版）、I-2、L-1；P2：G-4；编译、验收（G-1） | RB2 | V1.6 第 1 版 PDF，正文 ≤ 7 页 |
| 11-15 晚 | 复核 E-2 数字（再读 525 个 `raw_report.json` 统计 voxel_components；数 items_index 中 batch=2 的条目） | RB2 | NUMBERS_V1.6.md 初稿 |
| 11-16（一） | P1 内容：E-2 新小节（表放附录）、M-4 引用句、E-3、E-6、D-1、D-2（结构）、D-4、R-1/R-2/B-1、I-1/I-3/I-4、C-1、M-1（核实序列化排序）；若 U5 同意，跑显著性检验脚本 | RB2 | V1.6 第 2 版；significance.json |
| 11-17（二） | 附录：U4 执行（移除中文图，或采用 C′）、APP-2/3/4、E-4；B-2 venue 核对；E-8（若同意）；D-7；用户本机装 MiKTeX 试编（U9）；**24:00 为 U3 找证据的截止点** | RB2 + 用户 | V1.6 第 3 版；本机编译成功截图 / 日志 |
| 11-18（三） | 根据 U3 证据（或选项 C′）定稿 Table 1 / 附录 B；全文英语润色与术语统一（G-5）；G-6 数字逐一核对；页数终检 | RB2 | 内容冻结（content freeze） |
| 11-19（四） | 用户通读；修最后的小问题；**向 OpenReview 提交完整稿**（截止前可修改）；G-3 表单填完 | 用户 + RB2 | OpenReview 提交编号 |
| 11-20（五）12:00 前 | 只做必要替换（错别字、数字确认）；G-1/G-2 终检；上传最终 PDF | RB2 + 用户 | 最终 PDF |
| 11-20 12:00–19:59 | **缓冲期**，不再改内容，只处理上传或系统问题 | 用户 | 截止前完成（19:59 UTC+8） |

---

## 8. 条目统计核对

- **P0（7）**：G-1、G-2、G-3、E-1、E-9（R3 新增）、S-2、S-3。
- **P1（21）**：A-2、I-2、L-1、G-5、G-6、I-1、I-3、I-4、R-1、R-2、D-1、D-2、D-4、M-1、E-2、E-3、E-4、E-6、C-1、APP-2、APP-3。（R3：M-4 改为引用型。）
- **P2（10）**：G-4、G-7、A-3、I-5、R-3、D-5、D-6、D-7、M-3、E-7。
- **U（14）**：U1 标题；U2 作者 / 双盲；U3 79,301 vs 79,322 与 tokens；U4 中文历史图；U5 显著性检验；U6 空间推理评测；U7 消融；U8 PE/SigLIP2 定义；U9 编译环境；U10 权重版本；U11 Reproducibility checklist；U12 是否使用 525 条诊断；U13 种子 / 档位规则；U14 BrickGPT 运行配置（R3 新增）。（R2 此处标题误写为 “U（12）”，实际列了 13 条，R3 一并更正。）
- **另有引用型或从属条目，不单独计数**：A-1（=U1）、D-3（=U3）、M-2（=U10）、M-4（→E-2，R3）、E-5（=U5）、E-8（并入上一轮 #13，执行需用户同意）、L-2、L-3、APP-1（=U4）、APP-4、APP-5、B-1、B-2、S-1（=U9）、S-4。

合计：独立条目 7 + 21 + 10 + 14 = **52**（R2 为 51：+E-9、+U14、−M-4）。U4-b（image18）是 U4 的子项，不单独计数。

---

*本文件只写入 `D:\BrickMore\Essay\BrickMore\Plan_V1.6\PLAN_RB2_R3.md`（同轮另写 `CRITIQUE_RB2_R3.md`）。没有修改任何论文文件，也没有修改 R0–R2 或 RB1 的任何文件。*
