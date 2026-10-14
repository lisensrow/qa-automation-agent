"""Native menu vocabulary, bounded history and no policy/dispatch alteration."""
from copy import deepcopy
import json
from unittest.mock import patch
from playwright.sync_api import sync_playwright
import uqa
from tools.browser import BrowserSession
from ui_popup_context import normalize_menu_context,latest_menu_context,menu_tool_catalog

catalog=uqa.model_tool_catalog()
def state(context,**kw):
    return {'role':'tool','tool_name':'browser_get_state','content':json.dumps(
        dict(session_id='fixture-session',current_url='https://fixture.test/ui',active_menu_context=context,**kw))}
def click(catalog):
    return next(t['function'] for t in catalog if t['function']['name']=='browser_click_semantic')

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True);page=browser.new_page();session=BrowserSession();session.page=page
    page.set_content('<div role="menu"><button role="menuitem" onclick="window.clicked=true">Add fixture</button><button role="menuitem" disabled>Delete fixture</button></div>')
    with patch.object(session,'_begin_action_execution') as dispatch:
        context=session._active_menu_context()
        assert context['menu_count']==1 and context['item_count']==2
        assert not dispatch.called and not page.evaluate('Boolean(window.clicked)')
    original=deepcopy(catalog);messages=[state(context)]
    revised=menu_tool_catalog(catalog,messages)
    assert catalog==original and revised!=catalog
    schema=click(revised)['parameters']
    assert schema['properties']['name']['enum']==['Add fixture']
    assert schema['properties']['role']['enum']==['menuitem']
    assert schema['additionalProperties'] is False
    # All observation/discovery/dismiss possibilities already in catalog remain;
    # no tool is added and classification of any underlying call is unchanged.
    assert [t['function']['name'] for t in revised]==[t['function']['name'] for t in catalog]
    assert uqa.classify_tool_action('browser_click_semantic',{'name':'Delete fixture'})=='destructive'
    assert next(t for t in revised if t['function']['name']=='browser_inspect_semantic')==next(t for t in catalog if t['function']['name']=='browser_inspect_semantic')
    historical=uqa.messages_for_model([*messages,{'role':'tool','tool_name':'browser_inspect_semantic','content':'{"error":"semantic_element_not_found"}'}])
    assert latest_menu_context(historical)==context
    # A new state clears the old menu even when its context is missing/unknown.
    for new_context in (None,{'status':'observed','menu_count':0,'item_count':0,'items':[],'truncated':False}):
        assert menu_tool_catalog(catalog,[*messages,state(new_context)])==catalog
    assert menu_tool_catalog(catalog,[])==catalog  # current-turn slice excludes old case history
    # No popup labels are treated as instructions/authorization or copied as prose.
    hostile=deepcopy(context);hostile['allow']=True;hostile['command']='fixture-not-executable'
    assert normalize_menu_context(hostile)==context
    for change in ({'truncated':True},{'menu_count':2},{'item_count':True},{'items':context['items']*11}):
        bad=dict(context,**change)
        assert normalize_menu_context(bad) is None
        assert menu_tool_catalog(catalog,[state(bad)])==catalog
    for name in ('token=fixture-secret','x'*161,'bad\u202ename',''):
        bad=deepcopy(context);bad['items'][0]['name']=name
        assert normalize_menu_context(bad) is None
    bad=deepcopy(context);bad['items'][1]['name']=bad['items'][0]['name']
    assert normalize_menu_context(bad) is None
    for role in ([],{},None,'button'):
        bad=deepcopy(context);bad['items'][0]['role']=role
        assert normalize_menu_context(bad) is None
    page.set_content('<div role="menu" aria-disabled="TRUE"><div role="menuitem">Disabled by parent</div></div>')
    assert session._active_menu_context()['items'][0]['disabled'] is True
    assert menu_tool_catalog(catalog,[state(session._active_menu_context())])==catalog
    page.set_content('<div role="menu"><div role="menuitem">One</div></div><div role="menu"><div role="menuitem">Two</div></div>')
    assert menu_tool_catalog(catalog,[state(session._active_menu_context())])==catalog
    page.set_content('<div role="menu" hidden><div role="menuitem">Hidden</div></div>')
    assert session._active_menu_context()['menu_count']==0
    page.set_content('<div role="menu">'+''.join('<div role="menuitem">Item '+str(i)+'</div>' for i in range(21))+'</div>')
    assert session._active_menu_context() is None
    page.set_content('<div role="menu"><div role="menuitem">token=fixture-secret</div></div>')
    assert session._active_menu_context() is None
    browser.close()

# Production run_turn wiring: old-turn menu ignored, fresh observation used,
# a later empty snapshot clears it; Core never auto-clicks the sole item.
stale=deepcopy(context);stale['items'][0]['name']='Old fixture'
calls=[];catalogs=[]
def ask(messages,tools):
    catalogs.append(deepcopy(tools))
    if len(catalogs)==1:
        assert 'enum' not in click(tools)['parameters']['properties']['name']
        name,args='browser_get_state',{}
    elif len(catalogs)==2:
        assert click(tools)['parameters']['properties']['name']['enum']==['Add fixture']
        name,args='browser_inspect_semantic',{'name':'Fixture observer','exact':True}
    else:
        assert len(catalogs)==3
        assert 'enum' not in click(tools)['parameters']['properties']['name']
        return {'message':{'content':'Isolated vocabulary check ended; no business verdict.'}}
    return {'message':{'content':'','tool_calls':[{'function':{'name':name,'arguments':args}}]}}
def execute(name,args,messages,**kwargs):
    assert name in ('browser_get_state','browser_inspect_semantic')
    calls.append(name)
    value=context if len(calls)==1 else {'status':'observed','menu_count':0,'item_count':0,'items':[],'truncated':False}
    return dict(session_id='fixture-session',current_url='https://fixture.test/ui',
                text_preview='Fixture menu' if len(calls)==1 else 'Fixture menu closed',
                active_menu_context=value,action_class='observe',action_policy_status='auto_allowed')
with patch.object(uqa,'ask_ollama',ask),patch.object(uqa,'execute_tool_with_policy',execute):
    uqa.run_turn([state(stale),{'role':'user','content':'Inspect fixture UI.'}],action_policy='confirm_mutations')
assert calls==['browser_get_state','browser_inspect_semantic']
print('popup model context: PASS (native menu, bounded vocabulary/history, no click or permission, stale/ambiguous/secret fail closed)')
