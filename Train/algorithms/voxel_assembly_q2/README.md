# Q2：质量有界的拼接优化与校验

新通道 `quality_bounded_global_cover_q2_v2` 优先原形精确拼接，必要时才进行用户允许的 **最多2%局部新增**。旧 `voxel_assembly_b` 算法、原始模型、原提示词和已发布的80,000模型资产均不覆盖。新结果是另一套实验产物，不改写旧发布的通过数量。

## 固定质量底线

- 新增体素数不超过 `floor(0.02 * 原体素数)`，不足50体素的模型不能新增1个体素；分母不是修复后的数量。
- 不删除原体素、不改原体素RGB。新增颜色必须来自原模型已有调色板。
- 每个新增位置都必须与**原始**占用格点相距1个曼哈顿步，不允许用已新增材料无限延伸。坐标仍在48³内，外边界至多增长1格。
- 独立重新计算新增、删除、改色、改动比例、占用IoU、原/派生占用hash及每个新增格点的坐标/RGB。允许的仅新增修复对应占用IoU至少 `1/1.02 ≈ 98.04%`。
- 保留旧规则：同色标准矩形单砖高砖库、无碰撞、完整覆盖**目标模型**、逐层下支撑至少10%、最大支撑曼哈顿距离2studs、前缀组件最多64、最终单一真实stud组件并接地。没有用共用地面或侧贴虚拟合并。

修复后的拼接精确覆盖 `target.model.json`，**不是**冒充与原模型完全相同。`source.model.json` 是原始文件的逐字节副本；有改动时，派生目标使用新的ID，记录 `sourceModelId` 和新的占用hash，不复用原规范hash。未重新计算派生规范hash的状态明确写为 `not_recomputed_for_derived_variant`。

原训练描述不自动绑定为派生几何的新训练标签。修复报告标注 `promptBindingStatus=original_source_only_not_revalidated_for_repaired_geometry`。2%的几何边界不证明语义、审美或关键孔洞完全不变；`semanticVerified=false`。

## 算法改进

1. 位集MRV精确覆盖不再固定每层的第一个解。后层失败可以撤销砖块、并查集合并和前层选择，重新寻找跨层布局；用显式栈避免大模型的Python递归深度限制。
2. 原地可回滚并查集替代每个候选复制整个占用索引。底层不能再接触未来层的候选、已无未来接口的真实组件和“真实前缀组件—未来可能连接组件”二部图不连通的分支提前剪掉。未来图是过近似，不能用它把侧贴当成真实连接。
3. 优先合并真实下层根、跨越未来连接区域和使用有支撑的大砖。先搜索原模型，失败后用多个小修复方案尝试补局部下支撑或上下stud桥，再重新排砖。所有尝试仍受时间、节点及2%预算限制。
4. 新独立校验器从JSON重建占用与另一套增量并查集，不读取生成器的“通过”标志。根数不再逐砖重新扫描全部历史砖；几何检查约为 `O(V α(B))`，排序hash仍需 `O(V log V)`。
5. 每个导出结果重新读取JSON/TXT/LDR，且继续与**未修改的旧独立校验器**交叉核对。另查修复动作历史、原始字节、输出SHA、派生ID及禁止虚假的物理/语义通过声明。

有限搜索失败不证明无解；局部修复失败也不证明2%预算内不存在其他解。优先找到质量合格结果，不保证最少砖数、最少修复或最大可能通过率的数学最优。

## 实测证据

独立验证集按“类别 × 旧最终状态”分层取样，使用固定seed 1729的ID hash分为互不重叠的开发/验证两组。开发结果不作为8万模型的全量通过率；验证组不参与调参。旧成功结果重新核对SHA及真实导出后保留，避免升级退步。

| 独立验证分片 | 样本数 | 旧通过 | 新通过 | 新增通过 |
|---|---:|---:|---:|---:|
| AI_A | 71 | 15 | 18 | 3 |
| AI_B | 78 | 17 | 29 | 12 |
| 合计 | 149 | 32 | 47 | 15 |

该分层验证样本的通过比例从21.48%增至31.54%，成功数增加46.88%；原成功32个全部保留。新增7个原形精确通过、8个修复通过。最大实际修复比例约1.672%，无删除、无原体素改色。**样本的状态比例与总体不同，不能把31.54%当作80,000个模型的通过率；尚未用本算法全量重跑。**

证据：[A验证组](reports/benchmark_A_holdout_final.json)、[B验证组](reports/benchmark_B_holdout_final.json)、[开发与验证组整批回读](reports/benchmark_summary.json)、[回归与校验性能](reports/tests.json)。56项新旧回归通过，包括255种小占用的穷举独立对照、150种随机坏布局的双校验器一致性、跨层回滚、修复预算及导出篡改。1000砖块的碎片化**失败草稿**上，新独立校验约快12倍；这不是整个流水线12倍提速，旧校验器的交叉核对仍保留。

## 使用

在`Train` 目录运行单模型优化，输入仍为Y-up整数坐标和RGB三元组：

```text
python -B tools/optimize_assembly.py one --input MODEL.json --out NEW_OUTPUT --ratio 0.02 --seconds 12 --nodes 60000
```

用 `--ratio 0` 禁止一切几何修复。输出必须是新目录；成功写 `model.txt/model.ldr`，失败只写 `model.draft.txt/model.draft.ldr`。同时保留 `source.model.json`、`target.model.json`、`assembly.json`、`validation.json` 和 `report.json`。单模型退出码0为通过，2为明确失败草稿。

本地已封存的A/B逐模型选中索引可以作为升级基线（需保留其实际结果目录及冻结运行config，不仅是汇总标志）：

```text
python -B tools/optimize_assembly.py probe --dataset DATASET --baseline-index SEALED_REFINEMENT/selected_assembly_index.jsonl --out NEW_PROBE --split holdout --per-stratum 2 --workers 8
python -B tools/optimize_assembly.py run --dataset DATASET --baseline-index SEALED_REFINEMENT/selected_assembly_index.jsonl --out NEW_FULL_RUN --workers 16
python -B tools/optimize_assembly.py verify --dataset DATASET --out NEW_FULL_RUN --workers 16
```

无基线也可 `run`，但必须重新搜索所有模型，不能宣称“旧成功零退步”。基线索引先核对模型集合、结果目录边界及选中报告SHA；继承成功必须重新读取旧JSON/TXT/LDR并核对原始文件SHA。失败样本不会仅因标志或放松校验变成成功。

每次运行冻结源码SHA、配置、输入manifest/基线索引SHA、样本选择及 `source_snapshot/`。配置或源码变化必须用新的输出目录，已有产物不自动覆盖。旧运行可用其 `source_snapshot/tools/optimize_assembly.py` 重新验证；这提供算法回退，不重写Git历史或删除旧数据。

测试入口：

```text
python -B algorithms/voxel_assembly_q2/verify_quality.py
```

纯CPU、标准Python库。所有成功均为几何和受限修复通过，仍为 `staticVerified=null`、`fullPhysics=false`；没有验证静力、抗倾覆、摩擦、接头受力、插入路径或实物搭建。新算法不会自动推送仓库、上传或替换旧Release。
