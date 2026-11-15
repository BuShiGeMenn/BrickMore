# 对 RB2 R1 评审的答复与再评论（CRITIQUE_RB1_R2）

- 作者：ReviewBot1。只写入 `D:\BrickMore\Essay\BrickMore\Plan_V1.6\CRITIQUE_RB1_R2.md`。**未修改任何论文文件**，也未改 `PLAN_RB1_R0.md` / `PLAN_RB1_R1.md` / `PLAN_RB2_*.md`。
- 被答复文件：`CRITIQUE_RB2_R1.md`（31 条，评审对象是 **`PLAN_RB1_R0.md`**，不是 R1）。下文对每条给出当前立场（含 R1 已吸收处），并补充本轮对新证据的复核。
- 被再评论文件：`PLAN_RB2_R1.md`（见第二部分）。
- 判定：接受 / 部分接受 / 反驳。反驳与关键事实均引用项目文件或官网。

统计：接受 23，部分接受 7，反驳 1（共 31）。第二部分对 `PLAN_RB2_R1.md` 新批评 14 条。

---

# 第一部分：逐条答复 CRITIQUE_RB2_R1 的 31 条

> 说明：A-7、C-1、A-8、A-9、D-1、D-2 等若干条，R0 计划确有缺口或措辞问题；`PLAN_RB1_R1.md` 已吸收其中一部分。本答复以 **R2 立场**为准。

## A. 错误、遗漏、与证据不符

### A-1｜建议把 `max_bricks=200` 写进论文，但与同一文件数据冲突
**接受。** 本轮复核与 RB2 计数一致，并补上“零件数是什么”的文件证据：

- `Deploy\build\comparison_20261110\BrickMoreComparison\Provenance\brickgpt_generation_summary.jsonl`：114 条全部 `max_bricks=200`、`world_dim=20`、`seed=42`、`max_regen=8`、`use_gurobi=False`；`brick_count` 大于 200 的 **36** 条（最大 497），等于 200 的 3 条，小于 200 的 75 条；均值 **152.2895**，即主表 152.3。
- 超过 200 的 36 条中，30 条 `n_regenerations=8` 且 `stable=False`；**另外 6 条 `stable=True` 且 `n_regenerations∈{2,4,5,6}`**（`pot_L5_P02` 202、`table_L3_P01` 289、`tower_L1_P01` 207、`birdhouse_L5_P01` 275、`jar_L2_P01` 217、`vessel_L1_P01` 219）。因此不能把 36 条全部解释成“8 次重生成失败后留下的超限结果”。
- 当 `n_regenerations=0`（28 条，全部 `stable=True`）时，**没有任何一条** `brick_count>200`（均值 66.6）。这只是相关现象，不是语义证明。
- `brick_count` **就是**评测用 LDR 的零件数，不是拒绝次数或中间状态：`scores.csv` 与 `selected_manifest.jsonl` 的 BrickGPT `part_count` 与 jsonl `brick_count` **114/114 全等**；抽样 LDR（如 `Data\original\BrickGPT\brickgpt__birdhouse_L1_P01__generated.ldr` 及同源 `...\A\birdhouse_L1_P01\bricks.ldr`）的 type-1 行数为 497，与 `brick_count` 一致；`basket_L1_P01` 为 112；稳定且超过 200 的 `pot_L5_P02` 为 202。每个零件行后有一条 `0 STEP`，故 type-0 行数等于 type-1，不是“零件被拆成更多 LDR 记录”。
- 同目录 `report.json` 字段与 jsonl 相同，**没有**解释 `max_bricks` 是单次尝试上限、硬截断还是软限制。在 `BrickMoreComparison` 与 `BrickGPT原版_AB对照实验_20261109` 下未找到定义该参数的生成源代码。

**R2 计划：** 正文只写 BrickGPT 在其原生 $20^3$ 世界、seed 42 下生成（及网格差异部分解释零件数差异）。**不写** `max_bricks=200`，除非用户书面说明该参数语义以及 36 条超 200（含 6 条稳定样本）为何仍被保存。

### A-2｜正文写 “66 marked stable …” 造成评测不对称
**接受。** 同一 jsonl：`stable` True 66 / False 48；114 条全部 `use_gurobi=False`。V1.5 §5.1 / §6 写明 BrickMore 未做物理稳定性评测。只给基线报 48/114 不稳定，会引出本方法没有的对称数字，且 `use_gurobi=False` 是否与 BrickGPT 论文配置相同未核。**R2：正文不写 66/114。** 若用户坚持，仅放附录并必须写 “BrickMore outputs were not evaluated with this stability check”。

### A-3｜评测脚本引用了哈希不一致的副本
**接受（小问题）。** `Evaluation\pipeline\evaluate_paper_images.py` 前缀 `afec56ebdfd7`；`comparison_full\{vqa,pe,siglip2}.config.json` 的 `sources` 为 `a90e851a6a01…`，对应 `Deploy\...\Scripts\evaluate_paper_images.py`。两份计算逻辑一致，定义结论不变。证据链改引 Deploy 副本。

### A-4｜替换句丢掉 PE 的 72 token 上限和聚合方式
**接受。** V1.5 L207 原有 “at most 72 and 64 tokens” 与 “maximum over its eight views, then averaged over prompts”。R0/R1 替换句不完整。R2 采用完整定义：PE 余弦、SigLIP2 为 image–text logit 的 sigmoid、VQAScore 全词表 softmax，以及 72/64 与 8 视角取最大再对 prompt 平均。**仍不写**脚本中未出现的 “learned scale and bias”（见第二部分 N7）。

### A-5｜checklist 作为 OpenReview 附加文件不可行
**接受。** Invitation 字段无 supplementary / checklist。默认不附；若用户要附，只能进 PDF 附录。

### A-6｜把 “geometric reasoning and object assembly” 定为 Topic 2 框句并“不动”
**部分接受。** https://gsr-vlm.org/ Topic 05 原文确有 “for improving geometric and spatial reasoning”，“geometric reasoning” 不是 Topic 2 专属。R0 选择“保留不动”的原因是更早用户指示：已写入的 Topic 2 句不撤销、也不再扩写，**不是**认为该词禁用。同意：真正的缺口是“学到什么空间结构”的证据，而不是删这个词。R1 已把试验床框句、诊断（有条件）和相关工作升为 P1。**不写** “improves spatial reasoning”。

### A-7｜遗漏 525 条结构诊断与转换效益（最重要分歧）
**部分接受。** 同意：这两份材料**不必新实验**，可作 Topic 5 补强；转换效益数字已核（`retile_assembly_80000\summary.json`：65,503→79,298 等）。525 条诊断**可以**作为 Topic 5 证据，但必须按本轮核实的范围来写（详见下方专题 (a)）。

**反驳 RB2 的两点过强表述：**

1. **不能写 “114 条出自这 525 条输出”。** `selected_manifest.jsonl` 中 114 条 BrickMore primary 的 `original_source` **全部**指向 `D:\BrickMore\BrickNet_BrickGPT_Compirasion\BrickMore_汇总交付_20261107\展示\models\...`，`source_kind` 为 judged 45 / review_59 21 / 成功的模型 16 / round2 12 / round3 7 / nine_ldr 7 / regenerated 5 / car_trials 1；**0 条**提及 `brickmore48_eval_630`。114 条 caption 与 525 条新批 prompt 只重叠 **35**，与 630 索引（525+105 首批）重叠 **45**；`model_id` 与索引 id 重合 66 个，但其中 **21** 个同名不同提示（如 `piano-L1V2`：114 为 upright piano，索引为 “A concert piano shape.”）。另有 48 个 114 的 `model_id` 根本不在 630 索引中（`basket-L2-Q07`、`camera-L1-C1`、`car-之前_微调01` 等）。同名亦不能证明是同一次生成。
2. **不能写 “懂体素形状”。** autopsy / manifest 没有与提示词比对的形状保真字段；`shape_preserved=525` 只表示重铺前后界内体素并集一致。RB2 自己在 A-2 草稿里已警告，但 R1 计划 §0.2 仍写“懂体素形状，但不懂钉柱咬合”。

**R2：** 在用户批准（U12）且 U10 不把权重绑死为 step-79,000 的前提下，用已复算字段写几何探针（钉柱连通、分量数、重叠、碎片落地/悬空、求解档位）。称 “525 prompts from `brickmore48_eval_630`”（构成：`items_index.json` 中 batch=2 的 21×5×5）。正文一段，表默认附录；不写 additional / 形状保真 / spatial-reasoning benchmark。转换效益句吸收。

### A-8｜不新增文献，遗漏 Topic 5 相关工作
**接受。** R1 已吸收 MeshGPT / LLaMA-Mesh / SpatialVLM（本侧已用 arXiv API 补全全部作者；venue 暂只写 arXiv）。不写“我们提升了 VLM”。

### A-9｜以 Overleaf 为主路径
**部分接受。** 免费版每项目 1 名协作者、需上传未发表稿，反对“便于共同检查”的理由成立；box 实测编译很快，超时不是主因。R1 已改以 box TinyTeX 为主。**仍保留 Overleaf pdfLaTeX 作为备份**，不排除。

### A-10｜配对检验“不做多重比较校正”
**部分接受。** R0 原意是“不要把未预注册的检验写成最终推断”，不是禁止校正。6 次检验若报道 p 值，**同意用 Holm**。R1 已把符号检验 + Wilcoxon + Holm 列为推荐方案。计划中仍不预填 p 值。

## B. 优先级

### B-1｜把“维持不变”的约束列为 P0 任务
**部分接受。** 同意它们是约束而非新动作。R2 将改标为 **“P0 约束（维持）”**，与 P0 执行项分开。但执行清单里仍须可见，以免超页时误移 Algorithm 1 或改主表。

### B-2｜中文历史图定为 P2、“保持现状”
**反驳（仅针对“推荐删除”作为默认）。** 观感与“require verification”的风险成立，应列为用户决策，选项包括删除（`\iffalse`、磁盘保留）与保留并加说明（C′）。前几轮用户已规定未经确认不得删除这些图；它们全部在附录，**正文页数影响为 0**（V1.5 `main.pdf`：image13–19 对应第 7、8、9、10、13 页的 Figure 6–12）。默认仍是保留；用户同意删除后再执行。图内中文与选项见专题 (d)。

### B-3｜Topic 5 定位改写标为 P2“不动”
**部分接受。** R0 过保守。R1 已将试验床句、有条件诊断、相关工作、贡献改写升为 P1。仍不同意把摘要写入 525 全表、或把 Scope 改写标成 P0（V1.5 Scope 已合规）。

### B-4｜L1–L5 分层定为“P1/P2 可选”
**接受。** 源表存在且抽查与 `scores.csv` 复算方向一致。R1 已改为 P1、附录表、正文至多 1 句；写入前再算一遍。

## C. 超页或时间线

### C-1｜把全体作者 OpenReview profile 放在 11-18
**接受。** 专题 (c)：官网未写审核周期；OpenReview 文档写明公共邮箱注册 “may take up to 2 weeks in moderation”。R1 已改为 **11-15 当天**注册。再强调：有公共域邮箱的作者必须立刻注册并尽量验证机构邮箱。

### C-2｜T5 页数高估，整体留下约 0.44 页“不用”
**部分接受。** 删去 `max_bricks` 与 66/114 后，协议句大约 +0.02–0.08 页，R0 的 +0.12–0.18 确偏高。但不同意把省下的篇幅默认拿去放 E-2 整表（+0.35）并宣称预算仍宽松。R2：诊断表默认附录，正文一段；编译后再决定是否上表。

### C-3｜找训练清单没有截止点
**接受。** 采用 **11-17 24:00（UTC+8）** 为找日志/清单的截止点；之后启用拆表 + 中性表注（不提模型卡、不虚构 training report）。

## D. 合规 / 防虚构

### D-1｜“retained from the training report used in this manuscript” 无出处
**接受。** 仓库中不存在可称为 training report 的文件。表注改为中性语，例如 “Corpus counts are as recorded in our training run; the raw trainer log is being re-checked.” 或不写来源短语。

### D-2｜匿名稿中写 “A released model card …”
**接受。** 该模型卡对应 `Kyle308666/BrickGPT-Qwen3-1.7B-BrickMore-48`，有匿名风险。论文不提模型卡或 HuggingFace。拆表保留 79,301 与 396,610，不把 79,322 写入 “Integrated passing models”。

## E. 同意项（E-1–E-12）
**全部接受**（这些本是 RB2 对 R0 的吸收，R1/R2 继续维持），仅作两点收紧：E-1 的拆表措辞按 D-1/D-2 修正；E-5 的协议句按 A-1/A-2 不含 `max_bricks` 与 66/114。

---

# 专题 (a)–(d)：本轮文件证据

## (a) 525 条结构诊断能否作为 Topic 5 证据

**可以，但是“几何探针”，不是空间推理基准，也不是 114 条评测的子集。**

**源文件**（`D:\BrickMore\brickmore48_eval_630\`）：

- `prompts\items_index.json`：630 条。其中 batch=2、label V1–V5 共 **525**（21 类 × 5 级 × 5 措辞）；batch=1、label「首批」、id 形如 `basket-L1-A` 共 **105**。
- `manifests\manifest_w{0,1,2}.json`：225+250+50=525 条。字段包括 `raw_single_component`、`studOK`、`shape_preserved`、`solver_tier`、`raw_bricks`、`assembly_bricks`、`union_dropped_bricks`、`regen_seed`、`prompt` 等。
- `results\raw_failure_autopsy.json`：与 525 条对齐的失败解剖（`ok` / `ncomp` / `dup` / `orphan_air` / `orphan_ground`）。`results\best_all.json` 与 `best_all.md` **不存在**。
- `README.md` 描述了 525/105 构成与协议；其中不可从上述文件复算的数字（79/105 人工判决、与训练集零重叠、82% 紧贴、108–124 s/条、45 条 union 修复）**不得写入论文**（上轮已复算：`union_dropped_bricks>0` 为 0；耗时中位 93.9 s）。

**它们测量的是：** 微调模型 **raw 输出**是否单一钉柱连通、失败时钉柱分量数、重叠体素数、脱离碎片悬空/落地、以及同一套 MILP 重铺的档位与是否保持界内体素并集。这直接检查学到的放置是否满足可检验的几何约束，符合 Topic 5 的“空间表示 / 几何约束”关切。它们**不是**空间关系问答或规划基准，也没有微调前后对照，不能写成 “improves spatial reasoning”，也不能把 `shape_preserved` 写成与提示词的形状一致。

**与 114 的关系（不是子集）：** 主对比 114 条来自 `Results\...\comparison_full\`，BrickMore 文件来自 `BrickMore_汇总交付_20261107`，不是 `eval_630\models\`。caption 与 525 新批重叠 35/114，与全部 630 重叠 45/114；即使 id 相同也可能提示词不同（21 例）。因此应写成独立的诊断集，不得写 “525 additional prompts” 或 “114 taken from the 525”。

## (b) BrickGPT `max_bricks=200` 与 36/114 零件数超过 200

见对 A-1 的答复。结论：**`brick_count` / 主表零件数 = 所保存并用于评测的 LDR 中 type-1 零件行数**，不是拒绝计数，也不是后处理拆件造成的膨胀。参数栏记录了 `max_bricks=200`，但 36 个评测产物超过该值，其中 6 个还被标为 `stable=True`。项目文件**没有**给出该参数的操作定义。正文不要写 `max_bricks=200`。

## (c) 何时注册 OpenReview

- https://gsr-vlm.org/（2026-11-15 再读）：**没有**任何关于账号/profile 审核周期的说明；只列日期与 AAAI-27 模板。
- OpenReview Submission 邀请文案要求 “All authors must have an OpenReview profile prior to submitting a paper”，同样**未写**审核天数。
- OpenReview 官方文档 [Signing up for OpenReview](https://docs.openreview.net/getting-started/creating-an-openreview-profile/signing-up-for-openreview) 原文：“Signing up with a public domain may take up to 2 weeks in moderation.” 机构邮箱通常更快；[Expediting Profile Activation](https://docs.openreview.net/getting-started/creating-an-openreview-profile/expediting-profile-activation) 建议在待审档案上添加并验证机构邮箱。

**结论：** 会场页面未给出前置周期；官方通用规则下，公共邮箱可能要 **最多两周**，而距截止不足 6 天。**现在（11-15）就应让全体作者注册或确认已有 profile**，不要拖到 11-18。

## (d) 含中文的历史图

全部只出现在附录，**不占 7 页正文**。V1.5 `main.tex` 与 `main.pdf` 对应如下（PDF 页码按 `/workspace/V1.5_out/main.pdf` / 用户 V1.5 编译稿，16 页正文+附录；`pdftotext` 分页 1–16，第 17 页空）：

| 文件 | `main.tex` 行（约） | PDF | 图题要点 | 图内中文（据图像识读，非翻译改写） |
|---|---|---|---|---|
| `figures/image13.png` | L300–304 | 第 7 页 Figure 6 | 接触式重力筛查；图注写明中文标签保留 | 「每个重叠螺柱 4 个接触点（±0.25 格）」；「顶层积木」「底层积木」「底层」；「地面接触：底层积木角点（内缩 0.05），只受压」 |
| `figures/image14.png` | L308–309 | 第 8 页 Figure 7 | 转换与筛查对比；图注 require verification | 「(a) 80,000 模型几何装配通过数」；纵轴「几何装配通过率（%）」；柱名「严格策略 v3 (10-11)」「放宽档 多接地组件 (10-12)」「接口重铺 retile 全量 (10-13)」「钢琴B重生成后预览统计 (10-14)」及 7,902 / 65,503 / 79,298 / 79,301；「(b) 假设条件下自重静力筛查通过数（对数轴）」；图例「最终状态自重平衡通过」「最终+全部完成层前缀通过」等 |
| `figures/image15.png` | L314–315 | 第 8 页 Figure 8 | 分类通过率；require verification | 纵轴「几何装配通过率（%）」；图例「严格策略 v3（原发布）」「放宽档（多接地组件）」「接口重铺 retile」；横轴类别名为英文 |
| `figures/image16.png` | L318–321 | 第 9 页 Figure 9 | 160 模型样本；require verification | 纵轴「几何通过数 / 160」；横轴「原发布规则」「Q3：仅新增≤2%」「Q4 第一轮」「Q4 稀疏约束」；标注 22 / 55 / 56 / 57 |
| `figures/image17.png` | L326–327 | 第 10 页 Figure 10 | 物理筛查状态分布 | 图例含「仅受压自重平衡通过」「需未标定咬合拉力」「咬合需求未确定（超时）」「整体倾覆/零裕度」「求解器未定论」「见证被拒绝」「几何失败未评估」；轴「retile 全量」「放宽档」「模型数（共 80,000）」；可见 63,808、14,574、2,650、45,490、17,024、14,497 |
| `figures/image18.png` | L385–386 | 第 13 页 Figure 11 | 历史基线；非当前主对比 | 「(a) 分级通过比例（判据不同）」；「BrickMore-48：人工判定有合格模型的组」；「(b) 同一 114 条提示词的中位规模」；「BrickGPT 砖块数」；「(c) 逐提示词配对（蓝=stable）」 |
| `figures/image19.png` | L391–392 | 第 13 页 Figure 12 | 历史失败分类；require verification | 「(a) BrickGPT 逐砖拒绝采样原因（114 条累计）」；「(b) BrickNet 1.7B 失败尝试类型（共 53 次）」及「路径不完整」「零件缺连接器」「边语法不合法」「索引/量纲错误」「词表外零件/颜色」 |

**不是本项讨论对象、建议保留：** `image7.png`/`image8.png`（第 7 页 Figure 4，英文类名，无中文）；`image2–5,9–12`（Figure 5，修复示例，无文字）；`original_comparison.png`（第 14 页 Figure 13，英文列标题）。

**页数：** 删除 image13–19 对正文为 0；附录大约少 3–5 页（第 8–10 页几乎整页为这些图，第 7、13 页部分）。**选项：** A 从提交 PDF 注释掉并用已核实英文表替代转换数字；B 重绘英文版（费时，且多图数字自称未核实）；C 保持现状；C′ 保留并在附录段首标明 historical、不支撑任何主张。RB1 默认 C/C′，删除须用户明确同意。

---

# 第二部分：对 PLAN_RB2_R1.md 的新批评

下列编号为本文件新编（N1–N14），均引用 RB2 R1 条目。

**N1｜U12、E-2、§0.2：「114 条出自这批输出」**
与本轮核对不符，见专题 (a)。R1 仍写 “主对比 BrickMore 的 model_id … 说明 114 条出自这批输出”。应改为：114 与 525 是不同交付、不同来源目录的两套评测；仅部分 caption/id 重合，不能推断同一批生成。

**N2｜§0.2「懂体素形状，但不懂钉柱咬合」**
仍超出可复算字段。钉柱连通失败的证据充分；“懂体素形状”没有与提示词比对的度量。应删掉前半句，或等到对 `raw_report.json` 的 `voxel_components` 做完全量统计且仍只把它写成体素连通、而非形状保真。

**N3｜A-2 / I-3 / E-2 反复使用 “525 additional prompts”**
在 114⊄525 已核实后，additional 会误导为“同一批的额外抽样”。应写诊断集名称与构成，不写 additional / held-out。

**N4｜A-2 仍为 P0，且建议稿仍先出现 “reproduces voxel-level shape well”**
摘要写入 525 数字依赖 U12/U10，应为有条件 P1。草稿虽有自纠，但建议全文仍把不可写的句子放在前面，执行风险高。应只保留保守版，且摘要最多一句定性、不堆 8.8% 全表。

**N5｜I-3 仍含 “side by side without crossing layer boundaries”**
RB2 已承认 autopsy 无此字段。建议稿里不应再出现；核实前删除即可，不要作为默认可选项。

**N6｜G-1 仍写「References 标题必须出现在第 7 页或更早」**
上轮已指出：规则是正文（至结论）≤7 页，References 可以从第 8 页起。R1 未改。验收应改为：第 7 页之后无正文。

**N7｜E-1 仍写 “with the model's learned scale and bias”**
Deploy 脚本只有 `logits_per_image[:,0].float().sigmoid()`。不要写成项目脚本里的事实。

**N8｜超页兜底仍含「Algorithm 1 改为 figure*」**
与“算法留在正文”冲突，R1 未删。兜底只保留：下沉诊断表、移动 Figure 3、下沉 Table 2。

**N9｜A-2、I-3、I-4、E-2、C-1、L-1 重复同一组 8.8%/中位数 5**
与 I-2 省页目标相冲突。数字只在 §5.x 或附录展开一次。

**N10｜L-1、A-2 仍标 P0**
Scope 已写明无预训练/RL、生成器非 VLM。改写不是合规必须项。

**N11｜U2 仍写「结论：实际流程是双盲」**
按匿名 PDF 准备是对的，但官网无此四字。不要在论文或计划里写成已公布政策。

**N12｜G-3 TLDR 仍用 “79k”**
在 79,301 / 79,322 未裁定前应避免该约数。

**N13｜U3 前后不一致**
选项 C′ 正确写了不提模型卡、不写 training manifest；同条后段（约 L178–181）又出现 “sample counts are taken from the training manifest”。应删后一段，以免执行时写回无出处来源。

**N14｜B-1 文献条目作者仍不完整**
上轮已用 arXiv API 给出完整 8/7/9 人名单。R1 草稿仍用 `and others`。执行时必须补全；计划里应直接写入全名单，而不是再“执行时核对”。

另：D-1 仍写“执行时再读 relaxed”。`relaxed_assembly_80000\assembly_summary.json` 的 `geometryPassed=65503`、`addedVoxelCount=428278`、`removedVoxelCount=38230` 本侧上轮已读到，R2 计划可直接引用。
