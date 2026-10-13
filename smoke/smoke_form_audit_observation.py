"""Form scalar facts survive independently of bulky/truncated evidence. No values copied."""
from copy import deepcopy
from observation_extractor import extract_observations

tool = 'browser_inspect_form_validation_semantic'
result = {'current_url': 'https://fixture.test/forms', 'mutation_executed': False,
          'validation_audit': {'visible_control_count': 2, 'invalid_control_count': 1,
          'validation_passed': False, 'truncated': False,
          'invalid_controls': [{'value': 'private-fixture-value', 'validation_message': 'private'}]},
          'text_preview': 'private-fixture-value' * 10000}
data = extract_observations(tool, {}, result)[0]['data']
assert data['audit']['validation_passed'] is False
assert data['audit']['invalid_control_count'] == 1
assert data['observation_result'] == 'observed'
assert data['scope_kind'] == 'page'
assert 'private-fixture-value' not in str(data)
for change in ({'visible_control_count': True}, {'invalid_control_count': -1},
               {'validation_passed': 'true'}, {'truncated': True},
               {'invalid_control_count': 3}, {'validation_passed': True}):
    variant = deepcopy(result)
    variant['validation_audit'].update(change)
    assert extract_observations(tool, {}, variant)[0]['data']['observation_result'] == 'blocked'
for change in ({'mutation_executed': True}, {'executed': False}, {'error': 'fixture_error'},
               {'validation_audit': None}):
    variant = deepcopy(result)
    variant.update(change)
    assert extract_observations(tool, {}, variant)[0]['data']['observation_result'] == 'blocked'
empty = deepcopy(result)
empty['validation_audit'].update(visible_control_count=0, invalid_control_count=0, validation_passed=True)
zero = extract_observations(tool, {}, empty)[0]['data']
assert zero['audit']['visible_control_count'] == 0
assert 'status' not in zero  # Vacuous validation is not a form-open PASS.
for name, key, audit in (
    ('browser_inspect_field_label_contract_semantic', 'field_label_audit',
     {'field_count': 2, 'unlabeled_count': 0, 'broken_description_count': 0,
      'field_label_contract_passed': True, 'truncated': False}),
    ('browser_inspect_dialog_contract_semantic', 'dialog_contract_audit',
     {'dialog_count': 0, 'failure_count': 0, 'dialog_contract_passed': True, 'truncated': False}),
):
    observed = extract_observations(name, {}, {key: audit, 'mutation_executed': False})[0]['data']
    assert observed['audit'] == audit
    assert observed['observation_result'] == 'observed'
assert extract_observations('unknown_form_tool', {}, result) == []
print('form audit observation: PASS (typed allowlist, no field values, zero is not automatic PASS)')
