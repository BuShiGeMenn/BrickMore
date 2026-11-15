# REVIEW_V1.7 — 由 V1.6 生成 V1.7 的逐条记录

- 源版本：`D:\BrickMore\Essay\BrickMore\V1.6`（只读，未改写）
- 本版本：`D:\BrickMore\Essay\BrickMore\V1.7`
- 日期：2026-11-15（UTC+8）
- 会议：GSR-VLM workshop（AAAI-27 AuthorKit27 匿名长文，Topic 5）；截稿 2026-11-20 19:59 UTC+8
- 编译：box TinyTeX（TeX Live 2026，pdfTeX 1.40.29），`latexmk -pdf`，工作目录 `/workspace/v17_build`
- 编译状态：成功。日志无 `!`、无 undefined reference/citation、无 Overfull；3 处 Underfull（与 V1.6 同类，不改内容）。全部嵌入字体为 Type 1。纸张 letter（612×792 pt）。`pdfinfo` 无 Title/Author 字段，Creator=TeX，Producer=pdfTeX-1.40.29。第 1 页含 “Anonymous submission”。

## 0. 结果摘要

| 项 | 结果 |
| --- | --- |
| 总页数 | 17 页（letter） |
| 正文（摘要至结论） | 第 1–7 页；结论结束于第 7 页左栏；References 紧接结论始于第 7 页左栏，延续至第 8 页前部；附录 A 从第 7 页右栏下部开始 |
| Algorithm 1 | 仍在正文，位于第 6 页顶部（未改成 figure*，未移入附录） |
| `main.tex` | **V1.7 未改正文/附录源码**（SHA256 与 V1.6 相同：`5569DB553C0F739E67EDFA7D32B8120C9ECAF6AF39E0CCBA5001FB2F7271FA87`） |
| `main.pdf` | 3,622,494 B，SHA256 `0734FBE71B4C9EF509EAA8FA4BA4C32AF586C9F561D76C2C148C26B5719E319E`，编译时间 2026-11-15 13:43:42 UTC+8 |

V1.6 已按 FINAL_PLAN_V1.6 与当时用户决定执行了标题、方法改名、image18 `\iffalse`、Table 1 拆分、E-8/E-9、显著性表、U14 附录披露、BrickNet 仅 arXiv 等。V1.7 的新增工作是：重绘三张图中作为方法名的 “BrickMore”→“BrickForma”，清理投稿禁带文件，重编 PDF，并留下未决项。

## 1. 哪些 FINAL_PLAN / 用户决定已在 V1.6 落地（V1.7 保持原状）

下列项在 V1.6 的 `main.tex` / `references.bib` / `REVIEW_V1.6.md` 中已经完成，V1.7 **没有重做、没有回退**：

- 标题（用户已定，不再改）：`BrickForma: Text-to-Brick Generation with Voxel-to-Brick Data Construction and Geometric Reconstruction`
- 方法/系统名 BrickForma；数据集与已训练模型名 BrickMore-48 未改；外部模型名 BrickGPT / BrickNet 未改
- image18：整图 `\iffalse … \fi`（约 L493–500），`figures/image18.png` 保留，未删除
- U10：未写 “all evaluated outputs use this checkpoint”
- U3：Table 1 已拆成 Dataset (release reports) 与 Fine-tuning corpus；数字未改（V1.7 仍无新的可核验训练清单，故未改数）
- V1.6 两处已批准措辞：(a) 原 L208 附近 “the first candidate” 已删除，未写回；(b) “together the 114 outputs cover all 105 groups” 保留
- BrickNet：仅 arXiv（正文 “Kulits and Schmid 2026”，bib 为 `@misc` / arXiv；全文无 “CVPR 2026”）
- E-8、E-9、525 作为候选库的表述、Holm 检验表、Algorithm 1 在正文、中文历史图 13–17/19 仍在附录

## 2. V1.7 新做的修改

### 2.1 图重生（本次唯一的内容性改动）

按用户确认：把图中作为**方法/论文名**的 BrickMore 改为 BrickForma；BrickMore-48、BrickGPT 等不改。先将 V1.6 图像与对应 TeX 源拷入 `V1.7\backup\`，再改源重编，不覆盖未归档原件。

| 图 | 源 | 改动 | 新文件（文件名未改，`\includegraphics` 不必改） |
| --- | --- | --- | --- |
| Figure 1 面板 (d) | `figure_tex\figure1_content.tex` L71 | `(d) BrickMore model generation` → `(d) BrickForma model generation` | `figure1.pdf`（及 `figures\figure1.png` 300 dpi 预览） |
| Figure 2 节点 8 | `figure_tex\figure2_content.tex` L11 | `8/BrickMore model` → `8/BrickForma model` | `figure2.pdf`（及 `figures\figure2.png`） |
| 附录 `original_comparison.png` 列标题 | 项目内未找到生成脚本 | 见下 | `figures\original_comparison.png`（同名替换） |

编译方式：在 box 上用 TinyTeX `pdflatex` 对独立 `figure1.tex` / `figure2.tex`（standalone + TikZ）重编；为避免 typwriter 落入 Type 3 位图，安装了 `cm-super` 后重编 Figure 2，主 PDF 与两图的嵌入字体均为 Type 1。

`original_comparison.png`：在 `D:\BrickMore` 与论文脚本中检索 `original_comparison`、`BrickMore (raw)` 等，**没有找到可再生成的 Python/SVG/PPT 源**。因此只在页眉文字带（y=0–60，该带内无模型彩色像素）做谨慎替换：用与原字最接近的 Liberation Sans Bold 40 pt（Arial 度量兼容，对原 “BrickMore (raw)” 的字形匹配优于其他候选）重绘两列标题，并按原列中心对齐：

- `BrickMore (raw)` → `BrickForma (raw)`
- `BrickMore (retiled)` → `BrickForma (retiled)`
- `BrickGPT` 列像素与 y≥60 的全部画面 **逐字节未改**（校验：BrickGPT 页眉区域与图身完全一致）

目视检查（Read 工具直读新图）：

- Figure 1 面板 (d) 标题为 **“(d) BrickForma model generation”**；面板 (a)(b)(c) 及其他标签无方法名 BrickMore。
- Figure 2 第 8 节点为 **“8 BrickForma model”**；其余节点（Specification、LLM programs、Training records 等）未改；无 BrickGPT/BrickMore-48 需要保留的冲突。
- 新 `original_comparison.png` 页眉为 **“BrickForma (raw)” / “BrickForma (retiled)” / “BrickGPT”**，列对齐正常，无互相重叠。

新文件 SHA256：

- `figure1.pdf`：`92DB008A7F5C0733763BC158EA83208A3337B14A96453F636A536FFB4DC1E11E`
- `figure2.pdf`：`71ECC99C76C14128F644BCEFD3F41E1401FE66C54BEB628AC61367A08BDE4248`
- `figures\original_comparison.png`：`C9CE917F9344145EA72E33B269339E295A6F39E8DD8995D981545F5DF606498E`

备份位置（均为替换前的 V1.6 副本）：

- `V1.7\backup\figure1.pdf`
- `V1.7\backup\figure2.pdf`
- `V1.7\backup\figure_tex\figure1_content.tex`
- `V1.7\backup\figure_tex\figure2_content.tex`
- `V1.7\backup\figures\original_comparison.png`
- `V1.7\backup\figures\figure1.png`、`figure2.png`
- `V1.7\backup\figure2_units\...` 与 `V1.7\backup\main.tex`

### 2.2 其它图中残留的 “BrickMore”（未静默重绘）

已检查并**未改**下列未在任务清单中的图：

- `figures\generated_gallery.png`：仅有类名与 raw/retiled，无方法名。
- `figures\original_overview.png`：列标题为 Voxel model / Target after repair / Brick layout，无方法名。该文件本身也不被 `main.tex` 引用。
- `figures\image18.png`：已 `\iffalse` 移出 PDF；未重绘。
- 素材文件名 `figures\parts\brickmore__*.png` 与 `\asset{brickmore__...}` 仅为文件名，不出现在 PDF 文字中，未改名。

**需记录的配套资产（不在投稿 PDF 中）：**

- 已同步修改源 `figure2_units\content\unit_08_brickmore_model.tex` 的 `\unitheader{8}{BrickForma model}`（与 Figure 2 节点 8 同一问题）。
- 但 **未重导出** `figure2_units\unit_08_brickmore_model.png` 与 `figure2_units\overview.png`。这两张配套图若仍含 “BrickMore model”，只存在于单位图包，不进入 `main.pdf`。建议 RB2 如需分发该 zip 时再重导；本次不把它们当作投稿图替换。

### 2.3 清理（只在 V1.7，不动 V1.6）

从 V1.6 复制时带入、不得进入投稿包的文件，已从 V1.7 目录中移除（或移入 backup 后不打进投稿 zip）：

- `BrickMore_V1.5_LaTeX.zip`
- `build_verification.json`（含嵌套副本若存在）
- `stats\pe.jsonl`、`stats\siglip2.jsonl`（含绝对路径）
- 根目录遗留 `main.tex.bak_*`（编辑用备份只保留在 `V1.7\backup\`）

`BrickMore_V1.5_LaTeX\`、`BrickMore_V1.2_LaTeX\` 历史目录、`REVIEW_V1.3–V1.6.md`、编译中间文件等仍可能留在 V1.7 工作树中，**一律不进入投稿 zip**。

### 2.4 未做的改动（按 brief 明确禁止或仍待确认）

- **未**新写或删除摘要中的 “46 of 525”。V1.6 摘要为定性表述，不含该短语；正文诊断节仍有 “Only 46 raw layouts (8.8%)…”（525 诊断，已有数据）。此项曾是计划分歧，V1.7 维持 V1.6 现状，列为待确认。
- **未**新加 U14 附录披露。V1.6 附录 C 已有该段（主文只用 E-8 短句）；按 “若 V1.6 已有则保留、brief 未把它列为新确认项” 处理，不增不删。RB1/RB2 对是否披露仍可能有不同意见，保持开放。
- 未改标题、作者信息、U3 数字、中文历史图 13–17/19、核心结论或任何新实验/新数字。
- 未把数据集名 BrickMore-48 改成 BrickForma-48。

## 3. 已保留的确认决定（核对）

- 标题：是，PDF 第 1 页两行标题与 `\title{...}` 一致。
- 方法名 BrickForma / 模型与数据集名 BrickMore-48：正文仅在 L94、L133、L402 等处保留 BrickMore-48；图内方法名已改。
- image18：`\iffalse` 仍在；PDF 全文无该图题 “Historical baseline comparison with differing…”。
- U10 措辞：全文无 “all evaluated outputs use this checkpoint”。
- U3 数字：未改。
- “the first candidate”：未写回。
- 114 覆盖全部 105 组：PDF 有 “the 114 outputs cover all 105 groups”。
- BrickNet：无 “CVPR 2026”。

## 4. 仍未解决 / 待用户确认

1. **数据集名 BrickMore-48**（本版本不得关闭）：正文把它同时用作数据集名与训练模型名的一部分。是否改为 BrickForma-48 请用户决定；V1.7 未改。
2. **U3 训练清单**：Table 1 的 396,610 / 2,228,044,818 等仍未用 `trainer_state.json` 复核。无新可靠日志则维持现数字与拆表。
3. **U10 权重**：请书面确认 525/114 评测所用 checkpoint 是否即为 step 79,000 的发布权重。
4. **U14**：附录披露已在 V1.6 写入并在 V1.7 保留；若用户后来决定改为完全不披露，需明确指示后再删。此为政策分歧残留，不是新实验。
5. **摘要 “46 of 525”**：维持 V1.6（摘要不含该短语，正文诊断节有 46/525 的 8.8% 表述）。若要写入或从正文删除，需用户确认。
6. **§4 标题 “BrickForma Text-to-Brick Model” 与 Algorithm 1 标题**：V1.6 已按方法名改；若用户认为应保留训练模型名 BrickMore，请指出。V1.7 未改。
7. **中文历史图 13–17/19**：仍在附录，按“未在 V1.6 确认删除则保留”。是否移出请用户/RB2 再议。
8. **E-9 脚注**中各轮次英文名称（`review_59`、`nine_ldr` 等）如有更准确叫法可替换，计数不变。
9. `figure2_units` 配套 PNG/overview 未重导（见 §2.2）。
10. `original_comparison.png` 因无脚本，为页眉像素级重绘而非从源再生；字形已尽量匹配，但不是逐像素复刻原 Arial。若用户有原始排版文件，可用源再生替换。

以上第 1 项必须保持开放。其余均非 V1.7 擅自做的大改；**没有已实施但未批准的重大改动**。无需要立刻阻断投稿准备的排版溢出（正文仍 ≤7 页，无需删内容）。

## 5. 建议 ReviewBot-RB2 下一轮重点检查

1. 目视三张新图：Figure 1(d)、Figure 2 节点 8、`original_comparison.png` 页眉，确认方法名为 BrickForma，BrickGPT 未被动，且无其它漏改。
2. 核对 `main.tex` 相对 V1.6 的 diff 应为**空**（除若存在换行/时间戳外，SHA256 应一致），避免误改数字或 E-9/U10 措辞。
3. U14 附录段与摘要 “46 of 525” 的政策状态：是否建议用户在提交前最终拍板。
4. 数据集名 BrickMore-48 是否与标题/方法名 BrickForma 并读别扭，但不要自行改名。
5. 投稿 zip 是否清净（无 zip/bak/jsonl/`build_verification.json`/REVIEW/backup/绝对路径日志）。
6. Type 1 字体与匿名性（`pdfinfo`、第 1 页 Anonymous、无用户路径）。
7. Algorithm 1 是否仍在第 6 页正文；正文是否仍在第 7 页内结束。
8. `figure2_units\overview.png` 若被误打包，其中可能仍是旧节点名。

## 6. 投稿 zip

已制作清洁投稿包（见 V1.7 目录下的 zip，若复制成功）。打包白名单仅含编译所需：`main.tex`、`main.pdf`、`references.bib`、`aaai2027.sty`、`aaai2027.bst`、`figure1.pdf`、`figure2.pdf`、`figure_tex\`、`figures\`（含 image18.png 源文件，但 PDF 中被 iffalse 排除）、`archive\historical_tables.tex`。明确排除：`*.log`、`*.fls`、`*.fdb_latexmk`、`*.aux`、`*.blg`、`*.bak*`、`REVIEW_*.md`、`backup\`、历史 `BrickMore_V1.*` 目录与 zip、`build_verification.json`、任何 `.jsonl`、`stats\` 数据、`figure_data\provenance.json`。

## 7. V1.6 未被修改的核验

复制 V1.7 前记录，并在复制后及本轮结束时复核：

| 文件 | SHA256（V1.6，应保持不变） |
| --- | --- |
| `V1.6\main.tex` | `5569DB553C0F739E67EDFA7D32B8120C9ECAF6AF39E0CCBA5001FB2F7271FA87` |
| `V1.6\main.pdf` | `C2601C79DCCF1FF3984721961EE89A4C6D5BAE1ED67B36F1CF9B9E3C84E45FC9` |
| `V1.6\REVIEW_V1.6.md` | `AB6A423039B379FD67D3D2E90F4F2DA28470538728BFA65D57728542B523E138` |
| `V1.6\references.bib` | `049DAA9C236909813B52ACBFDC1C8A64905A4FA89808B06E7CD50205D4DB95E1` |

`Plan_V1.6` 本轮只读，未写入。
