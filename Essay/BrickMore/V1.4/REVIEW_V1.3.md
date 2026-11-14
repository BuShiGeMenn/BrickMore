# BrickMore V1.3 审稿与修订记录

- 工作目录：`D:\BrickMore\Essay\BrickMore\V1.3`
- 源副本：由 `D:\BrickMore\Essay\BrickMore\V1.2` 完整复制而来（149 个文件）。本轮未修改 V1.2。
- 评审基准：在先前项目交叉核对的基础上，按顶会写作标准检查，并以 [GSR-VLM](https://gsr-vlm.org/)（AAAI-27 workshop，Geometric & Spatial Reasoning in Vision-Language Models）的征稿与投稿要求核对应性。主题对齐**仅针对 Topic 5**（见下文「GSR-VLM 契合度」）。
- 编译：`D:\BrickMore\tmp\v12_build\tectonic\tectonic.exe`（Tectonic 0.17.0），成功生成 `V1.3\main.pdf`。
- 约束：未改标题与作者；未改核心论断或实验数据；未重写对比实验节；未虚构数字；保留 396,610 与 BrickGPT 配方表的 TODO；数据生成仍表述为 GPT-6.1 Sol 撰写程序的 agentic batch generation。

## 论文卖点与贡献（简要）

BrickMore 是一个 text-to-brick 框架，把**数据生成、语言模型微调与生成后几何修复**串成可审计的空间布局学习流程：

1. **数据生成（对应 Topic 5 的 data generation）**：用 GPT-6.1 Sol 以 agentic batch generation 撰写参数化生成程序，批量产生 80,000 个、覆盖 21 类物体的 $48^3$ 体素模型，每模型 5 条双语、不同详细程度的描述，共 400,000 条记录；经同色铺砖、连通分析、局部桥接与重铺后，最新整合版本中 79,301 个模型通过指定几何检查。
2. **体素到积木的几何约束目标**：训练目标强调钉柱连通的装配，而不仅是体素六邻接；并记录派生目标中对源体素的有限修改。
3. **微调（对应 Topic 5 的 fine-tuning）**：仅用英文描述（`captionEn`）对 Qwen3-1.7B 做 LoRA 微调，以固定空间序列化学习从文本到积木尺寸与位置的映射；训练过程（步数、最优校验损失、`load_best_model_at_end` 等）有文档记录。
4. **生成后约束**：由合法放置形成体素并集，用 MILP 求 exact cover，并检查单一钉柱连通分量；推理与超时阶梯在 Algorithm 1 中给出。
5. **评测（需按边界解读）**：在 114 条共享提示上，所提供的 BrickMore 输出在三项文本–图像指标上均值最高，且平均非法放置率 $P_{\mathrm{inv}}$ 为 0.00%，与 BrickGPT 持平。论文已说明这是指定协议下的“provided outputs”，不单独证明物理稳定性或可装配性。

本轮在摘要、引言、贡献与结论中，用文中已有事实补了一句 **Topic 5** 框架：把上述流程表述为学习并约束积木装配的**空间表示**，而不是新做预训练或强化学习实验。

---

## GSR-VLM 征稿要求核对

来源：[https://gsr-vlm.org/](https://gsr-vlm.org/)（本轮读取官方页面，2026-11-14）。页脚仍写 “Proposed AAAI-27 workshop · Details subject to confirmation”。官网未另设详细 CFP 子页。

| 项目 | 官网要求 | V1.3 现状 | 处理 |
|---|---|---|---|
| 会议 | AAAI-27 配套全天工作坊，蒙特利尔；工作坊日期待公布；主会 2027-02-16–23 | 稿件仍写 `\confName{CVPR}` / `\confYear{2026}`，并使用 `cvpr.sty` | 「待用户确认」更换模板与页眉，未改 |
| 存档 | **non-archival**（非存档） | 不影响当前正文内容 | 投稿时按非存档理解即可 |
| 长文 | 正文最多 **7 页**，参考文献与附录不限页 | 当前 PDF **14 页**（日志 `[1]`–`[14]`；附录历史表约第 13–14 页）。即便不计附录，正文已明显超过 7 页 | 「待用户确认」删减，未自行删节 |
| 短文/立场论文 | 正文最多 4 页，参考文献最多 2 页 | 同样超长 | 若改投短文需更大幅度压缩，「待用户确认」 |
| 已发表工作 | 仅展示，另有提交流程（尚未在官网页写明） | 本稿为工作稿，不按“已发表再投展示”处理 | 无需本轮操作 |
| 模板 | **必须使用 AAAI-27 模板**，官网链到 [https://aaai.org/authorkit27/](https://aaai.org/authorkit27/)（重定向至 AuthorKit27.zip） | 使用 CVPR 2026 `cvpr.sty` + `\twocolumn` 标题区 | 「待用户确认」迁移，未改 |
| 投稿系统 | OpenReview：[AAAI.org/2027/Workshop/GSR-VLM](https://openreview.net/group?id=AAAI.org/2027/Workshop/GSR-VLM) | 未提交 | 不在本轮范围 |
| 截止日期 | 一律 AoE（UTC−12）：开放 2026-10-12；截止 **2026-11-19**；通知 2026-12-01 | 距离截止已很近（截止约合用户时区 UTC+8 的 **2026-11-20 19:59**） | 仅提示，不改正文 |
| 匿名/双盲 | **工作坊官网页未写明**是否双盲。AAAI-27 主会投稿为匿名双盲，官方模板有 `[submission]` 匿名模式，但不宜直接等同为工作坊政策 | 作者栏为占位 “Authors and affiliations to be added”，`\paperID{*****}`；标题未改 | 「待用户确认」向组委会/OpenReview 核实后再填作者或改为匿名格式，本轮不改标题与作者 |

官方页也未写明 reproducibility checklist 是否为工作坊硬性要求（那是 AAAI-27 主会说明）。随模板迁移一并确认，列为「待用户确认」。

---

## GSR-VLM 契合度（仅 Topic 5）

**Topic 5：Learning spatial representations — Pretraining, fine-tuning, reinforcement learning, and data generation for improving geometric and spatial reasoning.**

本稿与 Topic 5 的自然契合点是 **data generation + fine-tuning**，而不是 pretraining 或 RL。本轮**没有、也不会**宣称做过预训练或强化学习实验。

### 已有内容如何对应 Topic 5

- **数据生成如何服务于空间表示学习**：agentic batch generation 产生参数化程序，从而在 $48^3$ 世界里得到大规模、可复现的几何目标；五级（不同详细程度）双语描述提供多粒度的语言条件；转换管线把体素覆盖变成积木放置，并用几何检查筛出 79,301 个可用模型。这些是“用数据学习空间布局”的语料，而不是语言模型直接输出体素坐标。
- **微调如何学习该表示**：Qwen3-1.7B + LoRA 在英文描述与积木放置序列上训练；固定空间序列化（训练节所述：Y 优先再 X）把三维布局写成可学习的离散序列；输出为尺寸与位置（不含颜色）。
- **几何约束如何进入学习与推理**：数据集校验与生成后重铺把覆盖、重叠和钉柱连通变成可检查的约束；MILP exact cover 与单一钉柱连通检查用于修复预测布局。20 种积木库（相对 BrickGPT 的 14 种，见训练节配方表；表中 BrickGPT 数字仍有 TODO）扩大了装配的离散空间。
- **本轮已做的小幅框句（只用原文已有事实）**：摘要写明框架是为了 “learn and constrain a spatial representation of brick assemblies”；引言补了一句：$48^3$ 工作空间、多级描述、固定空间序列化，以及转换期几何检查与生成后 exact-cover 重铺，共同约束覆盖、重叠和钉柱连通；贡献 1–3 与结论各加了对应从句。未新增实验，未把模型改称为 VLM，未写 RL/预训练。

### 对齐偏弱之处（不虚构实验）

- Topic 5 列举了 pretraining、fine-tuning、RL 与 data generation。本稿只有后两项；若在摘要中并列写 “pretraining / RL”，会构成不实主张，故未写。若用户希望用一句话显式声明“本文不做预训练或强化学习”，可「待用户确认」后加入。
- “如何改进几何/空间推理”在修订前主要靠流程描述，因果或能力提升的直接证据不足：114 条提示上的结果是文本–图像对齐与 $P_{\mathrm{inv}}$，**不是**专门的空间推理基准（例如空间关系问答、多步装配规划准确率）。不能把现有分数直接写成 “improves spatial reasoning”。机制说明已在引言加强，但评测与题目之间的缺口仍在，需「待用户确认」是否只在讨论中限定，或日后补专门评测。
- 工作坊标题是 Vision-Language Models，而 BrickMore 的生成器是 **Qwen3-1.7B 语言模型**，不是 VLM；VQAScore / PE / SigLIP2 只用在评测渲染图。定位应是“用数据生成与微调学习空间表示，并用视觉–语言度量评估”，切勿改称本文提出了一个 VLM。「待用户确认」表述口径。
- 训练节里对表示学习更关键的细节（20 种积木、Y-first 序列化、六邻接校验 vs 钉柱连通重铺）仍主要放在后文，摘要/贡献未逐一展开。若要在贡献列表中点名这些设计，属于较大改写，「待用户确认」。

说明：更早一轮曾按当时要求加过几何装配相关框句。按用户后续要求，**这些已有句子未撤回，本轮不再新增该类表述**；本节只讨论 Topic 5。

---

## 问题清单与处理

下列问题在阅读 V1.2/`abstract_introduction.md`、V1.3 编译稿，以及先前项目交叉核对后汇总。编号连续。对比实验节中的问题一律不改正文，只标「待用户确认」。

### 已修复或仅作小幅修订

1. **摘要与结论用语与数据生成事实不一致**（曾写 “large-language-model-assisted / LLM-assisted data construction”，易被读成模型直接生成体素）。  
   **处理：** 已改为 “agentic batch generation of training data”，与正文及项目中的程序批量生成一致。

2. **引言提到 BrickGPT / BrickNet 时缺少 `\cite`**。  
   **处理：** 已补 `(Pun et al., 2025)~\cite{brickgpt}`、`(Kulits and Schmid, 2026)~\cite{bricknet}`。

3. **“English descriptions” 与训练节 “English captions / captionEn” 不一致**（对比实验节之外）。  
   **处理：** 引言与方法句已改为 “English captions”。

4. **数据集复现句像稿件备忘**（“Model generation records … should be retained”）。  
   **处理：** 已改为“每条模型记录包含 geometry plan 与数据集版本标识”，未新造数字。

5. **物理筛查段祈使语气，像待办说明**。  
   **处理：** 改为陈述句：筛查结果与几何通过率分开；不同版本的历史计数在此不合并。仍不引入未核实的筛查数字。

6. **§3.1 后多余空行**。  
   **处理：** 已删。

7. **Figure 1/2 源文件标题仍为 “LLM-assisted data distillation / voxel synthesis”，与 teaser 及正文的 agentic 表述冲突**。  
   **处理：** `figure_tex/figure1_content.tex`、`figure2_content.tex` 已改为 “Agentic batch generation” / “Agentic batch voxel generation”，并用 tectonic 重编 `figure1.pdf`、`figure2.pdf`。V1.2 中的图源未改。

8. **摘要/引言/贡献未把工作放进 Topic 5 的“学习空间表示”（数据生成 + 微调）框架；对“这些设计如何约束空间布局”的说明偏隐**。  
   **处理：** 已用文中已有内容加框句（见「GSR-VLM 契合度」）。未声称 RL、预训练或 VLM 实验，未改贡献的事实与数字。

### 未改，标「待用户确认」

9. **【待用户确认】模板不符。** 工作坊要求 AAAI-27 模板，当前为 CVPR 2026 样式。改为官方 `aaai27`/`AuthorKit27` 属于大改（导言、标题块、文献样式、可能去掉 hyperref 彩色链接与页码等），本轮不迁移。

10. **【待用户确认】篇幅超过长文 7 页正文限制。** 现 PDF 14 页；大量历史图（image7–19、original_comparison 等）、训练表与附录历史表是主因。按规则不自行删除整节或大段压缩。建议由用户决定：删减/下沉历史图、压缩训练节、或改投短文（4 页）。

11. **【待用户确认】作者、单位、paperID 仍为占位；题名未动。** 需先确认工作坊是否双盲（官网未写明），再决定匿名稿还是实名稿。本轮不改标题与作者。

12. **【待用户确认】匿名政策需向工作坊/OpenReview 核实。** 不宜仅因 AAAI 主会是双盲就自行改稿。

13. **【待用户确认】对比实验协议不完整（节本身按用户要求保持不动）。** 交叉核对仍显示：BrickGPT 侧 `world_dim=20`、`max_bricks=200`、稳定样本 66/114 等限制与 BrickMore 的 $48^3$、约 413 零件、混合 `source_kind`、114 条对 105 个 category×level 组的不均衡，以及度量模型检查点（VQAScore / PE / SigLIP2）和 $P_{\mathrm{inv}}$ 内核，均未在该节写清。这些会影响“最高分 / $P_{\mathrm{inv}}$ 持平”的解读，但不改该节。

14. **【待用户确认】摘要写平均 $P_{\mathrm{inv}}=0.00\%$ 且与 BrickGPT 持平，未说明主对比中 110/114 条 BrickMore 主输出为重铺（stitched），仅 4 条为 raw。** 数字本身与结果文件一致，但证据边界应在摘要中点明。因靠近对比结论，本轮未改摘要中的评测句。

15. **【待用户确认】生成结果拼图说明 “One chair is raw” 不完整**（主输出实际有 4 条 raw）。该图注在对比实验节，未改。

16. **【待用户确认】训练样本 396,610 与 $79{,}301\times 5=396{,}505$ 相差 105。** 仓库中仍未找到可核定的 `build_stats.json` / `trainer_state.json` / `train_brickmore.log`。按规则保留 396,610 及 `% TODO verify sample count`，不编造解释。

17. **【待用户确认】BrickGPT 配方对照表中的论文数字尚未用原文核对。** 保留 `% TODO verify against BrickGPT paper`，不改表中数字。

18. **【待用户确认】相关工作过薄**（仅 BrickGPT、BrickNet、StableLego 三条手工文献）。本轮只补了已有引用的 `\cite`，不新造文献、不扩写整个相关工作节。

19. **【待用户确认】数据集与历史图仍大量标注 “require verification”，部分图含中文标注。** 删除或替换属于大改，且会牵动篇幅。本轮只调整了筛查段语气，未删图、未引入未核实计数。

20. **【待用户确认】对比实验节内 “stitched” 与 “retiled” 混用。** 不改该节。

21. **【待用户确认】评测指标缺少模型检查点与 $P_{\mathrm{inv}}$ 的形式定义**（内容在对比实验节）。不改该节。

22. **【待用户确认】无统计显著性检验。** 正文 Limitations 已承认，可保持；若要补检验需用户基于已有 per-prompt 记录另行计算，本轮不编造 p 值。

23. **【待用户确认】`D:\BrickMore\Essay\BrickMore\abstract_introduction.md` 已过时**（仍写模型直接产出三维体素坐标、“approximately 80,000”、仅英文 400,000、“483 grid”、乱码的 $P_{\mathrm{inv}}$ 等）。该文件不在 V1.3 内，本轮未改。建议与 V1.3 正文同步或标明作废。

24. **【待用户确认】定位口径：不要把生成器写成 VLM；不要把现有三项对齐分数写成空间推理能力的直接证明；是否在讨论中点明 Topic 5 只覆盖 data generation 与 fine-tuning。**

25. **【待用户确认】Teaser 使用 `\captionof`，编译出现 `hypcap=true` 被忽略的警告。** 小格式问题，宜随 AAAI 模板迁移一并处理，本轮不改 CVPR 标题区结构。

26. **algorithm.sty 的 Invalid UTF-8 字节警告** 来自宏包包内文件，非本文源码。未修改第三方宏包。随模板迁移可能不再使用该包组合。

27. **环境信息（非稿件错误）：** Fontconfig “Cannot load default config / No writable cache directories” 出现在 tectonic 日志中，不影响 PDF 生成。

---

## 编译结果

- 编译器：`D:\BrickMore\tmp\v12_build\tectonic\tectonic.exe`（0.17.0）
- 先编 `figure1.tex` / `figure2.tex`（exit 0），再编 `main.tex`（框句之后再次编译，exit 0）
- 输出：`D:\BrickMore\Essay\BrickMore\V1.3\main.pdf`（约 3,576,442 字节，2026-11-14 23:03 UTC+8）
- **页数：14**
- **无 TeX 错误**；无 Overfull/Underfull；无未定义引用
- 残留警告：`algorithm.sty:11` Invalid UTF-8；`Package caption Warning: hypcap=true will be ignored`（teaser 的 `\captionof`）

## V1.2 完整性

`D:\BrickMore\Essay\BrickMore\V1.2\main.tex` 仍为 33,981 字节、时间戳 2026-11-14 01:17:21（UTC+8）；`main.pdf` 时间戳 2026-11-14 01:17:30（UTC+8）。图源标题仍为 LLM-assisted。本轮全部修改只发生在 V1.3。
