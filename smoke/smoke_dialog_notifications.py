from tools.browser import BrowserSession
from tools.registry import TOOLS
from uqa import classify_tool_action


session = BrowserSession()
try:
    session._ensure_started()
    session.page.set_content(
        """
        <main>
          <div role="dialog" aria-label="Delete confirmation">
            <h2>Delete record?</h2>
            <button>Cancel</button>
            <button>Delete</button>
          </div>
          <div role="alert">Saved successfully</div>
          <div role="status" aria-label="Sync status">Complete</div>
          <div role="alertdialog" aria-label="Session warning">
            Session expires soon
          </div>
        </main>
        """
    )

    dialog = session.inspect_semantic(
        "Delete confirmation", role="dialog"
    )
    assert dialog.get("inspection_status") == "observed", dialog
    assert dialog.get("visible") is True, dialog
    assert dialog.get("semantic_strategy") == "role:dialog", dialog

    alert = session.inspect_semantic(
        "Saved successfully", role="alert"
    )
    assert alert.get("inspection_status") == "observed", alert
    assert alert.get("semantic_strategy") in {
        "role:alert",
        "explicit_role_text:alert",
    }, alert
    assert alert.get("role_constraint_matched") is True, alert

    status = session.inspect_semantic("Sync status", role="status")
    assert status.get("inspection_status") == "observed", status
    assert status.get("semantic_strategy") == "role:status", status

    alert_dialog = session.inspect_semantic(
        "Session warning", role="alertdialog"
    )
    assert alert_dialog.get("inspection_status") == "observed", alert_dialog
    assert alert_dialog.get("semantic_strategy") == "role:alertdialog", (
        alert_dialog
    )

    absent = session.inspect_semantic("Missing toast", role="alert")
    assert absent.get("error") == "semantic_element_not_found", absent

    assert classify_tool_action(
        "browser_inspect_semantic",
        {"name": "Saved successfully", "role": "alert"},
    ) == "observe"
    inspect_tool = next(
        item["function"]
        for item in TOOLS
        if item["function"]["name"] == "browser_inspect_semantic"
    )
    role_enum = inspect_tool["parameters"]["properties"]["role"]["enum"]
    assert {"dialog", "alertdialog", "alert", "status"} <= set(role_enum)
finally:
    session.close()

print("dialog and notification roles smoke: PASS")
