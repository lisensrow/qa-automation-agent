"""Closed native stage adapter; requires an already-claimed Core journal intent.

No public CLI, autonomous send loop, permission override, arbitrary programs or
adoption of historical tasks. Not registered until Core/recovery tests pass.
"""
from datetime import datetime,timezone
import hashlib,re,uuid
from pathlib import Path
from urllib.parse import urlsplit
import job_store
from operation_journal import list_operations,_fingerprint
from native_dispatch import AuditPreflightRefused
from command_probe_contract import (target,validate_target_state,validate_task_list,validate_preflight,
    validate_created,verify_result,payload,PLUGIN,VERSION,CORE,ORIGIN,PROFILE_ID)
from command_stage_profile import admitted_write,validate_context,metadata_payload,CREATE,BOOK_SHA
from tools.agent_plugins import summarize_plugin_audit
from tools.agent_update import audit_result_is_fresh

def now():return datetime.now(timezone.utc).isoformat()

def refusal(reason):
    return AuditPreflightRefused(error=reason,executed=False,mutation_executed=False,dispatch_state='not_started')

def claimed_stage(job_id,case_id,name,stage_id):
    stage=admitted_write(job_store.get_job(job_id),case_id,{'target':name,'stage_id':stage_id})
    ledger=list_operations(job_id)
    found=[o for o in ledger if o.get('case_id')==case_id and o.get('status')=='sending'
        and all(o.get(k)==stage[k] for k in ['workflow_id','stage_id','resource_key','tool'])
        and o.get('arguments_fingerprint')==_fingerprint(stage['arguments'])
        and o.get('verification_fingerprint')==_fingerprint(stage['verification'])]
    if len(found)!=1:raise ValueError('unique_durable_core_sending_intent_required')
    if any(o.get('case_id')==case_id and o.get('operation_id')!=found[0]['operation_id']
           and o.get('status') not in {'verified','not_sent'} for o in ledger):
        raise ValueError('prior_command_stage_unresolved')
    return stage,found[0]['operation_id']

def context(session,name):
    t=target(name);session._ensure_started()
    ci,_,observed_url,error=session._observed_agent_task_context(t['ci_name'])
    if error:raise ValueError('observed_command_target_context_required')
    source=urlsplit(observed_url);path=source.path.rstrip('/')
    if (source.scheme!='https' or source.netloc!=urlsplit(ORIGIN).netloc
        or not path.endswith('/agents/'+t['agent_id']+'/tasks')
        or ci.get('id')!=t['ci_id'] or ci.get('agent_id')!=t['agent_id'] or ci.get('name')!=t['ci_name']):
        raise ValueError('command_origin_target_mismatch')
    # Observed list GETs can carry pagination/filter queries. Like the existing
    # pinned adapters, derive new URLs from the verified PATH, never forward query.
    urls=[session._same_https_origin_url(observed_url,p) for p in [path,path[:-6],path[:-6]+'/plugin']]
    if not all(urls):raise ValueError('command_origin_target_mismatch')
    return t,ci,urls

def read_json(session,url,params=None):
    r=session.context.request.get(url,params=params,timeout=15000)
    if r.status!=200:raise ValueError('command_preflight_get_unavailable')
    b=r.json()
    if not isinstance(b,dict):raise ValueError('command_preflight_get_not_object')
    return b

def create_stage(session,name,stage_id,job_id,case_id):
    """Called ONLY by Core inside execute_journaled AFTER unchanged v069 approval."""
    try:
        stage,opid=claimed_stage(job_id,case_id,name,stage_id)
        if hashlib.sha256(Path('/home/adminacc/uqa-input/distributions/plugin_versions.xlsx').read_bytes()).hexdigest()!=BOOK_SHA:
            raise ValueError('command_workbook_revision_changed')
        t,ci,urls=context(session,name);tasks_url,agent_url,plugins_url=urls
        agent=read_json(session,agent_url);validate_target_state(name,ci,agent)
        task_name=stage['verification']['task_name']
        tasks=read_json(session,tasks_url,{'name':task_name,'periodic':False,'limit':100,'offset':0})
        items=validate_task_list(name,tasks,task_name)
        audit=read_json(session,plugins_url)
        checked=summarize_plugin_audit(ci,audit,PLUGIN,VERSION)
        own_tasks=getattr(session,'_closed_command_tasks',{})
        same_case=[o for o in own_tasks.values() if o['job_id']==job_id and o['case_id']==case_id
                   and o['target']==name and o['session_id']==session.session_id]
        if any(o['stage_id']==stage_id for o in same_case):raise ValueError('own_command_stage_already_sent')
        if stage_id=='initial_inventory':
            if checked['audit_fresh']:raise ValueError('command_inventory_already_fresh')
        elif stage_id=='post_delivery_inventory':
            if not any(o['stage_id']=='deliver_command_plugin' and o.get('stage_result_verified') is True for o in same_case):
                raise ValueError('own_verified_command_delivery_required')
        elif stage_id=='deliver_command_plugin':
            if not checked['audit_fresh']:raise ValueError('fresh_command_inventory_required_before_delivery')
            matched=checked['matched_plugins']
            if len(matched)>1:raise ValueError('command_version_ambiguous')
            if matched:
                v=matched[0]['version']
                if not isinstance(v,str) or not re.fullmatch(r'\d+\.\d+\.\d+',v):raise ValueError('command_version_unknown')
                if tuple(map(int,v.split('.')))>=tuple(map(int,VERSION.split('.'))):
                    raise ValueError('command_same_version_or_downgrade_forbidden')
            for item in items:
                params=item.get('additional_params')
                updates=params.get('plugins_to_update') if isinstance(params,dict) else None
                if not isinstance(updates,list):raise ValueError('old_plugin_delivery_parameters_unknown')
                if any(isinstance(p,dict) and p.get('plugin_name')==PLUGIN and p.get('plugin_version')==VERSION for p in updates):
                    raise ValueError('command_delivery_already_exists_no_rekey')
        elif stage_id=='execute_command':validate_preflight(name,ci,agent,audit,tasks)
        else:raise ValueError('closed_command_stage_required')
        marker='UQA_EXEC_OK_'+uuid.uuid4().hex if stage_id=='execute_command' else None
        body=payload(name,marker) if marker else metadata_payload(stage_id)
        url=plugins_url+'/update' if stage_id=='deliver_command_plugin' else tasks_url
    except Exception as exc:
        return refusal(str(exc)[:180] if isinstance(exc,ValueError) else 'closed_command_preflight_refused')
    # Every failure below is uncertain: the request may already have executed.
    observed_id=None
    try:
        sent=now();r=session.context.request.post(url,data=body,timeout=15000);received=now()
        expected_status=202 if stage_id=='deliver_command_plugin' else 201
        created=r.json() if r.status==expected_status else None
        if not isinstance(created,dict):raise ValueError('command_create_receipt_unverified')
        if str(uuid.UUID(created.get('id')))!=created['id']:raise ValueError('command_receipt_id_unverified')
        if (created.get('agent_id')!=t['agent_id'] or created.get('name')!=task_name
            or 'period' not in created or created['period'] is not None):
            raise ValueError('command_receipt_scope_unverified')
        observed_id=created['id']  # Quarantined identifier only if later receipt checks fail.
        own=(validate_created(name,marker,created,sent,received,session.session_id) if marker else {
            'task_id':created['id'],'agent_id':t['agent_id'],'ci_id':t['ci_id'],'ci_name':t['ci_name'],
            'target':name,'task_name':task_name,'profile_id':PROFILE_ID,'session_id':session.session_id,
            'sent_at':sent,'received_at':received,'server_created_at':created.get('created_at'),'request_origin':ORIGIN})
        own.update(job_id=job_id,case_id=case_id,stage_id=stage_id,operation_id=opid,stage_result_verified=False)
        if not hasattr(session,'_closed_command_tasks'):session._closed_command_tasks={}
        session._closed_command_tasks[created['id']]=own
        return {k:v for k,v in own.items() if k!='expected_marker'}|{'executed':True,'mutation_executed':True,
            'create_status':r.status,'business_pass':False,'status':'created'}
    except Exception:
        return {'error':'closed_command_dispatch_uncertain','executed':False,'dispatch_may_have_occurred':True,
            'observed_task_id':observed_id,'observed_identifier_is_owned_verified_receipt':False,'resend_authorized':False}

def inspect_stage(session,name,task_id,job_id,case_id):
    try:
        _,req=validate_context(job_store.get_job(job_id),case_id)
        if req['target']!=name:raise ValueError('own_command_target_required')
        own=getattr(session,'_closed_command_tasks',{}).get(task_id)
        if not own or any(own.get(k)!=v for k,v in {'target':name,'job_id':job_id,'case_id':case_id,
                                                  'session_id':session.session_id}.items()):
            raise ValueError('same_case_session_own_command_receipt_required')
        t,ci,urls=context(session,name)
        full=read_json(session,urls[0]+'/'+task_id+'/full')
        envelope=full.get('result')
        if not isinstance(envelope,dict):raise ValueError('own_command_stage_result_not_ready')
        fresh=audit_result_is_fresh(own['sent_at'],own['received_at'],own['server_created_at'],
            full.get('created_at'),envelope.get('processed_at'))
        if (not fresh or full.get('id')!=task_id or full.get('agent_id')!=t['agent_id'] or full.get('name')!=own['task_name']
            or 'period' not in full or full['period'] is not None
            or full.get('status')!='success' or envelope.get('machine_uid')!=t['ci_id']):
            raise ValueError('own_command_stage_identity_freshness_required')
        details={}
        if own['stage_id']=='execute_command':details=verify_result(own,full,session.session_id)
        elif own['stage_id']=='deliver_command_plugin':
            data=envelope.get('data') or {};downloaded=data.get('plugins_downloaded')
            if (envelope.get('result')!='success' or not isinstance(downloaded,list) or len(downloaded)!=1
                or downloaded[0].get('plugin_name')!=PLUGIN or type(downloaded[0].get('size_bytes')) is not int
                or downloaded[0]['size_bytes']<=0 or data.get('plugins_scheduled_for_deletion')!=[]):
                raise ValueError('own_command_delivery_result_mismatch')
            details={'delivery_verified':True}
        else:
            if envelope.get('result')!='success':raise ValueError('own_plugin_inventory_result_mismatch')
            ready=session.inspect_pinned_agent_readiness_semantic(t['ci_name'],t['agent_id'],PLUGIN,VERSION)
            audit=ready.get('plugin_audit') or {}
            at=datetime.fromisoformat(str(audit.get('last_audit_at')).replace('Z','+00:00'))
            created=datetime.fromisoformat(str(own['server_created_at']).replace('Z','+00:00'))
            if (ready.get('ci_id')!=t['ci_id'] or ready.get('agent_id')!=t['agent_id']
                or ready.get('core_version')!=CORE or ready.get('agent_status')!='online'
                or audit.get('audit_fresh') is not True or (at-created).total_seconds() < -120):
                raise ValueError('own_fresh_plugin_inventory_required')
            if own['stage_id']=='post_delivery_inventory' and ready.get('ready') is not True:
                raise ValueError('delivered_command_not_loaded')
            details={'plugin_readiness':ready}
        own['stage_result_verified']=True
        return {k:own[k] for k in ['task_id','ci_id','agent_id','ci_name','target','stage_id','task_name','session_id',
            'request_origin','server_created_at','operation_id']}|details|{'native_result_verified':True,
            'identity_verified':True,'fresh_result':True,'machine_uid':t['ci_id'],'task_status':'success',
            'processed_at':envelope['processed_at'],'read_at':now(),'mutation_executed':False,'business_pass':False}
    except Exception as exc:
        return {'error':str(exc)[:180] if isinstance(exc,ValueError) else 'closed_command_result_unavailable',
                'native_result_verified':False,'mutation_executed':False}
