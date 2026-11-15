# BrickMore V1.6 修订计划（RB2 · R0）

- 作者：ReviewBot2（RB2）。本文件**只是计划**：本轮没有修改任何论文文件，只写了本文件。
- 依据：本轮重新读取的 `D:\BrickMore\Essay\BrickMore\V1.5\main.tex`（33,614 字节，2026-11-14 23:36）和 `V1.5\REVIEW_V1.5.md`。按要求**没有读** `PLAN_RB1_R0.md` 或 RB1 写的任何内容。
- 评审口径：GSR-VLM workshop **只看 Topic 5**「Learning spatial representations: Pretraining, fine-tuning, reinforcement learning, and data generation for improving geometric and spatial reasoning」，不考虑 Topic 2。
- 硬约束：
  - AAAI-27 模板（`aaai2027.sty` 2027.1，`[submission]`）；
  - 正文 ≤ 7 页（参考文献、附录不限）；
  - 截止 **2026-11-20 19:59（UTC+8）**。OpenReview Submission invitation 的 `duedate`＝1795175940000 ms，换算后正是 2026-11-20 19:59 UTC+8（11:59 UTC）。
- 铁律：
  - 不编造数字或文献。本计划中每个建议写入论文的数字都标了**项目文件路径**；新增文献都经 arXiv API 核对。
  - 不把模型称为 VLM，不宣称做过预训练或 RL。
  - 没有用户同意，不改核心结论、不删整节、不做新实验。
- 写作时间：2026-11-15 00:40（UTC+8）。

---

## 0. 速览

### 0.1 现状（V1.5）
- **结构**：§1 Introduction，§2 Related Work，§3 Dataset Construction，§4 BrickMore Text-to-Brick Model（含 Algorithm 1、Table 2、Figure 3 拼图），§5 Comparative Evaluation（Table 3 主表、Table 4 raw/retiled），§6 Limitations，§7 Conclusion，References，附录 A–D。
- **页数**：正文在第 6 页左栏结束，**还有约 1–1.3 页余量**可用于加强 Topic 5 论证。
- **已经做好的**：模板合规、匿名、主表数字核对、BrickGPT 配方表已对照原文（V1.5 P1）、Scope 句（不做预训练/RL、生成器是纯文本 LM）。

### 0.2 Topic 5 视角下的最大短板（按重要性）
1. **缺少能说明“模型学到了什么空间表示”的证据。** 现有评测只有文本–图像对齐和 P_inv，不能回答 Topic 5 关心的“数据生成和微调如何影响几何/空间推理”。
   - **关键发现**：项目里已经有一份**未写进论文**的诊断结果：`D:\BrickMore\brickmore48_eval_630\`（525 条新提示词的生成账本和 raw 失败解剖）。它直接量化了学到的表示**懂体素形状，但不懂钉柱咬合**。这是本轮性价比最高的补强点，**不需要新实验**（见 E-2）。
2. **指标定义还不够精确。** V1.4/V1.5 都把 PE/SigLIP2 写成笼统的 “matching scores”。本轮已从实际评测脚本确认了精确定义（见 E-1、U8）。
3. **数据生成环节缺少“质量 / 效益”数字。** 例如重铺把通过数从 65,503 提到 79,298，`summary.json` 里有现成数字（见 D-1）。
4. 摘要、引言、贡献三处重复同一组数字（80,000 / 21 / 48³ / 79,301 出现 4 次以上），占篇幅又没有推进论证（见 I-2）。
5. 附录里含中文标注、口径为“历史”的图，对英文评审不友好，也容易被抓“数字不一致”（见 U4）。

### 0.3 核心策略（一句话）
把论文从“一个 text-to-brick 系统 + 对齐分数领先”，改写成：

> “用程序化生成的、经几何检查的数据去**微调学习积木装配的空间表示**，并**诊断**这种表示学到了什么、缺了什么（体素形状 vs 钉柱咬合），再用几何修复补上缺口。”

所有支撑都来自项目已有文件；结论（对齐分数最高、P_inv 与 BrickGPT 持平）不变。

### 0.4 条目统计

| 优先级 | 含义 | 条数 |
|---|---|---|
| **P0** | 投稿前必须完成，否则有合规风险或明显错误 | 9 |
| **P1** | 强烈建议，显著提升 Topic 5 契合度或审稿观感 | 19 |
| **P2** | 有余力再做 | 9 |
| **U（待用户确认）** | 需要用户拍板；每条都给了推荐选项和理由 | 12 |
| 合计 | | **49** |

（逐条编号见 §2–§3，统计核对见 §8。）

---

## 1. 页面预算（正文 ≤ 7 页）

V1.5 正文约 5.5–6 页（第 6 页左栏结束）。每完成一批修改就重新编译，并用以下命令核对正文结束位置：

```
pdftotext -f N -l N main.pdf -   # 查找 "References" 所在页
```

**References 标题必须出现在第 7 页或更早**，并且第 7 页之后不能再有正文文字。

| 变化 | 条目 | 估计页面影响 |
|---|---|---|
| 摘要压缩 | A-2 | −0.05 |
| 引言去重 | I-2 | −0.15 |
| 新增 Topic 5 研究问题段 | I-3 | +0.10 |
| 相关工作新增一段（3 篇文献） | R-1/R-2 | +0.12 |
| 数据集：转换效益句 + Table 1 两行 | D-1/D-2 | +0.08 |
| 指标精确定义（替换原句，净增少） | E-1 | +0.03 |
| **新增 §5.x 生成诊断（含小表）** | E-2 | +0.35 |
| 分级别 / 稳健性两句 | E-3/E-4 | +0.08 |
| 局限性与结论改写 | L-1/C-1 | +0.05 |
| 显著性检验一句（若 U5 同意） | U5 | +0.03 |
| **合计** | | **约 +0.65 页 → 正文约 6.2–6.6 页，仍 ≤ 7** |

兜底：如果超出，按以下顺序退回附录：
1. Figure 3 拼图（移到附录 C，−0.35 页）；
2. Table 2 微调配置（并入附录 B，−0.2 页）；
3. Algorithm 1 改为 `figure*` 双栏紧凑版。V1.5 约定 Algorithm 1 留在正文，**不建议移出**。

---

## 2. 待用户确认（U1–U12）：推荐选项与理由

> 这些条目没有用户同意前**不动正文**。每条给出推荐选项（★）。

### U1 标题（当前 `\title{BrickMore}`）
- **问题**：AAAI 要求描述性、mixed case 的标题。只有一个系统名，看不出与 Topic 5 的关系。
- **选项**：
  - ★A：`BrickMore: Learning Stud-Connected Brick Assembly from Agentically Generated Voxel Data`
  - B：`BrickMore: Fine-Tuning Language Models on Programmatically Generated Data for Text-to-Brick Assembly`
  - C：保持 `BrickMore`。
- **推荐 A 的理由**：
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
- **结论**：实际流程是双盲（作者对审稿人隐藏）。
- **推荐 ★**：
  - 保持 `\usepackage[submission]{aaai2027}`，PDF 中不出现作者；
  - 作者姓名只填在 OpenReview 表单里；
  - **今天就让所有作者注册 OpenReview profile**。没有机构邮箱的 profile 需要人工审核，可能要几天，这是**截止前最大的非写作风险**；
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
  - token：论文的 24,448 tokens/s × 25.3 h ≈ 2.227B，与 2,228,044,818 自洽；与 “~2.19B” 不一致（差约 1.7%）；
  - 训练日志 `trainer_state.json`、`build_stats.json` 在 `D:\BrickMore` 下**找不到**（V1.4 已全盘搜索）。
- **选项**：
  - ★A：请用户去训练服务器找到训练清单或日志（`trainer_state.json`、训练集 jsonl 行数、`train_brickmore.log`），以实测为准修正 Table 1 和附录配方表；
  - B：找不到实测证据时，正文改为只写“about 396.6k samples from the integrated corpus”这类不暗示精确模型数的写法——**不推荐**，会削弱可复现性；
  - C：维持现状（79,301 与 396,610 并存），审稿人一算就会发现乘不上——**不推荐**。
- **推荐 A 的理由**：只有实测清单能裁定。若实测是 79,322，需要在 §3.3 解释它与 79,301 的差别（例如训练清单构建时间早于钢琴替换），但这个解释**必须由用户提供证据**，不能代写。
- **截止前兜底**：如果 11-18 前仍无实测证据，采用如下中性写法（不新增数字）：
  > “The fine-tuning corpus contains 396,610 (model, English caption) samples (356,955 / 39,655 split by model).”

  并从 Table 1 删掉“Integrated passing models”和样本行之间的乘法暗示（两行分开写，加脚注 “sample counts are taken from the training manifest”）。这只在“训练清单确有 396,610 条”成立时才可写，而该数字目前只有模型卡和论文作为来源，**仍需用户确认**。
- 工作量：找证据由用户完成；改稿 20 分钟。页面影响 0。不需要新实验。风险：若实测是 79,322，§3.3 “Fine-tuning uses only geometrically passing models”是否仍然成立，也需要用户核实。

### U4 附录中含中文标注的历史图
- **现状**：附录 A/C 中的 image13（重力筛查示意）、image14–17（历史统计）、image18–19（历史基线/失败分类）带中文坐标轴和图例，图注里都写着“historical / require verification”。
- **选项**：
  - ★A：**从提交 PDF 中移除** image13–19（`\iffalse ... \fi` 注释掉，文件保留）。其中有价值且能核实的数字，用 D-1 / APP-2 的英文表格重新给出（来源 `retile_assembly_80000\summary.json`）；
  - B：用项目数据重绘英文版。每张约 1–2 小时，共 7 张约 8–12 小时，而且多张图的源数据版本不明（图注自己写着 require verification）；
  - C：保持现状。
- **推荐 A 的理由**：
  - 英文投稿出现中文图会被视为不专业；
  - 这些图的数字自称“需核实”，放进去反而给审稿人留下“数字不一致”的把柄；
  - 附录不限页，但不加分；
  - 删掉的是附录里的历史材料，不是正文章节，不改结论。
- **注意**：这仍然是“删除内容”，按规则**必须用户同意**。image7/8（体素样例，英文类名）和修复示例图（image2–5、9–12，无文字）**保留**。`original_comparison.png` 列标题为英文，可保留。
- 工作量（A）30 分钟；正文页面影响 0；附录约减少 4–5 页。不需要新实验。风险：用户若希望保留历史脉络，可改为只保留 image14 的英文重绘版（约 1.5 小时）。

### U5 是否补显著性检验
- **数据**：`D:\BrickMore\Results\three_model_comparison_20261111\intake\Results\comparison_full\report\scores.csv`（462 行，含逐 prompt 的 vqa/pe/siglip2/pinv）。胜/平/负已在 `...\analysis\三模型测评结果分析.md` 中给出：91/0/23、95/0/19、91/0/23。
- **推荐 ★：做**。在 114 条配对上做**双侧符号检验**（只用胜负数，最透明）和 **Wilcoxon 符号秩检验**，3 个指标 × 2 个对手（BrickGPT、BrickNet），Holm 校正。
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
  1. **数据侧**（D-1）：同一批 80,000 个模型，转换策略从 relaxed 到 retile，几何通过数从 **65,503** 变为 **79,298**；救回 **13,795** 个；新增体素 **228,582**、删除 **125**；**31,532** 个成功模型零体素改动。来源：`D:\BrickMore\Train\datasets\retile_assembly_80000\summary.json`（字段 `baselinePassed`、`geometryPassed`、`recoveredFailures`、`addedVoxelCount`、`removedVoxelCount`、`zeroVoxelChangeSuccessfulModels`）。V1.5 附录历史表中的 strict v3 = 7,902 需另外核对 `D:\BrickMore\Train\datasets\assembly_80000\assembly_summary.json` 后才能用。
  2. **推理侧**：raw vs retiled（Table 4，已在正文），加上 E-2 的 MILP 档位分布。
- **约束**：表述为“conversion-strategy comparison / repair analysis”，**不要叫 ablation of the learned model**。

### U8 PE / SigLIP2 分数：余弦相似度还是 sigmoid 概率
- **已用项目文件确认（推荐 ★：按脚本如实写）**。评测脚本 `D:\BrickMore\Deploy\build\comparison_20261110\BrickMoreComparison\Scripts\evaluate_paper_images.py` 的 SHA-256 前缀 `a90e851a6a01`，与 `...\three_model_comparison_20261111\intake\Results\comparison_full\{vqa,pe,siglip2}.config.json` 中 `sources.evaluate_paper_images.py` 记录的 `a90e851a6a0189d9…` 一致，可以确认是本次评测实际使用的版本：
  - **PE**：`encode_image(normalize=True)`、`encode_text(normalize=True)`，再 L2 归一化后点积 → **余弦相似度**（取值 [−1, 1]）；
  - **SigLIP2**：`model(**inputs).logits_per_image[:,0].float().sigmoid()` → 模型自带 logit scale/bias 后的 **sigmoid 概率**（取值 (0, 1)）；
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
  - Overleaf 免费版有编译超时限制，本稿约 3.7 MB 的 PNG 和 16 页附录可能超时，而且要上传整套素材。
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
- **推荐 ★**：请用户确认 525/114 条输出都来自 step-79,000（`load_best_model_at_end`）的那份权重。确认后，§4.1 可以写“all evaluated outputs are generated with this checkpoint”；无法确认就不写这句（V1.4 已删除过这句未核实的话）。
- 页面影响 0。

### U11 是否附 AAAI Reproducibility Checklist（新增）
- AuthorKit27 附有 `ReproducibilityChecklist.tex`，模板注释写“Check whether the conference requires…”；工作坊官网和 OpenReview 表单都**没有要求**。
- **推荐 ★：不附**。理由：不是硬性要求，填写需要逐项表态，有出错风险；时间优先给正文。若用户希望显得规范，可以放在附录最后（不计页），约 1 小时。

### U12 是否在正文使用 525 条诊断数据（新增，与 E-2 绑定）
- **推荐 ★：使用，但只用能从原始文件复算的部分**（`manifests\manifest_w{0,1,2}.json`、`results\raw_failure_autopsy.json`）。
- **不用**（无法核实）：
  - README 中的人工判决 79/105 组：`results\best_all.json` / `best_all.md` 在磁盘上**不存在**；
  - “与训练集零重叠”：没有对照文件；
  - “82% 碎片紧贴主体（≤1 格）”：autopsy 没有距离字段；
  - README 写的“108–124 s/条”：manifest 实测中位数 93.9 s，范围 22.9–401.6 s，两者矛盾。
- 需要用户确认：
  1. 同意把这批诊断写入正文；
  2. U10 的权重版本；
  3. 这 525 条提示词与主对比 114 条的关系。主对比 BrickMore 的 `model_id`（如 `basket-L1V5`）与 eval_630 的命名一致，说明 114 条出自这批输出，但选取规则需要用户说明。

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
  3. 逐页 `pdftotext` 找 “References” 所在页，≤ 7；
  4. `pdffonts main.pdf` 全部 Type 1 且已嵌入，没有 Type 3；
  5. `pdfinfo main.pdf` 没有 Title/Author 元数据。
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
  - TLDR 建议：“We fine-tune a 1.7B language model on 79k agentically generated, geometrically checked brick layouts and show what spatial structure it learns—and misses—before MILP retiling enforces stud connectivity.”（“79k”待 U3 定稿后同步）；
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

**A-2｜P0｜摘要重写：突出 Topic 5 学习表示的主线，去掉冗余，加入一句诊断发现**
- 改什么：V1.5 摘要约 260 词，句子 3–4（GPT-6.1 Sol 流程细节）和句子 6–7（修复流程细节）偏长，没有“模型学到了什么”这一句。
- 为什么：Topic 5 审稿人首先看“数据生成 / 微调是否改进了几何空间推理，以及证据是什么”。
- 怎么改（建议全文，约 215 词。【】为条件句：E-2 / U12 同意才保留；数字来源见 §5）：

```latex
\begin{abstract}
Generating brick structures from text requires geometric assembly: bricks must fit in a bounded grid, avoid overlaps, and interlock through studs, not merely resemble the described shape. We study how far a language model can learn such a spatial representation from programmatically generated data. Using GPT-6.1 Sol, an agentic batch-generation pipeline writes parametric generator programs that emit 80,000 voxel models across 21 categories on a $48^3$ grid, each with five bilingual captions of increasing detail. Same-color tiling, connectivity analysis, and local bridging and retiling convert the shapes into brick layouts, and 79,301 models pass the specified geometric checks. We fine-tune Qwen3-1.7B with LoRA on English captions and serialized brick placements, and repair its predictions by solving a shape-preserving exact cover with a single stud-connected component via mixed-integer linear programming (MILP). 【On 525 additional prompts, the fine-tuned model reproduces voxel-level shape well, but only 46 raw outputs (8.8\%) are stud-connected without repair; every failing raw output splits into two or more stud components (median five), indicating that the learned representation captures shape more readily than interlocking.】 On 114 shared prompts under a common rendering protocol, the evaluated BrickMore outputs (110 retiled, 4 raw) obtain the highest mean scores on three text--image alignment metrics and a mean invalid-placement ratio of 0.00\%, matching BrickGPT.
\end{abstract}
```

- 注意：
  - “reproduces voxel-level shape well”**不能直接写**，autopsy 没有形状保真度量。改为 “the fine-tuned model's raw layouts are voxel-connected in most cases” 也需要核实 `raw_report.json` 的 `voxel_components` 字段（README 称“0 条体素散架”，但 autopsy 文件没有这个字段）。
  - **在核实前用保守版**：“…but only 46 raw outputs (8.8\%) form a single stud-connected component without repair; every failing raw output splits into two or more stud components (median five).”
  - 执行前要逐个读 525 个 `models\*\*\raw_report.json`，统计 `voxel_components==1` 的数量。
- 工作量 40 分钟（含核对 voxel_components）。页面影响约 −0.05。不需要新实验（数据已有）。风险：U10/U12 未确认就只能删掉【】句。

**A-3｜P2｜摘要中 “GPT-6.1 Sol”**
- 保持原名（用户给定的事实），不改。只确认全文写法一致（V1.5 一致）。0 分钟。

### 3.I Introduction（§1，V1.5 共 7 段 + 贡献列表）

**I-1｜P1｜第 1 段：加一句空间表示框句**
- 改什么：第 1 段末尾 “…not only whether the overall shape resembles the described object.” 之后。
- 为什么：把问题放进 Topic 5 的“学习空间表示”语境。
- 怎么改（新增句）：
  > “This makes text-to-brick generation a useful testbed for learning spatial representations: the target is discrete, the constraints are exactly checkable, and a model's errors can be measured geometrically rather than only perceptually.”
- 工作量 5 分钟。页面影响 +2 行。不需要新实验。风险：无（是框句，不是结论）。

**I-2｜P0｜第 4–5 段去重**
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
Our analysis asks what such a model actually learns from generated data. 【On 525 additional prompts, only 8.8\% of raw outputs form a single stud-connected component; the failures are not scattered debris but layouts that split into a median of five stud components, most often bricks placed side by side without crossing layer boundaries.】 We therefore treat geometric repair as a complement to, not a substitute for, the learned representation, and we report both raw and retiled results.
```

- **注意**：“most often bricks placed side by side without crossing layer boundaries”来自 README §6 的定性结论，autopsy 只有分量数、悬空/落地计数，**没有“并排”的直接字段**。核实前**删掉这半句**，或改写为可核实的：“of the 2,240 detached fragments, 1,320 (59\%) are not grounded”（来源：`raw_failure_autopsy.json` 中 `orphan_air` 合计 1,320、`orphan_n` 合计 2,240、`orphan_ground` 合计 920）。
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
  author = {Siddiqui, Yawar and Alliegro, Antonio and Artemov, Alexey and Tommasi, Tatiana and Sirigatti, Daniele and Rosov, Vladislav and others},
  title = {{MeshGPT}: Generating Triangle Meshes with Decoder-Only Transformers},
  howpublished = {arXiv:2311.15475}, year = {2023}}
@misc{llamamesh,
  author = {Wang, Zhengyi and Lorraine, Jonathan and Wang, Yikai and Su, Hang and Zhu, Jun and Fidler, Sanja and others},
  title = {{LLaMA-Mesh}: Unifying {3D} Mesh Generation with Language Models},
  howpublished = {arXiv:2411.09595}, year = {2024}}
```

- 核对记录：
  - arXiv:2311.15475 “MeshGPT: Generating Triangle Meshes with Decoder-Only Transformers”，前 6 位作者 Siddiqui, Alliegro, Artemov, Tommasi, Sirigatti, Rosov，共 8 人；
  - arXiv:2411.09595 “LLaMA-Mesh: Unifying 3D Mesh Generation with Language Models”，Wang, Lorraine, Wang, Su, Zhu, Fidler，共 7 人。
  - **执行时**要用 arXiv 页面补全全部作者，或保留 `and others`（aaai2027.bst 会显示 “et al.”）。
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
  author = {Chen, Boyuan and Xu, Zhuo and Kirmani, Sean and Ichter, Brian and Driess, Danny and Florence, Pete and others},
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
  - 65,503 是 `baselinePassed`，需确认它对应 relaxed release。附录历史表是这么写的，执行时再读 `relaxed_assembly_80000\assembly_summary.json` 复核；
  - “31,532” 是整个 retile 运行的统计，与“整合版 79,301”口径不同，句中只说 “passing models” 不说“of the 79,301”。
- 工作量 20 分钟。页面影响 +0.06。不需要新实验。风险：口径表述。

**D-2｜P1｜Table 1 拆成“数据集”和“微调语料”两块**
- 为什么：V1.5 Table 1 把 79,301 与 396,610 上下相邻，读者会自然相乘发现 105 的差（见 U3）。拆开可以避免误导，同时如实保留。
- 怎么改：用 `\midrule` 分为 “Dataset (release reports)” 与 “Fine-tuning corpus (training manifest)” 两组，并加表注 “Corpus rows are taken from the training run and are reported as recorded.”
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

**M-4｜P1｜§4.2 末尾补实际运行统计（与 E-2 联动）**
- 为什么：Algorithm 1 的档位阶梯是“设计”。eval_630 的 manifest 给出了**实际**档位分布，能说明修复是否必要、代价多大。
- 怎么改（若 E-2 单设小节，这句放在 E-2，这里只留引用）：
  > “In practice, on 525 prompts the default ladder resolves 326, 133, and 18 cases at the 12, 60, and 180\,s tiers, two require the 600\,s recovery tier, 46 need no retiling, and 28 are regenerated with a new seed (Section~\ref{sec:diagnostics}).”
- 来源：`D:\BrickMore\brickmore48_eval_630\manifests\manifest_w0.json`、`manifest_w1.json`、`manifest_w2.json`，共 525 行；`solver_tier` 计数为 12s:326、60s:133、180s:18、600s:2、none_needed:46；含 `regen_seed` 字段的行有 28 条；`studOK` 为真 525 条；`shape_preserved` 为真 525 条。
- 工作量 10 分钟。页面影响 +2 行。不需要新实验。风险：依赖 U10/U12。

### 3.E Comparative Evaluation（§5）

**E-1｜P0｜§5.1 指标精确定义（U8 已有脚本证据）**
- 改什么：替换 “PE and SigLIP2 are image--text matching scores from …”。
- 为什么：VQAScore 当前写成 “probability that … answers Yes”，没说明是全词表 softmax；PE/SigLIP2 定义含糊，影响分数的可解释性（SigLIP2 的 0.12 vs PE 的 0.19 尺度不同）。
- 怎么改：

```latex
\emph{Text--image alignment.} VQAScore~\cite{vqascore} is the full-vocabulary softmax probability that Qwen2.5-VL-7B-Instruct~\cite{qwen25vl} generates the single token ``Yes'' as its first answer token when asked whether a rendered view shows the prompt. PE is the cosine similarity between L2-normalized image and text embeddings of PE-Core-bigG-14-448~\cite{pe}, and SigLIP2 is the sigmoid of the image--text logit (with the model's learned scale and bias) of SigLIP2 giant-opt-patch16-384~\cite{siglip2}; their text encoders read at most 72 and 64 tokens, respectively. For each metric, a model's score is the maximum over its eight views, averaged over prompts. The three metrics therefore live on different scales and are compared only within a metric.
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
To probe what the fine-tuned model learns, we analyze raw outputs for 525 additional prompts (21 categories $\times$ five levels $\times$ five phrasings) generated with the default protocol of Algorithm~\ref{alg:inference-retiling}. Only 46 raw layouts (8.8\%) form a single stud-connected component without retiling; this rate shows no clear trend across levels (13, 9, 9, 7, and 8 for L1--L5) but varies strongly by category (e.g., 8/25 for sofa, 0/25 for basket and camera). All 479 failing raw layouts split into at least two stud components (median 5, maximum 33). Overlaps are a minor cause: 50 failing layouts contain duplicated voxels, 41 of them with at most five (median 2), and 429 contain none. The 2,240 detached fragments are mostly not grounded (1,320 airborne versus 920 grounded). The learned representation thus places bricks whose in-bounds voxel union is retained by retiling but that often fail to interlock across layers; retiling yields a single stud-connected component for all 525 cases without changing that union (Table~\ref{tab:diag}).

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

- 来源：
  - `D:\BrickMore\brickmore48_eval_630\results\raw_failure_autopsy.json`（525 条；`ok`=46；失败 479 条 `ncomp` 最小 2、中位 5、最大 33；`dup>0`=50，其中 ≤5 的 41 条、中位 2；`dup==0`=429；`orphan_n` 合计 2,240，`orphan_air` 合计 1,320，`orphan_ground` 合计 920）；
  - `...\manifests\manifest_w{0,1,2}.json`（`solver_tier` 分布；分级别 none_needed 13/9/9/7/8；分类别 sofa 8、guitar 6、vessel 4…，basket/camera 0；`raw_bricks` 中位 183、最小 77、最大 623；`assembly_bricks` 中位 452；`regen_seed` 28；`studOK` 525；`shape_preserved` 525）；
  - `...\README.md`（21 类 × 5 级 × 5 变体的构成；它与 `prompts\items_index.json` 一致，但执行时应再数一遍 batch=2 的条目数）。
- **必须修改或删除的措辞**：
  - 上面片段已避免 “cover the intended shape” 一类说法：没有形状保真的直接度量，`shape_preserved` 只说明**重铺前后**体素一致，不说明 raw 与提示的匹配。
  - “0/25 for basket and camera”：从 manifest 复算时，basket、camera 没有出现在 none_needed 分组中（即 0），与 README 一致。
- 工作量 1.5 小时（写作 + 复核 + 表格排版）。页面影响约 +0.35。**不需要新实验**（数据已有），但这是新进入论文的数字，需要 U12 同意。风险：
  1. U10 权重版本；
  2. 525 条与 114 条的关系要写清：114 条的 BrickMore 输出是否就取自这 525+105 条？`selected_manifest.jsonl` 的 model_id 命名一致，但要用户说明选取规则；
  3. 不能写成 “spatial reasoning benchmark”。

**E-3｜P1｜§5.2 加分级别一致性与稳健性两句**
- 怎么改（接在 “…no significance test is reported.” 之前或替换该句，取决于 U5）：

```latex
The ordering is unchanged when each of the 105 category--level groups is weighted equally (BrickMore 0.2347 / 0.1840 / 0.1257 versus BrickGPT 0.1511 / 0.1459 / 0.0318 for VQAScore / PE / SigLIP2) and when truncated prompts are removed (PE on 89 prompts: 0.1821 vs.\ 0.1445; SigLIP2 on 85 prompts: 0.1088 vs.\ 0.0301), and BrickMore has the highest mean at every description level (Appendix~\ref{app:eval}).
```

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

**E-8｜U（并入 #13）｜BrickGPT 侧生成限制**
- 历史表写有 BrickGPT stable 66/114（`archive\historical_tables.tex`），以及 `world_dim=20`、`max_bricks=200`（V1.3 交叉核对）。可以从 `D:\BrickMore\BrickNet_BrickGPT_Compirasion\BrickGPT原版_AB对照实验_20261109\ab_experiment_20261109\summary.jsonl` 和 `D:\BrickMore\Deploy\build\comparison_20261110\BrickMoreComparison\Provenance\brickgpt_generation_summary.jsonl` 核实。
- 推荐 ★：核实后在 §5.1 加一句：
  > “BrickGPT outputs are generated in its native $20^3$ world with [setting]”

  这能解释零件数差异（413.0 vs 152.3），属于协议透明，对审稿有利。核实不了就不写。约 40 分钟，+1 行。**需要用户同意**（属上一轮遗留 #13）。

### 3.L Limitations and Discussion（§6）

**L-1｜P0｜Scope 段改写，明确 Topic 5 定位和未来方向（不宣称已做）**
- 怎么改（替换 V1.5 的 Scope 段）：

```latex
\emph{Scope.} BrickMore studies spatial representation learning through data generation and supervised fine-tuning only; it performs no pretraining or reinforcement learning, and its generator is a text-only language model, with vision--language models used solely as evaluation metrics. Our evidence about the learned representation is geometric (stud connectivity of raw outputs) and perceptual (text--image alignment of renders); we do not evaluate it on a dedicated spatial-reasoning benchmark. 【The diagnostics suggest that the interlocking rule is the main missing constraint, which makes connectivity-aware decoding or connectivity-based rewards natural directions for future work.】
```

- 注意：“connectivity-based rewards” 只能作为**未来方向**，不能写成已做。
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

**APP-1｜U4｜中文历史图**：见 U4。推荐移除 image13–19。

**APP-2｜P1｜附录 A 新增英文“转换策略对比”表，替代被移除的 image14**

| Release | Rule | Passing | Voxel changes |
|---|---|---|---|
| Relaxed | each component grounded | 65,503 | — |
| Retile | each component grounded | 79,298 | +228,582 / −125 |

- 来源：`retile_assembly_80000\summary.json`。Relaxed 行的 voxel changes 需从 `relaxed_assembly_80000\assembly_summary.json` 读取；historical 表写的是 +428,278 / −38,230，**执行时核实后再填**。Strict v3 = 7,902 同样要从 `assembly_80000\assembly_summary.json` 核实后才能列入。
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

**B-1｜P1｜新增 3 条已核实文献**（meshgpt、llamamesh、spatialvlm，见 R-1/R-2）。执行时用 arXiv 页面补全作者列表。15 分钟。

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
- 不使用无法从原始文件复算的数字：人工判决 79/105、零训练重叠、82% 紧贴、108–124 s/条、45 条 union 修复（manifest 中 `union_dropped_bricks>0` 为 0 条，与 README 的 45 不一致，不用）。
- 不改主表、Table 4 的任何数值；不改“对齐最高 / P_inv 持平”的结论。
- 不在 PDF 中放作者、GitHub/HF 仓库名或本地路径。
- 不改 `aaai2027.sty` / `.bst`；不用禁用宏包（hyperref 等）或禁用命令（`\clearpage` 等）。

---

## 5. 新增 / 改动数字的来源对照表

| 数字 | 用于 | 来源文件（字段） |
|---|---|---|
| 65,503 → 79,298；13,795；+228,582 / −125；31,532 | D-1、APP-2 | `D:\BrickMore\Train\datasets\retile_assembly_80000\summary.json`（baselinePassed, geometryPassed, recoveredFailures, addedVoxelCount, removedVoxelCount, zeroVoxelChangeSuccessfulModels） |
| 79,301＝79,298−1,902+1,905 | 现有 | `D:\BrickMore\Train\datasets\CURRENT_DATASET_STATUS.md` |
| 79,322×5＝396,610；~2.19B tokens | U3 | `D:\BrickMore\downloads\BrickGPT-Qwen3-1.7B-BrickMore-48\README.md` |
| 525 prompts；46（8.8%）；13/9/9/7/8；sofa 8/25、basket 0/25、camera 0/25 | A-2、I-3、E-2、APP-3 | `D:\BrickMore\brickmore48_eval_630\manifests\manifest_w{0,1,2}.json`（solver_tier, level, category） |
| 479 失败；ncomp 中位 5、最小 2、最大 33；dup>0 50 条（≤5 的 41 条、中位 2）；dup=0 429 条；碎片 2,240（悬空 1,320 / 落地 920） | E-2 | `D:\BrickMore\brickmore48_eval_630\results\raw_failure_autopsy.json` |
| 档位 326/133/18/2；none_needed 46；regen 28；studOK 525；shape_preserved 525；raw_bricks 中位 183（77–623）；assembly_bricks 中位 452 | M-4、E-2 | 同上 manifest |
| 105 组等权 0.2347/0.1840/0.1257 vs 0.1511/0.1459/0.0318；未截断 PE 89 条 0.1821 vs 0.1445、SigLIP2 85 条 0.1088 vs 0.0301；分级别各表 | E-3、E-4 | `D:\BrickMore\Results\three_model_comparison_20261111\analysis\三模型测评结果分析.md` |
| PE＝余弦；SigLIP2＝sigmoid；VQAScore＝全词表 softmax 下 “Yes” 的概率 | E-1、U8 | `D:\BrickMore\Deploy\build\comparison_20261110\BrickMoreComparison\Scripts\evaluate_paper_images.py`（sha256 a90e851a6a01…，与 `comparison_full\{vqa,pe,siglip2}.config.json` 的 sources 一致） |
| 72 / 64 文本 token 上限 | 现有 | `comparison_full\pe.model.json`、`siglip2.model.json` |
| 胜 / 负 91/23、95/19、91/23 | U5 | `...\analysis\三模型测评结果分析.md`；逐条数据 `...\comparison_full\report\scores.csv` |
| OpenReview 截止 2026-11-20 19:59 UTC+8；作者对审稿人隐藏；需要 OpenReview profile | U2、时间线 | OpenReview API `AAAI.org/2027/Workshop/GSR-VLM/-/Submission`（duedate 1795175940000；authors.readers） |

新增文献核对（arXiv API，2026-11-15）：
- arXiv:2311.15475 MeshGPT；
- arXiv:2411.09595 LLaMA-Mesh；
- arXiv:2401.12168 SpatialVLM。

标题与前 6 位作者一致。会议 venue 未核实，一律只写 arXiv。

---

## 6. 风险登记

| 风险 | 影响 | 缓解 |
|---|---|---|
| 作者 OpenReview profile 审核来不及 | 无法提交 | **11-15 当天**全部注册，用机构邮箱 |
| U3 找不到训练清单 | 数字自相矛盾 | 用 D-2 的拆表 + 中性措辞兜底；如实保留 TODO |
| U10 权重版本不一致 | E-2 不能写进正文 | E-2 改为附录，并注明权重版本 `92d1c595`，或者整体不用 |
| 新增内容让正文超过 7 页 | 违规 | §1 的兜底顺序：拼图 → Table 2 → 其他 |
| 显著性检验有项目不显著 | 削弱表述 | 如实报告；结论保持“均值最高” |
| box 编译环境不可用 | 无法出 PDF | 用户本机 MiKTeX（U9），11-17 前装好并试编一次 |
| 时间不够 | 漏交 | 11-19 提交一版完整稿到 OpenReview（截止前可以修改），11-20 只做替换 |

---

## 7. 时间线（现在 2026-11-15 00:40 UTC+8 → 截止 2026-11-20 19:59 UTC+8）

| 时间（UTC+8） | 任务 | 负责 | 产出 / 验收 |
|---|---|---|---|
| 11-15（日）上午 | **用户决策 U1–U12**（逐条选 ★ 或替代项）；**所有作者注册 OpenReview profile**；用户开始在训练服务器找 U3 证据（`trainer_state.json`、训练 jsonl 行数） | 用户 | 决策清单；profile ID |
| 11-15 下午 | 复制 V1.5 → V1.6；执行 P0：A-2（保守版）、I-2、E-1、L-1、G-4、G-2 初查；编译、验收（G-1） | RB2 | V1.6 第 1 版 PDF，正文 ≤ 7 页 |
| 11-15 晚 | 复核 E-2 数字（再读 525 个 `raw_report.json` 统计 voxel_components；数 items_index 中 batch=2 的条目） | RB2 | NUMBERS_V1.6.md 初稿 |
| 11-16（一） | P1 内容：E-2 新小节与表、M-4、E-3、E-6、D-1、D-2（结构）、D-4、R-1/R-2/B-1、I-1/I-3/I-4、C-1、M-1（核实序列化排序）；若 U5 同意，跑显著性检验脚本 | RB2 | V1.6 第 2 版；significance.json |
| 11-17（二） | 附录：U4 执行（移除中文图）、APP-2/3/4、E-4；B-2 venue 核对；E-8（若同意）；用户本机装 MiKTeX 试编（U9） | RB2 + 用户 | V1.6 第 3 版；本机编译成功截图 / 日志 |
| 11-18（三） | 根据 U3 证据定稿 Table 1 / 附录 B；全文英语润色与术语统一（G-5）；G-6 数字逐一核对；页数终检 | RB2 | 内容冻结（content freeze） |
| 11-19（四） | 用户通读；修最后的小问题；**向 OpenReview 提交完整稿**（截止前可修改）；G-3 表单填完 | 用户 + RB2 | OpenReview 提交编号 |
| 11-20（五）12:00 前 | 只做必要替换（错别字、数字确认）；G-1/G-2 终检；上传最终 PDF | RB2 + 用户 | 最终 PDF |
| 11-20 12:00–19:59 | **缓冲期**，不再改内容，只处理上传或系统问题 | 用户 | 截止前完成（19:59 UTC+8） |

---

## 8. 条目统计核对

- **P0（9）**：G-1、G-2、G-3、A-2、I-2、E-1、L-1、S-2、S-3。
- **P1（19）**：G-5、G-6、I-1、I-3、I-4、R-1、R-2、D-1、D-2、D-4、M-1、M-4、E-2、E-3、E-4、E-6、C-1、APP-2、APP-3。
- **P2（9）**：G-4、G-7、A-3、I-5、R-3、D-5、D-6、M-3、E-7。
- **U（12）**：U1 标题；U2 作者 / 双盲；U3 79,301 vs 79,322 与 tokens；U4 中文历史图；U5 显著性检验；U6 空间推理评测；U7 消融；U8 PE/SigLIP2 定义；U9 编译环境；U10 权重版本；U11 Reproducibility checklist；U12 是否使用 525 条诊断。
- **另有引用型或从属条目，不单独计数**：A-1（=U1）、D-3（=U3）、M-2（=U10）、E-5（=U5）、E-8（并入上一轮 #13，执行需用户同意）、L-2、L-3、APP-1（=U4）、APP-4、APP-5、B-1、B-2、S-1（=U9）、S-4。

合计：独立条目 9 + 19 + 9 + 12 = **49**。

---

*本文件只写入 `D:\BrickMore\Essay\BrickMore\Plan_V1.6\PLAN_RB2_R0.md`。没有修改 V1.x 中的任何论文文件，也没有读取 RB1 的任何文件。*
