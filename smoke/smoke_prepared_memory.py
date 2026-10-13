from copy import deepcopy
from prepared_memory import prepare_memory_context

base = {'job_id': 'fixture-job', 'stand': 'fixture-stand', 'status': 'created',
        'stand_identity': {'status': 'ok', 'server_version': 'old'},
        'test_cases': [{'case_id': 'fixture-case', 'status': 'pending',
                        'requirement': {'action_profile': 'read_only', 'memory_query': 'Name filter'}}]}
store = deepcopy(base)
saved = []
detected = []
seen = []
def detector(stand):
    detected.append(stand)
    return {'status': 'ok', 'server_version': 'new', 'installation_architecture': 'ansible',
            'deployment_partial': False, 'password': 'private-fixture-only'}
def retrieve(query, identity):
    seen.append(identity)
    assert identity['server_version'] == 'new'
    return {'status': 'ok', 'results': [{'fact_key': 'fixture-fact'}], 'evidence_for_pass': False}
job, payload = prepare_memory_context(base, 'fixture-case', detector, lambda _: deepcopy(store),
                                     saved.append, retrieve)
assert len(saved) == 1 and detected == ['fixture-stand']
assert 'password' not in job['stand_identity']
assert job['test_cases'][0]['memory_context']['binding_reconfirmation'] == 'not_performed'
assert job['test_cases'][0]['memory_context']['evidence_for_pass'] is False
assert base['stand_identity']['server_version'] == 'old'
legacy = deepcopy(base)
legacy['test_cases'][0]['requirement'].pop('memory_query')
assert prepare_memory_context(legacy, 'fixture-case', None, None, None) == (legacy, None)
for profile in ('write_ui_state', 'write_resource'):
    candidate = deepcopy(base)
    candidate['test_cases'][0]['requirement']['action_profile'] = profile
    try:
        prepare_memory_context(candidate, 'fixture-case', detector, None, None)
        raise AssertionError('write profile accepted')
    except ValueError:
        pass
changed = deepcopy(store)
changed['stand'] = 'different-stand'
try:
    prepare_memory_context(base, 'fixture-case', detector, lambda _: changed, saved.append, retrieve)
    raise AssertionError('concurrent stand change accepted')
except ValueError:
    pass
assert len(saved) == 1
def failed_detector(stand):
    raise RuntimeError('private-fixture-only')
unknown = []
job, payload = prepare_memory_context(base, 'fixture-case', failed_detector, lambda _: deepcopy(store),
    unknown.append, lambda q, i: {'status': 'unavailable', 'results': [], 'evidence_for_pass': False})
assert job['stand_identity']['status'] == 'unknown' and 'server_version' not in job['stand_identity']
assert 'private-fixture-only' not in str(job)
print('prepared memory context: PASS (fresh identity, opt-in, no false reconfirmation)')
