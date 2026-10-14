"""Accepted operation identity cannot be replaced by a later same-name member."""
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import job_store
import operation_journal as journal
import uqa

def witness(jid,cid,items):
    stamp=datetime.now(timezone.utc).isoformat()
    request='proof-'+str(len(job_store.get_job(jid)['test_cases'][0]['evidence']))
    result={'status':200,'method':'GET','url':'/fixture-members','request_id':request,
        'response_origin':'https://fixture.test','session_id':'fixture-session',
        'received_at':stamp,'request_started_at':stamp,'action_class':'observe','action_policy_status':'auto_allowed',
        'response_body':json.dumps({'items':items,'total':len(items),'count':len(items),'offset':0})}
    obs=uqa.record_tool_observations(jid,cid,'browser_get_network_detail',{'request_id':request},result)
    return uqa.record_tool_evidence(jid,cid,'browser_get_network_detail',{'request_id':request},result,
        observation_ids=[o['observation_id'] for o in obs])['evidence_id']

with TemporaryDirectory(prefix='uqa-immutable-proof-') as root, patch.object(job_store,'JOBS_DIR',Path(root)):
    jid=job_store.create_job('Isolated immutable proof',job_type='regression')['job_id']
    cid=job_store.add_test_case(jid,'Fixture')['case_id']
    job_store.add_observation(jid,cid,'ui_state','browser',{'session_id':'fixture-session','url':'https://fixture.test/'})
    baseline=witness(jid,cid,[])
    oracle={'version':1,'kind':'member_present','origin':'https://fixture.test','endpoint':'/fixture-members',
        'baseline_evidence_id':baseline,'selector':{'name':'uqa-test-fixture'},'expected_fields':{'name':'uqa-test-fixture'}}
    stage={'version':1,'workflow_id':'proof-flow','stage_id':'create','resource_key':'fixture-key',
        'tool':'fixture-send','arguments':{'name':'Save'},'verification':oracle}
    job=job_store.get_job(jid);job['test_cases'][0]['requirement']={'locked':True,'operation_stage':stage};job_store.save_job(job)
    claim=journal.begin_operation(job_id=jid,case_id=cid,workflow_id='proof-flow',stage_id='create',resource_key='fixture-key',
        tool='fixture-send',arguments=stage['arguments'],verification_contract=oracle)
    evidence=witness(jid,cid,[{'id':1,'name':'uqa-test-fixture'}])
    assert journal.reconcile_operation(jid,claim['operation_id'],evidence)['verified']
    saved=journal.list_operations(jid)[0]
    replacement=witness(jid,cid,[{'id':99,'name':'uqa-test-fixture'}])
    assert journal.reconcile_operation(jid,claim['operation_id'],replacement)['reason']=='operation_verification_immutable'
    assert journal.list_operations(jid)[0]==saved
    replay=journal.reconcile_operation(jid,claim['operation_id'],evidence)
    assert replay['verified'] and replay['identifier_value']=='1' and not replay['resend_authorized']
    assert journal.list_operations(jid)[0]==saved
print('PASS operation proof immutability: later same-name ID rejected, same evidence idempotent, no state rewrite or resend')
