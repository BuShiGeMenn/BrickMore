# BrickForma 论文矢量图生成说明

论文使用预生成的矢量 PDF，由 LaTeX 从图文件插入。绘图数据、图形样式和投稿 PDF 的字体处理分别由下列脚本负责。

| 论文图号 | 文件 | 来源与生成脚本 |
| --- | --- | --- |
| 图 15 | `01-zero-invalid.pdf` | [render_comparison_figures.py](render_comparison_figures.py) 从最新 525 条主评测生成零无效放置比例图。 |
| 图 16 | `02-means.pdf` | 同一脚本生成四项指标的总体均值图。 |
| 图 17 | `03-distributions.pdf` | 同一脚本从逐样本评分生成经验累积分布。 |
| 图 18 | `04-by-level.pdf` | 同一脚本按 L1–L5 生成分层均值曲线。 |
| 图 8、11 | `image14_en.pdf`、`image17_en.pdf` | 来自历史数据。原绘图代码在 [render_refinement_labels.py](render_refinement_labels.py) 的 Matplotlib 部分，读入 `figure_data/historical_release_counts.json`。旧脚本的前半部分需要历史项目里的原始 PNG 与字体文件。 |
| 图 13 | `image19_en.pdf` | 沿用历史失败类别统计的矢量图。当前项目保存了成图，未找到原绘图脚本。 |

[update_refined_comparison.py](update_refined_comparison.py) 把 refined 包与旧主评测的 525 条提示词逐一匹配，对照评分日志验证新结果，再将最终 BrickForma 结果与原 BrickGPT、BrickNet 基线汇总到 `data/20261119/scores.csv` 和 `paper_summary.json`。它也生成论文表格和图 3，并复用 [update_comparison_20261117.py](update_comparison_20261117.py) 中的表格和配对检验函数。`data/20261117/` 保存细化前的结果。

[outline_chart_fonts.py](outline_chart_fonts.py) 在绘图之后处理图 8、11、13、15–18。它将图中文字转换成矢量轮廓，并检查输出 PDF 的字体资源。

## 重现 525 条主评测图

将本目录的 Python 脚本放在论文 LaTeX 工程的 `scripts/` 目录下。使用包含 `data/20261117/`、`data/20261119/` 和配套图像素材的 Overleaf 工程包。命令在该工程根目录执行。需要 SciPy、Pillow、NumPy、Matplotlib、CairoSVG、pypdf 以及 Poppler 提供的 `pdftocairo` 和 `pdffonts`。CairoSVG 需要系统安装 Cairo。

~~~sh
python -m pip install scipy pillow numpy matplotlib cairosvg pypdf
python scripts/update_refined_comparison.py
python scripts/render_comparison_figures.py --snapshot 20261119
python scripts/outline_chart_fonts.py
latexmk -pdf main-claude.tex
~~~

四张主评测图输出到 `figures/comparison_20261119/`。Overleaf 直接读取工程包中的成图即可编译。修改图表时，先改相应的数据或 Python 脚本，再重新导出。
