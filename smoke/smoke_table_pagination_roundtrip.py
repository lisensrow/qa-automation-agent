from tools.browser import BrowserSession
from uqa import _core_observation_call_key, classify_tool_action


session = BrowserSession()
try:
    session._ensure_started()
    session.page.set_content("""
      <section>
        <div id="range">1-2 of 4</div>
        <table aria-label="Assets" data-total-count="4">
          <thead><tr><th>Name</th></tr></thead>
          <tbody><tr><td>Alpha</td></tr><tr><td>Beta</td></tr></tbody>
        </table>
        <button id="previous">Previous Page</button>
        <button id="page1" aria-current="page">1</button>
        <button id="page2">2</button>
        <button id="next">Next Page</button>
      </section>
      <script>
        const body = document.querySelector('tbody');
        const range = document.querySelector('#range');
        const page1 = document.querySelector('#page1');
        const page2 = document.querySelector('#page2');
        const render = page => {
          body.innerHTML = page === 1
            ? '<tr><td>Alpha</td></tr><tr><td>Beta</td></tr>'
            : '<tr><td>Gamma</td></tr><tr><td>Delta</td></tr>';
          range.innerText = page === 1 ? '1-2 of 4' : '3-4 of 4';
          if (page === 1) {
            page1.setAttribute('aria-current', 'page');
            page2.removeAttribute('aria-current');
          } else {
            page2.setAttribute('aria-current', 'page');
            page1.removeAttribute('aria-current');
          }
        };
        document.querySelector('#next').onclick = () => render(2);
        document.querySelector('#previous').onclick = () => render(1);
      </script>
    """)
    passed = session.verify_table_pagination_roundtrip_semantic(
        "Next Page", "Previous Page", "Assets",
    )
    assert passed["pagination_roundtrip_passed"] is True, passed
    assert passed["initial_page"] == 1, passed
    assert passed["adjacent_page"] == 2, passed
    assert passed["restored_page"] == 1, passed
    assert passed["visible_range_consistent"] is True, passed
    assert passed["initial_page_restored"] is True, passed
    assert passed["selection_ledger_used_as_product_evidence"] is False, passed
    assert classify_tool_action(
        "browser_verify_table_pagination_roundtrip_semantic", {},
    ) == "interact"
    assert _core_observation_call_key(
        "browser_verify_table_pagination_roundtrip_semantic",
        {"forward_control": "Next Page", "return_control": "Previous Page"},
    ) == (
        "browser_verify_table_pagination_roundtrip_semantic",
        "next page", "previous page",
    )

    session.page.locator("#next").evaluate(
        "el => el.setAttribute('disabled', '')"
    )
    blocked = session.verify_table_pagination_roundtrip_semantic(
        "Next Page", "Previous Page", "Assets",
    )
    assert blocked["observation_result"] == "BLOCKED", blocked
    assert blocked["error"] == "table_page_control_disabled", blocked
    assert blocked["executed"] is False, blocked

    invalid = session.verify_table_pagination_roundtrip_semantic(
        "Next Page", "Next Page", "Assets",
    )
    assert invalid["error"] == "pagination_controls_must_differ", invalid
finally:
    session.close()

print("table pagination roundtrip smoke: PASS")
