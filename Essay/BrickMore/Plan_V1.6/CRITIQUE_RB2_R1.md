# 对 RB1 计划（PLAN_RB1_R0.md）的交叉评审（RB2 · R1）

- 被评审文件：`D:\BrickMore\Essay\BrickMore\Plan_V1.6\PLAN_RB1_R0.md`（32,614 字节，SHA-256 `8C479495…35CC8ED`，2026-11-15 00:42 UTC+8）。
- 评审时间：2026-11-15 约 00:50–00:56（UTC+8）。
- 评审依据：V1.5 `main.tex`；项目文件（逐条列路径）；OpenReview API（`AAAI.org/2027/Workshop/GSR-VLM/-/Submission` 与同名 group）；https://gsr-vlm.org/ ；Overleaf 与 OpenReview 官方文档。
- **本文件只做评审，不修改任何论文文件。** 引用 RB1 条目时用其原编号（§0.x、A1–A9、B 表 T1–T10、C0.1–C12.4、D 表、E 日程、F 清单 #1–#16、G 风险）。
- 判定标准：只投 GSR-VLM Topic 5；AAAI-27 模板；正文 ≤ 7 页；截止 2026-11-20 19:59（UTC+8）；不虚构数字或文献；不称模型为 VLM；不宣称做过预训练或 RL。

## 0. 统计

| 类别 | 含义 | 条数 |
|---|---|---|
| **A** | 错误、遗漏、与证据不符 | 10 |
| **B** | 优先级不合理 | 4 |
| **C** | 超页或不符合时间线 | 3 |
| **D** | 违反 Topic 5 或防虚构规则 | 2 |
| **E** | 同意，并已吸收进 `PLAN_RB2_R1.md` | 12 |
| 合计 | | **31** |

总体评价：RB1 的数字核对**很扎实**。下列 RB1 数字我逐个复核，全部正确：

- `scores.csv`：462 行；三系统 `primary=True` 各 114 条；BrickMore stitched 110 / raw 4；L1–L5 条数 21/21/23/25/24；21 类；三系统 114 个 `prompt_id` 完全配对。
- 主表均值：0.2176 / 0.1856 / 0.1231、0.1401 / 0.1457 / 0.0297、0.0624 / 0.1302 / 0.0100；对 BrickGPT 胜 91 / 95 / 91，无平局。
- `brickgpt_generation_summary.jsonl`：114 条，`world_dim=20`、`max_bricks=200`、`seed=42` 全部一致；`stable` True 66 / False 48。
- 79,298 − 1,902 + 1,905 = 79,301（`CURRENT_DATASET_STATUS.md` 第 9、15、21 行）；79,301 × 5 = 396,505；24,448 × 25.3 × 3,600 = 2,226,723,840。
- 评测脚本中 VQAScore、SigLIP2、PE 三处定义的行号。
- OpenReview：`pdf` 上限 50 MB；license CC BY 4.0；截止 1795175940000＝2026-11-20 19:59 UTC+8；group 中联系邮箱 `li.li02@usc.edu`。

RB1 也没有称模型为 VLM，没有宣称做过预训练或 RL，没有引入未核实的文献。

**主要分歧在于方向。** RB1 基本是“维持现状 + 补口径说明”，几乎没有回答 Topic 5 的核心问题：数据生成和微调学到了什么空间结构、缺了什么。项目里现成的结构诊断证据，它完全没有使用（见 A-7）。

---

## A. 错误、遗漏、与证据不符（10）

### A-1 ｜ RB1 C9.1、F #9、§0.4、D 表“写入 BrickGPT world_dim / 66 stable”行：建议把 `max_bricks=200` 写进论文，但与同一文件的数据冲突
- 证据：`D:\BrickMore\Deploy\build\comparison_20261110\BrickMoreComparison\Provenance\brickgpt_generation_summary.jsonl` 本轮复算：
  - `brick_count` 大于 200 的有 **36 / 114**（最大 497），等于 200 的 3 条，小于 200 的 75 条；
  - 超过 200 的 36 条中，30 条 `n_regenerations=8` 且 `stable=False`，6 条 `stable=True`；
  - 论文主表 BrickGPT 平均零件数 152.3，正是该文件 `brick_count` 的均值 152.29。
- 问题：正文若写“generated with `max_bricks=200`”，同一页又报告零件数均值 152.3（其中 36 条超过 200），审稿人会直接看到矛盾。`max_bricks` 在 BrickGPT 代码中的确切含义（单次尝试上限、还是不含回滚重生成）本轮无法从项目文件确定，不能代为解释。
- 建议：只写可以自洽的部分——BrickGPT 在其原生 $20^3$ 世界、seed 42 下生成（见 E-5）。`max_bricks` 只有在用户说明其语义后才写。

### A-2 ｜ RB1 C9.1、§0.4、F #9：建议正文写“66 marked stable in the generation log”，造成评测不对称
- 证据：同一 jsonl 中，114 条全部是 `use_gurobi=False`、`max_regen=8`；`stable` 是 BrickGPT 自带物理稳定性检查的结果。V1.5 §5.1 与 §6 明确说 BrickMore **没有**做物理稳定性评测（$P_{\mathrm{inv}}=0$ “does not certify … stability”）。
- 问题：
  1. 只给基线报“48/114 不稳定”，而本方法不报，会被读成不对称地贬低基线，并立刻引出“BrickMore 稳定率是多少”——项目里没有对应数字；
  2. `use_gurobi=False` 时 `stable` 判定所用的稳定性分析是否与 BrickGPT 论文报告的配置相同，**需查证**，本轮未核实。
- 建议：正文不写 66/114。若用户坚持写，必须同时写对称的限制句（“BrickMore outputs were not evaluated with this stability check”），并且放附录。

### A-3 ｜ RB1 §0.3、A7“出处”：引用的评测脚本副本不是与评测记录哈希一致的那份
- 证据：RB1 行号取自 `D:\BrickMore\Evaluation\pipeline\evaluate_paper_images.py`，其 SHA-256 前缀为 **`afec56ebdfd7`**。`comparison_full\{vqa,pe,siglip2}.config.json` 的 `sources` 字段记录的是 **`a90e851a6a01…`**，对应 `D:\BrickMore\Deploy\build\comparison_20261110\BrickMoreComparison\Scripts\evaluate_paper_images.py`。
- 两份 diff 只有两处：L87 processor 元数据的序列化方式；Deploy 版 L196–199 多一段“全部缓存命中即返回”。三个指标的计算逻辑完全相同，所以 RB1 的**结论正确**。
- 建议：论文的证据链（`REVIEW_V1.6.md`、`NUMBERS_V1.6.md`）应引用哈希一致的 Deploy 副本。属于小问题。

### A-4 ｜ RB1 A7 建议句（以及 C9.1 P0）：替换整句时丢掉了 PE 的 72 token 上限和聚合方式
- V1.5 L207 原句写有 “whose text encoders read at most 72 and 64 tokens, respectively” 和 “maximum over its eight views, then averaged over prompts”。RB1 的替换句只保留 SigLIP2 的 64，丢了 PE 的 72（来源 `comparison_full\pe.model.json`）。替换的范围也不清楚，可能连同聚合说明一起被删掉。
- 建议：用 RB2 E-1 的完整替换句，同时写明 PE（余弦）、SigLIP2（sigmoid）、VQAScore（全词表 softmax 下 “Yes” 的概率），以及 72/64 token 上限和“8 视角取最大、再对 prompt 平均”。

### A-5 ｜ RB1 A9 第 1 点、F #16：“checklist 可作为 OpenReview 附加文件”不可行
- 证据：OpenReview Submission invitation 的 content 字段只有 `title`、`authors`、`paper_type`、`keywords`、`TLDR`、`abstract`、`pdf`、`email_sharing`、`data_release`（另有系统字段 venue/venueid）。**没有 supplementary material 字段**，也没有 checklist 字段。
- 建议：如果要附 checklist，只能放进 PDF 附录（不计页）。RB2 仍推荐不附（U11）。

### A-6 ｜ RB1 C2.1：把 Introduction 第 1 段的 “geometric reasoning and object assembly” 定性为 Topic 2 框句并决定“不动”，与官网不符
- 证据：https://gsr-vlm.org/ 的 Topic 05 原文是 “Learning spatial representations — Pretraining, fine-tuning, reinforcement learning, and data generation **for improving geometric and spatial reasoning**”。“geometric reasoning” 本身就是 Topic 5 的措辞。
- 问题：真正的风险不是“像 Topic 2”，而是正文没有证据说明学到了什么几何结构。RB1 因为这个误判，把引言、贡献、结论都标为“不动”（见 B-3）。
- 建议：保留这个词，同时补上“学到什么、缺什么”的证据和框句（RB2 I-1、I-3、E-2）。不要写 “improves spatial reasoning”。

### A-7 ｜ RB1 A6、D 表、C3–C10：遗漏项目中现成的 Topic 5 核心证据（最重要的分歧）
- RB1 的 Topic 5 补强只有 “L1–L5 分层均值”（仍是感知对齐分数）。它在 D 表写“空间推理新基准：否”“再训练消融：否”，但没有发现两份**不需要新实验**、直接回答 Topic 5 的现成文件：
  1. `D:\BrickMore\brickmore48_eval_630\manifests\manifest_w{0,1,2}.json` 与 `results\raw_failure_autopsy.json`（525 条额外提示词）：
     - 只有 46 条（8.8%）raw 输出不经修复就是单一钉柱连通；
     - 479 条失败全部分裂成 ≥ 2 个钉柱分量（中位 5，最大 33）；
     - 有重叠体素的只有 50 条（其中 41 条 ≤ 5 个），429 条无重叠；
     - 2,240 个脱离碎片中悬空 1,320、落地 920；
     - MILP 档位分布 326 / 133 / 18 / 2；`studOK` 525/525。
     
     这正是“微调学到的表示缺了哪条几何约束（层间咬合）”的直接几何探针。
  2. `D:\BrickMore\Train\datasets\retile_assembly_80000\summary.json`：数据生成与转换策略把几何通过数从 65,503 提到 79,298（救回 13,795；+228,582 / −125 体素）——数据生成环节的“效益”证据。
- 建议：按 RB2 E-2、D-1、M-4 写入（需用户确认 U10、U12）。正文约 +0.35 页，在预算之内。

### A-8 ｜ RB1 C4.2、C11：“不新增文献”，遗漏 Topic 5 直接相关的工作
- 本文本质上是“把 3D 结构序列化为文本，用语言模型微调学习”。审稿人会期待看到 LM 序列化 3D 生成的工作，以及工作坊主题下“合成空间数据 + 微调”的代表作。
- RB2 R0 已用 arXiv API 核对 3 条：MeshGPT（arXiv:2311.15475）、LLaMA-Mesh（arXiv:2411.09595）、SpatialVLM（arXiv:2401.12168），标题和前 6 位作者一致，venue 一律只写 arXiv。
- 建议：按 RB2 R-1、R-2、B-1 增加约 +0.12 页。SpatialVLM 句明确写 “BrickMore instead trains a text-only generator … uses vision–language models only for evaluation”，避免被读成 VLM。

### A-9 ｜ RB1 A8：以“便于作者共同检查”推荐 Overleaf 作为主路径
- 证据：Overleaf 官方 plan limits 页面（docs.overleaf.com，2026-11 读取）：免费版**每个项目只能邀请 1 名协作者**，编译超时 10 秒（付费 240 秒）。
- 本轮在 box 上实测：V1.4（与 V1.5 同结构，16 页）`latexmk -pdf` 全流程 3.6 秒，单次 pdflatex 0.8 秒。所以超时**不是**障碍。RB2 R0 U9 写的“可能超时”过度担心，R1 已更正。
- 真正的问题是：
  1. 免费版协作人数受限，与 RB1 的理由相反；
  2. 要把未发表稿件上传到第三方平台；
  3. box 的 TinyTeX 已产出合规 PDF。
- 建议：主路径用 box TinyTeX；本机 MiKTeX 作为备份；Overleaf（pdfLaTeX）作为第三备选，不作为主路径。

### A-10 ｜ RB1 A5：配对检验“不做多重比较校正”
- 3 个指标 × 2 个对手 = 6 次检验，不校正会被挑剔。
- 建议：主报告 Holm 校正后的符号检验（只用胜负数，最透明），Wilcoxon 作为辅助，bootstrap CI 可选。$P_{\mathrm{inv}}$ 不做检验（这一点同意 RB1，见 E-4）。本轮复算对 BrickNet 的胜场为 97 / 98 / 102（VQA / PE / SigLIP2，无平局，来源 `scores.csv`），仅作为计划依据，不预填 p 值。

---

## B. 优先级不合理（4）

### B-1 ｜ RB1 F #6、#7（以及 C8）：把“维持不变”的约束列为 P0 任务
- “Algorithm 1 留在正文”和“不改主表数字、不改结论方向、不宣称 RL/预训练/VLM”是**约束**，不需要执行动作。列成 P0 会稀释真正的 P0（指标定义、口径、匿名、编译）。
- 建议：移入“不做 / 约束清单”（RB2 §4）。

### B-2 ｜ RB1 A4、T8、F #13：中文历史图定为 P2、“保持现状”
- 理由：
  1. 英文工作坊投稿里出现中文坐标轴和图例，观感差；
  2. 这些图的图注自称 “require verification”，放进去等于主动给审稿人留下“数字不一致”的把柄；
  3. 它们不支撑 Topic 5 主论证。
- 建议：作为 U（待用户确认），推荐移除 image13–19，把能核实的数字用英文表格重给（RB2 U4、APP-2）。RB1 的“保持现状 + 段首说明”可以作为用户不同意删除时的**备选**，R1 已吸收为 U4 的选项 C′。

### B-3 ｜ RB1 C2.1、C2.3、C2.4、C4、C10.3：把所有 Topic 5 定位相关的改写标为 P2“不动”
- 本稿只投 Topic 5。引言的研究问题、贡献列表、相关工作、结论是审稿人判断“是否贴题”的主要位置。全部“不动”会让本文读起来仍是一个系统论文。
- 建议：至少 P1（RB2 I-1、I-3、I-4、R-1、R-2、C-1）。

### B-4 ｜ RB1 T7、F #11：L1–L5 分层定为“P1/P2 可选”
- 本轮已用 `scores.csv` 复算 L1–L5 三系统均值：BrickMore 在 15 个格子中全部最高，与 `三模型测评结果分析.md` 一致。
- 成本约 30 分钟，正文只增 1 句、附录 1 表，且直接回应“多粒度描述下学得是否稳定”。
- 建议：定为 P1（需用户同意引入新数字，同 RB2 E-3、E-4）。

---

## C. 超页或不符合时间线（3）

### C-1 ｜ RB1 E 日程 11-18 行、A2 风险：把“所有作者 OpenReview profile”放在 11-18 准备
- 证据：OpenReview 官方文档 “Signing up for OpenReview”：使用公共邮箱域名注册 “may take up to 2 weeks in moderation”。Submission 表单原文：“All authors must have an OpenReview profile prior to submitting a paper.”
- 问题：距截止约 5 天 19 小时。11-18 才注册，若有作者没有机构邮箱，几乎肯定来不及。**这是截止前最大的非写作风险。**
- 建议：**11-15 当天**全部作者注册或确认已有 profile，尽量添加并验证机构邮箱（RB2 U2 与 §7 已列）。

### C-2 ｜ RB1 B 页数预算：T5 估 +0.12–0.18 页；整体留下约 0.44 页不用
- 2–3 句协议说明在双栏下约 4–6 行，约 +0.05–0.08 页；按 A-1、A-2 删减后只剩半句，约 +0.02。
- RB1 的预算终点约 6.56 页，而 Topic 5 证据（A-7）一项都没放进去。不超页，但浪费了宝贵的空间。
- 建议：采用 RB2 的预算（约 +0.65 页，结束于 6.2–6.6 页），并保留 RB1“新表优先进附录”的原则。

### C-3 ｜ RB1 A3 末段、D 表：“若用户能在截稿前找到训练清单”没有设截止点
- 不设截止点，Table 1 就可能拖到 11-19 才定稿，挤压通读和上传时间。
- 建议：**11-17 24:00（UTC+8）为找证据的截止点**。届时找不到就启用兜底写法（RB2 U3 选项 C′，吸收自 RB1 A3），11-18 冻结内容。

---

## D. 违反 Topic 5 或防虚构规则（2）

### D-1 ｜ RB1 C5.3 建议表注、A3 第 4 点：“retained from the training report used in this manuscript”是无出处的来源声明
- 证据：RB1 自己在 §0.2 写明，2,228,044,818 “只出现在 V1.5 表 1（L115）及注释”，`trainer_state.json`、`build_stats.json`、`train_brickmore.log` 都没找到。项目中不存在一份可以称为 “training report” 的文件。
- 问题：把来源写成 “training report” 等于虚构证据链。
- 建议：如实写 “as recorded in our training run; the raw trainer log is being re-checked”，或在 U3 有结论前不写来源描述。

### D-2 ｜ RB1 C5.3 建议表注、A3 第 3 点：在匿名稿中写 “A released model card describes this corpus as 79,322 models”
- 证据：该模型卡对应公开的 HuggingFace 仓库 `Kyle308666/BrickGPT-Qwen3-1.7B-BrickMore-48`（`D:\BrickMore\downloads\BrickGPT-Qwen3-1.7B-BrickMore-48\README.md`）。
- 问题：
  1. 双盲投稿中提到“已发布的模型卡”，相当于给审稿人一个可以检索到作者账号的线索，有匿名风险；
  2. 等于在论文正文里自曝一个尚未解决的内部数字冲突。
- 建议：不在论文中提及模型卡。若 U3 无法解决，用不含乘法暗示的中性写法：拆表，并删除“模型数 × 5”的暗示（RB2 D-2、U3 C′）。

---

## E. 同意，并已吸收进 PLAN_RB2_R1.md（12）

| # | RB1 原条目 | 同意的内容 | R1 中的去处 |
|---|---|---|---|
| E-1 | A3 第 1–3 点；C5.3 | 79,301（整合几何通过）与 396,610（训练样本）**分开写**，不把 79,322 填进 “Integrated passing models” 格 | U3 新增兜底选项 C′（措辞按 D-1、D-2 修正） |
| E-2 | §0.2、A3 第 4 点 | 不用 24,448 × 25.3 h 的乘积替换 2,228,044,818（差 1,320,978） | U3、§4 不做清单 |
| E-3 | A3 第 5 点、C6.2、F #12 | 正文继续称 validation，必要时脚注说明模型卡称为 test | 新增 D-7（P2） |
| E-4 | A5 | $P_{\mathrm{inv}}$ 两者都是 0.00%，不做检验 | U5 |
| E-5 | C9.1（部分） | 说明 BrickGPT 在原生 $20^3$ 世界、seed 42 下生成（114 条全部） | E-8 重写；不含 max_bricks、stable（见 A-1、A-2） |
| E-6 | D 表“105 组等权”行 | 补充口径的数字必须重算后才能用 | E-3：等权与 L1–L5 已用 `scores.csv` 复算一致；“未截断子集”仍需执行前复算 |
| E-7 | E 末段编译检查 | 增加 `pdfinfo` 纸张为 letter、首页为 “Anonymous submission” 两项 | G-1 |
| E-8 | A2 第 3 点 | 可选：向组委会发一句询问双盲 | U2 可选子项（**由用户发送**，本计划不代发） |
| E-9 | A1 | 标题候选 “…by Agentic Data Generation and Language-Model Fine-Tuning” 直接对应 Topic 5 用词 | U1 新增选项 B′ |
| E-10 | A9 第 3 点、F #15 | `D:\BrickMore\Essay\BrickMore\abstract_introduction.md`（2026-11-14 00:45）不在 V1.6 范围 | §4 不做清单 |
| E-11 | G“把分析写成新实验” | 显著性和分层结果写成 “re-analysis of the existing per-prompt scores”，不写 “new evaluation” | U5、E-3 风险 |
| E-12 | C9.2、C9.3、F #7 | 主表与 Table 4 数字锁定（本轮复核主表均值与胜场一致） | §4 |

---

*本文件只写入 `D:\BrickMore\Essay\BrickMore\Plan_V1.6\CRITIQUE_RB2_R1.md`。未修改任何论文文件（V1.x 目录）；未修改 PLAN_RB1_R0.md 与 PLAN_RB2_R0.md。*
