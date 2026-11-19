# BrickMore refine 版 525 个模型的四项测评

本包包含 A 组 260 个、B 组 265 个最终 LDR，覆盖 21 类、L1–L5。34 个保留原布局，445 个对原始输出重铺，46 个换种子重生成。模型与原有评分记录通过 `prompt_id` 和提示词原文对应。最终文件哈希、重生成种子和裁剪记录随包保存在 `Data/manifest.jsonl` 与 `Provenance/`。

## 上传和预检

用 WinSCP 将 `.tar.gz` 和 `.sha256` 上传到之前的服务器目录。进入包目录后检查环境。

```bash
cd /mnt/brickmore-data/brickmore-jrd-20261025/uploads/comparision_20261116
df -hT .
sha256sum -c brickmore-refined525-four-scores-20261119.tar.gz.sha256 &&
  tar -xzf brickmore-refined525-four-scores-20261119.tar.gz &&
  cd BrickMore_Refined525_20261119 &&
  bash setup.sh --offline
```

预检会检查结构和渲染环境、CUDA、零件网格，以及 VQA、PE、SigLIP2 的固定版本缓存。通过后显示 `ENVIRONMENT READY`，详情见 `.runtime/environment.json`。脚本沿用服务器现有 `use-runtime.sh` 的设置。临时文件写到包目录下的 `.runtime/tmp`。

若模型缓存路径没有被找到，可在包目录复制 `environment.local.sh.example` 为 `environment.local.sh`，按需指定旧 Python 环境或 `HF_HOME`。之前的 Hugging Face 缓存目录为 `/mnt/brickmore-data/brickmore-jrd-20261025/runtime/cache/huggingface`。也可以把已有的对应快照链接或复制到 `Downloads/models/vqa`、`Downloads/models/pe`、`Downloads/models/siglip2`。

确实缺少文件时，在联网电脑解压本包并运行对应下载命令。

```bash
# 将 pe 改成实际缺失的指标，可一次列出多个
python Scripts/fetch.py models --metrics pe
# 在服务器缺少 CPU 依赖时下载 Linux x86_64、Python 3.12 的 wheels
python Scripts/fetch.py wheels
```

把下载完成的 `Downloads/models/` 或 `Downloads/wheels/` 放回服务器包目录，重新运行 `bash setup.sh --offline`。下载显示进度、速度和 ETA，断网后自动重试。再次执行相同命令会续传保留的 `.part` 文件，完成后校验文件哈希。若服务器可联网，也可以用 `bash setup.sh --online`。GPU 依赖缺失时，可在匹配的联网 Linux 或 WSL 环境用 `python Scripts/fetch.py pip-plan` 下载 GPU wheels，在服务器用 `python Scripts/verify_downloads.py Downloads/gpu_wheels` 校验后离线安装。

## 小样本和全量

```bash
bash run.sh smoke --workers 1
```

小样本为 6 个模型、48 张视角图，覆盖 A、B 两组的三种来源。看到 `FINISHED` 并确认四项结果均有值后，再跑全量。

```bash
bash run.sh full --workers 1 --out Results/brickmore_refined525
```

全量处理 525 个模型和 4,200 张视角图。终端显示各阶段进度、耗时和 ETA。中断后用相同命令与输出目录续跑，已完成记录通过校验后复用。可在另一个终端进入包目录查看进度。

```bash
bash run.sh status --watch --out Results/brickmore_refined525
```

## 报告与回传

全量报告为 `Results/brickmore_refined525/report/report.html`。同目录的 `scores.csv` 提供逐模型分数，`summary.json` 和 `by_batch_level.csv` 提供汇总。保留原始版 A、B 的评分结果，便于按提示词与本次结果配对。

```bash
bash run.sh export --out Results/brickmore_refined525
```

回传 `Results/brickmore_refined525-results.tar.gz` 和同名 `.sha256`。

P_inv 与上次一样，按交付 LDR 的记录顺序测量碰撞。重铺会改变零件划分和摆放顺序，前后分数解释需考虑这两项变化。三项图文评分沿用同一权重快照、512×512 的 8 个固定视角和统一黄色，先取每个模型的视角最高分，再对样本取均值。
