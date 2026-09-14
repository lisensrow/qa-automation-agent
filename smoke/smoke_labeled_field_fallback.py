#!/opt/uqa/.venv/bin/python

from tools.browser import BrowserSession


session = BrowserSession()

try:
    session._ensure_started()
    session.page.set_content(
        """
        <main>
          <div class="field-group">
            <div class="field-label">Name</div>
            <input id="location-name" type="text">
          </div>
        </main>
        """
    )

    result = session.fill_semantic(
        "Name",
        "uqa-smoke-location",
        exact=True,
    )

    assert "error" not in result, result
    assert result.get("fill_strategy") == "nearby-visible-label", result
    assert (
        session.page.locator("#location-name").input_value()
        == "uqa-smoke-location"
    )
finally:
    session.close()

print("smoke_labeled_field_fallback: PASS")
