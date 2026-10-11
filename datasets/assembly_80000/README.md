# A/B LEGO 拼接与独立回读结果

本目录保存公开发布清单及汇总证据。完整逐模型资产与统一索引放在单独的 [装配结果 Release](https://github.com/BuShiGeMenn/BrickMore/releases/tag/lego-assembly-ab-80000-20261011-v1)，原 AI_A/AI_B 体素 Release 不修改。

发布后的 [服务器端核对报告](release_verification.json) 记录全部 81 个文件的公开下载地址、大小与 SHA-256；原 AI_A、AI_B 发布的文件清单和校验值均保持不变。

## 下载与验证

在仓库根目录运行：

```text
python tools/download_assembly.py --shard all --output assembly_80000 --workers 4 --extract
```

只获取一批可用 `--shard A` 或 `--shard B`。不加 `--extract` 时仅下载和验证压缩包 SHA-256；加上时安全解压，并独立重读所有选中模型的实际 JSON/TXT/LDR、原体素和五级提示词。

每批 40 个装配包，每包 1,000 个模型；另有一个公共 `assembly_metadata.zip`。解压后保留 `AI_A/` 和 `AI_B/` 两个命名空间，统一 `assembly_index.jsonl` 每个原始 modelId 恰好一行。模型数包含成功与失败，不等于成功装配数。

每模型提供：

- 原始字节的 `source.model.json`、`source.prompts.json`；五级记录仍属于同一个模型。
- 实际 `assembly.json`、`validation.json`、`report.json`。
- 成功 `model.txt` / `model.ldr`，或明确命名的失败 `model.draft.txt` / `model.draft.ldr`。

原提示词内部的路径保持原始分片相对路径，不改写训练数据。本发布定位请使用统一装配索引的 `sourceModelJsonPath` 和 `sourcePairedPromptsPath`。公开报告只使用相对路径，没有本机用户名、目录或登录信息。

## 校验范围与限制

`success` 表示精确占用/RGB 保留、标准同色矩形单砖高砖库、无碰撞、逐层下支撑、单 stud 组件、接地及真实导出回读均通过。

`infeasible_under_selected_policy` 有当前砖库、上下 stud 连接和支撑策略下的必要条件失败证据，不是所有 LEGO 零件和所有装配顺序下的无解证明。

`search_failed` 是贪心/beam 与 MRV 逐层精确覆盖在有限时间/节点预算内均未找到通过结果，不是数学无解证明。失败草稿不能用于冒充成功装配。

所有公开 ZIP 均再次打开核对 CRC 和逐文件 SHA，并从 ZIP 内的真实 JSON/TXT/LDR 重建结果。几何通过不等于物理稳定：没有验证静力、倾覆、摩擦、接头受力、插入路径或实物搭建，始终 `staticVerified=null` / `fullPhysics=false`。

坐标从原 Y-up `[x,y,z]` 转内部 Z-up `[x,z,y]`，不修改原格点和 RGB。水平一格为 1 stud、竖直一格为 1 标准砖高，LDraw 单位比例 20/20/24，实物比例不同于等距体素预览。

## 重跑算法

先用原数据下载器完整取回任一分片，再运行：

```text
python tools/run_shard_assembly.py --shard A --dataset PATH_TO_AI_A --out PATH_TO_NEW_RUN --delivery PATH_TO_NEW_DELIVERY --workers 16
```

此入口依次执行平衡试跑、试跑回读、全量拼接、全量回读、所有首轮搜索失败项的 MRV 补充搜索、补充回读和公开 ZIP 打包回读。任一校验失败立即停止，不自动上传。已有运行配置、源码或输入变化时必须选择新的输出目录。

原 AI_B 已封存运行使用 `B_exact_grid_assembly_v2`；AI_A 使用 `exact_grid_assembly_v3`，只增加原 A/B 索引格式兼容，不放宽几何政策。补充方法仍为 `B_layer_mrv_exact_cover_v1`，历史方法名中的 B 不限制输入分片。时间预算使用实际墙钟，种子固定不保证跨机器成功数量完全相同，已发布结果由实际回读证据验收。
