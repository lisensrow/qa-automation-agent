import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from tools.browser import BrowserSession
from tools.registry import TOOLS
from uqa import classify_tool_action


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        title = "First page" if self.path.startswith("/first") else "Second page"
        body = f"<html><head><title>{title}</title></head><body>{title}</body></html>".encode()
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
    session.page.goto(f"{origin}/first", wait_until="domcontentloaded")
    session.page.goto(f"{origin}/second", wait_until="domcontentloaded")

    back = session.navigate_history_semantic("back", f"{origin}/first")
    assert back["history_status"] == "verified", back
    assert back["history_url_matches"] is True, back
    assert back["title"] == "First page", back

    forward = session.navigate_history_semantic("forward", f"{origin}/second")
    assert forward["history_status"] == "verified", forward
    assert forward["title"] == "Second page", forward

    blocked = session.navigate_history_semantic(
        "back", "https://unexpected.example/first",
    )
    assert blocked["error"] == "history_cross_origin_blocked", blocked
    assert classify_tool_action(
        "browser_navigate_history_semantic", {}
    ) == "interact"
    assert any(
        item["function"]["name"] == "browser_navigate_history_semantic"
        for item in TOOLS
    )
finally:
    session.close()
    server.shutdown()
    server.server_close()

print("history navigation smoke: PASS")
