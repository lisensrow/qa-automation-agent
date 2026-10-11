from tools.browser import BrowserSession
from uqa import _core_observation_call_key, classify_tool_action


session = BrowserSession()
try:
    session._ensure_started()
    session.page.set_content("""
      <table aria-label="Assets">
        <thead><tr><th aria-sort="descending">Name</th></tr></thead>
        <tbody>
          <tr><td>Charlie</td></tr>
          <tr><td>Beta</td></tr>
          <tr><td>Alpha</td></tr>
        </tbody>
      </table>
      <script>
        const header = document.querySelector('th');
        const body = document.querySelector('tbody');
        header.onclick = () => {
          const next = header.getAttribute('aria-sort') === 'ascending'
            ? 'descending' : 'ascending';
          const rows = Array.from(body.rows).sort((a, b) =>
            a.innerText.localeCompare(b.innerText)
          );
          if (next === 'descending') rows.reverse();
          rows.forEach(row => body.appendChild(row));
          header.setAttribute('aria-sort', next);
        };
      </script>
    """)
    passed = session.verify_table_sort_roundtrip_semantic(
        "Name", "ascending", "Assets",
    )
    assert passed["sort_roundtrip_passed"] is True, passed
    assert passed["initial_sort"] == "descending", passed
    assert passed["observed_sort"] == "ascending", passed
    assert passed["rows_follow_requested_order"] is True, passed
    assert passed["restored_sort"] == "descending", passed
    assert passed["initial_sort_restored"] is True, passed
    assert classify_tool_action(
        "browser_verify_table_sort_roundtrip_semantic", {},
    ) == "interact"
    assert _core_observation_call_key(
        "browser_verify_table_sort_roundtrip_semantic",
        {"column": "Name", "direction": "Ascending"},
    ) == (
        "browser_verify_table_sort_roundtrip_semantic", "name", "ascending",
    )

    unchanged = session.verify_table_sort_roundtrip_semantic(
        "Name", "descending", "Assets",
    )
    assert unchanged["error"] == "requested_sort_already_initial", unchanged
    assert unchanged["executed"] is False, unchanged

    invalid = session.verify_table_sort_roundtrip_semantic(
        "Name", "sideways", "Assets",
    )
    assert invalid["error"] == "unsupported_sort_direction", invalid
finally:
    session.close()

print("table sort roundtrip smoke: PASS")
