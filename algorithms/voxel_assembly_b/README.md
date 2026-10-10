# 彩色体素 LEGO 拼接与独立校验算法

算法标识：`B_exact_grid_assembly_v2` + `B_layer_mrv_exact_cover_v1`。完整方法说明见 [ALGORITHM.md](ALGORITHM.md)。纯 CPU，Python 3.12，无需模型权重、GPU、API key 或静力求解器。

本目录是算法源码，不是模型数据包。保留输入格点占用和 RGB，不填孔、不补桥、不删体素、不重涂颜色。体素侧贴和共用地面不能冒充 LEGO stud 连接。几何装配通过不等于物理稳定。

## 单模型使用

从本目录运行：

```text
python -B -m unittest -v test_assembly_pipeline test_single_model
python -B verify_repository.py
python -B assemble_one.py examples/bridge_y_up.json --out output_demo
python -B assemble_one.py your_model.json --out output_model
```

输入 JSON 为 `{"modelId":"...","voxels":[{"x":0,"y":0,"z":0,"color":[0,0,0]}]}`，整数坐标在0—47，Y向上，真实最低接地点Y=0；颜色是整数RGB三元组，包括黑色。示例是6格合成算法测试，不属于750—1250格的数据集样本。

输出目录必须不存在。成功输出 assembly.json、model.txt、model.ldr、validation.json、report.json；失败保留 model.draft.txt/model.draft.ldr，不写成功文件。TXT只编码尺寸和顺序，颜色以JSON/LDR为准。退出码0为通过，2为失败或输入错误。`verify_repository.py` 将15项测试结果及源码SHA-256写入 `reports/repository_tests.json`。

## 全数据集执行

数据集根目录需有 manifest.json，以及其中 modelPath 指向的规范 model.json。必须显式指定下载或解压后的实际路径；源码不会自动下载40,000个模型。

```text
python -B assembly_pipeline.py pilot --dataset PATH_TO_DATASET --out runs/B_pilot_v2 --workers 8
python -B assembly_pipeline.py verify --dataset PATH_TO_DATASET --out runs/B_pilot_v2 --workers 8
python -B assembly_pipeline.py run --dataset PATH_TO_DATASET --out runs/B_extended_v2 --workers 12
python -B assembly_pipeline.py verify --dataset PATH_TO_DATASET --out runs/B_extended_v2 --workers 12
python -B layer_cover.py run --out runs/B_layer_refinement_v1 --workers 12
python -B layer_cover.py verify --out runs/B_layer_refinement_v1 --workers 12
python -B finalize_assembly.py
```

可断点续跑，配置、源码或输入SHA变化后须用新目录。补充算法只重搜首轮搜索失败项，保持规则；最终索引每modelId一条，关联原来的五级配对提示词，不把两批文件重复算作新模型。

## 已执行的 AI_B 批次

本次测试对象为独立 AI_B 分片，不是仓库已有 AI_A 数据。40,000个模型全部处理和独立回读：最终3,288个几何装配通过（8.22%），31,627个不满足所选砖库/连接/支撑规则的必要条件，5,085个两套有界搜索仍未通过。补充搜索新增207个通过。具体类别数量见 [实测报告](reports/ASSEMBLY_REPORT.md)，机器摘要见 [assembly_summary.json](reports/assembly_summary.json)。

`reports/` 保存本地已完成批次的汇总证据，以及本仓库源码副本的测试结果。交付报告中的 ZIP 校验值对应本地算法归档；该 ZIP、完整逐模型索引和实际装配文件未包含在本仓库。原始适配器测试报告保留为 `adapter_tests.json`，仓库入口新增测试见 `repository_tests.json`。

原40,000个体素模型和200,000条双语训练记录未修改。失败没有丢弃或伪装成功。搜索失败不证明数学上无解；“规则下不可行”不等于所有LEGO零件及所有装配次序下都无解。

坐标显式 `(x,y,z) -> (x,z,y)`：Y-up转内部Z-up。水平1格=1stud，竖直1格=1标准砖高，LDraw比例20/20/24，实物高宽比与等距体素预览不同。

未验证抗倾覆、摩擦、接头受力、插入路径或实物搭建。始终 `staticVerified=null`、`fullPhysics=false`。A/B及历史去重不属于本算法，未因拼接而完成。

`toolkit_snapshot/` 为本地工具包五个实际依赖模块的未修改源码副本；来源见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。仓库不包含大体积运行资产、全量模型、完整提示词、账号配置或缓存。
