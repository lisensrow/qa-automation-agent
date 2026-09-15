from tools.browser import BrowserSession
from uqa import classify_tool_action


session = BrowserSession()

try:
    session._ensure_started()
    session.page.set_content(
        """
        <html><body>
          <button id="bulk" aria-label="Delete selected" disabled>
            Delete selected
          </button>
          <table aria-label="Users">
            <thead>
              <tr>
                <th>
                  <input
                    aria-label="Select all"
                    type="checkbox"
                    onchange="
                      document.querySelectorAll('#rows input[type=checkbox]')
                        .forEach(box => box.checked = this.checked);
                      document.getElementById('bulk').disabled = !this.checked;
                    "
                  >
                </th>
                <th role="columnheader">Name</th>
                <th role="columnheader">Team</th>
              </tr>
              <tr>
                <th></th>
                <th>
                  <input
                    aria-label="Name filter"
                    oninput="
                      const query = this.value.toLowerCase();
                      document.querySelectorAll('#rows tr').forEach(row => {
                        row.hidden = !row.cells[1].innerText
                          .toLowerCase().includes(query);
                      });
                    "
                  >
                </th>
                <th></th>
              </tr>
            </thead>
            <tbody id="rows">
              <tr><td><input type="checkbox"></td><td>Alpha</td><td>Ops</td></tr>
              <tr><td><input type="checkbox"></td><td>Beta</td><td>QA</td></tr>
            </tbody>
          </table>
        </body></html>
        """
    )

    filtered = session.fill_table_filter_semantic(
        "Name",
        "Beta",
        table="Users",
    )
    assert filtered.get("filter_status") == "applied", filtered
    assert filtered.get("rows_changed") is True, filtered
    assert filtered["table_after"]["visible_row_count"] == 1, filtered
    assert filtered["table_after"]["rows"][0]["cells"][1] == "Beta", filtered

    cleared = session.fill_table_filter_semantic(
        "Name",
        "",
        table="Users",
    )
    assert cleared.get("filter_status") == "applied", cleared
    assert cleared["table_after"]["visible_row_count"] == 2, cleared

    selected = session.set_table_all_selected(True, table="Users")
    assert selected.get("select_all_status") == "selected", selected
    assert selected.get("selected_row_count") == 2, selected

    selected_again = session.set_table_all_selected(True, table="Users")
    assert selected_again.get("select_all_status") == (
        "already_satisfied"
    ), selected_again

    preview = session.inspect_bulk_action_semantic(
        "Delete selected",
        table="Users",
        role="button",
    )
    assert preview.get("bulk_action_status") == "observed", preview
    assert preview.get("bulk_action_enabled") is True, preview
    assert preview.get("selected_row_count") == 2, preview
    assert session.page.locator("#bulk").get_attribute("data-clicked") is None

    assert classify_tool_action(
        "browser_inspect_bulk_action_semantic",
        {"name": "Delete selected"},
    ) == "observe"
    for tool_name in (
        "browser_fill_table_filter_semantic",
        "browser_set_table_all_selected",
    ):
        assert classify_tool_action(tool_name, {}) == "interact"
finally:
    session.close()

print("table filters and bulk preview smoke: PASS")
