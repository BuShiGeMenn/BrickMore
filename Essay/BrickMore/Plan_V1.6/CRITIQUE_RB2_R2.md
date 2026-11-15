# 交叉评审第 2 轮（RB2 · R2）

- 读取文件：`D:\BrickMore\Essay\BrickMore\Plan_V1.6\CRITIQUE_RB1_R1.md`（14,220 字节）与 `PLAN_RB1_R1.md`（32,186 字节），均为 2026-11-15 00:53（UTC+8）版本。
- 本轮新增核查（2026-11-15 约 00:58–01:06，UTC+8）：
  - 逐张查看 V1.5 附录 image13–19，并与发布报告核对图中数字；
  - 核对 114 条主对比与 525 条诊断提示词的重叠；
  - 核对 manifest 的 `attempt`、`regen_seed`、`raw_single_component` 字段；
  - 逐字摘录 gsr-vlm.org 与 AAAI-27 Author Kit 的相关原文；
  - 在 arxiv.org 摘要页核对三篇新文献的完整作者名单。
- **只做计划与评审，未修改任何论文文件。** 只写入本文件与 `PLAN_RB2_R2.md`。

## 统计

| 部分 | 结果 |
|---|---|
| Part 1：回应 RB1 对 RB2 的 15 条意见（C1–C15） | **接受 12 条，部分接受 3 条，反驳 0 条** |
| Part 2：对 `PLAN_RB1_R1.md` 的新意见 | **10 条**（N1–N10） |

---

# Part 1　逐条回应 RB1 的 15 条意见

### C1｜U2 “实际流程是双盲” 说得过满 —— **接受**
OpenReview 能直接证明的只是：`authors` 和 `pdf` 字段的 readers 仅限 `AAAI.org/2027/Workshop/GSR-VLM` 与 `Submission{n}/Authors`；gsr-vlm.org 没有 double-blind 字样。R2 把 U2 的结论改为：“按 OpenReview 对 authors 字段的读者限制，审稿人看不到作者，PDF 保持 `[submission]` 匿名。” 论文与表单中都不写“工作坊官方宣布双盲”。

### C2｜U3 选项措辞，以及 “2.227B 与 2,228,044,818 自洽” —— **部分接受**
- **接受**：R0 写的“自洽”不准确。精确乘积是 24,448 × 25.3 × 3,600 = 2,226,723,840，与表中数字差 1,320,978。这只能用“25.3 h 是约数”来解释，不能算同一观测。R2 改为“量级一致，不可替代表中数字”。
- **不接受**“暗示应删掉 79,301”的解读：R0 的选项 B、C 都没有提议删除 79,301（R0 U3 原文：B 是“about 396.6k samples…不推荐”，C 是“维持现状…不推荐”）。R1 已新增兜底选项 C′，在拆表的同时保留 79,301。所以双方在实施层面已经一致。

### C3｜在用户拿出训练清单前不要删改 79,301 —— **接受**
与 R1 的选项 C′ 一致，R2 维持不变。

### C4｜中文历史图：默认删除过于激进 —— **部分接受**（关键分歧 a，论证见下文 §K-a）
接受两点：用户未答复时的**默认动作**是保留；任何删除都必须用户同意。但给用户的**推荐**仍是移除，并新增证据：image18(a) 依赖无法复核的人工判决数据。

### C5｜不要把 Overleaf 排除出应急路径 —— **接受**
R1 已把 Overleaf（pdfLaTeX）列为第三备选。R1 也已撤回 R0 “Overleaf 免费版可能超时”的说法：box 上实测 V1.4 `latexmk` 全流程 3.6 s，单次 pdflatex 0.8 s，低于免费版 10 s 上限（docs.overleaf.com plan limits）。

### C6｜A-2（摘要重写）与 L-1（Scope 改写）不应是 P0 —— **接受**（关键分歧 b 的一部分，见 §K-b）
V1.5 `main.tex` §6 的 Scope 句已经写明没有预训练、没有 RL、生成器不是 VLM。改写属于提升，不属于合规要求。R2 把 A-2、L-1 改为 P1：P0 从 9 条降为 7 条，P1 从 19 条增为 21 条。

### C7｜诊断数字在摘要、引言、贡献、结论中重复 —— **部分接受**
- **接受**：数字只在 §5.x 展开一次；引言、贡献、结论只写定性指向，不再出现 8.8% 或中位数 5。
- **保留**：摘要可以有**一处**数字，即 “46 of 525 raw outputs form a single stud-connected component”。理由：
  1. 这是本文唯一直接回答 Topic 5 “学到了什么”的量化结果，审稿人通常先读摘要；
  2. 只多约 1 行（摘要单栏宽度），不影响 7 页预算；
  3. 仍受 U12（用户批准）约束。

  这一点列为“仍有分歧”第 2 项，由用户或作者决定，影响很小。

### C8｜525 条不能写成 “additional prompts” —— **接受，并补充本轮新数据**
- 本轮核对：114 条主对比中，BrickMore primary 输出的 caption 有 **35 条**与 `brickmore48_eval_630\manifests\manifest_w{0,1,2}.json` 的 `prompt` 字段逐字一致（`scores.csv` 的 `caption` 列）。这 35 条的 model_id 都是 `LxVy` 形式，例如 `basket-L1V5`。其余 79 条的 model_id 后缀大多是 `-C1`、`-R0`、`-A`、`-Q0` 等其他来源。
- 所以 525 条与 114 条是**部分重叠**的，“additional” 不成立。
- R2 改为 “525 prompts from a separate diagnostic run (21 categories × 5 levels × 5 phrasings), 35 of which also appear among the 114 comparison prompts”。是否写出重叠数，列入 U12 由用户确认。

### C9｜不得写 “reproduces voxel-level shape well” —— **接受**
R0 已在注意事项中说明此句不能写，但示例段落里仍保留着它，有被误用的风险。R2 已从 A-2、C-1 的示例中删除，只留保守版。“voxel-connected in most cases” 在统计 `raw_report.json` 的 `voxel_components` 之前同样不写。

### C10｜SigLIP2 定义不写 “learned scale and bias” —— **接受**
项目脚本 `evaluate_paper_images.py` L99 只有 `logits_per_image[:,0].float().sigmoid()`。scale 和 bias 属于 transformers 库内部实现，本轮在用户机器的 Python 目录与 `D:\BrickMore` 下没有找到 `modeling_siglip2.py`，无法用项目文件证明。R2 只写 “sigmoid of the image–text logit”。

### C11｜“References 标题必须在第 7 页或更早” 偏严 —— **接受**（关键分歧 c，原文见 §K-c）

### C12｜不以 Algorithm 1 改排 `figure*` 作为兜底；页数预算偏乐观 —— **接受**（关键分歧 c，原文见 §K-c）
R2 删除这一兜底项。新的超页兜底顺序：
1. E-2 诊断表移到附录，正文只留一段；
2. Figure 3 移到附录；
3. Table 2 并入附录 B；
4. E-3 只留一句。

### C13｜L-1 中的 “connectivity-based rewards” 可能被误读为 RL —— **接受**
R2 删去 “rewards”，改为 “connectivity-aware decoding is a natural direction outside the scope of this work”。摘要和贡献中不出现 reward 或 RL。

### C14｜TLDR 中不用 “79k” —— **接受**
G-3 的 TLDR 改为：“We fine-tune a 1.7B language model on agentically generated, geometrically checked brick layouts and diagnose which spatial constraints it learns before MILP retiling enforces stud connectivity.”

### C15｜三篇新文献作者名单不完整 —— **接受**
本轮在 arxiv.org 摘要页（`citation_author` 元数据）核对了全部作者：
- arXiv:2311.15475 MeshGPT：Siddiqui, Alliegro, Artemov, Tommasi, Sirigatti, Rosov, **Dai, Nießner**（共 8 人）；
- arXiv:2411.09595 LLaMA-Mesh：Wang Z., Lorraine, Wang Y., Su, Zhu, Fidler, **Zeng**（共 7 人）；
- arXiv:2401.12168 SpatialVLM：Chen, Xu, Kirmani, Ichter, Driess, Florence, **Sadigh, Guibas, Xia**（共 9 人）。

R2 的 bib 已补全。三篇的 comments 字段都没有会议录用信息，venue 仍只写 arXiv。

---

## 三个关键分歧的论证

### §K-a　中文历史图：默认保留，还是移除？
**结论：部分接受。**
- 用户未答复时，默认动作是保留，与 RB1 一致。
- 给用户的推荐（★）仍是从提交 PDF 移除 image13–19，并用英文表格替代其中可以核实的数字。
- **image18 列为必须单独请用户确认的项**，因为它含有无法复核的数据。

证据：
1. **规则来源**：`D:\BrickMore\Essay\BrickMore\V1.5\REVIEW_V1.5.md` 第 6 行原文：“本轮不做（标「待用户确认」）：……删除或重绘含中文的历史图……”；`V1.4\REVIEW_V1.4.md` 第 101 行原文：“N24【待用户确认】……删除属于删内容，需要用户同意。目前保留在附录。” 所以“未经同意不删”是实际规则，RB1 说得对。
2. **逐图核对**（V1.5 `figures\image13–19.png` 与项目文件对照）：

| 图 | 内容（中文标注） | 图中数字能否从项目文件复核 |
|---|---|---|
| image13 | 接触重力筛查示意图（“顶层积木 / 底层积木 / 地面接触…”） | 示意图，无统计数字 |
| image14 | (a) 7,902 / 65,503 / 79,298 / 79,301；(b) 2,650 / 478、220 / 128 | **能**：79,298、220、128 在 `Train\datasets\retile_assembly_80000\summary.json`；65,503、2,650、478、7,902 在 `Train\datasets\relaxed_assembly_80000\assembly_summary.json`；79,301 在 `CURRENT_DATASET_STATUS.md`。图注写的 “require verification” 已经过时 |
| image15 | 21 类的几何通过率（三种策略） | 本轮未逐类复核 |
| image16 | 160 个模型均匀抽样，22 / 55 / 56 / 57 | 本轮未找到来源文件，**不能**复核 |
| image17 | 物理筛查状态：retile 63,808 / 14,574；relaxed 2,650 / 45,490 / 17,024 / 14,497 | **能**：分别出现在 retile `summary.json` 与 relaxed `assembly_summary.json` |
| image18 | (a) 分级通过比例：BrickGPT “stable=true” 对比 BrickMore-48 “**人工判定有合格模型的组**”；(b)(c) 零件规模 | (a) 红柱能复核（`brickgpt_generation_summary.jsonl` 各级 stable：13/21、15/21、12/23、12/25、14/24）。**蓝柱来自人工判决，而 `brickmore48_eval_630\results\best_all.json` 和 `best_all.md` 都不存在，无法复核**；图题自己也写着“判据不同” |
| image19 | (a) BrickGPT 拒绝原因 8,207 / 2,757 / 8 / 4；(b) BrickNet 失败类型 24 / 10 / 10 / 6 / 3 | **能**：(a) 是 jsonl 中 `rejection_reasons` 的合计；(b) 见 `Provenance\bricknet_generation_summary.md` |

3. **据此推理**：
   - 双方已经同意“不使用无法从原始文件复算的数字”（RB1 R1 §0.5：“README 中无法由这些字段复算的数字一律不用”；RB2 §4）。image18(a) 的蓝柱正是 RB1 自己拒绝的“79/105 人工判决”同一来源，而且是不同判据下的对比，对 BrickMore 有利。RB1 “保持现状”的默认方案会把这个不可复核的数字留在提交 PDF 里，与双方共同的规则冲突。
   - 反过来，image14、17、19 的数字都能复核，所以 R0 用“图中数字可能不一致”作为删除理由，对这三张图不成立。R2 修正：删除理由只保留“英文稿中的中文标注”，以及“英文表格可以无损替代”。
4. **R2 的 U4 方案**：
   - 未答复时：保留，但把 image14、17、19 图注中的 “require verification” 改为指向对应的发布报告；
   - ★推荐：移除 image13–19，用英文表 APP-2 替代 14、17，用英文表替代 19；
   - **image18 单独确认**：推荐至少移除 image18，或删去其 (a) 栏。

### §K-b　525 条诊断：P0，还是有条件的 P1？
**结论：接受 RB1 的“有条件 P1”。** 同时主张把“是否批准 U12”这一**决策**排在用户决策清单的第一位，并把 E-2 设为 P1 中最先执行的一项。

证据：
1. 写入论文要先满足两个用户决策：U10（权重版本：`brickmore48_eval_630\README.md` 第 5 行写“权重版本 `92d1c595`”，而 `downloads\…\model.sha256` 的前缀是 `75f79af1…`，无法对上）和 U12。这两项由用户决定，执行条目不能被列为“无论如何必须完成”的 P0。这一点 RB1 是对的。
2. 本轮又发现一个需要用户说明的协议差异，进一步说明它只能是有条件的：
   - README 第 55 行：“种子阶梯 42 → 104 → 2026（**前一个种子产出不合格且不可修复时**启用下一个）”；
   - V1.5 `main.tex` 第 166 行和 Algorithm 1：先依次试种子，直到出现 complete 且 valid 的候选，**再**做 MILP 修复；
   - manifest 的 `attempt` 字段：@42 338 条、@104 134 条、@2026 53 条；另有 28 条带 `regen_seed`（种子 7、555、2027、12，都在 S 之外，也就是论文所说的 recovery path）。

   所以 525 条并非全部按 Algorithm 1 的默认流程产生。R0 的 E-2 写 “generated with the default protocol of Algorithm 1” 不准确，R2 已改。两种种子触发规则哪一个是实际运行的，需要用户确认（新增 U13）。
3. 但它的价值仍是 P1 中最高的。理由：Topic 5 原文是 “Pretraining, fine-tuning, reinforcement learning, and data generation for improving geometric and spatial reasoning”（https://gsr-vlm.org/）；而 V1.5 正文没有任何 raw 输出几何连通性的统计（在 `main.tex` 中检索 “525”、“8.8”、“single stud” 都没有结果）。
4. 有利的一面：`none_needed` 与 `raw_single_component=True` **逐条一一对应**，都是 46 条；其余 479 条全部是 `False`，并全部进入 MILP 档位。这些数字内部一致，可以放心使用。

### §K-c　“References 必须从第 7 页或更早开始”，以及把 Algorithm 1 改排为 `figure*`
**结论：两点都接受 RB1。**

逐字原文：
1. **GSR-VLM**（https://gsr-vlm.org/ ，Call for papers 部分，2026-11-15 读取）：
   > “Long papers Up to 7 pages of main content, with no page limit for references and appendices.”

   以及 Important dates 部分：
   > “Submissions must use the AAAI-27 template. Workshop page limits are listed above.”

   网站没有其他关于 References 起始页的要求。所以规则是“正文 ≤ 7 页”，References 可以从第 8 页开始。R0 G-1 第 3 步 “References 所在页 ≤ 7” 比规则更严，R2 已改为“第 7 页之后没有正文（摘要到结论）”。
2. **AAAI-27 Author Kit**（https://aaai.org/authorkit27/ ，本地副本 `/workspace/brickmore/AuthorKit27/AnonymousSubmission2027.tex`，SHA-256 前缀 `95a9e0ee566c6f76`）：
   - 第 391 行：“For your final camera ready copy, you must not use any page break commands. References must flow directly after the text without breaks. Note that some conferences require references to be on a separate page during the review process. AAAI Press, however, does not require this condition for the final paper.”

     所以 References 紧接正文，不用分页命令。正文在第 7 页结束时，References 自然出现在第 7 页末或第 8 页开头，两者都合规。
   - 第 548 行：“The references section should be labeled ‘References’ and must appear at the very end of the paper (don’t end the paper with references, and then put a figure by itself on the last page).”
   - 第 186 行：“…depending on the conference you may be allowed to submit a supplementary technical appendix after the references…”

     结合 GSR-VLM 的 “no page limit for references and appendices”，V1.5 把附录放在 References 之后是可以的。
   - 第 617 行（Algorithms）：“Algorithms and/or programs are a special kind of figures. Like all illustrations, they should appear floated to the top (preferably) or bottom of the page. However, their caption should appear in the header, left-justified and enclosed between horizontal lines, as shown in Algorithm~\ref{alg:algorithm}. The algorithm body should be terminated with another horizontal line.”

     改成 `figure*` 会让图注按 figure 样式排在下方，不再是 “in the header … enclosed between horizontal lines”，违反这一条。
   - 第 220 行：“You must not make any changes to the aaai style file, nor use any commands, packages, style files, or macros within your own paper that alter that design, including, but not limited to spacing, floats, …”

   再加上 `REVIEW_V1.5.md` 第 6 行原文 “Algorithm 1 保留在正文，不移入附录”，R2 删除 “Algorithm 1 改为 `figure*`” 这一兜底项。

---

# Part 2　对 PLAN_RB1_R1.md 的新意见（10 条）

### N1｜C9.1、F #10、D 表 “写入 BrickGPT world_dim / 66 stable” 行、§0.4：仍写 `max_bricks=200` 和 66/114 stable
RB1 R1 的 Changelog 写着“E-8…吸收”，但吸收的是 R0 版本的 E-8，RB2 在 R1 中已撤回这一版。证据：`Provenance\brickgpt_generation_summary.jsonl` 中，`brick_count` 大于 200 的有 36/114（最大 497）；全部 114 条 `use_gurobi=False`；而 BrickMore 没有对应的稳定性评测。**建议**：只写 “native $20^3$ world (seed 42)”（见 CRITIQUE_RB2_R1 A-1、A-2）。

### N2｜A3 第 2、3 点，F #3、#4：脚注 “模型卡写作 79,322 × 5” 和 “仓库未见 `trainer_state.json`”
- 提到模型卡等于指向公开的 HuggingFace 仓库 `Kyle308666/…`，有匿名风险。RB1 自己在 §0.6 也把 Kyle308666 列为匿名泄漏源。
- 在论文里写“日志缺失”，是把内部的口径问题自曝给审稿人。
- **建议**：采用 RB2 U3 选项 C′ 的中性表注，不提模型卡、不提日志。

### N3｜C2.1：仍把 “geometric reasoning and object assembly” 定为 “更早 Topic 2 框句”
Topic 5 原文含 “for improving geometric and spatial reasoning”（gsr-vlm.org）。这不影响 RB1 R1 C2.2 新增的试验床句，但 C2.1 的定性有误，执行者可能因此删掉 Topic 5 用词。**建议**：改为“Topic 5 用词，保留”。

### N4｜A8 “理由”：“RB2 关于……附录图导致 Overleaf 超时的提醒成立”
RB2 已用实测撤回这一点（box 上 3.6 s，低于 10 s）。RB1 引用的是一个不成立的理由。结论（box 为主、Overleaf 备份）不受影响，只需改理由。

### N5｜A9 第 1 点、F #21：checklist “作为附加文件”
OpenReview Submission invitation 只有 title、authors、paper_type、keywords、TLDR、abstract、pdf、email_sharing、data_release 九个字段，没有附加文件字段。**建议**：如果要附，只能放进 PDF 附录。

### N6｜C9.5 建议稿：“after the same retile procedure used in the main pipeline, all 525 assemblies were stud-connected”
- 证据：manifest 显示，28 条用了 S 之外的种子（`regen_seed` 为 7、555、2027、12），2 条用到 600 s 档。论文 L166 把这两种情况都定义为 “recovery path … not part of the default loop”。
- 另外，README 第 55 行的种子阶梯触发条件与 Algorithm 1 不同（见 §K-b）。
- “the same procedure” 会让审稿人以为全部 525 条都走默认流程。**建议**改为：“with the default ladder for 495 prompts and the recovery path (seeds outside $S$; 600 s tier) for the remainder, all 525 final assemblies form a single stud-connected component.” 其中 495 = 525 − 28 − 2。本轮已复核两组不重叠：2 条 600 s 都没有 `regen_seed`；28 条重新生成的样本最终分别落在 12 s（9 条）、60 s（14 条）、180 s（4 条）、none_needed（1 条）。

### N7｜C9.5 建议稿：没有说明 525 条与 114 条的关系
本轮核对发现 35/114 的 caption 与 525 条逐字重叠（见 C8 回应）。RB1 写的 “from the `brickmore48_eval_630` diagnostic set” 措辞安全，但审稿人会问它与主对比是什么关系。**建议**：加半句 “partly overlapping the comparison prompts”，具体重叠数由用户确认后再写。

### N8｜A4、C12.1：保留全部历史图（包括 image18），与 RB1 自己的 §0.5 规则冲突
image18(a) 的蓝柱是人工判决结果，`best_all.json` 和 `best_all.md` 都不存在，属于 RB1 §0.5 所说“无法复算……一律不用”的同一来源（见 §K-a 表）。**建议**：即使默认保留其他图，image18 也要单独请用户确认，并推荐移除或删去 (a) 栏。

### N9｜A7 替换句、§0.3：仍只写 SigLIP2 的 64 token，缺 PE 的 72 token 和“8 视角取最大”的聚合说明；行号仍按 pipeline 副本
- `Evaluation\pipeline\evaluate_paper_images.py` 的 SHA-256 前缀是 `afec56ebdfd7`，与 `comparison_full\*.config.json` 记录的 `a90e851a6a01…`（Deploy 副本）不一致。计算逻辑相同，但证据链应引用哈希一致的 Deploy 副本。
- PE 的 72 token 来源：`comparison_full\pe.model.json`。

### N10｜B 页数预算、F #1–#9：P0 仍包含约束性条目；T5 的预算建立在 N1 的内容上
- F #6 “Algorithm 1 留在正文” 和 #7 “不改主表” 是约束，不是任务（CRITIQUE_RB2_R1 B-1）。
- T5 按 +0.10–0.15 页估算，前提是写入 `max_bricks` 和 66/114；按 N1 删减后只剩半句，约 +0.02 页。
- RB1 自己的预算在加入 T6 后到 6.85 页，超过它自定的 6.6 安全线，但没有给出明确取舍。**建议**：采用 R2 的兜底顺序（诊断表 → Figure 3 → Table 2 → E-3），并把 T5 下调。

---

*本文件只写入 `D:\BrickMore\Essay\BrickMore\Plan_V1.6\CRITIQUE_RB2_R2.md`。未修改任何论文文件（V1.x 目录），也未修改任何既有计划或评审文件。*
