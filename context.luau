-- 判断可预览的文件类型与主机，不读取文件内容。
local context = {}

-- HTML 扩展名忽略大小写，路径必须由 Tern 的文件上下文提供。
function context.is_html(path)
    if type(path) ~= "string" then return false end
    local lower = string.lower(path)
    return lower:sub(-5) == ".html" or lower:sub(-4) == ".htm"
end

-- 按真实主机元信息识别本地文件，避免同名远程路径误读本机磁盘。
function context.is_local(cx, name)
    for _, host in cx.hosts:list() do
        if host.kind == "local" and host.name == name then return true end
    end
    return false
end

-- 只为当前本地 HTML 源码面板提供命令，不扫描或读取源码正文。
function context.current_source(cx)
    local focused = cx.session:focused()
    if not focused then return nil end
    local pane = cx.session:pane(focused)
    if not pane or pane.kind ~= "file" or not context.is_html(pane.path) then return nil end
    for _, host in cx.hosts:list() do
        if host.kind == "local" then
            for _, id in host.panes do
                if id == focused then return pane.path end
            end
        end
    end
    return nil
end

return context
