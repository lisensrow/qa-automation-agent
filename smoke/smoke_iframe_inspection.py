import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from tools.browser import BrowserSession
from tools.registry import TOOLS
from uqa import classify_tool_action


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = (
            b"<html><head><title>Embedded report</title></head>"
            b"<body>Report ready <button>Refresh</button></body></html>"
        )
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
        f'<iframe title="Report frame" src="{origin}/embedded"></iframe>'
    )
    result = session.inspect_iframe_semantic(
        "Report frame", f"{origin}/embedded",
    )
    assert result["iframe_status"] == "verified", result
    assert result["iframe_origin_matches"] is True, result
    assert result["iframe_title"] == "Embedded report", result
    assert "Report ready" in result["iframe_text_preview"], result
    assert result["iframe_interactive_count"] == 1, result
    assert len(session.context.pages) == 1, result

    mismatch = session.inspect_iframe_semantic(
        "Report frame", "https://unexpected.example/embedded",
    )
    assert mismatch["error"] == "iframe_url_mismatch", mismatch
    assert classify_tool_action(
        "browser_inspect_iframe_semantic", {}
    ) == "observe"
    assert any(
        item["function"]["name"] == "browser_inspect_iframe_semantic"
        for item in TOOLS
    )
finally:
    session.close()
    server.shutdown()
    server.server_close()

print("iframe inspection smoke: PASS")
