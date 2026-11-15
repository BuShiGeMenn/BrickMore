# REVIEW_V1.6 — 由 V1.5 生成 V1.6 的逐条记录

- 生成时间：2026-11-15 约 03:30（UTC+8）。执行者：Grok Bot（RB2 工作流）。
- 依据：用户经 PRTS 圈定的决定 + `Plan_V1.6\FINAL_PLAN_V1.6.md`（含 7 处修改与「RB2 审阅记录」版本，SHA256 `E105E27D…C475`）。
- 基线：`V1.5\` 整目录复制为 `V1.6\`，只在 V1.6 内编辑。V1.5 / V1.4 / V1.3 / V1.2 未改动（V1.5 的 404 个文件 SHA256 与 mtime 已在开始前和结束后各记录一次并比对，见文末）。
- 编译：box 上 TinyTeX（pdfTeX-1.40.29）`latexmk -g -pdf -interaction=nonstopmode main.tex`。
- 行号均指 **V1.6\main.tex**（520 行）。
- 没有新实验、没有重跑生成；所有新数字都来自项目内已有文件，脚本与原始输出保存在 `V1.6\stats\`。

## 0. 结果摘要

| 项 | 结果 |
|---|---|
| 总页数 | 17 页（letter，612×792 pt） |
| 正文（摘要至结论） | 第 1–7 页；结论最后一行在第 7 页左栏；References 在第 7 页右栏至第 8 页前部，附录 A 从第 7 页右栏下部开始 |
| G-1 | 通过：日志无 `!`、无 undefined reference/citation、无 Overfull；32 个字体全部为已嵌入 Type 1；纸张 letter；pdfinfo 无 Title/Author，Creator=TeX，Producer=pdfTeX；第 1 页含 “Anonymous submission” |
| G-2 | 通过（PDF 与 tex/bib/historical_tables）：未检出 Kyle308666、BuShiGeMenn、15778、Administrator、CHINAMI、`C:\Users`、`D:\Users`、`E:\brick`、`/home/box`、`/workspace`、huggingface、github 账号、model card、trainer_state。图片内小字须人工目视（见 §4） |
| U5 显著性 | 6 组比较全部显著；Holm 校正后最大 p = 1.24×10⁻⁹（Wilcoxon，SigLIP2，对 BrickGPT）。详见 §2 |

## 1. 逐条执行记录

### 用户决定
| 条目 | 处理 | main.tex 行 |
|---|---|---|
| 标题（U1） | `\title{BrickForma: Text-to-Brick Generation with Voxel-to-Brick Data Construction and Geometric Reconstruction}`；删除旧 TODO 注释。标题在 PDF 中折为两行 | L23 |
| 改名 BrickMore→BrickForma | 方法/系统/流程处全部改名；BrickMore-48（数据集/训练模型名）和 BrickGPT、BrickNet 不改。清单见 §3 | 见 §3 |
| image18（U4-b） | 整个 `figure*` 用 `\iffalse … \fi` 包住，`figures/image18.png` 保留。原图没有 `\label`，全文没有指向它的 `\ref`，无需修 | L493–500 |
| U4（C′） | 附录 A 段首加 “Historical material with Chinese labels; not used for any claim.”；删去旧的 “Values, physical-screening coverage, and missing entries require verification.”；image14、image17 图注改为 “values as in the corresponding release reports”，image19 改为 “values as in the corresponding run records”（数字来源是 BrickGPT/BrickNet 运行记录，不是发布报告）；image15、image16 图注保留 “require verification”（未逐项复核/无来源） | L289, L339, L357, L505 |
| U12 + 摘要 N | 写入 525 诊断（E-2），摘要只加定性半句，不写计数 | L37–39（摘要）、L243–245（§5.3） |
| U5 | 已做，结果见 §2 | L241（正文 1 句）、L415–435（附录说明与 Table `tab:sig`） |
| U14（B） | 附录 C 加入运行配置披露段（含 RB2 补的两个限定从句）；主文只用 E-8 短句；未写 `max_bricks` | L413（附录）、L218（E-8） |
| E-9 | 写 45/35/34 拆分；比计划句多一句 “35 replaced a judged winner in 34 groups, and 34 filled 26 groups … together the 114 outputs cover all 105 groups”（数字与 FINAL 条目 10 / RB2 审阅记录核对 2 一致） | L219–223 |
| U10 | 未写 “all evaluated outputs use this checkpoint”。Table 2 “Released checkpoint: step 79,000” 与 §4.1 “released weights are those of step 79,000” 为 V1.5 原文，只描述发布权重，保留 | L137, L152 |
| U3 | Table 1 拆成 “Dataset (release reports)” 与 “Fine-tuning corpus” 两块，数字一个都没改；表注中性；删除 V1.5 L121–125 中提到模型卡 / trainer_state 的源码注释；表内两条 TODO 注释改为 `% 待用户确认 (U3)`。**待用户确认**（11-17 24:00 截止） | L103–127 |
| 作者信息 | 保持占位、`[submission]` 匿名模式 | L4, L24–31 |

### P0
| 条目 | 处理 | 行 |
|---|---|---|
| G-1 / G-2 | 见 §0 | — |
| G-3 | OpenReview 表单素材不在 PDF 内，本次未改；摘要与 PDF 一致的去 LaTeX 版本待提交时生成 | — |
| E-1 | 按计划替换指标定义句 | L210 |
| E-9 | 见上；`\subsection{Setup and Metrics}` 加 `\label{sec:setup}` | L206–207, L219–223 |
| S-2 | 已建立 `V1.6\`，交付物齐全；`stats\` 替代计划中的 `analysis\significance.*` 命名 | — |
| S-3 | 页数、匿名已检；源包白名单写入 README | — |

### P1
| 条目 | 处理 | 行 |
|---|---|---|
| A-2 | 摘要整段按计划替换，【】取定性半句；“BrickMore” 改为 “BrickForma” | L37–40 |
| I-1 | 第 1 段末加 testbed 句 | L49 |
| I-2 | V1.5 L56 与 L58 合并为一段；颜色句移到 §4.1 | L55 |
| I-3 | 新增定性预告段（含 U12 句） | L57 |
| I-4 | 贡献列表按计划改写（含 U12 半句） | L62–66 |
| I-5（P2） | 结果预告末加 “The ordering holds at every description level from L1 to L5 (Appendix C).” | L59 |
| R-1 / R-2 | 新增 “Language models for serialized 3D structure” 段与 SpatialVLM 句；bib 新增 meshgpt / llamamesh / spatialvlm（作者全名单按 PLAN_RB2_R4） | L86–89；`references.bib` 末尾 |
| B-2 | BrickNet：arXiv 摘要页（2026-11-15 读取）无 CVPR 录用信息，按计划改为只写 arXiv（`@misc`，arXiv:2604.22984） | `references.bib` |
| D-1 | §3.2 加转换效益句。复核：`Train\datasets\retile_assembly_80000\summary.json` `baselinePassed` 65503、`geometryPassed` 79298、`recoveredFailures` 13795、L449 `addedVoxelCount` 228582、L450 `removedVoxelCount` 125、L453 `zeroVoxelChangeSuccessfulModels` 31532 | L98 |
| D-2 | 见 U3 | L103–127 |
| D-4 | §3.1 原样引用 L1 caption；L5 caption 原样放附录 A。来源 `V1.6\figure2_units\references\birdhouse_prompts_L1_L5.json`，`modelId` = `vx80k5p_20261010_A_birdhouse_m0001`（A 分片数据集编号，属训练描述而非示意图专用） | L94, L291 |
| M-1 | §4.1 加表示说明句（弱化版，只说 “line-per-brick serialization … one footprint and one absolute position”，未写序列排序规则）+ “The current output does not include color.” | L133 |
| E-2 | 新增 §5.3 “Structural Diagnostics of Raw Outputs” 与附录表 `tab:diag`。全部数字本次重新点算：`raw_failure_autopsy.json`（525 条：ok 46；失败 479，分量中位 5、最大 33、最小 2；dup>0 50 条，其中 ≤5 的 41 条，中位 2，dup=0 429 条；碎片 2,240 = 空中 1,320 + 着地 920）；`manifest_w0–2.json`（525 行：tier 12s 326 / 60s 133 / 180s 18 / 600s 2 / none_needed 46；`regen_seed` 28 条；600s 两条为 bench L1V5、L2V4，不在 28 条内；`raw_single_component` 按级 13/9/9/7/8，sofa 8、basket 0、camera 0；studOK 525、shape_preserved 525；raw 砖数中位 183（77–623）；assembly 砖数中位 452） | L243–245, L473–491 |
| E-3 | 替换 “no significance test is reported”；105 组等权与未截断子集均已从记录复算（`stats\robustness.py`）：等权 0.2347/0.1840/0.1257 vs 0.1511/0.1459/0.0318；未截断 PE 89 条 0.1821 vs 0.1445；SigLIP2 85 条 0.1088 vs 0.0301。截断标记取自 `comparison_full\pe.jsonl` / `siglip2.jsonl` 的逐视角 `diagnostics[].text_truncated`（同一 prompt 在 3 个系统间一致） | L241 |
| E-4 | 附录 C 新增分级别表 `tab:levels`（15/15 格 BrickForma 最高） | L437–468 |
| E-6 | raw/retiled 解释句 | L265 |
| L-1 | Scope 段替换（含 U12 句） | L272 |
| L-2 | U3 未定，§6 Data accounting 未改 | — |
| L-3 | 删除 “Paired uncertainty analysis can be conducted…”，改为指向附录检验 | L276 |
| C-1 | 结论替换（含 U12 句） | L278–279 |
| APP-2 | 附录 A 新增英文转换表 `tab:conversion`（7,902；65,503 +428,278/−38,230；79,298 +228,582/−125），作为 C′ 的补充，不替代图 | L293–308 |
| APP-3 | 由 `tab:diag` 与 `tab:levels` 承载 | — |
| APP-4 | 附录 D 首段加 “main text takes precedence” 句（Appendix A 用 `\ref{app:dataset}`） | L517 |
| APP-5 | 等 U3，未写 | — |
| G-4/G-5 | `six-neighbour` → `six-neighbor`（2 处）；术语 raw/retiled、BrickForma/BrickMore-48 统一 | L98, L274 |
| G-6 | 所有新写入数字均已对源文件核对（见各条） | — |
| E-8 | 加在 E-9 之前 | L218 |
| M-4 | §4.2 末加 “Section 5.3 reports how often each repair tier is reached.” | L168 |
| S-4 | README.md 更新标题、命名说明、编译方法、stats 与投稿包白名单 | `README.md` |

### P2
| 条目 | 处理 |
|---|---|
| E-7 | Table 3 表头 “VQA” → “VQAScore”（L231）；Table 4 精度保持 0.1897% / 0.0000% |
| A-3 | “GPT-6.1 Sol” 全文字面一致，已检 |
| I-5 | 已做（L59） |
| G-7 | 剩 3 条轻微 Underfull（badness 1062–2057），无 Overfull；未改内容 |
| R-3、D-5、D-6、D-7、M-3 | 未做（无文件依据或无需要；正文仍 ≤7 页，Figure 3 浮动位置未动） |

### 计划外的最小修改（请用户过目）
1. L208：V1.5 “For BrickMore, the provided output is the first candidate, using the retiled layout when available” 改为 “For BrickForma, the provided output uses the retiled layout when available”。原因：E-9 写明 45 条是人工 6 选 1、其余来自后续轮次，“first candidate” 与之矛盾。**待用户确认**。
2. `archive\historical_tables.tex`（V1.6 内，被 `\input`）：两处图注中 “missing BrickMore entries” / “The original BrickMore column” 改为 “BrickMore-48”，与该表列头 “BrickMore-48” 一致。
3. 附录 C 中 original_comparison.png 图注改为 “Columns show raw and retiled outputs of our system and BrickGPT outputs.”（避免在图注中出现与图内文字不同的名字）。

## 2. 显著性检验（U5）实际结果

- 数据：`D:\BrickMore\Results\three_model_comparison_20261111\intake\Results\comparison_full\report\scores.csv`（项目内唯一含完整三系统 114 prompt 的 scores.csv；其他 6 个同名文件为 smoke/早期验证），原样复制为 `V1.6\stats\scores.csv`，SHA256 `5e16e25d336b56528376b83edd0b0a74eca688d0ce74f88a2803fadd34cd50fe`。
- 取 `primary=True`：每系统 114 行（BrickMore 110 stitched + 4 raw；BrickGPT 114；BrickNet 114）。按 `prompt_id` 配对，114 个 prompt 三系统齐全，caption 一致。
- 差值 = BrickForma − 对手。符号检验：双侧精确二项检验（去掉平局；本数据无平局）。Wilcoxon 符号秩：双侧，scipy 1.18.1 默认（n=114>50 → 正态近似，zero_method='wilcox'）。Holm 校正在 3 指标 × 2 对手 = 6 次内进行，符号检验与 Wilcoxon 各自一族。未检验 P_inv。
- 脚本：`stats\significance.py`；原始输出：`stats\significance_output.txt`、`stats\significance.json`。

| 对手 | 指标 | n | 胜/负/平 | 符号 p | 符号 p(Holm) | Wilcoxon W | Wilcoxon p | Wilcoxon p(Holm) |
|---|---|---|---|---|---|---|---|---|
| BrickGPT | VQAScore | 114 | 91/23/0 | 9.29e-11 | 1.86e-10 | 898 | 1.72e-11 | 3.45e-11 |
| BrickGPT | PE | 114 | 95/19/0 | 2.42e-13 | 7.26e-13 | 433 | 8.80e-16 | 4.40e-15 |
| BrickGPT | SigLIP2 | 114 | 91/23/0 | 9.29e-11 | 1.86e-10 | 1129 | 1.24e-09 | 1.24e-09 |
| BrickNet | VQAScore | 114 | 97/17/0 | 8.64e-15 | 3.45e-14 | 843 | 5.85e-12 | 1.75e-11 |
| BrickNet | PE | 114 | 98/16/0 | 1.48e-15 | 7.39e-15 | 275 | 2.08e-17 | 1.25e-16 |
| BrickNet | SigLIP2 | 114 | 102/12/0 | 6.01e-19 | 3.61e-18 | 740 | 7.26e-13 | 2.90e-12 |

- 均值与 Table 3 一致（0.2176/0.1856/0.1231 vs 0.1401/0.1457/0.0297 vs 0.0624/0.1302/0.0100）。
- 论文写法：正文 L241 一句（“every Holm-adjusted p is at most 1.3×10⁻⁹”，并说明只针对交付输出）；附录 Table `tab:sig` 列出 Holm 后 p（两位有效数字）。按 E-9，p 值不解释为孤立模型能力。

## 3. 改名清单（BrickMore → BrickForma）

已改（方法/系统/流程）：L23 标题；L38 摘要；L44 Figure 1 图注；L55 引言；L59 结果预告（3 处）；L78、L81、L84、L87、L89 相关工作；L129 §4 标题；L163 Figure 3 图注（2 处）；L171 Algorithm 1 标题；L208 §5.1；L218、L220 E-8/E-9；L233 Table 3 行名；L241 主结果段（多处）；L245 §5.3；L272 Scope；L279 结论（2 处）；附录 C（L415、L433、L445–461）。

未改（按指示保留）：BrickMore-48（L94、L133、L402，以及 `historical_tables.tex` 列头与 L65 行名）；BrickGPT、BrickNet 全部。

**不确定处（待用户确认）：**
1. **BrickMore-48 作为数据集名**：本文中 BrickMore-48 首先是数据集名（L94 “BrickMore-48 contains 80,000 voxel models”，L133 “fine-tune … on BrickMore-48”，附录 Table `tab:brickgpt-recipe` “BrickMore-48, 79.3k models”），同时也是训练模型名的一部分。按 “不改训练模型名（如 BrickMore-48）” 保留。是否希望数据集改称 BrickForma-48，请确认。
2. **§4 标题 “BrickForma Text-to-Brick Model”**（L129）：讲的是本文方法中的模型，已改；若用户认为这里指训练模型、应保留 BrickMore，请指出。
3. **Algorithm 1 标题 “BrickForma inference and retiling”**（L171）：视为方法，已改。
4. `historical_tables.tex` 两处 “BrickMore” → “BrickMore-48”（指历史表中的模型列）。

**图片文件内含 “BrickMore” 文字（未改图，待用户确认）：**
1. `figure1.pdf`（Figure 1，正文第 1 页）面板 (d) 标题 “(d) BrickMore model generation”——与图注 “BrickForma overview” 不一致。源为 `figure_tex\figure1_content.tex` L71；若要改，需改源并用 Tectonic 重编 figure1.pdf（本次未动）。
2. `figure2.pdf`（Figure 2，第 3 页）第 8 步节点 “BrickMore model”。源 `figure_tex\figure2_content.tex` L11。此处若指训练模型，可保留；若指系统，需改源重编。
3. `figures\original_comparison.png`（附录 C）列标题 “BrickMore (raw)” / “BrickMore (retiled)”。图注已改为中性写法。
4. `figures\image18.png`：已 `\iffalse` 移出 PDF，不影响。
5. 文件名 `figures\parts\brickmore__*.png` 只是素材文件名，不出现在 PDF 文字里。

## 4. 待用户确认汇总

1. U3 训练清单：Table 1 的 396,610 / 2,228,044,818 未改；11-17 24:00（UTC+8）前提供 `trainer_state.json` 或训练清单，否则维持现拆表。
2. U10 权重：未写 “all evaluated outputs use this checkpoint”；请书面确认 525/114 所用权重。
3. 改名不确定处与 3 个图内 “BrickMore” 文字（§3）。
4. 计划外最小修改 3 处（§1 末）。
5. E-9 脚注中各轮次的英文名称（review_59、colleague success set、second-round redo、third-round fill-in、nine_ldr、regeneration、car_trials）如有更准确叫法可替换，计数不变。
6. 图片内小字（Figure 1–3、附录 image13–17、19、original_comparison）请目视确认无作者信息；本次目视检查 image13–17、19、original_comparison、generated_gallery，未见姓名或路径。
7. V1.6 目录中从 V1.5 复制来的 `BrickMore_V1.5_LaTeX\`、`BrickMore_V1.5_LaTeX.zip`、`build_verification.json`、`main.tex.bak_*`、`REVIEW_V1.3–V1.5.md` 均原样保留（未删除）；它们属于 V1.5 状态，不要打进投稿包。`stats\pe.jsonl`、`stats\siglip2.jsonl` 含 `original_source` 绝对路径，同样不得上传。

## 5. V1.5 未改动的验证

开始前与结束后各对 `V1.5\` 全部 404 个文件记录 SHA256 + LastWriteTime + 长度（`%TEMP%\v15_before.txt` / `v15_after.txt`），结果见交付报告；V1.4、V1.3、V1.2 未被任何命令访问写入。

结果（2026-11-15 约 03:40 UTC+8）：V1.5 前后两次记录各 404 行，Compare-Object 差异 0 行（SHA256、mtime、长度全部一致）。
