from tools.browser import BrowserSession
from uqa import classify_tool_action, tool_policy_check


session = BrowserSession()

try:
    session._ensure_started()
    session.page.set_content(
        """
        <html><body>
          <fieldset>
            <legend>Delivery</legend>
            <label><input type="radio" name="delivery" value="fast"> Fast</label>
            <label><input type="radio" name="delivery" value="safe"> Safe</label>
          </fieldset>

          <label for="tags">Tags</label>
          <select id="tags" name="tags" multiple>
            <option value="api">API</option>
            <option value="frontend">Frontend</option>
            <option value="smoke">Smoke</option>
          </select>

          <label for="owner">Owner</label>
          <input
            id="owner"
            role="combobox"
            aria-autocomplete="list"
            aria-controls="owners"
            oninput="
              document.getElementById('owners').hidden =
                this.value.toLowerCase() !== 'alice';
            "
          >
          <div id="owners" role="listbox" hidden>
            <button
              role="option"
              onclick="
                document.getElementById('owner').value = 'Alice';
                document.getElementById('owner')
                  .setAttribute('aria-valuetext', 'Alice');
                document.getElementById('owners').hidden = true;
              "
            >Alice</button>
          </div>
        </body></html>
        """
    )

    radio = session.choose_radio_semantic("Safe", "Delivery")
    assert radio.get("radio_status") == "selected", radio
    assert radio.get("mutation_executed") is True, radio
    assert session.page.locator('input[value="safe"]').is_checked()

    radio_again = session.choose_radio_semantic("Safe", "Delivery")
    assert radio_again.get("radio_status") == "already_satisfied", radio_again
    assert radio_again.get("mutation_executed") is False, radio_again

    selected = session.select_many_semantic(
        "Tags",
        ["API", "Smoke"],
    )
    assert selected.get("selection_status") == "selected", selected
    assert set(selected.get("selected_options") or []) == {"API", "Smoke"}

    selected_again = session.select_many_semantic(
        "Tags",
        ["Smoke", "API"],
    )
    assert selected_again.get("selection_status") == "already_satisfied", (
        selected_again
    )
    assert selected_again.get("mutation_executed") is False, selected_again

    autocomplete = session.select_semantic("Owner", "Alice")
    assert autocomplete.get("selection_strategy") == (
        "aria-autocomplete-option"
    ), autocomplete
    assert autocomplete.get("selected_text") == "Alice", autocomplete

    for tool_name, arguments in (
        (
            "browser_choose_radio_semantic",
            {"group": "Delivery", "option": "Safe"},
        ),
        (
            "browser_select_many_semantic",
            {"field": "Tags", "options": ["API", "Smoke"]},
        ),
    ):
        assert classify_tool_action(tool_name, arguments) == "write"
        blocked = tool_policy_check(
            tool_name,
            arguments,
            [{"role": "user", "content": "Только проверь, не изменяй"}],
        )
        assert blocked.get("status") == "blocked_by_policy", blocked
finally:
    session.close()

print("advanced form controls smoke: PASS")
