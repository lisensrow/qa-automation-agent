"""Pure fixtures, not plugin execution or autonomous acceptance."""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
import json
from plugin_audit_profiles import PROFILES,profile,summarize,scopes,stages_for,validate_context,validate_prior_delivery
from plugin_audit_runtime import catalog_for,evaluate_execution,CREATE,DELIVER,READ,READY,REPORT,REFRESH,RUN_AUDIT,compile_bound_action
from agent_audit_runtime import call_admitted
from tools.agent_update import pinned_audit_payload,pinned_plugin_payload,validate_locked_update_scope
from tools.registry import TOOLS

for name,(version,step,fields) in PROFILES.items():
    row={k:{'str':'x','number':1,'list':[],'bool':False}[kind] for k,kind in fields.items()}
    data=row if profile(name)['container']=='dict' else [row]
    result=summarize(name,data)
    assert result['structure_subset_matched'] and result['full_case_passed'] is False
    assert summarize(name,None)['structure_subset_matched'] is False
    bad=deepcopy(data);(bad if isinstance(bad,dict) else bad[0]).pop(next(iter(fields)))
    assert summarize(name,bad)['structure_subset_matched'] is False
    for kind in ('number','bool'):
        keys=[k for k,v in fields.items() if v==kind]
        if keys:
            bad=deepcopy(data);(bad if isinstance(bad,dict) else bad[0])[keys[0]]=True if kind=='number' else 1
            assert summarize(name,bad)['structure_subset_matched'] is False

scope={'ci_name':'host','agent_id':'agent','core_version':'1.3.27','task_name':'serviceAudit'}
r={'type':'pinned_plugin_audit','locked':True,'action_profile':'write_resource','pinned_audit_task':scope,
   'ci_id':'ci','expected_profile':profile('serviceAudit'),'allow_plugin_audit_refresh':True,
   'source_case':'US-T79','source_revision':'1.0-read-2026-10-16'}
audit,delivery=scopes(r);r['pinned_plugin_delivery']=delivery;r['operation_stages']=stages_for(r)
job={'stand':'lab','status':'running','resources':[],'request':' '.join(audit.values())+' pluginAudit',
     'test_cases':[{'case_id':'case','status':'running','requirement':r,'evidence':[]}]}
validate_context(job,'case');validate_locked_update_scope(job,job['test_cases'][0],audit,'pinned_audit_task')
validate_locked_update_scope(job,job['test_cases'][0],{**audit,'task_name':'pluginAudit'},'pinned_audit_task')
ci={'id':'ci','agent_id':'agent'};agent={'id':'agent','version':'1.3.27','status':'online'}
inventory={'agent_id':'agent','last_audit_at':datetime.now(timezone.utc).isoformat(),
    'detail':[{'plugin_name':'serviceAudit','plugin_version':'1.3.2','load_status':True,'load_error':''}]}
assert pinned_audit_payload(ci,agent,{'total':0,'items':[]},'agent','1.3.27','serviceAudit',inventory,'serviceAudit','1.3.2')['name']=='serviceAudit'
for task in ['executeCommand','changeState','configAudit']:
    try:pinned_audit_payload(ci,agent,{'total':0,'items':[]},'agent','1.3.27',task,inventory,task,'1.3.2')
    except ValueError:pass
    else:raise AssertionError('unreviewed task admitted')
assert pinned_plugin_payload(ci,agent,{'total':0,'items':[]},'agent','1.3.27','serviceAudit','1.3.2')['plugins_to_delete']==[]
ready={'tool':READY,'result':{'core_version':'1.3.27','agent_status':'online','ready':False,
    'plugin_audit':{'matched_plugins':[{'name':'serviceAudit','version':'1.2.25'}]}}}
assert not call_admitted(catalog_for(TOOLS,[],r),CREATE,audit)
assert call_admitted(catalog_for(TOOLS,[ready],r),DELIVER,delivery)
made={'tool':DELIVER,'result':{'task_id':'own','task_name':'managePlugin','mutation_executed':True}}
assert not call_admitted(catalog_for(TOOLS,[ready,made],r),CREATE,audit)
assert call_admitted(catalog_for(TOOLS,[ready,made],r),READ,{'ci_name':'host','agent_id':'agent','task_id':'own'})
assert not call_admitted(catalog_for(TOOLS,[ready,made],r),READ,{'ci_name':'host','agent_id':'agent','task_id':'invented'})
done={'tool':READ,'result':{'task_id':'own','operation_verification':{'verified':True}}}
assert call_admitted(catalog_for(TOOLS,[ready,made,done],r),REFRESH,{})
assert compile_bound_action(REFRESH,{},r)==(CREATE,{**audit,'task_name':'pluginAudit'})
assert compile_bound_action(RUN_AUDIT,{},r)==(CREATE,audit)
try:compile_bound_action(REFRESH,{'agent_id':'other'},r)
except ValueError:pass
else:raise AssertionError('bound scope must not be overridden')

now=datetime.now(timezone.utc);ts=lambda n:(now+timedelta(seconds=n)).isoformat()
def evidence(eid,tool,args,result,at):
    return {'evidence_id':eid,'source':'uqa_tool','execution_status':'observed','created_at':at,
        'value':json.dumps({'tool':tool,'arguments':args,'result':result})}
for stage in stages_for(r):
    task=stage['verification']['task_name']
    op={'operation_id':'op','case_id':'case','created_at':ts(-5),'receipt':{'acknowledged':True},
        **{k:stage[k] for k in ['workflow_id','stage_id','resource_key','tool']}}
    sent={'operation_id':'op','task_id':'own','task_name':task,'agent_id':'agent','session_id':'session',
        'request_origin':'https://uc.lab.local','mutation_executed':True,'create_status':202 if task=='managePlugin' else 201,
        'sent_at':ts(-4),'received_at':ts(-3),'server_created_at':ts(-3)}
    read={'task_id':'own','task_name':task,'agent_id':'agent','session_id':'session','ci_id':'ci','machine_uid':'ci',
        'request_origin':'https://uc.lab.local','native_result_verified':True,'identity_verified':True,'fresh_result':True,
        'task_status':'success','result_code':'success','read_at':ts(0),'server_created_at':ts(-3),'processed_at':ts(-1),
        'delivery_verified':True,'plugin_name':'serviceAudit','plugin_version':'1.3.2',
        'plugin_readiness':{'ready':True,'ci_id':'ci','agent_id':'agent','core_version':'1.3.27','agent_status':'online',
            'plugin_audit':{'audit_agent_id':'agent','audit_fresh':True,'last_audit_at':ts(-1),
                'matched_plugins':[{'name':'serviceAudit','version':'1.3.2','load_status':True,'load_error_present':False}]}}}
    j=deepcopy(job);j['test_cases'][0]['evidence']=[evidence('create',stage['tool'],stage['arguments'],sent,ts(-3)),
        evidence('read',READ,{'ci_name':'host','agent_id':'agent','task_id':'own'},read,ts(0))]
    proof=evaluate_execution(j,op,'read',stage['verification'])
    assert proof['verified'] and proof['business_pass'] is False and proof['resend_authorized'] is False
    for key,value in [('task_id','other'),('session_id','other'),('ci_id','other'),('fresh_result',False),('result_code','error')]:
        bad=deepcopy(j);b=json.loads(bad['test_cases'][0]['evidence'][1]['value']);b['result'][key]=value
        bad['test_cases'][0]['evidence'][1]['value']=json.dumps(b)
        assert not evaluate_execution(bad,op,'read',stage['verification'])['verified']
print('plugin_audit_profiles: PASS (9 bounded profiles, phase gates and 3 execution proofs; fixtures only)')
from operation_journal import _fingerprint
from plugin_audit_runtime import incomplete_terminal_feedback
feedback=incomplete_terminal_feedback(None,catalog_for(TOOLS,[ready,made,done],r))
assert feedback['automatic_action_taken'] is False
assert feedback['business_BLOCKED_does_not_complete_workflow'] is True
assert REFRESH in feedback['admitted_tools']
assert incomplete_terminal_feedback({'verdict':'BLOCKED'},[]) is None
original=deepcopy(job);stage=stages_for(r)[0]
prior_op={'operation_id':'old-op','case_id':'case','status':'verified',
    **{k:stage[k] for k in ['tool','workflow_id','stage_id','resource_key']},
    'arguments_fingerprint':_fingerprint(stage['arguments']),'verification_fingerprint':_fingerprint(stage['verification']),
    'verification':{'evidence_id':'old-read','postcondition_verified':True,'business_pass':False}}
original['test_cases'][0]['evidence']=[{'evidence_id':'old-read','source':'uqa_tool'}]
continued=deepcopy(r);continued['prior_verified_delivery']={'job_id':'old','case_id':'case','operation_id':'old-op'}
validate_prior_delivery(continued,lambda _:original,lambda _:[prior_op])
assert len(stages_for(continued))==2 and all(s['tool']!=DELIVER for s in stages_for(continued))
try:validate_prior_delivery(continued,lambda _:original,lambda _:[{**prior_op,'status':'uncertain'}])
except ValueError:pass
else:raise AssertionError('uncertain delivery cannot be adopted')
assert not call_admitted(catalog_for(TOOLS,[ready],continued),DELIVER,delivery)
assert call_admitted(catalog_for(TOOLS,[ready],continued),REFRESH,{})
