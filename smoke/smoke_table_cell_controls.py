"""Actual Playwright fixture page, no UC connection or product mutation."""
from playwright.sync_api import sync_playwright
from tools.table_cell_controls import operate
import uqa

class Fixture:
    def __init__(self,page):self.page=page
    def _ensure_started(self):pass
    def _reset_diagnostics(self):pass
    def _begin_action_execution(self):pass
    def _capture_state(self,action):return {'action':action,'fixture':True}

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True);page=browser.new_page();session=Fixture(page)
    page.set_content('''<table><thead><tr><th>Attribute</th><th>Operator</th><th>Value</th></tr></thead><tbody>
    <tr><td>Archived</td><td><select><option>Equal</option><option>Not equal</option></select></td><td><select><option>Yes</option><option>No</option></select></td></tr>
    <tr><td>OS name</td><td><select><option>Equal</option></select></td><td><input value="unchanged"></td></tr>
    </tbody></table>''')
    assert operate(session,'Archived','Value')['cell_control_status']=='observed'
    assert operate(session,'Archived','Value','select','No')['cell_control_status']=='applied'
    assert page.locator('tbody tr').nth(1).locator('input').input_value()=='unchanged'
    assert operate(session,'OS name','Value','fill','Ubuntu')['cell_control_status']=='applied'
    assert page.locator('tbody tr').nth(0).locator('td').nth(2).locator('select').input_value()=='No'
    assert operate(session,'Archived','Value','select','Missing')['error']=='cell_option_absent_or_ambiguous'
    page.evaluate("()=>document.querySelector('tbody').append(document.querySelector('tbody tr').cloneNode(true))")
    assert operate(session,'Archived','Value','select','Yes')['error']=='ambiguous_cell_row'
    page.set_content('<table><tr><th>Value</th></tr><tr><td><span>Secret field</span><input type="password"></td></tr></table>')
    assert operate(session,'Secret field','Value','fill','fixture-secret')['error']=='sensitive_cell_control'
    page.set_content('<table><tr><th colspan="2">Value</th></tr><tr><td>Target</td><td><input></td></tr></table>')
    assert operate(session,'Target','Value','fill','x')['error']=='merged_table_headers_unsupported'
    page.set_content('''<table><tr><th>Attribute</th><th>Value</th></tr><tr><td>OS</td><td>
        <div role="combobox" aria-controls="options" onclick="document.getElementById('options').hidden=false">Windows</div>
        </td></tr></table><ul id="options" role="listbox" hidden><li role="option" onclick="document.querySelector('[role=combobox]').textContent='Ubuntu';this.parentElement.hidden=true">Ubuntu</li></ul>''')
    assert operate(session,'OS','Value','select','Ubuntu')['cell_control_status']=='applied'
    page.set_content('''<aside><span>Archived</span></aside><section><div><div>Attribute</div><div>Operator</div><div>Value</div></div>
        <div><div><span>Archived</span></div><div><select><option>Equal</option></select></div><div><select><option>Yes</option><option>No</option></select></div></div>
        <div><div><span>OS name</span></div><div><select><option>Equal</option></select></div><div><input value="keep"></div></div></section>''')
    assert operate(session,'Archived','Value','select','No')['cell_control_status']=='applied'
    assert page.locator('input').input_value()=='keep'
    page.evaluate("()=>{const r=document.querySelector('section').children[1];r.prepend(document.createElement('button'));r.append(document.createElement('div'));}")
    assert operate(session,'Archived','Value','select','Yes')['cell_control_status']=='applied'
    page.evaluate("()=>document.querySelector('section').append(document.querySelector('section').children[1].cloneNode(true))")
    assert operate(session,'Archived','Value','select','Yes')['error']=='grid_row_absent_or_ambiguous'
    browser.close()
name='browser_table_cell_control_semantic'
assert uqa.classify_tool_action(name,{})=='observe'
assert uqa.classify_tool_action(name,{'action':'fill'})=='write'
assert uqa.classify_tool_action(name,{'action':'unknown'})=='unknown'
for strict in (False,True):
    assert uqa.tool_policy_check(name,{'action':'select'},[{'role':'user','content':'Read only. Do not change anything.'}],force_read_only=strict)['status']=='blocked_by_policy'
    assert uqa.tool_policy_check(name,{'action':'inspect'},[{'role':'user','content':'Read only.'}],force_read_only=strict) is None
print('PASS table cell controls: exact row/column, native and ARIA selection, neighbour untouched, ambiguity/password/merged header denial, v069 read-only preserved')
