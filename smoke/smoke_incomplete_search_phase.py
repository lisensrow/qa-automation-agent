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
    assert job==before
    for change in ({'status':'blocked'},{'job_type':'manual'}):
        other=deepcopy(job);other.update(change)
        assert uqa.incomplete_search_phase_message(other,'case') is None
    other=deepcopy(job);other['test_cases'][0]['requirement']['action_profile']='read_only'
    assert uqa.incomplete_search_phase_message(other,'case') is None
    for error in ('frontend_contract_search_action_unconfirmed','frontend_contract_search_evidence_unusable'):
        with patch.object(contracts,'evaluate_contract',return_value=({'status':'blocked'},error)):
            assert uqa.incomplete_search_phase_message(job,'case') is None
    with patch.object(contracts,'evaluate_contract',return_value=({'status':'passed'},None)):
        assert uqa.incomplete_search_phase_message(job,'case') is None
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
        return {'message':{'content':uqa.UQA_CHECKS_START +
            '{"checks":[{"check_id":"planned-001","title":"Filter restored","status":"blocked","evidence":[]}]}' + uqa.UQA_CHECKS_END}}
    def reject_execution(*args,**kwargs):
        raise AssertionError('Reminder executed an action')
    with patch.object(uqa,'ask_ollama',ask), patch.object(uqa,'incomplete_search_phase_message',return_value=message), \
            patch.object(uqa,'execute_tool_with_policy',reject_execution):
        uqa.run_turn([],job_id=stored['job_id'],case_id=case['case_id'],action_policy='confirm_mutations')
    assert len(calls)==2 and job_store.get_job(stored['job_id'])['status']=='blocked'
print('incomplete search phase: PASS (advisory only, full contract and facts required)')
