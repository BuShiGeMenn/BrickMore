# 全量重铺入口

`fresh_local_monochrome_bridge_retile_v2` 将已验证的局部跨接梁与接口重铺算法用于其余 19 类模型。每个待重跑模型都先实际执行新排砖搜索；只有新搜索未通过，才考虑独立复验通过且改动合规的旧成功结果。搜索记录明确包含 `fresh_retile_before_success_fallback`、新搜索是否通过和最后是否保留旧布局，避免把复验旧结果记为新搜索。

全量交付包含 A/B 两批 80,000 个模型：其他 19 类重跑 72,380 个；钢琴与桌子的 7,620 个已完成结果逐文件保留，不重新拼接、不重新运行物理筛查。完整最终统计和下载见 [全量交付](../../datasets/retile_assembly_80000/README.md)。

沿用同色标准矩形砖、实际上下凸点接触、每组件接地、零原格改色和新增＋删除≤原占用体素 2%规则。源模型及五级提示词字节保留，修改仅存在于派生目标中，派生 ID 使用 `_q7_`。实际 JSON/TXT/LDR 由两个几何检查器回读，失败草稿也覆盖完整目标。物理筛查仍使用原求解器与预算；未知咬合力不计通过，几何通过不代表完整实物认证。

从仓库根目录运行，Python 3.11+，物理筛查需要 NumPy/SciPy：

```text
python algorithms/voxel_assembly_retile_full/full_pipeline.py run model.json --out new_result --baseline old_result --seconds 8 --physics-seconds 5
python algorithms/voxel_assembly_retile_full/full_pipeline.py verify new_result
python -m unittest discover -s algorithms/voxel_assembly_retile_full -p test_full_retile.py
```

三个新增测试使用仓库中的实际已发布模型验证：旧成功不跳过新搜索；新搜索失败仍保留经核验的旧成功；实际导出回读且拒绝被篡改的 LDR。原重铺算法及其 14 项测试保持原版本。

全量运行冻结每个源模型与原报告 SHA、运行源码的实际字节、每模型 8 秒搜索/5 秒物理预算和 16 个工作进程。每模型记录来源、改动、布局、搜索决策和物理状态。分包按原始 80 个分区，每包 1,000 个模型，并再次核对真实文件、ZIP 成员 CRC 与 SHA256。下载后的核验工具从冻结源码分别加载旧版钢琴/桌子和新版其他类别检查器。

有界搜索未找到解不证明无解；历史 Release 保留，最新全量结果以独立 Release 发布。
