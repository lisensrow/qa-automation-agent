import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from tools.browser import BrowserSession
from tools.registry import TOOLS
from uqa import classify_tool_action


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"<html><head><title>Popup report</title></head><body>Ready report</body></html>"
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
        f'<a href="{origin}/reports/42" target="_blank">Open report</a>'
    )
    parent_url = session.page.url
    result = session.inspect_new_tab_semantic(
        "Open report", f"{origin}/reports/",
    )
    assert result["new_tab_status"] == "verified", result
    assert result["new_tab_url_matches"] is True, result
    assert result["new_tab_title"] == "Popup report", result
    assert "Ready report" in result["new_tab_text_preview"], result
    assert result["parent_context_restored"] is True, result
    assert session.page.url == parent_url, result
    assert len(session.context.pages) == 1, result

    blocked = session.inspect_new_tab_semantic(
        "Open report", "https://unexpected.example/reports/",
    )
    assert blocked["error"] == "new_tab_href_origin_mismatch", blocked
    assert classify_tool_action(
        "browser_inspect_new_tab_semantic", {}
    ) == "interact"
    assert any(
        item["function"]["name"] == "browser_inspect_new_tab_semantic"
        for item in TOOLS
    )
finally:
    session.close()
    server.shutdown()
    server.server_close()

print("new tab smoke: PASS")
