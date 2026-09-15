from tools.browser import BrowserSession
from uqa import classify_tool_action


session = BrowserSession()

try:
    session._ensure_started()
    session.page.set_content(
        """
        <html><body>
          <div id="table-scope">
            <table aria-label="Assets" data-total-count="137">
              <thead><tr>
                <th role="columnheader">Name</th>
                <th role="columnheader">
                  Status
                  <button aria-label="Filter status" aria-controls="status-filter">Filter</button>
                </th>
              </tr></thead>
              <tbody id="asset-rows">
                <tr><td>Alpha</td><td>Active</td></tr>
                <tr><td>Beta</td><td>Archived</td></tr>
              </tbody>
            </table>
            <div id="range">1-2 of 137</div>
            <button aria-current="page">1</button>
            <button aria-label="Next page">Next</button>
          </div>
          <div id="status-filter" role="dialog" aria-label="Status filter" hidden>
            <label>Operator<select id="operator">
              <option>Equals</option><option>Contains</option>
            </select></label>
            <label>Value<input id="filter-value"></label>
            <button id="apply">Apply</button>
          </div>
          <script>
            document.querySelector('[aria-label="Filter status"]').onclick = () => {
              document.getElementById('status-filter').hidden = false;
            };
            document.getElementById('apply').onclick = () => {
              const value = document.getElementById('filter-value').value.toLowerCase();
              document.querySelectorAll('#asset-rows tr').forEach(row => {
                row.hidden = !row.cells[1].innerText.toLowerCase().includes(value);
              });
              document.querySelector('table').setAttribute('data-total-count', '1');
              document.getElementById('range').innerText = '1-1 of 1';
              document.getElementById('status-filter').hidden = true;
            };
          </script>
        </body></html>
        """
    )

    before = session.inspect_table_pagination_semantic("Assets")
    assert before.get("total_row_count") == 137, before
    assert before.get("total_source") == "data-total-count", before
    assert before.get("visible_range_start") == 1, before
    assert before.get("visible_range_end") == 2, before
    assert before.get("current_page") == 1, before

    filtered = session.apply_table_filter_popover_semantic(
        "Status",
        "Active",
        table="Assets",
        trigger="Filter status",
        operator="Equals",
        apply_button="Apply",
    )
    assert filtered.get("filter_submission_status") == "submitted", filtered
    assert filtered.get("filter_popover_strategy") == "aria-controls", filtered
    assert filtered.get("filter_operator") == "Equals", filtered
    assert filtered.get("rows_changed") is True, filtered
    assert filtered["table_after"]["visible_row_count"] == 1, filtered

    after = session.inspect_table_pagination_semantic("Assets")
    assert after.get("total_row_count") == 1, after
    assert after.get("visible_range_start") == 1, after
    assert after.get("visible_range_end") == 1, after

    assert classify_tool_action(
        "browser_inspect_table_pagination_semantic",
        {},
    ) == "observe"
    assert classify_tool_action(
        "browser_apply_table_filter_popover_semantic",
        {},
    ) == "interact"
finally:
    session.close()

print("table popover/totals smoke: PASS")
