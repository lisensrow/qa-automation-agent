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

    # Labels and controls may be rendered in separate sibling branches.  The
    # first shared ancestor then contains several fields, so DOM ancestry alone
    # must not guess.  The bounded layout fallback selects the aligned field.
    session.page.set_content(
        """
        <main style="position: relative; width: 600px; height: 300px">
          <div style="position: absolute; left: 20px; top: 20px">Name</div>
          <div style="position: absolute; left: 20px; top: 110px">Parent</div>
          <div style="position: absolute; left: 20px; top: 45px">
            <input id="split-name" type="text"
                   style="display:block; width:300px; height:30px">
            <input id="split-parent" role="combobox" type="text"
                   style="display:block; width:300px; height:30px; margin-top:40px">
          </div>
        </main>
        """
    )

    result = session.fill_semantic(
        "Name",
        "uqa-spatial-location",
        exact=True,
    )

    assert "error" not in result, result
    assert result.get("fill_strategy") == "nearby-visible-label", result
    assert (
        session.page.locator("#split-name").input_value()
        == "uqa-spatial-location"
    )
    assert session.page.locator("#split-parent").input_value() == ""
finally:
    session.close()

print("smoke_labeled_field_fallback: PASS")
