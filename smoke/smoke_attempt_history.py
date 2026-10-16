"""Fixture-only historical proof/linkage/isolation; no live product acceptance."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import uqa,job_store,attempt_history as p
from tools.registry import execute_tool

a={'source_job_id':'20261016-040027-eeb562f2','source_case_id':'tc-51254348','operation_id':'op-'+'a'*32}
task='7e544929-1fce-4936-961d-761fafffa272'
def evidence(eid,tool,status,body):
    return {'evidence_id':eid,'source':'uqa_tool','type':tool,'execution_status':status,
        'value':json.dumps({'tool':tool,'arguments':{},'result':body})}
base={'job_id':a['source_job_id'],'case_id':a['source_case_id'],'operation_id':a['operation_id'],
      'task_id':task,'session_id':'fixture-session'}
ce=evidence('ev-create',p.CREATE,'executed',{**base,'executed':True,'mutation_executed':True})
fe=evidence('ev-full',p.READ,'observed',{**base,'native_result_verified':True,'identity_verified':True,'fresh_result':True})
job={'job_id':a['source_job_id'],'stand':'lab','test_cases':[{'case_id':a['source_case_id'],'evidence':[ce,fe]}]}
op={'operation_id':a['operation_id'],'case_id':a['source_case_id'],'tool':p.CREATE,'status':'verified',
    'receipt':{'acknowledged':True,'native_pre_dispatch_refusal':False},
    'verification':{'verified':True,'postcondition_verified':True,'receipt_evidence_id':'ev-create',
        'evidence_id':'ev-full','identifier_value':task}}
journal={'version':1,'job_id':a['source_job_id'],'operations':[op]}
out=p.project(job,journal,a)
assert out['request_sent'] is True and out['own_task_id']==task and not out['resend_authorized'] and not out['business_pass']
assert out['historical_only'] is True and out['live_postcondition_rechecked'] is False
for status in ['sending','uncertain','awaiting_verification','rejected','canceled']:
    j=deepcopy(journal);j['operations'][0]['status']=status
    assert p.project(job,j,a)['request_sent'] is None
for field,value in [('task_id','a'*36),('case_id','tc-00000000'),('operation_id','op-'+'b'*32),('job_id','20261016-000000-aaaaaaaa'),
                    ('native_result_verified',False),('identity_verified',False),('fresh_result',False),('session_id','other')]:
    altered=deepcopy(job);body=json.loads(altered['test_cases'][0]['evidence'][1]['value']);body['result'][field]=value
    altered['test_cases'][0]['evidence'][1]['value']=json.dumps(body)
    assert p.project(altered,journal,a)['request_sent'] is None
altered=deepcopy(job);altered['test_cases'][0]['evidence'][0]['source']='model'
assert p.project(altered,journal,a)['request_sent'] is None
nj=deepcopy(journal);no=nj['operations'][0];no['status']='not_sent';no['verification']=None
no['receipt']={'acknowledged':False,'native_pre_dispatch_refusal':True}
ref=evidence('ev-refused',p.CREATE,'tool_error',{'operation_id':a['operation_id'],'error':'preflight',
    'executed':False,'mutation_executed':False,'dispatch_state':'not_started'})
njob=deepcopy(job);njob['test_cases'][0]['evidence']=[ref]
assert p.project(njob,nj,a)['request_sent'] is False
dup=deepcopy(njob);dup['test_cases'][0]['evidence'].append(deepcopy(ref))
assert p.project(dup,nj,a)['request_sent'] is None
no['receipt']['native_pre_dispatch_refusal']=False
assert p.project(njob,nj,a)['request_sent'] is None
for bad in [{**a,'extra':'x'},{**a,'source_job_id':'../../secret'},{**a,'operation_id':'op-short'}]:
    try:p.key(bad)
    except ValueError:pass
    else:raise AssertionError('bad scope admitted')
assert execute_tool(p.TOOL,a)['error']=='trusted_Core_job_case_context_required'
assert uqa.classify_tool_action(p.TOOL,a)=='observe'
with TemporaryDirectory() as tmp,patch.object(job_store,'JOBS_DIR',Path(tmp)):
    root=Path(tmp);(root/'operations').mkdir()
    paths=[root/(a['source_job_id']+'.json'),root/'operations'/(a['source_job_id']+'.json')]
    paths[0].write_text(json.dumps(job));paths[1].write_text(json.dumps(journal))
    current=job_store.create_job('Read bounded historical proof only',stand='lab',job_type='manual');jid=current['job_id']
    c=job_store.add_test_case(jid,'Fixture',requirement={'profile_id':p.PROFILE,'locked':True,'history_attempts':[a]});cid=c['case_id']
    job_store.set_job_status(jid,'running');job_store.update_test_case(jid,cid,status='running')
    before=[x.read_bytes() for x in paths];names=set(root.rglob('*'))
    result=p.inspect(a,jid,cid)
    assert result['request_sent'] is True and result['mutation_executed'] is False
    assert before==[x.read_bytes() for x in paths] and names==set(root.rglob('*'))
    bad={**a,'operation_id':'op-'+'b'*32}
    refused=uqa.execute_tool_with_policy(p.TOOL,bad,[],job_id=jid,case_id=cid,force_read_only=True)
    assert refused['error']=='locked_attempt_history_scope_required'
    raw=p._bytes
    def changing(path,limit):
        data=raw(path,limit)
        changing.calls+=1
        return data+b' ' if changing.calls==3 else data
    changing.calls=0
    with patch.object(p,'_bytes',side_effect=changing):
        try:p.inspect(a,jid,cid)
        except ValueError as e:assert str(e)=='history_changed_during_read'
        else:raise AssertionError('concurrent change accepted')
print('attempt history fixture PASS')
