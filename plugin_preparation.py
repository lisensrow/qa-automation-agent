"""Closed preparation ONLY for four safe audit plugins, not plugin task execution.

No legacy inventory profile extension, commands, VNC/session/settings or deletion.
Core owns policy and durable claim. A loaded plugin is not a completed test case.
"""
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from uuid import UUID
import hashlib,json,re
import job_store
from command_probe_contract import target,validate_target_state,validate_task_list,CORE,ORIGIN
from command_stage_native import context,read_json,refusal
from command_stage_profile import BOOK_SHA
from operation_journal import list_operations,_fingerprint
from tools.agent_plugins import summarize_plugin_audit
from tools.agent_update import audit_result_is_fresh

CREATE='browser_create_closed_plugin_preparation_semantic'
READ='browser_inspect_closed_plugin_preparation_semantic'
READY='browser_read_closed_plugin_preparation_semantic'
PROFILE='safe-plugin-preparation-v1'
VERSIONS={'checkAlive':('1.3.2','B4'),'remoteConnections':('1.3.6','B25'),
          'storageAudit':('1.3.4','B33'),'defaultNetworkDeviceAudit':('1.3.5','B6')}
STAGES=(('initial_inventory','pluginAudit'),('delivery','managePlugin'),('post_inventory','pluginAudit'))

def now():return datetime.now(timezone.utc).isoformat()
def stamp(s):
    d=datetime.fromisoformat(str(s).replace('Z','+00:00'))
    if d.tzinfo is None:raise ValueError('timezone required')
    return d

def requirement(name,plugin,campaign):
    t=target(name)
    if plugin not in VERSIONS:raise ValueError('safe_preparation_plugin_required')
    if not isinstance(campaign,str) or not 1<=len(campaign)<=80 or not campaign.replace('-','').isalnum():
        raise ValueError('safe_preparation_campaign_required')
    version,cell=VERSIONS[plugin]
    r={'type':'closed_plugin_preparation','stand':'lab','locked':True,'action_profile':'write_resource',
        'target':name,'ci_id':t['ci_id'],'agent_id':t['agent_id'],'ci_name':t['ci_name'],
        'core_version':CORE,'plugin_name':plugin,'plugin_version':version,'profile_id':PROFILE,'campaign_id':campaign,
        'source_manifest':{'sha256':BOOK_SHA,'sheet':'1.3.27','version_cell':cell,
            'teacher_job':'20261016-051942-618b0a99' if plugin in {'storageAudit','defaultNetworkDeviceAudit'} else '20261016-024614-ccfd4c2e',
            'teacher_evidence':'ev-b541e59d632c' if plugin in {'storageAudit','defaultNetworkDeviceAudit'} else 'ev-cc0c022c1e08'},
        'expected_profile':{'fresh_loaded':True,'same_ci_agent_session':True,'plugin_case_executed':False,'business_pass':False}}
    r['operation_stages']=[{'version':1,'workflow_id':PROFILE,'stage_id':sid,
        'resource_key':'agent-'+t['agent_id']+'-'+plugin+'-'+sid,'tool':CREATE,
        'arguments':{'target':name,'plugin_name':plugin,'stage_id':sid},
        'verification':{'version':1,'kind':'owned_plugin_preparation','origin':ORIGIN,'target':name,
            'ci_id':t['ci_id'],'agent_id':t['agent_id'],'core_version':CORE,'plugin_name':plugin,
            'plugin_version':version,'task_name':task,'stage_id':sid}} for sid,task in STAGES]
    return r

def validate_context(job,case_id,starting=False):
    if not isinstance(job,dict) or not isinstance(job.get('test_cases'),list) or len(job['test_cases'])!=1:
        raise ValueError('single_preparation_case_required')
    c=job['test_cases'][0];r=c.get('requirement') or {}
    if (c.get('case_id')!=case_id or r!=requirement(r.get('target'),r.get('plugin_name'),r.get('campaign_id'))
        or job.get('stand')!='lab' or job.get('job_type') not in {'manual','regression'} or job.get('status')!='running'
        or c.get('status')!='running' or job.get('resources')):raise ValueError('locked_preparation_profile_required')
    if not isinstance(job.get('request'),str) or not all(r[k] in job['request'] for k in
        ['ci_id','agent_id','ci_name','core_version','plugin_name','plugin_version','profile_id']):
        raise ValueError('original_preparation_request_required')
    if starting and any(e.get('type')=='plugin_preparation_started' for e in c.get('evidence',[])):
        raise ValueError('preparation_runtime_no_replay')
    return c,r

def admitted_write(job,case_id,args):
    _,r=validate_context(job,case_id)
    if not isinstance(args,dict) or set(args)!={'target','plugin_name','stage_id'}:raise ValueError('closed_preparation_args_required')
    s=next((x for x in r['operation_stages'] if x['arguments']==args),None)
    if s is None:raise ValueError('preparation_stage_scope_mismatch')
    return deepcopy(s)

def readiness(session,r):
    t,ci,urls=context(session,r['target']);agent=read_json(session,urls[1]);validate_target_state(r['target'],ci,agent)
    raw=read_json(session,urls[2]);audit=summarize_plugin_audit(ci,raw,r['plugin_name'],r['plugin_version'])
    matched=audit.get('matched_plugins') or []
    details=raw.get('detail')
    rows=[x for x in details if isinstance(x,dict) and x.get('plugin_name')==r['plugin_name']] if isinstance(details,list) else []
    error_known=(len(rows)==1 and 'load_error' in rows[0] and rows[0]['load_error'] in ('',None))
    return {'target':r['target'],'ci_id':t['ci_id'],'agent_id':t['agent_id'],'core_version':agent['version'],
        'agent_status':agent['status'],'plugin_name':r['plugin_name'],'plugin_version':r['plugin_version'],
        'plugin_audit':audit,'load_error_empty_observed':error_known,
        'ready':audit['observation_result']=='PASS' and len(matched)==1 and not matched[0]['load_error_present'] and error_known,
        'read_at':now(),'session_id':session.session_id,'business_pass':False,'mutation_executed':False}

def read_ready(session,name,plugin,job_id,case_id):
    try:
        _,r=validate_context(job_store.get_job(job_id),case_id)
        if (name,plugin)!=(r['target'],r['plugin_name']):raise ValueError('preparation_read_scope_mismatch')
        return readiness(session,r)
    except Exception as e:return {'error':str(e)[:150] if isinstance(e,ValueError) else 'preparation_read_unavailable','mutation_executed':False}

def claimed_stage(job_id,case_id,args):
    stage=admitted_write(job_store.get_job(job_id),case_id,args);ops=list_operations(job_id)
    found=[o for o in ops if o.get('case_id')==case_id and o.get('status')=='sending'
        and all(o.get(k)==stage[k] for k in ['workflow_id','stage_id','resource_key','tool'])
        and o.get('arguments_fingerprint')==_fingerprint(stage['arguments'])
        and o.get('verification_fingerprint')==_fingerprint(stage['verification'])]
    if len(found)!=1 or any(o.get('case_id')==case_id and o['operation_id']!=found[0]['operation_id']
        and o.get('status') not in {'verified','not_sent'} for o in ops):raise ValueError('unique_resolved_preparation_intent_required')
    return stage,found[0]['operation_id']

def create(session,name,plugin,stage_id,job_id,case_id):
    try:
        args={'target':name,'plugin_name':plugin,'stage_id':stage_id};stage,opid=claimed_stage(job_id,case_id,args)
        _,r=validate_context(job_store.get_job(job_id),case_id)
        if hashlib.sha256(Path('/home/adminacc/uqa-input/distributions/plugin_versions.xlsx').read_bytes()).hexdigest()!=BOOK_SHA:
            raise ValueError('preparation_workbook_changed')
        t,ci,urls=context(session,name);ready=readiness(session,r);task=stage['verification']['task_name']
        tasks=validate_task_list(name,read_json(session,urls[0],{'name':task,'periodic':False,'limit':100,'offset':0}),task)
        ownmap=getattr(session,'_owned_plugin_preparations',{})
        own=[x for x in ownmap.values() if all(x.get(k)==v for k,v in
            {'job_id':job_id,'case_id':case_id,'session_id':session.session_id,'target':name,'plugin_name':plugin}.items())]
        if any(x['stage_id']==stage_id for x in own):raise ValueError('preparation_stage_already_sent')
        audit=ready['plugin_audit']
        if stage_id=='initial_inventory' and audit['audit_fresh']:raise ValueError('preparation_inventory_already_fresh')
        if stage_id=='post_inventory' and not any(x['stage_id']=='delivery' and x.get('stage_result_verified') is True for x in own):
            raise ValueError('own_verified_preparation_delivery_required')
        if stage_id=='delivery':
            if not audit['audit_fresh']:raise ValueError('fresh_preparation_inventory_required')
            matched=audit.get('matched_plugins') or []
            if len(matched)>1:raise ValueError('preparation_version_ambiguous')
            if matched:
                v=matched[0].get('version')
                if not isinstance(v,str) or not re.fullmatch(r'\d+\.\d+\.\d+',v):raise ValueError('preparation_version_unknown')
                if tuple(map(int,v.split('.')))>=tuple(map(int,r['plugin_version'].split('.'))):raise ValueError('preparation_same_version_or_downgrade_forbidden')
            for old in tasks:
                params=old.get('additional_params');updates=params.get('plugins_to_update') if isinstance(params,dict) else None
                if not isinstance(updates,list):raise ValueError('old_preparation_delivery_params_unknown')
                if any(isinstance(p,dict) and p.get('plugin_name')==plugin and p.get('plugin_version')==r['plugin_version'] for p in updates):
                    raise ValueError('preparation_delivery_exists_no_rekey')
            body={'plugins_to_update':[{'plugin_name':plugin,'plugin_version':r['plugin_version']}],
                'plugins_to_delete':[],'check_endpoint_os_version':True};url=urls[2]+'/update'
        else:
            body={'name':'pluginAudit','period':None,'ttl':None,'run_as_user':'','additional_params':{}};url=urls[0]
    except Exception as e:return refusal(str(e)[:160] if isinstance(e,ValueError) else 'preparation_preflight_refused')
    observed_id=None
    try:
        sent=now();response=session.context.request.post(url,data=body,timeout=15000);received=now()
        expected=202 if stage_id=='delivery' else 201
        created=response.json() if response.status==expected else None
        if not isinstance(created,dict) or str(UUID(created.get('id')))!=created['id']:raise ValueError('receipt_id')
        if (created.get('agent_id')!=t['agent_id'] or created.get('name')!=task or 'period' not in created
            or created['period'] is not None):raise ValueError('receipt_scope')
        observed_id=created['id']
        params=created.get('additional_params')
        if stage_id=='delivery' and (not isinstance(params,dict) or params.get('plugins_to_update')!=body['plugins_to_update']
            or params.get('plugins_to_delete')!=[] or params.get('check_endpoint_os_version',True) is not True):raise ValueError('receipt_params')
        if stage_id!='delivery' and params!={}:raise ValueError('inventory_receipt_params')
        # Require a timezone-bearing fresh server receipt before treating its ID as owned.
        if not -120<=(stamp(received)-stamp(created.get('created_at'))).total_seconds()<=300:raise ValueError('receipt_clock')
        own={'task_id':created['id'],'target':name,'plugin_name':plugin,'plugin_version':r['plugin_version'],
            'ci_id':t['ci_id'],'agent_id':t['agent_id'],'ci_name':t['ci_name'],'stage_id':stage_id,'task_name':task,
            'profile_id':PROFILE,'job_id':job_id,'case_id':case_id,'session_id':session.session_id,'request_origin':ORIGIN,
            'sent_at':sent,'received_at':received,'server_created_at':created['created_at'],'operation_id':opid}
        if not hasattr(session,'_owned_plugin_preparations'):session._owned_plugin_preparations={}
        session._owned_plugin_preparations[created['id']]=own
        return {**own,'executed':True,'mutation_executed':True,'create_status':expected,'business_pass':False}
    except Exception:return {'error':'preparation_dispatch_uncertain','executed':False,'dispatch_may_have_occurred':True,
        'observed_task_id':observed_id,'observed_identifier_is_owned_verified_receipt':False,'resend_authorized':False}

def read(session,name,plugin,task_id,job_id,case_id):
    try:
        _,r=validate_context(job_store.get_job(job_id),case_id)
        if (name,plugin)!=(r['target'],r['plugin_name']):raise ValueError('preparation_read_scope_mismatch')
        own=getattr(session,'_owned_plugin_preparations',{}).get(task_id)
        if not own or any(own.get(k)!=v for k,v in {'job_id':job_id,'case_id':case_id,'session_id':session.session_id,
            'target':name,'plugin_name':plugin}.items()):raise ValueError('own_preparation_receipt_required')
        t,_,urls=context(session,name);full=read_json(session,urls[0]+'/'+task_id+'/full');envelope=full.get('result')
        if not isinstance(envelope,dict):raise ValueError('own_preparation_result_not_ready')
        if (full.get('id')!=task_id or full.get('agent_id')!=t['agent_id'] or full.get('name')!=own['task_name']
            or 'period' not in full or full['period'] is not None or full.get('status')!='success'
            or envelope.get('machine_uid')!=t['ci_id'] or envelope.get('result')!='success'
            or not audit_result_is_fresh(own['sent_at'],own['received_at'],own['server_created_at'],full.get('created_at'),envelope.get('processed_at'))):
            raise ValueError('preparation_full_identity_freshness_required')
        extra={}
        if own['stage_id']=='delivery':
            data=envelope.get('data') or {};downloads=data.get('plugins_downloaded')
            if (not isinstance(downloads,list) or len(downloads)!=1 or downloads[0].get('plugin_name')!=plugin
                or type(downloads[0].get('size_bytes')) is not int or downloads[0]['size_bytes']<=0
                or data.get('plugins_scheduled_for_deletion')!=[]):raise ValueError('preparation_download_result_required')
            extra={'delivery_verified':True}
        else:
            ready=readiness(session,r);audit=ready['plugin_audit']
            if (not audit['audit_fresh'] or (stamp(audit['last_audit_at'])-stamp(own['server_created_at'])).total_seconds() < -120
                or own['stage_id']=='post_inventory' and ready['ready'] is not True):raise ValueError('preparation_fresh_loaded_inventory_required')
            extra={'plugin_readiness':ready}
        own['stage_result_verified']=True
        return {**{k:v for k,v in own.items() if k!='stage_result_verified'},**extra,
            'native_result_verified':True,'identity_verified':True,'fresh_result':True,'machine_uid':t['ci_id'],
            'task_status':'success','processed_at':envelope['processed_at'],'read_at':now(),'business_pass':False,'mutation_executed':False}
    except Exception as e:return {'error':str(e)[:160] if isinstance(e,ValueError) else 'preparation_result_unavailable',
        'native_result_verified':False,'mutation_executed':False}
