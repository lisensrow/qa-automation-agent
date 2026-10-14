"""Evidence-only recovery of fixture intents; no API, browser or mutation calls."""
import json
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import job_store
import operation_journal as journal
from operation_recovery import evaluate_recovery
import uqa

def now():return datetime.now(timezone.utc).isoformat()
def witness(jid,cid,items,received=None,**overrides):
    received=received or now()
    request='fixture-'+str(len(job_store.get_job(jid)['test_cases'][0]['evidence']))
    result={'status':200,'method':'GET','url':'/fixture-members?limit=0','request_id':request,
            'response_origin':'https://fixture.test',
            'session_id':'fixture-session','action_execution_id':'fixture-read',
            'received_at':received,'request_started_at':received,'action_class':'observe','action_policy_status':'auto_allowed',
            'response_body':json.dumps({'items':items,'total':len(items),'count':len(items),'offset':0})}
    result.update(overrides)
    obs=uqa.record_tool_observations(jid,cid,'browser_get_network_detail',{'request_id':request},result)
    evidence=uqa.record_tool_evidence(jid,cid,'browser_get_network_detail',{'request_id':request},result,
        observation_ids=[o['observation_id'] for o in obs])
    return evidence['evidence_id']

with TemporaryDirectory(prefix='uqa-operation-recovery-') as root, patch.object(job_store,'JOBS_DIR',Path(root)):
    job=job_store.create_job('Isolated recovery fixture',job_type='regression')
    jid=job['job_id'];case=job_store.add_test_case(jid,'Fixture');cid=case['case_id']
    job_store.add_observation(jid,cid,'ui_state','browser',{'session_id':'fixture-session','url':'https://fixture.test/'})
    baseline=witness(jid,cid,[])
    contract={'version':1,'kind':'member_present','origin':'https://fixture.test','endpoint':'/fixture-members',
              'baseline_evidence_id':baseline,'selector':{'name':'owned-fixture'},'expected_fields':{'name':'owned-fixture','parent_id':0}}
    stage={'version':1,'workflow_id':'fixture-workflow','stage_id':'create','resource_key':'owned-fixture',
           'tool':'fixture_send','arguments':{'name':'Save'},'verification':contract}
    job=job_store.get_job(jid);job['test_cases'][0]['requirement']={'locked':True,'operation_stage':stage};job_store.save_job(job)
    claim=journal.begin_operation(job_id=jid,case_id=cid,workflow_id=stage['workflow_id'],stage_id='create',resource_key='owned-fixture',
                                  tool=stage['tool'],arguments=stage['arguments'],verification_contract=contract)
    op=journal.list_operations(jid)[0]
    # Timeout or crash leaves 'sending'. A cached old response read now is stale.
    stale=witness(jid,cid,[{'id':1,'name':'owned-fixture','parent_id':0}],received=(datetime.fromisoformat(op['created_at'])-timedelta(seconds=1)).isoformat())
    assert not journal.reconcile_operation(jid,claim['operation_id'],stale)['verified']
    overlapping=witness(jid,cid,[{'id':1,'name':'owned-fixture','parent_id':0}],request_started_at=(datetime.fromisoformat(op['created_at'])-timedelta(seconds=1)).isoformat())
    assert not journal.reconcile_operation(jid,claim['operation_id'],overlapping)['verified']
    empty=witness(jid,cid,[])
    assert not journal.reconcile_operation(jid,claim['operation_id'],empty)['verified']
    assert journal.list_operations(jid)[0]['status']=='sending'  # NO retry permit.
    current=witness(jid,cid,[{'id':1,'name':'owned-fixture','parent_id':0}])
    basejob=job_store.get_job(jid)
    def reject(change):
        altered=deepcopy(basejob);change(altered)
        assert not evaluate_recovery(altered,op,current,contract)['verified']
    reject(lambda j:j['test_cases'][0]['evidence'][-1].update(usable_for_verdict=False))
    reject(lambda j:j['test_cases'][0]['evidence'][-1].update(observation_ids=[]))
    reject(lambda j:j['test_cases'][0]['observations'][0]['data'].update(url='https://wrong.test/'))
    invalid=witness(jid,cid,[{'id':1,'name':'owned-fixture','parent_id':0}],status=500)
    assert not journal.reconcile_operation(jid,claim['operation_id'],invalid)['verified']
    other_origin=witness(jid,cid,[{'id':1,'name':'owned-fixture','parent_id':0}],response_origin='https://wrong.test')
    assert not journal.reconcile_operation(jid,claim['operation_id'],other_origin)['verified']
    partial=witness(jid,cid,[{'id':1,'name':'owned-fixture','parent_id':0}],response_body=json.dumps({'items':[{'id':1,'name':'owned-fixture','parent_id':0}],'total':2,'count':1,'offset':0}))
    assert not journal.reconcile_operation(jid,claim['operation_id'],partial)['verified']
    foreign=job_store.add_test_case(jid,'Other case')
    # Evidence belongs to the current operation's case only.
    other=witness(jid,foreign['case_id'],[{'id':1,'name':'owned-fixture','parent_id':0}])
    assert not journal.reconcile_operation(jid,claim['operation_id'],other)['verified']
    changed=job_store.get_job(jid);changed['test_cases'][0]['requirement']['operation_stage']['verification']['expected_fields']['parent_id']=99;job_store.save_job(changed)
    assert journal.reconcile_operation(jid,claim['operation_id'],current)['reason']=='recovery_contract_missing_or_changed'
    restored=job_store.get_job(jid);restored['test_cases'][0]['requirement']['operation_stage']=deepcopy(stage);job_store.save_job(restored)
    verified=journal.reconcile_operation(jid,claim['operation_id'],current)
    assert verified['verified'] and verified['operation_status']=='verified' and verified['resend_authorized'] is False
    assert verified['causal_execution_proven'] is False and verified['product_evidence'] is False
    assert journal.list_operations(jid)[0]['status']=='verified'
    assert not journal.inspect_operation(jid,cid,'fixture-workflow','create','owned-fixture',{'name':'Save'})['allowed']
    resource=job_store.add_test_resource(jid,'fixture',name='owned-fixture',external_id='1',created_by_case=cid,metadata={'disposable':True})
    delete_baseline=witness(jid,cid,[{'id':1,'name':'owned-fixture','parent_id':0}])
    delete_contract={'version':1,'kind':'member_absent','origin':'https://fixture.test','endpoint':'/fixture-members',
        'baseline_evidence_id':delete_baseline,'selector':{'id':1},'resource_id':resource['resource_id']}
    delete_stage={**stage,'stage_id':'delete','tool':'fixture_delete','verification':delete_contract}
    job=job_store.get_job(jid);job['test_cases'][0]['requirement']['operation_stage']=delete_stage;job_store.save_job(job)
    deleting=journal.begin_operation(job_id=jid,case_id=cid,workflow_id='fixture-workflow',stage_id='delete',resource_key='owned-fixture',
        tool='fixture_delete',arguments=stage['arguments'],verification_contract=delete_contract)
    still_present=witness(jid,cid,[{'id':1,'name':'owned-fixture','parent_id':0}])
    assert not journal.reconcile_operation(jid,deleting['operation_id'],still_present)['verified']
    absent=witness(jid,cid,[])
    deleted=journal.reconcile_operation(jid,deleting['operation_id'],absent)
    assert deleted['verified'] and deleted['resend_authorized'] is False
    # Journal resolution is neither resource cleanup nor product PASS itself.
    assert job_store.get_test_resource(jid,resource['resource_id'])['status']=='active'
    assert uqa.classify_tool_action('operation_reconcile',{})=='observe'
    assert uqa.classify_tool_action('operation_list',{})=='observe'
print('PASS operation recovery: fresh complete native GET, baseline and case binding, stale/partial/foreign/replaced proof rejected; no resend authorization')
