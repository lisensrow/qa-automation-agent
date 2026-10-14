"""Local DOM only: reject table checkboxes and preserve real ambiguity."""
from tools.browser import BrowserSession

s = BrowserSession()
try:
    s._ensure_started()
    s.page.set_content('''
      <table><thead><tr><th><input type="checkbox"></th>
      <th><div><span>Name</span></div></th></tr></thead></table>
      <form><div><div>Name</div><input type="text"></div>
      <div><div>Group</div><input type="text" role="combobox"></div></form>
    ''')
    found = s._visible_nearby_labeled_field_matches('Name', True)
    assert len(found) == 1
    assert found[0].get_attribute('type') == 'text'
    result = s.fill_semantic('Name', 'fixture-only', exact=True)
    assert not result.get('error'), result.get('error')
    assert s.page.locator('input[type=text]').nth(0).input_value() == 'fixture-only'
    assert s.page.locator('[role=combobox]').input_value() == ''
    assert not s.page.locator('input[type=checkbox]').is_checked()

    # Identical unnamed inputs are different controls, not duplicate markup.
    s.page.set_content('<div><div>Name</div><input></div>' * 2)
    assert len(s._visible_nearby_labeled_field_matches('Name', True)) == 2
    result = s.fill_semantic('Name', 'must-not-write', exact=True)
    assert result.get('error', '').startswith('Ambiguous nearby field label:')
    assert s.page.locator('input').evaluate_all('(xs)=>xs.every(x=>x.value==="")')

    # Nested copies of the same visible label still identify one control.
    s.page.set_content('<div><div><span>Name</span></div><input></div>')
    assert len(s._visible_nearby_labeled_field_matches('Name', True)) == 1
    s.page.set_content('<div hidden><div>Name</div><input></div><div><div>Name</div><input></div>')
    assert len(s._visible_nearby_labeled_field_matches('Name', True)) == 1
    print('PASS nearby field identity: table checkbox, untouched sibling, real ambiguity, nested/hidden labels')
finally:
    s.close()
