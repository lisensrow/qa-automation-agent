"""Read hashes from real fixture controls, no native values leaked or changed."""
import hashlib
from playwright.sync_api import sync_playwright
from tools.grid_value_readback import inspect_values
import uqa

class Fixture:
    def __init__(self,page):self.page=page
    def _ensure_started(self):pass
    def _reset_diagnostics(self):pass
    def _capture_state(self,action):return {'session_id':'fixture','current_url':'https://fixture.test/new'}

cells=[{'row':'Attribute A','column':'Operator'},{'row':'Attribute A','column':'Value'}]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True);page=browser.new_page();session=Fixture(page)
    page.set_content('''<section><div><div>Attribute</div><div>Operator</div><div>Value</div></div>
    <div><div>Attribute A</div><div><span role="combobox">Equal</span></div><div><input value="fixture-only"></div></div></section>''')
    result=inspect_values(session,cells,'fixture','https://fixture.test/new')
    assert result.get('grid_value_status')=='observed',result.get('error')
    assert [c['value_sha256'] for c in result['grid_values']]==[hashlib.sha256(s.encode()).hexdigest() for s in ('Equal','fixture-only')]
    assert 'fixture-only' not in str(result) and result['mutation_executed'] is False
    assert page.locator('input').input_value()=='fixture-only'
    assert inspect_values(session,cells,'wrong','https://fixture.test/new')['error']=='grid_readback_binding_changed'
    assert inspect_values(session,cells*2,'fixture','https://fixture.test/new')['error']=='grid_readback_arguments_invalid'
    page.locator('input').evaluate("e=>e.type='password'")
    assert inspect_values(session,cells,'fixture','https://fixture.test/new')['error']=='grid_readback_sensitive_control'
    page.locator('input').evaluate("e=>e.type='text'")
    page.evaluate("()=>{let e=document.querySelector('section');e.append(e.lastElementChild.cloneNode(true))}")
    assert inspect_values(session,cells,'fixture','https://fixture.test/new')['error']=='grid_readback_cell_absent_or_ambiguous'
    browser.close()
assert uqa.classify_tool_action('browser_inspect_labeled_grid_values_semantic',{})=='observe'
print('PASS labeled-grid readback: exact cells/session/URL, six-cell capable hashes not values, no writes, ambiguity/password/duplicates denied')
