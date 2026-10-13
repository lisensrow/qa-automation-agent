"""Real isolated Chromium: markers are scoped, bounded, and secret-safe."""
from playwright.sync_api import sync_playwright
from tools.browser import BrowserSession
import json

with sync_playwright() as runtime:
    browser = runtime.chromium.launch(headless=True, args=["--no-sandbox"])
    try:
        page = browser.new_page()
        session = BrowserSession.__new__(BrowserSession)
        session.page = page
        page.set_content('''<div id="panel" role="tabpanel"><p>No data to display</p>
            <pre hidden>Infinite extent hidden</pre></div>
            <pre>Uncaught TypeError: outside this panel</pre>''')
        result = session._panel_renderer_message_audit("panel")
        assert result == {"observed": True, "complete": True, "markers": []}
        page.locator("#panel").evaluate('''root => {
            const error = document.createElement('pre');
            error.textContent = 'Infinite extent for field private-fixture-only: [Infinity, -Infinity]';
            root.append(error);
        }''')
        result = session._panel_renderer_message_audit("panel")
        assert result == {"observed": True, "complete": True, "markers": ["infinite_extent"]}
        assert "private-fixture-only" not in json.dumps(result)
        page.set_content('<div id="panel"><div>Infinite extent for field<br><span>private-fixture-only</span></div></div>')
        assert session._panel_renderer_message_audit("panel")["markers"] == ["infinite_extent"]
        page.set_content('<div id="panel"><span>Infinite</span> <span>extent</span><i aria-hidden="true"></i></div>')
        assert session._panel_renderer_message_audit("panel")["markers"] == ["infinite_extent"]
        page.set_content('<div id="panel">Uncaught (in promise) ReferenceError: private-fixture-only</div>')
        assert session._panel_renderer_message_audit("panel")["markers"] == ["javascript_reference_error"]
        assert session._panel_renderer_message_audit("absent")["observed"] is False
        page.set_content('<div id="panel" hidden>Infinite extent</div>')
        assert session._panel_renderer_message_audit("panel")["observed"] is False
        page.set_content('<div id="panel">' + '<span>ordinary data</span>'*501 + '</div>')
        assert session._panel_renderer_message_audit("panel")["complete"] is True
        page.set_content('<div id="panel"><pre>' + 'a'*65537 + '</pre></div>')
        assert session._panel_renderer_message_audit("panel")["complete"] is False
        page.set_content('<div id="panel"><pre>Infinite extent ' + 'a'*65537 + '</pre></div>')
        result = session._panel_renderer_message_audit("panel")
        assert result["complete"] is False and result["markers"] == ["infinite_extent"]
        page.set_content('''<div id="panel"><iframe srcdoc="<pre>Infinite extent private-fixture-only</pre>"></iframe>
            <iframe hidden srcdoc="<pre>Uncaught TypeError hidden</pre>"></iframe></div>
            <iframe srcdoc="<pre>Uncaught ReferenceError outside</pre>"></iframe>''')
        result = session._panel_renderer_message_audit("panel")
        assert result == {"observed": True, "complete": True, "markers": ["infinite_extent"]}
        assert "private-fixture-only" not in json.dumps(result)
        page.set_content('<div id="panel">' + '<iframe srcdoc="<p>ordinary data</p>"></iframe>'*9 + '</div>')
        result = session._panel_renderer_message_audit("panel")
        assert result["complete"] is False and result["markers"] == []
    finally:
        browser.close()
print("panel renderer real DOM fixtures: PASS (no product access, no raw messages)")
