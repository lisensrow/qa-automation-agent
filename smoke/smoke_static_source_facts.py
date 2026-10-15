"""Isolated historical projection fixtures, not autonomous product acceptance."""
from copy import deepcopy
import hashlib
import json
from unittest.mock import Mock
import static_source_facts as facts

profile = {'execution_mode': 'operator_readonly_static_source_review',
    'sources': {'dialog': {'sha256': 'a' * 64, 'bytes': 123}},
    'selected_static_markers': {'dialog': ['default_enabled:!0']},
    'static_observations': {'enabled': True},
    **{key: False for key in facts.PROFILE_FALSE}}
receipt = {'evidence_id': 'ev-fixture', 'type': 'policy_static_source_profile_v213',
    'source': 'operator_ssh_public_frontend_source_review', 'execution_status': 'observed',
    'usable_for_pass': False, 'usable_for_verdict': False, 'value': json.dumps(profile)}
job = {'stand': 'fixture', 'test_cases': [{'case_id': 'tc-fixture', 'evidence': [receipt]}]}
entry = {'source_id': 'fixture-static', 'stand': 'fixture', 'origin': 'https://fixture.invalid',
    'job_id': 'job-fixture', 'case_id': 'tc-fixture', 'evidence_id': 'ev-fixture',
    'evidence_sha256': hashlib.sha256(receipt['value'].encode()).hexdigest(),
    'facts': [{'predicate': 'example.initial_enabled', 'field': 'enabled', 'value_type': 'bool',
               'source_role': 'dialog', 'source_sha256': 'a' * 64, 'anchor': 'default_enabled:!0'}]}
registry = {'version': 1, 'sources': [entry]}


def project(doc=None, source_job=None, stand='fixture', origin='https://fixture.invalid'):
    return facts.project_static_facts(json.dumps(registry if doc is None else doc), stand,
                                     origin, lambda _: job if source_job is None else source_job)


valid = project()
assert valid['status'] == 'historical_candidate' and valid['facts'][0]['value'] is True
assert all(valid[k] is False for k in facts.FLAGS)
assert all(valid['facts'][0][k] is False for k in facts.FLAGS)
brief = facts.render_static_fact_brief(valid)
assert 'example.initial_enabled = true (bool)' in brief and entry['evidence_sha256'] in brief
assert 'default_enabled:!0' not in brief and 'не проверен' in brief
assert project(origin='https://FIXTURE.invalid:443/')['status'] == 'historical_candidate'
assert project(stand='other')['status'] == 'unavailable'
for origin in ('https://other.invalid', 'http://fixture.invalid', 'https://user:password@fixture.invalid',
               'https://fixture.invalid/path', 'https://fixture.invalid?x=1', 'https://fixture.invalid#x'):
    assert project(origin=origin)['status'] == 'unavailable'

for mode in ('version_bool', 'extra', 'empty', 'duplicate_source', 'ambiguous', 'bad_pin',
             'bad_token', 'bad_field_path', 'wrong_field', 'wrong_type', 'text_type',
             'wrong_anchor', 'wrong_role', 'wrong_source_pin', 'duplicate_fact', 'fact_budget'):
    d = deepcopy(registry); e = d['sources'][0]; f = e['facts'][0]
    if mode == 'version_bool': d['version'] = True
    elif mode == 'extra': d['extra'] = True
    elif mode == 'empty': d['sources'] = []
    elif mode == 'duplicate_source': d['sources'].append(deepcopy(e))
    elif mode == 'ambiguous':
        d['sources'].append({**deepcopy(e), 'source_id': 'another'})
    elif mode == 'bad_pin': e['evidence_sha256'] = 'z' * 64
    elif mode == 'bad_token': e['job_id'] = '../private'
    elif mode == 'bad_field_path': f['field'] = '../secret'
    elif mode == 'wrong_field': f['field'] = 'unknown'
    elif mode == 'wrong_type': f['value_type'] = 'int'
    elif mode == 'text_type': f['value_type'] = 'str'
    elif mode == 'wrong_anchor': f['anchor'] = 'not in retained source'
    elif mode == 'wrong_role': f['source_role'] = 'absent'
    elif mode == 'wrong_source_pin': f['source_sha256'] = 'b' * 64
    elif mode == 'duplicate_fact': e['facts'].append(deepcopy(f))
    else: e['facts'] *= 9
    result = project(d)
    assert result['status'] == 'unavailable' and 'facts' not in result, mode

for mode in ('wrong_stand', 'duplicate_case', 'duplicate_receipt', 'type', 'source', 'status',
             'pass', 'verdict', 'missing_value', 'changed_value', 'missing_case'):
    j = deepcopy(job); r = j['test_cases'][0]['evidence'][0]
    if mode == 'wrong_stand': j['stand'] = 'other'
    elif mode == 'duplicate_case': j['test_cases'] *= 2
    elif mode == 'duplicate_receipt': j['test_cases'][0]['evidence'] *= 2
    elif mode == 'type': r['type'] = 'native_get'
    elif mode == 'source': r['source'] = 'model'
    elif mode == 'status': r['execution_status'] = 'success'
    elif mode == 'pass': r['usable_for_pass'] = True
    elif mode == 'verdict': r['usable_for_verdict'] = 0
    elif mode == 'missing_value': del r['value']
    elif mode == 'changed_value': r['value'] += ' '
    else: j['test_cases'] = []
    assert project(source_job=j)['status'] == 'unavailable', mode

for key in facts.PROFILE_FALSE:
    p = deepcopy(profile); p[key] = True
    j = deepcopy(job); j['test_cases'][0]['evidence'][0]['value'] = json.dumps(p)
    d = deepcopy(registry)
    d['sources'][0]['evidence_sha256'] = hashlib.sha256(json.dumps(p).encode()).hexdigest()
    assert project(d, j)['status'] == 'unavailable', key

for markers in ('prefix default_enabled:!0 suffix', [], ['x' * 1025], [True]):
    p = deepcopy(profile); p['selected_static_markers']['dialog'] = markers
    j = deepcopy(job); j['test_cases'][0]['evidence'][0]['value'] = json.dumps(p)
    d = deepcopy(registry); d['sources'][0]['evidence_sha256'] = hashlib.sha256(json.dumps(p).encode()).hexdigest()
    assert project(d, j)['status'] == 'unavailable'

# Changing both reviewed source and pins is an operator registration change, not LLM inference.
p = deepcopy(profile); p['static_observations']['enabled'] = False
j = deepcopy(job); j['test_cases'][0]['evidence'][0]['value'] = json.dumps(p)
d = deepcopy(registry); d['sources'][0]['evidence_sha256'] = hashlib.sha256(json.dumps(p).encode()).hexdigest()
assert project(d, j)['facts'][0]['value'] is False  # No hardcoded true.
p['static_observations']['enabled'] = 1
j['test_cases'][0]['evidence'][0]['value'] = json.dumps(p)
d['sources'][0]['evidence_sha256'] = hashlib.sha256(json.dumps(p).encode()).hexdigest()
assert project(d, j)['status'] == 'unavailable'  # bool != int
d['sources'][0]['facts'][0]['value_type'] = 'int'
assert project(d, j)['facts'][0]['value'] == 1
for raw in ('{"version":1,"version":1,"sources":[]}', 'x' * 32769, '[]', 'null'):
    loader = Mock(side_effect=AssertionError('invalid registry must not read jobs'))
    assert facts.project_static_facts(raw, 'fixture', 'https://fixture.invalid', loader)['status'] == 'unavailable'
    loader.assert_not_called()
assert 'не определено' in facts.render_static_fact_brief({'status': 'unavailable'})
row = {'citation_id': 'S1', 'content': 'job-fixture ev-fixture',
       'source_bytes_rechecked': True, 'source': 'UQA-experience/fixture.md',
       'chunk_no': 1, 'source_sha256': 'b' * 64, 'chunk_sha256': 'c' * 64}
bound = facts.bind_static_facts_to_chunks(valid, [row])
assert bound['facts'][0]['value'] is True and bound['linked_chunks'][0]['citation_id'] == 'S1'
for content in ('job-fixture only', 'ev-fixture only', 'xjob-fixture ev-fixture',
                'job-fixture ev-fixture-extra', 'job-fixture ev-fixture' + 'x' * 8192):
    assert facts.bind_static_facts_to_chunks(valid, [{**row, 'content': content}]) is None
assert facts.bind_static_facts_to_chunks(valid, [{**row, 'source_bytes_rechecked': False}]) is None
assert facts.bind_static_facts_to_chunks({'status': 'unavailable'}, [row]) is None
legacy = 'Jobjob-fixture/tc-fixture/ev-fixture'
assert facts.bind_static_facts_to_chunks(valid, [{**row, 'content': legacy}])
for content in ('x' + legacy, legacy + '-extra', 'Jobjob-fixture/tc-wrong/ev-fixture',
                'Jobjob-fixture/ev-fixture'):
    assert facts.bind_static_facts_to_chunks(valid, [{**row, 'content': content}]) is None
print('static_source_facts: PASS (historical projection, pins/scope/types/ambiguity/flags; no runtime claim)')
