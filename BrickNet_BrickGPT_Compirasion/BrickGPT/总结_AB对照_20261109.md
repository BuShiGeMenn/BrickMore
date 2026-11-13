# BrickNet 1.7B · prompt 对照实验（A/B 各 57 条）生成总结

- 日期：2026-11-09　模型：BrickNet 1.7B（PT + SFT 两级 LoRA，合并到 Qwen3-1.7B）
- 输入：`F/2/prompt对照实验_均分2份_20261109/`（114 条英文 prompt 均分两份，分配种子 20261109，原文未改写）
- 运行：`temperature=1.0, top-k=20, top-p=0.95, max-new-tokens=1024, seed=20261109`；每条 prompt 取 1 个可行样本、最多 30 次尝试；`--no-collision`
- 两组用完全相同的模型、采样参数与判定规则，只换 prompt 批次

## 1. 参数模型来源确认

**确认来自官方 BrickNet（Kulits & Schmid, CVPR 2026），不是本项目自训权重。**

- 项目主页：<https://kulits.github.io/BrickNet/>　｜　代码：<https://github.com/kulits/BrickNet>　｜　渲染：<https://github.com/kulits/BrickNet-Render>
- 论文：*BrickNet: Graph-Backed Generative Brick Assembly*, CVPR 2026（arXiv:2604.22984）
- 权重：Hugging Face 组织 `kulits` 的 `BrickNet-1.7B-PT` / `BrickNet-1.7B-SFT`（LoRA，base = `Qwen/Qwen3-1.7B`）

| 组件 | 本地路径 | r | alpha | base_model | 字节 | SHA256 |
|---|---|---:|---:|---|---:|---|
| PT | `models/bricknet/BrickNet-1.7B-PT` | 32 | 32 | `Qwen/Qwen3-1.7B` | 69,782,744 | `18b69edfab8a9b1a…` |
| SFT | `models/bricknet/BrickNet-1.7B-SFT` | 32 | 64 | `Qwen/Qwen3-1.7B` | 69,782,744 | `1f5da181eaa6f47e…` |
| 底座 | `models/Qwen3-1.7B` | — | — | Qwen3-1.7B | — | — |

- 下载溯源：仓库根目录 `bn_pt.json` 为 HF API 对 `kulits/BrickNet-1.7B-PT` 的原始返回（`sha=0f75d5e5…`，`lastModified=2026-05-12T08:05:55Z`，仅 `adapter_config.json` + `adapter_model.safetensors`）。
- 如实说明：运行时再次请求 HF API 复核上游 SHA **连接超时**，表中 SHA256 均为**本地实测**，未与远端逐字节比对。

## 2. 两组总体对照

| 指标 | A 组 | B 组 | 合计 |
|---|---:|---:|---:|
| prompt 条数 | 57 | 57 | 114 |
| 拿到可行样本 | 57 | 57 | 114 |
| 成功率 | 100.0% | 100.0% | 100.0% |
| 尝试总次数 | 77 | 90 | 167 |
| 平均每条成功所需尝试 | 1.35 | 1.58 | 1.46 |
| 首次成功尝试 1 / 2 / ≥3 次 | 40 / 15 / 2 | 35 / 15 / 7 | 75 / 30 / 9 |
| LDR 文件数 | 57 | 57 | 114 |
| LDR 砖块总数 | 1,265 | 1,391 | 2,656 |
| 砖块数中位（范围） | 21（6–46） | 24（6–48） | 22（6–48） |
| 组内零件种类 | 214 | 217 | 323 |
| 组内颜色种类 | 34 | 31 | 41 |

> `n_parts == 写盘 LDR 行数` 在全部 114 个被接受样本上逐一成立（解析成功才导出；失败尝试不产生 LDR）。
>
> **A/B 是两批不同的 prompt，不是同一批 prompt 的两套设置**：按 `分组说明.md` 的建议，要比较两套参数应让两套设置跑同一批 prompt；这里的 A/B 只能作为两个执行批次做分布层面的对照。

## 3. 按描述等级

| 等级 | A prompt | A 成功 | B prompt | B 成功 |
|---|---:|---:|---:|---:|
| L1 | 11 | 11 | 10 | 10 |
| L2 | 10 | 10 | 11 | 11 |
| L3 | 12 | 12 | 11 | 11 |
| L4 | 12 | 12 | 13 | 13 |
| L5 | 12 | 12 | 12 | 12 |

## 4. 类别覆盖

| 类别 | A prompt | A 成功 | B prompt | B 成功 |
|---|---:|---:|---:|---:|
| basket | 3 | 3 | 2 | 2 |
| bed | 2 | 2 | 3 | 3 |
| bench | 2 | 2 | 3 | 3 |
| birdhouse | 3 | 3 | 2 | 2 |
| bookshelf | 2 | 2 | 3 | 3 |
| bottle | 2 | 2 | 3 | 3 |
| bowl | 2 | 2 | 3 | 3 |
| bus | 3 | 3 | 2 | 2 |
| camera | 3 | 3 | 2 | 2 |
| car | 2 | 2 | 3 | 3 |
| chair | 3 | 3 | 2 | 2 |
| guitar | 3 | 3 | 2 | 2 |
| jar | 2 | 2 | 3 | 3 |
| mug | 3 | 3 | 2 | 2 |
| piano | 3 | 3 | 3 | 3 |
| pot | 4 | 4 | 4 | 4 |
| sofa | 5 | 5 | 5 | 5 |
| table | 3 | 3 | 2 | 2 |
| tower | 2 | 2 | 3 | 3 |
| train | 3 | 3 | 2 | 2 |
| vessel | 2 | 2 | 3 | 3 |

## 5. 失败与异常

- **A 组**：57/57 全部拿到可行样本
- **B 组**：57/57 全部拿到可行样本
- 失败尝试共 **53 次**（A 20 / B 33），全部来自 BrickNet 自身的解析与图约束，我们未放宽任何判定：

| 失败类型 | 次数 |
|---|---:|
| 路径不完整（dangling node） | 24 |
| 零件缺所需连接器（no stud/tube/hole/clip/socket… connectors） | 10 |
| 边语法不合法（stud edge token 数不对 / bad edge） | 10 |
| 索引/量纲错误（degree 非整数、连接器序号越界） | 6 |
| 词表外零件/颜色（unknown part / unknown color） | 3 |

- 失败尝试 `n_parts` 中位 **43**，成功样本仅 **22**：序列越长越容易撞上无连接器的零件。

## 6. 方法学边界（重要）

1. **只做解析级可行性**（`--no-collision`）：能导出 LDR ≠ 无碰撞 ≠ 能按图纸搭起来。
2. 碰撞检测需 BrickNet 零件网格 + `trimesh`；本机 `trimesh` 缺失、`pip install` 失败，故未做。`bricknet_work/bricknet_data/inset` 下有 21,084 个 `.ply`，但未验证与当前版本数据布局匹配。
3. prompt 为 **BrickMore-48 短描述风格**，与 BrickNet 训练分布（"This is a LEGO model of …"）不同；两组同处理，比较方向一致。
4. 每条 prompt 单样本；两组各自连续运行、`seed=20261109` 只保证可复现的必要条件，不保证跨机器逐比特一致。
5. 结构规模普遍偏小（中位约 20 块），与 BrickNet 论文示例（数百零件）差距明显，主因是 prompt 短、且不在其训练措辞分布内。

## 7. 产物

| 路径 | 内容 |
|---|---|
| `A.jsonl` / `B.jsonl` | 两组输入 prompt（caption + prompt_id/类别/等级/模型 ID） |
| `A_out.jsonl` / `B_out.jsonl` | 逐次尝试记录（raw_text/text/n_parts/feasible/accepted/reason/ldr） |
| `A_ldr/` / `B_ldr/` | 成功样本的 LDR（`<序号>-<sample>-attempt-<n>.ldr`） |
| `A_ldr_57.zip` / `B_ldr_57.zip` | LDR 打包 |
| `A.log` / `B.log` | 运行日志 |
| `build_inputs.py` / `make_summary.py` | 输入构建与本文档生成 |

## 8. 逐条明细

### A 组

| # | prompt_id | 类别 | 等级 | 首次成功尝试 | n_parts | LDR 砖块 | LDR 文件 |
|---:|---|---|---:|---:|---:|---:|---|
| 1 | basket_L1_P01 | basket | L1 | 2 | 14 | 14 | `0-0-attempt-2.ldr` |
| 2 | basket_L2_P01 | basket | L2 | 1 | 20 | 20 | `1-0-attempt-1.ldr` |
| 3 | basket_L3_P01 | basket | L3 | 2 | 9 | 9 | `2-0-attempt-2.ldr` |
| 4 | bed_L2_P01 | bed | L2 | 3 | 36 | 36 | `3-0-attempt-3.ldr` |
| 5 | bed_L4_P01 | bed | L4 | 1 | 12 | 12 | `4-0-attempt-1.ldr` |
| 6 | bench_L2_P01 | bench | L2 | 1 | 27 | 27 | `5-0-attempt-1.ldr` |
| 7 | bench_L4_P01 | bench | L4 | 2 | 24 | 24 | `6-0-attempt-2.ldr` |
| 8 | birdhouse_L1_P01 | birdhouse | L1 | 2 | 32 | 32 | `7-0-attempt-2.ldr` |
| 9 | birdhouse_L2_P01 | birdhouse | L2 | 2 | 33 | 33 | `8-0-attempt-2.ldr` |
| 10 | birdhouse_L4_P01 | birdhouse | L4 | 1 | 26 | 26 | `9-0-attempt-1.ldr` |
| 11 | bookshelf_L3_P01 | bookshelf | L3 | 2 | 25 | 25 | `10-0-attempt-2.ldr` |
| 12 | bookshelf_L5_P01 | bookshelf | L5 | 2 | 31 | 31 | `11-0-attempt-2.ldr` |
| 13 | bottle_L3_P01 | bottle | L3 | 1 | 6 | 6 | `12-0-attempt-1.ldr` |
| 14 | bottle_L5_P01 | bottle | L5 | 1 | 6 | 6 | `13-0-attempt-1.ldr` |
| 15 | bowl_L1_P01 | bowl | L1 | 1 | 11 | 11 | `14-0-attempt-1.ldr` |
| 16 | bowl_L4_P01 | bowl | L4 | 1 | 6 | 6 | `15-0-attempt-1.ldr` |
| 17 | bus_L1_P01 | bus | L1 | 1 | 21 | 21 | `16-0-attempt-1.ldr` |
| 18 | bus_L2_P01 | bus | L2 | 1 | 22 | 22 | `17-0-attempt-1.ldr` |
| 19 | bus_L3_P01 | bus | L3 | 1 | 36 | 36 | `18-0-attempt-1.ldr` |
| 20 | camera_L2_P01 | camera | L2 | 1 | 10 | 10 | `19-0-attempt-1.ldr` |
| 21 | camera_L3_P01 | camera | L3 | 1 | 11 | 11 | `20-0-attempt-1.ldr` |
| 22 | camera_L5_P01 | camera | L5 | 1 | 9 | 9 | `21-0-attempt-1.ldr` |
| 23 | car_L1_P01 | car | L1 | 2 | 46 | 46 | `22-0-attempt-2.ldr` |
| 24 | car_L5_P01 | car | L5 | 1 | 29 | 29 | `23-0-attempt-1.ldr` |
| 25 | chair_L2_P01 | chair | L2 | 1 | 43 | 43 | `24-0-attempt-1.ldr` |
| 26 | chair_L3_P01 | chair | L3 | 1 | 14 | 14 | `25-0-attempt-1.ldr` |
| 27 | chair_L4_P01 | chair | L4 | 1 | 18 | 18 | `26-0-attempt-1.ldr` |
| 28 | guitar_L3_P01 | guitar | L3 | 1 | 42 | 42 | `27-0-attempt-1.ldr` |
| 29 | guitar_L4_P01 | guitar | L4 | 4 | 7 | 7 | `28-0-attempt-4.ldr` |
| 30 | guitar_L5_P01 | guitar | L5 | 1 | 40 | 40 | `29-0-attempt-1.ldr` |
| 31 | jar_L3_P01 | jar | L3 | 1 | 8 | 8 | `30-0-attempt-1.ldr` |
| 32 | jar_L4_P01 | jar | L4 | 1 | 8 | 8 | `31-0-attempt-1.ldr` |
| 33 | mug_L1_P01 | mug | L1 | 1 | 14 | 14 | `32-0-attempt-1.ldr` |
| 34 | mug_L3_P01 | mug | L3 | 1 | 18 | 18 | `33-0-attempt-1.ldr` |
| 35 | mug_L4_P01 | mug | L4 | 1 | 16 | 16 | `34-0-attempt-1.ldr` |
| 36 | piano_L1_P01 | piano | L1 | 1 | 13 | 13 | `35-0-attempt-1.ldr` |
| 37 | piano_L2_P01 | piano | L2 | 1 | 35 | 35 | `36-0-attempt-1.ldr` |
| 38 | piano_L4_P01 | piano | L4 | 2 | 19 | 19 | `37-0-attempt-2.ldr` |
| 39 | pot_L3_P01 | pot | L3 | 2 | 8 | 8 | `38-0-attempt-2.ldr` |
| 40 | pot_L3_P02 | pot | L3 | 1 | 21 | 21 | `39-0-attempt-1.ldr` |
| 41 | pot_L5_P01 | pot | L5 | 1 | 34 | 34 | `40-0-attempt-1.ldr` |
| 42 | pot_L5_P02 | pot | L5 | 1 | 6 | 6 | `41-0-attempt-1.ldr` |
| 43 | sofa_L1_P01 | sofa | L1 | 2 | 36 | 36 | `42-0-attempt-2.ldr` |
| 44 | sofa_L2_P01 | sofa | L2 | 1 | 16 | 16 | `43-0-attempt-1.ldr` |
| 45 | sofa_L5_P01 | sofa | L5 | 1 | 36 | 36 | `44-0-attempt-1.ldr` |
| 46 | sofa_L5_P02 | sofa | L5 | 1 | 15 | 15 | `45-0-attempt-1.ldr` |
| 47 | sofa_L5_P03 | sofa | L5 | 1 | 31 | 31 | `46-0-attempt-1.ldr` |
| 48 | table_L1_P01 | table | L1 | 1 | 39 | 39 | `47-0-attempt-1.ldr` |
| 49 | table_L2_P01 | table | L2 | 2 | 7 | 7 | `48-0-attempt-2.ldr` |
| 50 | table_L3_P01 | table | L3 | 2 | 8 | 8 | `49-0-attempt-2.ldr` |
| 51 | tower_L1_P01 | tower | L1 | 1 | 15 | 15 | `50-0-attempt-1.ldr` |
| 52 | tower_L4_P01 | tower | L4 | 2 | 46 | 46 | `51-0-attempt-2.ldr` |
| 53 | train_L1_P01 | train | L1 | 1 | 22 | 22 | `52-0-attempt-1.ldr` |
| 54 | train_L4_P01 | train | L4 | 2 | 30 | 30 | `53-0-attempt-2.ldr` |
| 55 | train_L5_P01 | train | L5 | 1 | 43 | 43 | `54-0-attempt-1.ldr` |
| 56 | vessel_L4_P01 | vessel | L4 | 1 | 22 | 22 | `55-0-attempt-1.ldr` |
| 57 | vessel_L5_P01 | vessel | L5 | 1 | 33 | 33 | `56-0-attempt-1.ldr` |

### B 组

| # | prompt_id | 类别 | 等级 | 首次成功尝试 | n_parts | LDR 砖块 | LDR 文件 |
|---:|---|---|---:|---:|---:|---:|---|
| 1 | basket_L4_P01 | basket | L4 | 3 | 35 | 35 | `0-0-attempt-3.ldr` |
| 2 | basket_L5_P01 | basket | L5 | 1 | 10 | 10 | `1-0-attempt-1.ldr` |
| 3 | bed_L1_P01 | bed | L1 | 1 | 13 | 13 | `2-0-attempt-1.ldr` |
| 4 | bed_L3_P01 | bed | L3 | 1 | 26 | 26 | `3-0-attempt-1.ldr` |
| 5 | bed_L5_P01 | bed | L5 | 1 | 36 | 36 | `4-0-attempt-1.ldr` |
| 6 | bench_L1_P01 | bench | L1 | 1 | 27 | 27 | `5-0-attempt-1.ldr` |
| 7 | bench_L3_P01 | bench | L3 | 1 | 28 | 28 | `6-0-attempt-1.ldr` |
| 8 | bench_L5_P01 | bench | L5 | 1 | 21 | 21 | `7-0-attempt-1.ldr` |
| 9 | birdhouse_L3_P01 | birdhouse | L3 | 2 | 32 | 32 | `8-0-attempt-2.ldr` |
| 10 | birdhouse_L5_P01 | birdhouse | L5 | 2 | 15 | 15 | `9-0-attempt-2.ldr` |
| 11 | bookshelf_L1_P01 | bookshelf | L1 | 2 | 33 | 33 | `10-0-attempt-2.ldr` |
| 12 | bookshelf_L2_P01 | bookshelf | L2 | 6 | 31 | 31 | `11-0-attempt-6.ldr` |
| 13 | bookshelf_L4_P01 | bookshelf | L4 | 1 | 19 | 19 | `12-0-attempt-1.ldr` |
| 14 | bottle_L1_P01 | bottle | L1 | 1 | 14 | 14 | `13-0-attempt-1.ldr` |
| 15 | bottle_L2_P01 | bottle | L2 | 1 | 20 | 20 | `14-0-attempt-1.ldr` |
| 16 | bottle_L4_P01 | bottle | L4 | 2 | 39 | 39 | `15-0-attempt-2.ldr` |
| 17 | bowl_L2_P01 | bowl | L2 | 1 | 6 | 6 | `16-0-attempt-1.ldr` |
| 18 | bowl_L3_P01 | bowl | L3 | 1 | 12 | 12 | `17-0-attempt-1.ldr` |
| 19 | bowl_L5_P01 | bowl | L5 | 1 | 6 | 6 | `18-0-attempt-1.ldr` |
| 20 | bus_L4_P01 | bus | L4 | 4 | 41 | 41 | `19-0-attempt-4.ldr` |
| 21 | bus_L5_P01 | bus | L5 | 1 | 25 | 25 | `20-0-attempt-1.ldr` |
| 22 | camera_L1_P01 | camera | L1 | 1 | 10 | 10 | `21-0-attempt-1.ldr` |
| 23 | camera_L4_P01 | camera | L4 | 2 | 28 | 28 | `22-0-attempt-2.ldr` |
| 24 | car_L2_P01 | car | L2 | 1 | 41 | 41 | `23-0-attempt-1.ldr` |
| 25 | car_L3_P01 | car | L3 | 2 | 24 | 24 | `24-0-attempt-2.ldr` |
| 26 | car_L4_P01 | car | L4 | 1 | 21 | 21 | `25-0-attempt-1.ldr` |
| 27 | chair_L1_P01 | chair | L1 | 2 | 14 | 14 | `26-0-attempt-2.ldr` |
| 28 | chair_L5_P01 | chair | L5 | 2 | 30 | 30 | `27-0-attempt-2.ldr` |
| 29 | guitar_L1_P01 | guitar | L1 | 2 | 8 | 8 | `28-0-attempt-2.ldr` |
| 30 | guitar_L2_P01 | guitar | L2 | 2 | 11 | 11 | `29-0-attempt-2.ldr` |
| 31 | jar_L1_P01 | jar | L1 | 1 | 14 | 14 | `30-0-attempt-1.ldr` |
| 32 | jar_L2_P01 | jar | L2 | 1 | 45 | 45 | `31-0-attempt-1.ldr` |
| 33 | jar_L5_P01 | jar | L5 | 1 | 48 | 48 | `32-0-attempt-1.ldr` |
| 34 | mug_L2_P01 | mug | L2 | 3 | 29 | 29 | `33-0-attempt-3.ldr` |
| 35 | mug_L5_P01 | mug | L5 | 1 | 32 | 32 | `34-0-attempt-1.ldr` |
| 36 | piano_L3_P01 | piano | L3 | 1 | 32 | 32 | `35-0-attempt-1.ldr` |
| 37 | piano_L3_P02 | piano | L3 | 2 | 37 | 37 | `36-0-attempt-2.ldr` |
| 38 | piano_L5_P01 | piano | L5 | 3 | 21 | 21 | `37-0-attempt-3.ldr` |
| 39 | pot_L1_P01 | pot | L1 | 1 | 23 | 23 | `38-0-attempt-1.ldr` |
| 40 | pot_L2_P01 | pot | L2 | 1 | 7 | 7 | `39-0-attempt-1.ldr` |
| 41 | pot_L4_P01 | pot | L4 | 1 | 11 | 11 | `40-0-attempt-1.ldr` |
| 42 | pot_L4_P02 | pot | L4 | 1 | 17 | 17 | `41-0-attempt-1.ldr` |
| 43 | sofa_L3_P01 | sofa | L3 | 1 | 15 | 15 | `42-0-attempt-1.ldr` |
| 44 | sofa_L4_P01 | sofa | L4 | 1 | 35 | 35 | `43-0-attempt-1.ldr` |
| 45 | sofa_L4_P02 | sofa | L4 | 2 | 18 | 18 | `44-0-attempt-2.ldr` |
| 46 | sofa_L4_P03 | sofa | L4 | 1 | 26 | 26 | `45-0-attempt-1.ldr` |
| 47 | sofa_L4_P04 | sofa | L4 | 1 | 21 | 21 | `46-0-attempt-1.ldr` |
| 48 | table_L4_P01 | table | L4 | 1 | 45 | 45 | `47-0-attempt-1.ldr` |
| 49 | table_L5_P01 | table | L5 | 1 | 30 | 30 | `48-0-attempt-1.ldr` |
| 50 | tower_L2_P01 | tower | L2 | 2 | 14 | 14 | `49-0-attempt-2.ldr` |
| 51 | tower_L3_P01 | tower | L3 | 2 | 37 | 37 | `50-0-attempt-2.ldr` |
| 52 | tower_L5_P01 | tower | L5 | 1 | 26 | 26 | `51-0-attempt-1.ldr` |
| 53 | train_L2_P01 | train | L2 | 1 | 38 | 38 | `52-0-attempt-1.ldr` |
| 54 | train_L3_P01 | train | L3 | 2 | 22 | 22 | `53-0-attempt-2.ldr` |
| 55 | vessel_L1_P01 | vessel | L1 | 1 | 16 | 16 | `54-0-attempt-1.ldr` |
| 56 | vessel_L2_P01 | vessel | L2 | 3 | 14 | 14 | `55-0-attempt-3.ldr` |
| 57 | vessel_L3_P01 | vessel | L3 | 3 | 42 | 42 | `56-0-attempt-3.ldr` |

