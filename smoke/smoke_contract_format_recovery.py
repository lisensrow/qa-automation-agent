"""Malformed prose gets bounded format recovery, never a synthetic PASS."""
import uqa
saved={k:getattr(uqa,k) for k in ('ask_ollama','prepared_observation_contract','prepared_contract_check_templates')}
try:
    uqa.prepared_observation_contract=lambda *args:None
    uqa.prepared_contract_check_templates=lambda *args:[{'check_id':'planned-001','status':'blocked'}]
    for responses,expected_calls in ((['bare JSON','bare JSON','still prose'],3),
                                    (['bare JSON','[UQA_CHECKS_JSON]{"checks":[{"title":"Fixture unavailable","status":"blocked"}]}[/UQA_CHECKS_JSON]'],2)):
        calls=[]
        def ask(messages, tools):
            calls.append(len([m for m in messages if 'STRUCTURED RESULT REQUIRED' in str(m.get('content'))]))
            return {'message':{'content':responses[len(calls)-1]}}
        uqa.ask_ollama=ask
        messages=[]
        uqa.run_turn(messages,action_policy='confirm_mutations')
        assert len(calls)==expected_calls and calls==list(range(expected_calls))
        assert not any(m.get('tool_calls') for m in messages)
finally:
    for k,value in saved.items():
        setattr(uqa,k,value)
print('contract format recovery: PASS (bounded retries, no action or inferred verdict)')

# The same refusal applies to ordinary QA cases without prepared contracts.
from copy import deepcopy
saved={k:getattr(uqa,k) for k in ('ask_ollama','get_job','update_test_case','recompute_job_status',
    'prepared_observation_contract','prepared_contract_check_templates')}
calls=[]
updates=[]
job={'job_id':'fixture-job','job_type':'manual','request':'Inspect only.',
     'test_cases':[{'case_id':'fixture-case','status':'running','planned_checks':['Visible field is present']}]}
try:
    uqa.get_job=lambda _:deepcopy(job)
    uqa.update_test_case=lambda *args,**kwargs:updates.append(kwargs)
    uqa.recompute_job_status=lambda _: 'blocked'
    uqa.prepared_observation_contract=lambda *args:None
    uqa.prepared_contract_check_templates=lambda *args:None
    def ask_manual(messages,tools):
        calls.append(len([m for m in messages if 'STRUCTURED RESULT REQUIRED' in str(m.get('content'))]))
        assert len(calls)<=3
        return {'message':{'content':'PASS, because I think it is correct.'}}
    uqa.ask_ollama=ask_manual
    uqa.run_turn([],job_id='fixture-job',case_id='fixture-case',action_policy='confirm_mutations')
    assert calls==[0,1,2] and updates[-1]['status']=='blocked'
    assert 'structured_result_missing' in updates[-1]['result']
finally:
    for k,value in saved.items():
        setattr(uqa,k,value)
print('ordinary QA format recovery: PASS (prose PASS rejected after two retries, no product action)')
