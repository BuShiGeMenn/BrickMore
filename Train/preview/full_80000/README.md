# 全部 80,000 个模型的独立预览器

下载最新版 Release 中的 `BrickMore_full_80000_preview_20261014.zip` 并解压。在 Windows 双击 `start_preview.cmd`；也可以运行 `python launch_preview.py`。浏览器自动打开 http://127.0.0.1:8770/index.html。需要 Python 3，查看模型时不需要联网，也不需要另行下载旧版数据包。

包含 A、B 两批、全部 21 类的 80,000 个模型，包括几何通过的 79,301 个和仍未通过的 699 个。B 批钢琴使用 2026-10-14 重新生成的 1,905 个模型，其余 78,095 个沿用全量发布。支持类别、批次、通过状态、编号筛选，以及体素/砖块对照、旋转缩放、五个视角和问题高亮。预览沿用修正遮挡的 WebGL 深度渲染器。

这个预览包包含每个模型的完整体素占用、颜色、砖块位置与检查摘要。为了减小体积，连续同色体素按行压缩存储，目标变化单独记录；解码后的源/目标坐标与颜色逐模型核对。完整 JSON/NPZ/OBJ/VOX、提示词、拼接 TXT/LDR和原报告仍由各模型的“完整模型包”链接下载。

每个预览记录附有四个实际输入文件的 SHA-256；包内 `preview_files_sha256.json` 用于校验模型预览与入口文件。`preview_verification.json` 记录完整性，`browser_verification.json` 记录浏览器检查。几何通过不代表完整物理认证。

仓库里的本目录提供界面与启动器，全部模型显示数据在 Release 的独立 ZIP 内。

下面的重新构建命令需要 Python 3.14；下载后的启动器使用普通 Python 3 即可。

```text
python tools/build_full_preview.py --base retile_full --replacement piano_b_supported --output full_preview_delivery
```
