# Q4：仅新增失败后的少量删除回退

这是独立的本地优化通道。Q2/Q3、80,000 原始模型和已发布装配 Release 均不覆盖。Q4 输出均是独立派生结果，不会把原始提示词自动绑定到修复后的模型。

## 固定质量边界

- 优先保留通过独立回读的 Q3/原装配成功结果；新模型必须先尝试仅新增，只有记录了真实失败才进入混合回退。有界失败不是无解证明。
- 改动预算为 `floor(原体素数 × 0.02)`。新增与删除合计计费；保留的原体素绝不改色。原文件字节不改动。
- 新增只能在原体素的一步曼哈顿邻域内，使用原有颜色。禁止连锁扩展远距离支撑。
- 删除限于原始几何中没有任何合法受支撑同色标准砖覆盖的非接地体素，或整个不接地潜在 stud 分量足够小的悬空部件。完整枚举原几何来确定候选，不能用超时/截断来猜测“没有支撑”。接地体素和其他核心体素均保护。这是结构筛选，不是语义无损证明。
- 每点记录新增/删除坐标、RGB 和删除原因，并重新计算新增、删除、总比例、IoU 与源/目标 hash。
- 矩形砖候选与删除变量联合求解。删掉的下层体素按实际覆盖动态计支撑，不能继续当固定支撑。碰撞、实际 stud 连通、接地、支撑比例、悬挑距离与前缀规则仍逐项检查。
- 导出 JSON/TXT/LDR 后用两套独立几何检查器回读，并检验修复差异、先新增失败证据、源文件 SHA 和物理力平衡见证。

## 物理筛查范围

直接复用 Q3 的 `gravity_audit.py`，没有为提高通过率放宽物理条件。它检查假定质量/接触面下的自重力与力矩平衡、无锚定地面的倾覆和每个完成层的前缀。内部接触只通过实际上下重叠 stud；未知咬合容量不能判通过。`staticVerified=null`、`fullPhysics=false`，也不认证逐砖安装过程、水平扰动、冲击、零件强度或真实材料参数。

## 复现

Python 3.12、SciPy 1.18。命令从`Train` 目录执行，数据路径自行替换：

```text
python algorithms/voxel_assembly_q4/verify_q4.py
python algorithms/voxel_assembly_q4/q4_experiment.py --dataset DATASET_A --baseline-index BASELINE_A/selected_assembly_index.jsonl --prior-q3-run downloads/quality_q3/A_uniform_retry_v3 --out downloads/quality_q4/A_uniform_fallback_v1 --count 80 --seconds 60 --candidate-limit 80000 --cut-rounds 16 --workers 6 --public-summary algorithms/voxel_assembly_q4/reports/benchmark_A_uniform_fallback_v1.json
python tools/summarize_quality_q4.py
```

B 批次同样运行。无 `--prior-q3-run` 时，会先进行 `--additions-seconds`（默认 24 秒）的新增优先搜索，再对失败进行混合回退。每次运行冻结算法源 SHA、实际源快照、清单/选样/前置结果 SHA。恢复时拒绝参数或源码变化，防止同一实验中悄悄混入不同算法。

私有模型结果保存在 `downloads/quality_q4/`，公开机器报告位于 `reports/`。均匀样本的同批重试仍是调参结果，不能当作新的独立验证，更不是 80,000 模型的整体通过率。

## 本轮实测

固定均匀样本 160 个：Q3 为 55 个，Q4 第一轮 56 个，稀疏约束重试后 **57 个（35.625%）**，没有几何成功退步，尚未达到 50%。假设下最终自重平衡 8 个、最终及全部完成层前缀通过 2 个；另外 49 个几何成功仍需未标定咬合力。

83 项测试全部通过。四个冻结实验共 320 份结果目录已独立复验，只有 160 个原模型，不能把重试次数当作模型数量。详见 [优化报告](reports/OPTIMIZATION_REPORT.md) 与 [机器汇总](reports/benchmark_summary.json)。
