import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from tools.browser import BrowserSession
from tools.registry import TOOLS
from uqa import classify_tool_action


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"""
        <html><head><title>Keyboard surface</title></head><body>
          <canvas id="screen" tabindex="0" width="320" height="200"></canvas>
          <script>
            const canvas = document.getElementById('screen');
            const context = canvas.getContext('2d');
            context.fillStyle = 'rgb(255, 0, 0)';
            context.fillRect(0, 0, canvas.width, canvas.height);
            canvas.addEventListener('keydown', event => {
              if (event.key === 'Enter') {
                context.fillStyle = 'rgb(0, 128, 0)';
                context.fillRect(0, 0, canvas.width, canvas.height);
              }
            });
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
        f'<iframe title="Keyboard frame" src="{origin}/keyboard"></iframe>'
    )
    result = session.press_iframe_surface_key_semantic(
        "Keyboard frame", f"{origin}/keyboard", "Enter",
        0.5, 0.5, True, wait_ms=200,
    )
    assert result["iframe_key_status"] == "verified", result
    assert result["surface_changed"] is True, result
    blocked = session.press_iframe_surface_key_semantic(
        "Keyboard frame", f"{origin}/keyboard", "A",
        0.5, 0.5, False,
    )
    assert blocked["error"] == "unsupported_iframe_keyboard_key", blocked
    assert classify_tool_action(
        "browser_press_iframe_surface_key_semantic", {}
    ) == "write"
    assert any(
        item["function"]["name"] == "browser_press_iframe_surface_key_semantic"
        for item in TOOLS
    )
finally:
    session.close()
    server.shutdown()
    server.server_close()

print("iframe surface key smoke: PASS")
