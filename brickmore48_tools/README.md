# brickmore48_tools — BrickMore-48 生成/验证/展示工具链

配套数据:`brickmore48_eval_630/`(630 模型 + 提示词 + 判决)。
本目录是生成、修复、导出、判决、展示全过程的代码,按角色分目录。

## 目录

| 目录 | 内容 |
|---|---|
| `pipeline/` | 生成主脚本与重生成。`gen_levels2.py`(采样→验证→重叠 union 修复→MILP 档位升级 12/60/180s→账本)、`regen_unsolved.py` / `regen_one_piano.py`(不可解条换种子重生成)、`download_retile_ab*.sh`(训练集下载,断点续传+慢速重连) |
| `export/` | 两种三维导出。`export_obj_batch*.py`(纯 Python OBJ:方砖+16 段凸点,**Z_SCALE=1.2** 真乐高层高比例,**stud 轴序已修正**)、`blender_glb_batch.py`(Blender 无头 LDR→GLB 真零件,ImportLDraw,Draco 压缩,**addGroundPlane 必须 False**)、`blender_open_models.py`(GUI 打开模型查看)、`obj2glb_one.py`(单个 OBJ→GLB) |
| `analysis/` | `raw_failure_autopsy.py`(失败病因量化:重叠/stud 咬合断裂/孤儿距离)、`think_test.py`(thinking 开关实验:现有 ckpt 思考块为空) |
| `prompts/` | `gen_round2_prompts.py` + `round2_prompts.json/.md`:按 48³ 训练集真实五级模板生成第二轮提示词(tower L3-L5 / train L1-L5 / vessel L2-L5,每组 10 条) |
| `judge_tool/` | 人工判决 HTTP 工具(三视图/放大/原版-重铺切换),**保存自动写 `best.md`**(Markdown 表:类别/等级/最佳 ID/标签/中英文提示词/备注,NONE=全部不合格) |
| `showcase/` | 三维展示站(21 类人工精选);`best105_page.html` + `best105.json` 为 105 自动评测推荐对照页 |

## 运行环境

- Python ≥3.12;生成需 CUDA torch 与 transformers(模型:Qwen3-1.7B BrickMore-48);
- 修复链依赖 `scipy`(HiGHS MILP);判决/展示仅标准库 + 本地 three.js r160 静态模块(已随目录附带 `static/js`、`static/utils`,含 Draco 解码器);
- Blender 5.0(无头):`blender.exe --background --factory-startup --python blender_glb_batch.py -- <job.txt> <log.txt>`;job 文件每行 `ldr路径|glb路径`;
- 判决工具:`cd judge_tool && python server.py`(端口 8123);展示站:`cd showcase && python server.py`(端口 8126)。

## 数据路径约定

脚本默认工作区为生成包布局(`BrickGPT/bmore48_levels2/<类>/L<级>V<变体>/`、`BrickGPT/bmore48_levels/<类>/L<级>/`),与 `brickmore48_eval_630/models/` 一一对应;移植时改脚本顶部常量即可。

## 关键算法说明

1. **判定链**:`run.py::validate`(格式/白名单/边界/重叠/体素连通)→ 重叠 **union 修复**(重复涂色格按一体素)→ `single_stud_cover.solve`(scipy MILP:精确覆盖 + 单一 stud 连通流,体素零增删)→ `single_stud_cover.audit` 独立复核。
2. **失败病因**(实测 525 条):10% 重叠(82% 仅 1-5 体素);**90% "贴身不咬合"**——体素层全连通但 stud 层中位裂 5 块,82% 孤儿紧贴主体(并排贴合、从不跨层交错)。这是"每块砖须与下层投影重叠≥1格"规则缺失,不是随机噪声。
3. **提示词必须落在训练分布内**:48³ 训练集每类只有一套标准描述 + 固定五级模板(L2 结构句/L3 几何句/L4 **比例句**/L5 配色句),见 `prompts/` 与 `round2_prompts.json` 的 `evidence` 字段;雉堞/锥顶/烟囱/锅炉/桅杆/帆等特征**训练集从未出现**,写进提示词会显著掉质量。

## 已知坑(代码里已规避,改代码时勿回退)

- OBJ 凸点几何曾把 Y/Z 轴写反(模型"点云"假象),`Z_SCALE=1.2` 是 LDraw 层高 24 LDu / 格距 20 LDu;
- Blender ImportLDraw 默认 `addGroundPlane=True` 会把大地面导进 GLB,相机取景全毁;
- 网页端:卡片 >16 张时每卡独立 WebGL 上下文会超浏览器上限(前几张空白),展示站已改单 renderer + scissor 多视口;envmap 软/硬件渲染亮度不一致,已弃用改纯灯光;
- 判决工具测试服务器的 cwd 会锁死所在目录,用 `Start-Process -WorkingDirectory` 启动。
