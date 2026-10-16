"""Closed ordinary source intent; isolated fixtures, no model or UC acceptance."""
from copy import deepcopy
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import schema_request_adapter as adapter
from schema_read_runtime import validate_context
import job_store
import uqa

text=('На стенде lab прочитай из зарегистрированного снимка API параметры командной задачи '
      'и формат полного результата. Ничего не запускай.')
for request in [text,text.upper(),text.replace('На стенде lab ',''),text.replace('стенде ',''),
                text.replace('из зарегистрированного снимка API','по зарегистрированной схеме API')]:
    plan=adapter.regression_plan(request,'lab')
    assert plan is not None and len(plan)==1 and len(plan[0]['checks'])==1
    req=plan[0]['requirement'];assert req['action_profile']=='read_only' and req['locked'] is True
    job={'stand':'lab','job_type':'regression','status':'running','resources':[],
         'request':request,'test_cases':[{'case_id':'fixture','status':'running','requirement':req}]}
    validate_context(job,'fixture')
    for change in ['raw_request','hash','source','profile','additional_action','extra_binding']:
        bad=deepcopy(job);r=bad['test_cases'][0]['requirement']
        if change=='raw_request':bad['request']+=' '
        elif change=='hash':r['schema_request_binding']['request_sha256']='0'*64
        elif change=='source':r['api_contract_source_id']='other'
        elif change=='profile':r['action_profile']='write_resource'
        elif change=='additional_action':bad['request']+=' И создай политику.'
        else:r['schema_request_binding']['extra']=True
        try:validate_context(bad,'fixture')
        except ValueError:pass
        else:raise AssertionError(change)
for request in [None,'',text+' И создай задачу.',text+'\nУдалить всё.',text+'\x00',
                text.replace('Ничего не запускай','Запусти команду'),text.replace('lab','production'),
                text.replace('снимка API','актуального API'),text.replace('командной','любой'),
                text.replace('прочитай','измени'),text+' Версия latest.', 'Как '+text]:
    assert adapter.regression_plan(request,'lab') is None,repr(request)
assert adapter.regression_plan(text,'prod') is None

for execution_mode in ['step','auto']:
    with TemporaryDirectory() as temp, ExitStack() as stack:
        stack.enter_context(patch.object(job_store,'JOBS_DIR',Path(temp)))
        stack.enter_context(patch.object(uqa,'plan_regression_cases',side_effect=AssertionError('unexpected generated planner')))
        stack.enter_context(patch.object(uqa,'prepare_locked_requirements',side_effect=AssertionError('immutable factory already compiled')))
        stack.enter_context(patch.object(uqa,'_ask_regression_plan_action',side_effect=AssertionError('no generated scope')))
        stack.enter_context(patch.object(uqa,'get_stand',return_value={'web_url':'https://fixture.test'}))
        mode=stack.enter_context(patch.object(uqa,'_ask_regression_execution_mode',return_value=execution_mode))
        reset=stack.enter_context(patch('tools.browser.reset_case_context',side_effect=AssertionError('source-only entry must not open browser')))
        stack.enter_context(patch.object(uqa,'export_regression_case_artifacts',return_value=None))
        stack.enter_context(patch.object(uqa,'_print_case_artifact_links'))
        stack.enter_context(patch.object(uqa,'export_regression_job_artifacts',return_value=None))
        stack.enter_context(patch.object(uqa,'run_cleanup_job'))
        stack.enter_context(patch.object(uqa,'reconcile_resource_lifecycle_checks',return_value=[]))
        def fake_turn(messages,**kwargs):
            job=job_store.get_job(kwargs['job_id']);case=job['test_cases'][0]
            assert job['request']==text and kwargs['action_policy']=='confirm_mutations'
            assert case['requirement']==adapter.request_requirement(text,'lab')
            validate_context(job,case['case_id'])
            job_store.update_test_case(job['job_id'],case['case_id'],status='blocked',result='isolated source fixture only')
        turn=stack.enter_context(patch.object(uqa,'run_turn',side_effect=fake_turn))
        jid=uqa.run_regression_job(text,text,current_stand='lab')
        assert len(job_store.get_job(jid)['test_cases'])==1
        mode.assert_called_once();turn.assert_called_once();reset.assert_not_called()
print('PASS ordinary source request fixture: whole intent/raw SHA, immutable source-only factory, no extra actions/browser, STEP/AUTO and v069 retained; not model acceptance')
