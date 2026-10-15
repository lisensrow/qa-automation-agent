"""Source-bound saved graph summary: fixture metadata is not native UI acceptance."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from tools.block_graph_controls import summarize_saved_block_graph

now = datetime(2026, 10, 15, tzinfo=timezone.utc)
body = {'offset':0,'limit':50,'count':1,'total':1,'items':[
    {'id':'private-fixture-id','name':'private fixture name','xml':'<xml><block id="private-block" type="private-type"><field name="SECRET">token=fixture-secret</field></block></xml>','context':{'private':'fixture-secret'}}]}
detail = {'request_id':'n1','method':'GET','status':200,'session_id':'fixture-session',
          'response_origin':'https://fixture.test','url':'/observed/collection',
          'received_at':now.isoformat(),'response_body_truncated':False,'response_body':json.dumps(body)}
def inspect(value, **kwargs):
    return summarize_saved_block_graph(value, 'private fixture name', current_origin='https://fixture.test',
                                      current_session_id='fixture-session',now=now,**kwargs)
def refuse(value, **kwargs):
    result = inspect(value,**kwargs)
    assert result['saved_graph_observation_status']=='refused',result
    assert not result['evidence_for_pass'] and not result['permission_granted']
    assert 'fixture-secret' not in json.dumps(result) and 'private fixture name' not in json.dumps(result)
r=inspect(detail)
assert r['saved_graph_observation_status']=='observed' and r['counts']['block']==1
assert r['source_session_matched'] and r['same_origin_source_verified'] and r['record_identity_matched']
assert not r['workspace_binding_verified'] and not r['record_context_verified'] and not r['evidence_for_pass']
assert all(s not in json.dumps(r) for s in ('fixture-secret','private-fixture-id','private fixture name','private-type','private-block'))
for change in ({'method':'POST'},{'status':True},{'status':500},{'session_id':'other'},
               {'response_origin':'https://other.test'},{'url':'https://other.test/collection'},
               {'url':'//other.test/collection'},{'url':'not-an-observed-path'},
               {'request_id':'n0'},{'request_id':'arbitrary'},{'received_at':'2026-10-14T00:00:00+00:00'},
               {'received_at':'2026-10-16T00:00:00+00:00'},{'received_at':'2026-10-15T00:00:00'},
               {'response_body_truncated':True},{'response_body_truncated':None},
               {'response_body':'invalid'},{'response_body':'[]'},{'response_body':'x'*65537},
               {'response_body':'['*1200},{'error':'private fixture error'}):
    refuse(dict(detail,**change))
for limit in (True,0,3601,'60'):
    refuse(detail,max_age_seconds=limit)
for change in ({'offset':1},{'offset':False},{'count':True},{'count':0},{'total':2},{'total':True},
               {'limit':0},{'limit':True},{'items':None}):
    refuse(dict(detail,response_body=json.dumps(dict(body,**change))))
for changed_items in ([body['items'][0],dict(body['items'][0],id='other')],
                      [body['items'][0],dict(body['items'][0],name='other')],
                      [dict(body['items'][0],xml='<xml><unsupported/></xml>')],
                      [dict(body['items'][0],id=None)], [None]):
    changed=dict(body,items=changed_items,count=len(changed_items),total=len(changed_items))
    refuse(dict(detail,response_body=json.dumps(changed)))
from types import SimpleNamespace
from unittest.mock import patch
import uqa
from tools.browser import BrowserSession
from tools.registry import execute_tool

tool='browser_inspect_saved_block_graph_semantic'
assert uqa.classify_tool_action(tool,{'request_id':'n1','exact_name':'private fixture name'})=='observe'
assert any(t['function']['name']==tool for t in uqa.model_tool_catalog({tool}))
schema=next(t['function']['parameters'] for t in uqa.model_tool_catalog({tool}) if t['function']['name']==tool)
assert set(schema['properties'])=={'request_id','exact_name'} and schema['additionalProperties'] is False
assert execute_tool(tool,{'request_id':'n1','exact_name':'fixture','max_age_seconds':0})['error']=='saved_graph_arguments_invalid'
session=BrowserSession();session.page=SimpleNamespace(url='https://fixture.test/observed-ui')
session.session_id='fixture-session'
native_detail=dict(detail,received_at=datetime.now(timezone.utc).isoformat())
with patch('tools.browser._session',session),patch.object(session,'_ensure_started'), \
     patch.object(session,'get_network_detail',return_value=native_detail) as read, \
     patch.object(session,'_begin_action_execution') as dispatch,patch.object(session,'_capture_state') as capture:
    native=execute_tool(tool,{'request_id':'n1','exact_name':'private fixture name'})
    assert native['saved_graph_observation_status']=='observed'
    assert native['mutation_executed'] is False and not dispatch.called and not capture.called
    read.assert_called_once_with('n1')
    assert all(s not in json.dumps(native) for s in ('fixture-secret','private-fixture-id','private fixture name'))
    with patch.object(uqa,'add_evidence',return_value={'evidence_id':'fixture-evidence'}) as store:
        uqa.record_tool_evidence('fixture-job','fixture-case',tool,{'request_id':'n1','exact_name':'private fixture name'},native)
        assert store.call_args.kwargs['usable_for_pass'] is False
        assert store.call_args.kwargs['usable_for_verdict'] is False
    read.side_effect=RuntimeError('token=fixture-secret')
    failure=execute_tool(tool,{'request_id':'n1','exact_name':'private fixture name'})
    assert failure['error']=='saved_graph_native_source_unavailable' and 'fixture-secret' not in json.dumps(failure)
    assert not dispatch.called
print('saved block graph: PASS (GET/session/origin/age/completeness/exact record, registry/native wiring, no values or business PASS)')
