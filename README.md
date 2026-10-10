# BrickMore

## 拼接与校验算法

新增算法源码位于 **[algorithms/voxel_assembly_b](algorithms/voxel_assembly_b/README.md)**，方法标注见 [ALGORITHM.md](algorithms/voxel_assembly_b/ALGORITHM.md)。包括同色标准砖贪心/beam拼接、MRV逐层位集精确覆盖，以及从真实JSON/TXT/LDR独立回读的几何校验；纯CPU，无模型权重或API密钥。

该算法对独立 **AI_B** 分片实际处理40,000个模型：3,288个几何装配通过，31,627个当前规则的必要条件失败，5,085个有界搜索未通过。此结果不代表本仓库下述AI_A数据已经进行LEGO处理，也不代表物理稳定性通过。原体素/颜色未修改，完整算法与失败证据边界见对应说明。

AI_A 彩色体素数据集：**40,000 个独立模型，200,000 条中英双语训练记录**。每个模型配有描述同一几何的 L1—L5 五条记录。

![21 类模型效果](preview/preview_21_categories.png)

| 项目 | 数量或规格 |
|---|---|
| 独立模型 | 40,000 |
| 双语训练记录 | 200,000；每级 40,000 |
| 类别 | 21 类；前 20 类各 1,905，vessel 为 1,900 |
| 网格 | 48×48×48；X 左右、Y 向上、Z 前后；坐标 0—47 |
| 实际占用体素 | 每模型 750—1250 |
| 结构族 | 每类 40 个，共 840 个；每族 47 或 48 模型 |
| 模型分包 | 40 个；每包 1,000 模型和 5,000 条记录 |

## 下载完整数据

完整模型分包、训练文本和索引见 **[AI_A 完整数据发布页](https://github.com/BuShiGeMenn/BrickMore/releases/tag/ai-a-40000-20261010-v2)**。全部下载约 2.96 GB。

下载 `AI_A_models_01_1000.zip` 至 `AI_A_models_40_1000.zip` 以及 `metadata.zip`，解压到同一个目录。模型和训练记录使用公共相对路径，各分包的子索引位于不同目录，合并时互不覆盖。

也可在下载本仓库后使用 Python 3.11 或更新版本运行以下命令，自动下载、逐个核对 SHA-256 并解压：

```text
python tools/download_dataset.py --output dataset --extract
```

发布页中的 `SHA256_DOWNLOADS.txt` 用于核对下载文件；`SHA256SUMS.txt` 是生产目录的逐文件校验清单。后者还列出生产检查点，检查点保留在本地，未包含在下载包中。

## 查看效果与文件结构

- 下载本仓库后，打开 `preview/index.html`，可离线旋转查看 21 类×3 个实际模型，切换五级描述，并载入其他 `model.json`。
- `preview/previews/` 是每类八个样例的拼图。
- `samples/` 提供 21 个完整样例模型，以及单独的样例索引。
- `programs/` 保存生成、渲染、独立验证和打包程序。完整生产元数据及恢复状态相关索引在 `metadata.zip` 中。
- `reports/` 保存全量独立验证、结构筛查和分包验证报告。
- `download_manifest.json` 列出下载地址、大小和 SHA-256。

完整解压后每个模型目录为 `models/<category>/<modelId>/`，包含 `model.json`、`model.npz`、`model.obj`、`model.mtl`、`model.vox`、`preview.png`、`validation.json`、`prompts.json`。五条描述引用同一份几何。

`metadata.zip` 包含 `manifest.json`、`all_prompts.jsonl`、`all_prompts.csv`、105 个类别/级别训练子集、去重索引、设计记录及完整说明。训练默认输入是 `captionZh` / `captionEn`；`voxelPromptZh` / `voxelPromptEn` 为带执行规则的备用输入。

## 类别

basket、bed、bench、birdhouse、bookshelf、bottle、bowl、bus、camera、car、chair、guitar、jar、mug、piano、pot、sofa、table、tower、train、vessel。

## 验证与处理状态

[独立验证报告](reports/independent_verification.json)记录全量 40,000 个模型读回成功、200,000 条记录配对正确、零错误，全部占用体素数在 750—1250。JSON、NPZ、VOX、OBJ/MTL 和预览经过实际读取核对，模型为单一六邻域连通组件。

40,000 个原始占用 hash 和 40,000 个轴变换规范 hash 均唯一；与提供的 55,255 条历史原始 hash 无重叠。结构族差异、类内近形和跨类别候选筛查均通过。自动筛查不能代替全面人工语义与审美评估。

历史索引未附完整旧坐标，历史旋转/镜像及近重复状态为 `unavailable_coordinates`。AI_B 索引尚未合并，跨任务去重为 `awaiting_merge`。本数据为彩色体素模型，LEGO 排砖和物理稳定性处理状态为 `not_run`。

原始任务规格见 [specification_zh.txt](docs/specification_zh.txt)，完整生产说明见 [dataset_readme_zh.md](docs/dataset_readme_zh.md)。
