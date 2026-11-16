-- 按选定方案直接调用 docs:read，保留 SDK 的完整返回值；来源限制见 README。
local browser = require("./browser")
local snapshots = require("./snapshots")
local remote = {}
local pending = {}
local panels = {}

-- 同路径在不同主机上必须使用不同快照，不依赖易变的面板编号。
local function source_key(source)
    return tern.json.encode({ host = source.host.address or source.host.name, path = source.path })
end

-- 从真实浏览器 URL 和在途请求收集引用，插件重载后也能保留活动快照。
local function references(cx)
    local urls = tern.json.array()
    local keys = tern.json.array()
    for _, pane in cx.session:panes() do
        if pane.kind == "browser" and pane.url then table.insert(urls, pane.url) end
    end
    for key in pending do table.insert(keys, key) end
    return { urls = urls, pending = keys }
end

-- 清理已关闭的快照；不会关闭面板或影响其他窗口。
function remote.collect(cx)
    snapshots.collect(cx, references)
end

-- 浏览器自动化只接受本机目标；复用本机标签，完全没有本机面板时才创建标签。
local function local_owner(cx)
    for _, host in cx.hosts:list() do
        if host.kind == "local" then
            local candidate = nil
            for _, id in host.panes do
                local pane = cx.session:pane(id)
                if pane and pane.tab and not pane.parked then
                    if pane.focused then return id end
                    candidate = candidate or id
                end
            end
            return candidate or cx.hosts:terminal(host.id, { cwd = tern.plugin.data })
        end
    end
    return nil
end

-- 读源码、写入独立快照，再创建或刷新预览；不会同步任何外部资源。
function remote.open(cx, source)
    local key = source_key(source)
    if pending[key] then return end
    local owner = cx.session:focused()
    if not owner then
        cx:toast("info", "无法打开 HTML 预览", "请先打开一个标签页")
        return
    end
    local request = { owner = owner, previous = panels[key], cancelled = false }
    pending[key] = request
    -- 所有成功、失败与取消路径都释放在途引用，然后回收不再显示的快照。
    local function finish(pane, err, fresh)
        pending[key] = nil
        if pane then panels[key] = pane end
        if err and not request.cancelled then fresh:toast("error", "无法预览 HTML 源码", err) end
        remote.collect(fresh)
    end
    local ok, failure = pcall(function()
        cx.docs:read(source.path):next(function(text, err, fresh)
            if not fresh then return end
            if request.cancelled then finish(nil, nil, fresh) return end
            if err or type(text) ~= "string" then
                finish(nil, err or "文档接口没有返回完整源码字符串", fresh)
                return
            end
            snapshots.save(fresh, key, text, function(snapshot, write_err, next_cx)
                if request.cancelled then finish(nil, nil, next_cx) return end
                if write_err then finish(nil, write_err, next_cx) return end
                if not next_cx.session:pane(owner) then finish(nil, nil, next_cx) return end
                local found, target = pcall(local_owner, next_cx)
                if not found or not target then
                    finish(nil, if found then "没有可用的本机预览面板" else tostring(target), next_cx)
                    return
                end
                next_cx.layout:focus(target)
                browser.show(next_cx, target, snapshot.url, true, finish)
            end)
        end)
    end)
    if not ok then finish(nil, tostring(failure), cx) end
end

-- 原始面板或已有预览关闭后取消在途请求，防止异步结果重新打开已关闭的预览。
function remote.closed(ev, cx)
    for _, request in pending do
        if request.owner == ev.pane or request.previous == ev.pane then request.cancelled = true end
    end
    for key, pane in panels do
        if pane == ev.pane then panels[key] = nil end
    end
    remote.collect(cx)
end

return remote
