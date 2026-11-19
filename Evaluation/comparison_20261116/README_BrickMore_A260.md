# BrickMore A 组 260 条四项补测

这次为 BrickMore A 组 `A01_L1` 至 `A52_L5` 补做 P_inv、VQAScore、PE、SigLIP2。260 条提示词与 11 月 16 日服务器测评中的 A 组 BrickGPT、BrickNet 逐条相同，覆盖 21 类和 L1–L5。回传后可按 `prompt_id` 合并成绩。

网格、四项评分代码、渲染参数和三个图文评分模型的快照沿用上次。BrickMore 的规范积木序列转换为 LDraw，并与原 GLB 已导出的砖逐块核对。部分 GLB 只包含序列前缀，评分采用完整规范序列。LDraw 使用物理砖高 24 LDU 和横向间距 20 LDU。包内保留规范序列和原 GLB 哈希，原 GLB 文件保存在原目录。

源清单中的全部 260 条均保留，包括标记为 `geometry_valid=false` 的 96 条、标记为 `generation_complete=false` 的 8 条。这两个源标记可能重叠。核对记录见 `Provenance/glb_geometry_verification.jsonl`，源状态见 `Data/manifest.jsonl`。

## 上传和预检

用 WinSCP 上传 `.tar.gz` 和 `.sha256` 到 `/mnt/brickmore-data/brickmore-jrd-20261025/uploads/comparision_20261116`，再在服务器运行：

```bash
cd /mnt/brickmore-data/brickmore-jrd-20261025/uploads/comparision_20261116
sha256sum -c brickmore-A260-four-scores-20261117.tar.gz.sha256 && tar -xzf brickmore-A260-four-scores-20261117.tar.gz && cd BrickMore_A260_20261117 && bash setup.sh --offline
```

预检按上次使用的 commit 查找 Qwen VQA、PE 和 SigLIP2 缓存，检查 Python 环境、CUDA 和零件网格。通过后显示 `ENVIRONMENT READY`。如提示缺少评分模型，可在联网电脑解压本包后运行 `python Scripts/fetch.py models --metrics pe`，将 `pe` 换成实际缺失的指标，再将 `Downloads/models/` 中补齐的目录转回服务器。下载会显示进度和 ETA，失败重试并保留 `.part` 以便续传。若服务器允许联网，可在包目录执行 `bash setup.sh --online`。

## 测评与回传

```bash
bash run.sh smoke --workers 1
bash run.sh full --workers 1 --out Results/brickmore_A260
```

小样本选了 3 条，共 24 张图。全量处理 260 条和 2,080 张图。终端显示各阶段进度与 ETA，中断后用相同命令和输出目录继续。可在另一个终端执行 `bash run.sh status --watch --out Results/brickmore_A260` 查看进度。

显示 `FINISHED` 后打包：

```bash
bash run.sh export --out Results/brickmore_A260
```

下载 `Results/brickmore_A260-results.tar.gz` 和同名 `.sha256`。服务器报告位于 `Results/brickmore_A260/report/report.html`，逐模型数据在同目录的 `scores.csv`。合并时也保留 11 月 16 日的 `comparison_full-results.tar.gz`。

P_inv 沿用文件放置顺序下的碰撞指标。图文评分沿用统一黄色的 512 像素八视角渲染，每个模型取最高视角分数再汇总。配色与承重需要独立验证。
