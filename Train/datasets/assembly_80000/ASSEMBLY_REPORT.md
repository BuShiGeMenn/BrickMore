# A/B 80,000 模型 LEGO 拼接与独立回读交付

两批均实际处理，成功和失败各保留一份被选结果；模型数不是成功装配数。

| 分片 | 已处理 | 几何通过 | 所选规则必要条件失败 | 有界搜索未通过 |
|---|---:|---:|---:|---:|
| AI_A | 40,000 | 4,614 | 34,013 | 1,373 |
| AI_B | 40,000 | 3,288 | 31,627 | 5,085 |

所有公开 ZIP 已检查 CRC、逐文件 SHA，并从 ZIP 内的真实 JSON/TXT/LDR 独立重建校验。
每模型含原始 source.model.json、source.prompts.json、assembly.json、validation.json、report.json，以及成功 model.txt/model.ldr 或明确命名的失败 model.draft.txt/model.draft.ldr。
原提示词中的 modelJsonPath/modelNpzPath 保持原始分片相对路径，不重写原记录；本包定位使用统一 assembly_index.jsonl 的 sourceModelJsonPath/sourcePairedPromptsPath。
几何通过范围：精确占用、RGB、无碰撞、标准同色矩形单砖高砖库、逐层下支撑、单 stud 组件和接地。
必要条件失败仅针对所选砖库和策略；有界搜索失败不证明无解。失败草稿不是可用装配。
未验证静力、抗倾覆、接头受力、摩擦、插入路径或实物搭建，staticVerified=null / fullPhysics=false。
源 Y-up [x,y,z] 转内部 Z-up [x,z,y]，不修改原占用/RGB。水平一格=1stud，竖直一格=1标准砖高，LDraw比例20/20/24，实物比例不同于等距体素预览。
下载所有 AI_A_assembly_*.zip、AI_B_assembly_*.zip 及 assembly_metadata.zip，安全解压到同一目录。与原体素数据集建议分开目录。
