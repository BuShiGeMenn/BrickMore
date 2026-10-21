# Model 文件夹的 Base 模型评测

Python 环境与权重放在项目外：`D:\PythonEnvs\brickmore-eval`。
调用 `Open-Eval.cmd` 后可使用下面命令；工作目录为 `D:\BrickMore`。

```bat
python Evaluation\pipeline\download_models.py --output D:\PythonEnvs\brickmore-eval\cache\huggingface\models
python Evaluation\pipeline\evaluate_models.py manifest --out Results\model_eval_20261021
python Evaluation\pipeline\evaluate_models.py render --out Results\model_eval_20261021
python Evaluation\pipeline\evaluate_models.py score --metric siglip2 --out Results\model_eval_20261021
python Evaluation\pipeline\evaluate_models.py score --metric pe --out Results\model_eval_20261021
python Evaluation\pipeline\evaluate_models.py summarize --out Results\model_eval_20261021
python Evaluation\pipeline\make_report.py --out Results\model_eval_20261021
```

渲染使用独立环境内的 playwright 1.56.0 和本机 Microsoft Edge。
复用项目内 Three.js、GLTFLoader 和 Draco 解码器，不操作已有浏览器窗口。

## 覆盖范围

逐文件评估四个评审包内的全部 GLB，严格区分 raw 与 stitched。实际存在
918 份 GLB，属于 480 个候选；缺失版本单独记录，不能用另一版本替代。

从各包 `judge_tool/static/items.json` 获取原始英文提示词；每份 GLB 计算 SHA-256。
每个候选自己的提示词不同，因此模型分数用于衡量与自身提示词的匹配，不能单独
决定同组候选的人工最佳选择。

## 渲染与分数

- 512×512，八个方位角 0、45、…、315°，仰角 25°，42° 透视相机。
- 按包围球自动适配，固定材质、灯光、曝光、背景与机位。
- 和自带评审器一致，统一使用黄色材质；不评估原始颜色遵循度。
- SigLIP2 Base 224：原文、64-token 上下文，单视角 sigmoid(logit)。
- PE-Core Base 224：原文、32-token 上下文，归一化特征余弦相似度。
- 单份 GLB 的主分数为八视角最高分；整体结果为各 GLB 主分数的均值。
- raw 与 stitched 分开汇总；前后变化仅在版本齐全的候选上配对计算。
- 保存逐视角分数、最佳视角和提示词截断标记；不把分数当成正确率。

权重来源与固定 revision、每文件官方哈希保存在项目外的模型下载目录中。
渲染与评分支持断点续跑；模型、图片或评分代码变更时需使用新的结果目录，
避免混合不一致结果。两种评分按顺序运行，默认每批一份 GLB（八张图片）。

这里使用 Base 权重与本地渲染协议，不直接复现论文 Giant/bigG 的数值。
几何碰撞、连接关系、力学稳定性不包含在图文语义评分中。
