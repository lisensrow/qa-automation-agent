"""One isolated three-stage fixture; no browser/API or product mutations."""
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import job_store
import operation_journal as journal
import operation_workflow as workflow
import uqa

def rejects(call):
    try:call()
    except (ValueError,KeyError,StopIteration):return
    raise AssertionError('unsafe transition accepted')

def witness(jid,cid,items):
    stamp=datetime.now(timezone.utc).isoformat()
    request='fixture-'+str(len(job_store.get_job(jid)['test_cases'][0]['evidence']))
    result={'status':200,'method':'GET','url':'/fixture-members','request_id':request,
        'response_origin':'https://fixture.test','session_id':'fixture-session',
        'received_at':stamp,'request_started_at':stamp,'action_class':'observe','action_policy_status':'auto_allowed',
        'response_body':json.dumps({'items':items,'total':len(items),'count':len(items),'offset':0})}
    obs=uqa.record_tool_observations(jid,cid,'browser_get_network_detail',{'request_id':request},result)
    return uqa.record_tool_evidence(jid,cid,'browser_get_network_detail',{'request_id':request},result,
        observation_ids=[o['observation_id'] for o in obs])['evidence_id']

with TemporaryDirectory(prefix='uqa-owned-workflow-') as root, patch.object(job_store,'JOBS_DIR',Path(root)):
    jid=job_store.create_job('Isolated lifecycle',job_type='regression')['job_id']
    cid=job_store.add_test_case(jid,'Single lifecycle')['case_id']
    job_store.add_observation(jid,cid,'ui_state','browser',{'session_id':'fixture-session','url':'https://fixture.test/'})
    baseline=witness(jid,cid,[])
    old,new='uqa-test-fixture','uqa-test-fixture-renamed'
    common={'version':1,'origin':'https://fixture.test','endpoint':'/fixture-members'}
    owned={**common,'selector':{'id':{'binding':'identifier_scalar'}},'resource_id':{'binding':'resource_id'},
        'baseline_evidence_id':{'binding':'previous_evidence_id'}}
    plan={'version':1,'workflow_id':'fixture-flow','resource_key':'fixture-key','resource_type':'fixture',
        'resource_name':old,'renamed_name':new,'stages':[
        {'stage_id':'create','tool':'browser_click_semantic','arguments':{'name':'Save'},
         'verification':{**common,'kind':'member_present','baseline_evidence_id':baseline,
             'selector':{'name':old},'expected_fields':{'name':old,'parent_id':0}}},
        {'stage_id':'rename','tool':'browser_click_semantic','arguments':{'name':'Save'},
         'verification':{**owned,'kind':'member_present','expected_fields':{'name':new,'parent_id':0},'allowed_changed_fields':['name']}},
        {'stage_id':'cleanup','tool':'browser_delete_json_resource','arguments':{'collection_endpoint':'/fixture-members',
             'exact_name':new,'expected_identifier':{'binding':'identifier_string'}},
         'verification':{**owned,'kind':'member_absent'}}]}
    job=job_store.get_job(jid)
    job['test_cases'][0]['requirement']={'locked':True,'type':'owned_resource_workflow','operation_workflow':plan}
    job_store.save_job(job);stale=deepcopy(job)
    workflow.initialize_workflow(jid,cid)
    altered=deepcopy(plan);altered['stages'][1]['verification']['allowed_changed_fields'].append('parent_id')
    rejects(lambda:workflow._validate(altered))
    operations=[];resource=None
    for index,items in enumerate(([{'id':1,'name':old,'parent_id':0}],[{'id':1,'name':new,'parent_id':0}],[])):
        stage=workflow.current_stage(jid,cid)
        assert stage['stage_id']==['create','rename','cleanup'][index]
        if index:
            assert stage['verification']['selector']=={'id':1}
            assert stage['verification']['resource_id']==resource['resource_id']
        claim=journal.begin_operation(job_id=jid,case_id=cid,workflow_id=stage['workflow_id'],stage_id=stage['stage_id'],
            resource_key=stage['resource_key'],tool=stage['tool'],arguments=stage['arguments'],verification_contract=stage['verification'])
        assert claim['allowed'];opid=claim['operation_id'];operations.append(opid)
        rejects(lambda:workflow.advance_workflow(jid,cid,opid))
        proof=journal.reconcile_operation(jid,opid,witness(jid,cid,items))
        assert proof['verified'] and not proof['resend_authorized']
        if index==0:
            rejects(lambda:workflow.advance_workflow(jid,cid,opid))
            bad=job_store.add_test_resource(jid,'fixture',name=old,external_id='99',created_by_case=cid,metadata={'disposable':True})
            rejects(lambda:workflow.attach_resource(jid,cid,bad['resource_id']))
            resource=job_store.add_test_resource(jid,'fixture',name=old,external_id='1',created_by_case=cid,metadata={'disposable':True})
            assert workflow.attach_resource(jid,cid,resource['resource_id'])['bound']
            duplicate=job_store.add_test_resource(jid,'fixture',name=old,external_id='1',created_by_case=cid,metadata={'disposable':True})
            rejects(lambda:workflow.attach_resource(jid,cid,duplicate['resource_id']))
        transition=workflow.advance_workflow(jid,cid,opid)
        assert transition['stage_index']==index+1 and not transition['product_evidence']
        rejects(lambda:workflow.advance_workflow(jid,cid,opid))
        if index==0:
            # Legacy stale whole-Job writes cannot roll the durable stage back.
            snapshot=job_store.get_job(jid)
            job_store.save_job(stale)
            assert workflow.current_stage(jid,cid)['stage_id']=='rename'
            # Whole-Job storage remains outside this journal's transaction guarantees.
            job_store.save_job(snapshot)
    assert len(journal.list_operations(jid))==3 and workflow.workflow_state(jid,cid)['completed']
    assert len(job_store.get_job(jid)['test_cases'])==1
    assert job_store.get_test_resource(jid,resource['resource_id'])['status']=='active'
    checks,errors=uqa.verify_structured_check_evidence(jid,cid,[{'check_id':'fixture-check','title':'Lifecycle','status':'passed','evidence_ids':[]}])
    assert checks[0]['status']=='blocked' and errors
    for name in ('operation_workflow_state','operation_attach_resource','operation_advance'):
        assert uqa.classify_tool_action(name,{})=='observe'
print('PASS owned operation workflow: one case, three durable stages, typed immutable ID, proof-gated transitions, no product PASS or permission grant')
