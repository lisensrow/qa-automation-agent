"""Core ledger update only: no real Job, browser, service or business writes."""
import json
from unittest.mock import patch
import uqa

def observation(data,tool='browser_get_network_detail'):
    return [{'role':'tool','tool_name':tool,'content':json.dumps(data)}]

good=observation({'status':201,'response_body':'{"id":"new-id","name":"owned-fixture"}'})
assert uqa._tool_history_observed_identifier(good,'new-id',expected_name='owned-fixture')
assert not uqa._tool_history_observed_identifier(good,'new-id',expected_name='existing-fixture')
assert not uqa._tool_history_observed_identifier(observation({'status':500,'response_body':'{"id":"new-id","name":"owned-fixture"}'}),'new-id',expected_name='owned-fixture')
assert not uqa._tool_history_observed_identifier(observation({'request_body':{'id':'new-id','name':'owned-fixture'}}),'new-id',expected_name='owned-fixture')
assert not uqa._tool_history_observed_identifier(observation({'id':'new-id','name':'owned-fixture'},'resource_list'),'new-id',expected_name='owned-fixture')

resource={'resource_id':'fixture-resource','name':'owned-fixture','external_id':None}
updates=[]
def update(**kwargs):
    updates.append(kwargs)
    resource.update({k:v for k,v in kwargs.items() if k in ('name','external_id') and v is not None})
    return dict(resource)
with patch.object(uqa,'get_test_resource',lambda *args:dict(resource)), patch.object(uqa,'update_test_resource',update):
    def call(value,messages):
        return uqa.execute_tool_with_policy('resource_update',{'resource_id':'fixture-resource','external_id':value},
            messages,action_policy='legacy',job_id='fixture-job',case_id='fixture-case')
    denied=call('new-id',[])
    assert denied['error']=='resource_identifier_not_observed_for_exact_resource' and not updates
    wrong=observation({'status':200,'response_body':'{"id":"new-id","name":"existing-fixture"}'})
    assert call('new-id',wrong)['executed'] is False and not updates
    accepted=call('new-id',good)
    assert accepted.get('status')=='ok' and resource['external_id']=='new-id',accepted.get('error')
    assert len(updates)==1
    assert call('replacement-id',good)['error']=='resource_identifier_immutable' and len(updates)==1
    assert call('',good)['error']=='resource_identifier_immutable' and len(updates)==1
    assert call('new-id',[])['status']=='ok' and len(updates)==2
print('PASS Core resource identity: exact-name observation for first binding, immutable known ID, no browser or stand changes')
