"""Pure fixtures: failed API detail must never create product knowledge."""
from copy import deepcopy
import candidate_facts as module

ui={'observation_id':'ui','type':'ui_state','data':{'action':'fill-semantic','path':'/items',
    'input':{'field':'Name','text':'fixture'},'action_execution_id':'action','session_id':'session',
    'network_window_closed':True,'network_requests':[{'request_id':'request','action_execution_id':'action',
        'method':'GET','url':'https://fixture.test/api/items?name=fixture'}]}}
api={'observation_id':'api','type':'api_exchange','data':{'method':'GET','path':'/api/items',
    'query':{'name':'fixture'},'http_status':200,'action_execution_id':'action','request_id':'request','session_id':'session'}}
backend={'observation_id':'backend','type':'backend_request','data':{'stand':'fixture','method':'GET',
    'endpoint':'/api/items','match_count':1}}
case={'case_id':'case','status':'passed','observations':[ui,api,backend],
      'evidence':[{'observation_ids':[ref],'usable_for_verdict':True} for ref in ('ui','api','backend')]}
base={'stand':'fixture','test_cases':[case]}
saved=module.get_job,module.upsert_candidate_fact
created=[]
try:
    def generate(job):
        module.get_job=lambda _:deepcopy(job)
        module.upsert_candidate_fact=lambda **candidate: created.append(candidate) or candidate
        created.clear()
        return module.generate_candidate_facts_for_case('job','case')
    facts=generate(base)
    assert len(facts)==1 and facts[0]['verification']['backend_request_correlated'] is True
    for changes in ({'method':None},{'path':''},{'path':'relative'},{'query':['bad']},
                    {'http_status':None},{'http_status':True},{'action_execution_id':None},
                    {'request_id':'invented'},{'session_id':'other'}):
        bad=deepcopy(base)
        bad['test_cases'][0]['observations'][1]['data'].update(changes)
        assert generate(bad)==[] and created==[],changes
    for alter in (lambda c:c['evidence'][1].update(usable_for_verdict=False),
                  lambda c:c['evidence'].append(deepcopy(c['evidence'][1])),
                  lambda c:c['observations'][0]['data'].update(network_window_closed=False),
                  lambda c:c['observations'][0]['data'].update(network_requests=[])):
        bad=deepcopy(base)
        alter(bad['test_cases'][0])
        assert generate(bad)==[] and created==[]
    wrong_backend=deepcopy(base)
    wrong_backend['test_cases'][0]['observations'][2]['data']['stand']='other'
    assert generate(wrong_backend)[0]['verification']['backend_request_correlated'] is False
finally:
    module.get_job,module.upsert_candidate_fact=saved
print('candidate runtime trace: PASS (empty/error API, wrong IDs, scopes and unusable evidence rejected)')
