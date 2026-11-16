#!/usr/bin/env python3
"""在隔离的真实 Tern 窗口验证手动预览、资源加载和面板复用。"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest


TERN = shutil.which("tern")
PLUGIN = Path(__file__).resolve().parent
BUTTON = '[data-plugin="html-preview"][data-id="preview"]'
COMMAND = "HTML Preview: 预览当前 HTML"


@unittest.skipUnless(TERN and os.environ.get("HTML_PREVIEW_UI_TEST") == "1", "需要 Tern 和 HTML_PREVIEW_UI_TEST=1；会打开隔离窗口")
class PreviewTest(unittest.TestCase):
    """只操作测试自己的配置、文件、窗口和守护进程。"""

    @classmethod
    def setUpClass(cls):
        """创建包含 URL 保留字符的页面，隔离工具安装器可写的 PATH。"""
        cls.temp = tempfile.TemporaryDirectory(prefix="tern-html-preview-test-", dir="/tmp")
        cls.root = Path(cls.temp.name)
        cls.window = None
        cls.log = None
        cls.addClassCleanup(cls.cleanup)
        cls.workspace = cls.root / "workspace"
        for name in ["home/.omp/agent", "bin", "config/plugins", "workspace", "empty"]:
            (cls.root / name).mkdir(parents=True)
        (cls.root / "bin/tern").symlink_to(TERN)
        (cls.root / "bin/python3").symlink_to(sys.executable)
        omp = shutil.which("omp")
        if omp:
            (cls.root / "bin/omp").symlink_to(omp)
        (cls.root / "config/plugins/html-preview").symlink_to(PLUGIN, target_is_directory=True)
        (cls.root / "config/settings.json").write_text(json.dumps({"widgets": [], "pane_headers": "Split"}), encoding="utf-8")
        cls.page = cls.workspace / "报告 #50%?+.HTML"
        cls.page.write_text(
            '<!doctype html><html><head><meta charset="utf-8"><title>HTML Preview verification</title>'
            '<link rel="stylesheet" href="style.css"></head><body><h1>本地 HTML 预览</h1>'
            '<p id="status">NOT_RUN</p><button onclick="document.getElementById(\'status\').textContent=\'CLICK_OK\'">验证交互</button>'
            '<script src="app.js"></script></body></html>', encoding="utf-8",
        )
        (cls.workspace / "style.css").write_text("body{font-family:sans-serif;padding:24px}h1{color:rgb(12,100,150)}", encoding="utf-8")
        (cls.workspace / "app.js").write_text('document.getElementById("status").textContent="RELATIVE_JS_OK";', encoding="utf-8")
        (cls.workspace / "plain.txt").write_text("plain text", encoding="utf-8")
        (cls.workspace / "alias.htm").symlink_to(cls.page)
        (cls.workspace / "folder.html").mkdir()
        cls.env = os.environ.copy()
        for key in ["OMP_PROFILE", "TERN_PANE", "TERN_WINDOW_KEY"]:
            cls.env.pop(key, None)
        cls.env.update({
            "HOME": str(cls.root / "home"), "PI_CODING_AGENT_DIR": str(cls.root / "home/.omp/agent"),
            "TERN_CONFIG_DIR": str(cls.root / "config"), "TERN_DAEMON_SOCKET": str(cls.root / "daemon.sock"),
            "STENCIL_LOG_DIR": str(cls.root / "logs"), "PATH": str(cls.root / "bin") + ":/usr/bin:/bin:/usr/sbin:/sbin",
        })
        if omp:
            cls.env["OMP_EXE"] = omp
        cls.log = (cls.root / "window.log").open("w", encoding="utf-8")
        cls.window = subprocess.Popen([TERN, "--control", str(cls.root / "control.sock"), str(cls.workspace)], cwd=cls.workspace, env=cls.env, stdout=cls.log, stderr=cls.log)
        deadline = time.monotonic() + 30
        while not (cls.root / "control.sock").exists():
            if cls.window.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError("隔离窗口启动失败：" + (cls.root / "window.log").read_text())
            time.sleep(0.1)
        cls.ctl("ready")
        cls.ctl("account", "signed-out")
        cls.ctl("key", "Escape")
        cls.ctl("files", "root", json.dumps(str(cls.root / "empty")))
        cls.ctl("files", "wait")

    @classmethod
    def cleanup(cls):
        """关闭测试窗口及其独立守护进程，不触碰用户会话。"""
        if cls.window and cls.window.poll() is None:
            try:
                cls.ctl("quit")
                cls.window.wait(timeout=10)
            except (OSError, subprocess.SubprocessError, RuntimeError):
                cls.window.terminate()
                cls.window.wait(timeout=10)
        if hasattr(cls, "env"):
            subprocess.run([TERN, "daemon", "stop", "--socket", str(cls.root / "daemon.sock")], env=cls.env, capture_output=True, timeout=15)
        if cls.log:
            cls.log.close()
        cls.temp.cleanup()

    @classmethod
    def ctl(cls, *args):
        """执行原生控制命令，保留失败的实际输出。"""
        result = subprocess.run([TERN, "ctl", "--control", str(cls.root / "control.sock"), *args], cwd=cls.workspace, env=cls.env, capture_output=True, text=True, timeout=25)
        if result.returncode:
            raise RuntimeError(result.stderr or result.stdout)
        return json.loads(result.stdout)

    @staticmethod
    def nodes(value):
        """遍历实际可见 UI 树，用于定位文件行和读取用户提示。"""
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from PreviewTest.nodes(child)
        elif isinstance(value, list):
            for child in value:
                yield from PreviewTest.nodes(child)

    def texts(self):
        """读取可见控件文字，不从插件内部变量构造预期结果。"""
        return [node["text"] for node in self.nodes(self.ctl("tree")) if node.get("text")]

    def click_preview(self):
        """先悬浮 Files 工具栏，再点击宿主真实按钮。"""
        self.ctl("hover", ".ft-tools")
        self.ctl("click", json.dumps(BUTTON))

    def until(self, predicate):
        """等待异步文件检查或 WebView 加载，超时保留最后一次错误。"""
        deadline = time.monotonic() + 15
        error = None
        while time.monotonic() < deadline:
            try:
                value = predicate()
                if value:
                    return value
            except RuntimeError as current:
                error = current
            time.sleep(0.1)
        self.fail(f"等待真实界面结果超时：{error}")

    def webcall(self, operation):
        """控制命令直接接收 JSON，不能套用 scenario 的二次引号。"""
        return self.ctl("webcall", ".kit-web-page", json.dumps(operation))

    def test_manual_preview_and_normalized_url_reuse(self):
        """验证显式触发、真实资源与交互，以及 WebKit 规范化 URL 后仍复用面板。"""
        self.click_preview()
        self.until(lambda: "请选择 HTML 文件" in self.texts())
        self.assertEqual(self.ctl("stats").get("webviews", []), [])
        self.ctl("files", "root", json.dumps(str(self.workspace)))
        self.ctl("files", "wait")
        self.ctl("files", "select", "plain.txt")
        self.click_preview()
        self.assertEqual(self.ctl("stats").get("webviews", []), [])
        self.ctl("files", "select", "folder.html")
        self.click_preview()
        self.until(lambda: any("不是普通文件" in text for text in self.texts()))
        self.assertEqual(self.ctl("stats").get("webviews", []), [])
        row = next(node for node in self.nodes(self.ctl("tree")) if node.get("text") == self.page.stem)
        x, y, width, height = row["rect"]
        self.ctl("click", str(x + width / 2), str(y + height / 2))
        self.assertEqual(self.ctl("stats").get("webviews", []), [])
        # 普通单击使用 Tern 自带的临时源码预览，不一定创建持久文件面板。
        self.ctl("key", "Escape")
        self.click_preview()
        loaded = self.until(lambda: self.webcall({"op": "eval", "function": "() => document.querySelector('#status')?.textContent === 'RELATIVE_JS_OK'"}).get("value"))
        self.assertTrue(loaded)
        self.assertEqual(self.webcall({"op": "eval", "function": "() => getComputedStyle(document.querySelector('h1')).color"})["value"], "rgb(12, 100, 150)")
        point = self.webcall({"op": "eval", "function": "() => {const r=document.querySelector('button').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};}"})["value"]
        self.webcall({"op": "input", "events": [{"type": "mouse", "action": "down", **point}, {"type": "mouse", "action": "up", **point}]})
        self.assertEqual(self.webcall({"op": "eval", "function": "() => document.querySelector('#status').textContent"})["value"], "CLICK_OK")
        self.ctl("files", "select", "alias.htm")
        self.click_preview()
        # 等待路径检查结束后验证没有新增面板，交互状态也没有被重新加载。
        self.ctl("wait", "800")
        self.assertEqual(len(self.ctl("stats")["webviews"]), 1)
        self.assertEqual(self.webcall({"op": "eval", "function": "() => document.querySelector('#status').textContent"})["value"], "CLICK_OK")
        self.ctl("close")
        self.until(lambda: not self.ctl("stats").get("webviews"))
        # Scenario 只支持有限转义，中文路径不能转换为 JSON 的 \\uXXXX。
        self.ctl("file", "open", json.dumps(str(self.page), ensure_ascii=False), "1")
        blocks = self.ctl("state")["file_blocks"]
        self.assertTrue(any(Path(block["path"]).resolve() == self.page.resolve() for block in blocks))
        self.ctl("palette", "HTML Preview")
        self.assertIn(COMMAND, "".join(self.texts()))
        self.ctl("key", "Enter")
        self.until(lambda: self.webcall({"op": "eval", "function": "() => document.querySelector('#status')?.textContent === 'RELATIVE_JS_OK'"}).get("value"))
        self.assertEqual(len(self.ctl("stats")["webviews"]), 1)
        self.assertEqual(self.webcall({"op": "eval", "function": "() => document.querySelector('#status').textContent"})["value"], "RELATIVE_JS_OK")
        self.ctl("file", "open", json.dumps(str(self.workspace / "plain.txt")))
        self.ctl("palette", "HTML Preview")
        self.assertNotIn(COMMAND, "".join(self.texts()))
        self.ctl("key", "Escape")
        type(self).capture = self.webcall({"op": "capture"})


if __name__ == "__main__":
    unittest.main()
