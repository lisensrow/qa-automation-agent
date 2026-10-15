"""Isolated native execution proof and durable pre-dispatch provenance checks."""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import job_store
import operation_journal as journal
from audit_operation_recovery import evaluate,stages_for,ORIGIN
from native_dispatch import AuditPreflightRefused

now=datetime.now(timezone.utc)
ts=lambda n:(now+timedelta(seconds=n)).isoformat()
scope={'ci_name':'host','agent_id':'agent','core_version':'1.3.27','task_name':'osAudit'}
stages=stages_for(scope,'ci');stage=stages[-1];contract=stage['verification']
op={'operation_id':'op-1','case_id':'case','created_at':ts(-4),'receipt':{'acknowledged':True},
    **{k:stage[k] for k in ('tool','workflow_id','stage_id','resource_key')}}
created={'operation_id':'op-1','task_id':'task','agent_id':'agent','task_name':'osAudit',
    'mutation_executed':True,'executed':True,'create_status':201,'request_origin':ORIGIN,'session_id':'session',
    'sent_at':ts(-3),'received_at':ts(-2),'server_created_at':ts(-2)}
read={'task_id':'task','agent_id':'agent','task_name':'osAudit','ci_id':'ci','machine_uid':'ci',
    'native_result_verified':True,'identity_verified':True,'fresh_result':True,'task_status':'success',
    'session_id':'session','request_origin':ORIGIN,'read_at':ts(0),'processed_at':ts(-1),'server_created_at':ts(-2)}
def ev(eid,tool,args,result,at):
    return {'evidence_id':eid,'source':'uqa_tool','execution_status':'observed','created_at':at,
        'value':json.dumps({'tool':tool,'arguments':args,'result':result})}
receipt=ev('create',stage['tool'],stage['arguments'],created,ts(-2))
reader=ev('read','browser_inspect_pinned_agent_audit_semantic',
          {'ci_name':'host','agent_id':'agent','task_id':'task'},read,ts(0))
req={'type':'pinned_agent_audit','locked':True,'allow_plugin_audit_refresh':True,
    'pinned_audit_task':scope,'expected_subset':{'machine_uid':'ci'},'operation_stages':stages}
job={'stand':'lab','test_cases':[{'case_id':'case','requirement':req,'evidence':[receipt,reader]}]}
proof=evaluate(job,op,'read',contract)
assert proof['verified'] is True and proof['business_pass'] is False and proof['resend_authorized'] is False
for field,value in [('task_id','other'),('agent_id','other'),('session_id','other'),('fresh_result',False),('task_status','error')]:
    j=deepcopy(job);d=json.loads(j['test_cases'][0]['evidence'][1]['value']);d['result'][field]=value
    j['test_cases'][0]['evidence'][1]['value']=json.dumps(d)
    assert evaluate(j,op,'read',contract)['verified'] is False
j=deepcopy(job);j['test_cases'][0]['evidence'][1]['source']='local_model_generated_report'
assert evaluate(j,op,'read',contract)['verified'] is False
assert evaluate(job,{**op,'receipt':{'acknowledged':False}},'read',contract)['verified'] is False
assert evaluate(job,op,'read',{**contract,'origin':'https://other'})['verified'] is False
# Refresh execution requires a new, loaded, exact plugin inventory as well as
# the owned pluginAudit task result. ACK alone or old inventory is insufficient.
refresh=stages[0]
j=deepcopy(job)
c={**created,'task_name':'pluginAudit'}
r={**read,'task_name':'pluginAudit','plugin_readiness':{
    'ready':True,'agent_id':'agent','ci_id':'ci','core_version':'1.3.27','agent_status':'online',
    'plugin_audit':{'audit_fresh':True,'audit_agent_id':'agent','last_audit_at':ts(-1),
        'matched_plugins':[{'name':'osAudit','version':'1.3.4','load_status':True,'load_error_present':False}]}}}
j['test_cases'][0]['evidence']=[ev('create',refresh['tool'],refresh['arguments'],c,ts(-2)),
    ev('read','browser_inspect_pinned_agent_audit_semantic',
       {'ci_name':'host','agent_id':'agent','task_id':'task'},r,ts(0))]
refresh_op={**op,**{k:refresh[k] for k in ('tool','workflow_id','stage_id','resource_key')}}
assert evaluate(j,refresh_op,'read',refresh['verification'])['verified'] is True
bad=deepcopy(j);d=json.loads(bad['test_cases'][0]['evidence'][1]['value'])
d['result']['plugin_readiness']['plugin_audit']['last_audit_at']=ts(-600)
bad['test_cases'][0]['evidence'][1]['value']=json.dumps(d)
assert evaluate(bad,refresh_op,'read',refresh['verification'])['verified'] is False
# A JSON copy cannot assert that an ambiguous operation was never sent.
with TemporaryDirectory(prefix='uqa-audit-journal-') as directory,patch.object(job_store,'JOBS_DIR',Path(directory)):
    def ctx(tool='browser_create_pinned_agent_audit_semantic'):
        j=job_store.create_job('Isolated journal fixture',stand='lab',job_type='manual')
        c=job_store.add_test_case(j['job_id'],'Fixture')
        return {'job_id':j['job_id'],'case_id':c['case_id'],'workflow_id':'fixture','stage_id':'create',
            'resource_key':'fixture','tool':tool,'arguments':{'fixture':True}}
    native=AuditPreflightRefused(error='preflight',executed=False,mutation_executed=False,dispatch_state='not_started')
    c=ctx();assert journal.execute_journaled(c,lambda:native)['operation_status']=='not_sent'
    assert journal.inspect_operation(**c)['allowed'] is True
    for fake in (dict(native),json.loads(json.dumps(native)),AuditPreflightRefused(dict(native,executed=True))):
        c=ctx();assert journal.execute_journaled(c,lambda:fake)['operation_status']=='uncertain'
    c=ctx('other_tool');assert journal.execute_journaled(c,lambda:native)['operation_status']=='uncertain'
print('audit_operation_recovery: PASS (execution only, not business PASS; isolated fixtures)')
