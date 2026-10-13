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
ui_state = deepcopy(base)
ui_state['test_cases'][0]['requirement'].update(action_profile='write_ui_state',policy_required=True,cleanup_contract='restore_prior_view')
approved=[]
prepare_memory_context(ui_state,'fixture-case',detector,lambda _:deepcopy(ui_state),approved.append,retrieve)
assert len(approved)==1
def failed_detector(stand):
    raise RuntimeError('private-fixture-only')
unknown = []
job, payload = prepare_memory_context(base, 'fixture-case', failed_detector, lambda _: deepcopy(store),
    unknown.append, lambda q, i: {'status': 'unavailable', 'results': [], 'evidence_for_pass': False})
assert job['stand_identity']['status'] == 'unknown' and 'server_version' not in job['stand_identity']
assert 'private-fixture-only' not in str(job)
print('prepared memory context: PASS (fresh identity, opt-in, no false reconfirmation)')

from prepared_memory import record_memory_reconfirmation
runtime_job={'job_id':'fixture-job','test_cases':[{'case_id':'fixture-case','status':'passed',
    'memory_context':{'fact_keys':['fixture-fact']},'observations':[
        {'observation_id':str(i),'type':kind} for i,kind in enumerate(('ui_state','api_exchange','backend_request'))]}]}
candidate={'fact_key':'fixture-fact','source_observation_ids':['0','1','2'],
    'verification':{k:True for k in ('runtime_ui_action_observed','runtime_api_exchange_observed','backend_request_correlated')}}
updates=[]
assert record_memory_reconfirmation('fixture-job','fixture-case',candidate,lambda _:deepcopy(runtime_job),updates.append)
assert updates[0]['test_cases'][0]['memory_context']['binding_reconfirmation']=='runtime_confirmed'
for change in ({'fact_key':'different'}, {'source_observation_ids':['0','1']}, {'verification':{}}):
    invalid=dict(candidate,**change)
    assert not record_memory_reconfirmation('fixture-job','fixture-case',invalid,lambda _:deepcopy(runtime_job),updates.append)
assert len(updates)==1
