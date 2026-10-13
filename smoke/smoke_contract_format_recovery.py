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
