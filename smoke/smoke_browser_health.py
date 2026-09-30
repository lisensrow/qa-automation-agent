from tools.browser import BrowserSession


session = BrowserSession()
try:
    session._ensure_started()
    session.page.set_content("<button>Health target</button>")
    session._reset_diagnostics()
    session.page.evaluate(
        """
        () => {
          console.error("frontend smoke error");
          setTimeout(() => { throw new TypeError("frontend smoke exception"); }, 0);
          fetch("http://127.0.0.1:1/api?token=do-not-expose").catch(() => {});
        }
        """
    )
    session.page.wait_for_timeout(250)
    state = session._capture_state("browser-health-smoke")

    assert state["frontend_health_passed"] is False, state
    assert any("frontend smoke error" in item for item in state["console_errors"]), state
    assert any(
        "frontend smoke exception" in item["message"]
        for item in state["page_errors"]
    ), state
    assert state["failed_requests"], state
    serialized = repr(state["failed_requests"])
    assert "do-not-expose" not in serialized, serialized
    assert "redacted" in serialized, serialized

    session._reset_diagnostics()
    clean = session._capture_state("browser-health-clean")
    assert clean["frontend_health_passed"] is True, clean
finally:
    session.close()

print("browser health smoke: PASS")
