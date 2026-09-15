from tools.browser import BrowserSession
from uqa import (
    _COMPLETED_REQUIRED_SELECTIONS,
    _selection_key,
    classify_tool_action,
    record_required_selection_result,
    tool_policy_check,
)


session = BrowserSession()

try:
    session._ensure_started()
    session.page.set_content(
        """
        <html><body>
          <label for="priority">Priority</label>
          <select id="priority" name="priority">
            <option value="low">Low</option>
            <option value="high">High</option>
          </select>
          <label><input id="active" type="checkbox"> Active</label>
          <button
            id="severity"
            role="combobox"
            aria-label="Severity"
            aria-expanded="false"
            onclick="
              document.getElementById('severity-options').hidden = false;
              this.setAttribute('aria-expanded', 'true');
            "
          >Choose severity</button>
          <div id="severity-options" role="listbox" hidden>
            <button
              role="option"
              onclick="
                document.getElementById('severity')
                  .setAttribute('aria-valuetext', 'Critical');
                document.getElementById('severity-options').hidden = true;
              "
            >Critical</button>
          </div>
          <button
            id="notifications"
            role="switch"
            aria-label="Notifications"
            aria-checked="false"
            onclick="
              this.setAttribute(
                'aria-checked',
                this.getAttribute('aria-checked') === 'true' ? 'false' : 'true'
              );
            "
          >Notifications</button>
        </body></html>
        """
    )

    selected = session.select_semantic("Priority", "High")
    assert selected.get("selection_status") == "selected", selected
    assert selected.get("selected_value") == "high", selected
    assert selected.get("mutation_executed") is True, selected
    assert session.page.locator("#priority").input_value() == "high"

    selected_again = session.select_semantic("Priority", "High")
    assert selected_again.get("selection_status") == "already_satisfied", (
        selected_again
    )
    assert selected_again.get("mutation_executed") is False, selected_again

    checked = session.set_checked_semantic("Active", True)
    assert checked.get("check_status") == "set", checked
    assert checked.get("checked") is True, checked
    assert checked.get("mutation_executed") is True, checked

    unchanged = session.set_checked_semantic("Active", True)
    assert unchanged.get("check_status") == "already_satisfied", unchanged
    assert unchanged.get("mutation_executed") is False, unchanged
    assert session.page.locator("#active").is_checked() is True

    unchecked = session.set_checked_semantic("Active", False)
    assert unchecked.get("check_status") == "set", unchecked
    assert unchecked.get("checked") is False, unchecked

    custom_selected = session.select_semantic("Severity", "Critical")
    assert custom_selected.get("selection_strategy") == "aria-option", (
        custom_selected
    )
    assert custom_selected.get("selected_text") == "Critical", custom_selected

    switched = session.set_checked_semantic("Notifications", True)
    assert switched.get("check_status") == "set", switched
    assert switched.get("checked") is True, switched

    assert classify_tool_action(
        "browser_select_semantic",
        {"field": "Priority", "option": "High"},
    ) == "write"
    assert classify_tool_action(
        "browser_set_checked_semantic",
        {"field": "Active", "checked": True},
    ) == "write"
    assert tool_policy_check(
        "browser_select_semantic",
        {"field": "Priority", "option": "High"},
        [{"role": "user", "content": "Только проверь, ничего не изменяй"}],
    ).get("status") == "blocked_by_policy"
    assert tool_policy_check(
        "browser_set_checked_semantic",
        {"field": "Active", "checked": True},
        [],
        force_read_only=True,
    ).get("status") == "blocked_by_policy"

    state_key = ("smoke-job", "smoke-case")
    record_required_selection_result(
        state_key[0],
        state_key[1],
        selected,
        "browser_select_semantic",
        {"field": "Priority", "option": "High"},
    )
    assert _selection_key("Priority", "High") in (
        _COMPLETED_REQUIRED_SELECTIONS[state_key]
    )
finally:
    session.close()

print("form controls smoke: PASS")
