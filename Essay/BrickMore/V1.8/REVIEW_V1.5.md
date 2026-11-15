# BrickMore V1.5 审稿与修订记录（第三轮）

- 工作目录：`D:\BrickMore\Essay\BrickMore\V1.5`（由 `V1.4` 完整复制，157 个文件）。**V1.2、V1.3、V1.4 均未改动。**
- 评审基准：[GSR-VLM](https://gsr-vlm.org/) Topic 5「Learning spatial representations」；**不考虑 Topic 2**。同时检查 V1.4（ReviewBot2）改动是否引入新错误。
- 本轮可直接做的：小幅修订；对照 [arXiv:2505.05469](https://arxiv.org/abs/2505.05469) 核对并更正 BrickGPT 配方表。
- 本轮不做（标「待用户确认」）：改标题；填写或改动作者信息（保持匿名占位）；新增实验、显著性检验、消融或任何新数字；删除或重绘含中文的历史图；裁定训练样本数 79,301 与 79,322 的冲突；改核心结论。Algorithm 1 保留在正文，不移入附录。不虚构数字，不宣称 RL / 预训练 / 模型是 VLM。

## 结果摘要

| 项目 | 结果 |
|---|---|
| 编译 | 在 Grok Bot box 上用已有 TinyTeX（TeX Live 2026，pdfTeX 1.40.29）执行 `latexmk -pdf`，exit 0。**未在用户电脑上安装任何软件。** |
| PDF | `V1.5\main.pdf`，共 **16 页**（letter） |
| 正文页数 | 正文（摘要→结论）在第 6 页左栏结束，References 从第 6 页左栏下部开始，附录 A 在第 6 页右栏参考文献之后接着出现 → **正文约 5.5–6 页，≤ 7 页** |
| 附录 | 约第 7–16 页（A 数据集历史图，B 训练细节与配方表，C 历史评测图，D 历史表格） |
| Algorithm 1 | 仍在正文第 4 页，未移动 |
| 匿名 | PDF 首页为 “Anonymous submission”，未见作者姓名、单位或邮箱 |
| 字体 | `pdffonts`：全部 Type 1、已嵌入，无 Type 3 |
| 引用 | 终稿无未定义引用/文献，无 Overfull，无 TeX 错误；仅有少量 Underfull |
| 本轮问题 | 新提出或重点核查 8 条（P1–P8）；直接修复 2 条（P1、P2）；其余为已达标确认或「待用户确认」 |

---

## 一、本轮问题与处理（P1–P8）

**P1. BrickGPT 配方表此前未对照原文（V1.3 #17 / V1.4 N21/原 #17）。**
处理：**已对照原文并更正/补全，数字原本即正确，未改任何已有数值。**
来源：BrickGPT / Pun et al.，[arXiv:2505.05469](https://arxiv.org/abs/2505.05469)（读取 HTML v3 与附录 A）。§5.1 写明 240k prompts、47k+ designs，以及“only up to 4096 tokens”；Appendix A Training details 写明：LoRA rank 32、alpha 16、dropout 0.05，仅 query/value、3.4M 参数；AdamW 学习率 0.002；cosine、100 warmup；global batch 64；3 epochs；8×NVIDIA RTX A6000、12 小时；基座 LLaMA-3.2-1B-Instruct。
与原表逐项核对后全部吻合（$2{\times}10^{-3}$ 即 0.002；47k / 240k；4,096 长度过滤）。本轮仅做与原文一致的表述补全：硬件写成 `8×RTX A6000`；LoRA 栏补上原文已有的 dropout 0.05；表注改为引用 `\cite{brickgpt}` 并写明取自 arXiv:2505.05469 的 §5.1 与附录 A；删除 `% TODO verify against BrickGPT paper`。我方（Qwen3）列数字未改。

**P2. 源码注释中的匿名风险。**
`main.tex` 样本数 TODO 注释含本地绝对路径 `D:\BrickMore\downloads\BrickGPT-Qwen3-1.7B-BrickMore-48\README.md`。虽不进入 PDF，但随源码提交可能暴露环境。
处理：已改为 “A released model card …”，去掉绝对路径。79,301 与 79,322、2.228B 与 ~2.19B 的冲突说明仍保留在注释中，按用户要求**不裁定**。作者栏仍为占位符；`[submission]` 模式下 PDF 显示 Anonymous submission。

**P3. 检查 ReviewBot2（V1.4）是否改动了此前已核对的评测数字。**
处理：主表 0.00% / 0.2176 / 0.1856 / 0.1231（BrickMore），BrickGPT 0.00% / 0.1401 / 0.1457 / 0.0297，BrickNet 21.99% / 0.0624 / 0.1302 / 0.0100，以及 91/95/91、零件数 413.0 / 152.3 / 23.3、raw/retiled 0.1897%→0、0.2065/0.2071、0.1858/0.1859、0.1379/0.1261 均与先前交叉核对一致。V1.4 新增的配对零件数 178.7 / 421.2 来自当时已有结果文件，本轮不改、不新造数字。

**P4. 移入附录后的交叉引用是否断裂。**
处理：正文对 `app:dataset`、`app:training`、`app:eval`、`tab:finetune-config`、`fig:teaser` 等引用在终稿中均已解析。配方表与验证损失表仅在附录出现，正文用文字指向附录，无悬空引用。

**P5. Algorithm 1 是否被误移到附录。**
处理：确认仍在正文（编译后第 4 页），未移动、未删除。

**P6. 模板与匿名是否因本轮改动而破坏。**
处理：仍为官方 `aaai2027.sty`（2027.1）+ `\usepackage[submission]{aaai2027}`，未改 sty/bst。PDF 无作者信息泄露。源码作者占位符按要求保留。

**P7. 少量 Underfull `\hbox`（贡献列表、Invalid placements 段、参考文献一行）。**
处理：属排版美观问题，不改会改变行距或措辞的句子，以免牵动 7 页边界。不修复，记录为次要残留。

**P8. 训练样本 79,301 与模型卡 79,322（×5=396,610）冲突（V1.4 N20）。**
处理：按用户要求只记录、不裁定。表 1 仍为 79,301 与 396,610，TODO 保留。

---

## 二、上一轮遗留问题状态

来源：`REVIEW_V1.3.md`、`REVIEW_V1.4.md`。

| 原项 | 状态 |
|---|---|
| V1.3 #1–#8、#9 模板、#10 篇幅、#14 摘要 110/4、#15 拼图图注、#18 相关工作、#20 术语、#21 指标定义、#25–#27 编译警告 | 保持已修（V1.4 已完成） |
| V1.3 #17 / V1.4 配方表未核对 | **本轮已修（P1）** |
| 源码路径注释 | **本轮已修（P2）** |
| 标题是否改为描述性标题（V1.4 N21） | 「待用户确认」，未改 |
| 作者信息与是否双盲（N22 / #11–#12） | 「待用户确认」，保持匿名占位 |
| 训练样本 79,301 vs 79,322、token 2.228B vs ~2.19B（N20 / #16） | 「待用户确认」，本轮不裁定（P8） |
| Reproducibility checklist（N23） | 「待用户确认」 |
| 附录中文历史图：重绘或删除（N24 / #19） | 「待用户确认」，仍保留在附录 |
| 用户本机无 pdfTeX（N25） | 「待用户确认」：本轮仍在 box 上编译；用户可用 MiKTeX/TeX Live 或 Overleaf（pdfLaTeX） |
| PE / SigLIP2 分数变换细节（N26） | 「待用户确认」 |
| BrickGPT 生成参数、105 组等权口径是否写入（#13 剩余） | 「待用户确认」 |
| 显著性检验（#22） | 「待用户确认」，不新造数字 |
| `abstract_introduction.md` 过时（#23） | 「待用户确认」，文件不在 V1.5 内，未改 |
| 是否补空间推理评测或数据消融（#24 延伸） | 「待用户确认」，属新实验 |

---

## 三、Topic 5 契合度

总体仍为**中等偏好**，对应 Topic 5 中的 **data generation + fine-tuning**，不含 pretraining 与 RL。

正文对应点（V1.4 已写明，本轮未改口径）：
- 数据生成：agentic batch generation 得到 80,000 个 $48^3$ 模型与五级双语描述，几何检查后 79,301 个可用布局，作为空间表示学习的语料。
- 微调：Qwen3-1.7B + LoRA，固定空间序列化（Y 优先）、20 种积木与 $48^3$ 工作空间决定学到的离散空间表示。
- 几何约束进入学习与推理：覆盖、接地、六邻接检查，以及生成后 MILP exact cover 与单一钉柱连通。
- Limitations 的 Scope 句已写明：不做预训练或强化学习；生成器是纯文本语言模型；VLM 只用于渲染图评测。5.4 节已写明三项指标不是专门的空间推理基准。

仍偏弱、且本轮按规则不补的部分：没有专门空间推理评测或数据消融；工作坊主题是 VLM，生成器不是 VLM。这些若要加强，需用户批准新实验或改写讨论，不能把现有对齐分数写成“提升了空间推理”。

---

## 四、「待用户确认」清单

1. 标题是否改为描述性 mixed-case 标题（现为 “BrickMore”）。
2. 作者信息：保持匿名投稿还是填实名（需先核实工作坊是否双盲）。
3. 训练样本口径：79,301 还是 79,322，以及 2,228,044,818 与约 2.19B tokens。
4. 是否提交 AAAI reproducibility checklist。
5. 附录含中文标注的历史图：重绘英文版或删除。
6. 用户本机编译环境（安装 TeX 或使用 Overleaf）。
7. PE / SigLIP2 分数是余弦还是 sigmoid 等精确定义。
8. 是否在正文补充 BrickGPT 侧生成限制（world_dim=20 等）及 105 组等权口径。
9. 是否基于已有 per-prompt 记录补显著性检验（会新增数字）。
10. 是否同步或作废 `D:\BrickMore\Essay\BrickMore\abstract_introduction.md`。
11. 是否补空间推理评测或数据消融以加强 Topic 5。

---

## 五、编译记录

- 环境：box 上 TinyTeX / TeX Live 2026，pdfTeX 1.40.29，`latexmk -pdf -interaction=nonstopmode`，exit 0。所需宏包已齐全，无需本轮新装。用户机器未安装任何软件。
- 终稿日志：无 `!` 错误、无 Overfull、无未定义引用或文献。
- 字体：全部嵌入 Type 1。
- 页面：共 16 页；正文在第 6 页结论处结束（≤ 7 页）；参考文献第 6 页起；附录约第 7–16 页。
- 时间：`main.pdf` 生成于 2026-11-14 23:37（UTC+8）。
