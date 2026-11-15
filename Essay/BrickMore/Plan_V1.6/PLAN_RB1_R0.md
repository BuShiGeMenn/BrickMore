# BrickMore V1.6 修订计划（ReviewBot1，R0）

- 计划文件：`D:\BrickMore\Essay\BrickMore\Plan_V1.6\PLAN_RB1_R0.md`
- 基稿：`D:\BrickMore\Essay\BrickMore\V1.5\main.tex`（2026-11-14 23:36 UTC+8）及 `V1.5\REVIEW_V1.5.md`；并参考 `REVIEW_V1.4.md`、`REVIEW_V1.3.md` 与项目 `D:\BrickMore`。
- **本文件只做规划。未修改任何版本文件夹中的论文源文件。** 未读取 `Plan_V1.6` 下任何 `PLAN_RB2_*.md`。
- 目标venue：[GSR-VLM](https://gsr-vlm.org/)（AAAI-27 workshop，非存档）。**仅对齐 Topic 5**（Learning spatial representations: pretraining, fine-tuning, RL, and data generation）。不考虑 Topic 2。
- 硬约束：官方 AAAI-27 模板；长文**正文 ≤ 7 页**（参考文献与附录不限）；Algorithm 1 必须留在正文；不虚构数字或文献；不宣称做过预训练、强化学习，或把生成器称为 VLM。
- 截止：官网 Submission deadline **2026-11-19 AoE（UTC−12）** ＝ **2026-11-20 19:59（UTC+8）**。本计划撰写时约为 2026-11-15 00:40（UTC+8），剩余约 **5 天 19 小时**。通知日 2026-12-01 AoE。投稿：OpenReview [AAAI.org/2027/Workshop/GSR-VLM](https://openreview.net/group?id=AAAI.org/2027/Workshop/GSR-VLM)。页脚仍写 “Proposed AAAI-27 workshop · Details subject to confirmation”。
- 当前页数（V1.5 `main.pdf`，pdfTeX 编译，2026-11-14 23:37 UTC+8）：**共 16 页**；正文（摘要→结论）在**第 6 页左栏**结束；References 从第 6 页左栏下部起；附录约第 7–16 页。相对 7 页上限，正文约有 **1.0–1.5 页余量**。为防浮动体把结论推到第 7 页之后，建议本轮正文净增控制在 **≤ 0.6 页**，新表优先放附录。

文中凡给出数字，均注明出处（已读文件或 V1.5 正文）。拟议新文献若未在本轮核验，标「需查证」。本计划不提出必须新增的文献。

---

## 0. 本轮重新核查的证据（供决策引用）

### 0.1 GSR-VLM 政策与双盲（2026-11-15 再次读取）

- 官网 https://gsr-vlm.org/：**仍然没有出现** anonymous / double-blind / review policy / reproducibility checklist 等字样。明确写出的是：非存档；长文 7 页正文、参考文献与附录不限；必须使用 [AAAI-27 模板](https://aaai.org/authorkit27/)；OpenReview 投稿；日期同上。
- OpenReview 邀请 `AAAI.org/2027/Workshop/GSR-VLM/-/Submission`（本轮 API 读取）：
  - 投稿表有 `authors` 字段，且该字段的 `readers` 仅限 `AAAI.org/2027/Workshop/GSR-VLM` 与 `.../Submission{number}/Authors`（作者姓名对默认读者受限，属于典型的匿名审稿配置）。
  - `pdf` 字段同样限制 readers。
  - `data_release` 选项写明：录用后、会议结束后才向公众公布投稿与作者名。
  - 官网组委会联系邮箱出现在 OpenReview 组资料中：`li.li02@usc.edu`（Shawn Li）。**官网正文仍未用文字宣布 “double-blind”。**
- **建议（见 §A）：PDF 继续使用 `\usepackage[submission]{aaai2027}`，不要把作者写进 PDF；作者只填 OpenReview 表单。若仍不放心，可在投稿前向组委会确认一句。**

### 0.2 79,301 vs 79,322，以及 token 数

| 数字 | 出处 | 含义 |
|---|---|---|
| 79,301 | `D:\BrickMore\Train\datasets\CURRENT_DATASET_STATUS.md`；`D:\BrickMore\Train\README.md`；V1.5 表 1 与 §3.3 | **整合口径的几何通过数**：79,298 − 1,902 + 1,905 = 79,301。文档写明这是两份发布报告的计算，**不是**重新跑全量验证；且“当前统计本身不证明某次训练已经使用替换数据”。 |
| 79,298、1,902、1,905、699 未通过 | 同上；V1.5 L97、表 1 | 全量重铺通过 79,298；B 批钢琴旧 1,902 / 新 1,905；整合未通过 699（80,000−79,301）。与论文一致。 |
| 79,322 × 5 = 396,610 | **仅见** `D:\BrickMore\downloads\BrickGPT-Qwen3-1.7B-BrickMore-48\README.md`（模型卡） | 写的是训练用模型数 × 5 条描述 = 396,610 samples（356,955 train / 39,655 test，按模型 9:1，seed 42）。算术成立。 |
| 396,610 与 356,955 / 39,655 | 模型卡 **与** V1.5 表 1 | 两边一致。论文称小份为 validation，模型卡称 test。 |
| 79,301 × 5 = 396,505（差 105） | 由上两行推出（V1.5 注释已写） | 105 / 5 = 21，**只是算术**，本轮**没有**找到 21 个额外模型或额外描述的清单，不能把“21 个模型”写成事实。 |
| 2,228,044,818 tokens | **只出现在 V1.5 表 1（L115）及注释** | 本轮在 `D:\BrickMore` 下**未找到** `trainer_state.json`、`build_stats.json`、`train_brickmore.log`。模型卡声称 “full training log history is in `trainer_state.json`”，但当前下载目录 `D:\BrickMore\downloads\BrickGPT-Qwen3-1.7B-BrickMore-48\` **没有**该文件（仅有权重、tokenizer 与 README）。 |
| ~2.19B tokens | 同一模型卡，Hardware 条 | 约数，与 2.228B 量级接近但不相同。 |
| 24,448 tokens/s，25.3 h | V1.5 附录 B（L333）与表 `tab:finetune-config` / 配方表 | 一致性验算（**不是新的论文数字**）：24,448 × 25.3 × 3,600 = 2,226,723,840，与 2,228,044,818 相差 1,320,978。若 25.3 为四舍五入，可以解释缺口，但不能代替原始日志。 |

jsonl / `vocab.json` 中出现的 “79322” 为 SHA256 或词表 id 的偶然子串，**不是**模型数证据。

### 0.3 PE / SigLIP2 / VQAScore 在代码里怎么算

主评测脚本（两份逻辑一致，仅 VQA processor 序列化细节不同）：

- `D:\BrickMore\Evaluation\pipeline\evaluate_paper_images.py`
- `D:\BrickMore\Deploy\build\comparison_20261110\BrickMoreComparison\Scripts\evaluate_paper_images.py`

（下列行号依 `Evaluation\pipeline\evaluate_paper_images.py`。）

- **VQAScore**（L34–36、L81–83）：对 “Yes” 词 id 做**全词表 softmax 概率**（注释写明不是 Yes/No 二元归一化）。
- **SigLIP2**（L89–99）：`model(**inputs).logits_per_image[:,0].float().sigmoid()` —— **对 image–text logit 做 sigmoid**，得到类似概率的分数，**不是**余弦相似度。文本 `max_length=64`，可截断。
- **PE**（L102–126）：`encode_image(..., normalize=True)` 与 `encode_text(..., normalize=True)`，再 `F.normalize` 后计算 `(a @ b.T)[:,0]` —— **L2 归一化后的点积，即余弦相似度**，**没有**再过 sigmoid。

论文 §5.1 目前把 PE 与 SigLIP2 统称为 “image–text matching scores”，不够精确。此项**不必做新实验**，只改表述。

### 0.4 已有 per-prompt 分数（显著性 / 分层分析可行性）

文件存在且可用：

`D:\BrickMore\Results\three_model_comparison_20261111\intake\Results\comparison_full\report\scores.csv`

- 462 行；列：`sample_id, system, model_id, variant, category, level, batch, prompt_id, primary, part_count, caption, pinv, invalid_placements, structure_status, vqa, pe, siglip2`。
- 三系统 **primary=True 各 114 条**（与主表一致）。BrickMore 主输出：stitched 110 + raw 4。level 与 category 字段齐全（21 类；各 level 条数 21/21/23/25/24）。
- 因此：**配对 Wilcoxon / 符号检验 / bootstrap 置信区间**，以及按 L1–L5 或类别的描述性分层，都可在**不重新生成、不重新打分**的前提下完成。这会**新增数字**，必须先「待用户确认」。
- 本计划**不计算、不写入任何 p 值或新均值**。

BrickGPT 生成限制可从已有溯源文件直接引用（不必重跑）：

`D:\BrickMore\Deploy\build\comparison_20261110\BrickMoreComparison\Provenance\brickgpt_generation_summary.jsonl`

本轮读取：114 条记录全部 `world_dim=20`、`max_bricks=200`、`seed=42`；`stable` 为 True 66 / False 48。

---

## A. 「待用户确认」项：推荐选项与理由

### A1. 标题（P0 决策，实施约 15 分钟，页数影响 ≈ 0～+2 行）

- 现状：`\title{BrickMore}`（L23）。AAAI 要求描述性 mixed-case 标题（V1.4 N21）。
- **推荐：改为描述性标题，但须用户圈定最终用词后再改。** Topic 5 导向的推荐候选（不引入新主张）：
  - *BrickMore: Learning Spatial Brick Assemblies by Agentic Data Generation and Language-Model Fine-Tuning*
  - 备选（V1.4 曾拟，偏装配而非 “representation”）：*BrickMore: Learning Stud-Connected Brick Assembly from Agentically Generated Voxel Data*
- 理由：单词汇标题在工作坊审稿中偏弱；推荐第一案直接点出 data generation + fine-tuning，避免 “reasoning / VLM / RL” 等本文没有实验的词。
- 风险：改标题不改结论，但需同步 OpenReview 的 title 字段；不要在标题里写 “improves spatial reasoning”。

### A2. 作者信息与是否双盲（P0 决策）

- 现状：`[submission]` 模式；PDF 首页为 “Anonymous submission”；源码作者为占位符。按用户要求本轮计划也**不擅自填作者**。
- **推荐：（1）PDF 保持匿名模板，直到相机就绪或组委会明确要求实名；（2）作者姓名只进入 OpenReview 表单（该表已限制 authors 字段读者）；（3）官网未写 “double-blind” 四字，若要 100% 确认，可在 11-15 或 11-16 用一封短邮件问组委会（OpenReview 组资料中的联系人为 li.li02@usc.edu），但不等确认也可以先按匿名 PDF 准备。**
- 理由：OpenReview 对 authors 的 readers 限制与 “录用后才公开作者名” 的选项，强烈暗示审稿阶段应对审稿人隐藏身份。把姓名写进 PDF 的风险高于继续匿名。
- 风险：若工作坊其实是单盲且要求 PDF 实名，再出一版相机就绪式稿即可；反向操作（先实名再撤回）更被动。所有作者须预先注册 OpenReview profile（表单说明原文）。

### A3. 模型数 79,301 vs 79,322；token 2.228B vs ~2.19B（P0 决策，正文 +0.1～0.15 页）

- **推荐：不要用其中一个悄悄覆盖另一个。** 建议在表 1 注或 §3.3 用两句把**两种口径分开**：
  1. **几何通过的整合口径**仍写 79,301，并保留已有算式与 “非全量重跑” 的限定（有 `CURRENT_DATASET_STATUS.md` 支撑）。
  2. **训练样本**仍写 396,610（356,955 / 39,655），因为论文与模型卡一致。
  3. 加一句：一份已发布的模型卡将这 396,610 条写成 79,322 models × 5 captions；该计数与 79,301 的整合几何通过数尚未用训练清单对齐。**不要**把 79,322 写进表的 “Integrated passing models” 格。
  4. Token：保留 2,228,044,818，脚注写模型卡作 ~2.19B，且本仓库未见 `trainer_state.json`，故精确值待日志复核；**不要**用 24,448×25.3h 的验算结果替换表中数字。
  5. 小份名称：建议正文继续用 validation（与 `load_best_model_at_end` 一致），必要时脚注 “模型卡称为 test”。
- 若用户能在截稿前找到真正的训练清单或 `trainer_state.json`：以清单为准更新“训练用模型数”，同时保留 79,301 作为发布整合口径。本轮检索**尚未找到**该文件。
- 风险：只报 79,301 却用 396,610，会被审稿人自己乘出来；只报 79,322 则与数据集文档冲突。分开写最稳妥。

### A4. 附录中含中文的历史图（P2，默认不改图）

- **推荐：保持现状（留在附录，图注已说明中文标注与 “require verification”）。截稿前不删除、不重绘。**
- 理由：用户已禁止未经确认的删除/重绘；重绘英文版费时且易引入标注错误；附录不占 7 页正文。审稿人可以忽略历史图，不影响 Topic 5 主论证。
- 风险：个别审稿人反感中文图。若有余力，仅可考虑在附录段首再加一句 “not part of the main evaluation”（现已有类似说明）。

### A5. 显著性检验（P1，需批准后才会新增数字）

- **推荐：批准的话，只对已有 `scores.csv` 做配对检验，结果放附录，正文用 1–2 句指向附录；不重跑模型。**
- 做法（批准后才执行，本计划不给出结果）：筛选三系统 `primary=True` 的 114 条，按 `prompt_id`（或 category+level+caption）对齐；对 VQA / PE / SigLIP2 做 BrickMore vs BrickGPT、BrickMore vs BrickNet 的 Wilcoxon 符号秩检验或配对 bootstrap 95% CI；预先声明这是描述性补充，不是预注册多重比较校正后的最终推断。$P_{\mathrm{inv}}$ 在 BrickMore 与 BrickGPT 上已均为 0，检验无区分度，不必硬做。
- 不可行 / 不建议：新的空间推理基准、新的训练消融（见 A6）。
- 风险：补了 p 值会改变“有数字的结果段落”的观感，但不应改结论句的方向性措辞（仍是 “highest means … matching on $P_{\mathrm{inv}}$”）。务必先批准再写入。

### A6. 空间推理评测与训练消融（默认不做，P2）

- **推荐：截稿前不做新的空间推理基准，也不做重新训练的消融。**
- 理由：生成器是文本 LM，现有指标已在 §5.4 / Limitations 中被正确限定为文本–图像对齐而非空间推理基准。从零设计空间关系问答或装配规划评测，5 天内无法可靠完成，也容易虚构协议。完整消融（不同数据规模、有无重铺监督、有无五级描述）需要重新训练，现有产物中**没有**第二套训练权重可对比。
- **可行的替代（若用户要“加强 Topic 5 而不新训”）**：用同一份 `scores.csv` 做 **L1–L5 分层均值**（已有 `level` 列），放附录，说明多粒度描述下的对齐是否稳定。这是分析不是新实验，但仍是新数字，需批准。
- 风险：把现有分数改写成 “improves spatial reasoning” 会被审稿人抓住。保持现行 Scope 句。

### A7. PE / SigLIP2 分数定义（P0 表述修订，无需实验，+0.05～0.08 页）

- **推荐：按代码改一句，不必再等确认实验，但建议用户点头后改稿（属于精度修正，不改数字）。**
- 建议替换 §5.1 中 “PE and SigLIP2 are image–text matching scores from …” 为（仅用代码已实现的定义，不发明公式编号以外的新量）：

> PE is the cosine similarity between L2-normalized image and text embeddings from PE-Core-bigG-14-448. SigLIP2 is the sigmoid of the image–text logit from SigLIP2 giant-opt-patch16-384 (text length capped at 64 tokens).

- 出处：`evaluate_paper_images.py` L99 与 L122–126（见 §0.3）。
- 风险：几乎无；可能使两种分数的数值尺度不可比这一点更明显（这是好事，正文已劝不要与他文比）。

### A8. 编译环境：MiKTeX vs Overleaf（P0 流程，不改论文）

- **推荐：以 Overleaf（编译器选 pdfLaTeX）作为投稿前的主路径；若本机要装，用 MiKTeX 或 TeX Live，命令为 `latexmk -pdf`。不要用 Tectonic。**
- 理由：`aaai2027.sty` 要求 pdfTeX；用户机器目前无 LaTeX；V1.5 已在 box 的 TinyTeX（TeX Live 2026，pdfTeX 1.40.29）上成功编译。Overleaf 不依赖本机安装，便于作者共同检查。MiKTeX 适合希望本地迭代的人，但要预留安装与宏包下载时间。
- 风险：临近截止才安装 MiKTeX 可能因宏包/字体出错。11-16 前应完成至少一次与 box 结果一致的编译。

### A9. 其它遗留确认（并入计划，不必单独开实验）

- **Reproducibility checklist**（V1.4 N23）：官网未要求。**推荐：若 Author Kit 的 checklist 填写成本低，可作为 OpenReview 附加文件；不写入 7 页正文。** 不填也不应被桌拒（官网未列）。需查证最终提交页是否出现该字段。
- **BrickGPT 生成限制与 105 组等权**（V1.3 #13 剩余）：**推荐写协议句（P1），等权口径若要写进正文会新增数字，优先放附录或先不做。** 溯源文件已有 world_dim=20 / max_bricks=200 / stable 66/114（见 §0.4）。
- **`abstract_introduction.md`**：仍过时且不在 V1.5 内。**推荐作废或在截稿后同步，不纳入 V1.6 正文工作。**

---

## B. 页数预算（滚动）

起点：正文约 5.5–6.0 页（结论在第 6 页左栏）。上限 7.0。安全使用上限建议 6.6。

| 编号 | 项 | 优先级 | 预估工时 | 正文页数增量 | 预算后约 |
|---|---|---|---|---|---|
| — | 起点 | — | — | 0 | 6.00 |
| T1 | 标题（A1） | P0 | 0.3 h | 0.00–0.03 | 6.03 |
| T2 | 保持匿名 PDF（A2） | P0 | 0.2 h | 0 | 6.03 |
| T3 | 79,301 / 79,322 与 token 口径说明（A3） | P0 | 1–2 h | +0.10–0.15 | 6.18 |
| T4 | PE / SigLIP2 定义（A7） | P0 | 0.5 h | +0.05–0.08 | 6.26 |
| T5 | BrickGPT 协议句（world_dim 等） | P1 | 1 h | +0.12–0.18 | 6.44 |
| T6 | 显著性检验：正文 1–2 句 + 附录表 | P1 | 2–3 h（含计算与反复编译） | +0.08–0.12（表在附录） | 6.56 |
| T7 | L1–L5 分层（可选，附录） | P1/P2 | 1–2 h | 0（附录） | 6.56 |
| T8 | 中文历史图 | P2 | 0（推荐不动） | 0 | 6.56 |
| T9 | 空间推理新基准 / 再训练消融 | P2 | 不可行于截止前 | — | — |
| T10 | Underfull 微调、匿名注释已在 V1.5 处理 | P2 | 0.5 h（可选） | ≈0 | 6.56 |

即使 T1–T6 全做，预计仍 ≤ 6.6 页，低于 7。若编译后结论越过第 7 页，**先把 T6 的数字表和 T5 的细节下沉附录**，不要删 Algorithm 1，不要删主表。

---

## C. 分节修订计划（按 V1.5 结构）

下列每项给出位置、改什么、为什么、怎么改、优先级、工时、页数、风险。未列出的段落默认**保持不动**。

### C0. 导言区（L1–36）

**C0.1 标题（L23）** — 见 A1。P0。须用户选定字符串后再改。`\title{...}` 一处 + PDF 页眉。风险：与 OpenReview 标题不一致。

**C0.2 作者块（L24–32）** — 见 A2。P0。在 `[submission]` 下 PDF 已显示 Anonymous submission，**不要**在截稿稿把占位符换成真名，除非组委会要求实名 PDF。风险：源码里若恢复真实邮箱/单位且不慎关掉 `[submission]`，会泄密。投稿前检索源码与 PDF：作者名、单位、`D:\`、个人主页、HuggingFace 用户名等。

**C0.3 模板行** — 不改 `aaai2027.sty` / `.bst`，不引入 `hyperref`。P0 维持。

### C1. Abstract（L38–42，一段）

**C1.1 现有框架句已对齐 Topic 5**（“learn and constrain a spatial representation…”；agentic batch generation + fine-tuning + repair）。**默认不改核心主张，不加入 RL/预训练/VLM。**

**C1.2 可选（仅当 A3 批准）**：在 “79,301 models pass the specified geometric checks” 之后不把 79,322 写进摘要。摘要继续用 79,301 + 400,000 records；训练样本量 396,610 若要出现，须避免读者直接乘 79,301×5。更稳：摘要维持现状，细节放 §3.3。页数 0。P1，倾向**摘要不动数字**。

**C1.3** “110 retiled, 4 raw” 与三项最高分、$P_{\mathrm{inv}}=0.00\%$ 已与 `scores.csv` 主输出一致，**不要改数字或结论句。**

### C2. Introduction（L49–69）

**C2.1 第 1 段（L50）** 含 “geometric reasoning and object assembly”。这是更早一轮 Topic 2 框句，按当时指示保留、本轮**不再增强 Topic 2**。P2：不动。

**C2.2 第 2 段（L52，BrickGPT/BrickNet 引用）** — 已有 `\cite`，不动。

**C2.3 第 3–5 段（问题、数据、微调+约束）** — Topic 5 机制句已在（$48^3$、多级描述、固定序列化、exact-cover）。P2：不动，除非标题改了需在贡献里用同一套词。

**C2.4 贡献列表（L63–67）** — 数字与 V1.5 一致。若 A3 批准，贡献 1 保持 79,301 为几何通过，不要改成 79,322。P0/P1 仅在用户要求时加半句 “these layouts supply the fine-tuning corpus of 396,610 English caption–sequence pairs”（数字已在表 1）。页数 +0.03。风险：与 79,301 并列时仍需在后文解释。

### C3. Figure 1 / Figure 2（L43–46，L70–75）

- 图源已在 V1.3 改为 Agentic 标题，V1.4/V1.5 沿用。P2：不动。
- 不要为了 Topic 5 重绘图（工期与风险都不划算）。

### C4. Related Work（L77–85）

**C4.1** 三段结构已覆盖积木生成、稳定性、程序化数据 + LoRA。Brick-by-Brick 的 RL 是**他人工作**，可保留，避免读成“我们也做了 RL”。P2：不动，或至多在提及 RL 的句子保持 “…has been studied as … deep reinforcement learning [brickbybrick]” 这种第三者表述（现已是）。

**C4.2** 不新增文献，除非用户指定且提供已核验的 arXiv。现有 `references.bib` 条目此前已核验过，本轮不再扩写。

### C5. Dataset Construction（L87–126）

**C5.1 §3.1（L89–90）** — 80,000、21 类、3,805–3,810、五级双语、无重复哈希：来自既有项目文件（V1.4 N19），不动数字。P2：可删 L91 多余空行（无页数影响）。

**C5.2 §3.2（L93–94）** — 六邻接 vs 多组件接地 vs 钉柱连通的区分已写清。不动。

**C5.3 §3.3 + 表 1（L96–126）— P0 核心修订，见 A3。**

位置：L97 段末、表 1 L113–115、L121–125 注释。

建议表注（数字均已出现在论文或模型卡，不新造）：

> The integrated geometric-pass count (79,301) is computed from two versioned release reports as $79{,}298-1{,}902+1{,}905$ and is not a new full-dataset verification (`CURRENT_DATASET_STATUS.md` 的事实改用论文体，不出现本地路径). The fine-tuning sample count 396,610 (356,955 / 39,655, split by model) is the corpus used in training. A released model card describes this corpus as 79,322 models $\times$ 5 captions; that model count has not been reconciled with the 79,301 integrated pass count. The token total 2,228,044,818 is retained from the training report used in this manuscript; the same model card lists approximately 2.19B tokens, and the raw trainer log was not available in the project tree at the time of writing.

同时删除或改写会暴露 `D:\` 的注释（V1.5 已去掉绝对路径，保持）。

工时 1–2 h；正文 +0.10–0.15 页；风险见 A3。

### C6. Model：Fine-Tuning（L127–156）

**C6.1 L131–135** — 20 种积木、Y-first、Qwen3 LoRA 超参、best checkpoint 79,000 / 0.0308：与模型卡及既有训练叙述一致，**不动数字**。

**C6.2** 模型卡称小份为 test，正文为 validation。建议在首次出现 “validation” 处加极短脚注（A3.5）。+0.02 页。P1。

**C6.3 表 `tab:finetune-config`** — 不动。与附录配方表的交叉引用已通。

### C7. Figure 3 生成拼图（L158–163）

图注已写明 “one chair is raw … 4 of the 114 … are raw”。与 `scores.csv` 主输出 110 stitched + 4 raw 一致。P2：不动。

### C8. Inference and Retiling + Algorithm 1（L165–200）

**P0 约束：Algorithm 1 必须留在正文，禁止移到附录或删除。** 本轮不改算法逻辑、种子 (42,104,2026)、超时阶梯 (12,60,180) 或 600 s 仅属于 recovery path 的说明。页数影响 0。风险：若正文超页，只能压缩别处，不能动该算法。

### C9. Comparative Evaluation（L202–257）

**C9.1 §5.1 Setup（L204–215）— P0 + P1 表述。**

- **P0（A7）**：按 §0.3 改写 PE / SigLIP2 定义（余弦 vs sigmoid）。VQAScore 可补 “full-vocabulary softmax probability of Yes”（与代码一致）。建议稿见 A7。
- **P1（协议，批准即可写，不新增实验数字）**：在 “The systems differ in candidate selection…” 之前或之后加 2–3 句，事实来自已读溯源文件，例如：

> BrickGPT outputs in this comparison were generated with `world_dim=20`, `max_bricks=200`, and seed 42 (114 prompts; 66 marked stable in the generation log). BrickMore placements lie on a $48^3$ grid. These generator constraints differ, and the scores should be read with that difference in mind.

出处：`brickgpt_generation_summary.jsonl`（本轮计数：world_dim 全部为 20，max_bricks 全部为 200，seed 全部为 42，stable 66/114）。**不要**把 66/114 解释成论文里 BrickGPT 官方测试集的稳定率。+0.12–0.18 页。

- 渲染协议、P_inv 公式、110/4 已在，不改数字。

**C9.2 §5.2 主表（L217–234）— 数字锁定。**

主表数字须保持：BrickMore 0.00% / 0.2176 / 0.1856 / 0.1231；BrickGPT 0.00% / 0.1401 / 0.1457 / 0.0297；BrickNet 21.99% / 0.0624 / 0.1302 / 0.0100；91/95/91；零件 413.0 / 152.3 / 23.3（均与先前交叉核对及当前 `scores.csv` 主输出一致，本计划不重算、不改）。

若 A5 批准：在 “no significance test is reported” 处改为指向附录的一句，例如 “Paired per-prompt tests on the existing scores are reported in Appendix~\ref{app:eval}.” 然后**删除** “no significance test is reported”，避免自相矛盾。不要改 “highest mean” 结论句，除非检验结果与方向冲突（若冲突，先停下来向用户汇报，不得自行改结论）。

**C9.3 §5.3 raw vs retiled 表（L236–254）** — 0.1897%→0.0000%、VQA 0.2065/0.2071、PE 0.1858/0.1859、SigLIP2 0.1379/0.1261、零件 178.7/421.2 已在 V1.4 用同一套结果核对。不动。

**C9.4 §5.4 Boundaries（L256–257）** — 已声明非空间推理基准、非精确复现他文。保持。P2 最多在 PE/SigLIP2 定义改完后，加半句两种分数尺度不同（余弦 vs sigmoid）。+0.03 页。

### C10. Limitations and Conclusion（L259–268）

**C10.1 Scope 句（L261）** — 已明确无预训练、无 RL、生成器为纯文本 LM、VLM 仅作评测。**锁定，禁止削弱或改成“我们提出一个 VLM”。**

**C10.2 Data accounting（L263）** — 若 A3 批准，与 §3.3 用同一口径（79,301 为整合几何通过）。不要在这里只改成 79,322。

**C10.3 Conclusion（L267–268）** — 不改核心结论。标题若更换，结论第一句仍以 BrickMore + 三项组成部分为准。

### C11. References（L270）

不新增未经核验的条目。BrickGPT 配方表已引用 arXiv:2505.05469（V1.5 已核）。P2：编译后检查有无 `?` 或 undefined citation。

### C12. Appendices（L275–末）

**C12.1 附录 A 历史图（含中文）** — 见 A4，默认不动。

**C12.2 附录 B 训练细节与配方表** — 配方表已与 arXiv:2505.05469 §5.1 / 附录 A 核对（V1.5 P1），**不要再改 BrickGPT 列数字**。24,448 tokens/s、损失表数字不动。Token 口径说明若太长，可把模型卡 ~2.19B 的脚注放这里而非正文。

**C12.3 附录 C** — 若 A5/A7 批准，在 `app:eval` 增加：
  - 一张配对检验表（系统对 × 三个对齐指标；写明检验名称、n=114、文件 `scores.csv`；不在计划里预填 p 值）；
  - 可选 L1–L5 均值表（同一文件的 `level` 列）。
  正文用交叉引用，不把大表塞进第 5 节。历史图仍保留。

**C12.4 附录 D 历史表** — 不动；继续标明不可替代主对比。

---

## D. 哪些需要新实验 / 新数据（及截止前是否可行）

| 想法 | 是否新实验 | 现有产物是否足够 | 截止前可行性 | 计划建议 |
|---|---|---|---|---|
| 改 PE/SigLIP2 文字定义 | 否 | 是，评测脚本已读 | 高 | 做（P0） |
| 79,301 vs 79,322 说明 | 否 | 部分：缺训练清单 / `trainer_state.json` | 高（分开写口径）；**彻底对齐取决于用户能否找到清单** | 做说明；不臆造 79,322 的来源细节 |
| 精确 token 复核 | 否（找日志） | **当前未找到日志** | 不确定 | 保留 2,228,044,818 + 脚注 |
| 配对显著性检验 | 否（新分析，有新数字） | 是，`scores.csv` 114 条 primary | 高（数小时） | 用户批准后做，放附录 |
| L1–L5 分层 | 否（新分析） | 是，同上 `level` 列 | 高 | 可选，放附录 |
| 写入 BrickGPT world_dim / 66 stable | 否 | 是，`brickgpt_generation_summary.jsonl` | 高 | 建议做（P1） |
| 105 组等权重算主表 | 新分析数字 | 分析文档中 V1.4 曾提及方向一致，但本计划不采用未在本轮重算的数字 | 中（需重算并核对） | 除非用户要求并亲自核定，否则不做 |
| 空间推理新基准 | 是 | 否 | **低** | 不做 |
| 再训练 / 数据规模消融 | 是 | 否（无第二套训练权重） | **低** | 不做 |
| 重绘中文图、补物理实验 | 是 | 否 | 低 / 中但无必要 | 不做 |

---

## E. 日程（UTC+8，含缓冲、编译、匿名、投稿）

假设用户在 **11-15 当天或 11-16 上午** 回复 §A 的选项。若决策推迟，压缩 T6/T7，优先 T3/T4/T5 与编译投稿。

| 时段 | 工作 | 产出 |
|---|---|---|
| **11-15 上午（今天）** | 用户圈定 A1–A8。准备 Overleaf 项目或确认继续用 box TinyTeX。不要安装到用户机器除非用户要求。 | 决策清单打勾 |
| **11-15 下午** | 实施 P0：标题（若定稿）、PE/SigLIP2 定义、§3.3/表 1 口径说明、匿名源码再检索。第一次 `latexmk -pdf`。检查正文是否仍在 ≤7 页、引用是否完整。 | V1.6 初稿 PDF |
| **11-16 上午** | 若批准：从 `scores.csv` 计算配对检验（及可选 L1–L5），草稿只放附录。写 BrickGPT 协议句。 | 附录草稿 |
| **11-16 下午** | 把批准的分析写入 V1.6，二次编译。对照页数预算；若接近 7 页，下沉 T5 细节。 | V1.6-pre PDF |
| **11-17 全天** | 通读英文：术语 retiled、caption、validation；Scope 句未动摇。第三方读一遍摘要/引言/§5。第三次编译。核对字体 Type 1、无 Overfull、无未定义引用。 | 接近定稿 |
| **11-18 全天（缓冲日）** | 冻结内容（除作者表单）。匿名清单：PDF 与源码搜作者名、邮箱、`D:\`、内部路径、致谢、可识别 URL。用 Overleaf pdfLaTeX 复现一版，与 box 页数对比。准备 OpenReview：所有作者 profile、title/abstract/keywords/TL;DR、paper type=Long Paper、PDF（&lt;50 MB）、许可 CC BY 4.0。 | 提交包 |
| **11-19 上午–下午（强烈建议的实际上传日）** | 最终 PDF 再编一次。OpenReview 提交并自行下载 PDF 核对。不要拖到 11-20 晚上。 | 已提交 |
| **11-20 12:00 前（最后缓冲）** | 仅处理系统故障或明显错别字修订（视 OpenReview 是否仍开放；截止为 11-19 AoE＝11-20 19:59 UTC+8，但不要依赖最后一小时）。 | 应急 |

编译检查每次至少包括：`latexmk -pdf` 退出码 0；日志无 undefined references/citations；`pdfinfo` 为 letter 且总页数合理；正文结论仍在第 7 页之前；`pdffonts` 无 Type 3；首页为 Anonymous submission。

---

## F. 按优先级汇总（实施清单）

### P0（截稿前必须处理或明确维持）

1. 用户确定标题（A1）；确定后改 `\title`。
2. PDF 保持匿名；作者只进 OpenReview（A2）。
3. 分开写 79,301（整合几何通过）与 396,610（训练样本）；注明模型卡 79,322，不擅自改表（A3）。
4. Token 保留 2,228,044,818，脚注 ~2.19B 与日志缺失（A3）。
5. 按代码修正 PE（余弦）与 SigLIP2（logit 的 sigmoid）定义（A7）。
6. Algorithm 1 留在正文。
7. 不改主表/配对表已核对数字，不改结论方向，不宣称 RL/预训练/VLM。
8. pdfTeX 编译通过；匿名与投稿流程（A8、日程 E）。

### P1（建议做，需部分批准）

9. §5.1 补充 BrickGPT `world_dim=20`、`max_bricks=200`、seed 42、生成日志中 66/114 stable（溯源文件）。
10. 若批准：对 `scores.csv` 做配对检验，附录出表，正文一句话引用。
11. 可选：L1–L5 分层附录表。
12. validation vs test 脚注。

### P2（建议不做或仅文档）

13. 重绘/删除中文历史图。
14. 新建空间推理评测或再训练消融。
15. 更新仓库根目录 `abstract_introduction.md`。
16. 微调 Underfull；填写 reproducibility checklist（仅当提交页出现该栏或时间充裕）。

---

## G. 风险总表（横切）

- **超页**：新增段落后浮动体把结论推后。对策：新表进附录；超页时先缩 T5 而非删算法或主表；每次编译量页。
- **口径冲突**：79,301 与 396,610 被审稿人乘出矛盾。对策：A3 分开写。
- **匿名失败**：PDF 或源码泄露。对策：11-18 清单；保持 `[submission]`。
- **把分析写成新实验**：显著性或分层是对已有分数的再分析，须在文中写数据来源，避免 “we conducted a new evaluation” 的夸大。
- **编译器错误**：Tectonic 无法编 AAAI 稿。对策：Overleaf pdfLaTeX 或 TinyTeX/MiKTeX + `latexmk -pdf`。
- **截止风险**：以 11-19（UTC+8）提交为目标，把 11-20 当应急。
