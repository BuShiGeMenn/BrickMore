# BrickMore V1.4 审稿与修订记录（第二轮）

- 工作目录：`D:\BrickMore\Essay\BrickMore\V1.4`（由 `V1.3` 完整复制，同级目录）。**V1.2、V1.3 均未改动。**
- 评审基准：[GSR-VLM](https://gsr-vlm.org/)（AAAI-27 workshop，2026-11-14 重新读取官网），**仅对齐 Topic 5**「Learning spatial representations: Pretraining, fine-tuning, reinforcement learning, and data generation for improving geometric and spatial reasoning」；Topic 2 本轮不考虑。
- 用户已同意的改动：换 AAAI-27 模板；正文 ≤ 7 页（参考文献、附录不限）；小改动（语言、逻辑、术语、指标定义、检查点说明、图注、相关工作）。
- 本轮不做：填真实作者；编造实验/数据；宣称做过预训练或 RL；把模型称为 VLM；在无项目文件依据时改数字；删整节；改核心论点/结论。

## 结果摘要

| 项目 | 结果 |
|---|---|
| 模板 | 官方 AAAI-27 Author Kit（`https://aaai.org/authorkit27/` → `AuthorKit27.zip`，`aaai2027.sty` 2026-10-21 版，未修改），匿名投稿模式 `[submission]` |
| 编译 | `latexmk -pdf`（pdfTeX 1.40.29 / TeX Live 2026，TinyTeX），exit 0；无 LaTeX 错误、无 Overfull、无未定义引用/文献；全部字体为嵌入的 Type 1 |
| PDF | `V1.4\main.pdf`，共 16 页 |
| 正文页数 | 正文（摘要→结论）在**第 6 页左栏**结束，References 从第 6 页开始 → **正文约 5.5 页，≤ 7 页** |
| 附录 | References 之后的 Technical Appendix A–D（数据集历史图、训练细节、历史评测图、历史表格），约第 7–16 页 |
| 问题数 | 本轮新提 26 条（N1–N26），已修 19 条，7 条「待用户确认」；上一轮 27 条中，本轮新解决 10 条（累计 18 条已解决），其余见下表 |

> 截止时间：官网 Submission deadline 2026-11-19 AoE（UTC−12）＝ **2026-11-20 19:59（UTC+8）**。投稿系统 OpenReview：`AAAI.org/2027/Workshop/GSR-VLM`。

---

## 一、本轮新提问题与处理（N1–N26）

### 已修复

**N1 模板为 CVPR 2026，工作坊要求 AAAI-27 模板。**
处理：从 AAAI 官方渠道下载 AuthorKit27，按 `AnonymousSubmission2027.tex` 重写导言区：`\usepackage[submission]{aaai2027}`、`natbib`、`caption`、`\frenchspacing`、`\pdfinfo{/TemplateVersion (2027.1)}`。去掉官方禁用的 `hyperref`、`\clearpage`、`\onecolumn`；`algpseudocode` 换为模板推荐的 `algorithmic`；开启节编号（`secnumdepth=2`，模板允许 0/1/2）。旧 `cvpr.sty`、`ieeenat_fullname.bst` 移到 `archive/cvpr_template/`（不再使用）。

**N2 新模板要求 pdfTeX，原编译链 Tectonic（XeTeX）无法编译。**
处理：`aaai2027.sty` 会检查 pdfTeX，用 Tectonic 编译直接报错。已改为 `latexmk -pdf`；`scripts/build.ps1` 已更新（两张独立 TikZ 图仍可用 Tectonic，`main.tex` 用 latexmk），`README.md` 已更新。用户电脑上没有 pdflatex/latexmk，本轮在 Grok Bot 的 box 上用 TinyTeX 编译，再把结果拷回。→ 用户本地重编需要安装 MiKTeX/TeX Live，或使用 Overleaf（pdfLaTeX）。

**N3 篇幅超限（V1.3 共 14 页，正文远超 7 页）。**
处理：只移动、不删除。下列次要内容移到 References 之后的 Technical Appendix：体素样例图（image7/8）、局部修复示例（image2–5、9–12）、接触重力筛查示意（image13）、历史统计图（image14–17）、验证损失表、BrickGPT 配方对照表、历史基线/失败分类/定性对比图（image18、19、original_comparison）、5 张历史表格。正文保留 Figure 1、Figure 2、生成结果拼图、Algorithm 1、数据表、微调配置表、主对比表、raw/retiled 表。原「Dataset Statistics and Analysis」「Physical Screening Results」「Relation to the Official BrickGPT Recipe」三个小节**合并**进相邻小节或附录表注，原文要点都保留，没有删掉任何一节的内容。

**N4 raw/stitched 配对子集的描述有误。** V1.3 说该 110 对“与三系统主表分开”，但核对 `Results\three_model_comparison_20261111\...\report\scores.csv` 后发现：BrickMore 主对比 114 条中，110 条是 stitched（primary），4 条是 raw；这 110 条 stitched 与对应的 raw 草稿配对，正好复现表中全部数值（P_inv 0.1897%→0、VQA 0.2065/0.2071、PE 0.1858/0.1859、SigLIP2 0.1379/0.1261）。
处理：改为“主对比中 110 条 retiled 输出与其 raw 草稿配对”。另外从同一文件算出平均零件数 178.7 → 421.2，加入表 4（来自已有文件，不是新实验）。

**N5 摘要和评测节没有说明主对比中 BrickMore 有 110 条 retiled、4 条 raw**（即上一轮 #14）。
处理：用 `selected_manifest.jsonl` 核实（stitched 110 / raw 4），已写入摘要与 5.1 节。结论句没改。

**N6 指标缺少检查点、渲染协议和 P_inv 形式定义**（上一轮 #21）。
处理：根据 `vqa/pe/siglip2.config.json`、`*.model.json`、`render_protocol.json`、`structure.config.json` 和分析文档补充：VQAScore 用 Qwen2.5-VL-7B-Instruct；PE 用 PE-Core-bigG-14-448（文本上限 72 token）；SigLIP2 用 giant-opt-patch16-384（文本上限 64 token）；8 视角取最大再对 prompt 平均；渲染为 512×512 正交视图、25° 仰角、0°–315° 每 45° 一张、统一黄色。P_inv 给出公式：按导出文件顺序，用 BrickNet 原版 inset 碰撞内核判定无效放置，按模型做 macro 平均。

**N7 stitched / retiled 术语混用**（上一轮 #20）。
处理：正文统一用 retiled，只在 4.2 节说明一次“文件名为 `stitched`”；表头 “Stitched” 改为 “Retiled”。

**N8 引用格式重复**，如 “(Pun et al., 2025)~\cite{brickgpt}”。
处理：改用 natbib + `aaai2027.bst` 的 `\cite`，作者年份自动生成；参考文献移到 `references.bib`。

**N9 相关工作太薄**（上一轮 #18）。
处理：新增 11 篇真实文献，作者和标题都用 arXiv API 核对过：Thompson et al. 2020（图生成 LEGO）、Brick-by-Brick（NeurIPS 2021）、Break and Make（ECCV 2022）、DreamFusion、Infinigen、LoRA、Qwen3、Qwen2.5-VL、VQAScore、SigLIP 2、Perception Encoder。相关工作扩成三段：积木装配与生成、稳定性分析、程序化数据与参数高效微调。

**N10 数据集校验“单一六邻接连通”与“允许多个分别接地组件”看起来矛盾。**
处理：3.2 节说明前者指体素六邻接，后者指积木组件各自接地；二者都不同于生成后重铺要求的单一钉柱连通分量。

**N11 正文没有明确说明 Topic 5 的覆盖范围**（上一轮 #24 的一部分）。
处理：Limitations 中加 “Scope” 一句：本文通过数据生成和监督微调学习空间布局，不做预训练或强化学习；生成器是纯文本语言模型，视觉–语言模型只用作渲染图评测指标。没有把模型称为 VLM。

**N12 数据统计表和训练数据表内容重复。**
处理：合并为表 1（数据集与微调语料）。表中数字一个不改。

**N13 Teaser 用 `\captionof` 放在标题区，产生 hypcap 警告**（上一轮 #25）。
处理：改为 `figure*`，排在第 2 页顶部；警告已消失。

**N14 algorithm.sty 的 UTF-8 警告和 Tectonic 的 Fontconfig 警告**（上一轮 #26、#27）。
处理：换成 pdflatex + algorithmic 后，两类警告都没有了。

**N15 生成结果拼图图注“One chair is raw”容易误读**（上一轮 #15）。
处理：改为“本拼图中一把椅子为 raw，其余为 retiled；完整主对比中 114 条里有 4 条 raw”。拼图移回正文（Figure 3）。

**N16 验证损失表“End of epoch 1 = step 44,500”不精确。**
处理：每个 epoch 为 356,955/8 ≈ 44,620 步（与总步数 133,860 吻合），已标为 “≈ End of epoch 1”，并在表注说明 44,500 是离 epoch 1 结束最近的一次评估。

**N17 评测指标与他文数值是否可比没有说明。** 评测配置写有 `exact_paper_reproduction: false`。
处理：5.4 节加一句：本次指标实现不是对已发表评测的精确复现，不宜与他文报告的数值直接比较。

**N18 原正文中的历史统计图（含中文标注）放在正文。**
处理：已全部移到附录，附录开头说明这些图保留中文标注、属于历史版本或口径。（是否重绘为英文或删除，见 N24。）

**N19 小的事实补充，均来自项目文件。**
`merge_report.json` 显示每类 3,805–3,810 个模型，A/B 两批在精确和规范（48 种轴/符号变换）占用哈希下都没有重复，已写入 3.1 节。79,298 − 1,902 + 1,905 = 79,301 的算式已写明，与 `Train\datasets\CURRENT_DATASET_STATUS.md` 一致。

### 待用户确认（本轮新提）

**N20【待用户确认】训练样本数和 token 数有新的冲突证据。**
`D:\BrickMore\downloads\BrickGPT-Qwen3-1.7B-BrickMore-48\README.md`（模型卡）写的是 “**79,322 models × 5 captions = 396,610 samples** (356,955 train / 39,655 test, 90/10 split by model, seed 42)” 和 “~2.19B tokens total”。
- 79,322 × 5 = 396,610，正好解释了 105 条差额，但 79,322 与论文和数据集文档的 79,301 整合口径不一致。
- 2.19B 与论文的 2,228,044,818（2.23B）不一致。不过按 24,448 tokens/s × 25.3 h ≈ 2.227B 推算，2.228B 与吞吐量自洽。
- 模型卡把 9:1 中的小份称为 test，论文称为 validation。
- 模型卡提到的 `trainer_state.json` 不在该目录；`build_stats.json` 在 `D:\BrickMore` 下也没找到。

处理：数字保持原样，`% TODO verify sample count` / `% TODO verify token count` 注释保留（表 1 与附录表）。正文不写冲突细节。需要用户确认训练实际用的是 79,301 还是 79,322 个模型。

**N21【待用户确认】标题仍只有 “BrickMore”。** AAAI 要求标题是描述性的 mixed case。建议（未改）：*BrickMore: Learning Stud-Connected Brick Assembly from Agentically Generated Voxel Data*。

**N22【待用户确认】匿名与作者信息。** 当前使用 AAAI 官方匿名模式，PDF 首页显示 “Anonymous submission”；源码里作者和单位是占位符。工作坊官网没有写明是否双盲。用户收集好作者信息、并确认工作坊政策后，再决定保持匿名还是去掉 `[submission]` 填入实名。

**N23【待用户确认】Reproducibility checklist。** AAAI 模板提示“视会议要求”，工作坊官网没有提到。本轮没有加入 `ReproducibilityChecklist.tex`。

**N24【待用户确认】附录中含中文标注的历史图（image13–19）怎么处理。** 可以重绘为英文版，也可以删除（删除属于删内容，需要用户同意）。目前保留在附录。

**N25【待用户确认】用户本地编译环境。** Tectonic 不能再编译 `main.tex`。需要安装 MiKTeX/TeX Live，或者上传到 Overleaf。

**N26【待用户确认】PE / SigLIP2 分数的具体变换方式**（余弦相似度还是 sigmoid 概率）在项目配置里没有写明，正文只写了 “image–text matching scores”。如果要写得更精确，需要核对评测脚本 `evaluate_paper_images.py`（不在本机项目目录中）。

---

## 二、上一轮（V1.3）27 条问题的处理情况

| # | 问题 | V1.4 状态 |
|---|---|---|
| 1–8 | 上一轮已修（agentic 用语、引用、English captions、复现句、筛查段语气、空行、图源标题、Topic 5 框句） | 保持已修；措辞在新模板中略有压缩，事实不变 |
| 9 | 模板不符 | **已修**（N1） |
| 10 | 篇幅超限 | **已修**（N3：正文约 5.5 页） |
| 11 | 作者、单位、paperID 占位；题名 | 作者为匿名模式 + 占位符，**待用户确认**（N21、N22） |
| 12 | 匿名政策需核实 | **待用户确认**（N22） |
| 13 | 对比协议不完整（BrickGPT `world_dim=20`、`max_bricks=200`、稳定 66/114；114 prompt 对 105 个类别×level 组不均衡等） | **部分修复**：检查点、渲染、P_inv、候选选择（首候选、优先 retiled）已补（N5、N6）。BrickGPT 侧生成参数和 105 组等权口径没有写进正文：前者本轮没有亲自核实，后者属于新增分析数字。**待用户确认**是否补充（分析文档中 105 组等权结果方向与主表一致：BrickMore 0.2347/0.1840/0.1257） |
| 14 | 摘要没说明 110 条 retiled、4 条 raw | **已修**（N5） |
| 15 | 拼图图注 “One chair is raw” | **已修**（N15） |
| 16 | 396,610 与 396,505 差 105 | **待用户确认**，TODO 保留，新增模型卡证据（N20） |
| 17 | BrickGPT 配方表数字未核对 | **待用户确认**。项目文件中没有 BrickGPT 原文数据；按要求没有用外部来源改数，`% TODO verify against BrickGPT paper` 保留（表已移到附录）。如用户同意，可对照 arXiv:2505.05469 原文核对 |
| 18 | 相关工作过薄 | **已修**（N9） |
| 19 | 历史图标 “require verification”、含中文 | **部分修复**：已移到附录并统一说明（N18）；重绘或删除**待用户确认**（N24） |
| 20 | stitched / retiled 混用 | **已修**（N7） |
| 21 | 指标检查点与 P_inv 定义 | **已修**（N6） |
| 22 | 无显著性检验 | **待用户确认**：Limitations 中已说明。若要补配对检验，可以用现有 `scores.csv` 计算，但会新增数字，需用户同意 |
| 23 | `abstract_introduction.md` 过时 | **待用户确认**：该文件不在 V1.4 内，未改 |
| 24 | 定位口径（不称 VLM、不把对齐分数当空间推理证据） | **部分修复**：N11 加 Scope 句，5.4 节明确三项指标不是空间推理基准；是否补空间推理评测或消融**待用户确认** |
| 25 | `\captionof` / hypcap 警告 | **已修**（N13） |
| 26 | algorithm.sty UTF-8 警告 | **已解决**（N14） |
| 27 | Fontconfig 环境警告 | **已解决**（N14） |

上一轮遗留的 19 条（#9–#27）中，本轮新解决 10 条（#9、#10、#14、#15、#18、#20、#21、#25、#26、#27）；加上原有 8 条，累计已解决 18 条。部分修复 3 条（#13、#19、#24）。仍待确认 6 条（#11、#12、#16、#17、#22、#23）。其中 #24 的剩余部分并入下文 Topic 5 讨论。

---

## 三、Topic 5 契合度

**总体：中等偏好。** 本文天然对应 Topic 5 中的 **data generation + fine-tuning**，不涉及 pretraining 与 RL。

正文中的对应点：
- **数据生成**：GPT-6.1 Sol 以 agentic batch generation 编写参数化生成程序，得到 80,000 个 $48^3$ 体素模型和五级双语描述；转换管线把体素覆盖变成钉柱连通的积木放置，经几何检查得到 79,301 个可用模型。这是“用生成数据学习空间布局”的核心。
- **微调**：Qwen3-1.7B + LoRA 学习从文本到积木尺寸和位置的映射；固定空间序列化（Y 优先）、20 种积木库和 $48^3$ 工作空间决定了模型学到的表示。
- **几何约束**：数据端有覆盖、接地、六邻接检查；生成端有 MILP exact cover 和单一钉柱连通检查。

偏弱之处（不虚构实验）：
1. 没有专门的空间推理评测。现有指标是渲染图的文本–图像对齐和 P_inv，不能直接说明“提升了空间推理”。正文已在 5.4 节和 Limitations 中写明。如需加强，需要用户决定是否补评测（属于新实验）。
2. 工作坊主题是 VLM，而本文生成器是纯文本 LM。正文已在 Scope 句中如实说明，VLM 只作为评测器。
3. 没有对照实验（例如同一模型在不同数据规模或不同描述层级下训练）来展示“数据生成如何改进空间表示”。属于新实验，**待用户确认**。

---

## 四、「待用户确认」清单汇总

1. **训练样本数和 token 数**：模型卡写 79,322 × 5 = 396,610、约 2.19B tokens，论文写 79,301 模型、2,228,044,818 tokens（N20 / 原 #16）。
2. **BrickGPT 配方表数字**：项目内无原文可核对；是否允许对照 arXiv 原文（原 #17）。
3. **标题**是否改为描述性标题（N21）。
4. **作者信息**与匿名政策：保持匿名模式还是填实名（N22 / 原 #11、#12）。
5. **Reproducibility checklist** 是否需要（N23）。
6. **附录中含中文标注的历史图**：重绘还是删除（N24 / 原 #19）。
7. **本地编译环境**：安装 MiKTeX/TeX Live，或使用 Overleaf（N25）。
8. **PE / SigLIP2 分数定义**的精确表述（N26）。
9. **对比协议补充**：BrickGPT 侧生成参数、105 组等权口径是否写入正文（原 #13）。
10. **显著性检验**：是否基于现有 per-prompt 记录补配对检验（原 #22）。
11. **`abstract_introduction.md`** 是否同步或作废（原 #23）。
12. **是否补空间推理评测或数据消融**，以加强 Topic 5 论证（新实验，原 #24 延伸）。

---

## 五、编译记录

- 环境：Grok Bot box 上的 TinyTeX（TeX Live 2026，pdfTeX 1.40.29），`latexmk -pdf -interaction=nonstopmode main.tex`，exit 0。
- 日志：无 `!` 错误、无 Overfull hbox、无未定义引用或文献；只有少量 Underfull 提示。
- 字体：`pdffonts` 显示 32 个字体，全部嵌入 Type 1，没有 Type 3。
- 页面：共 16 页；References 起始于第 6 页（正文 ≤ 7 页 ✓）；第 7–16 页为附录。
- 没有修改 `aaai2027.sty` / `aaai2027.bst`；`figure1.pdf` / `figure2.pdf` 沿用 V1.3 的编译结果（图源未改）。
