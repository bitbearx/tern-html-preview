-- 串行处理快照写入与回收，避免关闭事件与异步写入互相删除文件。
local snapshots = {}
local jobs = {}
local running = false
local collecting = false
local drain

-- 每次使用前一个异步回调的新上下文取出任务，不保留任何过期 cx。
drain = function(cx)
    if running or #jobs == 0 then return end
    running = true
    local job = table.remove(jobs, 1)
    local input = if type(job.input) == "function" then job.input(cx) else job.input
    local argv = { "python3", tern.plugin.dir .. "/snapshot_file.py", job.operation,
        tern.plugin.data .. "/snapshots", cx:window_key() }
    if job.key then table.insert(argv, job.key) end
    -- 先安排后续任务，再通知调用者；调用者异常不会让整个队列永久卡住。
    local function finish(data, err, fresh)
        running = false
        if #jobs > 0 then tern.timer(0, drain) end
        job.done(data, err, fresh)
    end
    local ok, failure = pcall(tern.process.run, argv, { stdin = input, timeout_ms = 10000 }, function(result, fresh)
        if not fresh then return end
        if result.status ~= 0 then
            finish(nil, if result.timed_out then "快照文件操作超时" else result.stderr, fresh)
            return
        end
        local decoded, data = pcall(tern.json.decode, result.stdout)
        if not decoded or type(data) ~= "table" then
            finish(nil, "快照程序没有返回有效结果", fresh)
            return
        end
        finish(data, nil, fresh)
    end)
    if not ok then finish(nil, tostring(failure), cx) end
end

-- HTML 通过 stdin 原样交给写入器，来源键同时隔离主机与路径。
function snapshots.save(cx, key, text, done)
    table.insert(jobs, { operation = "write", key = key, input = text, done = done })
    drain(cx)
end

-- 回收执行时才读取活动引用；队列等待期间新增的面板不会被误删。
function snapshots.collect(cx, references)
    if collecting or not tern.fs.exists(tern.plugin.data .. "/snapshots") then return end
    collecting = true
    table.insert(jobs, {
        operation = "prune",
        input = function(fresh)
            collecting = false
            return tern.json.encode(references(fresh))
        end,
        done = function(_, err, fresh)
            if err then fresh:toast("error", "无法清理 HTML 快照", err) end
        end,
    })
    drain(cx)
end

return snapshots
