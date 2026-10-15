"""Native drag/table fixture and fail-closed composite; no UC access."""
from copy import deepcopy
from unittest.mock import patch
from playwright.sync_api import sync_playwright
from tools.browser import BrowserSession
from tools.tree_row_controls import add_tree_row, validate
import uqa
import tempfile
from pathlib import Path
from product_knowledge_context import reviewed_tool_schema_hints

args = dict(source='Attribute A', target='And', parents=['Common'],
            cells=[{'column':'Operator','action':'select','value':'Wildcard'},
                   {'column':'Value','action':'fill','value':'*test*'}],
            session_id='fixture-session', current_url='https://fixture.test/new')
assert validate(**args)
for change in ({'cells':[]}, {'parents':['Common','Common']}, {'parents':['Attribute A']},
               {'cells':[dict(args['cells'][0],action='click')]}, {'session_id':''},
               {'cells':args['cells']*2}, {'source':'And'}):
    assert not validate(**{**args, **change})

HTML = '''<button onclick="window.saved++">Save</button><script>window.saved=0</script>
<ul role="tree"><li role="treeitem" aria-label="Common" aria-expanded="false" tabindex="0"
 onkeydown="if(event.key==='ArrowRight'){this.setAttribute('aria-expanded','true');document.querySelector('#leaf').hidden=false}">Common</li>
<li id="leaf" role="treeitem" aria-expanded="false" hidden draggable="true" ondragstart="event.dataTransfer.setData('text/plain','leaf')">Attribute A</li></ul>
<div style="width:200px;height:70px;border:1px solid" ondragover="event.preventDefault()"
 ondrop="event.preventDefault();document.querySelector('tbody').innerHTML='<tr><td>Attribute A</td><td><select><option>Equal</option><option>Wildcard</option></select></td><td><input></td></tr>'">And</div>
<table><thead><tr><th>Attribute</th><th>Operator</th><th>Value</th></tr></thead><tbody></tbody></table>'''

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True); page=browser.new_page()
    session=BrowserSession.__new__(BrowserSession); session.page=page
    session._ensure_started=lambda:None; session._reset_diagnostics=lambda:None
    session._begin_action_execution=lambda:None
    session._finish_action_execution=lambda result:result
    session._capture_state=lambda action:{'session_id':args['session_id'],'current_url':args['current_url']}
    page.set_content(HTML)
    result=add_tree_row(session,**args)
    assert result.get('tree_row_status')=='applied', result.get('error')
    assert page.locator('input').input_value()=='*test*'
    assert page.locator('select').input_value()=='Wildcard'
    assert page.evaluate('saved')==0
    assert not result['automatic_retry_allowed'] and not result['saved_filter_verified']
    assert add_tree_row(session,**args)['error']=='tree_row_label_already_present'
    page.set_content(HTML)
    assert add_tree_row(session,**{**args,'session_id':'other'})['error']=='tree_row_binding_changed'
    assert page.locator('tbody tr').count()==0
    page.set_content(HTML)
    with patch('tools.tree_row_controls.operate',return_value={'error':'ambiguous_cell_control'}):
        result=add_tree_row(session,**args)
        assert result['tree_row_status']=='partial' and result['error']=='tree_row_cell_unavailable'
        assert page.locator('input').input_value()==''
    page.set_content(HTML)
    with patch.object(session,'drag_semantic',side_effect=RuntimeError('private exception')):
        result=add_tree_row(session,**args)
        assert result['tree_row_status']=='uncertain' and result['executed'] is None
        assert 'private exception' not in str(result)
    page.set_content(HTML)
    bad=deepcopy(args);bad['cells'][0]['value']='Absent option'
    result=add_tree_row(session,**bad)
    assert result['tree_row_status']=='partial' and result['error']=='tree_row_cell_not_verified'
    assert page.locator('input').input_value()=='' and page.evaluate('saved')==0
    browser.close()

name='browser_add_tree_row_semantic'
assert uqa.classify_tool_action(name,args)=='write'
for strict in (False,True):
    assert uqa.tool_policy_check(name,args,[{'role':'user','content':'Read only. Do not change anything.'}],force_read_only=strict)['status']=='blocked_by_policy'
with tempfile.TemporaryDirectory() as directory:
    root=Path(directory); (root/'UQA-experience').mkdir()
    source=root/'UQA-experience/UQA_COLLECTIONS_KNOWLEDGE.md'
    actual=Path('/opt/uqa/knowledge/source/UQA-experience/UQA_COLLECTIONS_KNOWLEDGE.md').read_bytes()
    source.write_bytes(actual)
    assert reviewed_tool_schema_hints('Создай новую коллекцию с условиями',root)=={name}
    assert reviewed_tool_schema_hints('Прочитай существующую коллекцию',root)==set()
    assert reviewed_tool_schema_hints('Создай политику',root)==set()
    source.write_bytes(actual+b'\nchanged')
    assert reviewed_tool_schema_hints('Создай новую коллекцию',root)==set()
    assert name in {t['function']['name'] for t in uqa.model_tool_catalog({name})}
print('PASS tree-row controls: native expansion/leaf/drag/exact cells; existing row, binding, partial/uncertain, no save or retry, v069 preserved')
