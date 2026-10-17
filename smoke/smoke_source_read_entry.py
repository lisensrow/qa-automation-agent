"""Source-only entry projection fixtures, not model/runtime regression PASS."""
from copy import deepcopy
import json
import source_read_entry as e
from regression_read_coverage import requirement


def main():
    r = requirement('US-T79', 'fixture-source-read-entry')
    c = {'case_id': 'tc-00000001', 'status': 'running', 'requirement': r, 'evidence': []}
    j = {'stand': 'lab', 'job_type': 'manual', 'status': 'running', 'resources': [],
         'request': 'Прочитай US-T79 шаг6, вспомни продуктовую память', 'test_cases': [c]}
    assert e.admitted(j, c['case_id'])
    for field, value in [('locked', False), ('source_sha256', '0' * 64), ('action_profile', 'write_resource')]:
        bad = deepcopy(j); bad['test_cases'][0]['requirement'][field] = value
        assert not e.admitted(bad, c['case_id'])
    for field, value in [('stand', 'other'), ('job_type', 'advisory'), ('status', 'blocked')]:
        bad = deepcopy(j); bad[field] = value
        assert not e.admitted(bad, c['case_id'])
    assert not e.admitted(j, 'tc-ffffffff')
    messages = [{'role': 'system', 'content': 'GENERIC'}, {'role': 'system', 'content': 'Keep Core constraints'},
                {'role': 'user', 'content': j['request']}, {'role': 'tool', 'tool_name': 'knowledge_read_regression_case',
                'content': '{"source":"complete own receipt: do not truncate"}'}]
    original = deepcopy(messages)
    view = e.model_messages(messages, 'GENERIC', 'https://uc.lab.local/cmdb?token=DO_NOT_EXPOSE#fragment')
    assert messages == original and len(view) == 4
    assert view[-1] == messages[-1] and view[-2] == messages[-2] and view[1] == messages[1]
    assert 'DO_NOT_EXPOSE' not in json.dumps(view) and 'fragment' not in json.dumps(view)
    assert 'https://uc.lab.local/cmdb' in view[0]['content']
    assert 'bad.invalid' not in e.model_messages(messages, 'GENERIC', 'https://u:p@bad.invalid')[0]['content']
    allowed = ['knowledge_read_regression_case', 'knowledge_search', 'browser_open_agent_tasks_semantic']
    all_names = allowed + ['browser_create_managed_agent_task_semantic', 'browser_click_semantic']
    tools = [{'function': {'name': n}} for n in all_names]
    tools += [{'function': {'name': 'tool_catalog_select', 'parameters': {'properties': {
        'names': {'items': {'enum': all_names}}}}}}]
    before = deepcopy(tools); narrowed = e.catalog(tools)
    assert tools == before
    assert {t['function']['name'] for t in narrowed} == set(allowed) | {'tool_catalog_select'}
    assert narrowed[-1]['function']['parameters']['properties']['names']['items']['enum'] == allowed
    assert '[UQA_CHECKS_JSON]' in e.PROMPT and 'observations=[]' in e.PROMPT
    print('source read entry: PASS (exact immutable scope, preserved own source/user/Core history, no answers/dispatch, safe catalog/URL; fixtures only)')


if __name__ == '__main__':
    main()
