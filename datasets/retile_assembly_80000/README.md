# 全量接口重铺：80,000 模型

其他 19 类的 **72,380 个模型实际重跑**；钢琴与桌子 **7,620 个结果逐文件字节保留**，没有重复运行拼接或物理筛查。

几何通过 **79,298/80,000（99.12%）**，仍未通过 702 个。原放宽版通过 65,503 个；本轮其他类别新增救回 8,331 个，加上已完成钢琴/桌子的 5,464 个，合计新增 13,795 个；旧成功退步 0 个。

每个模型包含 `source.model.json` 原始体素、`source.prompts.json` 五级提示词、`target.model.json` 派生拼接目标、`assembly.json` 实际砖块、验证报告和实际 TXT/LDR；未通过结果明确标记为 draft。原始网格 48×48×48，原体素与提示词字节保持一致，保留格子颜色不变，新增＋删除总改动最多 2%。原五级提示词继续绑定原始体素；派生目标不会自动改绑原训练记录。

新算法先执行局部跨接梁与接口重铺搜索，只有新搜索未通过且旧结果独立复验通过，才回退到旧成功结果。共 5 个这样的保留回退。钢琴/桌子仍使用原发布的 v1 结果；其余 19 类使用 v2，元数据记录两种生成来源。

最终自重平衡筛查通过 220 个，完成层自重筛查通过 128 个。几何通过与物理状态分别记录，未知咬合力不计物理通过，完整物理认证 `fullPhysics=false`、`staticVerified=null`。

## 下载与预览

80 个模型 ZIP，每个 1,000 个模型；另一个元数据 ZIP 包含全量索引、统计、原始来源 SHA、冻结运行源码和采用逐像素深度测试的三维预览。全部 80,000 个通过结果或失败草稿均覆盖各自完整目标；JSON/TXT/LDR 已独立回读，全部压缩包成员经过 CRC 和 SHA256 核验。全部实际砖块另经独立整数体积扫描，无砖体重叠。

```text
python tools/download_retile_full.py --output retile_full --workers 4 --extract
python -m http.server 8727 --directory retile_full
```

打开 http://127.0.0.1:8727/index.html，按 21 类、A/B 批次、通过状态或模型编号查找。原始体素和当前拼接结果并排显示，沿用已修正遮挡的预览 v2。

原始 JSON 已附在每模型结果中；原始 OBJ/VOX/NPZ 等格式仍见 [AI_A 原始发布](https://github.com/BuShiGeMenn/BrickMore/releases/tag/ai-a-40000-20261010-v2) 和 [AI_B 原始发布](https://github.com/BuShiGeMenn/BrickMore/releases/tag/ai-b-40000-20261010-v1)。

完整结果下载：[独立 Release](https://github.com/BuShiGeMenn/BrickMore/releases/tag/lego-retile-ab-80000-20261013-v1)。
