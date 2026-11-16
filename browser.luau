-- 统一管理本地文件与源码快照的浏览器面板，不处理文件读取。
local browser = {}
local opening = {}

-- 比较解码后的 file 地址，兼容 WebView 的 URL 规范化与页内锚点。
local function file_address(url)
    if type(url) ~= "string" then return nil end
    local address = string.match(url, "^file://([^?#]*)")
    if not address then return nil end
    return (string.gsub(address, "%%(%x%x)", function(hex)
        return string.char(tonumber(hex, 16))
    end))
end

-- 将同步异常和浏览器操作错误统一交给调用者，回调只使用新的窗口上下文。
local function call(cx, operation, done)
    local ok, failure = pcall(function()
        cx.browser:call(operation):next(function(result, err, fresh)
            if not fresh then return end
            local message = err or (result and result.error and result.error.message)
            if not message and (not result or not result.ok) then message = "浏览器没有返回有效结果" end
            done(result and result.ok, message, fresh)
        end)
    end)
    if not ok then done(nil, tostring(failure), cx) end
end

-- 自动化调用结束后交还普通浏览器交互；面板仍存在时保留它的身份。
local function release(cx, pane, done)
    call(cx, { op = "release", block = pane }, function(_, err, fresh)
        done(if fresh.session:pane(pane) then pane else nil, err, fresh)
    end)
end

-- 打开或复用同址面板；快照请求刷新，本地文件请求仅聚焦。
function browser.show(cx, owner, url, refresh, done)
    if opening[url] then
        table.insert(opening[url], done)
        return
    end
    local address = file_address(url)
    for _, pane in cx.session:panes() do
        if address and pane.kind == "browser" and file_address(pane.url) == address then
            if pane.parked then
                local ok, err = cx.layout:unpark(pane.pane)
                if not ok then done(nil, err or "面板无法恢复", cx) return end
            end
            cx.layout:focus(pane.pane)
            if refresh then
                call(cx, { op = "nav", block = pane.pane, go = "reload" }, function(_, err, fresh)
                    if err then done(pane.pane, err, fresh) return end
                    release(fresh, pane.pane, done)
                end)
            else
                done(pane.pane, nil, cx)
            end
            return
        end
    end
    if not cx.session:pane(owner) then
        done(nil, "原始面板已关闭，请重新选择文件", cx)
        return
    end
    opening[url] = { done }
    -- 同址并发请求共享一次创建，完成后通知每个请求释放自己的状态。
    local function finish(pane, err, fresh)
        local callbacks = opening[url]
        opening[url] = nil
        for _, callback in callbacks do callback(pane, err, fresh) end
    end
    call(cx, {
        op = "open", owner = owner, url = url, how = "beside", profile = "html-preview",
    }, function(data, err, fresh)
        if err then finish(nil, err, fresh) return end
        release(fresh, data.block, finish)
    end)
end

return browser
