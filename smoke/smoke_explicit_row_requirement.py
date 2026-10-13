"""Exact row criterion, absent/duplicate/missing observation; no product writes."""
from copy import deepcopy
import uqa
from observation_extractor import extract_observations

spec = {'expected': 'Exactly one visible table row matches "fixture-row".',
        'task': 'Read-only. Inspect the table only.',
        'checks': ['One exact visible row']}
requirement = uqa.compile_locked_ui_requirement(spec)
source_plan = [{'expected': 'Planner paraphrase', 'checks': ['One exact visible row']}]
uqa._bind_source_row_criterion('Read-only. Expected result: Exactly one visible table row matches "fixture-row".', source_plan)
assert uqa.compile_locked_ui_requirement(source_plan[0]) == requirement
ambiguous = [{'expected': spec['expected'], 'checks': spec['checks']}]
uqa._bind_source_row_criterion('Read-only. Expected result: Exactly one visible table row matches "a". '
                              'Expected result: Exactly one visible table row matches "b".', ambiguous)
assert uqa.compile_locked_ui_requirement(ambiguous[0]) is None
write_plan = [{'expected': spec['expected'], 'checks': spec['checks'], 'task': 'Create a row.'}]
uqa._bind_source_row_criterion('Create a row. Expected result: Exactly one visible table row matches "fixture-row".', write_plan)
assert uqa.compile_locked_ui_requirement(write_plan[0]) is None
assert 'source_row_criterion' not in uqa._bind_source_row_criterion(
    'Expected result: Exactly one visible table row matches "fixture-row".',
    [{'checks': ['first', 'second']}])[0]
assert requirement['locked'] and requirement['bindings']['exact_row_name'] == 'fixture-row'
assert uqa.compile_locked_ui_requirement(dict(spec, checks=['One row', 'Details visible'])) is None
for text in ('Exactly one visible table row matches fixture-row',
             'Exactly one visible table row matches "fixture-row" after changing settings',
             'Exactly one visible table row matches " fixture-row"'):
    assert uqa.compile_locked_ui_requirement(dict(spec, expected=text)) is None
saved = uqa.get_job, uqa.get_stand
try:
    uqa.get_stand = lambda _: {'web_url': 'https://fixture.test'}
    for count, expected in ((1, 'passed'), (0, 'failed'), (2, 'failed'), (None, 'blocked'), (True, 'blocked')):
        obs = extract_observations('browser_inspect_table_row', {'name': 'fixture-row', 'exact': True},
                                  {'row_match_count': count})[0]
        obs['observation_id'] = 'obs-row'
        case = {'case_id': 'case', 'status': 'running', 'requirement': deepcopy(requirement), 'observations': [obs],
                'planned_checks': uqa._normalize_planned_checks(spec['checks']),
                'evidence': [{'evidence_id': 'ev-row', 'type': 'browser_inspect_table_row',
                              'observation_ids': ['obs-row'], 'usable_for_verdict': True}]}
        uqa.get_job = lambda _: {'job_type': 'regression', 'status': 'running', 'stand': 'fixture', 'test_cases': [case]}
        completed = uqa.completed_readonly_contract_checks(uqa.get_job('job'), 'case')
        assert (completed is not None) == (expected != 'blocked')
        if completed is not None:
            assert completed[0]['status'] == expected
        checks, errors = uqa.verify_structured_check_evidence('job', 'case', [
            {'check_id': 'planned-001', 'title': 'One exact visible row', 'status': 'passed',
             'evidence': ['made-up']}])
        assert checks[0]['status'] == expected, (count, checks, errors)
        if expected != 'blocked':
            assert checks[0]['evidence'] == ['ev-row'] and not errors
    valid = deepcopy(uqa.get_job('job'))
    valid['test_cases'][0]['observations'][0]['data']['row_match_count'] = 1
    assert uqa.completed_readonly_contract_checks(valid, 'case') is not None
    for mutate in (
        lambda j: j.update(status='passed'),
        lambda j: j.update(job_type='manual'),
        lambda j: j['test_cases'][0].update(status='pending'),
        lambda j: j['test_cases'][0]['requirement'].update(action_profile='write_resource'),
        lambda j: j['test_cases'][0]['planned_checks'].append({'check_id': 'planned-002', 'title': 'Unproven check'}),
        lambda j: j['test_cases'][0]['evidence'][0].update(usable_for_verdict=False),
        lambda j: j['test_cases'][0]['observations'][0]['data'].update(subject='other-row'),
    ):
        changed = deepcopy(valid)
        mutate(changed)
        assert uqa.completed_readonly_contract_checks(changed, 'case') is None
finally:
    uqa.get_job, uqa.get_stand = saved
print('explicit row requirement: PASS (strict grammar, actual count, absent/duplicate/malformed facts)')
