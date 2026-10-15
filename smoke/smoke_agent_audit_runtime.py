"""Admission and fail-closed policies only, no LLM, UC or business mutation."""
from copy import deepcopy
from agent_audit_runtime import validate_context, validate_baseline, run, TOOL_NAMES, admitted_catalog, call_admitted, admission_refusal
from audit_operation_recovery import stages_for
import json
scope={'ci_name':'example','agent_id':'agent','core_version':'1.3.27','task_name':'osAudit'}
expected={'host_name':'example','machine_uid':'ci','os':{'architecture':'64','current_build_os':'1',
    'family':'windows','name':'windows','version':'edition'}}
req={'type':'pinned_agent_audit','action_profile':'write_resource','oracle_kind':'legacy_os_baseline_comparison',
    'locked':True,'baseline_sha256':'a'*64,'pinned_audit_task':scope,'expected_subset':expected,
    'baseline_ref':{'job_id':'20261015-000000-aaaaaaaa','case_id':'tc-aaaaaaaa','evidence_id':'ev-aaaaaaaaaaaa'},
    'operation_stage':{'version':1,'tool':'browser_create_pinned_agent_audit_semantic','arguments':scope,
        'workflow_id':'workflow','stage_id':'create-once','resource_key':'agent-osAudit'}}
req.update(allow_plugin_audit_refresh=True,operation_stages=stages_for(scope,'ci'))
req['operation_stage']=req['operation_stages'][-1]
job={'job_id':'job','job_type':'manual','status':'running','stand':'lab','request':' '.join(scope.values()),
     'resources':[],'test_cases':[{'case_id':'case','status':'running','requirement':req,'evidence':[]}]}
job['request']+=' pluginAudit'
validate_context(job,'case')
prior={'job_id':'20261015-000000-aaaaaaaa','stand':'lab','test_cases':[{'case_id':'tc-aaaaaaaa','evidence':[{
    'evidence_id':'ev-aaaaaaaaaaaa','source':'operator_existing_task_list_and_full_get',
    'type':'operator_historical_os_task_shape_v298','execution_status':'observed',
    'value':json.dumps({'full_sha256':'a'*64,'identity_correlated':True,'historical_result_only':True,
        'new_task_created':False,'full':{'agent_id':'agent','name':'osAudit',
            'result':{'machine_uid':'ci','data':{'host_name':'example','os':expected['os']}}}})}]}]}
validate_baseline(job,req,lambda _:prior)
bad=deepcopy(req);bad['expected_subset']['os']['name']='invented'
try: validate_baseline(job,bad,lambda _:prior)
except ValueError: pass
else: raise AssertionError('model must not invent expected')
def rejected(j):
    try: validate_context(j,'case')
    except ValueError: return
    raise AssertionError('must fail closed')
for key,value in [('stand','prod'),('status','blocked'),('resources',[{}]),('job_type','advisory'),('request','audit')]:
    j=deepcopy(job);j[key]=value;rejected(j)
for key,value in [('locked',False),('type','other'),('oracle_kind','model_expected'),('baseline_sha256','bad')]:
    j=deepcopy(job);j['test_cases'][0]['requirement'][key]=value;rejected(j)
j=deepcopy(job);j['test_cases'][0]['evidence']=[{'type':'pinned_audit_runtime_started'}];rejected(j)
j=deepcopy(job);j['test_cases'][0]['requirement']['operation_stage']['arguments']={};rejected(j)
assert run(None,[],'job','case','legacy')['started'] is False
assert run(None,[],'job','case','confirm_mutations',True)['started'] is False
assert 'agent_build_pinned_audit_report' in TOOL_NAMES and 'browser_click_semantic' not in TOOL_NAMES
from tools.registry import TOOLS
catalog=admitted_catalog(TOOLS,[],scope)
assert not call_admitted(catalog,'browser_create_pinned_agent_audit_semantic',scope)
assert admission_refusal(catalog)['current_native_fact_bound_operations']==[]
stale=[{'tool':'browser_inspect_pinned_agent_readiness_semantic','result':{
    'ready':False,'plugin_audit':{'reason':'plugin_audit_stale'}}}]
catalog=admitted_catalog(TOOLS,stale,scope)
assert admission_refusal(catalog)['current_native_fact_bound_operations'][0]['exact_arguments']['task_name']=='pluginAudit'
assert call_admitted(catalog,'browser_create_pinned_agent_audit_semantic',{**scope,'task_name':'pluginAudit'})
assert not call_admitted(catalog,'browser_create_pinned_agent_audit_semantic',scope)
created={'tool':'browser_create_pinned_agent_audit_semantic','result':{
    'mutation_executed':True,'task_id':'own','task_name':'pluginAudit'}}
catalog=admitted_catalog(TOOLS,stale+[created],scope)
assert call_admitted(catalog,'browser_inspect_pinned_agent_audit_semantic',
    {'ci_name':'example','agent_id':'agent','task_id':'own'})
assert not call_admitted(catalog,'browser_inspect_pinned_agent_audit_semantic',
    {'ci_name':'example','agent_id':'agent','task_id':'invented'})
assert not call_admitted(catalog,'browser_create_pinned_agent_audit_semantic',scope)
goodread={'tool':'browser_inspect_pinned_agent_audit_semantic','result':{
    'task_id':'own','operation_verification':{'verified':True},'plugin_readiness':{'ready':True}}}
catalog=admitted_catalog(TOOLS,stale+[created,goodread],scope)
assert call_admitted(catalog,'browser_create_pinned_agent_audit_semantic',scope)
assert not call_admitted(catalog,'browser_create_pinned_agent_audit_semantic',{**scope,'task_name':'pluginAudit'})
print('agent_audit_runtime: PASS (admission only; not autonomous acceptance)')
