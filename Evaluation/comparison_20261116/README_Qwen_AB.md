# Qwen A、B 组四项测评

| 组别 | 原始提示词 | 可进入评分 | 评分输入 |
|---|---:|---:|---|
| A | 260 | 80 | 从未微调 Qwen3-1.7B 原始回答中严格解析出的部分积木布局 |
| B | 265 | 265 | `Qwen1.7b.zip` 交付的原始 LDR |

A 组有 178 条没有可解析的放置记录，另有 2 条包含本测评砖型映射未覆盖的 4×4 砖。这 180 条在覆盖表中保留，四项评分为 NA。A 组进入评分的 80 条在原报告中均未通过完整几何校验，解析只保留标准 `尺寸 (坐标)` 行，并保持行顺序和位置。A 组的分数描述有结果的部分输出。

B 组 265 条均按文件编号、物体名和 Level 配对。B 组 LDR 没有写入确切的模型检查点。`A260_对照包_20261117.zip` 的两份数据分别与已有原版 BrickGPT A 组和本包 Qwen A 源结果重复。

## 上传及预检

用 WinSCP 将压缩包与校验文件上传到原测评目录。执行：

```bash
cd /mnt/brickmore-data/brickmore-jrd-20261025/uploads/comparision_20261116
sha256sum -c qwen-A-B-four-scores-20261117.tar.gz.sha256 && tar -xzf qwen-A-B-four-scores-20261117.tar.gz && cd QwenComparison_20261117 && bash setup.sh --offline
```

预检检查 Python、CUDA、零件网格与 VQAScore、PE、SigLIP2 权重，按上次运行所用的 commit 查找缓存。显示 `ENVIRONMENT READY` 后可试跑。缺评分权重时，在联网电脑用 `python Scripts/fetch.py models --metrics pe` 下载对应项目，再将 `Downloads/models/` 下新增目录原样转回服务器。指标名按需替换为 `vqa`、`pe` 或 `siglip2`。下载有进度和 ETA，可重连并从 `.part` 继续。服务器允许联网时可以运行 `bash setup.sh --online`。

## 四项测评

```bash
bash run.sh smoke --workers 1
bash run.sh full --workers 1 --out Results/qwen_A_B
```

小样本检查 A 组两个部分布局和 B 组一个交付 LDR，共 24 张视图。全量测评 345 个模型，共 2,760 张图。沿用原来的 P_inv 碰撞检测和统一黄色、512 像素八视角渲染，图文分取最高视角，再按模型汇总。中断后用相同命令和输出目录续跑。另一终端可执行 `bash run.sh status --watch --out Results/qwen_A_B` 查看阶段进度。

## 查看及回传

服务器报告在 `Results/qwen_A_B/report/report.html`。`scores.csv` 是进入评分的逐条结果。`coverage_and_scores.csv` 覆盖全部 525 条提示词，因缺失几何或不支持的砖型而无法算出的分数为空（NA）。

```bash
bash run.sh export --out Results/qwen_A_B
```

下载 `Results/qwen_A_B-results.tar.gz` 和同名 `.sha256`。报告按 A、B 组给出覆盖率，可与之前结果按 `prompt_id` 配对分析。
