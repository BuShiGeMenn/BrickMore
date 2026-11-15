# BrickMore V1.6 修订计划（ReviewBot1，R1）

- 计划文件：`D:\BrickMore\Essay\BrickMore\Plan_V1.6\PLAN_RB1_R1.md`
- 本文件由 `PLAN_RB1_R0.md` 修订而来。**`PLAN_RB1_R0.md` 保持不动。** 交叉审阅见同目录 `CRITIQUE_RB1_R1.md`。
- 基稿：`D:\BrickMore\Essay\BrickMore\V1.5\main.tex`（2026-11-14 23:36 UTC+8）及 `V1.5\REVIEW_V1.5.md`；并对照 `PLAN_RB2_R0.md` 与项目 `D:\BrickMore`。
- **本文件只做规划。未修改任何版本文件夹中的论文源文件。**
- 目标 venue：[GSR-VLM](https://gsr-vlm.org/)（AAAI-27 workshop，非存档）。**仅对齐 Topic 5**。不考虑 Topic 2。
- 硬约束：官方 AAAI-27 模板；长文**正文（摘要至结论）≤ 7 页**（参考文献与附录不限；References 可以从第 8 页起，只要第 7 页之后不再有正文）；Algorithm 1 必须留在正文，不以改排 `figure*` 作为超页兜底；不虚构数字或文献；不宣称做过预训练、强化学习，或把生成器称为 VLM。
- 截止：**2026-11-20 19:59（UTC+8）**（＝ 2026-11-19 AoE）。建议 **11-19（UTC+8）** 完成提交。页脚仍写 “Proposed AAAI-27 workshop · Details subject to confirmation”。
- 当前页数（V1.5 `main.pdf`）：共 16 页；正文在第 6 页左栏结束。建议本轮正文净增控制在 **≤ 0.6 页**，新大表优先放附录。

文中数字均注明出处。拟议新文献已在本轮用 arXiv API（2026-11-15）核验 ID/标题/作者名单，venue 暂只写 arXiv。

---

## Changelog（相对 PLAN_RB1_R0）

### 从 RB2（`PLAN_RB2_R0.md`）吸收的内容

1. **U12 / E-2 / M-4**：将 `brickmore48_eval_630` 的 525 条可复算诊断作为 Topic 5 的补充证据（P1，**有条件**：须用户批准；须先处理 U10；正文不得写 “additional prompts / spatial-reasoning benchmark / voxel-level shape fidelity”）。数字本轮已对照 manifest / autopsy 复算，与 RB2 相符。不可复算的 README 数字（79/105 人工判决、82% 碎片、108–124 s/条、45 条 union 修复）**不写入**。
2. **D-1 / APP-2**：写入转换效益（relaxed 65,503 → retile 79,298，及 `summary.json` 中的体素改动）。须与 79,301 分口径。Relaxed 的 428,278 / 38,230 本轮已在 `relaxed_assembly_80000\assembly_summary.json` 读到，写入时引用该文件。
3. **D-2**：表 1 拆成 “release reports” 与 “fine-tuning corpus”，作为 A3 的实施形式（不是删除 79,301）。
4. **U10**：评测权重短标识 `92d1c595` 与下载模型 `model.sha256` 体系不同，新增「待用户确认」；未确认前不写 “all evaluated outputs use the step-79,000 checkpoint”。
5. **I-1**：引言增加 Topic 5 “可检查的空间表示试验床” 框句。
6. **I-2**：引言去重以省页（优先级作 **P1**，不作 P0）；若删 “output does not include color”，必须移到 §4.1。
7. **R-1 / R-2 / B-1**：新增 MeshGPT（arXiv:2311.15475，8 作者）、LLaMA-Mesh（arXiv:2411.09595，7 作者）、SpatialVLM（arXiv:2401.12168，9 作者）短段；venue 只写 arXiv；不写“我们提升了 VLM”。
8. **E-3 / E-4 / I-5**：105 组等权、未截断子集、L1–L5 分层——来源 `三模型测评结果分析.md`，抽查数字相符；作为补充口径放附录，不替代主表。R0 曾因“本轮未重算”而暂缓 105 组；现改为批准后可写，并注明来源文件。
9. **E-6**：`shape_preserved` 表述改为 “same in-bounds voxel union”，不写 prompt 保真。
10. **E-7**：P_inv 小数位与 “VQA”/“VQAScore” 用语统一（P2）。
11. **U5**：检验方案可同时采用符号检验与 Wilcoxon，并考虑 Holm（3 指标 × 2 对照）；仍须批准后才写入 p 值；本计划不预填。
12. **G-2**：匿名检索清单补上 Kyle308666、BuShiGeMenn（分别见于模型卡与 `piano_table_retile_7620\download_manifest.json`）。V1.5 `main.tex` 当前无这些串。
13. **G-3**：全体作者立即注册 OpenReview profile；TLDR 不用未裁定的 “79k”。
14. **G-4 / G-5**：美式拼写与术语统一，并入 P1 通读。
15. **超页兜底顺序**：先考虑移动 Figure 3，再下沉配置表；**不**把 Algorithm 1 改成 `figure*` 或移出正文。
16. **U6 / U7 / U11**：与 R0 一致并写明：不做新空间推理基准与再训练；转换对比不叫 model ablation；默认不附 reproducibility checklist。

### 相对 R0 的自身调整（含对 RB2 的不吸收）

- **编译路径（原 A8）**：主编译改为**已验证的 box TinyTeX**（`latexmk -pdf`）；Overleaf pdfLaTeX 与本机 MiKTeX 作为备份，不排除 Overleaf。
- **中文历史图（原 A4）**：维持默认保留；不采用 RB2 将删除作为推荐默认（用户若明确同意删除，再按 `\iffalse` 注释、磁盘保留）。
- **模型数（原 A3）**：维持“两口径并存 + 拆表/加注”，不接受“维持现状不推荐”且暗示应拿掉 79,301 的表述。
- **A-2 / L-1 不升为 P0**：525 诊断不进摘要作为必须项；Scope 句已合规，只做有限度的措辞收紧。诊断数字只在 §5.x 展开一次。
- **页面规则**：验收标准改为“第 7 页之后无正文”，不是“References 标题必须在第 7 页或更早”。
- **E-2 正文写法**：用 “525 prompts from `brickmore48_eval_630`”，在用户说明 114 与 525 的关系之前**不写 additional / held-out**。
- **SigLIP2**：只写 “sigmoid of the image–text logit”，不写项目脚本中未出现的 “learned scale and bias”。
- **未来工作**：若提及 connectivity-based rewards，必须标明 outside the scope，且不出现在摘要/贡献。
- 页数预算加入 D-1、相关工作短段、E-2 正文段（表默认附录）及 I-2 节余，目标仍 ≤ 6.6 页。

---

## 0. 本轮重新核查的证据（供决策引用）

### 0.1 GSR-VLM 政策与双盲（2026-11-15 再次读取）

- 官网 https://gsr-vlm.org/：**仍然没有出现** anonymous / double-blind / review policy / reproducibility checklist 等字样。明确写出的是：非存档；长文 7 页正文、参考文献与附录不限；必须使用 [AAAI-27 模板](https://aaai.org/authorkit27/)；OpenReview 投稿；截止日期同上。
- OpenReview 邀请 `AAAI.org/2027/Workshop/GSR-VLM/-/Submission`：`authors` 与 `pdf` 字段的 `readers` 仅限组委会与 Submission Authors；`data_release` 写明录用后、会议结束后才向公众公布投稿与作者名。组委会联系邮箱出现在组资料中：`li.li02@usc.edu`。
- **建议：PDF 继续使用 `\usepackage[submission]{aaai2027}`，不要把作者写进 PDF。** 按 OpenReview 字段限制按匿名审稿准备，但论文中不要写“工作坊官方宣布双盲”。

### 0.2 79,301 vs 79,322，以及 token 数

| 数字 | 出处 | 含义 |
|---|---|---|
| 79,301 | `Train\datasets\CURRENT_DATASET_STATUS.md`；`Train\README.md`；V1.5 表 1 与 §3.3 | 整合口径的几何通过数：79,298 − 1,902 + 1,905 = 79,301。是两份发布报告的计算，**不是**全量重跑；“当前统计本身不证明某次训练已经使用替换数据”。 |
| 79,298、1,902、1,905、699 未通过 | 同上；V1.5 L97、表 1 | 与论文一致。 |
| 79,322 × 5 = 396,610 | **仅见** `downloads\BrickGPT-Qwen3-1.7B-BrickMore-48\README.md` | 模型卡的训练用模型数。算术成立。 |
| 396,610 与 356,955 / 39,655 | 模型卡与 V1.5 表 1 | 两边一致。论文称 validation，模型卡称 test。 |
| 79,301 × 5 = 396,505（差 105） | 由上推出 | 105 / 5 = 21 **只是算术**，没有 21 个额外模型的清单，不能写成事实。 |
| 2,228,044,818 tokens | 只出现在 V1.5 表 1 | 仓库中**未找到** `trainer_state.json` / `build_stats.json` / `train_brickmore.log`。 |
| ~2.19B tokens | 同一模型卡 | 约数，与 2.228B 量级接近但不相同。 |
| 24,448 tokens/s，25.3 h | V1.5 附录 B | 24,448 × 25.3 × 3,600 = 2,226,723,840，与表中总数相差 1,320,978。可作约数解释，**不可称为已核实的同一观测，也不可替换表中数字**。 |

### 0.3 PE / SigLIP2 / VQAScore 在代码里怎么算

脚本：`Evaluation\pipeline\evaluate_paper_images.py` 与 `Deploy\build\comparison_20261110\BrickMoreComparison\Scripts\evaluate_paper_images.py`（行号依前者）。

- **VQAScore**（L34–36、L81–83）：对 “Yes” 做**全词表 softmax** 概率。
- **SigLIP2**（L89–99）：`logits_per_image[:,0].float().sigmoid()`。文本 `max_length=64`。不要添加脚本中未出现的 “learned scale and bias”。
- **PE**（L102–126）：L2 归一化后的点积，即余弦相似度，无 sigmoid。文本上限 72。

### 0.4 已有 per-prompt 分数与 BrickGPT 协议

`Results\three_model_comparison_20261111\intake\Results\comparison_full\report\scores.csv`：三系统 primary 各 114 条。本轮复算 BrickMore vs BrickGPT：VQA 91/0/23，PE 95/0/19，SigLIP2 91/0/23（无平局）。

`Deploy\build\comparison_20261110\BrickMoreComparison\Provenance\brickgpt_generation_summary.jsonl`：114 条全部 `world_dim=20`、`max_bricks=200`、`seed=42`；stable True 66 / False 48。

### 0.5 转换效益与 525 条诊断（本轮复算，R0 未列入正文计划）

`Train\datasets\retile_assembly_80000\summary.json`：`baselinePassed=65503`，`geometryPassed=79298`，`recoveredFailures=13795`，`addedVoxelCount=228582`，`removedVoxelCount=125`，`zeroVoxelChangeSuccessfulModels=31532`。

`Train\datasets\relaxed_assembly_80000\assembly_summary.json`：`geometryPassed=65503`（故 65,503 即 relaxed 几何通过），`addedVoxelCount=428278`，`removedVoxelCount=38230`。

`brickmore48_eval_630\`：三份 manifest 合计 525 条；`solver_tier` 12s 326、60s 133、180s 18、600s 2、`none_needed` 46；`studOK` 与 `shape_preserved` 均为 525；含 `regen_seed` 28 条；`raw_bricks` 中位 183（77–623）；`assembly_bricks` 中位 452；`union_dropped_bricks>0`＝0；耗时中位 93.9 s（22.9–401.6）。`none_needed` 按级 13/9/9/7/8。`raw_failure_autopsy.json`：失败 479，失败 `ncomp` 中位 5（2–33）；`dup>0` 50，`dup==0` 429。`results\best_all.json` / `best_all.md` **不存在**。README 中无法由这些字段复算的数字一律不用。`shape_preserved` 仅表示 retile 与 raw 的界内体素并集一致。114 条与 525 条的子集关系**尚未确认**（`model_id` 仅命名相近）。

分析文档 `Results\three_model_comparison_20261111\analysis\三模型测评结果分析.md`：105 组等权与未截断子集、L1–L5 表存在；抽查与 RB2 引用四位四舍五入后一致（如 BrickMore 105 组 0.234664 / 0.183975 / 0.125722；L5 VQA 0.096763 / 0.074845 / 0.036335）。写入前再从该文件或从 `scores.csv` 重算一遍，不在计划中预填未复核的单元格。

### 0.6 匿名泄漏（项目中有，V1.5 正文目前没有）

- `downloads\BrickGPT-Qwen3-1.7B-BrickMore-48\README.md`：Kyle308666
- `Train\datasets\piano_table_retile_7620\download_manifest.json`：BuShiGeMenn

投稿前必须检索源码、PDF、图注与附录。

---

## A. 「待用户确认」项：推荐选项与理由

### A1. 标题（P0 决策，约 15 分钟，页数 ≈ 0～+2 行）

- 现状：`\title{BrickMore}`。
- **推荐：改为描述性标题，须用户圈定用词后再改。** 仍推荐：
  - *BrickMore: Learning Spatial Brick Assemblies by Agentic Data Generation and Language-Model Fine-Tuning*
  - 备选：*BrickMore: Learning Stud-Connected Brick Assembly from Agentically Generated Voxel Data*（RB2 更倾向 stud-connected 案；若用户更强调钉柱连通约束可选备选，但不在标题写 “improves spatial reasoning”）。
- 同步 OpenReview 的 title 字段。

### A2. 作者信息与是否双盲（P0 决策）

- **推荐：（1）PDF 保持 `[submission]` 匿名；（2）作者只进 OpenReview 表单；（3）全体作者立即注册 profile（审核可能数日）；（4）不必等组委会回信再准备匿名 PDF；若要 100% 确认政策措辞，可邮件 `li.li02@usc.edu`。**
- 不要在论文里声称“官方双盲”。

### A3. 模型数与 token（P0，正文 +0.08～0.15 页）——实施形式改为拆表（吸收 D-2）

- **推荐：不要用其中一个覆盖另一个。表 1 拆成两块或两列组：**
  1. **Release reports**：整合几何通过 79,301（算式与“非全量重跑”限定保留）。
  2. **Fine-tuning corpus**：396,610（356,955 / 39,655）。脚注：模型卡写作 79,322 × 5；尚未用训练清单与 79,301 对齐。**不要**把 79,322 写入 “Integrated passing models” 格。
  3. Token 保留 2,228,044,818；脚注模型卡 ~2.19B，仓库未见 `trainer_state.json`。不要用 24,448×25.3 h 替换。
  4. 正文继续用 validation，必要时脚注 “模型卡称为 test”。
- 若截稿前找到训练清单：以清单更新“训练用模型数”，同时保留 79,301 作为发布整合口径。
- 风险：“fine-tuning uses only geometrically passing models” 若与 79,322 冲突，须改成与清单一致的限定，或删掉该全称判断。

### A4. 附录中含中文的历史图（P2，默认不改图）

- **推荐：保持现状。** 截稿前不删除、不重绘。若有余力，仅在附录段首再标明 “not part of the main evaluation”。
- 若用户**明确同意**按 RB2 方案 A 移除提交 PDF 中的 image13–19：用 `\iffalse` 注释，磁盘文件保留，不以删除文件为默认。

### A5. 显著性检验（P1，须批准后才新增数字）

- **推荐：批准则只对已有 `scores.csv` 做配对检验，结果放附录，正文 1–2 句指向附录。**
- 做法：114 条 primary 对齐；对 VQA / PE / SigLIP2，BrickMore vs BrickGPT 与 vs BrickNet。可采用**符号检验 + Wilcoxon**，并对 6 次比较考虑 Holm。预先声明这是描述性补充。$P_{\mathrm{inv}}$ 在 BrickMore 与 BrickGPT 上已为 0，不必硬做。计划中**不预填 p 值**。不显著则如实写，不改“均值最高且 $P_{\mathrm{inv}}$ 打平 BrickGPT”的方向。

### A6. 空间推理评测、训练消融，以及已有诊断（默认不新做实验）

- **推荐：截稿前不做新的空间推理基准，也不做重新训练的消融。** 转换效益与 raw/retiled 称作 conversion / repair analysis，不叫 model ablation。
- **吸收的替代（P1，有条件，见 A10/A11）**：用已复算的 525 条几何诊断 + 已有 `scores.csv` 的 L1–L5 / 105 组等权 / 未截断子集。都是已有产物的再分析，须批准，且不得改写成 “spatial reasoning benchmark” 或 “improves spatial reasoning”。

### A7. PE / SigLIP2 分数定义（P0 表述，无需实验，+0.05～0.08 页）

建议替换句：

> PE is the cosine similarity between L2-normalized image and text embeddings from PE-Core-bigG-14-448. SigLIP2 is the sigmoid of the image–text logit from SigLIP2 giant-opt-patch16-384 (text length capped at 64 tokens). VQAScore is the full-vocabulary softmax probability of Yes at the first generated token.

### A8. 编译环境（P0 流程）——相对 R0 调整

- **推荐：以已经验证的 box TinyTeX（TeX Live 2026，pdfTeX 1.40.29，`latexmk -pdf`）作为主编译。** Overleaf（明确选 pdfLaTeX）与本机 MiKTeX/TeX Live 为备份。不要用 Tectonic。
- 理由：V1.5 已在 box 上成功编译；用户机器目前无 LaTeX。RB2 关于未发表稿上传与附录图导致 Overleaf 超时的提醒成立，故不再把 Overleaf 当作唯一主路径，但仍保留为应急。
- 11-16 前至少完成一次与 box 页数一致的复现编译（可用 Overleaf 或本机）。

### A9. 其它遗留

- **Reproducibility checklist**：官网未要求。**推荐默认不附**；仅当提交页出现该栏或用户要求时作为附加文件，不进 7 页正文。
- **`abstract_introduction.md`**：不作 V1.6 正文工作。

### A10. 评测权重是否即 step-79,000（新，P0 决策 / 实施为脚注）

- 评测目录标签 `92d1c595` 与 `downloads\...\model.sha256`（前缀 75f79af1…）标识体系不同，本轮**不能**确认是同一检查点。
- **推荐：请用户书面确认。** 未确认则论文只写评测使用的权重标识，不写 “all evaluated outputs are from the step-79,000 checkpoint”。

### A11. 是否把 525 条诊断写入 V1.6（新，P1，须批准）

- **推荐：批准则写入。** 这是加强 Topic 5、且不必新实验的最高性价比材料。条件：
  1. 只使用 §0.5 已复算字段；
  2. 正文一段 + **表放附录**（若页数有余且用户希望，可把极简表放正文；超页则表必须下沉）；
  3. 称 “525 prompts from the `brickmore48_eval_630` diagnostic set”；在关系说明前不写 additional / held-out；
  4. 不把该诊断写成空间推理基准或形状保真；
  5. 数字只在 §5.x（或附录）展开，摘要/引言/结论最多各一句定性指向，避免重复铺陈 8.8% 与中位数 5；
  6. 依赖 A10：未确认权重时，不把诊断结果与 “best checkpoint 79,000” 绑死。

### A12. 新增三篇相关工作（新，P1，须批准）

- 本轮已核 arXiv：MeshGPT 2311.15475（Yawar Siddiqui, Antonio Alliegro, Alexey Artemov, Tatiana Tommasi, Daniele Sirigatti, Vladislav Rosov, Angela Dai, Matthias Nießner）；LLaMA-Mesh 2411.09595（Zhengyi Wang, Jonathan Lorraine, Yikai Wang, Hang Su, Jun Zhu, Sanja Fidler, Xiaohui Zeng）；SpatialVLM 2401.12168（Boyuan Chen, Zhuo Xu, Sean Kirmani, Brian Ichter, Danny Driess, Pete Florence, Dorsa Sadigh, Leonidas Guibas, Fei Xia）。
- **推荐：批准则各用 1–2 句写入 Related Work，venue 暂只写 arXiv**（MeshGPT 的 CVPR 2024 身份若要写，须另核正式题录）。SpatialVLM 只作空间表示/空间推理文献背景，并重申本系统生成器是语言模型、VLM 仅用于评测。

---

## B. 页数预算（滚动）

起点：正文约 5.5–6.0 页。安全使用上限建议 6.6。

| 编号 | 项 | 优先级 | 预估工时 | 正文页数增量 | 预算后约 |
|---|---|---|---|---|---|
| — | 起点 | — | — | 0 | 6.00 |
| T1 | 标题（A1） | P0 | 0.3 h | 0.00–0.03 | 6.03 |
| T2 | 保持匿名 PDF（A2）+ 检索（G-2） | P0 | 0.5 h | 0 | 6.03 |
| T3 | 拆表 + 79,301 / 396,610 / token 口径（A3） | P0 | 1–2 h | +0.08–0.15 | 6.18 |
| T4 | PE / SigLIP2 / VQA 定义（A7） | P0 | 0.5 h | +0.05–0.08 | 6.26 |
| T5 | BrickGPT 协议句 | P1 | 1 h | +0.10–0.15 | 6.41 |
| T11 | 转换效益 65,503→79,298（D-1） | P1 | 0.5 h | +0.06–0.10 | 6.51 |
| T12 | 引言去重（I-2）及试验床句（I-1） | P1 | 1 h | −0.08～−0.12 与 +0.04 净约 −0.05 | 6.46 |
| T13 | Related Work 三篇短引（A12） | P1 | 1 h | +0.08–0.12 | 6.58 |
| T14 | 525 诊断：正文一段，表在附录（A11） | P1 | 2 h | +0.10–0.15 | 6.73（偏紧，见下） |
| T6 | 显著性：正文 1–2 句 + 附录表 | P1 | 2–3 h | +0.08–0.12 | 6.85（须压缩） |
| T7 | L1–L5 / 105 组 / 未截断子集（附录） | P1 | 1–2 h | 0（附录；正文至多 +0.04） | — |
| T8 | 中文历史图 | P2 | 0（默认不动） | 0 | — |
| T9 | 新空间推理基准 / 再训练 | P2 | 截止前不可行 | — | — |

T14 与 T6、T13 全部进入正文后可能超过 6.6。**执行顺序：先写入 T1–T5、T11、T12；编译量页后再决定 T13 / T14 / T6 的正文长度。** 超页时的下沉顺序：（1）T14 的表保持附录、压缩正文段；（2）移动 Figure 3 至附录或缩小；（3）T5 细节下沉附录；（4）T6 只留一句。禁止移动或改排 Algorithm 1，禁止删主表。

---

## C. 分节修订计划（按 V1.5 结构）

未列出的段落默认保持不动。

### C0. 导言区（L1–36）

**C0.1 标题** — 见 A1。P0。

**C0.2 作者块** — 见 A2。P0。投稿前检索：作者名、单位、`D:\`、个人主页、HuggingFace / GitHub，以及 **Kyle308666、BuShiGeMenn**。

**C0.3 模板行** — 不改 `aaai2027.sty` / `.bst`，不引入 `hyperref`。

### C1. Abstract（L38–42）

**C1.1** 现有 Topic 5 框句默认不改核心主张，不加入 RL/预训练/VLM。

**C1.2** 摘要**维持数字现状**（79,301 + 400,000 records；不写 79,322；不把 525 全表写进摘要）。若 A11 批准，最多加半句定性（例如 diagnostic checks of stud-connectivity after generation），**不写 8.8% 或中位数 5**。

**C1.3** “110 retiled, 4 raw” 与三项最高分、$P_{\mathrm{inv}}=0.00\%$ **不要改数字或结论句。**

### C2. Introduction（L49–69）

**C2.1** “geometric reasoning and object assembly” 为更早 Topic 2 框句，保留、不再增强。

**C2.2（P1，I-1）** 在问题段后加一句：积木程序在离散网格上给出可精确检查的空间表示（钉柱连通、部件计数、与体素的界内并集），因此可作语言建模下空间表示学习的试验床。不要写成已做空间推理基准。

**C2.3（P1，I-2）** 压缩引言中与 §3 重复的 80,000 / 79,301 / 400,000 展开。若删除 “The output does not include color…”，必须在 §4.1 补上等价句（V1.5 §4.1 目前无此句）。

**C2.4 贡献列表** — 贡献 1 保持 79,301 为几何通过。若 A11 批准，贡献 3 可加半句指向生成后几何诊断（定性，不堆数字）。未批准则不动贡献 3 后半。

### C3. Figure 1 / Figure 2

P2：不动图。超页时优先考虑移动 **Figure 3**（见 B），不是 Figure 1/2，也不是 Algorithm 1。

### C4. Related Work（L77–85）

**C4.1** Brick-by-Brick 的 RL 保持第三者表述。

**C4.2（P1，A12）** 在积木生成或语言–3D 段加入已核验的 MeshGPT、LLaMA-Mesh；另用 1 句提 SpatialVLM 作为空间表示背景，并立即限定“本文生成器不是 VLM”。作者名单必须完整。不新增未经核验的条目。

### C5. Dataset Construction（L87–126）

**C5.1–C5.2** 数字不动。

**C5.3 §3.3 + 表 1 — P0，见 A3（拆表）。** 建议表注仍用 R0 的两口径说明（不出现本地路径）。

**C5.4（P1，D-1）** 在重铺段加 2–3 句：同一 80,000 源在 relaxed 几何检查下通过 65,503，经 retile 后几何通过 79,298（恢复 13,795）；`summary.json` 记录增加 228,582、删除 125 个体素，其中 31,532 个通过模型体素集合未变。必须写明这是 **relaxed→retile 的发布统计**，不要写成 65,503→79,301。附录可补充 relaxed 体素改动 428,278 / 38,230（`assembly_summary.json`）。

### C6. Model：Fine-Tuning（L127–156）

数字不动。validation 脚注见 A3。若 A10 未确认，不要把评测段与 step-79,000 强制等同。

### C7. Figure 3

图注与 110+4 一致，默认不动。超页时可移至附录并在正文留引用。

### C8. Inference and Retiling + Algorithm 1（L165–200）

**P0：Algorithm 1 必须留在正文。** 不改算法逻辑、种子 (42, 104, 2026)、超时阶梯 (12, 60, 180) 或 600 s 仅属 recovery 的说明。不以 `figure*` 改排作为兜底。

### C9. Comparative Evaluation（L202–257）

**C9.1 §5.1 Setup — P0 + P1。**

- P0（A7）：按 §0.3 / A7 改定义。
- P1：BrickGPT 协议句（world_dim=20，max_bricks=200，seed 42，日志中 66/114 stable）。不要把 66/114 解释成 BrickGPT 官方测试集稳定率。
- P2（E-7）：统一 VQAScore 用语与 P_inv 小数位。

**C9.2 主表数字锁定**：BrickMore 0.00% / 0.2176 / 0.1856 / 0.1231；BrickGPT 0.00% / 0.1401 / 0.1457 / 0.0297；BrickNet 21.99% / 0.0624 / 0.1302 / 0.0100；91/95/91；零件 413.0 / 152.3 / 23.3。若 A5 批准，将 “no significance test is reported” 改为指向附录，避免自相矛盾。若检验与方向冲突，先停下来向用户汇报，不得自行改结论。

**C9.3 raw vs retiled 表** — 数字不动。

**C9.4 Boundaries** — 保持非空间推理基准的限定；可加半句两种分数尺度不同（余弦 vs sigmoid）。

**C9.5（P1，A11）新小节或段「Generation-time geometric diagnostics」。** 建议稿（数字均来自 §0.5 复算；表本身放附录）：

> We also inspected 525 BrickMore generations from the `brickmore48_eval_630` diagnostic set. Raw decoder outputs were stud-connected in 46 cases (8.8\%); after the same retile procedure used in the main pipeline, all 525 assemblies were stud-connected. Among the 479 raw failures, the median number of stud-connected components was 5 (range 2--33). The MILP exact-cover solver was not required for the 46 already-connected outputs; 326 / 133 / 18 / 2 cases finished within the 12 s / 60 s / 180 s / 600 s tiers. These checks evaluate stud connectivity and in-bounds voxel-union consistency, not prompt-level shape fidelity or spatial reasoning.

禁止使用 README 中未复算数字；禁止在统计 `raw_report.json` 的 `voxel_components` 之前写 “voxel-connected in most cases”。

### C10. Limitations and Conclusion（L259–268）

**C10.1 Scope 句锁定。** 不要削弱。若增加未来工作，connectivity-based rewards 必须写成 outside the scope of this work，且不出现在摘要或贡献。

**C10.2 Data accounting** 与 §3.3 同一口径。

**C10.3 Conclusion** 不改核心结论。若 A11 批准，最多一句指向诊断，不重复全表。

### C11. References

仅新增 A12 已核验的三条（作者名单完整，venue 暂 arXiv）。编译后检查有无 `?`。

### C12. Appendices

**C12.1 附录 A 历史图** — 见 A4，默认不动。

**C12.2 附录 B** — BrickGPT 配方表数字锁定。Token 脚注过长可放这里。

**C12.3 附录 C（评测）** — 若批准，增加：（1）525 诊断表（solver tiers、raw vs retiled 连通、失败组分位数；并注明 `shape_preserved`＝界内体素并集）；（2）配对检验表（不预填 p）；（3）L1–L5 与可选的 105 组等权、未截断子集（标明补充口径，不替代主表）。正文只交叉引用。

**C12.4 附录 D 历史表** — 不动。

---

## D. 哪些需要新实验 / 新数据（及截止前是否可行）

| 想法 | 是否新实验 | 现有产物是否足够 | 截止前可行性 | 计划建议 |
|---|---|---|---|---|
| 改 PE/SigLIP2/VQA 文字定义 | 否 | 是，评测脚本已读 | 高 | 做（P0） |
| 79,301 vs 79,322 拆表说明 | 否 | 部分：缺训练清单 | 高 | 做说明；不臆造 79,322 来源 |
| 精确 token 复核 | 否（找日志） | 当前未找到日志 | 不确定 | 保留 2,228,044,818 + 脚注 |
| 转换效益 65,503→79,298 | 否 | 是，两份 summary 已读 | 高 | 做（P1） |
| 525 条几何诊断 | 否（已有产物） | 是，已复算可写字段 | 高 | 用户批准后做（P1）；表默认附录 |
| 配对显著性检验 | 否（新分析，有新数字） | 是，`scores.csv` | 高 | 批准后做，放附录 |
| L1–L5 / 105 组 / 未截断子集 | 否（新分析） | 是，分析文档 + csv | 高 | 批准后放附录；写入前再算一遍 |
| 写入 BrickGPT world_dim / 66 stable | 否 | 是，溯源 jsonl | 高 | 做（P1） |
| 确认评测权重＝step 79,000 | 否（需用户/哈希） | **尚未对齐** | 取决于用户 | 未确认则不写等同 |
| 空间推理新基准 | 是 | 否 | **低** | 不做 |
| 再训练 / 数据规模消融 | 是 | 否 | **低** | 不做 |
| 重绘中文图、补物理实验 | 是 | 否 | 低 | 默认不做 |

---

## E. 日程（UTC+8，含缓冲、编译、匿名、投稿）

假设用户在 **11-15 当天或 11-16 上午** 回复 §A（含新增 A10–A12）。若决策推迟，压缩 T6/T7/T13，优先 T3/T4/T5/T11 与编译投稿。

| 时段 | 工作 | 产出 |
|---|---|---|
| **11-15 上午–下午** | 用户圈定 A1–A12。全体作者注册 OpenReview profile。确认主编译（box TinyTeX）与备份路径。 | 决策清单；已注册 profile |
| **11-15 晚 / 11-16 上午** | 实施 P0：标题（若定稿）、PE/SigLIP2/VQA 定义、表 1 拆表与口径、匿名检索（含新用户名）。第一次 `latexmk -pdf`。 | V1.6 初稿 PDF |
| **11-16** | 若批准：D-1 转换句、引言去重与试验床句、BrickGPT 协议句；从已有文件起草 525 表、检验与分层附录。二次编译量页。 | V1.6-pre PDF |
| **11-17** | 写入批准的 A11/A12/A5；控制在 6.6 页。通读英文与 Scope 句。第三次编译：letter、无 Type 3、无未定义引用、第 7 页后无正文。 | 接近定稿 |
| **11-18（缓冲日）** | 冻结内容（除作者表单）。匿名清单。用备份编译器复现一版并对页。准备 OpenReview：profile、title/abstract/keywords/TL;DR（避免 79k）、Long Paper、PDF（<50 MB）、CC BY 4.0。 | 提交包 |
| **11-19 上午–下午（实际上传日）** | 最终再编一次。提交并自行下载 PDF 核对。不要拖到 11-20 晚上。 | 已提交 |
| **11-20 12:00 前（应急）** | 仅系统故障或明显错别字（视系统是否仍开放）。截止为 11-20 19:59 UTC+8，不依赖最后一小时。 | 应急 |

每次编译检查：`latexmk -pdf` 退出码 0；无 undefined references；`pdfinfo` 为 letter；**结论在第 7 页结束或更早**（References 可从第 8 页起）；`pdffonts` 无 Type 3；首页 Anonymous submission。

---

## F. 按优先级汇总（实施清单）

### P0（截稿前必须处理或明确维持）

1. 用户确定标题（A1）；确定后改 `\title`。
2. PDF 保持匿名；作者只进 OpenReview；全体作者注册 profile（A2）。
3. 拆表分开写 79,301 与 396,610；注明模型卡 79,322，不擅自改表（A3）。
4. Token 保留 2,228,044,818，脚注 ~2.19B 与日志缺失（A3）。
5. 按代码修正 PE（余弦）、SigLIP2（logit 的 sigmoid）与 VQAScore（全词表 softmax）定义（A7）。
6. Algorithm 1 留在正文。
7. 不改主表已核对数字，不改结论方向，不宣称 RL/预训练/VLM。
8. pdfTeX 编译通过；匿名检索含 Kyle308666 / BuShiGeMenn；box TinyTeX 主编译（A8、日程 E）。
9. 用户确认或搁置评测权重与 step-79,000 的关系（A10）。

### P1（建议做，需部分批准）

10. §5.1 补充 BrickGPT `world_dim=20`、`max_bricks=200`、seed 42、生成日志 66/114 stable。
11. 转换效益 65,503→79,298（及已复核的体素改动），与 79,301 分口径。
12. 若批准：525 诊断正文一段 + 附录表（A11 全部条件）。
13. 若批准：`scores.csv` 配对检验（符号检验 + Wilcoxon，可选 Holm），附录出表。
14. 若批准：L1–L5、105 组等权、未截断子集附录表（写入前重算）。
15. 引言去重；颜色句移到 §4.1；试验床框句。
16. 若批准：MeshGPT / LLaMA-Mesh / SpatialVLM 短引（完整作者，venue 暂 arXiv）。
17. validation vs test 脚注。

### P2（建议不做或仅文档）

18. 默认不重绘/删除中文历史图（仅当用户明确同意时按注释方案处理）。
19. 新建空间推理评测或再训练消融。
20. 更新仓库根目录 `abstract_introduction.md`。
21. 统一 VQAScore 用语与 P_inv 小数位；Underfull；checklist 仅当提交页要求。

---

## G. 风险总表（横切）

- **超页**：T13+T14+T6 同时进正文可能把结论推出第 7 页。对策：诊断表默认附录；超页先压诊断段、再移 Figure 3；每次编译量页；不改 Algorithm 1。
- **口径冲突**：79,301 与 396,610 被误乘；65,503→79,298 被写成 79,301。对策：拆表；转换句只引用 retile 发布数。
- **诊断被写成过强结论**：additional / 形状保真 / 空间推理基准。对策：A11 条件；数字不在摘要重复。
- **权重未对齐**：把 525 条或主评测绑到 step-79,000。对策：A10。
- **匿名失败**：对策：11-18 清单，含新用户名；保持 `[submission]`。
- **把分析写成新实验**：须写数据来源，避免 “we conducted a new evaluation”。
- **编译器错误**：不用 Tectonic；主编译 box TinyTeX，Overleaf/MiKTeX 备份。
- **截止风险**：以 11-19（UTC+8）提交为目标，11-20 仅应急；profile 须在 11-15 启动。
