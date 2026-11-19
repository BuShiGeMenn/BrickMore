# BrickGPT A 组第 130–260 条服务器生成包

本包使用已确认的两端包含范围，共 131 条提示词。第 130 条是 A26 单反相机 L5，第 260 条是 A52 拖船 L5。`Data/prompts.json` 保留原始英文文本、源文件行号、对象编号、Level 和输出文件名。

## 手动上传和环境检查

将 `.tar.gz` 和 `.sha256` 一起上传到数据分区的新目录，例如 `/mnt/brickmore-data/brickmore-jrd-20261025/uploads/brickgpt-a130-a260-20261115`。在上传目录运行：

```bash
df -hT .
sha256sum -c brickgpt-A130-A260-20261115.tar.gz.sha256 && tar -xzf brickgpt-A130-A260-20261115.tar.gz && cd BrickGPT_A130_A260
bash setup.sh --offline
```

脚本优先复用上次的服务器 `paper` Python 环境。`doctor` 检查 Python、CUDA、空闲显存、可用空间、推理依赖、权重文件和分词器。报告保存在 `.runtime/environment.json`。检查期间禁用联网。

如果报告只缺 `peft`、`accelerate` 或 `networkx`，可使用包里的离线 wheel：

```bash
bash run.sh deps
bash setup.sh --offline
```

wheel 安装在本包 `.runtime/deps`。如果缺 PyTorch、Transformers 或其他底层依赖，请设置 `BRICKGPT_PYTHON` 为具备这些依赖的 CUDA Python 解释器，再次执行检查。

## 检查和复用模型权重

预检会检查 `Downloads/models`、Hugging Face 缓存（含已保存的 commit 快照）、历史运行目录及常见本地合并权重目录。复用方式有两种：

- 原版 BrickGPT 已合并的 Llama 3.2 1B 权重。若预检找不到现有目录，在同一终端运行 `export BRICKGPT_MERGED=/实际路径/brickgpt_merged`，然后重跑检查。
- 官方 `AvaLovelace/BrickGPT` LoRA 加上 `meta-llama/Llama-3.2-1B-Instruct` 基座。外部目录可用 `BRICKGPT_BASE`、`BRICKGPT_ADAPTER` 指定。包内默认路径是 `Downloads/models/base`、`Downloads/models/adapter`。

有 `ENVIRONMENT READY` 就可运行小样本。若缺权重，优先核对旧机器或其他数据分区是否已有所需文件。

## 补下载权重

服务器能访问 Hugging Face 时，在包目录运行：

```bash
bash run.sh download
```

默认只下载未找到的组件。终端显示文件序号、进度、速度、ETA 和重连次数。已完成文件校验后跳过，半截文件和下载信息保存在 `.part`、`.part.json`。断网或 Ctrl+C 后用同样的命令续传。下载完成后再运行 `bash setup.sh --offline`。

内网服务器无法访问 Hugging Face 时，将本包也解压到联网电脑。用 PowerShell 或 Bash 在包目录运行：

```text
python Scripts/batch.py download --component adapter
python Scripts/batch.py download --component base
```

只运行缺失组件对应的命令。将补好的 `Downloads/models/adapter` 或 `Downloads/models/base` 整个目录转入服务器的对应路径。公网适配器和分词器合计约 31 MB，基座约 2.5 GB。仅在缺基座时，需要用已获授权的 Hugging Face 账号登录联网电脑的 HF CLI，或用该账号的只读 token 设置 `HF_TOKEN`。Token 只需在联网下载环境使用。[Llama 基座授权页](https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct)

## 生成、续跑与导出

环境检查通过后，在当前包目录执行：

```bash
bash run.sh smoke
bash run.sh full
```

`smoke` 跑第 130 条。它的结果会被 `full` 复用。模型载入和单条生成期间有终端心跳，生成完每条会立即保存，终端显示完成数、百分比与 ETA。首个模型完成后才有 ETA。

有 `tmux` 时可先执行 `tmux new -s brickgpt131`，再在会话内运行 `bash run.sh full`。按 `Ctrl+B` 再按 `D` 可离开会话，重新登录后用 `tmux attach -t brickgpt131` 查看。也可以在包目录另开终端执行 `bash run.sh status --watch`。

中断后使用相同命令、模型路径、设备和输出目录继续。已完成的 LDR 会做哈希核对。空结果、碰撞或越界输出会换种子重试，默认每条每次最多 3 个种子。若仍未得到有效 LDR，提示词会保持待处理，再执行 `full` 可从下一个种子继续。默认从种子 42 开始。

沿用历史 A/B 运行记录的配置：20 格空间，每轮最多新增 200 块，最多 8 次回退，使用连通性检查。LDR 采用官方导出颜色。可查看每条 `records/*.json` 中的 `connected` 和重试记录。

完整运行显示 `FINISHED full` 和 `131/131` 后执行：

```bash
bash run.sh export
```

LDR 在 `Results/brickgpt_A130_A260/ldr/`。导出文件是 `Results/brickgpt_A130_A260-results.tar.gz` 和同名校验文件，含 131 个 LDR、逐条生成记录、原始砖块文本和汇总。

官方代码：[BrickGPT](https://github.com/AvaLovelace1/BrickGPT)。官方适配器：[AvaLovelace/BrickGPT](https://huggingface.co/AvaLovelace/BrickGPT)。本包附带的第三方源码修订和修改说明见 `Vendor/PROVENANCE.json`。
