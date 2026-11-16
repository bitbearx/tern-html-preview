# HTML Preview for Tern

手动将本地 HTML 文件放到 Tern 内置浏览器中预览，不安装文件路由，不接管原有文件打开行为。

## 安装

需要桌面版 Tern 和 `python3`。已在 macOS 的 Tern 0.9.23（35c63ab）验证；其他平台尚未实测。

```sh
cd tern-html-preview
tern plugin link .
```

插件 ID 为 `html-preview`。修改插件文件后 Tern 会自动重新加载；卸载链接：

```sh
tern plugin unlink html-preview
```

## 按钮在哪里、何时出现

- 按钮位于 **Files 文件树顶部工具栏**，提示文字为“预览 HTML”，使用地球图标。
- 跟随 Tern 原生工具栏规则：鼠标移入 Files 面板时显示，按钮获得键盘焦点时也显示。
- SDK 不提供依据选中文件动态显隐的接口，因此按钮不会只在选择 HTML 时出现；在 Changes、Refs 页签中也可能显示。
- 在 Files 页签选择一个本地 `.html` / `.htm` 文件后点击，右侧打开浏览器分屏。扩展名不区分大小写。
- 未选择、选择多个文件、选择非 HTML、目录或远程文件时提示原因，不打开空预览。无显式选择时，Tern 可能把文件树当前光标行作为选择传给插件。

## 源码与预览

当前焦点是本地 HTML 源码面板时，命令面板提供 **HTML Preview: 预览当前 HTML**；普通文本、浏览器和远程文件面板不显示此命令。Files 收起时也可以使用。

插件不会把普通文件点击改成自动渲染，也不会改变 `tern open --wait`。Tern 自身的行为仍然保留：此版本单击文件可以显示临时源码预览，正式打开 HTML 可能直接进入内置浏览器。需要持久源码面板时，可以带行号打开：

```sh
tern open '/绝对路径/页面.html:1'
```

同一窗口已有相同文件的浏览器面板时，预览按钮会聚焦该面板，不重复创建、不重新加载。中文、空格、`#`、`%`、`?`、`+` 等文件名字符会正确编码；符号链接解析到真实文件后复用相同预览。链接页面的相对资源以真实文件所在目录为基址。

- 展示的是**磁盘上已保存的内容**，不是编辑器中的未保存缓冲区。
- 修改后先保存，再使用内置浏览器的刷新按钮；没有自动刷新。
- 关闭预览不会关闭源码面板或终端。刷新、导航、关闭均使用 Tern 原生控件。
- 页面导航到其他文件后，再次预览原文件不会覆盖它，而是查找或新建原文件的预览。

## 范围与安全

- 仅支持本地普通 HTML 文件。远程文件需要先将页面及依赖资源保存到本机。
- 使用 `file://` 加载，不启动 HTTP 服务。普通相对 CSS、JavaScript 和交互已经实测；ES Modules、`fetch()`、跨域请求及需要 dev server 的项目应使用合适的 HTTP 环境，不绕过浏览器安全策略。
- 预览会执行 HTML 中的脚本，也可能产生页面自身的网络请求。只预览可信内容。
- 新建的浏览器面板使用 `html-preview` profile；复用已有同址面板时保留该面板原来的 profile。独立 profile 不等于断网或权限沙箱。
- 插件通过参数数组运行 `python3 resolve_file.py`，仅查询路径元信息，不读取 HTML 正文、不拼接 shell 命令、不上传文件。运行环境缺少 `python3` 时会提示错误。

## 验证

核心路径测试：

```sh
python3 -m unittest -v test_resolve_file
```

真实界面测试（会打开独立 Tern 窗口）：

```sh
HTML_PREVIEW_UI_TEST=1 python3 -m unittest -v test_preview
```

界面测试隔离 HOME、Tern 配置、守护进程 socket 和可写 PATH，结束后清理自己的窗口和会话。覆盖无效选择、普通点击不触发插件渲染、HTML/CSS/JS、按钮交互、URL 规范化与符号链接复用、源码上下文命令。

模块索引见 [AGENTS.md](AGENTS.md)。接口依据：[Files 按钮](https://docs.stencil.so/tern/reference/api-window.html#ternfilesbutton)、[内置浏览器](https://docs.stencil.so/tern/reference/api-window.html#browser-cx)。
