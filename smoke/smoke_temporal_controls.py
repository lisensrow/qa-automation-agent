from tools.browser import BrowserSession
from uqa import classify_tool_action


session = BrowserSession()

try:
    session._ensure_started()
    session.page.set_content(
        """
        <html><body>
          <label>Start date
            <input type="date" min="2026-01-01" max="2026-12-31" value="2026-09-01">
          </label>
          <label>Start time
            <input type="time" min="09:00" max="18:00" step="900" value="09:00">
          </label>
          <label>Meeting
            <input type="datetime-local" min="2026-09-01T09:00" max="2026-09-30T18:00">
          </label>
          <label>Billing month<input type="month"></label>
          <label>Release week<input type="week"></label>
          <label>Locked date<input type="date" value="2026-09-01" disabled></label>
          <button onclick="window.submitClicks += 1">Save</button>
          <script>window.submitClicks = 0;</script>
        </body></html>
        """
    )

    date_result = session.set_temporal_semantic(
        "Start date", "2026-09-16"
    )
    assert date_result.get("temporal_status") == "applied", date_result
    assert date_result.get("actual_value") == "2026-09-16", date_result
    assert date_result.get("temporal_input_type") == "date", date_result

    date_again = session.set_temporal_semantic(
        "Start date", "2026-09-16"
    )
    assert date_again.get("temporal_status") == "already_satisfied", date_again
    assert date_again.get("mutation_executed") is False, date_again

    invalid_date = session.set_temporal_semantic(
        "Start date", "2026-02-30"
    )
    assert invalid_date.get("error") == (
        "temporal_value_invalid_or_out_of_range"
    ), invalid_date
    assert invalid_date.get("executed") is False, invalid_date
    assert session.page.get_by_label("Start date").input_value() == "2026-09-16"

    out_of_range = session.set_temporal_semantic(
        "Start date", "2027-01-01"
    )
    assert out_of_range.get("constraint_validation", {}).get(
        "range_overflow"
    ) is True, out_of_range

    bad_step = session.set_temporal_semantic("Start time", "09:07")
    assert bad_step.get("constraint_validation", {}).get(
        "step_mismatch"
    ) is True, bad_step
    time_result = session.set_temporal_semantic("Start time", "09:30")
    assert time_result.get("temporal_status") == "applied", time_result

    meeting = session.set_temporal_semantic(
        "Meeting", "2026-09-16T14:30"
    )
    assert meeting.get("actual_value") == "2026-09-16T14:30", meeting
    month = session.set_temporal_semantic("Billing month", "2026-10")
    assert month.get("actual_value") == "2026-10", month
    week = session.set_temporal_semantic("Release week", "2026-W42")
    assert week.get("actual_value") == "2026-W42", week
    locked = session.set_temporal_semantic("Locked date", "2026-09-16")
    assert locked.get("error") == "temporal_field_not_editable", locked
    assert locked.get("executed") is False, locked

    assert session.page.evaluate("window.submitClicks") == 0
    assert classify_tool_action(
        "browser_set_temporal_semantic",
        {"field": "Start date", "value": "2026-09-16"},
    ) == "write"
finally:
    session.close()

print("temporal controls smoke: PASS")
