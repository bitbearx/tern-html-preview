-- 手动预览入口：保留 Tern 默认文件打开和编辑行为。
local context = require("./context")
local preview = require("./preview")
local remote = require("./remote")

-- 本地保持原文件预览；远程入口只读取文档接口并生成单文件快照。
local function open_source(cx, source)
    if source.host.kind == "remote" then
        remote.open(cx, source)
    else
        preview.open(cx, source.path)
    end
end

tern.files.button({
    id = "preview",
    title = "预览 HTML",
    icon = "globe",
    -- Files 顶部按钮沿用宿主的显隐规则，只接受单个 HTML 文件。
    run = function(files, cx)
        if files.tab ~= "files" then
            cx:toast("info", "请选择 HTML 文件", "请切换到 Files 文件列表后选择一个文件")
            return
        end
        if #files.selection ~= 1 or not context.is_html(files.selection[1]) then
            cx:toast("info", "请选择 HTML 文件", "请只选择一个 .html 或 .htm 文件")
            return
        end
        local host = context.host(cx, files.host)
        if not host then
            cx:toast("error", "无法确定文件来源", "文件所在主机已不可用，请重新选择文件")
            return
        end
        open_source(cx, { path = files.selection[1], host = host })
    end,
})

tern.command({
    id = "preview-current",
    title = "HTML Preview: 预览当前 HTML",
    icon = "globe",
    -- 只对已打开的 HTML 源码面板提供命令，包括远程面板。
    available = function(cx)
        return context.current_source(cx) ~= nil
    end,
    -- 再次检查上下文，避免命令面板打开后目标面板已改变。
    run = function(cx)
        local source = context.current_source(cx)
        if not source then
            cx:toast("info", "没有可预览的 HTML", "请先打开一个 HTML 源码面板")
            return
        end
        open_source(cx, source)
    end,
})

-- 会话恢复完成后再回收；插件重载后关闭事件仍可根据活动 URL 清理快照。
tern.on("window_start", remote.collect)
tern.on("pane_closed", remote.closed)
-- 旧 VM 的写入进程结束时回收孤立快照，不依赖已经失效的回调。
tern.on("process_exit", function(_, cx)
    remote.collect(cx)
end)
