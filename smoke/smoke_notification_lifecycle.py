from tools.browser import BrowserSession
from uqa import classify_tool_action


session = BrowserSession()
try:
    session._ensure_started()
    session.page.set_content("""
      <main style="width:300px;height:120px">
        <div role="alert" style="width:200px;height:30px">Saved successfully</div>
      </main>
      <script>
        setTimeout(() => document.querySelector('[role=alert]').remove(), 250);
      </script>
    """)
    dismissed = session.inspect_notification_lifecycle_semantic(
        "Saved successfully", role="alert", expected_state="dismissed",
        wait_ms=2000, require_seen=True,
    )
    assert dismissed.get("notification_status") == "verified", dismissed
    assert dismissed["notification_observed_visible"] is True, dismissed
    assert dismissed["notification_final"]["match_count"] == 0, dismissed

    session.page.set_content("""
      <main style="width:300px;height:120px"></main>
      <script>
        setTimeout(() => {
          document.querySelector('main').innerHTML =
            '<div role="status" style="width:200px;height:30px">Sync complete</div>';
        }, 250);
      </script>
    """)
    appeared = session.inspect_notification_lifecycle_semantic(
        "Sync complete", role="status", expected_state="visible", wait_ms=2000,
    )
    assert appeared.get("notification_status") == "verified", appeared
    assert appeared["notification_initial"]["match_count"] == 0, appeared
    assert appeared["notification_final"]["visible"] is True, appeared

    session.page.set_content("""
      <div role="alert" style="width:100px;height:20px">Duplicate</div>
      <div role="alert" style="width:100px;height:20px">Duplicate</div>
    """)
    ambiguous = session.inspect_notification_lifecycle_semantic(
        "Duplicate", wait_ms=0,
    )
    assert ambiguous["error"] == "notification_not_unique", ambiguous
    assert ambiguous["notification_status"] == "mismatch", ambiguous
    assert classify_tool_action(
        "browser_inspect_notification_lifecycle_semantic", {},
    ) == "observe"
finally:
    session.close()

print("notification lifecycle smoke: PASS")
