"""Read-only component identity: unknown is not compatibility."""
from memory_identity import detect_memory_identity, memory_components_from_inventory
from prepared_memory import prepare_memory_context
from copy import deepcopy

calls = []
def inventory(*images):
    return {'status':'ok','containers':[{'image':image,'name':'frontend'} for image in images]}
assert memory_components_from_inventory(inventory('registry:5000/app/frontend:2.21.0'))=={'frontend':'2.21.0'}
assert memory_components_from_inventory(inventory('app/frontend:2.21.0','app/frontend:2.21.0'))=={'frontend':'2.21.0'}
for ambiguous in (inventory('app/frontend:2.21.0','app/frontend:2.22.0'), inventory('app/frontend:latest'),
                  inventory('app/frontend'), {'status':'error'}, inventory()):
    assert memory_components_from_inventory(ambiguous)=={}
def backend(stand):
    calls.append(('backend',stand))
    return {'status':'ok','installation_architecture':'ansible','server_version':'4.9.0'}
def components(stand):
    calls.append(('components',stand))
    return {'frontend':'2.21.0'}
identity = detect_memory_identity('fixture',backend,components)
assert identity['frontend_status']=='ok' and identity['frontend_version']=='2.21.0'
assert calls==[('backend','fixture'),('components','fixture')]
for value in (None, 'latest', 'dev', '2.21.0 / 2.22.0', '', 123):
    unknown=detect_memory_identity('fixture',backend,lambda _: {'frontend':value})
    assert unknown['frontend_status']=='unknown' and unknown['frontend_version'] is None
def failed(_):
    raise RuntimeError('private-fixture-only')
assert 'private-fixture-only' not in str(detect_memory_identity('fixture',backend,failed))
base={'job_id':'job','stand':'fixture','status':'created','test_cases':[{'case_id':'case','status':'pending',
    'requirement':{'action_profile':'read_only','memory_query':'Name'}}]}
saved=[]
def retrieve(query, received):
    assert received['frontend_version']=='2.21.0'
    return {'status':'ok','results':[], 'frontend_recheck_needed_count':1}
job, _ = prepare_memory_context(base,'case',lambda _:identity,lambda _:deepcopy(base),saved.append,retrieve)
assert job['stand_identity']['frontend_version']=='2.21.0'
assert job['test_cases'][0]['memory_context']['frontend_recheck_needed_count']==1
print('memory frontend identity: PASS (fresh tag, unknown blocks reuse, prepared context preserves scope)')
