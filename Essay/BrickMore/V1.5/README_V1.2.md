# BrickMore V1.2 图版更新

以 `V1.1XZC/BrickMore_LaTeX_工程` 为基础更新首页 Figure 1 和数据构建 Figure 2。保留原论文正文、其余图表及原有待补充信息。`README.md` 是原工程说明。

编译后的论文共 10 页。添加 T1 字体编码，使 CVPR 样式所要求的 Times 字体正常加载；Figure 2 的浮动声明提前放置，以固定在第 3 页。编译与版面核对记录见 `build_verification.json`。

## 交付文件

- `main.tex` / `main.pdf`：更新后的论文；Figure 1 在第 1 页，Figure 2 在第 3 页。
- `figure1.tex` / `figure1.pdf`：首页展示图独立可编译版本。
- `figure2.tex` / `figure2.pdf`：图像化流程图独立可编译版本。
- `figures/figure1.png` / `figures/figure2.png`：300 dpi 图片。
- `figure_tex/figure1_content.tex` / `figure_tex/figure2_content.tex`：可编辑的 TikZ 布局、文字、箭头、图例和图标。
- `figure_tex/style.tex`：公共字体、颜色、箭头样式。
- `figures/parts/`：不含版面文字的模型渲染图片。
- `figure_data/`：重建图片所需的体素坐标、积木实例、零件网格、颜色映射和来源记录。
- `scripts/render_figure_assets.py`：用实际模型数据渲染图片，不依赖生成式图片工具。

## 砖型配色

所有积木图片按 `figure_data/brick_type_colors.json` 使用同一套 11 色映射。旋转不改变类型：例如 1×2 和 2×1 都是蓝色。灰色体素是输入示意，彩色积木是砖型可视化；颜色不代表模型预测的外观，也不用于声称数据原始颜色。显示时加入细小砖缝；保存的坐标、尺寸和模型数据没有改变。

| 砖型 | LDraw ID | 颜色 |
|---|---|---|
| 1×1 | 3005 | #DF4C4C 红 |
| 1×2 | 3004 | #3D7BCE 蓝 |
| 1×3 | 3622 | #E79A34 橙 |
| 1×4 | 3010 | #33A697 青绿 |
| 1×6 | 3009 | #9472C7 紫 |
| 1×8 | 3008 | #D6BE39 黄 |
| 2×2 | 3003 | #E37BA7 粉 |
| 2×3 | 3002 | #62BBCB 浅青 |
| 2×4 | 3001 | #86AA52 草绿 |
| 2×6 | 2456 | #AD7956 棕 |
| 2×8 | 3007 | #687686 蓝灰 |

## 编译

从本目录执行：

```sh
tectonic figure1.tex
tectonic figure2.tex
tectonic main.tex
```

或者依次使用 `latexmk -pdf figure1.tex`、`latexmk -pdf figure2.tex`、`latexmk -pdf main.tex`。工程已经包含两个图的 PDF，直接编译 `main.tex` 也可生成论文。Overleaf 上传整个工程后将 `main.tex` 设为主文件；编辑图版后，先分别编译对应的 `figure1.tex` / `figure2.tex` 并更新图 PDF，再编译主文件。

Windows 可使用 `scripts/build.ps1 -Tectonic <tectonic.exe 的路径> -RenderPng`。首次使用 Tectonic 可能需要联网下载宏包。`-RenderPng` 需要 Poppler 的 `pdftoppm`。

重新渲染模型（仅修改文字或布局不需要此步骤）：

```sh
python -m pip install numpy numba pillow
python scripts/render_figure_assets.py
```

修改图例配色时，同时更新 `figure_data/brick_type_colors.json` 和 `figure_tex/style.tex`，然后重新渲染、编译。具体样本来源见 `figure_data/provenance.json`。

## 图版含义

Figure 1 上方展示体素转换和生成结果的重铺修复，中间连接数据构建与 Qwen3-1.7B 训练，下方分别展示 LLM 辅助构建的数据和 BrickMore 的生成结果。后者明确标记 raw / retiled。

Figure 2 采用与参考图相同的八步顺序，第一行从左到右、第二行从右到左，并保留修复回路。物理接触示意是检查方法的图解，不是该示例通过实体稳定性实验的证据。80k 表示源数据规模；没有将其写成物理筛选通过数量。
