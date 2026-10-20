# BrickMore

基于 BrickNet 和 BrickGPT 相关研究开展的积木建模项目。

## 项目目录

- [Train/](Train/README.md)：训练数据及配套代码，包括数据生成、排砖与修复、验证、下载与打包工具、样例、预览和报告。
- `Essay/`：论文写作资料与参考论文。

训练相关文件已统一移入 `Train/`，内部目录结构保持一致。运行原有命令前，请先进入该目录：

```powershell
cd Train
python tools/download_dataset.py --shard all --output dataset_80000 --extract
```

完整数据说明、各版本结果与使用方法见 [Train/README.md](Train/README.md)。

## 本地模型生成的六个 LEGO 样例

[查看六个样例、LDR 模型和完整下载包](Train/samples/brickgpt_qwen3_1p7b_six_20261020/README.md)。包含椅子、汽车、钢琴、吉他、马克杯和鸟屋的真实原始输出、生成报告、三维预览，以及五个通过的最终重铺版本。钢琴保留失败标记；几何通过不等同于物理稳定性验证。
