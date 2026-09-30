from tools.browser import BrowserSession
from tools.registry import TOOLS
from uqa import classify_tool_action


session = BrowserSession()
try:
    session._ensure_started()
    session.page.set_content(
        """
        <button id="time-trigger" aria-label="Start time"
                aria-controls="time-overlay"
                onclick="document.getElementById('time-overlay').hidden=false">
          Choose time
        </button>
        <div id="time-overlay" role="dialog"
             aria-label="Start time picker" hidden>
          <div role="listbox" aria-label="Available times">
            <button role="option" aria-label="09:00"
                    data-time="09:00">09:00</button>
            <button role="option" aria-label="09:30"
                    data-time="09:30"
                    onclick="this.setAttribute('aria-selected','true');
                      document.getElementById('time-trigger').textContent='09:30';
                      document.getElementById('time-overlay').hidden=true">09:30</button>
            <button role="option" aria-label="10:00"
                    aria-disabled="true" data-time="10:00">10:00</button>
          </div>
        </div>
        """
    )

    closed = session.inspect_time_picker_semantic("Start time")
    assert closed.get("error") == "time_picker_not_open", closed
    opened = session.open_time_picker_semantic("Start time")
    assert opened.get("time_picker_status") == "opened", opened
    assert opened["time_picker_snapshot"]["listbox_count"] == 1, opened
    assert any(
        item["time"] == "09:30"
        for item in opened["time_picker_snapshot"]["options"]
    ), opened
    observed = session.inspect_time_picker_semantic("Start time")
    assert observed.get("time_picker_status") == "observed", observed

    missing = session.select_time_picker_option_semantic(
        "Start time", "09:45"
    )
    assert missing.get("error") == "time_picker_option_not_found", missing
    disabled = session.select_time_picker_option_semantic(
        "Start time", "10:00"
    )
    assert disabled.get("error") == "time_picker_option_disabled", disabled
    selected = session.select_time_picker_option_semantic(
        "Start time", "09:30"
    )
    assert selected.get("time_picker_status") == "selected", selected
    assert selected.get("selection_verified") is True, selected
    assert selected.get("trigger_changed") is True, selected
    assert selected.get("time_picker_open_after") is False, selected

    assert classify_tool_action(
        "browser_inspect_time_picker_semantic", {"trigger": "Start time"}
    ) == "observe"
    assert classify_tool_action(
        "browser_open_time_picker_semantic", {"trigger": "Start time"}
    ) == "interact"
    assert classify_tool_action(
        "browser_select_time_picker_option_semantic",
        {"trigger": "Start time", "option": "09:30"},
    ) == "write"
    names = {item["function"]["name"] for item in TOOLS}
    assert {
        "browser_inspect_time_picker_semantic",
        "browser_open_time_picker_semantic",
        "browser_select_time_picker_option_semantic",
    } <= names
finally:
    session.close()

print("time picker overlay smoke: PASS")
