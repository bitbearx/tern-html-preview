#!/usr/bin/env python3
"""原子写入私有 HTML 快照，并仅清理当前窗口不再引用的快照。"""

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from urllib.parse import unquote, urlsplit


UTF8_BOM = b"\xef\xbb\xbf"


def digest(value):
    """将窗口和来源标识转换成固定长度目录名，不暴露远端路径。"""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def window_root(base, owner):
    """每个窗口使用独立目录，防止清理其他窗口仍在显示的快照。"""
    return Path(base).resolve() / digest(owner)


def write_snapshot(base, owner, source_key, source):
    """以 UTF-8 BOM 固定浏览器编码，流式原子替换完整源码，不截断长行。"""
    root = window_root(base, owner)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    folder = root / digest(source_key)
    folder.mkdir(mode=0o700, exist_ok=True)
    target = folder / "index.html"
    fd, temporary = tempfile.mkstemp(prefix=".write-", dir=folder)
    try:
        with os.fdopen(fd, "wb") as output:
            first = source.read(3)
            output.write(UTF8_BOM)
            if first != UTF8_BOM:
                output.write(first)
            shutil.copyfileobj(source, output)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"url": target.as_uri(), "path": str(target)}


def prune_snapshots(base, owner, references):
    """保留活动浏览器及在途请求，仅删除本窗口自己的孤立快照目录。"""
    root = window_root(base, owner)
    if not root.exists():
        return {"removed": 0}
    keep = {root / digest(key) for key in references.get("pending", [])}
    for url in references.get("urls", []):
        parsed = urlsplit(url)
        if parsed.scheme != "file" or parsed.netloc not in {"", "localhost"}:
            continue
        path = Path(unquote(parsed.path))
        if path.name == "index.html" and path.parent.parent == root:
            keep.add(path.parent)
    removed = 0
    for child in root.iterdir():
        if child in keep:
            continue
        if child.is_symlink() or child.is_file():
            child.unlink()
        else:
            shutil.rmtree(child)
        removed += 1
    if not any(root.iterdir()):
        root.rmdir()
    return {"removed": removed}


def main():
    """命令参数只携带标识；HTML 从标准输入传入，避免进入 shell 或命令行。"""
    try:
        operation, base, owner, *args = sys.argv[1:]
        if operation == "write" and len(args) == 1:
            result = write_snapshot(base, owner, args[0], sys.stdin.buffer)
        elif operation == "prune" and not args:
            result = prune_snapshots(base, owner, json.load(sys.stdin))
        else:
            raise ValueError("无效的快照操作")
        print(json.dumps(result))
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
