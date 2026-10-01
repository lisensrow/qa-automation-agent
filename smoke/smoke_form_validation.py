from tools.browser import BrowserSession
from uqa import classify_tool_action


session = BrowserSession()
try:
    session._ensure_started()
    session.page.set_content("""
      <form aria-label="Profile">
        <label>Email <input name="email" type="email" required></label>
        <label>Age <input name="age" type="number" min="18" value="10"></label>
      </form>
    """)
    invalid = session.inspect_form_validation_semantic("Profile")
    audit = invalid["validation_audit"]
    assert audit["validation_passed"] is False, invalid
    assert audit["invalid_control_count"] == 2, invalid
    assert all("value" not in item for item in audit["invalid_controls"]), invalid
    session.page.locator("[name=email]").fill("qa@example.test")
    session.page.locator("[name=age]").fill("20")
    valid = session.inspect_form_validation_semantic("Profile")
    assert valid["validation_audit"]["validation_passed"] is True, valid
    assert classify_tool_action("browser_inspect_form_validation_semantic", {}) == "observe"
finally:
    session.close()

print("form validation smoke: PASS")
