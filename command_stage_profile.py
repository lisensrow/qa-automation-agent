"""Immutable four-stage command microcase. No dispatch or policy authority.

Initial and post-delivery inventory have distinct explicit stage IDs, avoiding
same-tool/same-arguments journal rebinding. Not wired into Core until accepted.
"""
from copy import deepcopy
from command_probe_contract import target,PROFILE_ID,PLUGIN,VERSION,CORE,ORIGIN

CREATE='browser_create_closed_command_stage_semantic'
READ='browser_inspect_closed_command_stage_semantic'
WORKFLOW='closed-command-probe-v1'
BOOK_SHA='7fef498ba403c70a48dcdfb5f80ef84cde927b7f6e8d947d3740ccaeaa415f53'
SOURCE={'kind':'reviewed_user_workbook','sha256':BOOK_SHA,'sheet':'1.3.27',
    'name_cell':'A11','version_cell':'B11','plugin_name':PLUGIN,'plugin_version':VERSION,
    'preparation_job':'20261016-012227-e00c785a','preparation_evidence':'ev-f10ef9db5d12'}
EXPECTED={'kind':'exact_private_marker_exit_zero','profile_id':PROFILE_ID,
    'period':None,'ttl':None,'run_as_user':'','stderr_empty':True,
    'fresh_owned_task_result':True,'same_ci_agent_session':True,
    'full_source_case_passed':False,'developer_confirmed_bug':False}
STAGES=(('initial_inventory','pluginAudit'),('deliver_command_plugin','managePlugin'),
        ('post_delivery_inventory','pluginAudit'),('execute_command',PLUGIN))

def stages_for(name):
    t=target(name)
    return [{'version':1,'workflow_id':WORKFLOW,'stage_id':sid,
        'resource_key':'agent-'+t['agent_id']+'-'+sid,'tool':CREATE,
        'arguments':{'target':name,'stage_id':sid},
        'verification':{'version':1,'kind':'owned_command_stage_execution','origin':ORIGIN,
            'target':name,'ci_id':t['ci_id'],'agent_id':t['agent_id'],'core_version':CORE,
            'plugin_name':PLUGIN,'plugin_version':VERSION,'task_name':task,'stage_id':sid}}
        for sid,task in STAGES]

def requirement(name,campaign):
    t=target(name)
    if not isinstance(campaign,str) or not 1<=len(campaign)<=80 or not campaign.replace('-','').isalnum():
        raise ValueError('bounded_command_campaign_required')
    return {'type':'closed_command_probe','stand':'lab','locked':True,'action_profile':'write_resource',
        'target':name,'ci_id':t['ci_id'],'agent_id':t['agent_id'],'ci_name':t['ci_name'],
        'core_version':CORE,'plugin_name':PLUGIN,'plugin_version':VERSION,'profile_id':PROFILE_ID,
        'campaign_id':campaign,'source_manifest':deepcopy(SOURCE),'expected_profile':deepcopy(EXPECTED),
        'operation_stages':stages_for(name)}

def validate_context(job,case_id,starting=False):
    if not isinstance(job,dict):raise ValueError('command_job_required')
    cases=job.get('test_cases')
    if not isinstance(cases,list) or len(cases)!=1:raise ValueError('single_command_case_required')
    c=cases[0];r=c.get('requirement') or {}
    if c.get('case_id')!=case_id:raise ValueError('own_command_case_required')
    expected=requirement(r.get('target'),r.get('campaign_id'))
    if (r!=expected or job.get('stand')!='lab' or job.get('job_type') not in {'manual','regression'}
        or job.get('status')!='running' or c.get('status')!='running' or job.get('resources')):
        raise ValueError('locked_command_profile_required')
    request=job.get('request')
    if not isinstance(request,str) or not all(x in request for x in [r['ci_id'],r['agent_id'],r['ci_name'],
        CORE,PLUGIN,VERSION,PROFILE_ID]):raise ValueError('original_command_request_scope_required')
    if starting and any(e.get('type')=='closed_command_runtime_started' for e in c.get('evidence',[])):
        raise ValueError('command_runtime_no_replay')
    return c,r

def admitted_write(job,case_id,args):
    _,r=validate_context(job,case_id)
    if not isinstance(args,dict) or set(args)!={'target','stage_id'}:raise ValueError('command_stage_args_closed')
    s=next((s for s in r['operation_stages'] if s['arguments']==args),None)
    if s is None:raise ValueError('command_stage_scope_mismatch')
    return deepcopy(s)

def metadata_payload(stage_id):
    """Source-grounded known wire bodies; not permission to send them."""
    if stage_id in {'initial_inventory','post_delivery_inventory'}:
        return {'name':'pluginAudit','period':None,'ttl':None,'run_as_user':'','additional_params':{}}
    if stage_id=='deliver_command_plugin':
        return {'plugins_to_update':[{'plugin_name':PLUGIN,'plugin_version':VERSION}],
            'plugins_to_delete':[],'check_endpoint_os_version':True}
    raise ValueError('command_payload_requires_private_marker_compiler')
