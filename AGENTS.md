# 模块索引

本目录是独立 Tern 窗口插件，插件 ID 为 `html-preview`。用户使用说明见 [README.md](README.md)。

- `plugin.toml`：插件元信息与窗口入口。
- `window.luau`：Files 顶部按钮、HTML 源码上下文命令；不注册文件路由。
- `context.luau`：HTML 后缀、主机身份与当前源码面板识别。
- `preview.luau`：本地文件路径检查与直接预览。
- `browser.luau`：共用 WebView 创建、复用、原生刷新和普通浏览器交互恢复。
- `remote.luau`：直接调用 `cx.docs:read()` 的源码快照入口、取消和引用回收。
- `snapshots.luau`：串行快照写入与清理队列，避免异步操作互相删除文件。
- `snapshot_file.py`：私有快照目录、UTF-8 原子写入和按窗口引用清理。
- `resolve_file.py`：普通文件校验、符号链接规范化、file URL 编码；不读取正文。
- `tern.d.luau`：`tern plugin types .` 生成的本机 SDK 类型。
- `test_resolve_file.py`：路径、编码、符号链接与非法目标核心测试。
- `test_snapshot_file.py`：长行完整性、编码、权限、主机/窗口隔离和引用回收测试。
- `test_preview.py`：本地行为及双 loopback 源码快照的真实窗口回归，默认跳过，需 `HTML_PREVIEW_UI_TEST=1`。

## 约束

- 普通文件打开保持宿主行为。本地预览只读已保存文件；远程入口保存文档接口的完整返回值，再次点击重新读取并刷新，不自动保存源码或同步外部资源。
- 异步回调使用新传入的窗口上下文，不能保留旧 `cx`。
- 不把文件路径拼入 shell。`cx.docs:read()` 在当前版本可能读到本机同名缓冲区；这是已确认且明确保留的 SDK 限制，详见 README，不能宣称其返回值必然来自远端。
- 浏览器会规范化 URL，复用时比较解码后的文件地址，不把 `+` 当作空格。
- 当前浏览器自动化无法接受远程 owner，快照挂载到本机标签，禁止手算或修改宿主面板编号。
- 快照写入与清理必须串行，清理执行时重新取得活动 URL 和在途来源键；关闭事件、窗口恢复和旧 VM 进程结束时触发回收。
- UI 测试必须隔离 HOME、配置、socket 与 PATH；仅停止自己的守护进程。
- Tern `ctl` 的 scenario 字符串不支持 JSON 的 `\uXXXX` 转义，含中文路径使用 `json.dumps(..., ensure_ascii=False)`；`webcall` 的 JSON 则直接传递，不加二次引号。
