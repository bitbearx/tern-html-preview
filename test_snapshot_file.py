#!/usr/bin/env python3
"""覆盖完整源码保存、窗口隔离和关闭后的引用回收。"""

import io
import json
from pathlib import Path
import tempfile
import unittest

from snapshot_file import prune_snapshots, write_snapshot


class SnapshotFileTest(unittest.TestCase):
    """使用真实临时文件验证快照，不依赖用户数据。"""

    def test_complete_source_and_utf8_encoding(self):
        """超长内联脚本和多行源码完整保留，旧 charset 不影响 UTF-8 快照。"""
        with tempfile.TemporaryDirectory() as directory:
            text = '<meta charset="gbk"><h1>中文快照</h1><script>const x="' + "a" * 2_000_000 + '";</script>' + "\n<!-- line -->" * 2501
            result = write_snapshot(directory, "window", "source", io.BytesIO(text.encode("utf-8")))
            path = Path(result["path"])
            self.assertEqual(path.read_text(encoding="utf-8-sig"), text)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
            changed = "<h1>再次预览</h1>"
            refreshed = write_snapshot(directory, "window", "source", io.BytesIO(changed.encode("utf-8")))
            self.assertEqual(refreshed["url"], result["url"])
            self.assertEqual(path.read_text(encoding="utf-8-sig"), changed)

    def test_same_path_on_different_hosts_and_windows_is_isolated(self):
        """同名远程文件和不同窗口不能覆盖彼此的页面或被一起清理。"""
        with tempfile.TemporaryDirectory() as directory:
            first_key = json.dumps({"host": "one", "path": "/report.html"})
            second_key = json.dumps({"host": "two", "path": "/report.html"})
            first = write_snapshot(directory, "window-a", first_key, io.BytesIO(b"FIRST"))
            second = write_snapshot(directory, "window-a", second_key, io.BytesIO(b"SECOND"))
            other = write_snapshot(directory, "window-b", first_key, io.BytesIO(b"OTHER"))
            prune_snapshots(directory, "window-a", {"urls": [second["url"]], "pending": []})
            self.assertFalse(Path(first["path"]).exists())
            self.assertEqual(Path(second["path"]).read_text(encoding="utf-8-sig"), "SECOND")
            self.assertEqual(Path(other["path"]).read_text(encoding="utf-8-sig"), "OTHER")

    def test_live_and_pending_references_survive_until_closed(self):
        """导航锚点和在途请求保护快照；全部引用释放后才删除。"""
        with tempfile.TemporaryDirectory() as directory:
            live = write_snapshot(directory, "window", "live", io.BytesIO(b"LIVE"))
            pending = write_snapshot(directory, "window", "pending", io.BytesIO(b"PENDING"))
            prune_snapshots(directory, "window", {"urls": [live["url"] + "#section"], "pending": ["pending"]})
            self.assertEqual(Path(live["path"]).read_text(encoding="utf-8-sig"), "LIVE")
            self.assertEqual(Path(pending["path"]).read_text(encoding="utf-8-sig"), "PENDING")
            prune_snapshots(directory, "window", {"urls": [], "pending": []})
            self.assertFalse(Path(live["path"]).exists())
            self.assertFalse(Path(pending["path"]).exists())


if __name__ == "__main__":
    unittest.main()
