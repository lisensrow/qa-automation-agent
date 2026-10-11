from tools.browser import BrowserSession
from uqa import _core_observation_call_key, classify_tool_action


def install_fixture(session, with_total=True):
    total = ' data-total-count="3"' if with_total else ""
    session.page.set_content(f"""
      <label>Search by name <input type="search" aria-label="Search by name"></label>
      <table aria-label="Assets"{total}>
        <thead><tr><th>Name</th><th>OS</th></tr></thead>
        <tbody>
          <tr><td>Alpha</td><td>Linux</td></tr>
          <tr><td>Alpine</td><td>Linux</td></tr>
          <tr><td>Beta</td><td>Windows</td></tr>
        </tbody>
      </table>
      <script>
        const input = document.querySelector('input');
        input.addEventListener('input', () => {{
          const wanted = input.value.toLowerCase();
          document.querySelectorAll('tbody tr').forEach(row => {{
            row.style.display = row.cells[0].innerText.toLowerCase().includes(wanted)
              ? '' : 'none';
          }});
        }});
      </script>
    """)


session = BrowserSession()
try:
    session._ensure_started()
    install_fixture(session)
    passed = session.verify_table_text_filter_roundtrip_semantic(
        "Search by name", "Al", "Name", "Assets",
    )
    assert passed["filter_roundtrip_passed"] is True, passed
    assert passed["visible_row_count"] == 2, passed
    assert passed["visible_rows_match_filter"] is True, passed
    assert passed["reported_total_present"] is True, passed
    assert passed["filter_restored"] is True, passed
    assert session.page.get_by_role(
        "searchbox", name="Search by name", exact=True,
    ).input_value() == ""
    assert classify_tool_action(
        "browser_verify_table_text_filter_roundtrip_semantic", {},
    ) == "interact"
    assert _core_observation_call_key(
        "browser_verify_table_text_filter_roundtrip_semantic",
        {"filter_name": "Search by name", "value": "Al", "column": "Name"},
    ) == (
        "browser_verify_table_text_filter_roundtrip_semantic",
        "search by name", "al", "name",
    )

    install_fixture(session, with_total=False)
    blocked = session.verify_table_text_filter_roundtrip_semantic(
        "Search by name", "Al", "Name", "Assets",
    )
    assert blocked["observation_result"] == "BLOCKED", blocked
    assert blocked["reported_total_present"] is False, blocked
    assert blocked["filter_restored"] is True, blocked

    session.page.set_content("""
      <input type="search" aria-label="Search">
      <input type="search" aria-label="Search">
      <table><thead><tr><th>Name</th></tr></thead><tbody><tr><td>A</td></tr></tbody></table>
    """)
    duplicate = session.verify_table_text_filter_roundtrip_semantic(
        "Search", "A", "Name",
    )
    assert duplicate["error"] == "table_filter_control_not_unique", duplicate
finally:
    session.close()

print("table filter roundtrip smoke: PASS")
