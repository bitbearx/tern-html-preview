#!/usr/bin/env python3
"""验证影响真实文件加载的 URL 编码、符号链接和非法文件边界。"""

import os
from pathlib import Path
import tempfile
import unittest
from urllib.parse import unquote, urlsplit

from resolve_file import resolve_file


class ResolveFileTest(unittest.TestCase):
    """使用真实临时文件，不依赖用户目录或浏览器。"""

    def test_special_characters_and_case(self):
        """中文、空格和 URL 保留字符不能被误解释为查询或锚点。"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "报告 #50%?+.HTML"
            path.write_text("<!doctype html><h1>预览</h1>", encoding="utf-8")
            parts = urlsplit(resolve_file(str(path)))
            self.assertEqual(parts.scheme, "file")
            self.assertEqual(parts.query, "")
            self.assertEqual(parts.fragment, "")
            self.assertEqual(Path(unquote(parts.path)), path.resolve())

    def test_aliases_share_the_same_url(self):
        """符号链接与真实文件应复用一个预览，资源基址使用真实目录。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "index.htm"
            target.write_text("<h1>页面</h1>", encoding="utf-8")
            alias = root / "alias.html"
            alias.symlink_to(target)
            self.assertEqual(resolve_file(str(alias)), resolve_file(str(target)))

    def test_invalid_targets_are_rejected(self):
        """不存在的路径、目录、非 HTML 和 FIFO 均不能启动预览。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "folder.html"
            folder.mkdir()
            text = root / "notes.txt"
            text.write_text("text", encoding="utf-8")
            targets = [root / "missing.html", folder, text, Path("relative.html")]
            if hasattr(os, "mkfifo"):
                fifo = root / "pipe.html"
                os.mkfifo(fifo)
                targets.append(fifo)
            for path in targets:
                with self.subTest(path=path), self.assertRaises((OSError, ValueError)):
                    resolve_file(str(path))


if __name__ == "__main__":
    unittest.main()
