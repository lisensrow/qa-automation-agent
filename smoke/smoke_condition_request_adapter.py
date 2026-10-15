"""Whole-request intent binding; no stand calls or model-authored expected."""
from copy import deepcopy
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import condition_request_adapter as adapter
import condition_draft_profiles as profiles
from condition_draft_runtime import validate_context
import job_store
import uqa

text = 'На стенде lab проверь в CMDB в новой несохранённой коллекции AND-условия: неархивные Endpoint с Ubuntu. Не сохраняй.'
for os_name in ['Ubuntu', 'Windows']:
    request = text.replace('Ubuntu', os_name)
    plan = adapter.regression_plan(request, 'lab')
    assert len(plan) == 1 and len(plan[0]['checks']) == 1
    req = plan[0]['requirement']
    assert req['condition_profile_id'] == profiles.TYPED_FAMILY_PROFILE_ID
    assert next(r for r in req['expected_plan']['conditions'] if r['field']=='OS name')['value'] == os_name
    job = {'job_type':'regression', 'status':'running', 'stand':'lab', 'request':request,
           'resources':[], 'test_cases':[{'case_id':'fixture', 'status':'running',
           'requirement':req, 'planned_checks':plan[0]['checks']}]}
    with patch.object(profiles, 'source_current', return_value=True):
        validate_context(job, 'fixture')
        for change in ['text', 'expected', 'pin', 'cases']:
            broken=deepcopy(job)
            if change=='text':broken['request'] += ' И сохрани.'
            elif change=='expected':broken['test_cases'][0]['requirement']['expected_plan']['conditions'][0]['value']=True
            elif change=='pin':broken['test_cases'][0]['requirement']['condition_request_binding']['request_sha256']='0'*64
            else:broken['test_cases'].append(deepcopy(broken['test_cases'][0]))
            try:validate_context(broken,'fixture')
            except ValueError:pass
            else:raise AssertionError(change)
for request in [text.replace('в CMDB ', ''), text+' И запусти политику.', text.replace('Не сохраняй','Сохрани'),
                text.replace('Ubuntu','Debian'), text.replace('AND','OR'),
                text.replace('неархивные','архивные'), text.replace('lab','production'),
                text.replace('Endpoint','Windows'), text+'\x00', 'Как '+text,
                text.replace('Ubuntu','Ubuntu с RAM > 8'), text+'\nУдалить всё.']:
    assert adapter.regression_plan(request,'lab') is None
assert adapter.regression_plan(text,'other') is None
assert adapter.regression_plan(None,'lab') is None

# The ordinary entry must create one source-bound case and still ask STEP/AUTO.
# Fixtures only: no browser/model/policy execution, and no acceptance claim.
with TemporaryDirectory() as tmp, ExitStack() as stack:
    stack.enter_context(patch.object(job_store,'JOBS_DIR',Path(tmp)))
    stack.enter_context(patch.object(uqa,'plan_regression_cases',side_effect=AssertionError('model planner not expected')))
    stack.enter_context(patch.object(uqa,'_ask_regression_plan_action',side_effect=AssertionError('no generated scope')))
    stack.enter_context(patch.object(uqa,'get_stand',return_value={'web_url':'https://fixture.test'}))
    mode=stack.enter_context(patch.object(uqa,'_ask_regression_execution_mode',return_value='step'))
    stack.enter_context(patch('tools.browser.reset_case_context'))
    stack.enter_context(patch.object(uqa,'export_regression_case_artifacts',return_value=None))
    stack.enter_context(patch.object(uqa,'_print_case_artifact_links'))
    stack.enter_context(patch.object(uqa,'export_regression_job_artifacts',return_value=None))
    stack.enter_context(patch.object(uqa,'run_cleanup_job'))
    stack.enter_context(patch.object(uqa,'reconcile_resource_lifecycle_checks',return_value=[]))
    def fake_turn(messages,**kwargs):
        j=job_store.get_job(kwargs['job_id']); c=j['test_cases'][0]
        assert kwargs['action_policy']=='confirm_mutations'
        assert c['requirement']==adapter.request_requirement(text,'lab')
        assert c['planned_checks']==adapter.regression_plan(text,'lab')[0]['checks']
        job_store.update_test_case(j['job_id'],c['case_id'],status='blocked',result='fixture only')
    turn=stack.enter_context(patch.object(uqa,'run_turn',side_effect=fake_turn))
    jid=uqa.run_regression_job(text,text,current_stand='lab')
    assert len(job_store.get_job(jid)['test_cases'])==1
    mode.assert_called_once(); turn.assert_called_once()
print('PASS whole-request condition adapter: closed intent, immutable caller expected, request pin, one case, ordinary entry retains STEP/AUTO and policy; fixture only')
