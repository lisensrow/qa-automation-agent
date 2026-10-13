"""Only verified filtering plus an unattempted locked restoration yields an advisory."""
from copy import deepcopy
from unittest.mock import patch
import uqa
import frontend_check_contracts as contracts
job = {'job_type':'regression','status':'running','stand':'fixture','test_cases':[{
    'case_id':'case','status':'running','planned_checks':['Filtered','Restored'],
    'requirement':{'type':'frontend_contracts','locked':True,'action_profile':'write_ui_state',
        'bindings':{'field':'Search','value':'fixture'},'check_contracts':{
            'planned-001':{'tool':'browser_inspect_semantic','subject_binding':'field',
                'value_binding':'value','phase':'filtered','assertions':[{'field':'value_matches_binding','operator':'eq','expected':True}]},
            'planned-002':{'tool':'browser_inspect_semantic','subject_binding':'field',
                'value_binding':'value','phase':'restored','assertions':[{'field':'value_empty','operator':'eq','expected':True}]}}}}]}
def evaluate(case, req, check, url):
    if check['check_id']=='planned-001':
        return dict(check,status='passed'),None
    return dict(check,status='blocked'),'frontend_contract_search_action_missing'
with patch.object(uqa,'get_stand',return_value={'web_url':'https://fixture.test'}), \
        patch.object(contracts,'evaluate_contract',evaluate):
    before=deepcopy(job)
    message=uqa.incomplete_search_phase_message(job,'case')
    assert 'planned-002' in message['content'] and message['role']=='user'
    assert '"field": "Search", "text": ""' in message['content']
    assert 'this message authorizes nothing' in message['content']
    assert job==before
    partial=deepcopy(job)
    partial_case=partial['test_cases'][0]
    partial_case['planned_checks'].append('Filtered table')
    partial_case['requirement']['check_contracts']['planned-003']=deepcopy(
        partial_case['requirement']['check_contracts']['planned-001'])
    partial_case['requirement']['check_contracts']['planned-003']['tool']='browser_inspect_table_semantic'
    partial_case['requirement']['check_contracts']['planned-003']['column_binding']='column'
    partial_case['requirement']['check_contracts']['planned-003']['assertions']=[
        {'field':'rows_match_binding','operator':'eq','expected':True}]
    def partial_evaluate(case,req,check,url):
        if check['check_id']=='planned-003':
            return dict(check,status='blocked'),'frontend_contract_search_phase_read_missing'
        return evaluate(case,req,check,url)
    with patch.object(contracts,'evaluate_contract',partial_evaluate):
        assert uqa.locked_contract_observer_tools(partial,'case')=={
            'browser_inspect_semantic','browser_inspect_table_semantic'}
        partial_bad=deepcopy(partial)
        del partial_bad['test_cases'][0]['requirement']['check_contracts']['planned-003']
        assert not uqa.locked_contract_observer_tools(partial_bad,'case')
        partial_bad=deepcopy(partial)
        partial_bad['test_cases'][0]['requirement']['locked']=False
        assert not uqa.locked_contract_observer_tools(partial_bad,'case')
        partial_bad=deepcopy(partial)
        partial_bad['test_cases'][0]['requirement']['check_contracts']['planned-003']['tool']='browser_fill_semantic'
        assert not uqa.locked_contract_observer_tools(partial_bad,'case')
        advisory=uqa.incomplete_search_phase_message(partial,'case')
        assert 'LOCKED PHASE READ MISSING' in advisory['content']
        assert 'browser_inspect_table_semantic' in advisory['content']
        assert 'filtered phase, but' not in advisory['content']
    for change in ({'status':'blocked'},{'job_type':'manual'}):
        other=deepcopy(job);other.update(change)
        assert uqa.incomplete_search_phase_message(other,'case') is None
    other=deepcopy(job);other['test_cases'][0]['requirement']['action_profile']='read_only'
    assert uqa.incomplete_search_phase_message(other,'case') is None
    other=deepcopy(job);other['test_cases'][0]['requirement']['bindings']['field']=''
    assert uqa.incomplete_search_phase_message(other,'case') is None
    for error in ('frontend_contract_search_action_unconfirmed','frontend_contract_search_evidence_unusable'):
        with patch.object(contracts,'evaluate_contract',return_value=({'status':'blocked'},error)):
            assert uqa.incomplete_search_phase_message(job,'case') is None
    with patch.object(contracts,'evaluate_contract',return_value=({'status':'passed'},None)):
        assert uqa.incomplete_search_phase_message(job,'case') is None
        assert len(uqa.completed_readonly_contract_checks(job,'case'))==2
        unsupported=deepcopy(job)
        unsupported['test_cases'][0]['requirement']['action_profile']='write_resource'
        assert uqa.completed_readonly_contract_checks(unsupported,'case') is None
    assert uqa.completed_readonly_contract_checks(job,'case') is None
    with patch.object(contracts,'evaluate_contract',return_value=({'status':'blocked'},'frontend_contract_table_snapshot_incomplete')):
        assert uqa.completed_readonly_contract_checks(job,'case') is None
from pathlib import Path
from tempfile import TemporaryDirectory
import job_store
with TemporaryDirectory(prefix='uqa-phase-') as directory, patch.object(job_store,'JOBS_DIR',Path(directory)):
    stored=job_store.create_job('Filter and clear the same field.',stand='fixture',job_type='manual')
    case=job_store.add_test_case(stored['job_id'],title='Bounded reminder',planned_checks=['Filter restored'])
    job_store.set_job_status(stored['job_id'],'running')
    job_store.update_test_case(stored['job_id'],case['case_id'],status='running')
    calls=[]
    def ask(messages, tools):
        calls.append(True)
        assert len(calls)<=2
        assert sum(m.get('content')==message['content'] for m in messages)==1
        if len(calls)==1:
            return {'message':{'content':'Unable to complete the workflow.'}}
        repairs=[m['content'] for m in messages if '[UQA CORE: STRUCTURED RESULT REQUIRED]' in m.get('content','')]
        assert len(repairs)==1
        parsed,_,error=uqa.extract_structured_checks(repairs[0])
        assert not error and parsed[0]['check_id']=='planned-001'
        assert parsed[0]['status']=='blocked' and parsed[0]['evidence']==[]
        return {'message':{'content':uqa.UQA_CHECKS_START +
            '{"checks":[{"check_id":"planned-001","title":"Filter restored","status":"blocked","evidence":[]}]}' + uqa.UQA_CHECKS_END}}
    def reject_execution(*args,**kwargs):
        raise AssertionError('Reminder executed an action')
    with patch.object(uqa,'ask_ollama',ask), patch.object(uqa,'incomplete_search_phase_message',return_value=message), \
            patch.object(uqa,'execute_tool_with_policy',reject_execution):
        uqa.run_turn([],job_id=stored['job_id'],case_id=case['case_id'],action_policy='confirm_mutations')
    assert len(calls)==2 and job_store.get_job(stored['job_id'])['status']=='blocked'
print('incomplete search phase: PASS (advisory only, full contract and facts required)')
