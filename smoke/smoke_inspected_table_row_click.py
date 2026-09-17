"""A row click requires one previously inspected exact visible cell."""

from tools.browser import BrowserSession


session = BrowserSession()
try:
    session._ensure_started()
    session.page.set_content("""
        <table><thead><tr><th>Name</th><th>OS</th></tr></thead>
        <tbody>
          <tr onclick="document.querySelector('#opened').textContent='ubuntu'">
            <td>test-ubuntu</td><td>Ubuntu</td>
          </tr>
          <tr onclick="document.querySelector('#opened').textContent='windows'">
            <td>test-windows</td><td>Windows</td>
          </tr>
        </tbody></table><div id="opened"></div>
    """)
    denied = session.click_semantic(
        "test-ubuntu", role="row", container="test-ubuntu",
    )
    assert denied["error"] == "row_click_requires_exact_inspection", denied
    assert session.page.locator("#opened").inner_text() == ""

    inspected = session.inspect_table_row("test-ubuntu")
    assert inspected["row_match_count"] == 1, inspected
    opened = session.click_semantic(
        "test-ubuntu", role="row", container="test-ubuntu",
    )
    assert not opened.get("error"), opened
    assert session.page.locator("#opened").inner_text() == "ubuntu"

    repeated = session.click_semantic("test-ubuntu", role="row")
    assert repeated["error"] == "row_click_requires_exact_inspection"

    session.inspect_table_row("test-ubuntu")
    session.page.locator("tbody").evaluate(
        "body => body.insertAdjacentHTML('beforeend', '<tr><td>test-ubuntu</td><td>Other</td></tr>')"
    )
    ambiguous = session.click_semantic("test-ubuntu", role="row")
    assert ambiguous["error"] == "row_exact_cell_missing_or_ambiguous"
    assert ambiguous["matches"] == 2
finally:
    session.close()

print("inspected table row click smoke: PASS")
