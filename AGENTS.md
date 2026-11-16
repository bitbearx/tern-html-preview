# 模块索引

本目录是独立 Tern 窗口插件，插件 ID 为 `html-preview`。用户使用说明见 [README.md](README.md)。

- `plugin.toml`：插件元信息与窗口入口。
- `window.luau`：Files 顶部按钮、HTML 源码上下文命令；不注册文件路由。
- `context.luau`：HTML 后缀判断、本地主机与当前源码面板识别。
- `preview.luau`：异步路径检查、WebView 创建与复用、普通浏览器交互恢复。
- `resolve_file.py`：普通文件校验、符号链接规范化、file URL 编码；不读取正文。
- `tern.d.luau`：`tern plugin types .` 生成的本机 SDK 类型。
- `test_resolve_file.py`：路径、编码、符号链接与非法目标核心测试。
- `test_preview.py`：隔离真实窗口的端到端核心回归，默认跳过，需 `HTML_PREVIEW_UI_TEST=1`。

## 约束

- 普通文件打开保持宿主行为；预览只读已保存文件，不自动保存或刷新。
- 异步回调使用新传入的窗口上下文，不能保留旧 `cx`。
- 不把文件路径拼入 shell；远程路径不能按本机路径处理。
- 浏览器会规范化 URL，复用时比较解码后的文件地址，不把 `+` 当作空格。
- UI 测试必须隔离 HOME、配置、socket 与 PATH；仅停止自己的守护进程。
- Tern `ctl` 的 scenario 字符串不支持 JSON 的 `\uXXXX` 转义，含中文路径使用 `json.dumps(..., ensure_ascii=False)`；`webcall` 的 JSON 则直接传递，不加二次引号。
