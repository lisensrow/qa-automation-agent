import threading
from pathlib import Path
from unittest.mock import patch
from playwright.sync_api import Locator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from tools.browser import BrowserSession
from tools.registry import TOOLS
from uqa import classify_tool_action


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"""
        <html><head><title>Live surface</title></head><body>
          <canvas id="screen" width="320" height="200"></canvas>
          <script>
            const canvas = document.getElementById('screen');
            const context = canvas.getContext('2d');
            context.fillStyle = 'rgb(255, 0, 0)';
            context.fillRect(0, 0, canvas.width, canvas.height);
            window.changeFrame = () => setTimeout(() => {
              context.fillStyle = 'rgb(0, 0, 255)';
              context.fillRect(0, 0, canvas.width, canvas.height);
            }, 200);
          </script>
        </body></html>
        """
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
origin = f"http://127.0.0.1:{server.server_port}"

session = BrowserSession()
try:
    session._ensure_started()
    session.page.set_content(
        f'<iframe title="Live frame" src="{origin}/live"></iframe>'
    )
    iframe = session.page.locator("iframe").element_handle().content_frame()
    # Fixture synchronization only: arm the 200ms paint AFTER the real baseline
    # screenshot. Starting it before inspection races slower screenshot capture.
    # Native screenshots/hashes, expected change and stable checks are unchanged.
    original_capture = Locator.screenshot
    armed = []
    def capture_then_arm(locator, *args, **kwargs):
        result = original_capture(locator, *args, **kwargs)
        if Path(str(kwargs.get("path", ""))).name.startswith("iframe-before-"):
            armed.append(True)
            iframe.evaluate("window.changeFrame()")
        return result
    with patch.object(Locator, "screenshot", capture_then_arm):
        changed = session.observe_iframe_surface_change_semantic(
            "Live frame", f"{origin}/live", True, wait_ms=600,
        )
    assert armed == [True], "fixture must arm only after baseline capture"
    assert changed["surface_change_status"] == "verified", changed
    assert changed["surface_changed"] is True, changed
    assert changed["surface_before_sha256"] != changed["surface_after_sha256"], changed

    stable = session.observe_iframe_surface_change_semantic(
        "Live frame", f"{origin}/live", False, wait_ms=200,
    )
    assert stable["surface_change_status"] == "verified", stable
    assert stable["surface_changed"] is False, stable
    assert classify_tool_action(
        "browser_observe_iframe_surface_change_semantic", {}
    ) == "observe"
    assert any(
        item["function"]["name"]
        == "browser_observe_iframe_surface_change_semantic"
        for item in TOOLS
    )
finally:
    session.close()
    server.shutdown()
    server.server_close()

print("iframe surface change smoke: PASS")
