# BrickNet 官方测试方案：来源与复现核对

核对日期：2026-10-24。此次仅查阅官方材料与本地文件，没有安装依赖或运行测评。

## 官方入口

| 内容 | 来源 |
| --- | --- |
| 项目主页 | https://kulits.github.io/BrickNet/ |
| 论文 | https://arxiv.org/html/2604.22984v1 |
| 主仓库 | https://github.com/kulits/BrickNet |
| 图文评分协议 | https://github.com/kulits/BrickNet/blob/master/eval/README.md |
| 结构评分代码 | https://github.com/kulits/BrickNet/blob/master/src/bricknet/score.py |
| 数据格式与验证集 | https://github.com/kulits/BrickNet/blob/master/DATA.md |
| 数据申请入口（此处仅提供链接） | https://forms.gle/dm4eYSa5gh4DqzRT6 |
| 官方渲染器 | https://github.com/kulits/BrickNet-Render |

## 论文测试项目

- 表 2：无条件生成，每个模型 65,536 条、每条 100 个零件；统计连接有效和无碰撞的首次失败前平均步数，并比较 AS/NS。NS 为 top-k=20、top-p=0.95。
- 表 3：512 条留出提示词；P_inv 衡量无效放置，VQAScore、PE、SigLIP2 衡量渲染图与提示词符合程度。不可解析的生成会重新生成。
- 表 4：留出序列上的困惑度，需要模型和真实序列，不是对最终 GLB 直接评分。

论文依据为第 4、5 节。官方 DATA.md 列出 `val.npz.xz`、`captions_val.jsonl.xz` 和 `paths_val.jsonl.xz`；验证 captions 每模型一条。数据需申请访问，不是仓库直接附带的公开下载。

## 官方公开图文协议

输入是 captions JSONL（id、caption）以及每提示词八视角的渲染 tar 分片。每视角独立评分，先取同一模型八视角的最高分，再对模型取平均。

| 指标 | eval README 指定模型 | 单视角分数 |
| --- | --- | --- |
| PE | PE-Core-bigG-14-448，pretrained=meta | 归一化图文向量余弦相似度 |
| SigLIP2 | google/siglip2-giant-opt-patch16-384 | sigmoid(logits_per_image) |
| VQAScore | Qwen/Qwen2-VL-7B-Instruct | 第一个回答 token 为 Yes 的词表概率 |

VQA 问句为 `Is this LEGO set {caption}?`，caption 合并空格、转小写并去掉末尾句末标点。论文第 5.2 节却写 Qwen2.5-VL 7B，存在论文与公开代码的模型差异；复现报告需披露并锁定具体 revision，不能默认为同一模型。

公开入口分别是 `eval/pe.py`、`eval/siglip2.py`、`eval/vqascore.py`。`--images-dir` 指 tar 分片目录，`--captions-jsonl` 指提示词文件，`--out` 指逐模型 JSONL 结果。

## 结构评分与版本边界

主仓库 README 的 2026-10-01 更新明确：新版用凸分解和 Bullet 穿透深度，允许 1 LDU 重叠；**复现论文原始数字使用 v0.1.0**，该版本采用预内缩网格上的三角形相交检测。论文也描述了预内缩网格流程。不能将两个检测器的数字当作同一协议。

结构评分入口为 `python -m bricknet score samples.jsonl scored.jsonl`。输入是 BrickNet path 文本，字段 path 或 text，不接受 GLB 直接替代。当前公开代码输出 n_actions、invalid、collisions，终端汇总可解析率、可解析且无碰撞率、首次失败前平均步数；没有直接给出表 3 的单个 P_inv 聚合值。

因此，P_inv 的最终聚合、解析失败后缀处理、缺碰撞体处理应单独核实。不能把“有碰撞的模型比例”当成“无效放置比例”。结构和图文评分均须保留样本 ID、版本和配置。

## 渲染与生成入口

官方渲染仓库提供 `bricknet-render model.ldr out/views --views 8`，输入为 LDraw 模型。当前仓库要求 Python 3.13+、Blender/bpy 5.1+；与现有 Python 3.12 评分环境分开管理，或使用独立 Blender。当前渲染器的默认设置也不能未经核对就认定与论文历史设置完全相同。

完整官方主仓库包含 `scripts/generate.py`，本地精简版没有该目录。官方文档的条件生成方案使用 Qwen3 基座，按顺序叠加 BrickNet-PT 和 BrickNet-SFT 适配器，读取含 caption 字段的 JSONL；生成脚本默认 temperature=1、top_k=20、top_p=0.95、max_new_tokens=4096。默认命令不包含论文所述的不可解析样本重生成闭环，严格复现需要补齐该环节并记录重试。

## 应用于 BrickMore

1. 若目标是论文复现，先申请官方 512 条验证数据，固定 v0.1.0、对应碰撞网格、生成模型、渲染器和三项评分模型；先解决 VQA 模型差异以及 P_inv 聚合细节。
2. 若目标是评估本项目，使用现有 480 个候选、918 份 GLB、7,344 张图片；将其明确命名为 BrickMore 测试集上的适配测评。现有 Base 评分模型、Three.js 渲染、统一黄色材质均与官方配置不同。
3. 现有 GLB 缺原始生成路径，原版 P_inv 不能直接运行；应补齐结构源文件，或独立报告经过验证的最终场景碰撞指标。

本地随附文档位于 `D:\BrickMore\Evaluation\BrickNet-master\eval\README.md`；先前的本机实施设计位于同目录 `P_INV_VQA_PLAN.md`，其碰撞版本说明已同步修正。
