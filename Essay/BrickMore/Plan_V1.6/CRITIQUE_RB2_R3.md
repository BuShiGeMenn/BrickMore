# 对 RB1 R2 的答复与分歧处理（CRITIQUE_RB2_R3）

- 作者：ReviewBot2（RB2）。写于 2026-11-15 约 01:20（UTC+8）。
- 读取：`Plan_V1.6\CRITIQUE_RB1_R2.md`（21,976 字节，sha256 前缀 AE23922F7B83）、`Plan_V1.6\PLAN_RB1_R2.md`（19,024 字节，AF14B5FF7E2B）。
- **只做规划**：本轮没有修改任何论文文件（V1.5 及更早版本、`main.tex`、`references.bib`、图片都没动）。只写本文件与 `PLAN_RB2_R3.md`，R0–R2 和 RB1 的所有文件保持不变。
- 引用格式：`文件路径` + 行号或字段。所有核对都在用户机器上用只读方式完成（Python 读文件、`Select-String`、`Get-FileHash`、`pdftotext`）。

---

## 本轮最重要的两项新发现（先说结论）

1. **核对 (a) 只部分支持 RB1。** 114 条主对比的 BrickMore 文件确实放在另一个交付目录，caption 与 525 条也确实只重叠 35 条。**但这 35 条不是另一次独立运行，而是 eval_630 中的同一批生成输出**：
   - 它们是 630 条候选里经人工判决选出的“最佳”（`best_all.json` 的 `choice_id` 与 `model_id` 逐一相同）；
   - 零件数与 eval_630 输出 LDR 的零件行数 35/35 相同（连同 10 条首批，45/45 相同）；
   - 同一权重版本 `92d1c595`；
   - 种子与 MILP 档位也能从 eval_630 manifest 读出。
   
   由此还推出一个 V1.5 没有写清的事实：**主对比中 45/114 条 BrickMore 输出（连同它们的提示词）是从每组 6 个候选中人工挑出的最佳**。其余 69 条来自后续的补缺、重生成和复审轮次。BrickGPT 和 BrickNet 则是在这些已选定的 caption 上各跑一次。这是对比公平性必须披露的信息。我在 PLAN R3 中新增 **E-9（P0）**，请 RB1 评议。
2. **两份计划都写错了一处：`best_all.json` / `best_all.md` 其实存在**，只是不在 `brickmore48_eval_630\results\` 下，而在 `D:\BrickMore\BrickNet_BrickGPT_Compirasion\BrickMore_汇总交付_20261107\资料与记录\`（另有两份副本，三份 sha256 均为 1003CBF4377D1508…）。所以：
   - image18(a) 的蓝柱**可以复核**，与图一致；红柱也可以复核；
   - README 中的 “79/105 组有最佳” 也可以复算：`choice_id≠NONE` 的有 79 条。
   
   我撤回 U4-b 中“image18(a) 不可复核”这条理由。

---

# 第一部分：逐条答复 RB1 的 N1–N14，以及 RB1 反驳我的 1 条（B-2）

**统计：15 条中，接受 13 条、部分接受 2 条（N1、B-2）、反驳 0 条。**

R2 时我已独立改掉了 N3–N8、N10–N12、N14（RB1 的批评针对的是我的 R1）。这些条目下面写“接受（R2 已改）”，并给出 R2 中的位置。N2、N13 和 D-1 附注在 R2 中仍有残留，R3 已经修正。

### N1｜U12、E-2、§0.2：“114 条出自这批输出”——**部分接受**
- **接受的部分**：“114 条出自这批（525）输出”的说法错误，R3 全文删除。R2 L351 已改写，但仍写“选取规则需要用户说明”。R3 改为直接引用核对结果（见下方核对 (a)）。
- **不接受的部分**：RB1 的替代表述“114 与 525 是不同交付、不同来源目录的两套评测；仅部分 caption/id 重合，**不能推断同一批生成**”。文件证据显示，这 35 条重叠项就是同一批生成。证据与逐条数字见核对 (a)。
- **R3 的写法**：
  - “525 条诊断批次是一个候选池。主对比 114 条中有 35 条 BrickMore 输出，就是从这个池中经人工判决选出的同一文件；另有 10 条选自同组的 105 条首批。其余 69 条来自后续轮次。”
  - 正文不写 “additional”，不写 “114 taken from the 525”，也不写 “separate/independent run”。

### N2｜§0.2 “懂体素形状，但不懂钉柱咬合”——**接受**
- R2 的 §0.2 L111 和 §0.3 L120（“体素形状 vs 钉柱咬合”）仍残留这一说法，我在 R2 中漏改。R3 删去“懂体素形状”，改为“raw 输出大多不能跨层咬合，形成单一钉柱连通件”。
- 论文建议文本里本来就没有这半句（R2 A-2 L434 已明确禁止）。

### N3｜反复使用 “525 additional prompts”——**接受（R2 已改）**
- R2 变更记录第 4 条与 E-2 L642 已改为 “a separate diagnostic run on 525 prompts”。
- R3 进一步删去 “separate”，理由见 N1：35 条与主对比是同一输出。

### N4｜A-2 仍为 P0，建议稿先出现 “reproduces voxel-level shape well”——**接受（R2 已改，R3 再收紧）**
- R2 已把 A-2 降为 P1，建议稿只保留保守版（R2 L429）。
- R3 采纳 RB1 的立场：**摘要不放任何诊断数字**，最多半句定性。这就消除了 R2「仍有分歧」第 2 项。

### N5｜I-3 仍含 “side by side without crossing layer boundaries”——**接受（R2 已改）**
- R2 的建议文本（L470）里已经没有这半句，只在“注意”中把它作为禁写项引用（L473）。
- R3 把这条引用移到 §4 不做清单，I-3 注意栏只保留可核实的替代句。

### N6｜G-1 仍写 “References 标题必须出现在第 7 页或更早”——**接受（R2 已改）**
- 见 R2 §1 L146 与 G-1 第 3 步（L367）：验收标准是“第 7 页之后没有正文（摘要到结论）”。

### N7｜E-1 仍写 “learned scale and bias”——**接受（R2 已改）**
- R2 的 E-1 建议句（L628）只写 “the sigmoid of the image--text logit”。
- R3 还把 U8 证据栏 L297 的 “模型自带 logit scale/bias 后的” 改为“`logits_per_image` 的 sigmoid”，以免执行时被误抄进正文。

### N8｜兜底含 “Algorithm 1 改为 figure*”——**接受（R2 已改）**
- 见 R2 §1 L162–168：兜底顺序是诊断表 → Figure 3 → Table 2 → E-3，并明确 Algorithm 1 不改排。

### N9｜多处重复 8.8% / 中位数 5——**接受**
- R2 已把 I-3、I-4、C-1、L-1 改成定性写法，但摘要仍保留一个数字，M-4 也重复了档位数字。
- R3 的处理：
  - 摘要不放数字（见 N4）；
  - M-4 改为指向 E-2 的引用，不再单列数字；
  - 诊断数字只在 E-2（正文一段，表默认放附录）出现一次。

### N10｜L-1、A-2 仍标 P0——**接受（R2 已改）**
- 见 R2 变更记录第 1 条：两者均为 P1。

### N11｜U2 写“结论：实际流程是双盲”——**接受（R2 已改）**
- 见 R2 U2 L197：只写“按 OpenReview `authors` 字段的读者限制，审稿人看不到作者”。

### N12｜TLDR 用 “79k”——**接受（R2 已改）**
- 见 R2 G-3 L388。

### N13｜U3 前后不一致：后段仍有 “sample counts are taken from the training manifest”——**接受**
- R2 L230 仍残留这句，是我漏改的。R3 删去整段旧兜底，U3 只保留选项 C′ 一种兜底写法（不提模型卡，不写 training manifest，也不写 training report）。

### N14｜B-1 文献作者不全——**接受（R2 已改，R3 清理残留）**
- R2 R-1/R-2 的 bib（L510–540）已是 8 / 7 / 9 人全名单。
- B-1（L778）与 §5 文献核对段（L843）还残留“执行时补全”“前 6 位一致”的旧说法。R3 统一改为“已补全，执行时原样使用”。

### 附注｜D-1 “执行时再读 relaxed”——**接受**
- 本轮已在用户机器上读取 `D:\BrickMore\Train\datasets\relaxed_assembly_80000\assembly_summary.json`：
  - L8 `"geometryPassed": 65503`、L21 `"addedVoxelCount": 428278`、L22 `"removedVoxelCount": 38230`；
  - L9 `"gravityScreenedPassed": 478`、L10 `"finalGravityEquilibriumPassed": 2650`；
  - L13–15：45490 / 17024 / 14497；
  - L75 `"originalPublishedGeometryPassed": 7902`。
- `D:\BrickMore\Train\datasets\assembly_80000\assembly_summary.json` L9 `"success": 7902`。
- R3 的 D-1、APP-2、U7 改为直接引用这些行，删除“执行时核实”。

### B-2（RB1 反驳我）｜中文历史图默认删除——**部分接受**
- **接受**：
  - 默认动作是保留（C′）。这些图全部在附录，正文页数影响为 0（RB1 专题 (d)：PDF 第 7、8、9、10、13 页，Figure 6–12）；
  - 删除必须经用户明确同意（`V1.5\REVIEW_V1.5.md` L6）；
  - R3 不再把 A 标为 ★。A 与 C′ 并列为用户选项，默认 C′。
- **保留的部分**：
  - 我仍把 A（`\iffalse` 移出 PDF，文件保留，用英文表替代 14/17/19）列为可选项，因为英文投稿中出现中文图的观感风险是真实存在的；
  - 我也撤回 R2 中“image18(a) 不可复核”的理由（见本文开头第 2 点和下方 U4 更新）。
- **结果**：这一项不再是 RB1 与 RB2 之间的分歧，只剩用户选择。

---

# 第二部分：RB1「仍有分歧」6 项的立场

| # | 议题 | RB2 R3 立场 | 说明 |
|---|---|---|---|
| 1 | 附录中文历史图 | **同意（默认 C′）；最终由用户选 A / C / C′ / B** | 见 B-2。R3 默认 C′：附录段首加 “Historical material with Chinese labels; not used for any claim.”，image14/17/19 的 “require verification” 改为指向发布报告。**新增**：image18 图注补一句 “(a) compares different criteria: BrickGPT's per-prompt stability flag versus whether human review found an acceptable BrickMore output among six candidates per group; not a like-for-like comparison.” 数字来源见下方 U4 更新。RB2 不再推荐删除 image18(a)（R2 的理由已不成立）。 |
| 2 | 525 条结构诊断的写法 | **同意 RB1 的版式；对 114/525 关系的表述提出折中** | 同意：正文一段、表默认放附录、摘要不放数字、不写 additional / 114 出自 525 / 懂体素形状，数字只出现一次。不同意“不能推断同一批生成”，核对 (a) 证明 35 条是同一输出。**折中表述**（可由文件裁定，无需用户）：“The 525-prompt diagnostic batch is part of the candidate pool from which 35 of the 114 comparison outputs were selected (Section 5.1).” 是否写入诊断本身，仍须用户批准（U12）。 |
| 3 | 标题 | **只有用户能决定** | RB2 仍略偏好 A（点出 stud-connected），也明确接受 B′。两者都不引入虚假主张。R3 把 A、B′ 并列，不再论证。 |
| 4 | 显著性检验 | **同意；p 值由用户批准** | 双方一致：符号检验 + Wilcoxon，6 次比较，Holm 校正，不预填 p 值，不显著就如实写。补充：E-9 披露“45 条为人工从 6 个候选中挑选”后，检验结果只能解释为“这批交付输出”的差异，不能解释为模型能力的差异（V1.5 L216 已有 “rather than isolated model capability”，保持不变）。 |
| 5 | U10 评测权重 | **同意；由用户确认，R3 补充证据** | 新证据：`BrickMore_汇总交付_20261107\资料与记录\provenance.json` L3 写有 `"revision": "92d1c595f5fe076971cc2633d6844f097a84eef3"`，与 `eval_630\README.md` L5 的 `92d1c595` 前缀一致；`92d1c595` 是 Git 提交号，而 `downloads\...\model.sha256` 的 `75f79af15dd7…` 是文件哈希，两者本就属于不同的标识体系。因此，45 条 judged 输出（来自 eval_630）是 `92d1c595`。5 条 `regenerated` 应当对应 11-07 重生成包（`provenance.json` 所记录的那一包），但这个对应关系是按目录和交付说明推断的，没有逐文件核对。其余 64 条（review_59 21、成功的模型 16、round2 12、round3 7、nine_ldr 7、car_trials 1）在项目里没找到权重记录，**仍需用户确认**。注意：`provenance.json` 中的仓库名含 GitHub/HF 用户名，绝不能进论文。 |
| 6 | 79,301 vs 396,610 / token | **同意；由用户决定** | 双方一致：11-17 24:00（UTC+8）前找训练清单，找不到就启用拆表 C′（不提模型卡，不写 training manifest 或 training report，不把 79,322 填进表）。R3 已删除与之矛盾的旧兜底（N13）。 |

---

# 核对 (a)：525 与 114 是否不同批次、35 条重叠是否是独立运行

**结论：RB1 描述的目录和重叠数字正确，但“不同批次、独立运行”的推断不成立。35 条重叠是同一次生成的同一输出（连同首批是 45 条），而且是人工挑选的结果。**

1. **RB1 的描述性数字，全部复核成立**：
   - 文件 `D:\BrickMore\Results\three_model_comparison_20261111\intake\Results\comparison_full\selected_manifest.jsonl`（sha256 BC3962358139DE93…）共 462 行，其中 BrickMore `primary=True` 114 条；
   - `source_kind` 分布：judged 45、review_59 21、成功的模型 16、round2 12、round3 7、nine_ldr 7、regenerated 5、car_trials 1；
   - `original_source` 全部在 `D:\BrickMore\BrickNet_BrickGPT_Compirasion\BrickMore_汇总交付_20261107\展示\models\` 下，**没有一条**指向 `eval_630`。例：L2 为 `basket-L1V5`，`original_source` 是 `...\展示\models\judged_basket-L1V5_st.glb`，`part_count` 420；
   - caption 与 525 条 manifest 的 `prompt` 逐字一致的有 **35** 条，与全部 630 条（各 `models\<类>\<组>\prompt.txt` 第 1 行）一致的有 **45** 条。
2. **这 45 条就是 `source_kind=judged` 的 45 条，没有其他来源**。重叠 35 条全是 V1–V5，另外 10 条是首批 `-A`。
3. **“judged” 的含义：630 条候选的人工判决最佳**：
   - `BrickMore_汇总交付_20261107\模型总清单.csv` L2：`basket,1,basket-L1V5,judged,人工判决最佳,…`。该文件共 45 行 `judged`；
   - `...\资料与记录\best_all.json`（105 条，sha256 1003CBF4377D1508…）：45 条 judged 的 `model_id` **全部**是某条记录的 `choice_id`。例：第 1 条为 `"choice_id": "basket-L1V5"`、`"prompt": "A round storage basket with a closed base."`；
   - `D:\BrickMore\brickmore48_eval_630\README.md`：
     - L14：“每个‘类 × 等级’构成一组（共 105 组），每组 6 个候选（525 批的 V1-V5 + 首批 1 条）参与人工判决”；
     - L91–94 §7：“5 名评审……逐组比较 6 候选……每组选最佳或判‘全部不合格’……79 组 (75%) 有最佳”。
4. **输出层面相同（不是重跑）**：
   - 对 45 条 judged，把 `selected_manifest` 的 `part_count` 与 eval_630 对应目录 `models\<类>\L<n>[V<k>]\stitched.ldr`（没有 stitched 时用 `raw.ldr`）的 type-1 行数比较，**45/45 相同**；`prompt.txt` 与 caption 也 45/45 逐字相同；
   - 对 35 条 V 系列，eval_630 manifest 的 `assembly_bricks` 与 `part_count` 也全部相同，没有不一致；
   - 作为反例，21 条 `review_59` 与 7 条 `nine_ldr` 的 id 在 eval_630 中有同名目录，但 prompt 与零件数都**不同**。这些是复用 id 的另一次运行，与 RB1 所说“21 个 id 相同但提示词不同”一致；
   - 局限：114 侧保存的是 GLB，eval_630 侧是 LDR，格式不同，所以没有做字节级比对。证据是零件数、caption 和人工判决 `choice_id` 三者同时一致。
5. **种子、档位、权重（35 条重叠项）**：
   - eval_630 manifest 的 `attempt`：@42 23 条、@104 10 条、@2026 2 条；
   - `solver_tier`：12s 19、60s 8、none_needed 4、180s 2、600s 2；
   - 其中 **bench-L1V5、bench-L2V4 用的是 600 s 档**（`manifests\manifest_w0.json` L1074、L1150），**basket-L3V1 带 `regen_seed` 2027**（`manifest_w0.json` 中 `"regen_seed": 2027` 出现在 L208、L1689、L1955，basket-L3V1 是其中之一）。这两种情况都超出了 V1.5 Algorithm 1 的 $T=(12,60,180)$ s 与 $S=(42,104,2026)$。2027 可以算作 QueueReseed，600 s 档则不在算法里。这一点并入 U13；
   - 权重：`eval_630\README.md` L5 “权重版本 `92d1c595`”；`汇总交付\资料与记录\provenance.json` L3 revision `92d1c595f5fe…`（这份 provenance 记录的是 11-07 重生成包）。
6. **由此推出的新问题（E-9，P0）**：V1.5 §5.1 只写了 “The systems differ in candidate selection, filtering, and post-processing”（L216），没有说明 BrickMore 一侧有 45/114 条是“同组 6 个候选（6 种提示措辞）中人工判为最佳者，连同其提示词一起入选”，也没有说明其余 69 条来自后续的补缺、重生成和复审轮次。BrickGPT 一侧则是在这些 caption 上用 seed 42 各跑一次（`brickgpt_generation_summary.jsonl`）。这是对比偏向 BrickMore 的选择效应，应当具体披露。PLAN R3 E-9 给出了建议句，数字全部来自上面的文件。

# 核对 (b)：`max_bricks` 在项目中是否有定义

**结论：RB1 正确。全项目没有任何代码或配置定义 `max_bricks`，它只作为运行记录字段出现。论文不应写它。**

1. **扫描范围**：`D:\BrickMore` 全树，文本文件 11,597 个，命中 131 个。另外对 `.py/.yaml/.yml/.toml/.cfg/.sh/.ps1/.ipynb/.log/.txt` 单独扫了一遍，范围包括 `D:\BrickMore`、用户 Python 安装目录、`AppData\Roaming\Python` 和 HF 缓存。检索词为 `max_bricks`、`max_n_bricks`、`maxBricks`、`max_regen`、`max_regenerations`，以及中文的“最大砖 / 砖块上限 / 砖数上限”。
2. **数据和记录类命中（仅这些）**：
   - `D:\BrickMore\BrickNet_BrickGPT_Compirasion\BrickGPT原版_AB对照实验_20261109\ab_experiment_20261109\{A,B}\<prompt>\report.json`，共 114 个，每个文件有一行 `"max_bricks": 200,`，行号依文件不同为 L14、L16、L17 或 L18。例：`A\basket_L1_P01\report.json`，同文件还有 `max_regen 8`、`world_dim 20`、`use_gurobi false`、`seed 42`、`brick_count 112`、`n_regenerations 8`、`stable false`；
   - `...\ab_experiment_20261109\summary.jsonl`（114 行）；
   - `D:\BrickMore\Deploy\build\comparison_20261110\BrickMoreComparison\Provenance\brickgpt_generation_summary.jsonl`（114 行，字段含 `max_bricks`、`max_regen`、`world_dim`、`use_gurobi`、`model`）；
   - 其余命中全是评审或计划 markdown（`Plan_V1.6\*`、`V1.3–V1.5\REVIEW_*.md`）。
3. **代码中没有**：所有代码文件对上述检索词 0 命中。`world_dim` 只出现在 BrickMore 自己的工具里（例：`Evaluation\comparison\build_inputs.py` L83 读 `report.get('world_dim')`；`toolkit_snapshot\optimized_geometry.py` L45 `world_dim: int = 20` 的默认值），与 BrickGPT 的砖数上限无关。
4. **BrickGPT 相关目录里没有源码**：
   - `BrickNet_BrickGPT_Compirasion\BrickGPT\` 只有 `A_ldr_57.zip`、`B_ldr_57.zip`（本轮列目录：各 57 个 `.ldr`，没有代码）和 `总结_AB对照_20261109.md`。后者内容实为 BrickNet 1.7B 的 A/B 实验（L1–5），与 BrickGPT 无关；
   - `BrickGPT原版_AB对照实验_20261109\` 只有 114 个 txt、114 个 json、114 个 ldr 和 1 个 jsonl。
5. **BrickGPT 论文本身（项目内 `D:\BrickMore\Essay\brickGPT\2505.05469v3.pdf`，16 页，sha256 前缀 bc4e753bee123914）也没有 `max_bricks`**：
   - Algorithm 1（第 6 页）只有 `max_rejections`（逐砖拒绝采样上限）和 “max rollbacks exceeded”；
   - 第 8 页：“We allow up to 100 physics-aware rollbacks … The nonlinear optimization in Eqn. 3 is solved using Gurobi”；
   - 第 4 页的 “typically-sized (i.e., < 200 bricks) structures” 只是描述稳定性分析耗时的数据集规模，不是生成上限；
   - 全文检索 “max_bricks / maximum number of bricks / brick limit” 命中 0。
6. **附带发现（新增 U14，不写进论文，除非用户确认）**：
   - 运行记录 `max_regen=8`、`use_gurobi=False` 与 BrickGPT 论文报告的“最多 100 次 rollback、Gurobi 求解稳定性”不同；
   - `max_regen` 是否对应论文中的 rollback 次数，项目内同样没有定义（观测到 `n_regenerations` 最大为 8，其中 30 条在 8 次时 `stable=False`）；
   - 因此正文不能写“BrickGPT 按作者默认配置运行”；
   - 另外，`report.json` 和 `brickgpt_generation_summary.jsonl` 的 `model` 字段含本地用户路径（`D:\Users\<用户名>\Desktop\…`），属于匿名风险，任何附件里都不能带上。

---

# 本轮对 PLAN 的影响（详见 PLAN_RB2_R3.md 变更记录）

- 新增 E-9（P0，选择效应披露）和 U14（BrickGPT 运行配置）；M-4 改为引用型条目；
- U4：默认 C′，A 不再标 ★；image18 补图注；撤回“不可复核”；
- U10、U12、U13 引用本轮新证据；
- 删除 N2、N13 的残留，把 D-1 改为直接引用数据；
- 条目数：P0 7、P1 21、P2 10、U 14，合计 **52**。

*本文件只写入 `D:\BrickMore\Essay\BrickMore\Plan_V1.6\CRITIQUE_RB2_R3.md`。没有修改任何论文文件。*
