from copy import deepcopy
from frontend_check_contracts import evaluate_contract
from run_uconnect_manual_frontend_benchmark import build_job_spec,load_and_validate_manifest
spec=build_job_spec(load_and_validate_manifest(),'uc-front-003','lab',
                    {'filter_field':'Search by name','filter_value':'fixture-host','filter_column':'Name'})
requirement=spec['case']['requirement']
case={'observations':[],'evidence':[]}
def add(kind,tool,extra):
    oid='obs-'+str(len(case['observations']))
    case['observations'].append({'observation_id':oid,'type':kind,
        'data':dict(tool=tool,url='https://fixture.invalid/cmdb',**extra)})
    case['evidence'].append({'evidence_id':'ev-'+oid,'type':tool,'observation_ids':[oid],'usable_for_verdict':True})
def table(names):
    return {'table_resolution':'unique_visible','table_summary':{
        'snapshot_complete':True,'headers':[{'name':'Name'}],
        'rows':[{'values_by_header':{'Name':n}} for n in names],
        'row_signature':names,'visible_row_count':len(names)}}
add('ui_element','browser_inspect_table_semantic',table(['fixture-host','other-host']))
add('ui_state','browser_fill_semantic',{'input':{'field':'Search by name','text':'fixture-host'},
    'action_execution_id':'action-1','network_window_closed':True})
add('ui_element','browser_inspect_semantic',{'subject':'Search by name','exact':True,'value':'fixture-host'})
add('ui_element','browser_inspect_table_semantic',table(['fixture-host']))
add('ui_state','browser_fill_semantic',{'input':{'field':'Search by name','text':''},
    'action_execution_id':'action-2','network_window_closed':True})
add('ui_element','browser_inspect_semantic',{'subject':'Search by name','exact':True,'value':''})
add('ui_element','browser_inspect_table_semantic',table(['fixture-host','other-host']))
def check(source,number):
    return evaluate_contract(source,requirement,{'check_id':f'planned-{number:03d}','status':'blocked'},'https://fixture.invalid')[0]
assert all(check(case,n)['status']=='passed' for n in range(1,5))
assert check(case,1)['observations']!=check(case,3)['observations']
for index,field,value,number,status in (
    (2,'value','incorrect',1,'failed'),(5,'value','not-cleared',3,'failed'),
    (3,'table_summary',table(['other-host'])['table_summary'],2,'failed'),
    (6,'table_summary',table(['changed-host'])['table_summary'],4,'failed'),
    (3,'url','https://wrong.invalid',2,'blocked'),
):
    altered=deepcopy(case); altered['observations'][index]['data'][field]=value
    assert check(altered,number)['status']==status
altered=deepcopy(case); altered['observations'][3]['data']['table_summary']['snapshot_complete']=False
assert check(altered,2)['status']=='blocked'
altered=deepcopy(case); altered['evidence'][1]['usable_for_verdict']=False
assert check(altered,1)['status']=='blocked'
assert evaluate_contract(case,requirement,{'check_id':'planned-001','status':'passed'},None)[0]['status']=='blocked'
altered=deepcopy(case); altered['observations'][3]['data']['table_resolution']='named'
assert check(altered,2)['status']=='blocked'
altered=deepcopy(case); altered['observations'][0]['data']['table_summary'].pop('row_signature')
assert check(altered,4)['status']=='blocked'
altered=deepcopy(case); altered['observations'][1]['data']['network_window_closed']=False
assert check(altered,1)['status']=='blocked'

from playwright.sync_api import sync_playwright
from tools.browser import BrowserSession
with sync_playwright() as runtime:
    browser=runtime.chromium.launch(headless=True,args=['--no-sandbox'])
    try:
        page=browser.new_page()
        page.set_content('<table><thead><tr><th>Name</th></tr></thead><tbody><tr><td>fixture-host</td></tr></tbody></table>')
        assert BrowserSession._table_snapshot(page.locator('table'))['snapshot_complete'] is True
        page.set_content('<table><tbody>'+ '<tr><td>fixture</td></tr>'*201+'</tbody></table>')
        assert BrowserSession._table_snapshot(page.locator('table'))['snapshot_complete'] is False
        page.set_content('<table><tbody><tr><td>'+ 'x'*301+'</td></tr></tbody></table>')
        assert BrowserSession._table_snapshot(page.locator('table'))['snapshot_complete'] is False
    finally:
        browser.close()
print('search phase contracts: PASS (real DOM bounds, wrong phase/value/origin/evidence rejected)')

from observation_extractor import extract_observations
observed=extract_observations('knowledge_search',{'query':'Name'},
    {'status':'ok','result_count':0,'results':[],
     'product_memory':{'status':'ok','results':[{'fact_key':'fixture-fact','data':{'secret':'private-fixture-only'}}]}})
assert observed[0]['data']['product_memory_summary']['loaded_fact_count']==1
assert observed[0]['data']['product_memory_summary']['evidence_for_pass'] is False
assert 'private-fixture-only' not in str(observed)
