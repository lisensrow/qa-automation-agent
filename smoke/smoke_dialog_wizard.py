from tools.browser import BrowserSession
from tools.registry import TOOLS
from uqa import classify_tool_action


session = BrowserSession()
try:
    session._ensure_started()
    session.page.set_content(
        """
        <button>Next</button>
        <div id="wizard" role="dialog" aria-label="Setup wizard">
          <ol>
            <li id="step-one" data-step="Account" aria-current="step">Account</li>
            <li id="step-two" data-step="Review">Review</li>
          </ol>
          <section id="panel-one"><label>Name<input></label></section>
          <section id="panel-two" hidden>Review data</section>
          <button id="next" onclick="
            document.getElementById('step-one').removeAttribute('aria-current');
            document.getElementById('step-two').setAttribute('aria-current','step');
            document.getElementById('panel-one').hidden=true;
            document.getElementById('panel-two').hidden=false">Next</button>
          <button disabled>Unavailable</button>
          <button id="finish" onclick="document.getElementById('wizard').hidden=true">Finish</button>
        </div>
        """
    )

    observed = session.inspect_dialog_semantic("Setup wizard")
    assert observed.get("dialog_status") == "observed", observed
    assert observed["dialog_snapshot"]["active_steps"] == ["Account"], observed
    assert observed["dialog_snapshot"]["visible_field_count"] == 1, observed

    missing = session.click_dialog_button_semantic(
        "Setup wizard", "Missing"
    )
    assert missing.get("error") == "dialog_button_not_found", missing
    disabled = session.click_dialog_button_semantic(
        "Setup wizard", "Unavailable"
    )
    assert disabled.get("error") == "dialog_button_disabled", disabled
    advanced = session.click_dialog_button_semantic("Setup wizard", "Next")
    assert advanced.get("dialog_button_status") == "clicked", advanced
    assert advanced.get("step_changed") is True, advanced
    assert advanced["dialog_after"]["active_steps"] == ["Review"], advanced
    assert advanced.get("dialog_open_after") is True, advanced

    finished = session.click_dialog_button_semantic("Setup wizard", "Finish")
    assert finished.get("dialog_closed") is True, finished
    assert finished.get("dialog_open_after") is False, finished

    assert classify_tool_action(
        "browser_inspect_dialog_semantic", {"dialog": "Setup wizard"}
    ) == "observe"
    assert classify_tool_action(
        "browser_click_dialog_button_semantic",
        {"dialog": "Setup wizard", "button": "Next"},
    ) == "interact"
    assert classify_tool_action(
        "browser_click_dialog_button_semantic",
        {"dialog": "Setup wizard", "button": "Save"},
    ) == "write"
    assert classify_tool_action(
        "browser_click_dialog_button_semantic",
        {"dialog": "Setup wizard", "button": "Delete"},
    ) == "destructive"
    names = {item["function"]["name"] for item in TOOLS}
    assert {
        "browser_inspect_dialog_semantic",
        "browser_click_dialog_button_semantic",
    } <= names
finally:
    session.close()

print("dialog wizard smoke: PASS")
