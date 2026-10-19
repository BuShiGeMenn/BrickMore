# 钢琴 B 批重新生成：双层键床，零增删拼接

最新版还提供 [全部 80,000 模型的独立预览包](../../preview/full_80000/README.md)，解压启动即可查看更新后的所有模型，省去单独下载旧版数据再合并的步骤。

旧 B 批的 1,905 个钢琴均存在键盘支撑缺口；当前整砖、单色、真实上下连接规则下，保持原占用和颜色无法完成接地。诊断原始数据见 `old_B_support_diagnostic.json`。

本次采用 A 批五级提示词格式，重写 B 批立式钢琴语义：琴键下方必须有至少两层连续实心键床，键床接入琴体承重框，黑白键作为表面层，四个实心琴脚分别落地。尺寸、颜色、比例和哈希都从新模型实测生成。全部 1,905 个原始体素重新生成并拼接通过；拼接新增、删除、改色均为 **0**。这是重新生成的模型，不是修改旧拼接标签。

模型网格 48³，占用 750–1250。模型 ID 保留 B 批原有槽位，`datasetVersion` 更新，原旧 B 数据及历史 Release 保留。全部源 JSON/NPZ/OBJ/VOX 与实际拼接 JSON/TXT/LDR已回读验证，所有键都有双层直接支撑且黑白键俯视可见。独立检查 215,771 块砖，无重叠，源体素与拼接目标占用/RGB完全一致。

单独列出几何通过训练子集：`training/passed_model_index.jsonl` / CSV、`training/passed_prompt_records.jsonl`，**1,905 个模型、9,525 条提示词**。路径、源文件 SHA 与占用/规范几何哈希均核对。所有 L1—L5应按同一模型分组划分训练/验证/测试，建议同时按 geometryFamilyId 分组。

物理筛查沿用原求解器，最终自重通过 0 个，完成层通过 0 个。几何通过不等于完整物理认证，未知咬合力不计通过，`fullPhysics=false`。

本修订只替换 B 批钢琴 1,905 个，其他 78,095 个来自原完整发布。`overlay_manifest.json` 保存基线发布及明确的替换 ID。模型包包括全部新原始格式和拼接结果；训练与元数据包包含通过子集、运行源码、统计和最新 80,000 模型预览。覆盖应用说明见仓库的数据目录。

下载并单独预览 B 批：

```text
python tools/download_piano_b_supported.py --output piano_b_supported --extract
python -m http.server 8728 --directory piano_b_supported
```

打开 http://127.0.0.1:8728/index.html。要预览更新后的完整 80,000 个模型，先保留旧完整发布的解压目录，再运行 `python tools/serve_piano_b_supported.py --replacement piano_b_supported --base retile_full --port 8727`；服务器优先显示新 B 钢琴，其他模型读取原目录，不修改旧版文件。
