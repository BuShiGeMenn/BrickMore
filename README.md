# BrickMore

基于 BrickNet 和 BrickGPT 相关研究开展的积木建模项目。

## 当前数据集口径

当前采用原全量重铺发布加新版 B 批钢琴替换的整合口径：80,000 个模型中 **79,301 个通过相应几何检查**，699 个未通过。原始 A/B 下载命令不会自动应用钢琴替换。计算、下载边界及历史版本见 [当前数据集统计口径](Train/datasets/CURRENT_DATASET_STATUS.md)。几何通过不等于物理稳定性通过。

## 项目目录

- [Train/](Train/README.md)：训练数据及配套代码，包括数据生成、排砖与修复、验证、下载与打包工具、样例、预览和报告。
- `Essay/`：论文写作资料与参考论文；[BrickMore 论文草稿](Essay/BrickMore/README.md)目前包含 Abstract 和 Introduction。

训练相关文件已统一移入 `Train/`，内部目录结构保持一致。运行原有命令前，请先进入该目录：

```powershell
cd Train
python tools/download_dataset.py --shard all --output dataset_80000 --extract
```

完整数据说明、各版本结果与使用方法见 [Train/README.md](Train/README.md)。

## 本地模型生成的六个 LEGO 样例

[查看六个样例、LDR 模型和完整下载包](Train/samples/brickgpt_qwen3_1p7b_six_20261020/README.md)。包含椅子、汽车、钢琴、吉他、马克杯和鸟屋的真实原始输出、生成报告、三维预览，以及五个通过的最终重铺版本。钢琴保留失败标记；几何通过不等同于物理稳定性验证。

## 本地生成的 A 组 260 条样例

**[查看完整结果、模型、积木序列和提示词](Train/samples/brickgpt_qwen3_1p7b_a_260_20261114/README.md)**。使用 BrickGPT-Qwen3-1.7B-BrickMore-48（revision 92d1c595f5fe076971cc2633d6844f097a84eef3）本地推理生成，未使用 MILP 重拼接。几何检查 164/260 通过；其余 96 个结果也保留，并在索引中标明。