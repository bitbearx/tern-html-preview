#!/usr/bin/env python3
"""只读取路径元信息，为本地 HTML 文件生成规范的 file URL。"""

import json
from pathlib import Path
import sys


def resolve_file(value):
    """拒绝非 HTML 和非普通文件，保留相对资源的原始目录语义。"""
    path = Path(value)
    if not path.is_absolute() or path.suffix.lower() not in {".html", ".htm"}:
        raise ValueError("请选择一个本地 .html 或 .htm 文件")
    path = path.resolve(strict=True)
    if not path.is_file():
        raise ValueError("所选路径不是普通文件")
    return path.as_uri()


def main():
    """向插件输出 JSON；路径错误以非零状态和可读提示返回。"""
    try:
        if len(sys.argv) != 2:
            raise ValueError("需要一个 HTML 文件路径")
        print(json.dumps({"url": resolve_file(sys.argv[1])}))
    except (OSError, ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
