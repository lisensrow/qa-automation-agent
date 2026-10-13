"""Core follows only the exact safe capability observer, never a mutation."""
from pathlib import Path
from tempfile import TemporaryDirectory
import uqa
import job_store

saved = {k: getattr(uqa, k) for k in ('ask_ollama', 'execute_tool_with_policy', 'get_stand')}
saved_dir = job_store.JOBS_DIR
try:
    with TemporaryDirectory(prefix='uqa-preflight-') as directory:
        job_store.JOBS_DIR = Path(directory)
        uqa.get_stand = lambda _: {'web_url': 'https://fixture.test'}
        job = job_store.create_job('Open Add only; close without saving.', stand='fixture', job_type='manual')
        case = job_store.add_test_case(job['job_id'], title='Fixture', planned_checks=['No submit'],
                                       requirement={'stand': 'fixture', 'action_profile': 'write_ui_state'})
        job_store.set_job_status(job['job_id'], 'running')
        job_store.update_test_case(job['job_id'], case['case_id'], status='running')
        asks = []
        calls = []
        def ask(messages, tools):
            asks.append(True)
            if len(asks) == 1:
                return {'message': {'content': '', 'tool_calls': [{'function': {
                    'name': 'browser_click_semantic', 'arguments': {'name': 'Add', 'exact': True}}}]}}
            assert calls == ['browser_click_semantic', 'browser_probe_capabilities']
            return {'message': {'content': uqa.UQA_CHECKS_START +
                '{"checks":[{"check_id":"planned-001","title":"No submit","status":"blocked","evidence":[]}]}' +
                uqa.UQA_CHECKS_END}}
        def policy(name, args, messages, **kwargs):
            calls.append(name)
            assert kwargs['action_policy'] == 'confirm_mutations'
            if name == 'browser_click_semantic':
                return {'error': 'managed_compatibility_probe_required', 'status': 'blocked_by_policy',
                        'executed': False, 'action_policy_status': 'blocked_by_compatibility_preflight',
                        'required_action_candidate': {'tool': 'browser_probe_capabilities', 'arguments': {}}}
            assert name == 'browser_probe_capabilities' and args == {}
            return {'status': 'ok', 'executed': True, 'action_class': 'observe',
                    'action_policy_status': 'auto_allowed', 'compatibility_status': 'compatible'}
        uqa.ask_ollama, uqa.execute_tool_with_policy = ask, policy
        uqa.run_turn([], job_id=job['job_id'], case_id=case['case_id'], action_policy='confirm_mutations')
        assert len(asks) == 2 and calls == ['browser_click_semantic', 'browser_probe_capabilities']
        assert job_store.get_job(job['job_id'])['status'] == 'blocked'
        retry_job = job_store.create_job('Open Add only; close without saving.', stand='fixture', job_type='manual')
        retry_case = job_store.add_test_case(retry_job['job_id'], title='Bounded retry', planned_checks=['No submit'],
                                             requirement={'stand': 'fixture', 'action_profile': 'write_ui_state'})
        job_store.set_job_status(retry_job['job_id'], 'running')
        job_store.update_test_case(retry_job['job_id'], retry_case['case_id'], status='running')
        calls = []
        retry_asks = []
        def retry_ask(messages, tools):
            retry_asks.append(True)
            assert len(retry_asks) <= 3
            return {'message': {'content': '', 'tool_calls': [{'function': {
                'name': 'browser_click_semantic', 'arguments': {'name': 'Add', 'exact': True}}}]}}
        uqa.ask_ollama = retry_ask
        uqa.run_turn([], job_id=retry_job['job_id'], case_id=retry_case['case_id'], action_policy='confirm_mutations')
        assert calls == ['browser_click_semantic', 'browser_probe_capabilities', 'browser_click_semantic',
                         'browser_probe_capabilities', 'browser_click_semantic']
        assert len(retry_asks) == 3
        result_case = job_store.get_job(retry_job['job_id'])['test_cases'][0]
        assert result_case['status'] == 'blocked' and 'compatibility_preflight_unresolved' in result_case['result']
finally:
    job_store.JOBS_DIR = saved_dir
    for key, value in saved.items():
        setattr(uqa, key, value)
print('compatibility preflight progress: PASS (Core OBSERVE through policy, no auto mutation or PASS)')
