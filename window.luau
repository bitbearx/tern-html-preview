-- 手动预览入口：保留 Tern 默认文件打开和编辑行为。
local context = require("./context")
local preview = require("./preview")

tern.files.button({
    id = "preview",
    title = "预览 HTML",
    icon = "globe",
    -- Files 顶部按钮沿用宿主的显隐规则，只接受单个本地 HTML 文件。
    run = function(files, cx)
        if files.tab ~= "files" then
            cx:toast("info", "请选择 HTML 文件", "请切换到 Files 文件列表后选择一个文件")
            return
        end
        if #files.selection ~= 1 or not context.is_html(files.selection[1]) then
            cx:toast("info", "请选择 HTML 文件", "请只选择一个 .html 或 .htm 文件")
            return
        end
        if not context.is_local(cx, files.host) then
            cx:toast("info", "暂不支持远程 HTML 文件", "请先将页面及依赖资源保存到本机")
            return
        end
        preview.open(cx, files.selection[1])
    end,
})

tern.command({
    id = "preview-current",
    title = "HTML Preview: 预览当前 HTML",
    icon = "globe",
    -- 非 HTML、远程文件和浏览器面板不显示此命令。
    available = function(cx)
        return context.current_source(cx) ~= nil
    end,
    -- 再次检查上下文，避免命令面板打开后目标面板已改变。
    run = function(cx)
        local path = context.current_source(cx)
        if not path then
            cx:toast("info", "没有可预览的 HTML", "请先打开一个本地 HTML 源码面板")
            return
        end
        preview.open(cx, path)
    end,
})
