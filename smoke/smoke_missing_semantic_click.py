"""An identical missing click never gets a second policy execution on unchanged UI."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import job_store
import uqa

def check_guard(change_state):
    job = job_store.create_job('Open Add only; no save.', stand='fixture', job_type='manual')
    case = job_store.add_test_case(job['job_id'], title='Missing target', planned_checks=['Form observed'])
    job_store.set_job_status(job['job_id'], 'running')
    job_store.update_test_case(job['job_id'], case['case_id'], status='running')
    requested = []
    executed = []
    def ask(messages, tools):
        requested.append(True)
        if len(requested) == 1:
            name, args = 'browser_open_page', {'url': 'https://fixture.test/catalog'}
        elif len(requested) == 2:
            name, args = 'browser_click_semantic', {'name': 'Add', 'role': 'button', 'container': 'Section'}
        elif change_state and len(requested) == 3:
            name, args = 'browser_get_state', {}
        else:
            assert len(requested) <= (5 if change_state else 3)
            assert any('CLICK TARGET NOT FOUND' in str(m.get('content', '')) for m in messages)
            name, args = 'browser_click_semantic', {'container': 'Section', 'role': 'button', 'exact': True, 'name': 'Add'}
        return {'message': {'content': '', 'tool_calls': [{'function': {'name': name, 'arguments': args}}]}}
    def policy(name, args, messages, **kwargs):
        assert kwargs['action_policy'] == 'confirm_mutations'
        executed.append(name)
        if name == 'browser_open_page':
            return {'http_status': 200, 'current_url': 'https://fixture.test/catalog', 'text_preview': 'Section',
                    'action_class': 'observe', 'action_policy_status': 'auto_allowed'}
        if name == 'browser_get_state':
            return {'current_url': 'https://fixture.test/catalog', 'text_preview': 'Section changed',
                    'action_class': 'observe', 'action_policy_status': 'auto_allowed'}
        assert name == 'browser_click_semantic'
        return {'error': 'semantic_element_not_found', 'executed': False}
    with patch.object(uqa, 'ask_ollama', ask), patch.object(uqa, 'execute_tool_with_policy', policy), \
            patch.object(uqa, 'get_stand', return_value={'web_url': 'https://fixture.test'}):
        uqa.run_turn([], job_id=job['job_id'], case_id=case['case_id'], action_policy='confirm_mutations')
    expected = ['browser_open_page', 'browser_click_semantic']
    if change_state:
        expected += ['browser_get_state', 'browser_click_semantic']
    assert executed == expected
    actual = job_store.get_job(job['job_id'])['test_cases'][0]
    assert actual['status'] == 'blocked'
    assert 'repeated_missing_semantic_click' in actual['result']
    final = json.loads(actual['evidence'][-1]['value'])['result']
    assert final['executed'] is False
    assert final['error'] == 'repeated_missing_semantic_click_blocked'
    assert not actual['evidence'][-1]['usable_for_verdict']
with TemporaryDirectory(prefix='uqa-click-') as directory, patch.object(job_store, 'JOBS_DIR', Path(directory)):
    check_guard(False)
    check_guard(True)
print('missing semantic click: PASS (unchanged UI blocked, changed UI reevaluated, policy retained)')
