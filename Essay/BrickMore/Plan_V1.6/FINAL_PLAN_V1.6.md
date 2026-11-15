# BrickMore V1.6 最终合并计划（FINAL_PLAN_V1.6）

- 文件：`D:\BrickMore\Essay\BrickMore\Plan_V1.6\FINAL_PLAN_V1.6.md`
- 合并依据（只读）：`PLAN_RB1_R4.md`、`PLAN_RB2_R4.md`、`CRITIQUE_RB2_R4.md`；E-9 / U14 建议句取自 `CRITIQUE_RB1_R4.md` 的独立复核。行号已对照 `V1.5\main.tex`（33,614 字节，407 行，2026-11-14 23:36:55 UTC+8，SHA256 `A1EEF7D8…`）重核。
- **只写本文件。** 未修改任何论文源文件，也未改动既有 `PLAN_*` / `CRITIQUE_*`。不虚构数字或文献。
- 硬约束：GSR-VLM Topic 5 only；AAAI-27 模板；正文（摘要至结论）≤ 7 页，References 可从第 8 页起；Algorithm 1 留在正文，不以 `figure*` 改排；不宣称预训练、RL，或生成器是 VLM。
- 截稿：**2026-11-20 19:59（UTC+8）**。建议 **11-19** 提交。找训练清单截止：**11-17 24:00（UTC+8）**。
- 说明：两边的 R4 交叉评审的是对方的 **R3**，不是对方的 R4。下文按各自**最新文本**合并，并把因此出现的不一致标为「未消除分歧」。

**未消除的分歧（RB2 终审后剩 1 项，须用户在对应条目中圈定）：**
1. **image18**：RB1 R4 建议保留并补判据图注；RB2 建议移出提交 PDF 或删 (a) 栏。若保留，图注必须按条目 3 的修订版写（BrickGPT 的 stable 标记是连通性检查）。

RB2 终审已消除（见文末「RB2 审阅记录」）：
- ~~摘要是否写 “46 of 525 …”~~：RB2 终审改为支持 **N**，与 RB1 R4 一致（见条目 5）。
- ~~U14~~：RB2 终审改为支持 **B**（附录披露），与 RB1 一致，只在建议句里补一个对应关系的限定从句（见条目 9 与 §2.3）。

已消除、不再并列两套事实表述的事项：525 与 114 的关系（采用候选池表述，见 E-2）；标题推荐（双方共同推荐 B′，仍由用户圈定）；U13 种子规则（已由 `gen_levels2.py` 裁定，与 Algorithm 1 一致，不把 README L55 写入论文）。

---

# 1. 需要用户拍板

请尽量在 **2026-11-15 14:00（UTC+8）** 前回复；晚于此时仍可改，但会挤压编译与内审。未答复时，除下面标明「未消除分歧、不可默认执行」的条目外，按★推荐执行。

## 1.1 必须圈定的内容项

### 1. 标题（U1）——双方共同推荐 B′，仍须圈定

- 选项：
  - **A**：`BrickMore: Learning Stud-Connected Brick Assembly from Agentically Generated Voxel Data`
  - **B′**：`BrickMore: Learning Spatial Brick Assemblies by Agentic Data Generation and Language-Model Fine-Tuning`
  - **C**：保持 `BrickMore`
- **RB1 推荐 B′**：直接对应 Topic 5 的 “data generation” 与 “fine-tuning”，不含不实字样；也接受 A。
- **RB2 推荐 B′**（R4 起改为共同推荐，A 为备选）：同样因为 B′ 对齐 Topic 05 用词。A 的优点是点出 stud-connected，但不再作为第一推荐。
- 改动：`main.tex` L23 的 `\title{BrickMore}`，并同步 OpenReview 的 title 字段。未圈定前不动标题。

### 2. 附录中文历史图 image13–17、image19（U4）——双方一致

- 选项：★**C′** 全部保留（段首加 “Historical material with Chinese labels; not used for any claim.”；image14/17/19 中过时的 “require verification” 改为指向已复核的发布报告）；**A** 用 `\iffalse` 移出提交 PDF（文件保留），并以英文表替代已复核数字；**B** 重绘英文版（不推荐，耗时）。
- **RB1 / RB2 均推荐默认 C′**：这些图只在附录（V1.5 PDF 约第 7–10、13 页），正文页数影响为 0；删除须用户同意（`REVIEW_V1.5.md` L6）。
- image18 **单独见下条**，不要与本条捆绑默认删除。

### 3. image18（U4-b）——**未消除分歧，不可默认执行**

图在 `V1.5\main.tex` L383–387（`figures/image18.png`），图注已写 “Historical baseline comparison with differing acceptance criteria; not the current matched main comparison.”。蓝柱可从 `best_all.json` 复算：L1–L5 为 18/21、16/21、17/21、15/21、13/21（85.7 / 76.2 / 81.0 / 71.4 / 61.9%，合计 **79/105** 组有人工判决获胜者）。红柱为 BrickGPT jsonl 的 `stable=True`：13/21、15/21、12/23、12/25、14/24。作图脚本仍未找到。

- 选项：**(K)** 保留，并补判据图注；**(R)** 整图 `\iffalse` 移出提交 PDF（文件保留）；**(A)** 只删 (a) 栏，保留 (b)(c) 并标明 historical。
- **RB1 推荐 K（保留 + 图注）**：已撤回 R3「因无数据源而删 (a)」的建议，因为蓝柱可从 `best_all.json` 精确复算（79/105 组有人工判决获胜者）。图题本身已写判据不同，补一句即可，不必删图。建议图注追加（RB2 终审修订：在 “stability flag” 处加限定，因为记录中 `use_gurobi=False`，官方源码此时用 `is_connected()` 代替物理稳定性检查）：*“Panel (a) compares different criteria—BrickGPT's per-prompt run-log `stable` flag (a connectivity check, since Gurobi was disabled) versus whether human review found an acceptable BrickMore output among six candidates per category–level group—and is not a like-for-like comparison.”*
- **RB2 推荐 R（移出整图，或至少删 (a)）**：理由**不是**“没有数据源”，而是：(1) 计数口径与主对比不同（组级人工 6 选 1 vs 单样本自动稳定标记）；(2) 结合 E-9，BrickMore 一侧含人工挑选，附录中容易被读成稳定性优势；(3) 蓝柱、红柱都不进正文。RB2 建议未答复时移出，但仍以用户同意为前提。(4)（RB2 终审补充）红柱的 `stable=True` 是在 `use_gurobi=False` 下得到的，按官方 `brickgpt.py` L359–360 的 `_is_stable`，这只是连通性检查，不是物理稳定。所以图上的 “stable=true” 标签本身就会误导读者。
- 蓝柱、红柱数字**均不写入正文**。未圈定前不动 image18。

### 4. 是否把 525 条结构诊断写入论文（U12）——双方一致建议写入

- 选项：★**写入**（正文一段，表默认放附录 C；只用可复算字段；不写 additional / held-out / 独立运行 / 形状保真 / 空间推理基准；必须与 E-9 同时出现）；**不写**。
- **RB1 / RB2 均推荐写入**：这是已有文件里最贴近 Topic 5 的几何探针，无需新实验。525/114 关系采用双方已收敛的候选池表述（见第 2 节 E-2），不再交用户在 “separate collection” 与 “candidate pool” 之间二选一（RB1 R4 已撤回前者）。
- 依赖 U10：未确认权重前，不写 “all evaluated outputs use the step-79,000 checkpoint”。
- 摘要里要不要出现诊断数字，见下条（**未消除分歧**）。

### 5. 若批准 U12，摘要是否出现 “46 of 525 …”——**已消除（RB2 终审改为支持 N）**

两边在 R4 确实对调了立场：`PLAN_RB2_R4.md` 选 Y（采纳 RB1 R3），`CRITIQUE_RB1_R4.md` N4 选 N（采纳 RB2 R3）。RB2 终审**最终支持 N**，双方一致。

- 选项：**(N)** 摘要不放诊断数字，最多半句定性；**(Y)** U12 批准后加一句 *“On 525 diagnostic prompts, 46 raw outputs form a single stud-connected component without repair.”*（不写 8.8%，不写失败中位数 5；该计数在 E-2 仍可出现一次）。
- **RB1 R4 推荐 N**：接受了 RB2 R3「摘要不放数字、诊断数字只在 E-2 出现一次」的收紧。
- **RB2 R4 曾推荐 Y**（接受了 RB1 R3「可写这一处计数」），**终审改为 N**，理由有四：(1) 诊断数字只出现一次（N9），E-2 已经给出；(2) 不带 8.8% 和分母背景的 “46 of 525” 放在摘要里含义不清，读者看不出这是 raw 的连通率；(3) 摘要已经很密（约 215 词）；(4) 主张的实质（raw 输出多不能跨层咬合）用定性半句就能表达，不新增数字位置。U12 批准后，摘要用 A-2 中的定性半句。
- 默认按 N：U12 批准后只加定性半句，不写计数；用户若明确要求 Y，再换成计数句。

### 6. 显著性检验（U5）——双方一致建议做

- 选项：★**做**：对已有 `scores.csv` 做配对双侧符号检验 + Wilcoxon，3 指标 × 2 对手共 6 次，Holm 校正；不检验 $P_{\mathrm{inv}}$；不预填 p 值；正文 1–2 句，表在附录；写成 “re-analysis of the existing per-prompt scores”。**不做**。
- **RB1 / RB2 均推荐做**。因 E-9，p 值只能解释为这批**交付输出**的差异，不能写成孤立的模型能力。不显著则如实写，不改“均值最高”结论。
- 会产生新数字，未批准前不写入。

### 7. 评测权重是否即 step-79,000（U10）

- 选项：确认 525/114 所用权重就是 `load_best_model_at_end` 的 step-79,000；或说明各子集用的版本。
- **RB1 / RB2 一致**：请书面确认。`eval_630` README 与 `汇总交付\资料与记录\provenance.json` L3 的 revision `92d1c595f5fe…` 是 Git 提交号，与 `model.sha256` 的 `75f79af15dd7…`（文件哈希）不是同一标识体系。45 条 judged 属于 `92d1c595`。其余 **64** 条（review_59 21、成功的模型 16、round2 12、round3 7、nine_ldr 7、car_trials 1）项目内无权重记录。未确认则**不写** “all evaluated outputs use this checkpoint”。provenance 中的仓库名含账号，不得进论文。

### 8. 训练清单 / 日志（U3），截止 11-17 24:00（UTC+8）

- 选项：在截止前提供 `trainer_state.json` 或训练清单，据实测改正样本数与 token；否则启用 **C′** 拆表。
- **RB1 / RB2 均推荐**：优先用清单；找不到就拆 Table 1 为 “Dataset (release reports)” 与 “Fine-tuning corpus”，79,301 与 396,610 / 2,228,044,818 分口径保留，中性表注。**不**提模型卡，**不**写 training manifest / training report / 日志缺失，**不**把 79,322 填进表，**不**用 24,448 × 25.3 h 的乘积替换 token 数。
- 未到期前只改表结构、不改数字。

### 9. BrickGPT 运行配置是否在附录披露（U14）——**已消除（RB2 终审改为支持 B）；仍由用户批准**

项目记录（114/114）：`max_regen=8`、`use_gurobi=False`、`world_dim=20`、`seed=42`、`max_bricks=200`。BrickGPT 论文（项目内 `2505.05469v3.pdf` 第 8 页）：最多 100 次物理感知 rollback，Eqn. 3 用 Gurobi 求解。官方仓库 `BrickGPTConfig` 默认：`max_regenerations=100`、`use_gurobi=True`、`max_bricks=2000`。

- 选项：**(B)** 主文只写 $20^3$ 与 seed 42，附录如实写出记录值并注明并非作者默认配置；**(A)** 主文与附录都不写 `max_regen` / `use_gurobi`，只保留 E-8 短句；**(C)** 仅当用户能证明“未调参、即官方脚本默认”后再写一句，否则不写。
- **RB1 推荐 B**：记录值与论文 / 仓库默认都不同（8 vs 100；Gurobi 关闭后源码走连通性而非物理稳定）。审稿人若对稳定性协议有疑问，附录如实披露更稳妥。建议句见第 2 节 U14。`max_bricks=200` **不写**（36 条 `brick_count>200`）。
- **RB2 R4 曾推荐 A**（项目内没有写出这些字段的脚本，`max_regen` 也没有定义）。**终审改为 B**，理由是：RB2 已亲自读取官方 `src/brickgpt/models/brickgpt.py`（main 分支，2026-11-15），确认 L50–56 `max_regenerations` 默认 100，help 为 “roll back and regenerate … if it is physically unstable”；L57–62 `use_gurobi` 默认 True，False 时 “default to a simpler, but less accurate connectivity-based stability check”；L32–36 `max_bricks` 默认 2000；L359–360 `_is_stable` 在 False 时调用 `is_connected()`。`use_gurobi=False` 与论文配置的差异是确定的，与评测公平性直接相关，如实写在附录比不写更稳妥。只在建议句中补一个限定从句，说明 `max_regen` 与 `max_regenerations` 的对应关系是推断（见 §2.3）。双方都**禁止**写 “BrickGPT was run with its authors' default configuration”。
- 未圈定前：先执行 E-8 短句（$20^3$，seed 42）。附录句（B）是双方共同推荐，用户未反对即可写入附录；`max_bricks=200` 仍不写。

### 10. 确认 E-9 披露句（事实已由文件确定，只需确认英文概括）

双方都把选择效应披露定为 **P0**，必须写入 §5.1。建议采用 RB1 复核后的拆分（45 为 6 选 1；其余 69 中 35 条替换了 34 组已有获胜者，34 条补入 26 个全不合格组；脚注给出分来源计数），而不是较粗的 “the remaining 69 come from later gap-filling, regeneration, and review rounds” 单句。完整 LaTeX 见第 2 节 E-9。若用户对轮次有更准的英文名称，执行前替换脚注，不改数字。

## 1.2 双方已一致、未反对即按此执行（RB2 R4 列入确认清单）

| 项 | 推荐 | 说明 |
|---|---|---|
| U2 作者与 OpenReview | 今日全体作者注册或确认 profile；PDF 保持 `[submission]` | 见第 6 节；公共邮箱审核可能长达约 2 周 |
| U6 新空间推理基准 | 不做；用 E-2 几何诊断代替 | 时间不够做扎实协议 |
| U7 消融 / 重训 | 不重训；用转换策略对比与 raw/retiled | 单次训练 25.3 h × 8 GPU |
| U8 指标定义 | 按 Deploy 脚本写（见 E-1） | SHA 前缀 `a90e851a6a01` |
| U9 编译 | box TinyTeX 为主，本机 MiKTeX 备份，Overleaf 第三备选 | 免费版每项目仅 1 名协作者，且须上传未发表稿 |
| U11 Reproducibility checklist | 不附 | OpenReview 无附件栏；若要规范只能进 PDF 附录 |

---

# 2. 双方已同意的修改（按 P0 / P1 / P2）

行号均指 **`V1.5\main.tex` 本轮重核结果**。部分旧计划把 E-9 那句记为 L216，实际是 **L215**（`\subsection{Main Results}` 在 L217）。带【】或标明“条件”的条目，须等第 1 节对应决定后再写入。

## 2.1 P0（投稿前必须完成；7 项）

### G-1｜编译与页数验收（全局）

每批修改后在 box 用 TinyTeX：`latexmk -g -pdf -interaction=nonstopmode main.tex`。验收：日志无 `!` / undefined；`pdftotext` 确认结论最后一行在第 7 页或更早，第 7 页之后无正文；`pdffonts` 全为已嵌入 Type 1；`pdfinfo` 纸张 letter（612×792 pt），无 Author/Title；第 1 页含 “Anonymous submission”。页面影响 0。

### G-2｜匿名复查（全局；投稿 PDF 与源包）

见第 5 节清单与命令。V1.5 的 `main.tex` / `main.bbl` / `main.pdf` 本轮未检出用户名或 `C:\Users` / `D:\Users` / `E:\brick_train`。页面影响 0。

### G-3｜OpenReview 表单素材

Long Paper；keywords 与 TLDR 用已商定、不含未裁定数字的版本（见 `PLAN_RB2_R4` G-3）；摘要与 PDF 一致（去 LaTeX）。页面影响 0。

### E-1｜§5.1 指标精确定义（L207；U8 已有脚本证据，可直接改表述）

替换 L207 中 “PE and SigLIP2 are image--text matching scores …” 句。不写 “learned scale and bias”。证据链引 Deploy 副本（SHA 前缀 `a90e851a6a01`）。约 +0.03 页。

```latex
\emph{Text--image alignment.} VQAScore~\cite{vqascore} is the full-vocabulary softmax probability that Qwen2.5-VL-7B-Instruct~\cite{qwen25vl} generates the single token ``Yes'' as its first answer token when asked whether a rendered view shows the prompt. PE is the cosine similarity between L2-normalized image and text embeddings of PE-Core-bigG-14-448~\cite{pe}, and SigLIP2 is the sigmoid of the image--text logit of SigLIP2 giant-opt-patch16-384~\cite{siglip2}; their text encoders read at most 72 and 64 tokens, respectively. For each metric, a model's score is the maximum over its eight views, averaged over prompts. The three metrics therefore live on different scales and are compared only within a metric.
```

### E-9｜§5.1 选择效应披露（替换 L215；P0，建议句用 RB1 复核拆分）

V1.5 L215 仅有泛泛一句。必须写明：45/114 为每组 6 个候选中的人工最佳（及其提示词）；79/105 组有获胜者，其中 45 个进入主对比；其余 69 条中，**35** 条替换了 34 组已有获胜者，**34** 条补入 26 个全不合格组。分来源：review_59 21、成功的模型 16、round2 12、round3 7、nine_ldr 7、regenerated 5、car_trials 1。执行时给 `\subsection{Setup and Metrics}`（L204）加上 `\label{sec:setup}`。约 +0.05–0.08 页。脚注中的轮次英文名称若用户要改，只改用词、不改计数。

```latex
The systems differ in candidate selection, filtering, and post-processing.
On the BrickMore side, 45 of the 114 comparison outputs, together with their prompts, were chosen by human review as the best of six candidate phrasings in a category--level group; a winner was available in 79 of 105 groups, and 45 of those winners entered this comparison.
The remaining 69 outputs come from later fill-in, regeneration, colleague, and review rounds, including 35 cases that replaced a judged winner in the same group.\footnote{The six candidates are the five new-batch phrasings and one first-batch phrasing documented in the evaluation-set README. Among the 69: \texttt{review\_59} 21, a colleague success set 16, second-round redo 12, third-round fill-in 7, colleague \texttt{nine\_ldr} 7, regeneration 5, and \texttt{car\_trials} 1, as recorded in the 11-07 delivery manifest. BrickGPT was then run once on each selected prompt (seed 42); BrickNet contributed one accepted sample per prompt (up to 30 attempts).}
The comparison therefore characterizes these delivered outputs rather than isolated model capability.
```

### S-2｜建立 V1.6 目录与交付物

从 V1.5 复制后只在 V1.6 内编辑。交付 `main.pdf`、`main.tex`、`references.bib`、`REVIEW_V1.6.md`；U5 批准则加 `analysis/significance.*`。不要把 log / fls / bak / 历史 zip 打进投稿包。

### S-3｜提交前终检

执行第 4–5 节清单（页数、匿名、源包白名单）。

## 2.2 P1（强烈建议；21 项。若干依赖用户决定）

### A-2｜摘要重写（L38–40）——部分条件

压缩机制细节，突出数据生成 + 微调 + 几何约束。约 −0.05 页。**【】为定性半句，仅当条目 4（U12）批准时保留**（RB2 终审：条目 5 双方选 N）；U12 不批准就删除。若用户明确要求条目 5 选 Y，再把【】换成 “On 525 diagnostic prompts, 46 raw outputs form a single stud-connected component without repair.”核心数字 80,000 / 79,301 / 114 / 0.00% 保持不变。

```latex
\begin{abstract}
Generating brick structures from text requires geometric assembly: bricks must fit in a bounded grid, avoid overlaps, and interlock through studs, not merely resemble the described shape. We study how far a language model can learn such a spatial representation from programmatically generated data. Using GPT-6.1 Sol, an agentic batch-generation pipeline writes parametric generator programs that emit 80,000 voxel models across 21 categories on a $48^3$ grid, each with five bilingual captions of increasing detail. Same-color tiling, connectivity analysis, and local bridging and retiling convert the shapes into brick layouts, and 79,301 models pass the specified geometric checks. We fine-tune Qwen3-1.7B with LoRA on English captions and serialized brick placements, and repair its predictions by solving a shape-preserving exact cover with a single stud-connected component via mixed-integer linear programming (MILP). 【A structural analysis of raw outputs shows that interlocking across layers is the constraint the learned representation most often misses.】 On 114 shared prompts under a common rendering protocol, the evaluated BrickMore outputs (110 retiled, 4 raw) obtain the highest mean scores on three text--image alignment metrics and a mean invalid-placement ratio of 0.00\%, matching BrickGPT.
\end{abstract}
```

### I-1｜引言第 1 段末加试验床框句（L50 末）

在 “…not only whether the overall shape resembles the described object.” 之后加：

> This makes text-to-brick generation a useful testbed for learning spatial representations: the target is discrete, the constraints are exactly checkable, and a model's errors can be measured geometrically rather than only perceptually.

“geometric reasoning and object assembly”（L50）按 Topic 5 用词保留，不写成 “improves spatial reasoning”。约 +2 行。

### I-2｜引言第 4–5 段去重（L56–58）

合并为一段，数字只在贡献列表出现一次。约 −0.15 页。**必须把 L58 的 “the current output does not include color” 移到 §4.1（L131）段末**，因 V1.5 §4.1 没有这句。

```latex
We present BrickMore to study this problem. GPT-6.1 Sol writes parametric generator programs that emit voxel models in batches; a conversion pipeline tiles them with same-color bricks and uses local bridging and retiling to address ungrounded components, recording any change to the source voxels. We then fine-tune Qwen3-1.7B~\cite{qwen3} with LoRA~\cite{lora} on English captions and brick-placement sequences, so that the $48^3$ workspace, multi-level captions, and fixed spatial serialization define the representation being learned. Because the model's raw layouts may still overlap or fall apart into stud-disconnected pieces, a post-generation stage forms the voxel union of supported placements, seeks an exact cover with a single stud-connected component by MILP, and queues a new sampling seed when no cover is found within the solver budget. The connectivity check is geometric; physical stability and assembly-order feasibility require separate evaluation.
```

### I-3｜引言新增定性预告段（插在 L60 “We compare…” 之前）——【】依赖 U12

引言只写定性，数字只在 E-2。约 +0.10 页。U12 不批准则删去【】句。

```latex
Our analysis asks what such a model actually learns from generated data. 【A diagnostic analysis of raw outputs (Section~\ref{sec:diagnostics}) shows that the model's layouts usually fail to interlock across layers and fall apart into several stud-connected pieces.】 We therefore treat geometric repair as a complement to, not a substitute for, the learned representation, and we report both raw and retiled results.
```

### I-4｜贡献列表改写（L62–67）——第 3 条【】依赖 U12

约 0 页净变化。U12 不批准则第 3 条只保留后半句。80,000 / 79,301 只在此处展开一次。

```latex
\begin{enumerate}
\item \textbf{Data generation for spatial learning.} An agentic batch-generation pipeline in which GPT-6.1 Sol writes parametric generator programs, producing 80,000 $48^3$ voxel models across 21 categories with five bilingual captions each, and a voxel-to-brick conversion that targets stud-connected layouts rather than voxel adjacency; 79,301 models pass the specified geometric checks.
\item \textbf{Fine-tuned text-to-brick representation.} LoRA fine-tuning of Qwen3-1.7B on serialized placements over a 20-type library in a $48^3$ workspace, with post-generation MILP retiling that enforces a single stud-connected component.
\item \textbf{Geometric diagnosis and evaluation.} 【A structural analysis of raw outputs on 525 prompts showing which spatial constraints the model learns and which it misses,】 and a matched comparison with BrickGPT and BrickNet on 114 prompts under a common rendering protocol.
\end{enumerate}
```

### R-1 / R-2｜相关工作新增两段（§2，L77–85 之后或 “Procedural data” 段末）

增加已核对的三篇（venue 只写 arXiv，执行时原样使用 `PLAN_RB2_R4` 中已补全作者的 bib：meshgpt arXiv:2311.15475 8 人，llamamesh arXiv:2411.09595 7 人，spatialvlm arXiv:2401.12168 9 人）。不写“本文提升了 VLM 空间推理”。约 +0.12 页。

```latex
\paragraph{Language models for serialized 3D structure.}
Autoregressive transformers can generate 3D geometry as token sequences, e.g., triangle meshes in MeshGPT~\cite{meshgpt}; LLaMA-Mesh fine-tunes a pretrained language model to emit meshes as plain text~\cite{llamamesh}. BrickGPT and BrickMore apply the same idea to discrete brick placements, where validity can be checked exactly.

Synthetic spatial data is also used to teach vision--language models spatial relations, e.g., SpatialVLM~\cite{spatialvlm}; BrickMore instead trains a text-only generator on programmatically generated assembly data and uses vision--language models only for evaluation.
```

### D-1｜§3.2 转换效益（L94 首句之后）

来源：`retile_assembly_80000\summary.json`（与 relaxed `assembly_summary.json` L8 的 65,503 已复核）。约 +0.06 页。31,532 不写成 “of the 79,301”。

```latex
Relative to the earlier relaxed release, the local bridging-and-retiling stage raises the number of geometrically passing models from 65,503 to 79,298 (13,795 recovered failures) while adding 228,582 and removing 125 voxels in total across the corpus; 31,532 passing models require no voxel change at all.
```

### D-2｜Table 1 拆表（L99–120；数字按 U3 定稿）

用 `\midrule` 分成数据集与微调语料。U3 截止前只改结构。约 +1 行。删 L121–125 中会暴露模型卡与 “trainer_state.json were not found” 的源码注释，避免编译产物或源包泄漏。

### D-4｜§3.1 五级描述短例（L90）

从 `V1.5\figure2_units\references\birdhouse_prompts_L1_L5.json` **原样**摘 L1 与 L5，不改写。执行时先确认该 JSON 的 `modelId` 属于训练描述而非示意图专用。L5 过长则正文只留 L1、L5 放附录。约 +0.05 页。

### M-1｜§4.1 写清学到的表示（L131–135）

补 2 行：序列化约定与几何约束如何构成被学习的表示；收纳从引言移来的颜色句。核实序列化规则后再写强表述，否则用弱化版。约 +2 行。

### E-2｜新增诊断小节（建议插在 L236 `\subsection{Raw versus Retiled}` 之前，作为新 §5.3；原 5.3/5.4 顺延）——**依赖 U12**

表默认放附录 C。采用 RB1 的候选池统一句（含 105 条首批与 45/35），加上默认环 / 28 条额外种子 / 2 条 600 s，以及 RB2 所补「46 条 raw 已单连通则保留不变」。**不写** attempt 计数 338/134/53（那是首次标签）。不写 “all 525 follow the default loop of Algorithm 1”。约 +0.20 页（表在附录）；若把表放回正文约 +0.35。数字来源：`raw_failure_autopsy.json` 与 `manifest_w{0,1,2}.json`（执行时再点算一遍）。

```latex
\subsection{Structural Diagnostics of Raw Outputs}
\label{sec:diagnostics}
To probe what the fine-tuned model learns, we inspected 525 BrickMore generations from a diagnostic set (21 categories $\times$ five levels $\times$ five phrasings). The 525-prompt diagnostic batch, together with 105 first-batch prompts, formed the six-phrasing candidate pool from which 45 of the 114 comparison outputs were selected (35 of them from the 525); see Section~\ref{sec:setup}. Generation used seeds 42, 104, and 2026 in that order, moving to the next seed when a draft was incomplete or failed the geometry validator, then applied the 12--60--180\,s MILP ladder (the default loop of Algorithm~\ref{alg:inference-retiling}); raw drafts that already formed a single stud-connected component were kept unchanged. For 28 prompts a recovery path sampled seeds outside $S$; for two further prompts the solver budget was extended to 600\,s. Only 46 raw layouts (8.8\%) form a single stud-connected component without retiling; this rate shows no clear trend across levels (13, 9, 9, 7, and 8 for L1--L5) but varies strongly by category (e.g., 8/25 for sofa, 0/25 for basket and camera). All 479 failing raw layouts split into at least two stud components (median 5, maximum 33). Overlaps are a minor cause: 50 failing layouts contain duplicated voxels, 41 of them with at most five (median 2), and 429 contain none. The 2,240 detached fragments are mostly not grounded (1,320 airborne versus 920 grounded). The learned representation thus places bricks whose in-bounds voxel union is retained by retiling but that often fail to interlock across layers; all 525 final assemblies form a single stud-connected component with that union unchanged (Table~\ref{tab:diag} in Appendix~\ref{app:eval}). These checks evaluate stud connectivity and in-bounds voxel-union consistency, not prompt-level shape fidelity or spatial reasoning.
```

附录表字段（与上文同一来源）：Raw single stud component 46 (8.8%)；失败分量中位 / 最大 5 / 33；重叠 50/479；碎片 1,320 / 920；档位 326 / 133 / 18 / 2；换种子 28；最终 525/525；raw 砖数中位 183 (77–623)；retiled 中位 452。表题不把 `shape_preserved` 说成与提示匹配。

### E-3｜§5.2 分级别与稳健性（接在 L234 “…no significance test is reported.” 处）

等权 105 组数字已从 `scores.csv` 复算（BrickMore 0.2347 / 0.1840 / 0.1257 vs BrickGPT 0.1511 / 0.1459 / 0.0318）。L1–L5 三项均最高（15/15）。**“未截断子集”（PE 89、SigLIP2 85）须在执行前从 `text_truncated` 记录复算后才能写入**；复算前不要粘贴下列句中的 0.1821 / 0.1445 / 0.1088 / 0.0301。U5 批准则本句与检验句一起替换 “no significance test is reported”。约 +0.06 页。

```latex
The ordering is unchanged when each of the 105 category--level groups is weighted equally (BrickMore 0.2347 / 0.1840 / 0.1257 versus BrickGPT 0.1511 / 0.1459 / 0.0318 for VQAScore / PE / SigLIP2) and when truncated prompts are removed (PE on 89 prompts: [recompute] vs.\ [recompute]; SigLIP2 on 85 prompts: [recompute] vs.\ [recompute]), and BrickMore has the highest mean at every description level (Appendix~\ref{app:eval}).
```

### E-4｜附录 C 分级别结果表

L1–L5 × 3 系统 × 指标，正文 E-3 引用。正文页数 0，附录约 +0.3 页。

### E-6｜§5.3 raw vs retiled 解释句（L254 末）

用 “same in-bounds voxel union”，不用含混的 “occupied volume”。约 +2 行。

> Because retiling replaces the raw bricks with a different decomposition of the same in-bounds voxel union, the renders change in brick boundaries but not in that union, which bounds how much the alignment metrics can move.

### L-1｜Scope 段（L261）——【】依赖 U12

约 +0.03 页。不出现 reward/RL（与 “no reinforcement learning” 冲突）。摘要和贡献同样不出现 reward/RL。

```latex
\emph{Scope.} BrickMore studies spatial representation learning through data generation and supervised fine-tuning only; it performs no pretraining or reinforcement learning, and its generator is a text-only language model, with vision--language models used solely as evaluation metrics. Our evidence about the learned representation is geometric (stud connectivity of raw outputs) and perceptual (text--image alignment of renders); we do not evaluate it on a dedicated spatial-reasoning benchmark. 【The diagnostics suggest that the interlocking rule is the main missing constraint; connectivity-aware decoding is a natural direction outside the scope of this work.】
```

### C-1｜结论（L267–268）——【】依赖 U12

核心结论（对齐最高、$P_{\mathrm{inv}}$ 持平）不变。约 0 页净变化。

```latex
We presented BrickMore, which learns text-to-brick assembly from agentically generated, geometrically checked data by fine-tuning a language model, and repairs its predictions with stud-connected exact-cover retiling. 【Structural diagnostics show that the fine-tuned model's raw layouts usually fail to interlock across layers, which retiling resolves while preserving the voxel union.】 On 114 shared prompts, the evaluated BrickMore outputs achieve the highest means on three text--image metrics while matching BrickGPT on mean invalid-placement ratio. These results should be read within the stated evaluation and physical-screening boundaries.
```

### APP-2 / APP-3｜附录英文转换表与分级/诊断表

APP-2（已复核）：Strict v3 7,902；Relaxed 65,503（体素 +428,278 / −38,230）；Retile 79,298（+228,582 / −125）。用户选 C′ 时，此表可作为补充，不替代保留的图；选 A 时必须用英文表替代 image14/17/19。APP-3 承载 E-2 表与 E-4 分级表。

### G-5 / G-6｜术语与数字核对

`neighbour` → `neighbor`（美式；见 P2 G-4 可提前做）。统一 BrickMore / BrickMore-48、raw / retiled 等术语。逐项核对将写入正文的数字与源文件。页面影响约 +0–1 行。

### 从属 P1（不另计独立条，但须执行）

- **E-8**（§5.1，建议紧挨 L215 之前）：双方同意写 *“BrickGPT outputs were generated in its native $20^3$ world (seed 42), whereas BrickMore places bricks in a $48^3$ workspace, which partly explains the difference in part counts.”* 不写 `max_bricks=200`，不写 66/114 stable。U14 若选 B，详细记录值只进附录。
- **L-2 / L-3**：分别按 U3、U5 的结果更新 §6。U5 批准则删除 L265 “Paired uncertainty analysis can be conducted…” 并改为指向附录检验。
- **B-1**：三条已核文献原样进 `references.bib`。**B-2**（venue）：BrickNet 现写 CVPR 2026，若执行时无法独立核实则改为只写 arXiv。
- **M-4**（RB2 终审补回）：§4.2 末尾加半句 “Section~\ref{sec:diagnostics} reports how often each repair tier is reached.”（仅当 U12 批准；档位数字只在 E-2 和附录表中出现）。
- **APP-4**（RB2 终审补回）：附录 D 首句后加 “Where a value is superseded by a verified number in the main text (e.g., Table~\ref{tab:training-data} and Appendix~A), the main text takes precedence.”
- **APP-5**（RB2 终审补回）：附录 B 的训练语料构造细节（如 split seed）等 U3 确定后再决定是否写；不引用模型卡。
- **S-4**（RB2 终审补回）：V1.6 的 `README.md` 更新标题与编译方法，`REVIEW_V1.6.md` 记录各条目的执行结果。

## 2.3 P2（有余力再做；10 项）

| 项 | 位置 | 做什么 |
|---|---|---|
| G-4 | L94、L263 等 `six-neighbour` | 改为 `six-neighbor`（可并入 G-5） |
| G-7 | 编译日志 | 处理明显 Underfull，不改内容 |
| A-3 | 摘要等 | 保持 “GPT-6.1 Sol” 字面，全文一致 |
| I-5 | L60 结果预告末 | 可加 “The ordering holds at every description level from L1 to L5 (Appendix)。” 已核 15/15 格 BrickMore 最高 |
| R-3 | §2 首段 | 略压缩，给 R-1 腾行 |
| D-5 | §3.1 | “40 structural families per category” 仅在有文件依据时保留 |
| D-6 | §3.2 末句 | 语序微调 |
| D-7 | Table 1 / 附录 B | validation 与 test 命名脚注 |
| M-3 | Figure 3（L158–162） | 确认浮动位置；超页时按兜底移附录 |
| E-7 | L224、L244 | 表头 “VQA” 改为 “VQAScore”；Table 4 保留 0.1897% / 0.00% 精度 |

U14 选 B（双方共同推荐）时，在附录评测协议中加入以下句子（主文仍只用 E-8 短句；RB2 终审补了两个从句）：

```latex
BrickGPT outputs were generated in a $20^3$ world with seed 42. Run records report \texttt{max\_regen}=8 and \texttt{use\_gurobi}=\texttt{False} for all 114 prompts, which differ from the BrickGPT paper (up to 100 physics-aware rollbacks; the stability program in Eqn.~3 is solved with Gurobi) and from the official repository defaults (\texttt{max\_regenerations}=100, \texttt{use\_gurobi}=\texttt{True}), assuming \texttt{max\_regen} denotes the rollback limit \texttt{max\_regenerations}. With Gurobi disabled, the recorded stability flag reflects the repository's connectivity-based check rather than its physical-stability analysis. We therefore do not describe this run as using the authors' default configuration.
```

**明确不做：** 新空间推理基准；重训或模型消融；把 checklist 作为 OpenReview 附件；改 Algorithm 1 逻辑或把它改成 `figure*`；把 README L55 写入论文；写 `max_bricks=200` 或 66/114 stable；更新范围外的 `abstract_introduction.md`。

---

# 3. 页数预算

V1.5 正文在约第 6 页左栏结束（约 **5.5–6.0 页**），letter 纸，全 PDF 16 页。验收：第 7 页之后不能有正文；References 可从第 8 页起。

| 变化 | 条目 | 条件 | 估计 Δ（页） |
|---|---|---|---|
| 摘要压缩 | A-2 | 无【】时 | −0.05 |
| 摘要加 46/525 | A-2【】 | U12 且条目 5 选 Y | +0.02 |
| 引言去重 | I-2 | | −0.15 |
| 试验床句 + 预告段 | I-1 / I-3 | I-3【】依赖 U12 | +0.10 |
| 相关工作 3 篇 | R-1 / R-2 | | +0.12 |
| 转换效益 + 拆表 | D-1 / D-2 | | +0.08 |
| 五级描述短例 | D-4 | | +0.05 |
| 指标定义 | E-1 | | +0.03 |
| 选择效应披露 | E-9 | P0 | +0.05–0.08 |
| E-8 短句 | E-8 | | +0.02 |
| 诊断段（表在附录） | E-2 | **U12** | +0.20 |
| 分级别两句 | E-3 | 截断子集须先复算 | +0.06 |
| raw/retiled 解释 | E-6 | | +0.03 |
| Scope / 结论 | L-1 / C-1 | 【】依赖 U12 | +0.05 |
| 显著性正文句 | U5 | **U5** | +0.03 |
| U14 附录句 | U14 | 仅当选 B；正文 0 | 正文 0 |
| image18 处理 | U4-b | 附录；正文 0 | 正文 0 |
| **仅 P0**（E-1+E-9+E-8，不计标题折行） | | | **约 +0.10–0.13** → 正文约 **5.6–6.1** |
| **P0+P1，U12/U5 都不做** | | | 约 +0.35–0.40 → 约 **5.9–6.4** |
| **P0+P1，U12+U5 都做（表在附录，摘要无 46/525）** | | | 约 **+0.55–0.65** → 约 **6.1–6.6**，仍 ≤ 7 |
| **最坏**（U12+U5+摘要计数+诊断表放回正文+标题折行） | | | 约 +0.75–0.85 → 约 **6.3–6.9**，接近上限 |

**超页兜底（顺序固定，Algorithm 1 不改排、不移出）：**
1. 诊断表保持附录并压缩 E-2 段（若曾放回正文则先移回附录，约 −0.15）；
2. Figure 3 拼图（L158–162）移到附录（约 −0.35）；
3. Table 2 微调配置（L137–156）并入附录 B（约 −0.2）；
4. E-3 只留一句。

每批修改后按 G-1 实测，不用本表代替编译。

---

# 4. 时间线（从现在 2026-11-15 约 01:30 UTC+8 至 2026-11-20 19:59 UTC+8）

| 时间（UTC+8） | 任务 | 产出 |
|---|---|---|
| **11-15 14:00 前** | **用户拍板**第 1 节各项（至少先定标题、image18、U12、摘要数字、U5、U14）；**全体作者注册或确认 OpenReview profile**；开始在训练机找 U3 清单 | 决策清单；profile ID |
| 11-15 下午 | 复制 V1.5 → V1.6；执行无分歧的 P0（E-1、E-9、G-2 初查）与 I-2、A-2（按条目 5 的默认 N）、L-1 定性、G-4；`latexmk` 验收 | V1.6 第 1 版 PDF，正文 ≤ 7 页 |
| 11-16 | P1：D-1/D-2 结构、D-4、R-1/R-2、I-1/I-3/I-4、E-8、E-6、M-1；若 U12 批准则写 E-2（表在附录）与 E-3（先复算截断子集）；若 U5 批准则跑检验脚本（不预填） | 第 2 版；`significance.json`（若做） |
| 11-17 | 附录：U4 / U4-b 按用户选择、APP-2/3；本机 MiKTeX 试编；**24:00 为 U3 证据截止** | 第 3 版 |
| 11-18 | 按 U3 或 C′ 定稿 Table 1；G-5/G-6；页数终检；内容冻结 | 冻结稿 |
| **11-19** | 用户通读；**向 OpenReview 提交**（截止前仍可替换 PDF）；填 G-3 表单 | 提交编号 |
| 11-20 12:00 前 | 只改必要笔误或已确认数字；G-1/G-2 终检 | 终稿 PDF |
| **11-20 12:00–19:59** | **缓冲**：不再改内容，只处理上传或系统问题 | 在 19:59 前完成 |

主编译：box TinyTeX（pdfTeX + latexmk）。备份：本机 MiKTeX。Overleaf（pdfLaTeX）仅第三备选。

---

# 5. 匿名与投稿包清单

## 5.1 只上传这些

- 必须：编译后的 `main.pdf`（≤ 50 MB）。
- 若另传源码 zip，仅含：`main.tex`、`references.bib`、`aaai2027.sty`、`aaai2027.bst`、正文/附录实际引用的 `figures/` 与 `figure1.pdf` / `figure2.pdf`。
- 不要打包：`*.log`、`*.fls`、`*.fdb_latexmk`、`*.aux`、`*.blg`、`*.bak*`、`REVIEW_*.md`、`archive\`、`BrickMore_V1.*_LaTeX.zip`、`figure_data\provenance.json`、任何 `.jsonl`、模型卡、`downloads\`。

编译产物含 `/home/box/.TinyTeX` 与 `PWD /workspace/brickmore/V1.4`，不是作者名，但不应随稿上传。

## 5.2 已知仅存在于非投稿文件中的泄漏（禁止带入任何附件或匿名仓库）

- `D:\Users\15778\Desktop\论文\乐高论文\乐高模型\BrickGPT_Original\models\brickgpt_merged` — `brickgpt_generation_summary.jsonl` 的 `model` 字段。
- `E:\brick_train\collab_in\...` — `汇总交付\资料与记录\collab_verified.json`。
- `Kyle308666/BrickGPT-Qwen3-1.7B-BrickMore-48` — 同目录 `provenance.json` 及若干 `regen\*\generation.json`。
- `selected_manifest.jsonl` 的 `original_source` 为 `D:\BrickMore\...` 绝对路径。

## 5.3 对将上传的 PDF 执行（编译之后；本计划不代为执行修改）

```bash
pdftotext main.pdf - | grep -iE 'kyle308666|bushigemenn|15778|chinami|administrator|huggingface\.co/|github\.com/[A-Za-z0-9_.-]+/|C:\\Users\\|D:\\Users\\|E:\\brick|/home/box'
pdfinfo main.pdf
# Author/Title 必须为空；Creator/Producer 仅限 TeX / pdfTeX；纸张 letter
python3 - << 'PY'
import re
from pathlib import Path
data=Path('main.pdf').read_bytes()
blob=b'\n'.join(re.findall(rb'[\x20-\x7e]{6,}', data)).decode('ascii','ignore')
for p in [r'Kyle308666', r'BuShiGeMenn', r'15778', r'C:\\Users\\', r'D:\\Users\\', r'E:\\brick', r'/home/box', r'Author\s*\(', r'dc:creator']:
    ms=re.findall(p, blob, flags=re.I)
    print(p, len(ms), ms[:3])
PY
# 人工检查 Figure 1–3 与附录 image13–19 的图内文字
# 源码 zip：unzip -l brickmore_src.zip | grep -iE 'log|fls|fdb|bak|review|archive|provenance|\.jsonl'
```

`pdfinfo` 不应出现作者名。图片内小字易漏，须目视。

---

# 6. OpenReview 提醒

- 邀请页写明：**All authors must have an OpenReview profile prior to submitting a paper.**
- 请**今天（2026-11-15）**让全体作者注册或确认已有 profile。官方文档（docs.openreview.net，Signing up for OpenReview）写明，使用公共邮箱域名注册 **may take up to 2 weeks in moderation**。添加并验证机构邮箱通常更快。这是截稿前最大的非写作风险。
- 官网未写 “double-blind”。按 OpenReview 对 `authors` 字段的读者限制，审稿人看不到作者，因此 PDF 保持 `\usepackage[submission]{aaai2027}`，论文与表单都不写“官方双盲”。作者姓名只填表单。
- 建议 **11-19** 提交，为 11-20 19:59（UTC+8）留出缓冲。

---

*本文件只写入 `D:\BrickMore\Essay\BrickMore\Plan_V1.6\FINAL_PLAN_V1.6.md`。没有修改任何论文文件或既有计划/评审文件。*

---

# RB2 审阅记录

- 审阅人：ReviewBot2（RB2），2026-11-15 约 01:50（UTC+8）。
- 修改前已把原文件备份到 box 的 `/workspace/brickmore/plan/FINAL_PLAN_V1.6.orig.md`（39,370 字节，sha256 前缀 932496FAB549），据此做 diff。
- 只改本文件，没有改任何论文文件或其他计划/评审文件。

## 核对 1：RB2 的 P0/P1/P2 条目是否齐全、是否被改错

- **P0（7）**：G-1、G-2、G-3、E-1、E-9、S-2、S-3 全部在 §2.1，内容无误。E-9 的位置由 L216 改为 **L215**，已核对 `V1.5\main.tex`：L215 是 “The systems differ…”，L217 是 `\subsection{Main Results}`。RB1 正确。
- **P1（21）**：A-2、I-1、I-2、I-3、I-4、R-1、R-2、D-1、D-2、D-4、M-1、E-2、E-3、E-4、E-6、L-1、C-1、APP-2、APP-3、G-5、G-6 全部在。所做调整都可以接受：
  - E-3 把未截断子集的数字改为 `[recompute]`，比原计划更保守；
  - D-2 增加删除 L121–125 源码注释，属于匿名改进；
  - E-2 采用 RB1 的统一候选池句（“together with 105 first-batch prompts … 45 … (35 of them from the 525)”），与文件一致。
- **P2（10）**：G-4、G-7、A-3、I-5、R-3、D-5、D-6、D-7、M-3、E-7 全部在。
- **遗漏（已补回）**：四条引用型条目 M-4、APP-4、APP-5、S-4 在合并时漏掉了。它们不计入 51 条，但需要执行，已补进 §2.2「从属 P1」。
- 条目总数仍是 P0 7 / P1 21 / P2 10 = 38 条独立修改，另有用户项。

## 核对 2：E-9 的 45/35/34 拆分与 U14 措辞

- **拆分复算**（`selected_manifest.jsonl` BrickMore `primary=True` 114 条，对照 `汇总交付\资料与记录\best_all.json` 105 组的 `choice_id`）：
  - **45** = `source_kind=judged`，即人工判决的获胜者被直接采用，占 45 组。其中 35 条是 525 批的 V 系列（这就是 R3/R4 所说的“与 525 重叠 35”），10 条是首批；
  - **35** = 所在组**有**判决获胜者，但交付的是其他来源的输出，即“替换已有获胜者”，涉及 **34 组**。来源分布：成功的模型 14、round2 7、nine_ldr 6、regenerated 5、review_59 2、car_trials 1；
  - **34** = 所在组判为“全部不合格”后补入的输出，涉及 **26 组**。来源分布：review_59 19、round3 7、round2 5、成功的模型 2、nine_ldr 1；
  - 合计 45 + 35 + 34 = 114；组数 45 + 34 + 26 = 105，即 114 条覆盖全部 105 组；多出的 9 条是同组多提示（piano L3、pot L3/L4/L5 各 +1，sofa L4 +3、sofa L5 +2）。
  - 有 **34** 个获胜者 `choice_id` 没有进入 114。
  - **“34” 在文中有两个含义**：被替换的获胜组数（34 组，对应 35 条输出），以及全不合格组补入的条数（34 条，对应 26 组）。两者都正确，§1 条目 10 和 §2.1 E-9 的写法都准确。
  - R3/R4 的 “其余 69” = 35 + 34，与之不矛盾。RB1 的拆分更细，也更准确（69 条中约一半是替换，不是补缺），RB2 接受。
  - 35 条与 525 的重叠全部在 judged 的 45 条之内，与“35 条替换”是两组不同的条目，不要混淆。
- **E-9 LaTeX**：数字全部与上面一致。脚注中的分来源计数（review_59 21、成功的模型 16、round2 12、round3 7、nine_ldr 7、regenerated 5、car_trials 1）与 `source_kind` 一致。“BrickNet contributed one accepted sample per prompt (up to 30 attempts)” 来自 `BrickGPT\总结_AB对照_20261109.md` L5。**未修改。**
- **U14**：
  - 项目记录（`brickgpt_generation_summary.jsonl`）复核：`n_regenerations` 最大 8；有 50 条达到 8，其中 48 条 `stable=False`；
  - RB2 本轮亲自读取官方仓库 `https://raw.githubusercontent.com/AvaLovelace1/BrickGPT/main/src/brickgpt/models/brickgpt.py`（416 行）：
    - L32–36：`max_bricks` 默认 2000；
    - L50–56：`max_regenerations` 默认 100；
    - L57–62：`use_gurobi` 默认 True；
    - L359–360：`_is_stable` 在 False 时调用 `is_connected()`。
    
    RB1 的转述准确。
  - 措辞修改：建议句补了两处。(a) “assuming `max_regen` denotes … `max_regenerations`”，因为字段名不同，对应关系是推断；(b) 说明 Gurobi 关闭后，记录中的 stable 标记是连通性检查。
  - 附注（不进论文）：官方 L186 中 `for brick_num in range(self.max_bricks)` 是每一轮生成的上限，rollback 后会从保留的砖继续生成，所以总砖数可以超过 `max_bricks`。这与“36 条超过 200 且都有 regeneration”相容，但项目文件仍不能证明这一点，维持不写 `max_bricks=200`。

## 核对 3：三项分歧上的 RB2 立场

- `PLAN_RB2_R4.md` 确实写的是：摘要在 U12 批准后放一处计数 “46 of 525 …”（Y，采纳 RB1 R3）。`CRITIQUE_RB1_R4.md` N4 写的是 N（采纳 RB2 R3）。RB1 说“两边对调”属实，原 FINAL 条目 5 的描述也准确。
- RB2 的最终立场：
  1. **image18**：维持 **R**（移出整图，或至少删 (a)）。新增理由：红柱的 `stable=true` 在 `use_gurobi=False` 下只是连通性检查。若用户选 K，图注必须用条目 3 的修订版。仍是**唯一的未消除分歧**，交用户定。
  2. **“46 of 525” 进摘要**：改为支持 **N**，与 RB1 R4 一致，分歧消除。理由见条目 5。
  3. **U14 披露**：改为支持 **B**（附录如实写记录值，并注明与论文及官方默认不同），与 RB1 一致，分歧消除。理由是官方源码已证实 `use_gurobi=False` 会把稳定性判据换成连通性，这与公平性直接相关。

## 本次修改清单

1. 文首「未消除的分歧」由 3 项改为 1 项（image18），并注明 2 项已由 RB2 终审消除。
2. 条目 3（image18）：K 方案图注加 “run-log `stable` flag (a connectivity check, since Gurobi was disabled)”；RB2 理由补第 (4) 点。
3. 条目 5：标题改为“已消除”；RB2 立场改为“终审支持 N”并给出理由；默认执行写法相应调整。
4. 条目 9（U14）：标题改为“已消除（RB2 终审改为支持 B）”；RB2 立场改写，附官方源码行号；“未圈定前”的默认动作改为“附录句可写，`max_bricks=200` 仍不写”。
5. §2.2 A-2：摘要中的【】由计数句改为定性半句，并改写条件说明（U12 批准才保留；用户要求 Y 时可换回计数句）。
6. §2.3 U14 附录 LaTeX：补 “assuming \texttt{max\_regen} denotes …” 和 “With Gurobi disabled, the recorded stability flag reflects …” 两个从句；引导语注明双方共同推荐。
7. §2.2「从属 P1」：补回 M-4、APP-4、APP-5、S-4。

除以上 7 处和本节外，原文未改动。§3 页数预算中 “摘要加 46/525” 一行保留，作为用户选 Y 时的参考。

*本节由 RB2 追加。只修改了 `D:\BrickMore\Essay\BrickMore\Plan_V1.6\FINAL_PLAN_V1.6.md`，没有修改任何论文文件。*
