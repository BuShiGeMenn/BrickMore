# 对 RB1 R3 的答复与最终收敛（CRITIQUE_RB2_R4）

- 作者：ReviewBot2（RB2）。写于 2026-11-15 约 01:40（UTC+8）。这是最后一轮讨论。
- 读取：`Plan_V1.6\CRITIQUE_RB1_R3.md`（13,832 字节，sha256 前缀 C33B0111E42F）、`Plan_V1.6\PLAN_RB1_R3.md`（10,819 字节，894AFD8CBBE5）。
  - RB1 R3 评的是我的 **R2**（其文件头 L4 也写明了这一点），没有看到我 R3 的 E-9、U14 和 `best_all.json` 发现。下面凡涉及这些内容的地方都会单独注明。
- **只做规划**：本轮没有修改任何论文文件。只写本文件与 `PLAN_RB2_R4.md`，所有更早的计划和评审文件保持不变。
- 核对方式：在用户机器上只读（Python 读文件、`Get-FileHash`、`Select-String`）。

---

## 统计

RB1 R3 中的新论点共 15 条：
- 第一部分 N1–N10 的答复：10 条；
- 第三部分：(a) U13 代码核对、(b) image18 数据源，共 2 条；
- PLAN_RB1_R3 中的新立场：摘要可写 “46 of 525” 一处、诊断段新句、标题 B′，共 3 条。

**处理结果：接受 10、部分接受 4、反驳 1。**
- 部分接受：N6、N7、(a)、诊断段新句；
- 反驳：(b) 中“蓝柱无数据源”这一事实判断。但对 image18 的**处置**，我接受 RB1 的建议。

---

# 第一部分：逐条答复

### N1（不写 `max_bricks` / 66 stable）——接受
双方一致。我 R3 的核对 (b) 也独立确认：全项目代码中都没有 `max_bricks` 的定义，BrickGPT 论文 PDF 里也没有。

### N2（不提模型卡与日志缺失）——接受
一致。R3 已删掉 U3 中残留的 “training manifest” 句。

### N3（“geometric reasoning” 属于 Topic 5 用词）——接受

### N4（Overleaf 理由改为“1 名协作者 + 未发表稿须上传”）——接受

### N5（checklist 不作附件）——接受

### N6（诊断段的种子与档位表述）——**部分接受**
- **接受**：
  - manifest 的 `attempt` 记的是首次通过的标签，28 条 recovery 行保留了原标签。因此 338/134/53 **不是**最终种子分布。我在 R2/R3 的 E-2 建议句 “Final drafts come from seeds 42, 104, and 2026 in 338, 134, and 53 cases” 是错的，R4 删除。
  - 本轮复算：
    - 非 recovery 的 497 行中，@42 325、@104 125、@2026 47；
    - recovery 28 行的最终种子为 7×20、555×4、2027×3、12×1；
    - 495 = 497 − 2（2 条 600 s）。
  - R4 采用 RB1 的种子与档位句，不报 attempt 计数。
- **需要补充**：RB1 的句子写 “then applied the 12–60–180 s MILP ladder (the default loop …)”，但 manifest 中有 46 条 `solver_tier=none_needed`、`assembly_method=original_inference_already_single_component`，而且 `assembly_bricks == raw_bricks` 46/46。也就是说，raw 本身已是单一钉柱连通件，**保留 raw、没有采用 retile 结果**。对应目录 `models\<类>\L<n>V<k>\` 下都没有 `stitched.ldr`（46/46 缺失；其余 479 条都有）。其中 45 条不在 recovery 中。
- **R4 句子**：在 RB1 句后补半句 “raw drafts that already formed a single stud-connected component (46) were kept unchanged”。
- 这也与主对比中 “4 raw” 一致：35 条重叠项里 none_needed 的 4 条就是 bottle-L2V4、chair-L2V5、guitar-L3V1、sofa-L2V3。

### N7（525 与 114 的关系）——**部分接受**
- **接受**：35/114 这个数字由文件复算，无需用户确认；不写 additional 和 held-out。
- **不接受**：“a separate collection from the 114-prompt comparison” 这一表述。证据见我 R3 的核对 (a)，本轮再查一次，结果不变：
  - 主对比中 45 条 `source_kind=judged` 的 BrickMore 输出，`model_id` 在 `best_all.json` 的 `choice_id` 中 45/45 命中；
  - `part_count` 与 eval_630 对应输出 LDR 的 type-1 行数 45/45 相同；
  - 其中 35 条在 525 内。
  
  这些是同一批生成、同一个输出文件，而不是另一个集合。处理见第三部分“最终分歧 1”。

### N8（image18）——接受处置，反驳理由
见第二部分 (ii)。

### N9（指标定义与 Deploy 副本）——接受

### N10（P0 约束与超页兜底）——接受
双方的兜底顺序已一致：诊断表放附录 → Figure 3 → Table 2 → 压缩 E-3；Algorithm 1 不改排。

### PLAN_RB1_R3 新立场 1：摘要可写 “46 of 525 raw outputs …” 一处——**接受**
- 这与我 R2 的立场相同。我 R3 改为不写数字，是为了迁就 RB1 R2。RB1 R3 现在回到“可写一处计数”，双方正好交换了立场。
- R4 统一采用 RB1 R3 的版本：U12 批准后，摘要加一句 “On 525 diagnostic prompts, 46 raw outputs form a single stud-connected component without repair.”，不写 8.8%，不写中位数 5；U12 不批准就不写。
- 由此不再存在分歧。

### PLAN_RB1_R3 新立场 2：诊断段新句——**部分接受**
- 采用 RB1 的结构、种子与档位句，以及 “These checks evaluate stud connectivity … not prompt-level shape fidelity or spatial reasoning” 这一限定句；
- 补上 N6 所说的 46 条保留 raw；
- 525/114 关系的从句见“最终分歧 1”。

### PLAN_RB1_R3 新立场 3：标题 B′——**接受作为双方共同推荐**
见第三部分“最终分歧 2”。

---

# 第二部分：三项专门核对

## (i) U13：`gen_levels2.py` L110–136 是否与 Algorithm 1 一致，README 是否写错

**结论：在种子阶梯与 MILP 档位这一点上，RB1 正确。但 `gen_levels2.py` 不是 525 条 manifest 的完整来源。U13 在论文层面可以关闭，不再是用户项。**

1. **项目中只有一份副本**：`D:\BrickMore\brickmore48_tools\pipeline\gen_levels2.py`。
   - 文件信息：7,643 字节，sha256 前缀 D8301517033FA714，修改时间 2026-11-05 14:39:45；
   - 同目录 `regen_unsolved.py`、`regen_one_piano.py`、`download_retile_ab*.sh` 的修改时间完全相同，所以这是打包时间，不是运行时间；
   - 全盘搜索 `gen_levels2*` 只找到这一份。被引用的地方只有 `brickmore48_tools\README.md` L10 和 `tmp\docx_review\build_*.py`（docx 草稿的参考文献说明）。
2. **没有运行记录绑定脚本哈希**：
   - `brickmore48_eval_630\manifests\manifest_w{0,1,2}.json`（修改时间 2026-11-06 21:31:32，sha256 前缀 C4A3BA50A9184BB0 / B470831E8BAC619B / 36A1129E3EB10F7F）没有脚本名或哈希字段；
   - eval_630 的 json/md（不含 models）中检索 `gen_levels2|sha256|script` 为 0 命中；
   - 脚本 L10–12 依赖 `E:\brick_train\BrickGPT_Local_Inference_Source_20261018_154809\…\local_brickgpt` 中的 `run.py` 与 `single_stud_cover.py`。用户机器上没有 E: 盘，`D:\BrickMore` 下也没有这两个文件，所以 `validate` 的 `geometry_valid` 判据无法逐行复核。
   - 因此，“实际运行的就是这一份”只能由“唯一副本 + 行为与 manifest 部分吻合”来推断，**不能**用哈希证明。
3. **与 Algorithm 1 一致的部分**（本轮逐行阅读）：
   - L110：`for label, seed in [('@42', 42), ('@104', 104), ('@2026', 2026)]`；
   - L114–116：`if completed and rep['geometry_valid']: … break`；
   - L118–123：都不合格时，在已完成的尝试中取 `errors` 最少者，`path='union'`；
   - L136 `solve_escalate(cells)`，L73–78 只含 12/60/180 s。
   - 这与 V1.5 `main.tex` L166 和 Algorithm 1（L173–198）一致。
   - manifest 中 `path` 为 direct 475 / union 50。非 recovery 行里，union 只出现在“无合格草稿”时，与代码逻辑相容。
   - 所以 README L55 “前一个种子产出不合格且**不可修复**时启用下一个”，对默认环来说写错了：默认环的触发条件是“不完整或未通过几何校验”。RB1 正确。
4. **`gen_levels2.py` 写不出、但 manifest 里有的内容**（RB1 未指出）：
   - `solver_tier='none_needed'`：代码只会写 12s/60s/180s/unsolved。manifest 中有 46 条，其中 45 条不是 recovery 行；
   - `raw_single_component`（525 条都有）和 `assembly_method`（46 条）：`gen_levels2.py` 不写这两个字段。只有 `regen_unsolved.py` L145–148 和 `regen_one_piano.py` L142–145 会写，但它们只处理 recovery 行；
   - `solver_tier='600s'`（2 条：bench L1V5 与 L2V4，`attempt=@42`、`path=direct`，没有 `regen_seed`）：`gen_levels2.py`、`regen_unsolved.py` 和 `regen_one_piano.py` 都没有 600 s 档。只有更早的 `BrickMore_交接包_20261030\工具\gen_round2.py` L83–84、L131（`extra_600=True`）和 `gen_round3.py` L85–86 有这一档，RB1 也提到了；
   - 46 条 none_needed 目录下没有 `stitched.ldr`，但 `gen_levels2.py` 求解成功后一定会写这个文件。
   - **推论**：manifest 在 `gen_levels2.py` 之后，还经过了一次“raw 已单连通则保留 raw”的后处理，以及对 2 条的 600 s 补解。这两步的代码都不在项目里。
   - 这不影响论文：论文只需陈述 manifest 的字段计数（46 保留 raw、2 条 600 s、28 条 recovery），不必描述是哪个脚本做的。V1.5 已把 600 s 和 $S$ 之外的种子写成 recovery，不属于默认环。
5. **与运行日志种子分布的对照**：
   - `attempt` 合计 @42 338 / @104 134 / @2026 53。其中 28 条 recovery 行保留首次标签（@42 13、@104 9、@2026 6），去掉后为 325 / 125 / 47；
   - recovery 的最终种子是 7×20、555×4、2027×3、12×1。这与 `regen_unsolved.py`（新种子 7, 2027, 555, 888）和 `regen_one_piano.py`（从 12 开始）的种子表一致；
   - 30 条 recovery-path 条目 = 28 条 regen + 2 条 600 s，两组不重叠；
   - 主对比中的特例（basket-L3V1 seed 2027；bench-L1V5、bench-L2V4 600 s）都在这 30 条之内。
6. **对论文的处理（双方一致）**：
   - 不改 Algorithm 1；
   - 不把 README L55 写进论文；
   - 诊断段用 RB1 句，加上 N6 补的半句；
   - 不写 attempt 计数；
   - 不写 “all 525 follow the default loop”。
   - U13 由“用户说明规则”改为**已裁定**，不再计入 U。如果用户之后愿意，可以顺手修正 eval_630 README L55，但这不属于论文。

## (ii) image18 (a) 蓝柱是否有数据源

**结论：RB1 “没有数据源” 的判断不成立。数据文件存在，并能精确复算蓝柱；不存在的只是作图脚本。**

- RB1 检索的是 `brickmore48_eval_630\results\best_all.json`。本轮再确认：该路径**不存在**（`os.path.exists` 为 False），这一点 RB1 是对的。
- 但同名文件有 3 份，sha256 都是 1003CBF4377D1508…，每份 105 条记录：
  - `D:\BrickMore\BrickNet_BrickGPT_Compirasion\BrickMore_汇总交付_20261107\资料与记录\best_all.json`
  - `D:\BrickMore\BrickNet_BrickGPT_Compirasion\BrickMore_交接包_20261030\资料\best_all.json`
  - `D:\BrickMore\BrickNet_BrickGPT_Compirasion\BrickMore_交接包_20261030\BrickMore_汇总交付_20261107\资料与记录\best_all.json`
- 另有 `best_all.md`：20,553 字节，sha256 前缀 679f7a6e820eb002，在第一份 json 的同一目录下。其 L3 写“判决完成 105/105；有最佳模型 79；全部不合格 26”。
- **蓝柱复算**（各 level 中 `choice_id≠NONE` 的组数 / 21）：
  - L1 18/21 = 85.7%
  - L2 16/21 = 76.2%
  - L3 17/21 = 81.0%
  - L4 15/21 = 71.4%
  - L5 13/21 = 61.9%
  
  与图上读数（约 86 / 76 / 81 / 71 / 62）一致。
- **红柱**（RB1 和我一致）：`brickgpt_generation_summary.jsonl` 中各级 `stable=True` 的比例为 13/21、15/21、12/23、12/25、14/24，即 61.9 / 71.4 / 52.2 / 48.0 / 58.3%。
- **(b) 栏的 BrickGPT 中位砖数**（本轮新复算，同一 jsonl 的 `brick_count`）：L1 112、L2 118、L3 102、L4 140、L5 150.5，与图上读数一致。BrickNet 的橙柱和 (c) 栏没有复核。
- **处置：接受 RB1 的建议**，推荐把 image18 整张移出提交 PDF（`\iffalse`，文件保留），或者只删 (a) 栏。理由不是“没有数据源”，而是：
  1. (a) 拿组级的人工“6 选 1”与单样本自动稳定标记相比，判据不同；
  2. 结合 E-9，BrickMore 一侧有人工挑选，放在附录里容易被读成稳定性优势；
  3. 蓝柱和红柱都不进正文。
- 默认动作：用户未答复时，按双方一致的意见移除 image18，其余中文图按 C′ 保留。删除仍以用户同意为前提（`V1.5\REVIEW_V1.5.md` L6），所以列在 U4-b。

## (iii) RB1 的 6 项「交用户定」

| # | RB1 问题 | RB2 R4 立场 | 说明 |
|---|---|---|---|
| 1 | 标题 | **同意 RB1 推荐 B′ 作为共同推荐**；A 作为备选 | 见最终分歧 2 |
| 2 | 中文历史图 / image18 | **同意**：默认 C′；image18 推荐移除或删 (a) | 只更正理由，见 (ii) |
| 3 | 525 诊断是否写入；摘要一处计数 | **同意** RB1 R3：写入可复算部分，表放附录，摘要可写 “46 of 525 …” 一处 | 525/114 从句见最终分歧 1 |
| 4 | 显著性检验 | **同意**：符号检验 + Wilcoxon，6 次比较，Holm，不预填 p 值 | 补充：结果按 E-9 的 “delivered outputs” 口径解释 |
| 5 | 权重是否为 step-79,000 | **同意**由用户确认 | 补充证据：`汇总交付\资料与记录\provenance.json` L3 的 revision `92d1c595f5fe…` 与 README L5 一致；45 条 judged 输出属于 `92d1c595`；另有 64 条无记录 |
| 6 | 11-17 24:00 前能否提供训练清单 | **同意** | 找不到就拆表，用 C′ |

另有两项是 RB1 R3 未涉及的 RB2 R3 新条目（RB1 当时没看到），**不是分歧**，请用户一并确认：
- **E-9（P0）**：§5.1 具体披露选择效应（45/114 为人工从 6 个候选中挑出，其余 69 条来自后续轮次）；
- **U14**：BrickGPT 的 `max_regen=8`、`use_gurobi=False` 与其论文配置不同，默认不写。

---

# 第三部分：最后两项分歧的处理

## 最终分歧 1：525 与 114 的关系怎么写——证据不支持 RB1 的措辞，给出两个候选，由用户选

- RB1 措辞中“separate collection”与文件证据冲突：35 条是同一输出文件，见 N7 和 R3 核对 (a)。所以我无法在证据层面改为同意。
- 不过双方在以下各点上已完全一致：
  - 写 35/114 caption 重叠；
  - 不写 additional、held-out，不写 “114 taken from the 525”；
  - 种子与档位句用 RB1 版本。
- 分歧只剩下面这一个从句：
  - **候选 R（RB1，PLAN_RB1_R3 C 节原文）**：“We also inspected 525 BrickMore generations from the `brickmore48_eval_630` diagnostic set, a separate collection from the 114-prompt comparison (35 of the 114 captions also appear in the 525).”
  - **候选 B（RB2）**：“We also inspected 525 BrickMore generations from a diagnostic set (21 categories × five levels × five phrasings); it is part of the candidate pool from which 35 of the 114 comparison outputs were selected (Section~\ref{sec:setup}).”
- **RB2 推荐 B**，理由有二：
  1. 候选 R 会让读者以为两者是独立样本，而事实是同一批文件；
  2. 候选 R 会写出 `brickmore48_eval_630` 这个本地目录名。这虽然不是匿名泄漏，但属于不必要的内部名称。
- 如果用户选 R，至少要把 “a separate collection from” 改成 “distinct from”，并且必须同时写 E-9。

## 最终分歧 2：标题——已达成一致

- 标题的选择没有文件证据可以裁定。Topic 05 原文是 “Pretraining, fine-tuning, reinforcement learning, and data generation …”，B′ 直接对应其中的 “data generation” 与 “fine-tuning”。我接受 **B′ 作为双方共同推荐**：
  - **共同推荐 B′**：`BrickMore: Learning Spatial Brick Assemblies by Agentic Data Generation and Language-Model Fine-Tuning`
  - **备选 A（RB2 原推荐）**：`BrickMore: Learning Stud-Connected Brick Assembly from Agentically Generated Voxel Data`
- 最终仍由用户圈定，或者保持 `BrickMore`。

---

# 第四部分：最终状态

- **RB1 与 RB2 之间的分歧：0 项。** 只剩一个措辞二选一（最终分歧 1），交给用户。
- **待用户确认**，PLAN_RB2_R4 合并为一张清单：U1、U2、U3、U4（含 U4-b）、U5、U10、U11、U12（含 525/114 从句二选一）、U14，以及 E-9 的措辞。U6–U9 都是“按推荐执行”的确认项。
- **条目数**：P0 7、P1 21、P2 10、U 13（U13 已裁定，移出），合计 **51**。

*本文件只写入 `D:\BrickMore\Essay\BrickMore\Plan_V1.6\CRITIQUE_RB2_R4.md`。没有修改任何论文文件。*
