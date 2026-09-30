from tools.browser import BrowserSession
from tools.registry import TOOLS
from uqa import classify_tool_action


session = BrowserSession()
try:
    session._ensure_started()
    session.page.set_content(
        """
        <button id="unnamed"></button>
        <img id="logo" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==">
        <div id="duplicate"></div><span id="duplicate"></span>
        <button aria-describedby="missing-description">Save</button>
        """
    )
    failed = session.inspect_accessibility_semantic()
    audit = failed["accessibility_audit"]
    assert failed.get("inspection_status") == "observed", failed
    assert audit["accessibility_passed"] is False, audit
    assert audit["unnamed_interactive_count"] == 1, audit
    assert audit["images_missing_alt_count"] == 1, audit
    assert audit["duplicate_id_count"] == 1, audit
    assert audit["broken_aria_reference_count"] == 1, audit

    session.page.set_content(
        """
        <label for="search">Search</label><input id="search">
        <button aria-label="Save"></button>
        <img alt="Product logo"
             src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==">
        <p id="save-help">Saves the form</p>
        <button aria-describedby="save-help">Submit</button>
        """
    )
    passed = session.inspect_accessibility_semantic()
    clean = passed["accessibility_audit"]
    assert clean["accessibility_passed"] is True, clean
    assert clean["issue_count"] == 0, clean

    assert classify_tool_action(
        "browser_inspect_accessibility_semantic", {}
    ) == "observe"
    assert any(
        item["function"]["name"]
        == "browser_inspect_accessibility_semantic"
        for item in TOOLS
    )
finally:
    session.close()

print("accessibility audit smoke: PASS")
