from tools.browser import BrowserSession
from uqa import classify_tool_action


session = BrowserSession()
try:
    session._ensure_started()
    session.page.set_content("""
      <button onclick="window.answer = confirm('Apply change?')">Apply</button>
      <button onclick="window.answer = confirm('Delete item?')">Delete</button>
    """)
    dismissed = session.handle_native_dialog_semantic(
        "Apply", "confirm", "Apply change?", "dismiss",
    )
    assert dismissed["native_dialog_status"] == "verified", dismissed
    assert session.page.evaluate("window.answer") is False
    accepted = session.handle_native_dialog_semantic(
        "Apply", "confirm", "Apply change?", "accept",
    )
    assert accepted["native_dialog_status"] == "verified", accepted
    assert session.page.evaluate("window.answer") is True
    mismatch = session.handle_native_dialog_semantic(
        "Delete", "confirm", "Wrong text", "accept",
    )
    assert mismatch["native_dialog_status"] == "mismatch", mismatch
    assert mismatch["native_dialog_observed"][0]["fail_closed"] is True
    assert session.page.evaluate("window.answer") is False
    assert classify_tool_action("browser_handle_native_dialog_semantic", {"target": "Apply", "decision": "accept"}) == "write"
    assert classify_tool_action("browser_handle_native_dialog_semantic", {"target": "Delete", "decision": "accept"}) == "destructive"
finally:
    session.close()

print("native dialog smoke: PASS")
