from tools.browser import BrowserSession
from uqa import classify_tool_action


session = BrowserSession()
try:
    session._ensure_started()
    session.page.set_content("""
      <main aria-label="Results" aria-busy="true" style="width:300px;height:120px">
        <div role="progressbar" aria-label="Loading results" style="width:200px;height:20px"></div>
      </main>
      <script>
        setTimeout(() => {
          const root = document.querySelector('main');
          root.setAttribute('aria-busy', 'false');
          document.querySelector('[role=progressbar]').remove();
          root.insertAdjacentHTML('beforeend', '<p>Ready</p>');
        }, 250);
      </script>
    """)
    lifecycle = session.inspect_loading_state_semantic(
        "Results", expected_state="ready", wait_ms=2000,
        require_transition=True,
    )
    assert lifecycle.get("loading_status") == "verified", lifecycle
    assert lifecycle["loading_observed_busy"] is True, lifecycle
    assert lifecycle["loading_observed_ready"] is True, lifecycle
    assert lifecycle["loading_initial"]["busy"] is True, lifecycle
    assert lifecycle["loading_final"]["busy"] is False, lifecycle

    session.page.set_content('<section aria-label="Stable" style="width:200px;height:50px">Done</section>')
    ready = session.inspect_loading_state_semantic("Stable", wait_ms=0)
    assert ready["loading_status"] == "verified", ready
    assert ready["loading_final"]["busy"] is False, ready
    assert ready["loading_final"]["indicators"] == [], ready

    missing_transition = session.inspect_loading_state_semantic(
        "Stable", wait_ms=100, require_transition=True,
    )
    assert missing_transition["loading_status"] == "mismatch", missing_transition
    assert missing_transition["error"] == "loading_state_verification_failed"

    session.page.set_content("""
      <section aria-label="Duplicate" style="width:10px;height:10px"></section>
      <section aria-label="Duplicate" style="width:10px;height:10px"></section>
    """)
    ambiguous = session.inspect_loading_state_semantic("Duplicate", wait_ms=0)
    assert ambiguous == {
        "error": "loading_scope_not_unique", "matches": 2, "executed": False,
    }, ambiguous
    assert classify_tool_action("browser_inspect_loading_state_semantic", {}) == "observe"
finally:
    session.close()

print("loading state smoke: PASS")
