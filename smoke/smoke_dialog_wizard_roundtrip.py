from tools.browser import BrowserSession
from uqa import classify_tool_action


def install_fixture(session, submit_on_next=False):
    request = (
        "fetch('/mutate', {method: 'POST', body: 'x'});"
        if submit_on_next else ""
    )
    session.page.route(
        "https://wizard.test/**",
        lambda route: route.fulfill(status=204)
        if route.request.url.endswith("/mutate")
        else route.fulfill(status=200, content_type="text/html", body=""),
    )
    session.page.goto("https://wizard.test/start")
    session.page.set_content(f"""
      <button id="open">Open wizard</button>
      <div role="dialog" aria-label="Setup wizard" hidden>
        <div data-step="Account" class="active">Account</div>
        <div data-step="Options">Options</div>
        <div data-step="Review">Review</div>
        <button id="back">Back</button>
        <button id="next">Next</button>
        <button id="cancel">Cancel</button>
      </div>
      <script>
        const dialog = document.querySelector('[role=dialog]');
        const steps = Array.from(document.querySelectorAll('[data-step]'));
        let current = 0;
        function render() {{
          steps.forEach((step, index) => step.classList.toggle('active', index === current));
          document.querySelector('#back').disabled = current === 0;
          document.querySelector('#next').disabled = current === steps.length - 1;
        }}
        document.querySelector('#open').onclick = () => {{ dialog.hidden = false; render(); }};
        document.querySelector('#next').onclick = () => {{ {request} current += 1; render(); }};
        document.querySelector('#back').onclick = () => {{ current -= 1; render(); }};
        document.querySelector('#cancel').onclick = () => {{ dialog.hidden = true; }};
      </script>
    """)


session = BrowserSession()
try:
    session._ensure_started()
    install_fixture(session)
    passed = session.verify_dialog_wizard_roundtrip_semantic(
        "Open wizard", "Setup wizard", ["Account", "Options", "Review"],
    )
    assert passed["wizard_roundtrip_passed"] is True, passed
    assert passed["observed_forward_steps"] == ["Account", "Options", "Review"], passed
    assert passed["observed_backward_steps"] == ["Options", "Account"], passed
    assert passed["dialog_closed"] is True, passed
    assert passed["no_submit_request_sent"] is True, passed
    assert passed["mutation_executed"] is False, passed
    assert classify_tool_action(
        "browser_verify_dialog_wizard_roundtrip_semantic", {}
    ) == "interact"

    forbidden = session.verify_dialog_wizard_roundtrip_semantic(
        "Open wizard", "Setup wizard", ["Account", "Options"],
        next_button="Submit",
    )
    assert forbidden["error"] == "wizard_submit_like_button_forbidden", forbidden
    assert forbidden["executed"] is False, forbidden
finally:
    session.close()


session = BrowserSession()
try:
    session._ensure_started()
    install_fixture(session, submit_on_next=True)
    blocked = session.verify_dialog_wizard_roundtrip_semantic(
        "Open wizard", "Setup wizard", ["Account", "Options", "Review"],
    )
    assert blocked["wizard_roundtrip_passed"] is False, blocked
    assert blocked["write_request_count"] >= 1, blocked
    assert blocked["no_submit_request_sent"] is False, blocked
    assert blocked["observation_result"] == "BLOCKED", blocked
finally:
    session.close()


print("dialog wizard roundtrip smoke: PASS")
