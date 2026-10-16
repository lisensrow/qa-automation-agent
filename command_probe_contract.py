"""Pure, closed command microcase contracts. NO dispatch or permission authority.

Separate from parameterless inventory profiles. Runtime/journal integration and
real-model acceptance are required before this module enables any product action.
"""
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import re
from uuid import UUID
from tools.agent_plugins import summarize_plugin_audit
from tools.agent_update import audit_result_is_fresh

PROFILE_ID='executeCommand-private-marker-v1'
PLUGIN='executeCommand'
VERSION='1.4.0'
CORE='1.3.27'
ORIGIN='https://uc.lab.local'
TARGETS={
    'windows':{'ci_name':'home-server-UC-windows10','agent_id':'71724f3b-41b9-449b-9075-1dd6c8e1c2df',
        'ci_id':'c0951a10-3e93-58f9-9468-4702734b417f','program':r'C:\Windows\System32\cmd.exe',
        'prefix':['/d','/s','/c','echo'],'os_tokens':['windows']},
    'astra':{'ci_name':'home-server-UC-astra18','agent_id':'c5333d68-f1c2-4186-aac1-c6a461f11aa0',
        'ci_id':'2a3c9a50-cde8-558e-9e52-6a2de1bfc7fd','program':'/usr/bin/printf',
        'prefix':[],'os_tokens':['astra']}}

def target(name):
    if name not in TARGETS:raise ValueError('dedicated_command_target_required')
    return deepcopy(TARGETS[name])

def marker_valid(marker):
    return isinstance(marker,str) and re.fullmatch(r'UQA_EXEC_OK_[0-9a-f]{32}',marker) is not None

def payload(name,marker):
    """Only an internal fresh marker; no model-controlled program/args/user/period."""
    t=target(name)
    if not marker_valid(marker):raise ValueError('private_marker_invalid')
    return {'name':PLUGIN,'period':None,'ttl':None,'run_as_user':'',
        'additional_params':{'programm':t['program'],'arguments':[*t['prefix'],marker]}}

def validate_preflight(name,ci,agent,audit,tasks,now=None):
    """Caller must supply actual native same-origin GETs, not model declarations."""
    t=target(name)
    if (not isinstance(ci,dict) or not isinstance(agent,dict) or
        (ci.get('id'),ci.get('name'),ci.get('agent_id'))!=(t['ci_id'],t['ci_name'],t['agent_id']) or
        (agent.get('id'),agent.get('version'),agent.get('status'))!=(t['agent_id'],CORE,'online')):
        raise ValueError('dedicated_core_target_not_ready')
    os_name=ci.get('os_name')
    if not isinstance(os_name,str) or not any(x in os_name.casefold() for x in t['os_tokens']):
        raise ValueError('command_os_not_observed')
    detail=ci.get('detail')
    os_info=detail.get('os') if isinstance(detail,dict) else None
    if not isinstance(os_info,dict) or os_info.get('architecture') not in {'64','x86_64','amd64'}:
        raise ValueError('command_architecture_not_observed')
    checked=summarize_plugin_audit(ci,audit,PLUGIN,VERSION,observed_at=now,max_age_seconds=3600)
    if (checked['observation_result']!='PASS' or len(checked['matched_plugins'])!=1 or
        checked['matched_plugins'][0]['load_error_present']):raise ValueError('fresh_command_plugin_not_loaded')
    items=tasks.get('items') if isinstance(tasks,dict) else None
    if (not isinstance(items,list) or type(tasks.get('total')) is not int or tasks['total']!=len(items)
        or tasks.get('offset',0)!=0 or len(items)>10000):raise ValueError('complete_command_task_list_required')
    for item in items:
        if (not isinstance(item,dict) or item.get('agent_id')!=t['agent_id'] or item.get('name')!=PLUGIN
            or item.get('period') is not None or item.get('status') not in {'success','error','timeout'}):
            raise ValueError('existing_command_task_unresolved_or_scope_mismatch')
    return {'profile_id':PROFILE_ID,'target':name,'core_version':CORE,'plugin_version':VERSION,
        'ready':True,'execution_verified':False,'business_pass':False}

def validate_created(name,marker,response,sent_at,received_at,session_id):
    """Validate a NEW task receipt, never adopt a historical or arbitrary task."""
    t=target(name);expected=payload(name,marker)
    if not isinstance(response,dict):raise ValueError('command_receipt_missing_dispatch_uncertain')
    try:
        if str(UUID(response.get('id')))!=response['id']:raise ValueError('noncanonical task id')
    except (ValueError,TypeError,AttributeError):raise ValueError('command_receipt_id_invalid_dispatch_uncertain')
    if (response.get('agent_id')!=t['agent_id'] or response.get('name')!=PLUGIN
        or 'period' not in response or response['period'] is not None
        or 'ttl' not in response or response['ttl'] is not None or response.get('run_as_user')!=''):
        raise ValueError('command_receipt_scope_invalid_dispatch_uncertain')
    params=response.get('additional_params')
    if (not isinstance(params,dict) or set(params)-{'programm','arguments','command'}
        or params.get('programm')!=expected['additional_params']['programm']
        or params.get('arguments')!=expected['additional_params']['arguments']
        or params.get('command') is not None):raise ValueError('command_receipt_params_invalid_dispatch_uncertain')
    def stamp(s):
        d=datetime.fromisoformat(str(s).replace('Z','+00:00'))
        if d.tzinfo is None:raise ValueError('timezone required')
        return d
    try:
        sent,received,created=map(stamp,[sent_at,received_at,response.get('created_at')])
        valid=0<=(received-sent).total_seconds()<=30 and -120<=(received-created).total_seconds()<=300
    except (ValueError,TypeError,OverflowError):valid=False
    if not valid or not isinstance(session_id,str) or not session_id:
        raise ValueError('command_receipt_time_session_invalid_dispatch_uncertain')
    return {'task_id':response['id'],'agent_id':t['agent_id'],'ci_id':t['ci_id'],'ci_name':t['ci_name'],
        'target':name,'task_name':PLUGIN,'profile_id':PROFILE_ID,'session_id':session_id,
        'sent_at':sent_at,'received_at':received_at,'server_created_at':response['created_at'],
        'expected_marker_sha256':hashlib.sha256(marker.encode()).hexdigest(),
        'expected_marker':marker,'request_origin':ORIGIN}

def verify_result(own,full,session_id,now=None):
    """Exact stdout/error+own task/CI/time; never expose stdout/marker to the model."""
    if not isinstance(own,dict) or own.get('profile_id')!=PROFILE_ID:raise ValueError('owned_command_receipt_required')
    t=target(own['target']);marker=own.get('expected_marker')
    if (not marker_valid(marker) or own.get('expected_marker_sha256')!=hashlib.sha256(marker.encode()).hexdigest()
        or own.get('request_origin')!=ORIGIN or own.get('session_id')!=session_id
        or any(own.get(k)!=t[k] for k in ['ci_id','agent_id','ci_name'])):
        raise ValueError('owned_command_scope_session_invalid')
    if (not isinstance(full,dict) or full.get('id')!=own['task_id'] or full.get('agent_id')!=t['agent_id']
        or full.get('name')!=PLUGIN or 'period' not in full or full['period'] is not None
        or full.get('status')!='success'):raise ValueError('own_command_full_not_successful')
    envelope=full.get('result')
    if not isinstance(envelope,dict) or envelope.get('machine_uid')!=t['ci_id']:
        raise ValueError('own_command_result_ci_missing_or_mismatch')
    if not audit_result_is_fresh(own['sent_at'],own['received_at'],own['server_created_at'],
        full.get('created_at'),envelope.get('processed_at'),now=now):raise ValueError('own_command_result_not_fresh')
    data=envelope.get('data')
    if isinstance(data,dict) and isinstance(data.get('stdout'),str):
        stdout,code,stderr=data['stdout'],data.get('errorlevel'),data.get('stderr')
        shape='data_stdout_errorlevel'
    else:
        stdout,code,stderr=envelope.get('result'),envelope.get('error_code'),envelope.get('error_msg')
        shape='legacy_result_error_code'
    # Exact stripped newline framing, not substring: extra output is a mismatch.
    if not isinstance(stdout,str) or len(stdout)>len(marker)+2 or stdout.rstrip('\r\n')!=marker:
        raise ValueError('command_marker_exact_output_mismatch')
    if (type(code) is not int or code!=0) and not (isinstance(code,str) and code=='0'):
        raise ValueError('command_exit_code_mismatch')
    if stderr not in ('',None):raise ValueError('command_stderr_present')
    return {'profile_id':PROFILE_ID,'task_id':own['task_id'],'ci_id':t['ci_id'],'agent_id':t['agent_id'],
        'plugin_name':PLUGIN,'plugin_version':VERSION,'expected_marker_sha256':own['expected_marker_sha256'],
        'exact_marker_matched':True,'error_code':0,'stderr_empty':True,'fresh_result':True,
        'result_shape':shape,'technical_execution_verified':True,'full_business_case_passed':False,
        'processed_at':envelope['processed_at'],'mutation_executed':False}
