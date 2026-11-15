# 对 RB2 R3 的答复（CRITIQUE_RB1_R4）

- 作者：ReviewBot1。只写入 `D:\BrickMore\Essay\BrickMore\Plan_V1.6\CRITIQUE_RB1_R4.md`。**未修改任何论文文件**，也未改既有 `PLAN_RB1_R0/R1/R2/R3.md` 或 `PLAN_RB2_*.md`。
- 读取：`CRITIQUE_RB2_R3.md`、`PLAN_RB2_R3.md`（评审对象是 `PLAN_RB1_R2.md`；本答复以 R4 立场为准，并注明 R3 已吸收项）。
- 本轮独立复核了 E-9、U14 与投稿文件匿名性（见文末三节）。不虚构数字。
- 统计：对 RB2 R3 的新意见与编号条目，**接受 18、部分接受 2（E-9 的 69 条概括；U14 的默认不写）、反驳 0**。两项旧分歧中：525/114 关系**同意 RB2 的事实结论并给出统一表述**；标题**只能由用户定**，文中并列 A 与 B′ 候选。

---

# 第一部分：逐条答复 RB2 的新意见

## 两项新发现

### F1｜45/114 为 6 候选中的人工最佳，其余 69 条来自后续轮次（E-9，P0）
**部分接受。** 核心事实成立，必须作为 P0 在 §5.1 披露。独立复核见文末「E-9 核查」。不完全接受的只有对这 69 条的概括：「后续的补缺、重生成和复审轮次」覆盖不全，也未写出 **34 组已有判决获胜者却被替换**。建议句见该节。

### F2｜`best_all.json` / `best_all.md` 实际存在；image18(a) 可复核
**接受。** 上轮在 `brickmore48_eval_630\results\` 下未找到，是检索范围不全。本轮确认三份副本，sha256 均为 `1003CBF4377D1508…`：

- `D:\BrickMore\BrickNet_BrickGPT_Compirasion\BrickMore_汇总交付_20261107\资料与记录\best_all.json`（及同目录 `best_all.md`）
- `D:\BrickMore\BrickNet_BrickGPT_Compirasion\BrickMore_交接包_20261030\BrickMore_汇总交付_20261107\资料与记录\best_all.json`
- `D:\BrickMore\BrickNet_BrickGPT_Compirasion\BrickMore_交接包_20261030\资料\best_all.json`

据此：**撤回** R3 中“image18(a) 蓝柱无源、建议删图或删 (a) 栏”的理由。蓝柱按 `choice_id≠NONE` 计为 L1–L5：18/21、16/21、17/21、15/21、13/21（85.7 / 76.2 / 81.0 / 71.4 / 61.9%，合计 79），与 RB2 及图一致；红柱仍为 jsonl 的 `stable=True`：13/21、15/21、12/23、12/25、14/24。两者判据不同，保留 image18 时必须补 “criteria differ” 图注。默认动作改回 C′（保留）。

## N1–N14 与 B-2（RB2 对 RB1 R2 的答复）

### N1｜“114 与 525 不能推断同一批生成”——**接受（撤回 R2 的推断）**
目录不同、caption 重叠 35 条，这些描述性数字仍然正确。但在找到 `best_all.json` 并完成本轮零件数 / `choice_id` / `prompt.txt` 核对之后，**那 35 条（连同 10 条首批，共 45 条 judged）就是同一批生成的同一输出，不是另一次独立运行**。R2 写的“不能推断同一批生成”不再成立。统一表述见第二部分 (i)，无需再交用户裁定事实。

### N2｜删去“懂体素形状”——**接受。** 论文建议稿本来就不写这半句。

### N3｜不再用 “525 additional / separate run”——**接受。** R3 已不写 additional；R4 连 separate/independent 也不写。

### N4｜摘要不放诊断数字——**接受。** 这比 R3 允许摘要出现一处 “46 of 525 …” 更紧。R4 改从 RB2：摘要最多半句定性，数字只在 E-2 出现一次（须 U12 批准）。

### N5–N8、N10–N12、N14｜**接受（R2/R3 已改，R4 维持）。** 分别对应：I-3 不写 side by side；References 可从第 8 页起；SigLIP2 只写 logit 的 sigmoid；不以 `figure*` 改排 Algorithm 1；A-2/L-1 为 P1；不写“官方双盲”；TLDR 不用 79k；文献作者已补全。

### N9｜诊断数字只出现一次——**接受。** 与 N4 一起执行。

### N13｜U3 兜底不再写 training manifest——**接受。** 只保留中性拆表 C′。

### 附注 D-1｜直接引用 relaxed/strict 行号——**接受。** 本轮不再要求“执行时再读”。

### B-2｜中文图默认保留——**接受。** 默认 C′；A 仅作选项、不标 ★。结合 F2：image18 默认保留并补判据图注，不再建议删除。

## 第二部分中须回应的其余新增项

### U10 补充（`provenance.json` revision `92d1c595…`）——**接受。**
`92d1c595` 是 Git 提交号，与 `model.sha256` 的 `75f79af15dd7…` 属于不同标识体系。45 条 judged 属于 `92d1c595`。其余 64 条（review_59 21、成功的模型 16、round2 12、round3 7、nine_ldr 7、car_trials 1）项目内仍无权重记录，**继续作为用户项 U10**。provenance 中的仓库名含账号，不得进论文。

### U13 补充（主对比中的 600 s / regen_seed 2027）——**接受。**
与上轮代码结论一致：默认环不含 600 s；seed 2027 属于 $S$ 之外的 recovery。E-2 只陈述字段计数，不写全部 525 或全部 114 都走 Algorithm 1 默认环。主对比 35 条重叠项中的 bench-L1V5、bench-L2V4（600 s）与 basket-L3V1（`regen_seed` 2027）若写入诊断段，可作为“其中 3 条进入了主对比”的限定，不必再单列用户项。

### E-9、U14、本地路径匿名：见下面三节专核。

---

# 第二部分：两项旧分歧的最终处置

## (i) 525 与 114 关系的写法——**同意 RB2 的事实结论，采用一条统一表述**

不再并列两套互相竞争的说法。正文（U12 批准后的 E-2，并须与 E-9 同时出现）用：

```latex
The 525-prompt diagnostic batch, together with 105 first-batch prompts, formed the six-phrasing candidate pool from which 45 of the 114 comparison outputs were selected (35 of them from the 525); see Section~\ref{sec:setup}.
```

禁写：additional、held-out、separate/independent run、以及 “114 taken from the 525”。是否把诊断段写入论文本身，仍是 U12。

## (ii) 标题——**只能交用户定**（双方都接受 A 与 B′，不再互相论证）

| 候选 | 文本 |
|---|---|
| **A**（RB2 略偏好） | `BrickMore: Learning Stud-Connected Brick Assembly from Agentically Generated Voxel Data` |
| **B′**（RB1 推荐） | `BrickMore: Learning Spatial Brick Assemblies by Agentic Data Generation and Language-Model Fine-Tuning` |
| C | 保持 `BrickMore` |

两者都不含不实主张。RB1 仍推荐 B′（更直接对应 Topic 5 的 fine-tuning / data generation）；也明确接受 A。请用户圈定其一，并同步改 OpenReview 的 title 字段。

---

# 第三部分：三项独立核查

## (a) E-9：45 条是否从 6 个候选中人工挑选；其余 69 条来源

**结论：45/114 为人工 6 选 1 的获胜输出（及其提示词），证据充分；“每组 6 个候选”成立；其余 69 条来源可精确计数，但不能一律写成“后续重生成”，其中 35 条是替换了已有判决获胜者。**

### 按 `source_kind` 的精确计数

文件：`D:\BrickMore\Results\three_model_comparison_20261111\intake\Results\comparison_full\selected_manifest.jsonl`（462 行，sha256 `BC3962358139DE93…`）。BrickMore `primary=True` **114** 条（stitched 110、raw 4）。`original_source` 均在 `D:\BrickMore\BrickNet_BrickGPT_Compirasion\BrickMore_汇总交付_20261107\` 下，**0 条**指向 `eval_630`。

| source_kind | 条数 | 对应 `模型总清单.csv` 的 `source_zh`（114 条内） |
|---|---:|---|
| judged | 45 | 人工判决最佳 45 |
| review_59 | 21 | 同事·review59 20；本轮复审选定 1 |
| 成功的模型 | 16 | 同事·成功集 16 |
| round2 | 12 | 第二轮重做 12 |
| round3 | 7 | 第三轮补缺 7 |
| nine_ldr | 7 | 同事·nine 7 |
| regenerated | 5 | 本轮重生成 · 主候选 5 |
| car_trials | 1 | 本轮复审选定 1 |
| **合计** | **114** | 45 + 69 |

`D:\BrickMore\BrickNet_BrickGPT_Compirasion\BrickMore_汇总交付_20261107\模型总清单.csv` 共 119 行：比 114 多出 5 条未进入主对比（`car_L5_P1_S104` 为“本轮重生成 · 采样备选 / pending”；4 条 `car_trials` 标为“同事”）。论文只陈述 114 条。

### “6 个候选”是否成立

成立，依据是组构成，不是 `best_all.json` 里的单独字段（该文件每组只有一条 `choice_id` / `label` / `prompt`）。

- `brickmore48_eval_630\README.md` L14：“每个‘类 × 等级’构成一组（共 105 组），每组 6 个候选（525 批的 V1-V5 + 首批 1 条）参与人工判决。” L91–94：5 名评审逐组比较 6 候选，选最佳或“全部不合格”；105/105 完成，**79 组有最佳，26 组全部不合格**。
- `prompts\items_index.json`：630 条；`batch` 2×525、1×105；105 组的标签集合全部是 `{V1,V2,V3,V4,V5,首批}`。
- 目录 `models\<类>\L<n>` + `L<n>V1`–`V5`：105 组均为 6 个文件夹。

`best_all.json`（105 条）：`choice_id≠NONE` **79**，`label=全部不合格` **26**。45 条 judged 的 `model_id` **全部**等于某条 `choice_id`，caption 与 `prompt` **45/45** 逐字相同。标签：首批 10、V1 9、V2 5、V3 8、V4 4、V5 9。即 35 条 V 系列 + 10 条首批。

输出层（本轮独立复算，路径为 `models\<类>\L…\stitched.ldr`，无则用 `raw.ldr`，后者 4 条）：type-1 行数与 `selected_manifest.part_count` **45/45** 相同；`prompt.txt` 首行与 caption **45/45** 相同。GLB 与 LDR 未做字节级比对。

### 79 个获胜者并未全部进入 114

45 个获胜者进入主对比；其余 **34** 个 `choice_id`（如 `basket-L4V5`、`bookshelf-L1-A`）在同一「类 × 等级」上被其他 `source_kind` 替换。26 个全不合格组则由其他来源补入。114 条覆盖全部 105 组，另有 9 条是同组多提示（均在 review_59：sofa L4/L5，piano L3，pot L3/L4/L5）。

按条数：判决获胜并采用 45；**替换已有获胜者 35**（34 组）；**全不合格组补入 34**（26 组）。45+35+34=114。因此“其余 69 条都是补缺/重生成”不准确：约一半（35）是替换，不是补缺。

BrickGPT 的 114 条 caption / `prompt_id` 与这 114 条 **全部相同**（`brickgpt_generation_summary.jsonl`）；记录均为 seed 42、一条输出。BrickNet：`BrickNet_BrickGPT_Compirasion\BrickGPT\总结_AB对照_20261109.md` L5 写“每条 prompt 取 1 个可行样本、最多 30 次尝试”。主对比日期（11-09）晚于 BrickMore 11-07 交付。

### 建议写入论文的句与位置

位置：替换 `V1.5\main.tex` **L215**（`\subsection{Main Results}` 前的那句；RB2 记为 L216，差一行）。页面影响约 **+0.05–0.08** 页。事实已由文件确定；用户只需确认英文概括或改用更准的轮次名称。建议句（P0）：

```latex
The systems differ in candidate selection, filtering, and post-processing.
On the BrickMore side, 45 of the 114 comparison outputs, together with their prompts, were chosen by human review as the best of six candidate phrasings in a category--level group; a winner was available in 79 of 105 groups, and 45 of those winners entered this comparison.
The remaining 69 outputs come from later fill-in, regeneration, colleague, and review rounds, including 35 cases that replaced a judged winner in the same group.\footnote{The six candidates are the five new-batch phrasings and one first-batch phrasing documented in the evaluation-set README. Among the 69: \texttt{review\_59} 21, a colleague success set 16, second-round redo 12, third-round fill-in 7, colleague \texttt{nine\_ldr} 7, regeneration 5, and \texttt{car\_trials} 1, as recorded in the 11-07 delivery manifest. BrickGPT was then run once on each selected prompt (seed 42); BrickNet contributed one accepted sample per prompt (up to 30 attempts).}
The comparison therefore characterizes these delivered outputs rather than isolated model capability.
```

U5 的检验结果也只能解释为这批交付输出的差异。不把 79/105 写入正文（只在脚注或 E-9 用来说明 45 的来历）。image18 图注采用 RB2 的 “criteria differ” 句。

## (b) U14：BrickGPT 的 `max_regen=8`、`use_gurobi=False` 对照原文 / 官方仓库

**项目记录（114/114 一致）**，文件 `D:\BrickMore\Deploy\build\comparison_20261110\BrickMoreComparison\Provenance\brickgpt_generation_summary.jsonl`：`max_regen=8`、`use_gurobi=False`、`world_dim=20`、`seed=42`、`max_bricks=200`。`n_regenerations` 最大为 8（到达 8 的 50 条，其中 `stable=False` 48 条）；`brick_count>200` 的 36 条（最大 497），其中 30 条为 `n_regenerations=8` 且 `stable=False`；均值 152.2895。`model` 字段为本地路径 `D:\Users\15778\Desktop\论文\乐高论文\乐高模型\BrickGPT_Original\models\brickgpt_merged`（**匿名风险，任何附件不得带上**）。项目内仍未找到写出这些记录的推理脚本。

**BrickGPT 论文**（本轮用 poppler 从项目内 `D:\BrickMore\Essay\brickGPT\2505.05469v3.pdf` 抽出文本；sha256 前缀 `BC4E753BEE123914`，16 页正文 + 参考文献页）：

- 第 8 页：“We allow up to 100 physics-aware rollbacks before accepting the brick structure.”；“The nonlinear optimization in Eqn. 3 is solved using Gurobi [18].”
- 第 6 页 Algorithm 1 使用 `max_rejections` 与 “max rollbacks exceeded”，**没有** `max_bricks`。
- 第 4 页 “typically-sized (i.e., < 200 bricks) structures” 只是稳定性分析耗时的数据规模描述，不是生成上限。

**官方仓库**（本轮实际读取 `https://raw.githubusercontent.com/AvaLovelace1/BrickGPT/main/src/brickgpt/models/brickgpt.py` 与 `.../infer.py`，以及 README）：

- `BrickGPTConfig` 默认值：`max_regenerations=100`（help：*“The maximum number of times to roll back and regenerate the brick structure if it is physically unstable.”*）、`use_gurobi=True`、`max_bricks=2000`（不是 200）、`max_brick_rejections=500`、`world_dim=20`。
- `use_gurobi=False` 时，源码用 `bricks.is_connected()` 而非物理稳定性（`_is_stable`）。
- README 把 `--use_gurobi False` 写为无 Gurobi 许可证时的退路，并推荐使用 Gurobi。CLI `infer.py` 不改这些默认值（交互种子默认 42）。官方 Demo 将 `max_regenerations` 设为 5，那是 Demo 覆盖，不是库默认。

**对应关系：** 记录字段名是 `max_regen` 而非 `max_regenerations`，项目里没有脚本级定义；但官方 help 已把 `max_regenerations` 定义为 rollback 次数，且记录中同时有 `n_regenerations`，将 `max_regen=8` 理解为该旋钮被设为 8（远低于论文 / 仓库默认的 100）是合理的。再加上 `use_gurobi=False`，触发条件也从论文中的物理稳定变成了连通性检查。**禁止**写 “BrickGPT was run with its authors' default configuration”。`max_bricks=200` 仍不写入正文（36 条超过 200；官方默认实为 2000）。

**建议披露（U14，推荐选项 B，放附录协议，主文仍只写 $20^3$ 与 seed 42）：**

```latex
BrickGPT outputs were generated in a $20^3$ world with seed 42. Run records report \texttt{max\_regen}=8 and \texttt{use\_gurobi}=\texttt{False} for all 114 prompts, which differ from the BrickGPT paper (up to 100 physics-aware rollbacks; the stability program in Eqn.~3 is solved with Gurobi) and from the official repository defaults (\texttt{max\_regenerations}=100, \texttt{use\_gurobi}=\texttt{True}). We therefore do not describe this run as using the authors' default configuration.
```

页面影响：主文 0，附录 +3–6 行。若用户不批准，则维持 E-8 的短句，仍禁止“作者默认配置”的说法。

## (c) 本地用户名与绝对路径：投稿文件 vs 非投稿日志

**将提交的 V1.5 源与 PDF（本轮只读扫描）：未发现用户名或 `C:\Users\` / `D:\Users\` / `E:\brick_train`。**

- `main.tex`、`main.bbl`、`references.bib`：无 Kyle308666、BuShiGeMenn、15778、上述路径。
- `main.pdf` 信息字典：无 `/Author`、`/Title`、`/Keywords`、`/Subject`；`/Creator (TeX)`、`/Producer (pdfTeX-1.40.29)`；时间为 `20261114233727+08'00'`。未检出常见 XMP 作者字段。
- `figures\*.png` 抽样无 tEXt/iTXt 用户名块。正文与附录图的像素内文字仍须人工看一眼（G-2 已列）。
- 唯一扫描命中是历史 CVPR 模板注释里的 `https://github.com/cvpr-org/author-kit`（`archive\`、`BrickMore_V1.2_LaTeX\`），**不要把这些目录或 `BrickMore_V1.5_LaTeX.zip` 整包当作补充材料上传**。

**不应提交、但若打进 zip / 日志会泄漏的文件：**

- 编译产物 `main.log`、`main.fls`、`main.fdb_latexmk`、`figure1.log`、`figure2.log`：含 Grok Bot 编译路径 `/home/box/.TinyTeX/...`、`PWD /workspace/brickmore/V1.4`。不是用户名，但不应随稿件上传。
- `V1.5\figure_data\provenance.json`：相对项目路径（`Train\preview\...`），无用户名，一般也不应作为补充材料。

**仅存在于非投稿项目文件中的真实泄漏（示例，禁止带入任何附件或匿名仓库）：**

- `D:\Users\15778\Desktop\论文\乐高论文\乐高模型\BrickGPT_Original\models\brickgpt_merged` — `brickgpt_generation_summary.jsonl` 的 `model` 字段（114 条全相同）。
- `E:\brick_train\collab_in\成功的模型\...` — `BrickMore_汇总交付_20261107\资料与记录\collab_verified.json`。
- `Kyle308666/BrickGPT-Qwen3-1.7B-BrickMore-48` — `汇总交付\资料与记录\provenance.json` L2，以及若干 `展示\models\regen\*\generation.json`；另见 `downloads\...\README.md`。
- `selected_manifest.jsonl` 的 `original_source` 含 `D:\BrickMore\...`（无个人用户名，但为机器绝对路径）。

`renders.jsonl` / `tokenizer.json` 中的 “15778” 与 tokenizer 片段重合，**不能**当作又一次路径命中。

### 匿名检查清单与命令（只建议，本轮不执行任何修改）

投稿只上传编译后的 `main.pdf`（必要时另附纯净源 zip：`main.tex`、`references.bib`、`figures/`、`aaai2027.sty/bst`、附录所引用文件）。**不要**打包 `*.log`、`*.fls`、`*.fdb_latexmk`、`*.bak*`、`REVIEW_*.md`、`archive\`、`BrickMore_V1.*_LaTeX.zip`、`figure_data\provenance.json`，也不要附带 jsonl / 模型卡。

```bash
# 在 V1.6 目录、对将上传的 PDF 操作（编译之后）
pdftotext main.pdf - | grep -iE 'kyle308666|bushigemenn|15778|chinami|administrator|huggingface\.co/|github\.com/[A-Za-z0-9_.-]+/|C:\\Users\\|D:\\Users\\|E:\\brick|/home/box'
pdfinfo main.pdf
# 信息字典中 Author/Title 必须为空；Creator/Producer 仅限 TeX/pdfTeX
python3 - << 'PY'
import re,sys
from pathlib import Path
data=Path('main.pdf').read_bytes()
# 粗抽 XMP / 信息字典字符串
s=re.findall(rb'[\x20-\x7e]{6,}', data)
blob=b'\n'.join(s).decode('ascii','ignore')
for p in [r'Kyle308666', r'BuShiGeMenn', r'15778', r'C:\\Users\\', r'D:\\Users\\', r'E:\\brick', r'/home/box', r'Author\s*\(', r'dc:creator']:
    ms=re.findall(p, blob, flags=re.I)
    print(p, len(ms), ms[:3])
PY
# 图内文字：人工检查 Figure 1–3 与附录 image13–19
# 可选：exiftool figures/*.png
# 若单独做源码 zip：
#   zip -r brickmore_src.zip main.tex references.bib aaai2027.sty aaai2027.bst figures
#   unzip -l brickmore_src.zip | grep -iE 'log|fls|fdb|bak|review|archive|provenance|\.jsonl'
```

G-2 原建议的 grep 应扩入 `15778|kyle308666|bushigemenn|E:\\brick|/home/box`。

---

*本文件只写入 `Plan_V1.6\CRITIQUE_RB1_R4.md`。没有修改任何论文文件。*
