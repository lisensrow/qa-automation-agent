from tools.browser import BrowserSession
from uqa import classify_tool_action


session = BrowserSession()
try:
    session._ensure_started()
    session.page.set_content(
        """
        <button aria-label="Settings" aria-controls="settings-popup"
                onclick="document.getElementById('settings-popup').hidden = false">Settings</button>
        <div id="settings-popup" role="dialog" aria-label="Settings panel" hidden>
          <label>Theme<input value="light"></label>
          <button onclick="window.applyClicks += 1">Apply</button>
        </div>
        <button aria-label="Unlinked">Unlinked</button>
        <script>
          window.applyClicks = 0;
          document.addEventListener('keydown', event => {
            if (event.key === 'Escape') {
              document.getElementById('settings-popup').hidden = true;
            }
          });
        </script>
        """
    )
    missing = session.open_popover_semantic("Unlinked")
    assert missing.get("error") == "popover_missing_aria_controls", missing
    closed = session.inspect_popover_semantic("Settings")
    assert closed.get("error") == "popover_not_open", closed
    opened = session.open_popover_semantic("Settings")
    assert opened.get("popover_status") == "opened", opened
    assert opened["popover_snapshot"]["name"] == "Settings panel", opened
    assert any(
        control["name"] == "Apply"
        for control in opened["popover_snapshot"]["controls"]
    ), opened
    again = session.open_popover_semantic("Settings")
    assert again.get("popover_status") == "already_open", again
    observed = session.inspect_popover_semantic("Settings")
    assert observed.get("popover_status") == "observed", observed
    dismissed = session.close_popover_semantic("Settings")
    assert dismissed.get("popover_status") == "closed", dismissed
    dismissed_again = session.close_popover_semantic("Settings")
    assert dismissed_again.get("popover_status") == "already_closed", dismissed_again
    assert session.page.evaluate("window.applyClicks") == 0
    assert classify_tool_action("browser_inspect_popover_semantic", {}) == "observe"
    assert classify_tool_action(
        "browser_open_popover_semantic", {"trigger": "Settings"}
    ) == "interact"
    assert classify_tool_action(
        "browser_open_popover_semantic", {"trigger": "Delete item"}
    ) == "destructive"
    assert classify_tool_action(
        "browser_open_popover_semantic", {"trigger": "Apply filter"}
    ) == "write"
    assert classify_tool_action("browser_close_popover_semantic", {}) == "interact"
finally:
    session.close()

print("popover lifecycle smoke: PASS")
