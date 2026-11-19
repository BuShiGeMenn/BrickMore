# 11 月 16 日乐高模型四项对比测评

| 提示词组 | 提示词数 | BrickMore | BrickGPT | BrickNet | LDR 合计 |
|---|---:|---:|---:|---:|---:|
| A | 260 | — | 260 | 260 | 520 |
| B | 265 | 265 | 265 | 265 | 795 |
| 全量 | 525 | 265 | 525 | 525 | 1,315 |

B 组有 265 条同提示词三方配对，A 组有 260 条同提示词两方配对。两组均覆盖 21 类、L1–L5。BrickNet 的文件编号由用户确认，0–259 对应 A 组，260–524 对应 B 组，组内按原提示词顺序排列。编号对应表见 `Provenance/bricknet_index_to_prompt.jsonl`。

## 上传和预检

在 `/mnt/brickmore-data/brickmore-jrd-20261025/uploads/comparision_20261116` 上传 `.tar.gz` 和 `.sha256`。执行以下命令。

```bash
cd /mnt/brickmore-data/brickmore-jrd-20261025/uploads/comparision_20261116
df -hT .
sha256sum -c brickmore-three-models-four-scores-20261116.tar.gz.sha256 && tar -xzf brickmore-three-models-four-scores-20261116.tar.gz && cd BrickMoreComparison_20261116 && bash setup.sh --offline
```

预检通过时显示 `ENVIRONMENT READY`。它检查可用的 Python 环境、CUDA、零件网格以及三个评分模型的本地缓存，明细写入 `.runtime/environment.json`。脚本尝试加载原服务器的 `use-runtime.sh`，按上次完成测评所用的 commit 查找评分模型，包括 PE 的 `17aa0c2` 快照。临时文件写在包目录的 `.runtime/tmp`。

如果三个缓存都已就绪，可以直接运行小样本。预检若提示缺失，请在联网电脑补对应项目，再转回内网包目录。

```bash
# Python 标准库，Windows 或 Linux 均可执行。只下载缺失的指标。
python Scripts/fetch.py models --metrics pe
# 按需把 pe 改为 vqa 或 siglip2，也可列出多个。

# CPU 环境缺件时才运行，适用于 Linux x86_64、CPython 3.12。
python Scripts/fetch.py wheels
```

将 `Downloads/models/<指标>/` 或 `Downloads/wheels/` 放回服务器包目录，再运行 `bash setup.sh --offline`。若服务器允许联网，也可执行 `bash setup.sh --online`。下载显示进度、速度和 ETA，断网自动重试，中断后用相同命令续传 `.part`，完成后校验文件哈希。

自定义环境可参考 `environment.local.sh.example` 设置解释器和原缓存位置。GPU 依赖确实缺失时，可在匹配的联网 Linux 或 WSL 环境运行 `python Scripts/fetch.py pip-plan --python /path/to/python3.12`。将 `Downloads/gpu_wheels/` 转到服务器，用目标 Python 执行 `python Scripts/verify_downloads.py Downloads/gpu_wheels`，再离线安装 `python -m pip install --no-index --find-links Downloads/gpu_wheels -r requirements-gpu.txt`。

## 小样本和全量

```bash
bash run.sh smoke --workers 1
```

小样本覆盖 A 组一对和 B 组一组三方配对，共 5 个模型、40 个视角。显示 `FINISHED` 后运行全量。

```bash
bash run.sh full --workers 1
```

全量处理 1,315 个 LDR、10,520 张图，依次进行 P_inv、八视角渲染、VQAScore、PE 和 SigLIP2。终端显示当前阶段、完成数和 ETA。可在 tmux 中运行，并在另一终端的包目录执行 `bash run.sh status --watch`。中断后用相同命令和输出目录继续，已完成的样本会经过校验后复用。

如果只需要 B 组三方主对照，可用 `bash run.sh full --scope primary --out Results/comparison_B`。全量默认包含 A、B 两组。

## 报告和回传

在 `Results/comparison_full/report/` 查看 `report.html`、`scores.csv`、`by_category_level.csv`、`by_batch_level.csv` 和 `summary.json`。总体报告有 B 组三方配对和 A 组两方配对，均给出实际评分覆盖率。A、B 的生成设置有差异，表中分别列出两组的同提示词结果。

```bash
bash run.sh export
```

回传 `Results/comparison_full-results.tar.gz` 和同名 `.sha256`。自定义输出目录需在 `export` 时带相同的 `--out`。

## 评分口径

- P_inv 使用 BrickNet 0.1.0 的原版 inset 碰撞网格，按 LDR 行顺序统计无效放置比例。报告同时保留模型均值和按放置次数加权的值。这个指标用于比较碰撞，正好为零的模型仍需独立验证连通或承重。
- VQAScore 用 Qwen2.5-VL-7B-Instruct，PE 用 PE-Core-bigG-14-448，SigLIP2 用 giant-opt-patch16-384。图文评分先取八视角最高分，再按模型求平均。原始每视角分数和文本截断诊断随结果保留。
- 延续上次的 512 像素、八个固定视角和统一黄色零件网格渲染，评分适用于几何和图文匹配。配色没有进入渲染对比。
- BrickMore 的输入 LDR 标记为 `raw_model_output` 和 `Q8_0`。BrickGPT 的 A、B 两组生成设置见 `Provenance/`。全部按现有交付 LDR 评分。
