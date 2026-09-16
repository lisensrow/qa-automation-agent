from tools.browser import BrowserSession
from tools.registry import TOOLS
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
          <div role="listbox" aria-label="Mode">
            <div role="option" aria-selected="false" onclick="this.setAttribute('aria-selected', 'true')">Dark</div>
            <div role="option" aria-selected="false" aria-disabled="true">Disabled mode</div>
            <div role="option">Unsupported mode</div>
          </div>
          <button onclick="window.applyClicks += 1">Apply</button>
          <button disabled>Disabled action</button>
          <button>Duplicate</button><button>Duplicate</button>
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
    dark_before = next(
        control for control in observed["popover_snapshot"]["controls"]
        if control["name"] == "Dark"
    )
    assert dark_before["selected"] is False, observed
    chosen = session.select_popover_option_semantic("Settings", "Dark")
    assert chosen.get("popover_option_status") == "selected", chosen
    dark_after = next(
        control for control in chosen["popover_after"]["controls"]
        if control["name"] == "Dark"
    )
    assert dark_after["selected"] is True, chosen
    chosen_again = session.select_popover_option_semantic("Settings", "Dark")
    assert chosen_again.get("popover_option_status") == "already_selected", chosen_again
    disabled = session.select_popover_option_semantic("Settings", "Disabled mode")
    assert disabled.get("error") == "popover_option_disabled", disabled
    unsupported = session.select_popover_option_semantic("Settings", "Unsupported mode")
    assert unsupported.get("error") == "popover_option_selection_contract_missing", unsupported
    absent = session.select_popover_option_semantic("Settings", "Missing")
    assert absent.get("error") == "popover_option_not_unique", absent
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
    assert classify_tool_action(
        "browser_select_popover_option_semantic", {"option": "Dark"}
    ) == "write"
    assert classify_tool_action(
        "browser_select_popover_option_semantic", {"option": "Delete record"}
    ) == "destructive"
    assert session.click_popover_button_semantic(
        "Settings", "Apply"
    ).get("error") == "popover_not_open"
    session.open_popover_semantic("Settings")
    assert session.click_popover_button_semantic(
        "Settings", "Missing"
    ).get("error") == "popover_button_not_unique"
    assert session.click_popover_button_semantic(
        "Settings", "Duplicate"
    ).get("error") == "popover_button_not_unique"
    assert session.click_popover_button_semantic(
        "Settings", "Disabled action"
    ).get("error") == "popover_button_disabled"
    applied = session.click_popover_button_semantic("Settings", "Apply")
    assert applied.get("popover_button_status") == "clicked", applied
    assert applied.get("popover_open_after") is True, applied
    assert session.page.evaluate("window.applyClicks") == 1
    assert classify_tool_action(
        "browser_click_popover_button_semantic", {"button": "Apply"}
    ) == "write"
    assert classify_tool_action(
        "browser_click_popover_button_semantic", {"button": "Delete record"}
    ) == "destructive"
    assert classify_tool_action(
        "browser_click_popover_button_semantic", {"button": "Details"}
    ) == "write"
    assert any(
        item["function"]["name"] == "browser_click_popover_button_semantic"
        for item in TOOLS
    )
finally:
    session.close()

print("popover lifecycle smoke: PASS")
