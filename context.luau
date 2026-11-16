-- 判断可预览的文件类型与主机，不读取文件内容。
local context = {}

-- HTML 扩展名忽略大小写，路径必须由 Tern 的文件上下文提供。
function context.is_html(path)
    if type(path) ~= "string" then return false end
    local lower = string.lower(path)
    return lower:sub(-5) == ".html" or lower:sub(-4) == ".htm"
end

-- 使用宿主提供的主机身份，不把远端路径当作本机路径校验。
function context.host(cx, name)
    for _, host in cx.hosts:list() do
        if host.name == name then return host end
    end
    return nil
end

-- 当前 HTML 源码同时携带主机和面板身份，供本地直读或远程快照分流。
function context.current_source(cx)
    local focused = cx.session:focused()
    if not focused then return nil end
    local pane = cx.session:pane(focused)
    if not pane or pane.kind ~= "file" or not context.is_html(pane.path) then return nil end
    for _, host in cx.hosts:list() do
        for _, id in host.panes do
            if id == focused then return { path = pane.path, host = host, pane = focused } end
        end
    end
    return nil
end

return context
