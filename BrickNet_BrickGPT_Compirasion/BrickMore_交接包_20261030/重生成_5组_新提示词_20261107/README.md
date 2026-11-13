# BrickMore 五组重生成

模型：`Kyle308666/BrickGPT-Qwen3-1.7B-BrickMore-48`。
固定版本：`92d1c595f5fe076971cc2633d6844f097a84eef3`。

双击 `start_preview.cmd` 打开可旋转三维预览（需要 Python，无需权重或 GPU）。
`overview.png` 是实际生成模型的多角度总览。每个模型同时提供 GLB、LDR、TXT 和原始推理输出。

仅处理 camera L2、car L4、car L5、guitar L1、vessel L1。car L3 和 piano L5 的原人工选择未修改。
五条推荐提示词均重新构造措辞，参考 dataset 对应 Level 的训练元素与复杂度，不直接使用 dataset 原始 caption。当前推荐原文见 recommended_prompts.txt / .json；全部版本和分级证据见 revised_prompts.json。
第一批五个候选已由用户判为不合格；直接采用 dataset 原 caption 的第二批只作对照。前两批保留在单独目录，不计入本批。
原始输出与实际解码参数见各模型目录。主候选采用确定性解码，汽车 L5 另提供采样候选供比较。

all_attempts_manifest.json 保留本批所有尝试（包括已淘汰结果）；预览只显示几何通过且未被外形初审淘汰的候选。

| 组 | 种子 | 提示词来源 | 几何与凸点检查 |
|---|---:|---|---|
| camera_L2 | 42 | reconstructed-camera-L2-v1 | 通过（外形待人工复审） |
| car_L4 | 42 | reconstructed-car-L4-v1 | 通过（外形待人工复审） |
| car_L5 | 42 | reconstructed-car-L5-v1 | 通过（外形待人工复审） |
| guitar_L1 | 42 | reconstructed-guitar-L1-v2 | 通过（外形待人工复审） |
| vessel_L1 | 42 | reconstructed-vessel-L1-v2 | 通过（外形待人工复审） |
| car_L5 | 104 | reconstructed-car-L5-v1 | 通过（外形待人工复审） |

确定性解码出现相同原始输出：car_L4_P1_G / car_L5_P1_G。另附汽车 L5 采样候选供比较。

黄色是统一展示色，模型输出没有颜色。
raw.txt 是未经改写的模型输出；raw_geometry.txt 为沿用既有审查管线 YX 尺寸约定后的 XY 标准排砖。
保形重铺严格覆盖原始砖块占用的体素并集，不增删体素；原始重叠另有记录。
该尺寸约定与既有 630 模型审查一致，尚未对照原训练转换器核验。
几何无重叠、无越界、单一凸点连通不等同于物理稳定性认证。模型外形需要人工复审。
