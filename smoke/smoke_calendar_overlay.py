from tools.browser import BrowserSession
from tools.registry import TOOLS
from uqa import classify_tool_action


session = BrowserSession()
try:
    session._ensure_started()
    session.page.set_content(
        """
        <button id="date-trigger" aria-label="Start date"
                aria-controls="calendar-overlay"
                onclick="document.getElementById('calendar-overlay').hidden=false">
          Choose date
        </button>
        <div id="calendar-overlay" role="dialog"
             aria-label="Start date calendar" hidden>
          <div role="grid" aria-label="September 2026">
            <button role="gridcell" aria-label="September 29, 2026"
                    data-date="2026-09-29">29</button>
            <button role="gridcell" aria-label="September 30, 2026"
                    data-date="2026-09-30"
                    onclick="this.setAttribute('aria-selected','true');
                      document.getElementById('date-trigger').textContent='2026-09-30';
                      document.getElementById('calendar-overlay').hidden=true">30</button>
            <button role="gridcell" aria-label="October 1, 2026"
                    aria-disabled="true" data-date="2026-10-01">1</button>
          </div>
        </div>
        """
    )

    closed = session.inspect_calendar_semantic("Start date")
    assert closed.get("error") == "calendar_not_open", closed
    opened = session.open_calendar_semantic("Start date")
    assert opened.get("calendar_status") == "opened", opened
    assert opened["calendar_snapshot"]["grid_count"] == 1, opened
    assert any(
        item["date"] == "2026-09-30"
        for item in opened["calendar_snapshot"]["options"]
    ), opened
    observed = session.inspect_calendar_semantic("Start date")
    assert observed.get("calendar_status") == "observed", observed

    missing = session.select_calendar_option_semantic(
        "Start date", "September 31, 2026"
    )
    assert missing.get("error") == "calendar_option_not_found", missing
    disabled = session.select_calendar_option_semantic(
        "Start date", "October 1, 2026"
    )
    assert disabled.get("error") == "calendar_option_disabled", disabled
    selected = session.select_calendar_option_semantic(
        "Start date", "September 30, 2026"
    )
    assert selected.get("calendar_status") == "selected", selected
    assert selected.get("selection_verified") is True, selected
    assert selected.get("trigger_changed") is True, selected
    assert selected.get("calendar_open_after") is False, selected

    assert classify_tool_action(
        "browser_inspect_calendar_semantic", {"trigger": "Start date"}
    ) == "observe"
    assert classify_tool_action(
        "browser_open_calendar_semantic", {"trigger": "Start date"}
    ) == "interact"
    assert classify_tool_action(
        "browser_select_calendar_option_semantic",
        {"trigger": "Start date", "option": "September 30, 2026"},
    ) == "write"
    names = {item["function"]["name"] for item in TOOLS}
    assert {
        "browser_inspect_calendar_semantic",
        "browser_open_calendar_semantic",
        "browser_select_calendar_option_semantic",
    } <= names
finally:
    session.close()

print("calendar overlay smoke: PASS")
