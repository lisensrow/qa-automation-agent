from tools.browser import BrowserSession
from uqa import classify_tool_action

s = BrowserSession()
s._private_clipboard_text = "temporary value"
s._private_clipboard_source = {"name": "field"}
r = s.clear_private_clipboard()
assert r["status"] == "private_clipboard_cleared" and r["had_value"] is True, r
assert s._private_clipboard_text is None and s._private_clipboard_source is None
assert r["mutation_executed"] is False
assert classify_tool_action("browser_clear_private_clipboard", {}) == "interact"
print("private clipboard clear smoke: PASS")
