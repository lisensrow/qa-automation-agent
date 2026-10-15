"""No product calls: one source-rechecked panel + unique native tab + fresh inspection."""
from copy import deepcopy
import json
from unittest.mock import patch
import uqa
from control_location_recovery import candidate_for_missing_field

hint={'status':'candidate_location_hint','requested_control_label':'Name','document_panel_name':'Settings',
      'source_refs':[{'source_id':'fixture-guide','sha256':'a'*64,'document_revision':'fixture-rev'}],
      'evidence_for_pass':False,'current_runtime_applicability_verified':False}
state={'session_id':'s1','current_url':'https://fixture.test/items/new/form',
       'navigation_labels':['Settings'], 'interactive_elements':[
           {'tag':'button','role':'tab','text':'Settings','enabled':True},
           {'tag':'a','role':'','text':'Settings','enabled':True}]}
assert candidate_for_missing_field(hint,state)['arguments']=={'name':'Settings','role':'tab','exact':True}
for change in ('duplicate','disabled','selected','missing_session','no_labels','duplicate_labels'):
    bad=deepcopy(state)
    if change=='duplicate':bad['interactive_elements'].append(bad['interactive_elements'][0])
    elif change=='disabled':bad['interactive_elements'][0]['enabled']=False
    elif change=='selected':bad['interactive_elements'][0]['selected']=True
    elif change=='missing_session':bad.pop('session_id')
    elif change=='no_labels':bad['navigation_labels']=[]
    else:bad['navigation_labels']*=2
    assert candidate_for_missing_field(hint,bad) is None
bad=deepcopy(hint);bad['source_refs']=[]
assert candidate_for_missing_field(bad,state) is None

def exercise(*, inspection_changes=None, profile='write_ui_state', policy='confirm_mutations',
             force=False, error='Field not found: Name', action_class=None):
    job={'status':'running','job_type':'manual','request':'Create a new collection',
         'test_cases':[{'case_id':'fixture-case','status':'running','requirement':{'action_profile':profile}}]}
    messages=[{'role':'user','content':job['request']},
              {'role':'tool','tool_name':'browser_get_state','content':json.dumps(state)}]
    inspection={**state,'visible':True,'enabled':True,'selected':False,'semantic_strategy':'role:tab',
                'requested_role':'tab','role_constraint_matched':True,'element':{'role':'tab'}}
    inspection.update(inspection_changes or {})
    click={**state,'current_url':'https://fixture.test/items/new/settings','click_status':'executed'}
    attempts=set()
    with patch.object(uqa,'get_job',return_value=job), \
         patch('product_knowledge_context.retrieve_control_location_hint',return_value=hint), \
         patch.object(uqa,'execute_tool_with_policy',side_effect=[inspection,click]) as invoke, \
         patch.object(uqa,'record_tool_observations',return_value=[]), \
         patch.object(uqa,'record_tool_evidence',return_value={'evidence_id':'ev-fixture'}), \
         patch.object(uqa,'classify_tool_action',wraps=uqa.classify_tool_action) as classify:
        if action_class is not None:classify.side_effect=None;classify.return_value=action_class
        result=uqa.recover_missing_field_panel('browser_fill_semantic',{'field':'Name'}, {'error':error},
            messages,attempts,'fixture-job','fixture-case',policy,force)
        count=invoke.call_count
        for call in invoke.call_args_list:
            assert call.kwargs['action_policy']==policy and call.kwargs['require_compatibility_probe'] is True
            assert call.args[0] in {'browser_inspect_semantic','browser_click_semantic'}
        # Same stale source URL/session/field must never replay a recovery.
        if count==2:
            repeat_messages=[{'role':'tool','tool_name':'browser_get_state','content':json.dumps(state)}]
            assert uqa.recover_missing_field_panel('browser_fill_semantic',{'field':'Name'},{'error':error},
                repeat_messages,attempts,'fixture-job','fixture-case',policy,force) is None
            assert invoke.call_count==count
        return result,count,messages

result,count,messages=exercise()
assert count==2 and result['click_status']=='executed'
assert exercise(inspection_changes={'semantic_strategy':'explicit_role_text:tab'})[1]==2
assert all(json.loads(m['content'])['core_navigation_recovery']['model_selected_action'] is False
           for m in messages if m.get('role')=='tool' and m.get('tool_name') in {'browser_click_semantic','browser_inspect_semantic'})
for changes in ({'selected':True},{'selected':None},{'visible':False},{'enabled':False},
                {'semantic_strategy':'text'},{'session_id':'other'},
                {'current_url':'https://other.test/items/new/form'},{'error':'unavailable'},
                {'requested_role':'link'},{'role_constraint_matched':False},{'element':{'role':'link'}}):
    assert exercise(inspection_changes=changes)[1]==1
for kwargs in ({'profile':'read_only'},{'policy':'legacy'},{'force':True},
               {'error':'Option not found: item'},{'action_class':'write'}):
    assert exercise(**kwargs)[1]==0
print('PASS field-panel recovery: unique native tab, fresh deselected same-session inspection, one INTERACT via policy, no fill/save/permission grant')
