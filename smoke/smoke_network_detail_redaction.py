from tools.browser import BrowserSession
from uqa import classify_tool_action

class Request:
    method = "POST"
    resource_type = "fetch"
    post_data = '{"name":"agent","password":"hidden"}'
    def all_headers(self):
        return {"content-type": "application/json", "authorization": "secret"}

class Response:
    url = "https://example.test/api/agents?token=hidden"
    status = 200
    def all_headers(self):
        return {"content-type": "application/json", "set-cookie": "secret"}
    def text(self):
        return '{"status":"ok","token":"hidden"}'

s = BrowserSession()
try:
    s._ensure_started()
    s.network_details["n1"] = {"request": Request(), "response": Response()}
    r = s.get_network_detail("n1")
    assert "hidden" not in str(r), r
    assert "authorization" not in r["request_headers"], r
    assert "set-cookie" not in r["response_headers"], r
    assert "<redacted>" in r["request_body"] and "<redacted>" in r["response_body"], r
    assert classify_tool_action("browser_get_network_detail", {}) == "observe"
finally:
    s.close()
print("network detail redaction smoke: PASS")
