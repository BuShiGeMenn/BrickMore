# 对 PLAN_RB2_R0 的交叉审阅（CRITIQUE_RB1_R1）

- 作者：ReviewBot1。只写入 `D:\BrickMore\Essay\BrickMore\Plan_V1.6\CRITIQUE_RB1_R1.md`。**未修改任何论文版本文件**，也未改 `PLAN_RB1_R0.md` / `PLAN_RB2_R0.md`。
- 依据：通读 `PLAN_RB2_R0.md`；对照 `V1.5\main.tex`、`V1.5\REVIEW_V1.5.md`；并在本轮对 RB2 引用的项目文件做了复算或抽查（路径见各条）。
- 口径：GSR-VLM Topic 5；正文 ≤ 7 页；截止 2026-11-20 19:59 UTC+8；不虚构数字/文献；不宣称预训练、RL 或生成器是 VLM。

下文按 RB2 原编号/标题逐条。先列问题，再列同意并拟吸收的项。

---

## 一、错误、不精确、优先级或合规问题

**C1｜U2「结论：实际流程是双盲」**
官网 https://gsr-vlm.org/（2026-11-15 再读）仍无 double-blind 字样。OpenReview `authors` 字段的 readers 仅限组委会与 Submission Authors，这是很强的匿名审稿证据，**同意按匿名 PDF 准备**。但把“实际流程是双盲”写成已公布政策，略过满。论文和投稿说明里不宜自称“本工作坊官方宣布双盲”；应写“按 OpenReview 对作者字段的读者限制，PDF 保持 `[submission]` 匿名”。

**C2｜U3 选项 C「维持现状……不推荐」**
79,301 有 `Train\datasets\CURRENT_DATASET_STATUS.md` 支撑（79,298−1,902+1,905）；396,610 在论文表 1 与模型卡中一致。问题是二者相邻会被误乘，不是“不能同时出现”。在找不到 `trainer_state.json`（本轮与 V1.4 均未在 `D:\BrickMore` 找到）时，**更好的兜底是拆表/加注，同时保留两个口径**，而不是暗示必须删掉整合通过数。RB2 后文 D-2 的拆表其实已经提供了正确做法，与选项 C 的措辞不一致。另外，“24,448 tokens/s × 25.3 h ≈ 2.227B，与 2,228,044,818 自洽”只是量级接近：精确乘积为 2,226,723,840，相差 1,320,978，可用 25.3 为约数解释，但不可称为已核实的同一观测。

**C3｜U3 与 §3.3「Fine-tuning uses only geometrically passing models」**
同意这是真实风险（若训练清单是 79,322，未必等于整合通过 79,301）。但在用户拿出清单前，**不要**为了消除乘法矛盾而改写或删掉 79,301。RB2 选项 A（先找实测清单）正确，应作为前置条件。

**C4｜U4 ★A「从提交 PDF 中移除 image13–19」**
理由（英文稿中文图、图注自称待核实）成立，且 RB2 也标明须用户同意。但前几轮用户已规定：未经确认不得删除或重绘含中文的历史图。在 5 天截止内把“删除”作为默认推荐偏激进。RB1 维持默认**保留附录并加说明**；若用户明确选 A，则应按 RB2 用 `\iffalse` 注释、磁盘文件保留，并用已核实的英文表替代（见 D-1 / APP-2）。

**C5｜U9 ★A 以 box+MiKTeX 为主、Overleaf 为次**
“未发表稿不必上传第三方”和附录 PNG 可能导致 Overleaf 超时，是合理担忧，但不是会场强制规则。用户机器无 LaTeX 是事实（V1.4/V1.5）。**同意 box TinyTeX 已验证、应作为主编译**；Overleaf（pdfLaTeX）仍是合法备份，尤其当本机安装延误时。不宜把 Overleaf 排除出应急路径。

**C6｜A-2 标为 P0；L-1 标为 P0**
A-2 摘要重写（含 525 条诊断）**依赖 U12 / U10**，在用户未批准前不是合规必须项，应为 **P1（有条件）**。当前摘要在数字与 Topic 5 框句上已经可用。L-1：V1.5 Scope 句已经写明无预训练、无 RL、生成器非 VLM（`main.tex` §6），改写不是 P0。P0 应限于：口径说明、指标定义、匿名/编译/投稿、Algorithm 1 留在正文、不改已核对主表。

**C7｜A-2 / I-3 / I-4 / E-2 / C-1 对同一组诊断数字的重复**
RB2 在 I-2 批评 80,000 / 79,301 重复占用篇幅，却建议把 46/525（8.8%）、中位数 5 写入摘要、引言预告、贡献 3、新小节 E-2 和结论。这会抵消 I-2 省下的约 0.15 页，并有把“诊断”写成全文主结论的风险。建议：**数字只在 §5.x 出现一次**，摘要/引言/结论各留一句不含全表的定性指向。

**C8｜E-2 / U12 / A-2 将 525 条称为 “additional prompts”**
RB2 自己也写：114 条与 525 条的关系需用户说明；`selected_manifest.jsonl` 的 `model_id` 仅是命名相近。在关系确认前，正文写 “525 additional prompts” 可能不实（114 或取自同一批）。应改为 “525 prompts from `brickmore48_eval_630`” 或等用户说明后再写 additional / held-out / overlapping。

**C9｜A-2 初稿中的 “reproduces voxel-level shape well”**
RB2 已正确指出 autopsy 无形状保真字段，并给出保守版。但建议摘要里仍先出现了不可写的句子。执行时必须只用保守版，且须先按他们所说统计 `raw_report.json` 的 `voxel_components`——在该统计完成前，连“voxel-connected in most cases”也不要写。本轮复算仅确认了 manifest 的 `raw_single_component` 为 True 46 / False 479，**不能**据此声称体素形状保真。

**C10｜E-1「with the model's learned scale and bias」**
脚本 `evaluate_paper_images.py`（pipeline 与 Deploy 两份）写的是 `logits_per_image[:,0].float().sigmoid()`，没有单独乘 scale/bias 的代码行。scale/bias 可能已含在 transformers 的 `logits_per_image` 中，但**这不是项目脚本里的直接证据**。写入论文时应只写 “sigmoid of the image–text logit”。其余定义（PE 为归一化后点积即余弦；VQAScore 为全词表 softmax 下 Yes 的概率）与脚本一致，见下“同意”部分。

**C11｜§1 页面预算 / G-1「References 标题必须出现在第 7 页或更早」**
工作坊规则是**正文（至结论）≤ 7 页**，参考文献与附录不限。若结论在第 7 页末结束，References 可以从第 8 页开始。正确验收是：第 7 页之后不再有正文（摘要–结论）。“References 必须在第 7 页或更早”偏严，可能误导去压缩参考文献。

**C12｜页面预算偏乐观，以及兜底项「Algorithm 1 改为 figure* 紧凑版」**
E-2 单表 +0.35，再加上 I-3、R-1/R-2、D-1、E-3 等，合计 +0.65 是理想值，浮动体可能把结论推出第 7 页。兜底先移 Figure 3 可以接受。将 Algorithm 1 改排为 `figure*` **不建议作为兜底**：用户要求算法留在正文，改浮动类型易造成跨节漂移或被移到附录。超页时压缩诊断表（改放附录、正文留一段）优于改算法排版。

**C13｜L-1「connectivity-based rewards」作为未来方向**
已标明是未来工作，不构成“已做 RL”。但放在刚刚声明 “performs no … reinforcement learning” 的同一段，仍可能被快读误解。若保留，应写成 “outside the scope of this work” 一类，不要在摘要/贡献出现 reward / RL。

**C14｜G-3 TLDR 中的 “79k”**
在 79,301 与 79,322 未裁定前，不宜在对外字段用 79k 这种会指向某一模型数的约数。可写 “hundreds of thousands of caption–sequence pairs” 或等 U3 定稿后再写。

**C15｜B-1 文献条目作者列表不完整（执行风险，非 ID 错误）**
本轮用 arXiv API（2026-11-15）核对：
- arXiv:2311.15475 MeshGPT，8 位作者（RB2 草稿漏 Angela Dai、Matthias Nießner）；
- arXiv:2411.09595 LLaMA-Mesh，7 位（漏 Xiaohui Zeng）；
- arXiv:2401.12168 SpatialVLM，9 位（漏 Dorsa Sadigh、Leonidas Guibas、Fei Xia）。
标题与前六位作者与 RB2 一致。同意吸收这三篇，但执行时必须补全作者，venue 只写 arXiv（RB2 已注意 MeshGPT 的 CVPR 需另核，正确）。

---

## 二、本轮复算后，RB2 数字与文件相符的部分（不是问题）

以下条目的数字本轮已对照原始文件，**未发现编造**：

- **U7 / D-1 / §5 表**：`Train\datasets\retile_assembly_80000\summary.json` 中 `baselinePassed=65503`、`geometryPassed=79298`、`recoveredFailures=13795`、`addedVoxelCount=228582`、`removedVoxelCount=125`、`zeroVoxelChangeSuccessfulModels=31532`。另读 `Train\datasets\relaxed_assembly_80000\assembly_summary.json`：`geometryPassed=65503`，故 65,503 确为 relaxed 几何通过；该文件还有 `addedVoxelCount=428278`、`removedVoxelCount=38230`（RB2 要求 APP-2 核实后再写，谨慎正确）。
- **U12 / E-2 / M-4**：`brickmore48_eval_630\manifests\manifest_w{0,1,2}.json` 合计 525 条；`solver_tier` 为 12s 326、60s 133、180s 18、600s 2、`none_needed` 46；`studOK` 与 `shape_preserved` 均为 525；含 `regen_seed` 的 28 条；`raw_bricks` 中位 183（77–623）；`assembly_bricks` 中位 452；`union_dropped_bricks>0` 为 **0**（因此正确拒绝 README 的 45 条）；耗时中位 93.9 s、范围 22.9–401.6 s（因此正确拒绝 README 的 108–124 s/条）。`none_needed` 按级 13/9/9/7/8，sofa 8、basket/camera 0。`results\raw_failure_autopsy.json`：ok 46 / 失败 479；失败 `ncomp` 最小 2、中位 5、最大 33；`dup>0` 50（其中 ≤5 的 41、中位 2），`dup==0` 429；`orphan_n` 合计 2240，`orphan_air` 1320，`orphan_ground` 920。`results\best_all.json` / `best_all.md` **不存在**，拒绝 79/105 人工判决是对的。
- **U5**：`scores.csv` 114 条 primary 对齐后，BrickMore vs BrickGPT 的 VQA/PE/SigLIP2 为 91/0/23、95/0/19、91/0/23（与分析文档一致；本轮用 csv 复算，无平局）。
- **E-3**：`三模型测评结果分析.md` 中 105 组等权与未截断子集数字，按四位四舍五入后与 RB2 引用一致（BrickMore 0.234664/0.183975/0.125722 等；PE 89 条 0.182061 vs 0.144490；SigLIP2 85 条 0.108762 vs 0.030068）。L5 VQAScore 0.096763 / 0.074845 / 0.036335 与 I-5 引用一致。本轮未逐格重算全部 15 个 level 单元格，但源表存在且抽查相符。

---

## 三、同意并将吸收进 PLAN_RB1_R1 的项

- **U8 / E-1**：按脚本写清 PE＝余弦、SigLIP2＝logit 的 sigmoid、VQAScore＝全词表 softmax（吸收；删掉未在脚本中出现的 scale/bias 表述）。评测脚本与 `comparison_full\*.config.json` 的对应关系，RB2 的核实方向正确。
- **U10**：评测权重 `92d1c595` 与下载模型 `model.sha256` 标识体系不同，不能写 “all evaluated outputs use the step-79,000 checkpoint”，除非用户确认。新增为「待用户确认」。
- **U11**：官网与 OpenReview 表单未要求 checklist，推荐不附（与 R0 一致，维持）。
- **U12 / E-2 / M-4**：在用户批准且不写 “additional / spatial reasoning benchmark / 形状保真” 的前提下，这是 Topic 5 性价比最高的已有证据。数字本轮复算相符。RB1 吸收为 **P1，有条件**：正文一段 + 表（若超页则表改附录）；禁止在摘要/引言/结论重复全表。
- **U5 / E-5**：同意用已有 `scores.csv` 做符号检验与 Wilcoxon（可加 Holm），新 p 值须批准后写入，计划中不预填 p 值；不显著则如实写，不改“均值最高”结论。
- **U6 / U7**：截止前不新建空间推理基准、不重训。数据侧转换对比与 raw/retiled 可称 conversion/repair analysis，不叫 model ablation。同意。
- **D-1 / APP-2**：转换效益句可吸收（数字已核）；必须写明 65,503→79,298 是 relaxed→retile 发布，**不要**与 79,301 混为一谈。Relaxed 的体素改动 428,278 / 38,230 现已在 `relaxed_assembly_80000\assembly_summary.json` 读到，若写入须引用该文件。
- **D-2**：表 1 拆成 “release reports” 与 “fine-tuning corpus”，避免误乘。吸收，并与 RB1 的“两口径并存”兜底合并。
- **I-1**：Topic 5 “可精确检查的空间表示试验床”框句，吸收。
- **I-2**：引言去重以省页，**优先级改为 P1**；若删除引言中 “output does not include color”，必须移到 §4.1（V1.5 §4.1 确无此句）。吸收该风险提示。
- **I-4**：贡献改写方向可吸收；第 3 条诊断依赖 U12，未批准则只保留评测后半句。
- **R-1 / R-2 / B-1**：MeshGPT、LLaMA-Mesh、SpatialVLM 的 arXiv 号与标题已核；吸收段落方向；作者补全；不写“我们提升了 VLM”。
- **E-3 / E-4 / I-5**：105 组等权、未截断子集、L1–L5 表，来源文件存在且抽查相符；作为**补充口径**进附录、正文 1–2 句，不替代主表。吸收。
- **E-6**：改为 “same in-bounds voxel union”，吸收。
- **E-7**：P_inv 小数位与 “VQA”/“VQAScore” 统一，吸收（P2）。
- **E-8**：§5.1 写 BrickGPT `world_dim=20`、`max_bricks=200`、seed 42、日志中 66/114 stable。本轮已从 `Deploy\...\Provenance\brickgpt_generation_summary.jsonl` 复核（114 条全部为上述设置，stable True 66）。吸收。
- **G-2**：投稿前检索 Kyle308666、BuShiGeMenn、huggingface、github、`D:\` 等。`downloads\...\README.md` 与 `Train\datasets\piano_table_retile_7620\download_manifest.json` 中确有这些标识；V1.5 `main.tex` 当前无。吸收为 P0 检查。
- **G-3**：OpenReview 字段、全体作者先注册 profile（审核可能要几天）。吸收；TLDR 避免 79k。
- **G-4 / G-5 / G-6 / G-7**：美式拼写、术语统一、数字核对表、Underfull。吸收为 P1/P2。
- **§4 不做清单**中拒绝无法复算的 README 数字：同意，且本轮复算支持这些拒绝。
- **日程**：11-15 注册 OpenReview；11-19 提交完整稿；11-20 只做应急。与 R0 一致，吸收 profile 紧急项。
- **超页兜底顺序**：先移 Figure 3，再考虑把微调配置表并入附录；**不**把 Algorithm 1 移出正文。

---

## 四、小结（供 R1 计划使用）

RB2 的主要贡献是把项目里**已有但未入论文**的材料（eval_630 诊断、retile 转换效益、分析文档中的稳健性口径）组织成 Topic 5 论证，并且对不可复算数字做了明确剔除。这些方向 RB1 吸收。主要分歧是：525 条内容的优先级与铺陈密度、默认是否删除中文历史图、U3 兜底时是否保留 79,301、编译路径是否排除 Overleaf、以及若干 P0 标注与 “additional prompts / scale and bias / References 必须在第 7 页前” 等表述精度。
