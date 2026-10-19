# 钢琴 B：双层键床与零增删拼接

旧 B 批的键盘存在没有下方支撑的薄层；在现有整砖、单色、仅上下真实 stud 连接的规则下，1,905 个源模型均无法保持原占用/RGB完成接地。这个结论针对当前零件库，不否定使用其他 LEGO 零件或更细网格的可能性。

`generate.py` 用 A 批五级提示词格式重写 B 批立式钢琴描述，并从新参数生成几何：完整琴体、前方黑白键盘、至少两层连续实心键床、四个落地实心琴脚。每个琴键的两层下方支撑、表面可见性和两种颜色都实测；源模型生成后派生 JSON/NPZ/OBJ/VOX，再回读数据和提示词配对。

`strict_core.py` 只在原始占用内重铺，禁止增加、删除或改色；若无解保留完整失败，不调用允许增加体素的旧回退。生成过程只接受实际零改动拼接通过的设计，再用 `pipeline.py` 导出、双审计 JSON/TXT/LDR并执行原物理筛查。生成器拒绝与原80,000模型及新批次重复的占用/规范几何哈希。

全部 B 钢琴1,905个已重新生成并实际拼接，通过1,905个；新增/删除/改色均0。原 B 模型、历史发布、A批及其他类别保留。数据、诊断、训练清单和下载见 [交付说明](../../datasets/piano_b_supported_1905/README.md)。

导出器外层继承原2%上限，但本模块的实际搜索与验收更严格，全部要求0改动。物理求解器未修改，未知咬合力不算通过，完整认证始终 `fullPhysics=false`。

```text
python algorithms/voxel_piano_b_support/pipeline.py run model.json --out new_exact_result --seconds 8 --physics-seconds 5
python algorithms/voxel_piano_b_support/pipeline.py verify new_exact_result
```

`generator_snapshot` 保存本次实际使用的 A 流程导出与检查器字节；其中钢琴说明专门适配了 B 的四脚立式结构。生成脚本记录本次 Windows 工作区位置，重生成前应配置新输出位置，避免覆写已交付的元数据。
