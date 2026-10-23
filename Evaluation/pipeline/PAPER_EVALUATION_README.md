# BrickNet 测评脚本盘点与补齐

更新：2026-10-24。本次新增独立脚本，没有修改已完成 Base 评分所依赖的 evaluate_models.py、render.html 或其结果；也没有改动人工标注。

## 盘点

| 功能 | 原有情况 | 现在的入口 |
| --- | --- | --- |
| GLB 清单、Three.js 八视角渲染、Base PE/SigLIP2 | 已有，已运行 | evaluate_models.py，保持原样 |
| 论文大模型图文评分 | 有官方三个脚本，仅接收 tar，无本项目 PNG 适配/续跑 | evaluate_paper_images.py：VQA、PE、SigLIP2，或 prepare_paper_inputs.py pack 后调用原脚本 |
| 结构解析与碰撞检测 | 有 BrickNet 0.1.1，非原论文检测版本 | 独立 0.1.0 环境 + evaluate_structure.py |
| P_inv 两种聚合、覆盖率、首次失败及生存曲线数据 | 缺 | evaluate_structure.py |
| PT/SFT 生成、解析失败重生成及逐次日志 | 缺（本地精简仓库没有 scripts/） | generate_paper_samples.py |
| path 转 LDR、官方渲染器适配 | 原有 path2ldr，缺流程适配 | prepare_paper_inputs.py convert/render |
| PT/SFT 困惑度 | 缺 | evaluate_perplexity.py |
| 四项指标关联、分组、raw/stitched 配对 | 仅 Base 报告 | report_paper_eval.py |
| 环境/脚本/结构输入审计 | 缺 | audit_paper_eval.py |
| 独立旧版环境、统一运行入口 | 缺 | setup_paper_environment.cmd，run_paper_evaluation.cmd |

所有新增 Python 文件均在本目录。通用 I/O、哈希和续跑约束位于 paper_common.py。数值与异常路径回归测试位于 tests/test_paper_eval.py。

## 协议依据与边界

来源：[论文第 4、5 节](https://arxiv.org/html/2604.22984v1)、[官方 eval README](https://github.com/kulits/BrickNet/blob/master/eval/README.md)、[官方结构评分代码](https://github.com/kulits/BrickNet/blob/master/src/bricknet/score.py)、[官方生成代码](https://github.com/kulits/BrickNet/blob/master/scripts/generate.py)、[官方渲染仓库](https://github.com/kulits/BrickNet-Render)。核对时主仓库树为 283faf73063d3af4eb378b624df68dec683e4695，渲染仓库树为 b49e8733782a5fa7040cc776b5fba8c55b0b894e。

- 碰撞复现使用 PyPI bricknet 0.1.0 和 inset 网格。官方文档提到的 v0.1.0 Git 标签在核对时返回 404，故 requirements 固定发行包 URL 和已验证 SHA-256，未用新版代替。
- paper-text 预设按论文文字选择 Qwen2.5-VL-7B；released-code 按公开代码选择 Qwen2-VL-7B。两者的 PE/SigLIP2 均为 bigG/Giant。local 为 Qwen2-VL-2B、PE Base 和 SigLIP2 Base，不属于原模型复现。
- 图文主分数为八视角 max，再对模型平均。VQA 为整个词表上首个回答 token 的 Yes 概率，非 Yes/No 归一化；SigLIP2 为 sigmoid(logit)；PE 为归一化余弦。
- 结构主输出同时给 pinv_macro 和 pinv_micro。默认 pinv 汇总留空，只有明确 --pinv-aggregation macro/micro 才选择其一；公开代码不足以确认论文采用哪一种，因此始终标记聚合对齐未验证。解析失败后缀不伪造成有效动作，缺网格不计零碰撞。
- 无条件生成默认 NS（temperature=1、top-k=20、top-p=0.95），65,536 样本、100 parts；AS 关闭 top-k/top-p 截断。条件生成只拒绝无法解析的结果，绝不先过滤碰撞。重试有 50 次工程上限，耗尽时退出失败并保留全部尝试，不能当成完整评估。
- 表 4 实现为路径 token 的 NLL 加权困惑度；条件模式屏蔽 caption。窗口/EOS/验证路径选取的原始完整细节尚未公开确认，记录为可配置复现实验，不承诺与论文表格逐值一致。
- 所有评分保存配置、依赖、模型 revision 或本地权重哈希和输入哈希。配置/输入改变时拒绝混合续跑。历史渲染器机位灯光是否完全匹配也需要另行核准，结果不自动标为 exact reproduction。

## 环境

原有 `D:\PythonEnvs\brickmore-eval` 保持现状。新建独立的 `D:\PythonEnvs\brickmore-paper`，沿用已安装 Python 3.12。

```bat
cd /d D:\BrickMore
Evaluation\pipeline\setup_paper_environment.cmd cpu
Evaluation\pipeline\run_paper_evaluation.cmd audit
```

cpu 安装原版 BrickNet、MeshLib、NumPy、SciPy，不安装 PyTorch。需要生成/图文/PPL 时执行 `setup_paper_environment.cmd cuda`；这会向新环境安装 CUDA PyTorch 和锁定的增量依赖，可能产生较大下载。量化不是默认选项，需要额外验证 bitsandbytes 的本机兼容性。

直接运行下方 python 命令前，在 CMD 中启用新环境及 D 盘缓存（setup 脚本本身的变量只在安装进程内生效）：

```bat
call D:\PythonEnvs\brickmore-paper\Scripts\activate.bat
set "PYTHONUTF8=1"
set "HF_HOME=D:\PythonEnvs\brickmore-paper\cache\huggingface"
set "PIP_CACHE_DIR=D:\PythonEnvs\brickmore-paper\cache\pip"
set "TEMP=D:\PythonEnvs\brickmore-paper\cache\temp"
set "TMP=%TEMP%"
set "BRICKNET_DATA=D:\PythonEnvs\brickmore-paper\cache\bricknet-v010"
```

原始碰撞网格单独下载，约 369MB；未随本次脚本验证下载：

```bat
set "BRICKNET_DATA=D:\PythonEnvs\brickmore-paper\cache\bricknet-v010"
set "PYTHONUTF8=1"
D:\PythonEnvs\brickmore-paper\Scripts\python.exe -m bricknet fetch-meshes
```

官方当前渲染器需独立 Python 3.13+ 和 Blender/bpy 5.1+，不能装进这个 3.12 环境。render 入口通过 --renderer-python 指向独立环境，启动时检查版本。需先在该环境安装官方 renderer 并执行 `python -m bricknet_render fetch-glbs`。目前 renderer 使用其安装版本的默认机位/灯光，并保存软件版本与原图哈希。

## 本项目现有图片：无需重新渲染

仅验证文件与计划，不加载或下载模型：

```bat
D:\PythonEnvs\brickmore-eval\Scripts\python.exe Evaluation\pipeline\evaluate_paper_images.py --metric vqa --preset local --renders Results\model_eval_20261021\renders.jsonl --out Results\paper_vqa_local\vqa.jsonl --limit 8 --dry-run
```

配置好新环境 CUDA 依赖后，去掉 --dry-run 才进行实际 VQA 推理。先用 --limit 8 单独输出做显存预跑；扩大到全量时使用新的输出文件（limit 改变会更改配置）。本机 6GB 不自动运行 7B/Giant/bigG；脚本也不会静默降级模型或精度。

可用 --model 指向现有本地权重，--offline 禁止模型联网下载。remote 模型启动时先解析并记录不可变 commit。每份 GLB 的八视角依次评分，默认 view batch=1；local VQA 固定较小像素预算，paper-text/released-code 默认沿用模型处理器预算。参数变化均进入配置签名。

如果要直接运行官方原评分脚本，将现有 PNG 打包：

```bat
D:\PythonEnvs\brickmore-eval\Scripts\python.exe Evaluation\pipeline\prepare_paper_inputs.py pack --renders Results\model_eval_20261021\renders.jsonl --out Results\paper_render_shards
```

输出 captions.jsonl 和顺序严格对应的 tar 分片，跨分片也保持 prompt_index 全局唯一。

## 官方验证集与端到端顺序

先通过[官方表单](https://forms.gle/dm4eYSa5gh4DqzRT6)取得验证数据，不包含自动申请动作。captions_val.jsonl 每条需 id、caption；本项目清单则使用 sample_id、caption。路径输入用 path 或 text 字段，生成和后续步骤保留同一 sample_id。

下面的路径是示例，应替换成真实数据与模型位置。先进入项目根目录并设置上述 BRICKNET_DATA，所有命令在新 paper 环境中执行。

```bat
python Evaluation\pipeline\generate_paper_samples.py --mode conditional --model Qwen/Qwen3-0.6B --lora kulits/BrickNet-0.6B-PT --lora kulits/BrickNet-0.6B-SFT --prompts D:\BrickNetData\captions_val.jsonl --out Results\paper_run\generated.jsonl
python Evaluation\pipeline\evaluate_structure.py --input Results\paper_run\generated.jsonl --out Results\paper_run\structure.jsonl --data-dir D:\PythonEnvs\brickmore-paper\cache\bricknet-v010
python Evaluation\pipeline\prepare_paper_inputs.py convert --input Results\paper_run\generated.jsonl --out Results\paper_run\ldr
python Evaluation\pipeline\prepare_paper_inputs.py render --input Results\paper_run\ldr\ldr_manifest.jsonl --out Results\paper_run\rendered --renderer-python D:\PythonEnvs\brickmore-render\Scripts\python.exe
python Evaluation\pipeline\evaluate_paper_images.py --metric vqa --preset paper-text --renders Results\paper_run\rendered\renders.jsonl --out Results\paper_run\vqa_qwen25vl7b.jsonl
python Evaluation\pipeline\evaluate_paper_images.py --metric pe --preset paper-text --renders Results\paper_run\rendered\renders.jsonl --out Results\paper_run\pe_bigg.jsonl
python Evaluation\pipeline\evaluate_paper_images.py --metric siglip2 --preset paper-text --renders Results\paper_run\rendered\renders.jsonl --out Results\paper_run\siglip2_giant.jsonl
python Evaluation\pipeline\report_paper_eval.py --manifest Results\paper_run\generated.jsonl --structure Results\paper_run\structure.jsonl --images vqa_qwen25vl7b=Results\paper_run\vqa_qwen25vl7b.jsonl --images pe_bigg=Results\paper_run\pe_bigg.jsonl --images siglip2_giant=Results\paper_run\siglip2_giant.jsonl --out Results\paper_run\report
```

模型先使用 --dry-run 检查计划；需足够硬件才运行原版大模型。多种模型大小及 PT/SFT/No-PT 等实验通过改变 --model/--lora，并分别使用独立输出目录运行，不将不同模型混成一个平均分。

表 2：generate 改为 --mode unconditional，默认 65,536 条、100 parts；分别 --sampling ns/as 输出不同文件，再运行 evaluate_structure，summary 含逐步生存率和首次失败前均值。生成的语法失败样本保留，不进行重试过滤。

表 4：输入应为真实留出 path，而非模型生成结果。join-captions 支持直接读取官方 .jsonl.xz，按 source/id 关联 caption，保留所有路径和唯一身份；不自动将 45,516 条路径当成 512 个独立模型。示例：

```bat
python Evaluation\pipeline\prepare_paper_inputs.py join-captions --paths D:\BrickNetData\paths_val.jsonl.xz --captions D:\BrickNetData\captions_val.jsonl.xz --out D:\BrickNetData\val_paths_with_caption.jsonl
python Evaluation\pipeline\evaluate_perplexity.py --input D:\BrickNetData\val_paths_with_caption.jsonl --model Qwen/Qwen3-0.6B --lora kulits/BrickNet-0.6B-PT --lora kulits/BrickNet-0.6B-SFT --conditional --out Results\paper_run\ppl.jsonl
```

当前 Model 只有 918 份 GLB，缺原始生成路径，不能用于上述原版 P_inv/PPL。不要通过碰撞过滤的 sample 命令重建待测路径，避免在评价前筛掉失败。

## 测试

```bat
D:\PythonEnvs\brickmore-eval\Scripts\python.exe -X utf8 -m unittest discover -s Evaluation\pipeline\tests -v
D:\PythonEnvs\brickmore-paper\Scripts\python.exe -X utf8 -m unittest discover -s Evaluation\pipeline\tests -v
```

前者覆盖 PyTorch 数值、窗口、聚合和断点逻辑；后者验证实际 0.1.0 解析、合成几何上的碰撞内核与缺网格行为。旧版 BrickNet 的零件目录默认用系统编码读取，Windows 中文系统须用 -X utf8 或提前 set PYTHONUTF8=1；两个 CMD 入口已自动设置，原始发行包源码不作修改。不同环境缺少的可选后端测试会显式 skip。具体本次验证结果见 Results/paper_script_validation_20261024，不把无权重的单元测试等同于完整 7B 测评。

本次验证：13 项独立测试在两个环境中全部覆盖通过；原版解析器与 MeshLib 合成相交/分离/重复零件测试通过。新图文入口用缓存的 Base 权重实际运行两份 GLB、每项 16 张图片；与原流程逐视角最大绝对差为 SigLIP2 1.29e-7、PE 1.17e-4（视角 batch 不同），并验证了 tar 分片、LDR 转换和 HTML/CSV 汇总。CUDA 增量依赖解析 dry-run 成功，但没有安装新环境的整套 CUDA 依赖或下载 VQA/生成大模型。
