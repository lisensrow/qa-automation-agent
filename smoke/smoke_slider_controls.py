from tools.browser import BrowserSession
from uqa import classify_tool_action


session = BrowserSession()

try:
    session._ensure_started()
    session.page.set_content(
        """
        <html><body>
          <label>Volume
            <input type="range" min="0" max="10" step="2" value="2">
          </label>
          <div id="zoom" role="slider" aria-label="Zoom" tabindex="0"
               aria-valuemin="0" aria-valuemax="10" aria-valuenow="4"
               data-step="2" style="width: 200px; height: 20px;"></div>
          <button onclick="window.saveClicks += 1">Save</button>
          <script>
            window.saveClicks = 0;
            document.getElementById('zoom').addEventListener('keydown', event => {
              const el = event.currentTarget;
              let value = Number(el.getAttribute('aria-valuenow'));
              if (event.key === 'ArrowRight') value = Math.min(10, value + 2);
              if (event.key === 'ArrowLeft') value = Math.max(0, value - 2);
              el.setAttribute('aria-valuenow', String(value));
            });
          </script>
        </body></html>
        """
    )

    native = session.set_slider_semantic("Volume", 6)
    assert native.get("slider_status") == "applied", native
    assert native.get("slider_adapter") == "native-range", native
    assert native.get("actual_value") == "6", native
    assert native.get("slider_key_presses") == 2, native

    native_again = session.set_slider_semantic("Volume", 6)
    assert native_again.get("slider_status") == "already_satisfied", native_again
    assert native_again.get("mutation_executed") is False, native_again

    mismatch = session.set_slider_semantic("Volume", 5)
    assert mismatch.get("error") == "slider_value_step_mismatch", mismatch
    assert mismatch.get("executed") is False, mismatch
    out_of_range = session.set_slider_semantic("Volume", 12)
    assert out_of_range.get("error") == "slider_value_out_of_range", out_of_range

    aria = session.set_slider_semantic("Zoom", 8)
    assert aria.get("slider_status") == "applied", aria
    assert aria.get("slider_adapter") == "aria-slider", aria
    assert aria.get("actual_value") == "8", aria
    assert aria.get("slider_key") == "ArrowRight", aria

    assert session.page.evaluate("window.saveClicks") == 0
    assert classify_tool_action(
        "browser_set_slider_semantic",
        {"field": "Volume", "value": 6},
    ) == "write"
finally:
    session.close()

print("slider controls smoke: PASS")
