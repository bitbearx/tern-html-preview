-- 异步校验文件并管理内置浏览器；不安装文件路由或启动本地服务器。
local preview = {}
local resolving = {}
local opening = {}

-- 统一解析浏览器的异步错误和操作错误，不把失败当作预览成功。
local function browser_error(result, err)
    if err then return err end
    if result and result.error then return result.error.message end
    if not result or not result.ok then return "浏览器没有返回有效结果" end
    return nil
end

-- WebView 会把 %2B 等转回字面字符；按解码后的文件地址复用，忽略页内锚点。
local function file_address(url)
    if type(url) ~= "string" then return nil end
    local address = string.match(url, "^file://([^?#]*)")
    if not address then return nil end
    return (string.gsub(address, "%%(%x%x)", function(hex)
        return string.char(tonumber(hex, 16))
    end))
end

-- 复用窗口中相同 URL 的浏览器面板；关闭或导航离开的面板不会被误用。
local function show_existing(cx, url)
    local address = file_address(url)
    for _, pane in cx.session:panes() do
        if pane.kind == "browser" and file_address(pane.url) == address then
            if pane.parked then
                local ok, err = cx.layout:unpark(pane.pane)
                if not ok then
                    cx:toast("error", "无法显示 HTML 预览", err or "面板无法恢复")
                    return true
                end
            end
            cx.layout:focus(pane.pane)
            return true
        end
    end
    return false
end

-- 在原始目标右侧打开真实网页，完成后交还用户，恢复普通浏览器交互策略。
local function open_browser(cx, owner, url)
    if show_existing(cx, url) or opening[url] then return end
    if not cx.session:pane(owner) then
        cx:toast("info", "未打开 HTML 预览", "原始面板已关闭，请重新选择文件")
        return
    end
    opening[url] = true
    cx.browser:call({
        op = "open",
        owner = owner,
        url = url,
        how = "beside",
        profile = "html-preview",
    }):next(function(result, err, next_cx)
        opening[url] = nil
        if not next_cx then return end
        local failure = browser_error(result, err)
        if failure then
            next_cx:toast("error", "无法打开 HTML 预览", failure)
            return
        end
        next_cx.browser:call({ op = "release", block = result.ok.block }):next(function(released, release_err, final_cx)
            local release_failure = browser_error(released, release_err)
            if release_failure and final_cx then
                final_cx:toast("error", "无法恢复普通浏览器交互", release_failure)
            end
        end)
    end)
end

-- 点击后才检查本地普通文件，使用参数数组避免文件名进入 shell。
function preview.open(cx, path)
    if resolving[path] then return end
    local owner = cx.session:focused()
    if not owner then
        cx:toast("info", "无法打开 HTML 预览", "请先打开一个标签页")
        return
    end
    resolving[path] = true
    local ok, failure = pcall(tern.process.run, {
        "python3", tern.plugin.dir .. "/resolve_file.py", path,
    }, { timeout_ms = 5000 }, function(result, next_cx)
        resolving[path] = nil
        if not next_cx then return end
        if result.status ~= 0 then
            next_cx:toast("error", "无法预览所选文件", if result.timed_out then "文件检查超时" else result.stderr)
            return
        end
        local decoded, data = pcall(tern.json.decode, result.stdout)
        if not decoded or type(data) ~= "table" or type(data.url) ~= "string" then
            next_cx:toast("error", "无法预览所选文件", "路径检查程序没有返回有效 URL")
            return
        end
        open_browser(next_cx, owner, data.url)
    end)
    if not ok then
        resolving[path] = nil
        cx:toast("error", "无法检查 HTML 文件", "请确认 python3 可用：" .. tostring(failure))
    end
end

return preview
