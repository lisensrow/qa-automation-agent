from tools.browser import BrowserSession
from uqa import classify_tool_action


session = BrowserSession()

try:
    session._ensure_started()
    session.page.set_content(
        """
        <html><body>
          <table aria-label="Users">
            <thead>
              <tr>
                <th>Select</th>
                <th
                  role="columnheader"
                  aria-sort="none"
                  onclick="
                    const body = this.closest('table').tBodies[0];
                    const rows = Array.from(body.rows);
                    const descending =
                      this.getAttribute('aria-sort') !== 'descending';
                    rows.sort((a, b) => descending
                      ? b.cells[1].innerText.localeCompare(a.cells[1].innerText)
                      : a.cells[1].innerText.localeCompare(b.cells[1].innerText)
                    );
                    rows.forEach(row => body.appendChild(row));
                    this.setAttribute(
                      'aria-sort',
                      descending ? 'descending' : 'ascending'
                    );
                  "
                >Name</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody id="rows">
              <tr><td><input type="checkbox"></td><td>Alpha</td><td>10</td></tr>
              <tr><td><input type="checkbox"></td><td>Beta</td><td>20</td></tr>
            </tbody>
          </table>
          <button
            aria-label="Next page"
            onclick="
              document.getElementById('rows').innerHTML =
                '<tr><td><input type=checkbox></td><td>Gamma</td><td>30</td></tr>' +
                '<tr><td><input type=checkbox></td><td>Delta</td><td>40</td></tr>';
            "
          >Next</button>
        </body></html>
        """
    )

    inspected = session.inspect_table_semantic("Users")
    summary = inspected.get("table_summary") or {}
    assert summary.get("visible_row_count") == 2, inspected
    assert summary["rows"][0]["values_by_header"]["Name"] == "Alpha", inspected

    sorted_result = session.sort_table_semantic(
        "Name",
        "desc",
        table="Users",
    )
    assert sorted_result.get("sort_status") == "sorted", sorted_result
    assert sorted_result.get("observed_aria_sort") == "descending", sorted_result
    assert sorted_result["table_after"]["rows"][0]["cells"][1] == "Beta"

    selected = session.set_table_row_selected("Alpha", True)
    assert selected.get("row_selection_status") == "selected", selected
    assert selected.get("selected") is True, selected

    selected_again = session.set_table_row_selected("Alpha", True)
    assert selected_again.get("row_selection_status") == (
        "already_satisfied"
    ), selected_again

    paged = session.table_page_semantic(
        "Next page",
        table="Users",
    )
    assert paged.get("table_page_status") == "changed", paged
    assert paged["table_after"]["rows"][0]["cells"][1] == "Gamma", paged

    assert classify_tool_action(
        "browser_inspect_table_semantic",
        {"table": "Users"},
    ) == "observe"
    for tool_name in (
        "browser_sort_table_semantic",
        "browser_set_table_row_selected",
        "browser_table_page_semantic",
    ):
        assert classify_tool_action(tool_name, {}) == "interact"
finally:
    session.close()

print("table controls smoke: PASS")
