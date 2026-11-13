# 本地验证记录

5 项自检通过；6 条模型、48 张图完成原版碰撞内核与统一网格渲染测试。相同命令再次运行复用全部结果。PE / SigLIP2 的 Base 缓存模型各完成 2 条、16 视角 GPU 接口验证，PE 再次执行显示 `2/2 CACHED_ALL`。

`local_validation.json` 记录实际范围与结果，`local_render_contact.png` 是渲染检查图。此处的 Base 分数仅验证接口。正式 7B / bigG / Giant 四项全流程需在内网服务器运行 `bash run.sh smoke` 后确认。

补充验证：已修正 Windows 写文件造成的 Shell CRLF；三个入口脚本的 LF 字节检查、Bash 前两行实际执行及校验记录均通过。原地修复命令在原始包副本上连续运行两次通过。
