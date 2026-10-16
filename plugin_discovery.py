"""Closed benign main-task discovery. Execution proof is NOT a product oracle.

Only checkAlive and remoteConnections, no delivery/commands/remote sessions.
"""
from copy import deepcopy
from pathlib import Path
from uuid import UUID
import hashlib,json
import job_store
from plugin_preparation import (requirement as preparation_requirement, readiness, now,stamp,
    VERSIONS,BOOK_SHA,CORE,ORIGIN)
from command_stage_native import context,read_json,refusal
from command_probe_contract import validate_task_list
from operation_journal import list_operations,_fingerprint
from tools.agent_update import audit_result_is_fresh
from task_page_preflight import complete_task_list

CREATE='browser_create_closed_plugin_discovery_semantic'
READ='browser_inspect_closed_plugin_discovery_semantic'
READY='browser_read_closed_plugin_discovery_semantic'
PROFILE='safe-plugin-discovery-v1'

def requirement(name,plugin,campaign):
    r=preparation_requirement(name,plugin,campaign)
    r.update(type='closed_plugin_discovery',profile_id=PROFILE,
        expected_profile={'own_fresh_successful_execution':True,'bounded_shape_observed':True,
            'semantic_oracle_known':False,'business_pass':False})
    r['operation_stages']=[{'version':1,'workflow_id':PROFILE,'stage_id':'main_discovery',
        'resource_key':'agent-'+r['agent_id']+'-'+plugin+'-main-discovery','tool':CREATE,
        'arguments':{'target':name,'plugin_name':plugin,'stage_id':'main_discovery'},
        'verification':{'version':1,'kind':'owned_plugin_discovery','origin':ORIGIN,
            'target':name,'ci_id':r['ci_id'],'agent_id':r['agent_id'],'core_version':CORE,
            'plugin_name':plugin,'plugin_version':r['plugin_version'],'task_name':plugin,
            'stage_id':'main_discovery'}}]
    return r

def validate_context(job,case_id,starting=False):
    if not isinstance(job,dict) or len(job.get('test_cases',[]))!=1:raise ValueError('single_discovery_case_required')
    c=job['test_cases'][0];r=c.get('requirement') or {}
    if (c.get('case_id')!=case_id or r!=requirement(r.get('target'),r.get('plugin_name'),r.get('campaign_id'))
        or job.get('stand')!='lab' or job.get('job_type') not in {'manual','regression'}
        or job.get('status')!='running' or c.get('status')!='running' or job.get('resources')):
        raise ValueError('locked_discovery_profile_required')
    if not isinstance(job.get('request'),str) or not all(r[k] in job['request'] for k in
        ['ci_id','agent_id','ci_name','core_version','plugin_name','plugin_version','profile_id']):
        raise ValueError('original_discovery_request_required')
    if starting and any(e.get('type')=='plugin_discovery_started' for e in c.get('evidence',[])):
        raise ValueError('discovery_runtime_no_replay')
    return c,r

def admitted_write(job,case_id,args):
    _,r=validate_context(job,case_id);s=r['operation_stages'][0]
    if args!=s['arguments']:raise ValueError('closed_discovery_args_required')
    return deepcopy(s)

def read_ready(session,name,plugin,job_id,case_id):
    try:
        _,r=validate_context(job_store.get_job(job_id),case_id)
        if (name,plugin)!=(r['target'],r['plugin_name']):raise ValueError('discovery_read_scope')
        return readiness(session,r)
    except Exception as e:return {'error':str(e)[:150] if isinstance(e,ValueError) else 'discovery_read_unavailable','mutation_executed':False}

def shape(value):
    """Only types/cardinalities and digest; no keys, hostnames, users or secrets.

    Complete bytes are hashed before bounded type census. Large/deep results
    remain BLOCKED rather than silently truncating a proof.
    """
    raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    if len(raw)>1048576:raise ValueError('discovery_payload_budget')
    counts={};nodes=0
    def walk(v,depth):
        nonlocal nodes
        nodes+=1
        if nodes>20000 or depth>20:raise ValueError('discovery_shape_budget')
        kind=type(v).__name__;counts[kind]=counts.get(kind,0)+1
        if isinstance(v,dict):
            for x in v.values():walk(x,depth+1)
        elif isinstance(v,list):
            for x in v:walk(x,depth+1)
    walk(value,0)
    return {'root_type':type(value).__name__,'root_count':len(value) if isinstance(value,(dict,list,str)) else None,
        'json_bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'type_counts':counts,
        'complete_census':True,'semantic_oracle_known':False,'business_pass':False}

def create(session,name,plugin,stage_id,job_id,case_id):
    try:
        args={'target':name,'plugin_name':plugin,'stage_id':stage_id}
        stage=admitted_write(job_store.get_job(job_id),case_id,args)
        ops=list_operations(job_id)
        found=[o for o in ops if o.get('case_id')==case_id and o.get('status')=='sending'
            and all(o.get(k)==stage[k] for k in ['workflow_id','stage_id','resource_key','tool'])
            and o.get('arguments_fingerprint')==_fingerprint(args)
            and o.get('verification_fingerprint')==_fingerprint(stage['verification'])]
        if len(found)!=1 or any(o['operation_id']!=found[0]['operation_id'] and o.get('status') not in {'verified','not_sent'} for o in ops):
            raise ValueError('unique_resolved_discovery_intent_required')
        _,r=validate_context(job_store.get_job(job_id),case_id)
        if hashlib.sha256(Path('/home/adminacc/uqa-input/distributions/plugin_versions.xlsx').read_bytes()).hexdigest()!=BOOK_SHA:
            raise ValueError('discovery_source_changed')
        t,_,urls=context(session,name);ready=readiness(session,r)
        if (ready.get('ready') is not True or ready.get('load_error_empty_observed') is not True
            or ready['plugin_audit'].get('audit_fresh') is not True):raise ValueError('discovery_fresh_loaded_required')
        _,task_pages=complete_task_list(session,urls[0],name,plugin)
        if any(x.get('job_id')==job_id and x.get('case_id')==case_id for x in
            getattr(session,'_owned_plugin_discoveries',{}).values()):raise ValueError('discovery_already_sent')
        body={'name':plugin,'period':None,'ttl':None,'run_as_user':'','additional_params':{}}
    except Exception as e:return refusal(str(e)[:160] if isinstance(e,ValueError) else 'discovery_preflight_refused')
    observed_id=None
    try:
        sent=now();response=session.context.request.post(urls[0],data=body,timeout=15000);received=now()
        created=response.json() if response.status==201 else None
        if not isinstance(created,dict) or str(UUID(created.get('id')))!=created['id']:raise ValueError('receipt_id')
        if (created.get('agent_id')!=t['agent_id'] or created.get('name')!=plugin or 'period' not in created
            or created['period'] is not None):raise ValueError('receipt_scope')
        observed_id=created['id']
        if created.get('additional_params')!={} or not -120<=(stamp(received)-stamp(created.get('created_at'))).total_seconds()<=300:
            raise ValueError('receipt_params_clock')
        own={'task_id':created['id'],'target':name,'plugin_name':plugin,'plugin_version':r['plugin_version'],
            'ci_id':r['ci_id'],'agent_id':r['agent_id'],'stage_id':stage_id,'task_name':plugin,'profile_id':PROFILE,
            'job_id':job_id,'case_id':case_id,'session_id':session.session_id,'request_origin':ORIGIN,
            'sent_at':sent,'received_at':received,'server_created_at':created['created_at'],
            'operation_id':found[0]['operation_id'],'preflight_readiness':ready,'preflight_task_pages':task_pages}
        if not hasattr(session,'_owned_plugin_discoveries'):session._owned_plugin_discoveries={}
        session._owned_plugin_discoveries[created['id']]=own
        return {**own,'executed':True,'mutation_executed':True,'create_status':201,'business_pass':False}
    except Exception:return {'error':'discovery_dispatch_uncertain','executed':False,'dispatch_may_have_occurred':True,
        'observed_task_id':observed_id,'observed_identifier_is_owned_verified_receipt':False,'resend_authorized':False}

def read(session,name,plugin,task_id,job_id,case_id):
    try:
        _,r=validate_context(job_store.get_job(job_id),case_id)
        own=getattr(session,'_owned_plugin_discoveries',{}).get(task_id)
        if not own or any(own.get(k)!=v for k,v in {'job_id':job_id,'case_id':case_id,
            'session_id':session.session_id,'target':name,'plugin_name':plugin}.items()) or (name,plugin)!=(r['target'],r['plugin_name']):
            raise ValueError('own_discovery_receipt_required')
        t,_,urls=context(session,name);full=read_json(session,urls[0]+'/'+task_id+'/full');env=full.get('result')
        if not isinstance(env,dict):raise ValueError('own_discovery_result_not_ready')
        if (full.get('id')!=task_id or full.get('agent_id')!=r['agent_id'] or full.get('name')!=plugin
            or 'period' not in full or full['period'] is not None or full.get('status')!='success'
            or full.get('additional_params')!={} or env.get('machine_uid')!=r['ci_id'] or env.get('result')!='success'
            or 'data' not in env or not audit_result_is_fresh(own['sent_at'],own['received_at'],own['server_created_at'],
                full.get('created_at'),env.get('processed_at'))):raise ValueError('discovery_full_identity_freshness_required')
        census=shape(env['data'])
        return {**own,'response_shape':census,'native_result_verified':True,'identity_verified':True,'fresh_result':True,
            'machine_uid':t['ci_id'],'task_status':'success','processed_at':env['processed_at'],'read_at':now(),
            'business_pass':False,'mutation_executed':False}
    except Exception as e:return {'error':str(e)[:160] if isinstance(e,ValueError) else 'discovery_result_unavailable',
        'native_result_verified':False,'mutation_executed':False}

def evaluate(job,op,evidence_id,contract):
    """Independent native receipt/full linkage; never accepts shape as semantics."""
    try:
        c,r=validate_context(job,op['case_id']);s=r['operation_stages'][0]
        if contract!=s['verification'] or any(op.get(k)!=s[k] for k in ['workflow_id','stage_id','resource_key','tool']) or (op.get('receipt') or {}).get('acknowledged') is not True:
            raise ValueError('discovery_contract')
        def native(e,tool):
            if e.get('source')!='uqa_tool' or e.get('execution_status') not in {'observed','executed'} or stamp(e['created_at'])<stamp(op['created_at']):raise ValueError('native_evidence')
            b=json.loads(e['value'])
            if b.get('tool')!=tool or not isinstance(b.get('result'),dict):raise ValueError('tool_evidence')
            return b
        ev=next(e for e in c['evidence'] if e['evidence_id']==evidence_id);rb=native(ev,READ);readback=rb['result']
        creates=[]
        for e in c['evidence']:
            if e.get('source')!='uqa_tool':continue
            try:b=json.loads(e['value'])
            except (ValueError,TypeError):continue
            if b.get('tool')==CREATE and (b.get('result') or {}).get('operation_id')==op['operation_id']:creates.append((e,native(e,CREATE)))
        if len(creates)!=1:raise ValueError('unique_receipt')
        ce,cb=creates[0];created=cb['result']
        if (cb.get('arguments')!=s['arguments'] or rb.get('arguments')!={'target':r['target'],'plugin_name':r['plugin_name'],'task_id':created.get('task_id')}
            or created.get('create_status')!=201 or created.get('executed') is not True or created.get('mutation_executed') is not True
            or created.get('error') or readback.get('error') or any(created.get(k)!=v or readback.get(k)!=v for k,v in
                {'target':r['target'],'ci_id':r['ci_id'],'agent_id':r['agent_id'],'plugin_name':r['plugin_name'],
                 'plugin_version':r['plugin_version'],'profile_id':PROFILE,'stage_id':'main_discovery','task_name':r['plugin_name'],
                 'job_id':job['job_id'],'case_id':op['case_id'],'operation_id':op['operation_id'],'request_origin':ORIGIN}.items())
            or not created.get('task_id') or readback.get('task_id')!=created['task_id'] or not created.get('session_id')
            or readback.get('session_id')!=created['session_id'] or readback.get('machine_uid')!=r['ci_id']
            or readback.get('task_status')!='success' or readback.get('business_pass') is not False
            or any(readback.get(k) is not True for k in ['native_result_verified','identity_verified','fresh_result'])
            or stamp(ev['created_at'])<stamp(ce['created_at']) or not -5<=(stamp(now())-stamp(ev['created_at'])).total_seconds()<=300
            or not -5<=(stamp(ev['created_at'])-stamp(readback['read_at'])).total_seconds()<=60
            or not audit_result_is_fresh(created['sent_at'],created['received_at'],created['server_created_at'],readback['server_created_at'],readback['processed_at'])):
            raise ValueError('own_full_receipt')
        ready=created['preflight_readiness'];a=ready['plugin_audit'];cs=readback['response_shape']
        pageproof=created['preflight_task_pages']
        if (pageproof!=readback.get('preflight_task_pages') or pageproof.get('complete_enumeration') is not True
            or pageproof.get('atomic_snapshot') is not False or type(pageproof.get('total')) is not int
            or not 0<=pageproof['total']<=1000 or pageproof.get('unique_ids')!=pageproof['total']
            or not isinstance(pageproof.get('pages'),list) or not 1<=len(pageproof['pages'])<=10
            or sum(x['count'] for x in pageproof['pages'])!=pageproof['total']
            or pageproof.get('head_rechecked') is not (len(pageproof['pages'])>1)):
            raise ValueError('complete_task_pages_required')
        if (ready.get('ready') is not True or ready.get('load_error_empty_observed') is not True or a.get('audit_fresh') is not True
            or any(ready.get(k)!=v for k,v in {'ci_id':r['ci_id'],'agent_id':r['agent_id'],'core_version':CORE,
                'agent_status':'online','plugin_name':r['plugin_name'],'plugin_version':r['plugin_version'],'session_id':created['session_id']}.items())
            or not 0<=(stamp(created['sent_at'])-stamp(ready['read_at'])).total_seconds()<=60
            or cs.get('complete_census') is not True or cs.get('semantic_oracle_known') is not False or cs.get('business_pass') is not False
            or type(cs.get('json_bytes')) is not int or not 0<cs['json_bytes']<=1048576
            or len(bytes.fromhex(cs.get('sha256','')))!=32):raise ValueError('discovery_preflight_shape')
        return {'verified':True,'evidence_id':evidence_id,'receipt_evidence_id':ce['evidence_id'],
            'identifier_value':created['task_id'],'postcondition_verified':True,'resend_authorized':False,
            'verification_scope':'fresh_main_execution_and_shape_only_not_semantics','business_pass':False}
    except (ValueError,TypeError,KeyError,AttributeError,StopIteration,OverflowError):
        return {'verified':False,'reason':'plugin_discovery_evidence_insufficient','resend_authorized':False}
