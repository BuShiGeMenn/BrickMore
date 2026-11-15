# Figure 2：八个独立单元

本目录提供八张独立 PNG（300 dpi）及对应的可编辑 TikZ / LaTeX 源码，供逐项修改和重新组合。

1. `unit_01_pending`：第一单元待定，保留空白占位。
2. `unit_02_llm_code`：项目 `Train/programs/produce.py` 中 `generate()` 的代码摘录；省略部分以 `...` 表示。完整显示文本见 `references/generation_excerpt.py`。
3. `unit_03_five_levels`：同一体素模型向五个 Level 提示词发散，恰好五个向外箭头。图中文字是项目真实提示词的简短摘录；五级完整中英文描述见 `references/birdhouse_prompts_L1_L5.json`。
4. `unit_04_deduplication`：去重。
5. `unit_05_tiling_repair`：拼接与修复。
6. `unit_06_contact_screening` 为几何检查，接触筛查另记状态。
7. `unit_07_training_records`：数据输出。
8. `unit_08_brickmore_model` 为 BrickForma 方法示意，文件名沿用既有名称。

V1.8 已同步 GPT-6.1 Sol、axis/sign transforms、同色铺砖与局部修复、几何准入及 BrickForma 标签。第 6 单元按正文三个几何检查重画。第一单元继续保留既有待定占位。

`overview.png` 仅供并排审阅；每个单元的独立 PNG 都在本目录。`content/` 可编辑具体布局，`style.tex` 可编辑公共样式，`assets/` 为模型渲染素材。

在本目录执行 `tectonic unit_03_five_levels.tex`（或其他对应文件）即可生成独立矢量 PDF。也可以使用 `pdflatex`。修改后再执行 `pdftoppm -png -singlefile -r 300 unit_03_five_levels.pdf unit_03_five_levels` 导出图片。

本目录是拆分审阅图。V1.8 PNG 由 `scripts/sync_figure_assets_v18.py` 同步既有渲染与源码标签，局部字形采用 Arial。最终矢量排版仍须重新编译 TikZ。`overview.png` 已由八张当前单元图重新组合。
