# 官方 BrickGPT · A 组 260 条提示词运行结果

- 运行时间:2026-11-16 11:32
- 模型:AvaLovelace/BrickGPT(合并权重 D:\MODELS\BrickGPT-official-merged,Llama-3.2-1B + LoRA)
- 链路:官方原版推理(BrickGPT 类:逐砖 logit 屏蔽 + 拒绝采样 KV 回滚 + 物理稳定性回滚),20³ 网格
- 参数:world_dim=20, max_bricks=2000, max_brick_rejections=500, max_regenerations=100, temperature=0.6, seed=42
- 完成:260/260,失败:0

## 统计

| 指标 | 数值 |
|---|---|
| 单条耗时 | 中位 40s / 均值 207s / 最长 8068s |
| 砖数 | 中位 73 / 范围 5-716 |
| 拒绝采样总次数 | 34614 |
| 越界条目 | 0 |
| 重叠条目 | 0 |
| 体素多分量条目 | 44 |

## 目录

- results/<prompt_id>/: prompt.txt / output.txt / output.ldr / report.json
- manifest.csv 全量汇总;inputs/ 原始 MD 与解析 JSON
