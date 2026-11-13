# BrickMore / BrickGPT / BrickNet：四项服务器测评包

本包用于“电脑 → 向日葵堡垒机 → 内网服务器”的手动传输流程。本次没有连接服务器，也没有把历史分数当成新结果。

## 数据与对照口径

- 114 条相同英文 prompt（A/B 各 57），覆盖 21 类、105 个正式类别×Level 组。
- 主对照 342 条：三个系统各 114 条。BrickMore 在跑分前固定使用 A/B 清单第一个 model_ids，优先最终 stitched，否则 raw；不按分数挑最好样本。
- 全量 462 条：BrickMore 234、BrickGPT 114、BrickNet 114。额外候选、raw/stitched 对照、4 个未归档等级汽车试作保留为补充数据。交接目录的重复副本、未引用历史淘汰文件不重复计数。
- 原目录 `BrickGPT/A_ldr_57.zip`、`B_ldr_57.zip` 实际是 BrickNet，已根据生成总结正确标注；外层“BrickGPT原版”数据是 BrickGPT。
- 324 种真实零件的原版 inset 碰撞网格和统一渲染网格已随包携带，无需内网下载完整零件库。
- 部分 Raw GLB 为无节点名的程序化方砖网格：采用完整 12 三角形砖体、20 种合法尺寸和全部剩余顶面凸点包络校验恢复；1900 项带节点 GLB 的局部边界也已独立核对。水平格距统一为 20 LDU、砖高 24 LDU；相关源显示高度约定的转换在逐条记录中保留。

## 首次上传和环境检查

上传 `.tar.gz` 与同名 `.sha256` 到新的独立目录，不覆盖旧评测。

```bash
sha256sum -c brickmore-three-models-four-scores-20261110.tar.gz.sha256
tar -xzf brickmore-three-models-four-scores-20261110.tar.gz
cd BrickMoreComparison
bash run.sh verify
bash run.sh doctor
bash setup.sh --offline
bash run.sh dry-run
```

自动尝试复用原 `/mnt/brickmore-data/brickmore-jrd-20261025/use-runtime.sh` 中的环境与 HF 缓存。不会自动升级已有 GPU 环境，也不会在评分时偷偷联网下载。

若自动定位不适用，复制 `environment.local.sh.example` 为 `environment.local.sh`，填入现有解释器和缓存路径。也可对每次命令传入 `--gpu-python`、`--structure-python`、`--render-python`。

Doctor 检查：解释器与依赖、BrickNet 0.1.0、CUDA/GPU 空闲显存、324 种零件资源、三项评分模型配置及权重分片。输出 `.runtime/environment.json`，缺失时停止在重计算之前。

## 内网缺失项：在联网中转端补齐

把测评包也解压在联网电脑/堡垒机。以下下载器仅用 Python 标准库，支持 Windows 和 Linux；完整文件校验后跳过，`.part` 会保留，断网后指数退避重试、HTTP Range 续传，最终校验 SHA-256 / Git blob hash。

```bash
# Linux x86_64、CPython 3.12 的完整 CPU wheel 集；可在 Windows 下载
python Scripts/fetch.py wheels

# 只补 doctor 列出的缺失大模型；已有服务器缓存无需重复下载
python Scripts/fetch.py models --metrics vqa pe siglip2
# 如需替代端点，可追加 --endpoint https://hf-mirror.com
```

把生成的 `Downloads/wheels/` 和缺失的 `Downloads/models/<指标>/` 原样转入内网解压目录，再执行 `bash setup.sh --offline`。大模型权重未包含在主上传包中；三个模型合计可能占用数十 GB，确认缺失后再补。

GPU 依赖如需新装，在匹配的联网 Linux/WSL Python 环境生成二进制 wheel 下载计划（同样用持久断点下载器下载实际 payload）：

```bash
python Scripts/fetch.py pip-plan --python /path/to/python3.12
```

然后转入 `Downloads/gpu_wheels/`，用目标 GPU 解释器运行 `python Scripts/verify_downloads.py Downloads/gpu_wheels`，再用 `python -m pip install --no-index --find-links Downloads/gpu_wheels -r requirements-gpu.txt`。保留原有可用 Torch/CUDA，不要无版本限制升级环境。Windows 的 CPU wheel 模式不能代替完整 Linux GPU 依赖解析。

## 小样本、全量与终端进度

```bash
bash run.sh smoke --workers 1
tmux new -s brickmore_compare
bash run.sh full --workers 1
```

Smoke 使用六条覆盖三模型、GLB/LDR 与新旧结构的记录，共 48 视角。全量默认为 462 条、3696 张图；若只跑严格配对主实验，用新的输出目录：

```bash
bash run.sh full --scope primary --workers 1 --out Results/comparison_primary
```

终端显示当前阶段、完成数、百分比、耗时、ETA、当前模型或视角。初始化加载时 ETA 显示 `--`，同时持续心跳；每阶段完整输出保存在对应 `.log`，总体状态在 `progress.json`。

```bash
bash run.sh status --watch
tail -f Results/comparison_full/vqa.log
```

流程：输入校验 → 环境检查 → P_inv → 八视角渲染 → VQA → PE → SigLIP2 → 分类/等级及严格三方配对汇总。
Ctrl+B 后按 D 离开 tmux；Ctrl+C 会停止任务。中断后用**相同命令、相同 `--out` 和配置**续跑，已完成记录校验后复用。更改输入、作用范围或配置时须用新的输出目录，防止混分。

仅做 CPU 预检查可用 `bash run.sh smoke --cpu-only`；它不代表三项 GPU 评分通过。

## 输出与回传

```bash
bash run.sh export
# 自定义目录则加 --out Results/comparison_primary
```

回传 `Results/comparison_full-results.tar.gz` 和同名校验文件。解压后打开 `report/report.html`；逐模型、分类/Level、严格同 prompt 三方比较分别保存在 `report/scores.csv`、`by_category_level.csv`、`summary.json`。

## 指标边界

- P_inv 明确为 `pinv_file_order`：使用原版 BrickNet 0.1.0、inset 网格、逐记录顺序放置的无效比例。GLB/LDR 导出顺序不冒充已验证的原始生成顺序；三种模型均不使用 FixedEdge 免碰撞豁免。保留 macro/micro，缺网格/计算失败为 NA，不补零。
- VQA 使用 Qwen2.5-VL-7B-Instruct；PE 为 PE-Core-bigG-14-448；SigLIP2 为 giant-opt-patch16-384。八视角取最大值，再对模型平均；保留每视角值和截断诊断，不合成未经验证的“综合分”。
- 三模型全部使用同一真实零件网格、相机、灯光与统一黄色。该 CPU 渲染协议是适配版本，不能与旧服务器/论文数字直接混合；统一颜色也不能验证原始配色准确性。
- 生成阶段的稳定性标签保留，不以“是否通过生成过滤”再筛测评样本；图文分数、碰撞分数均不能自动认定人工外形合格或物理稳定。

## 旧服务器数据定位摘要（来自历史聊天，未连接复核）

原四项包：`brickmore-eval630-four-scores-20261027.tar.gz`，630 候选、1243 版本（Raw 620、Stitched 623）。
历史全量目录：`/mnt/brickmore-data/brickmore-jrd-20261025/uploads/eval630-20261027/BrickMoreEval630/Results/eval630_full_v2/`。
更早 918 模型三项图文目录：`/mnt/brickmore-data/brickmore-jrd-20261025/BrickMore/Results/server_paper_full_20261026/`。
P_inv 后来另做过 917/918 GLB 结构结果。旧包、旧结果在当前工作区并不完整，本次没有据此虚构现存服务器文件或重用其分数。
