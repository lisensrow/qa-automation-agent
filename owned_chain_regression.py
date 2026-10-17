"""Closed, new-owned three-audit chain; no arbitrary endpoints or existing writes.

Every POST passes Core WRITE and the durable per-stage journal. Own POST
receipts are followed by independent native GETs. Completion here is technical
chain execution, never full source PASS: the source also requires agent logs.
"""
import hashlib, json, re
from copy import deepcopy
from uuid import UUID
import job_store
from command_probe_contract import target, validate_target_state, ORIGIN, CORE
from command_stage_native import context, read_json, refusal
from operation_journal import list_operations, _fingerprint
from plugin_preparation import stamp, now
from regression_read_coverage import load
from regression_source_reader import MANIFEST_SHA

CREATE = 'browser_create_owned_chain_stage_semantic'
READ = 'browser_inspect_owned_chain_stage_semantic'
READY = 'browser_read_owned_chain_readiness_semantic'
PROFILE = 'owned-three-audit-chain-v1'
# Installed OpenAPI alone did not establish routed runtime availability (719).
# Keep the compiler/READ diagnostics, but never offer this unaccepted writer.
WRITES_ENABLED = False
TASKS = ('driveDeviceAudit', 'networkDeviceAudit', 'softAudit')
VERSIONS = ('1.3.5', '1.5.1', '1.3.8')
STAGES = ('stage1', 'stage2', 'stage3', 'pipeline', 'attach', 'job', 'run')
SCHEMA_SHA = '3113e8a27e7d73025bb2e490fbc0489413f7a0abe83dd15480f298d42a533f8e'

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def requirement(name, campaign, source_ref):
    t = target(name)
    if not re.fullmatch(r'uqa-[a-z0-9-]{1,65}', str(campaign)):
        raise ValueError('owned_chain_campaign')
    if (type(source_ref) is not list or len(source_ref) != 2
        or any(type(x) is not str or not re.fullmatch(r'[A-Za-z0-9-]{1,80}', x) for x in source_ref)):
        raise ValueError('owned_chain_source_ref')
    key = 'US-T93' if name == 'windows' else 'US-T115'
    _, source, _ = load(key)
    r = {'type': 'owned_chain_regression', 'stand': 'lab', 'locked': True, 'action_profile': 'write_resource',
         'target': name, 'campaign_id': campaign, 'profile_id': PROFILE,
         **{k: t[k] for k in ('ci_id', 'ci_name', 'agent_id')}, 'core_version': CORE,
         'source_case': key, 'source_sha256': source['json_sha256'], 'source_ref': list(source_ref),
         'schema_sha256': SCHEMA_SHA, 'task_names': list(TASKS), 'plugin_versions': list(VERSIONS),
         'existing_core_is_precondition_no_reinstall': True, 'log_verification_required_for_full_case': True}
    r['operation_stages'] = [{'version': 1, 'workflow_id': PROFILE, 'stage_id': sid,
        'resource_key': campaign + '-' + name + '-' + sid, 'tool': CREATE,
        'arguments': {'target': name, 'stage_id': sid},
        'verification': {'version': 1, 'kind': 'owned_chain_stage', 'origin': ORIGIN,
                         'target': name, 'campaign_id': campaign, 'stage_id': sid,
                         'ci_id': t['ci_id'], 'agent_id': t['agent_id'], 'schema_sha256': SCHEMA_SHA}}
        for sid in STAGES]
    return r

def validate_context(job, cid):
    if not isinstance(job, dict) or len(job.get('test_cases', [])) != 1:
        raise ValueError('single_owned_chain_case')
    c = job['test_cases'][0]; r = c.get('requirement') or {}
    if (c.get('case_id') != cid or r != requirement(r.get('target'), r.get('campaign_id'), r.get('source_ref'))
        or job.get('stand') != 'lab' or job.get('job_type') not in {'manual', 'regression'}
        or job.get('status') != 'running' or c.get('status') != 'running' or job.get('resources')):
        raise ValueError('locked_owned_chain_case')
    if not all(r[k] in job.get('request', '') for k in ('ci_id','agent_id','ci_name','core_version','campaign_id','source_case')):
        raise ValueError('owned_chain_original_request_scope')
    source = job_store.get_job(r['source_ref'][0])
    sc = next(c for c in source['test_cases'] if c['case_id'] == r['source_ref'][1])
    sr=sc.get('requirement') or {}
    if (source.get('stand') != 'lab' or source.get('resources')
        or sr.get('type')!='owned_regression_source_read' or sr.get('locked') is not True
        or sr.get('action_profile')!='read_only' or sr.get('source_manifest_sha256')!=MANIFEST_SHA
        or sr.get('case_key') != r['source_case']
        or sc['requirement'].get('source_sha256') != r['source_sha256'] or list_operations(source['job_id'])):
        raise ValueError('owned_chain_exact_source_job')
    valid = False
    for e in sc.get('evidence', []):
        if e.get('source') != 'uqa_tool': continue
        b = json.loads(e['value']); v = b.get('result') or {}
        if (b.get('tool') == 'knowledge_inspect_own_regression_read_coverage'
            and v.get('case_key') == r['source_case'] and v.get('source_sha256') == r['source_sha256']
            and v.get('source_manifest_sha256') == MANIFEST_SHA
            and v.get('complete_case_source_content_read') is True): valid = True
    if not valid: raise ValueError('owned_chain_full_own_source_required')
    return c, r

def admit(job, cid, args, for_write=True):
    _, r = validate_context(job, cid)
    if type(args) is not dict or set(args) != {'target','stage_id'} or args['target'] != r['target']:
        raise ValueError('owned_chain_exact_stage_args')
    if for_write and not WRITES_ENABLED:
        raise ValueError('legacy_chain_writer_retired_runtime_route_unavailable')
    return deepcopy(next(s for s in r['operation_stages'] if s['stage_id'] == args['stage_id']))

def own(case, tool, sid):
    found = []
    for e in case.get('evidence', []):
        if e.get('source') != 'uqa_tool': continue
        b = json.loads(e['value']); v = b.get('result') or {}
        if b.get('tool') == tool and v.get('stage_id') == sid and not v.get('error'):
            found.append((e, v))
    return found

def identifier(case, sid):
    rows = own(case, CREATE, sid)
    if len(rows) != 1: raise ValueError('owned_chain_unique_receipt_required')
    value = rows[0][1]['object_id']
    if str(UUID(value)) != value: raise ValueError('owned_chain_uuid')
    return value

def compile_request(r, case, sid):
    prefix = r['campaign_id']
    if sid.startswith('stage'):
        n = STAGES.index(sid)
        return '/api/v1/stages', {'name': prefix + '-' + sid, 'description': prefix,
            'detail': {'task_name': TASKS[n], 'additional_params': {}, 'context_params': {}, 'run_as_user': None}}, 201
    if sid == 'pipeline':
        return '/api/v1/pipelines', {'name': prefix + '-pipeline', 'description': prefix}, 201
    pipeline = identifier(case, 'pipeline')
    if sid == 'attach':
        return '/api/v1/pipelines/' + pipeline + '/add-stages', [
            {'stage_id': identifier(case, 'stage' + str(i)), 'order': i} for i in (1,2,3)], 200
    if sid == 'job':
        return '/api/v1/jobs', {'pipeline_id': pipeline, 'default_agent_id': r['agent_id'],
                               'crontab_schedule': None, 'ignore_agent_status': False}, 200
    if sid == 'run': return '/api/v1/jobs/' + identifier(case,'job') + '/run', None, 200
    raise ValueError('owned_chain_stage_unknown')

def check_object(r, case, sid, body, payload, object_id=None):
    if sid == 'attach':
        expected = [(identifier(case, 'stage'+str(i)), i, TASKS[i-1]) for i in (1,2,3)]
        if (type(body) is not list or len(body) != 3
            or sorted((b.get('id'), b.get('order'), (b.get('detail') or {}).get('task_name')) for b in body)
                != sorted(expected)):
            raise ValueError('owned_chain_stage_order_mismatch')
        return identifier(case, 'pipeline')
    if type(body) is not dict or str(UUID(body.get('id'))) != body.get('id'):
        raise ValueError('owned_chain_native_object_id')
    if object_id is not None and body['id'] != object_id: raise ValueError('owned_chain_read_id')
    if sid.startswith('stage') or sid == 'pipeline':
        for k,v in payload.items():
            if body.get(k) != v: raise ValueError('owned_chain_read_payload_mismatch')
    elif sid == 'job':
        if (body.get('pipeline_id') != payload['pipeline_id'] or body.get('default_agent_id') != r['agent_id']
            or body.get('is_enabled') is not True
            or body.get('crontab_schedule_id') is not None or body.get('crontab_schedule') is not None):
            raise ValueError('owned_chain_job_scope_or_schedule')
    elif sid == 'run':
        if body.get('job_id') != identifier(case,'job'): raise ValueError('owned_chain_instance_job')
    return body['id']

def summarize_history(r, case, instance, body):
    if (type(body) is not dict or type(body.get('items')) is not list
        or body.get('total')!=len(body['items']) or body.get('offset',0)!=0 or len(body['items'])>3):
        raise ValueError('owned_chain_complete_instance_history_required')
    rows=[];seen=set();pipeline=identifier(case,'pipeline')
    for item in body['items']:
        if type(item) is not dict or item.get('job_instance_id')!=instance:
            raise ValueError('owned_chain_history_instance_mismatch')
        relation=item.get('pipeline_stage');stage=item.get('stage')
        if not isinstance(relation,dict) or not isinstance(stage,dict):
            return {'complete':False,'reason':'history_relation_unknown','stages':rows,'agent_logs_verified':False}
        order=relation.get('order')
        if (type(order) is not int or order not in (1,2,3) or order in seen
            or relation.get('pipeline_id')!=pipeline or relation.get('stage_id')!=identifier(case,'stage'+str(order))
            or stage.get('id')!=relation['stage_id'] or (stage.get('detail') or {}).get('task_name')!=TASKS[order-1]):
            raise ValueError('owned_chain_history_stage_target_or_order')
        seen.add(order);result=item.get('result')
        rows.append({'order':order,'stage_id':stage['id'],'task_name':TASKS[order-1],
                     'status':item.get('status'),'processed_at':item.get('processed_at'),
                     'result_sha256':digest(result),'result_keys':sorted(result) if isinstance(result,dict) else None,
                     'result_object_present':isinstance(result,dict)})
    return {'complete':seen=={1,2,3} and all(x['status']=='success' and x['result_object_present'] for x in rows),
            'reason':'native_instance_stage_history_only_not_agent_logs','stages':sorted(rows,key=lambda x:x['order']),
            'history_sha256':digest(body),'agent_logs_verified':False}

def ready(session, name, jid, cid):
    try:
        c,r = validate_context(job_store.get_job(jid),cid)
        if name != r['target']: raise ValueError('owned_chain_target')
        t,ci,urls = context(session,name); agent = read_json(session,urls[1]); validate_target_state(name,ci,agent)
        response = session.context.request.get(ORIGIN+'/api/v1/docs/openapi.json',timeout=30000)
        if response.status != 200 or hashlib.sha256(response.body()).hexdigest() != SCHEMA_SHA:
            raise ValueError('owned_chain_current_schema_changed')
        routes=[]
        for path in ('/api/v1/stages','/api/v1/pipelines','/api/v1/jobs'):
            params={'limit':1,'offset':0}
            if path!='/api/v1/jobs':params['name']=r['campaign_id']
            response=session.context.request.get(ORIGIN+path,params=params,timeout=15000)
            body=response.body(); parsed=None
            try:parsed=response.json()
            except Exception:pass
            usable=(response.status==200 and isinstance(parsed,dict) and isinstance(parsed.get('items'),list)
                    and type(parsed.get('total')) is int)
            routes.append({'path':path,'http_status':response.status,'json_collection':usable,
                           'body_sha256':hashlib.sha256(body).hexdigest()})
        if not all(x['json_collection'] for x in routes):
            return {'ready':False,'reason':'legacy_chain_routes_not_json','routes':routes,
                    'write_profile_enabled':WRITES_ENABLED,'mutation_executed':False,'full_case_passed':False}
        checks=[]
        for task,version in zip(TASKS,VERSIONS):
            observed=session.inspect_pinned_agent_readiness_semantic(r['ci_name'],r['agent_id'],task,version)
            checks.append({'task_name':task,'version':version,'ready':observed.get('ready'),
                           'reason':(observed.get('plugin_audit') or {}).get('reason')})
            tasks=read_json(session,urls[0],{'name':task,'periodic':False,'limit':100,'offset':0})
            if (type(tasks.get('items')) is not list or tasks.get('total') != len(tasks['items'])
                or any(x.get('agent_id') != r['agent_id'] or x.get('name') != task
                       or x.get('status') not in {'success','error','timeout'} for x in tasks['items'])):
                raise ValueError('owned_chain_existing_audit_unresolved_or_incomplete')
        return {'ready':WRITES_ENABLED and all(x['ready'] is True for x in checks),'checks':checks,'target':name,
                'write_profile_enabled':WRITES_ENABLED,'routes':routes,
                'ci_id':r['ci_id'],'agent_id':r['agent_id'],'core_version':agent['version'],
                'schema_sha256':SCHEMA_SHA,'read_at':now(),'mutation_executed':False,'full_case_passed':False}
    except Exception as e:return refusal(str(e)[:150] if isinstance(e,ValueError) else 'owned_chain_readiness_unavailable')

def create(session, name, sid, jid, cid):
    try:
        job=job_store.get_job(jid);c,r=validate_context(job,cid);stage=admit(job,cid,{'target':name,'stage_id':sid})
        ops=list_operations(jid); candidates=[o for o in ops if o['status']=='sending' and o.get('case_id')==cid
            and all(o.get(k)==stage[k] for k in ('workflow_id','stage_id','resource_key','tool'))
            and o.get('arguments_fingerprint')==_fingerprint(stage['arguments'])
            and o.get('verification_fingerprint')==_fingerprint(stage['verification'])]
        if len(candidates)!=1:raise ValueError('owned_chain_unique_core_intent')
        opid=candidates[0]['operation_id']
        if any(o['operation_id']!=opid and o['status'] not in {'verified','not_sent','rejected'} for o in ops):
            raise ValueError('owned_chain_prior_operation_unresolved')
        for previous in STAGES[:STAGES.index(sid)]:
            if not any(o['stage_id']==previous and o['status']=='verified' for o in ops):
                raise ValueError('owned_chain_previous_stage_unverified')
        if ready(session,name,jid,cid).get('ready') is not True: raise ValueError('owned_chain_not_ready')
        path,payload,status=compile_request(r,c,sid)
        if sid.startswith('stage') or sid=='pipeline':
            root='/api/v1/stages' if sid.startswith('stage') else '/api/v1/pipelines'
            exists=read_json(session,ORIGIN+root,{'name':payload['name'],'limit':100,'offset':0})
            if type(exists.get('items')) is not list or exists.get('total')!=0 or exists['items']:
                raise ValueError('owned_chain_new_name_absence_required')
        if own(c,CREATE,sid):raise ValueError('owned_chain_no_resend')
    except Exception as e:return refusal(str(e)[:150] if isinstance(e,ValueError) else 'owned_chain_preflight_refused')
    try:
        sent=now();response=session.context.request.post(ORIGIN+path,data=payload,timeout=15000);received=now()
        if response.status != status:raise ValueError('owned_chain_create_status')
        body=response.json();oid=check_object(r,c,sid,body,payload)
        if sid!='attach' and body.get('created_at') and not -120<=(stamp(received)-stamp(body['created_at'])).total_seconds()<=300:
            raise ValueError('owned_chain_create_time')
        return {'target':name,'stage_id':sid,'operation_id':opid,'object_id':oid,'response_body':body,
                'payload_sha256':digest(payload),'response_sha256':digest(body),'request_origin':ORIGIN,
                'session_id':session.session_id,'sent_at':sent,'received_at':received,'create_status':status,
                'executed':True,'mutation_executed':True,'full_case_passed':False}
    except Exception:return {'error':'owned_chain_dispatch_uncertain_no_resend','executed':False,
                              'dispatch_may_have_occurred':True,'resend_authorized':False}

def read(session,name,sid,jid,cid):
    try:
        c,r=validate_context(job_store.get_job(jid),cid)
        if name!=r['target']:raise ValueError('owned_chain_target')
        rows=own(c,CREATE,sid)
        if len(rows)!=1:raise ValueError('owned_chain_own_receipt_required')
        ce,a=rows[0];path,payload,_=compile_request(r,c,sid)
        if a['session_id']!=session.session_id:raise ValueError('owned_chain_original_session_required')
        oid=a['object_id']
        getpath=('/api/v1/stages/'+oid if sid.startswith('stage') else '/api/v1/pipelines/'+oid
                 if sid=='pipeline' else '/api/v1/pipelines/'+oid+'/stages' if sid=='attach'
                 else '/api/v1/jobs/'+oid if sid=='job' else '/api/v1/job-instance/'+oid)
        response=session.context.request.get(ORIGIN+getpath,timeout=15000)
        if response.status!=200:raise ValueError('owned_chain_read_http')
        body=response.json()
        check_object(r,c,sid,body,payload,oid)
        extra={}
        if sid=='run':
            history=read_json(session,ORIGIN+'/api/v1/job-instance/stages',{'job_instance_id':oid,'limit':100,'offset':0})
            summary=summarize_history(r,c,oid,history)
            extra={'instance_status':body.get('status'),'stage_history':summary,
                   'chain_execution_complete':body.get('status')=='success' and summary['complete'],
                   'agent_logs_verified':False}
        return {**{k:a[k] for k in ('target','stage_id','operation_id','object_id','session_id','request_origin','payload_sha256')},
                'response_body':body,'response_sha256':digest(body),'create_evidence_id':ce['evidence_id'],
                'create_evidence_sha256':hashlib.sha256(ce['value'].encode()).hexdigest(),
                'native_readback_verified':True,'read_at':now(),'mutation_executed':False,'full_case_passed':False,
                'verification_scope':'owned_new_chain_structure_or_instance_not_agent_logs',**extra}
    except Exception as e:return refusal(str(e)[:150] if isinstance(e,ValueError) else 'owned_chain_read_unavailable')

def evaluate(job,op,eid,contract):
    try:
        c,r=validate_context(job,op['case_id']);sid=op['stage_id'];stage=admit(job,op['case_id'],{'target':r['target'],'stage_id':sid},for_write=False)
        if contract!=stage['verification']:raise ValueError('contract')
        e=next(e for e in c['evidence'] if e['evidence_id']==eid);b=json.loads(e['value'])
        if e.get('source')!='uqa_tool' or b.get('tool')!=READ or b.get('arguments')!={'target':r['target'],'stage_id':sid}:
            raise ValueError('own read')
        v=b['result'];ce,a=own(c,CREATE,sid)[0]
        path,payload,_=compile_request(r,c,sid)
        if (v.get('native_readback_verified') is not True or v.get('error') or a.get('operation_id')!=op['operation_id']
            or v.get('operation_id')!=op['operation_id'] or v.get('create_evidence_id')!=ce['evidence_id']
            or v.get('create_evidence_sha256')!=hashlib.sha256(ce['value'].encode()).hexdigest()
            or v.get('payload_sha256')!=digest(payload) or a.get('payload_sha256')!=digest(payload)
            or v.get('response_sha256')!=digest(v['response_body']) or a.get('executed') is not True
            or a.get('response_sha256')!=digest(a['response_body'])
            or any(v.get(k)!=a.get(k) for k in ('target','stage_id','object_id','session_id','request_origin'))
            or v.get('request_origin')!=ORIGIN or not -5<=(stamp(now())-stamp(v['read_at'])).total_seconds()<=300
            or not stamp(op['created_at'])<=stamp(ce['created_at'])<=stamp(e['created_at'])):raise ValueError('proof')
        check_object(r,c,sid,a['response_body'],payload,a['object_id'])
        check_object(r,c,sid,v['response_body'],payload,a['object_id'])
        return {'verified':True,'evidence_id':eid,'receipt_evidence_id':ce['evidence_id'],
                'identifier_value':a['object_id'],'postcondition_verified':True,'business_pass':False,
                'resend_authorized':False,'verification_scope':'owned_chain_native_readback_not_full_source_case'}
    except Exception:return {'verified':False,'reason':'owned_chain_evidence_insufficient','resend_authorized':False}
