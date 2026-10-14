"""Full phase proof, not model words/counts; no live stand action."""
from copy import deepcopy
from frontend_check_contracts import evaluate_contract
url='https://fixture.test/'
row={'index':0,'tag':'input','type':'text','label_hint':'Field','native_required':False,
     'native_disabled':False,'native_read_only':False,'native_will_validate':True,
     'in_viewport':True,'aria_hidden':False,'inert':False}
def snapshot(i,rows):
    return {'observation_id':f'obs-{i}','type':'ui_contract_audit','data':{
        'tool':'browser_inspect_form_validation_semantic','session_id':'session','url':url,
        'observation_result':'observed','mutation_executed':False,'scope_kind':'page',
        'control_states_reported':True,'control_geometry_reported':True,
        'audit':{'visible_control_count':len(rows),'truncated':False},'control_states':deepcopy(rows)}}
def action(i,tool,args):
    return {'observation_id':f'obs-{i}','type':'ui_state','data':{
        'tool':tool,'input':args,'session_id':'session','url':url,
        'action_execution_id':f'ax-{i}','network_window_closed':True}}
case={'observations':[snapshot(1,[]),action(2,'browser_click_semantic',{'name':'fixture-trigger'}),
      snapshot(3,[row]),action(4,'browser_press_key_semantic',{'key':'Escape'}),snapshot(5,[])]}
case['evidence']=[{'evidence_id':f'ev-{i}','type':o['data']['tool'],'observation_ids':[o['observation_id']],
                  'usable_for_verdict':True} for i,o in enumerate(case['observations'])]
req={'locked':True,'bindings':{'trigger':'fixture-trigger','close':'Escape'},'check_contracts':{
    'opened':{'tool':'browser_inspect_form_validation_semantic','subject_binding':'trigger',
        'close_key_binding':'close','phase':'opened','assertions':[{'field':'form_controls_opened','operator':'eq','expected':True}]},
    'closed':{'tool':'browser_inspect_form_validation_semantic','subject_binding':'trigger',
        'close_key_binding':'close','phase':'restored','assertions':[{'field':'form_controls_restored','operator':'eq','expected':True},
            {'field':'no_input_submit_execution','operator':'eq','expected':True}]}}}
for key in ('opened','closed'):
    computed,error=evaluate_contract(case,req,{'check_id':key,'status':'passed'},url)
    assert error is None and computed['status']=='passed'
for mutation in ('no_close','no_baseline','no_closed_read','changed_session','wrong_origin','unusable','no_geometry','same_visible_set', 'invalid_tag', 'bool_count', 'missing_observation_id'):
    bad=deepcopy(case)
    if mutation=='no_close':bad['observations'].pop(3)
    elif mutation=='no_baseline':bad['observations'].pop(0)
    elif mutation=='no_closed_read':bad['observations'].pop()
    elif mutation=='changed_session':bad['observations'][2]['data']['session_id']='other'
    elif mutation=='wrong_origin':bad['observations'][2]['data']['url']='https://other.test/'
    elif mutation=='unusable':bad['evidence'][2]['usable_for_verdict']=False
    elif mutation=='no_geometry':bad['observations'][2]['data']['control_geometry_reported']=False
    elif mutation=='same_visible_set':bad['observations'][0]=snapshot(1,[row])
    elif mutation=='invalid_tag':bad['observations'][2]['data']['control_states'][0]['tag']='div'
    elif mutation=='bool_count':bad['observations'][2]['data']['audit']['visible_control_count']=True
    elif mutation=='missing_observation_id':bad['observations'][2]['observation_id']=None
    computed,error=evaluate_contract(bad,req,{'check_id':'closed','status':'passed'},url)
    assert computed['status']=='blocked' and error,mutation
bad=deepcopy(case);bad['observations'][-1]=snapshot(5,[row])
computed,error=evaluate_contract(bad,req,{'check_id':'closed','status':'passed'},url)
assert error is None and computed['status']=='failed'
bad=deepcopy(case)
extra=action(6,'browser_fill_semantic',{'name':'Field','text':'fixture-only'})
bad['observations'].insert(3,extra)
bad['evidence'].append({'evidence_id':'ev-extra','type':'browser_fill_semantic',
    'observation_ids':['obs-6'],'usable_for_verdict':True})
computed,error=evaluate_contract(bad,req,{'check_id':'closed','status':'passed'},url)
assert error is None and computed['status']=='failed'
from frontend_check_contracts import validate_contracts
bad_contracts=deepcopy(req['check_contracts']);bad_contracts['opened']['phase']='restored'
try:
    validate_contracts(bad_contracts)
except ValueError as exc:
    assert str(exc)=='frontend_contract_form_field_phase_invalid'
else:
    raise AssertionError('wrong phase accepted')
print('form lifecycle contract: PASS (phase actions, geometry, same episode, evidence; absent close BLOCKED)')

from form_lifecycle_contracts import needs_form_baseline
baseline_case = {'case_id':'case-1','status':'running','requirement':dict(req,
    type='frontend_contracts', action_profile='write_ui_state'),
    'planned_checks':[{'check_id':key} for key in req['check_contracts']],
    'observations':[action(0,'browser_open_page',{'url':url})],
    'evidence':[{'evidence_id':'ev-page','type':'browser_open_page',
                 'observation_ids':['obs-0'],'usable_for_verdict':True}]}
baseline_case['observations'][0]['data']['http_status']=200
baseline_case['observations'][0]['data']['action_execution_id']=None
baseline_case['observations'][0]['data']['network_window_closed']=None
baseline_job={'job_type':'regression','status':'running','test_cases':[baseline_case]}
assert needs_form_baseline(baseline_job,'case-1',url)
for mutation in ('opened','already_read','unlocked','coverage','wrong_origin','unusable','http_error','wrong_session','not_running'):
    bad=deepcopy(baseline_job); c=bad['test_cases'][0]
    if mutation=='opened':c['observations'].append(action(2,'browser_click_semantic',{'name':'fixture-trigger'}))
    elif mutation=='already_read':c['observations'].append(snapshot(1,[]))
    elif mutation=='unlocked':c['requirement']['locked']=False
    elif mutation=='coverage':c['planned_checks'].pop()
    elif mutation=='wrong_origin':c['observations'][0]['data']['url']='https://other.test/'
    elif mutation=='unusable':c['evidence'][0]['usable_for_verdict']=False
    elif mutation=='http_error':c['observations'][0]['data']['http_status']=500
    elif mutation=='wrong_session':c['observations'][0]['data']['session_id']=None
    elif mutation=='not_running':c['status']='blocked'
    assert not needs_form_baseline(bad,'case-1',url),mutation
assert not needs_form_baseline(None,'case-1',url)
print('form baseline gate: PASS (declared coverage, trusted page, before action, single observation)')

import uqa
from unittest.mock import patch
assert uqa.locked_form_support_tools(baseline_job,'case-1') == {'browser_press_key_semantic'}
assert 'browser_press_key_semantic' in {t['function']['name'] for t in uqa.model_tool_catalog(
    uqa.locked_form_support_tools(baseline_job,'case-1'))}
bad=deepcopy(baseline_job);bad['test_cases'][0]['requirement']['locked']=False
assert not uqa.locked_form_support_tools(bad,'case-1')
bad=deepcopy(baseline_job);bad['test_cases'][0]['requirement']['bindings']['close']='Enter'
assert not uqa.locked_form_support_tools(bad,'case-1')
assert not uqa.locked_form_support_tools({},'case-1')
advisory_job=deepcopy(baseline_job)
advisory_case=advisory_job['test_cases'][0]
advisory_case['observations']=deepcopy(case['observations'][:3])
advisory_case['evidence']=deepcopy(case['evidence'][:3])
before=deepcopy(advisory_job)
with patch.object(uqa,'get_stand',return_value={'web_url':url}):
    message=uqa.incomplete_form_phase_message(advisory_job,'case-1')
    assert message and 'Escape' in message['content'] and 'authorizes nothing' in message['content']
    assert advisory_job==before
    advisory_case['observations']=deepcopy(case['observations'])
    advisory_case['evidence']=deepcopy(case['evidence'])
    assert uqa.incomplete_form_phase_message(advisory_job,'case-1') is None
    assert len(uqa.completed_readonly_contract_checks(advisory_job,'case-1'))==2
    advisory_case['observations'].pop(0)
    assert uqa.incomplete_form_phase_message(advisory_job,'case-1') is None
print('form phase advisory: PASS (verified opening only, no execution, computed completion)')

import json
sequence_req=deepcopy(req)
sequence_req['bindings']['opening']=json.dumps(['fixture-menu','fixture-trigger'])
for contract in sequence_req['check_contracts'].values():
    contract['opening_sequence_binding']='opening'
sequence_case=deepcopy(case)
sequence_case['observations'].insert(1,action(7,'browser_click_semantic',{'name':'fixture-menu'}))
sequence_case['evidence'].append({'evidence_id':'ev-menu','type':'browser_click_semantic',
    'observation_ids':['obs-7'],'usable_for_verdict':True})
for key in ('opened','closed'):
    check,error=evaluate_contract(sequence_case,sequence_req,{'check_id':key,'status':'blocked'},url)
    assert error is None and check['status']=='passed'
bad=deepcopy(sequence_case);bad['observations'].pop(1)
check,error=evaluate_contract(bad,sequence_req,{'check_id':'closed','status':'passed'},url)
assert error=='form_contract_opening_sequence_unproven' and check['status']=='blocked'
bad=deepcopy(sequence_case);bad['evidence'][-1]['usable_for_verdict']=False
check,error=evaluate_contract(bad,sequence_req,{'check_id':'closed','status':'passed'},url)
assert error=='form_contract_evidence_unusable' and check['status']=='blocked'
print('form opening sequence: PASS (bound sequence, provenance, no extra action acceptance)')
