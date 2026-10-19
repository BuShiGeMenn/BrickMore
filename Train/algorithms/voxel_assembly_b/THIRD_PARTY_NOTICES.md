# 来源与第三方边界

本阶段复用工作区 `brick_assembly_toolkit` 的五个 CPU 模块，原文件未修改；副本在 `toolkit_snapshot/`，逐文件 SHA-256 在各运行目录 `config.json`。新增数据适配、独立校验、批处理、逐层覆盖与交付整合代码位于本目录。未打包模型权重、官方生成器、静力求解器或零件网格库。

以下为原工具包 `THIRD_PARTY_NOTICES.md` 的来源记录，其许可判断属于原记录，本阶段没有新增第三方源码或替第三方重新授权：

`optimized_geometry.py` 来源于本项目 2026-10-09 增强算法版本。官方 BrickGPT 上游链接为 [AvaLovelace/BrickGPT](https://github.com/AvaLovelace/BrickGPT)。原记录说明官方仓库采用 MIT 许可；这不意味着本阶段新编写代码由上游作者授权或负责。

LDraw 零件编号和网格转换用于格式互操作；本阶段没有包含 LDraw 零件网格库。查看 LDR 需要接收方的查看器及其零件库。

原 Ocean 分析对象为 [QuasarH-lab/Ocean-work-main](https://github.com/QuasarH-lab/Ocean-work-main)，提交 `cd8bb67eefe742ca65f92994f1ebb49545215b1f`。本阶段不包含该仓库源码。原工具包记录未找到 LICENSE，公开可访问不能代替复制、修改或分发许可。

本阶段没有安装或打包 Python、NumPy、Torch/Transformers、Qwen 或 Gurobi 等第三方二进制。
