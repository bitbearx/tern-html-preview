-- 本地文件仍直接加载原文件，不创建快照或改变原有刷新行为。
local browser = require("./browser")
local preview = {}
local resolving = {}

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
        browser.show(next_cx, owner, data.url, false, function(_, err, fresh)
            if err then fresh:toast("error", "无法打开 HTML 预览", err) end
        end)
    end)
    if not ok then
        resolving[path] = nil
        cx:toast("error", "无法检查 HTML 文件", "请确认 python3 可用：" .. tostring(failure))
    end
end

return preview
