# Q3：联合局部修复、排砖与自重静力筛查（实验版本）

本目录不修改 Q2、已发布的 80,000 个原模型或原拼接结果。新结果保存在独立目录。
目标是提高成功率，**50% 是目标，不是预先承诺或已验证的全量结果**。

## 质量边界

- 原体素全部保留，原色不变；仅新增，最多 `floor(原体素数 × 0.02)`。
- 新增位置必须距原模型一个 Manhattan 步，颜色来自原调色板。
- 使用原真实矩形积木目录；覆盖准确、无碰撞、真实上下 stud 连接、接地。
- 保留原局部支撑比例、悬挑距离、组装前缀组件上限；没有放宽检查换取通过率。
- JSON、TXT、LDR 实际读回；新旧独立几何检查器必须一致。
- 派生模型另设 ID、占用 hash 和改动清单，原提示词未自动认证适配派生几何。

## 联合算法

`joint_cover.py` 同时决定矩形积木选择和新增体素：原位置恰好覆盖一次，可选位置至多一次，总新增量受 2% 限制。下层实际占用参与支撑约束，而不是假设所有候选支撑都存在。对实际断开的整数布局增加真实 stud 邻接切割，再求解；结果仍须独立审核。

v3 已取消初版“每块最多新增四个体素”的候选限制，改为完整积木目录与总 2% 预算；仍有候选数、时间和切割轮数限制。因此失败只表示**本次有限搜索未通过**，不能宣称模型在所有合法修复下必然不可行。物理反馈尝试重排，找不到更好结果时保留已复验的旧几何成功布局。

## 物理检查与边界

`gravity_audit.py` 为每块积木建立竖直力及两个重力相关力矩的平衡方程；同一接触力对上下积木作用相反，载荷贯穿整个模型。仅允许真实重叠 stud 的局部接触点；地面只能提供压力，不能靠虚构锚固防倾覆。

先求仅压缩接触的自重静力平衡；若失败，再求理想化模型下所需的最小每-stud 咬合拉力。**咬合力限值未知时不会把后一种情况认证为通过**。每份平衡报告包含可独立重算残差的接触力见证。最终布局通过后还检查每个已完成层的前缀；前缀的多个 stud 组件分别在无锚固地面上检查，不让地面假装连接它们。这仍不包含层内每次放砖或实际插入路径的稳定性验证。

采用明确的假设：stud 间距 8 mm、砖高 9.6 mm，质量暂按每占用 stud-brick 1 g；内部接触方形半宽 0.25 stud，地面边界内缩 0.05 stud。质量分布、接触几何、承载能力尚未通过实物标定。重心、接地多边形和抗倾覆角仅针对自重、水平无锚固地面；不覆盖侧向力、冲击、弹性变形、长期蠕变、真实咬合失效。因此 `fullPhysics=false`、`staticVerified=null`，`gravityEquilibriumPassed` 是**假设条件下的静力筛查**，不是完整物理认证。

研究依据：真实 LEGO 稳定性分析需要逐块力/力矩平衡及经实验测量的连接容量，参见 [StableLego 原论文](https://arxiv.org/html/2402.10711v1) 与 [ICCV 2025 原论文](https://openaccess.thecvf.com/content/ICCV2025/papers/Pun_Generating_Physically_Stable_and_Buildable_Brick_Structures_from_Text_ICCV_2025_paper.pdf)。本实现是范围更窄的独立重力 LP 筛查，不是上述论文完整算法的复现。[SciPy MILP](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html) 和 [LP](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html) 为求解接口。

## 运行

依赖 Python、NumPy、SciPy（实测 SciPy 1.18.0；需要含 `milp` 的版本）。在仓库根目录：

```powershell
python algorithms/voxel_assembly_q3/experiment.py --dataset D:\360Downloads\C\voxel_A_20261011 --baseline-index D:\360Downloads\C\voxel_A_20261011_assembly\runs\A_layer_refinement_v1\selected_assembly_index.jsonl --out downloads\quality_q3\A_uniform --count 80 --seconds 24 --workers 6
```

默认从完整 40,000 个清单按固定 hash 均匀抽样。`--q2-run` 用于重复旧队列回归，它不是新的独立留出集。几何通过与自重静力筛查通过分别报告。冻结配置、选择名单和所有依赖源代码；更新算法必须另建输出目录，旧运行可用自己的 `source_snapshot` 复验。
