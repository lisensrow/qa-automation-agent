"""Real isolated Chromium DOM fixtures; no U-Connect, credentials, or model."""
from playwright.sync_api import sync_playwright
from tools.browser import BrowserSession

with sync_playwright() as runtime:
    browser = runtime.chromium.launch(headless=True, args=["--no-sandbox"])
    try:
        page = browser.new_page()
        session = BrowserSession.__new__(BrowserSession)
        session.page = page
        session._ensure_started = session._reset_diagnostics = lambda: None
        session._capture_state = lambda _: {}
        page.set_content('<table><tr><td>Exact CI</td><td>Exact CI</td></tr></table>')
        snapshot = session._tab_details_identity_snapshot("Exact CI")
        assert snapshot == {"anchor_match_count": 0, "exact_visible_count": 2, "outside_row_match_count": 0}
        page.set_content('<table><tr><td>Exact CI</td></tr></table><h2>Exact CI</h2><div hidden>Exact CI</div>')
        snapshot = session._tab_details_identity_snapshot("Exact CI")
        assert snapshot == {"anchor_match_count": 1, "exact_visible_count": 2, "outside_row_match_count": 1}
        page.set_content('''<div role="tablist" aria-label="Details">
            <button role="tab" aria-selected="true" aria-controls="agent-panel">Agent</button>
            <button role="tab" aria-selected="false" aria-controls="monitor-panel">Monitoring</button>
            <div id="agent-panel" role="tabpanel">
                <div role="tablist" aria-label="Agent sections">
                    <button role="tab" aria-selected="true" aria-controls="tasks-panel">Tasks</button>
                    <button role="tab" aria-selected="false" aria-controls="plugins-panel">Plugins</button>
                </div><div role="tabpanel" id="tasks-panel">Tasks content</div>
                <div role="tabpanel" id="plugins-panel" hidden>Plugins content</div>
            </div><div id="monitor-panel" role="tabpanel" hidden>Monitoring content</div>
        </div>''')
        assert session.inspect_tabs_contract_semantic()["matches"] == 2
        audit = session.inspect_tabs_contract_semantic(_target_tab_name="Agent")["tabs_audit"]
        assert audit["selected_count"] == 1 and audit["tab_count"] == 2
        assert [tab["label"] for tab in audit["tabs"]] == ["Agent", "Monitoring"]
        assert audit["tabs_contract_passed"] is True
        child = session.inspect_tabs_contract_semantic(_target_tab_name="Tasks")["tabs_audit"]
        assert child["selected_count"] == 1 and child["tab_count"] == 2
        assert session.inspect_tabs_contract_semantic(_target_tab_name="Absent")["matches"] == 0
        page.locator("body").evaluate('''body => {
            const copy = document.createElement('div'); copy.setAttribute('role','tablist');
            copy.innerHTML = '<button role="tab" aria-selected="true">Agent</button>';
            body.append(copy);
        }''')
        assert session.inspect_tabs_contract_semantic(_target_tab_name="Agent")["matches"] == 2
    finally:
        browser.close()
print("tab navigation real DOM fixtures: PASS (no product access)")
