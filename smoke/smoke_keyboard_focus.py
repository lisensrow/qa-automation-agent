from tools.browser import BrowserSession
from uqa import classify_tool_action, tool_policy_check


session = BrowserSession()

try:
    session._ensure_started()
    session.page.set_content(
        """
        <html><body>
          <button id="start">Start</button>
          <label for="name">Name</label>
          <input id="name">
          <label><input id="active" type="checkbox"> Active</label>
          <button
            id="save"
            onclick="this.dataset.activations =
              String(Number(this.dataset.activations || '0') + 1)"
          >Save</button>
        </body></html>
        """
    )

    focus = session.check_focus_order_semantic(
        ["Start", "Name", "Active", "Save"]
    )
    assert focus.get("focus_order_status") == "matched", focus
    assert focus.get("mutation_executed") is False, focus

    escaped = session.press_key_semantic("Escape", "Name", role="textbox")
    assert escaped.get("pressed_key") == "Escape", escaped
    assert escaped.get("focus_before", {}).get("name") == "Name", escaped

    entered = session.press_key_semantic("Enter", "Save", role="button")
    assert entered.get("pressed_key") == "Enter", entered
    assert session.page.locator("#save").get_attribute("data-activations") == "1"

    assert classify_tool_action(
        "browser_check_focus_order_semantic",
        {"targets": ["Start", "Name"]},
    ) == "interact"
    assert classify_tool_action(
        "browser_press_key_semantic",
        {"key": "Tab"},
    ) == "interact"
    assert classify_tool_action(
        "browser_press_key_semantic",
        {"key": "Enter", "target": "Save"},
    ) == "write"
    assert classify_tool_action(
        "browser_press_key_semantic",
        {"key": "Delete"},
    ) == "destructive"

    assert tool_policy_check(
        "browser_press_key_semantic",
        {"key": "Enter", "target": "Save"},
        [{"role": "user", "content": "Только проверь, ничего не меняй"}],
    ).get("status") == "blocked_by_policy"
    assert tool_policy_check(
        "browser_press_key_semantic",
        {"key": "Tab"},
        [{"role": "user", "content": "Только проверь, ничего не меняй"}],
    ) is None

    unsupported = session.press_key_semantic("Control+Alt+Delete")
    assert unsupported.get("error") == "unsupported_keyboard_key", unsupported
    assert unsupported.get("executed") is False, unsupported
finally:
    session.close()

print("keyboard and focus smoke: PASS")
