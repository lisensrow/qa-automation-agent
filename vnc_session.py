"""Closed supplied-release VNC connection; no desktop input, tokens or resends."""
import hashlib,json
from copy import deepcopy
from urllib.parse import urlsplit
from uuid import UUID
import job_store
from command_probe_contract import target,validate_target_state,ORIGIN,CORE
from command_stage_native import context,read_json,refusal
from plugin_preparation import readiness,requirement as preparation,stamp,now,validate_release_source,RELEASE_JOB
from operation_journal import list_operations,_fingerprint

CREATE='browser_start_closed_vnc_session_semantic'
READ='browser_inspect_closed_vnc_session_semantic'
READY='browser_read_closed_vnc_readiness_semantic'
PROFILE='supplied-vnc-receive-session-v1'
TASKS=('displayMonitoring','initRemoteDesktopConnection')
PLUGIN_VERSIONS={'displayMonitoring':'1.3.1','vncServer':'1.5.5'}
REPAIR_REVIEW={'job_id':'20261016-101836-d1357955','evidence_id':'ev-b5d50f390bc1',
 'sha256':'66d13feadda926930ddc096a92d6b9658fa70c6d4707968365197a1911afe319'}

def requirement(name,campaign,repair_review=None):
    t=target(name)
    if not isinstance(campaign,str) or not 1<=len(campaign)<=80 or not campaign.replace('-','').isalnum():
        raise ValueError('closed_vnc_campaign_required')
    r={'type':'closed_vnc_session','stand':'lab','locked':True,'action_profile':'write_resource',
       'target':name,**{k:t[k] for k in ['ci_id','agent_id','ci_name']},'core_version':CORE,
       'profile_id':PROFILE,'campaign_id':campaign,'plugins':deepcopy(PLUGIN_VERSIONS),
       'remote_user_session':'_ACTIVE_USER_','source_release_job':RELEASE_JOB,
       'expected_profile':{'own_linked_tasks':True,'decoded_remote_image':True,'desktop_input':False,
                           'workbook_target_satisfied':False,'full_business_case_passed':False}}
    r['operation_stages']=[{'version':1,'workflow_id':PROFILE,'stage_id':'connect',
      'resource_key':'agent-'+t['agent_id']+'-vnc-session','tool':CREATE,'arguments':{'target':name},
      'verification':{'version':1,'kind':'owned_vnc_session','origin':ORIGIN,'target':name,
          'ci_id':t['ci_id'],'agent_id':t['agent_id'],'profile_id':PROFILE}}]
    if repair_review is not None:
        if repair_review!=REPAIR_REVIEW:raise ValueError('exact_authorized_vnc_repair_review_required')
        r['prior_attempt_review']=deepcopy(repair_review)
    return r

def validate_context(job,cid,starting=False):
    if _configured_profile(job):
        from configured_vnc_session import validate_context as configured_context
        return configured_context(job,cid,starting)
    if not isinstance(job,dict) or len(job.get('test_cases',[]))!=1:raise ValueError('single_vnc_case_required')
    c=job['test_cases'][0];r=c.get('requirement') or {}
    if (c.get('case_id')!=cid or r!=requirement(r.get('target'),r.get('campaign_id'),r.get('prior_attempt_review'))
        or job.get('stand')!='lab' or job.get('status')!='running' or c.get('status')!='running'
        or job.get('job_type') not in {'manual','regression'} or job.get('resources')):
        raise ValueError('locked_vnc_context_required')
    if not all(r[k] in job.get('request','') for k in ['ci_id','agent_id','ci_name','profile_id','core_version']):
        raise ValueError('original_vnc_request_required')
    if starting and any(e['type']=='vnc_session_started' for e in c.get('evidence',[])):
        raise ValueError('no_vnc_runtime_replay')
    return c,r

def admit(job,cid,args):
    _,r=validate_context(job,cid)
    if args!={'target':r['target']}:raise ValueError('exact_vnc_target_required')
    return deepcopy(r['operation_stages'][0])

def complete_tasks(name,body,task):
    t=target(name);rows=body.get('items') if isinstance(body,dict) else None
    if (not isinstance(rows,list) or type(body.get('total')) is not int or body['total']!=len(rows)
        or body.get('offset',0)!=0 or len(rows)>1000):raise ValueError('complete_vnc_task_list_required')
    ids=set()
    for x in rows:
        if (not isinstance(x,dict) or x.get('agent_id')!=t['agent_id'] or x.get('name')!=task
            or x.get('period') is not None or str(UUID(x.get('id')))!=x['id'] or x['id'] in ids):
            raise ValueError('vnc_task_identity_required')
        ids.add(x['id'])
    return rows

def linked_receipts(name,before,after,sent,received):
    t=target(name);found=[]
    for task in TASKS:
        old=complete_tasks(name,before[task],task);new=complete_tasks(name,after[task],task)
        ids={x['id'] for x in old}
        if not ids.issubset({x['id'] for x in new}):raise ValueError('vnc_task_history_changed')
        fresh=[x for x in new if x['id'] not in ids]
        if len(fresh)!=1:raise ValueError('unique_new_vnc_pair_required')
        x=fresh[0];p=x.get('additional_params')
        if (not isinstance(p,dict) or not isinstance(p.get('session_id'),str)
            or str(UUID(p['session_id']))!=p['session_id'] or x.get('run_as_user')!='_ACTIVE_USER_'
            or not -120<=(stamp(x['created_at'])-stamp(sent)).total_seconds()<=180
            or not -120<=(stamp(received)-stamp(x['created_at'])).total_seconds()<=180):
            raise ValueError('vnc_pair_time_session_required')
        found.append(x)
    if found[0]['additional_params']['session_id']!=found[1]['additional_params']['session_id']:
        raise ValueError('vnc_pair_session_mismatch')
    for task in TASKS:
        if any(x.get('additional_params',{}).get('session_id')==found[0]['additional_params']['session_id']
               for x in before[task]['items']):raise ValueError('vnc_session_not_new')
    return [{'task_id':x['id'],'task_name':x['name'],'server_created_at':x['created_at']} for x in found]

def _configured_profile(job):
    cases=(job or {}).get('test_cases') or []
    return bool(len(cases)==1 and (cases[0].get('requirement') or {}).get('profile_id')=='configured-vnc-receive-session-v1')

def read_ready(session,name,jid,cid):
    try:
        if _configured_profile(job_store.get_job(jid)):
            from configured_vnc_session import read_ready as configured_ready
            return configured_ready(session,name,jid,cid)
        _,r=validate_context(job_store.get_job(jid),cid)
        if name!=r['target']:raise ValueError('vnc_target_scope')
        t,ci,urls=context(session,name);agent=read_json(session,urls[1]);validate_target_state(name,ci,agent)
        plugins={}
        for plugin in PLUGIN_VERSIONS:
            checked=readiness(session,preparation(name,plugin,r['campaign_id']))
            plugins[plugin]=bool(checked['ready'] and checked['load_error_empty_observed'] and checked['plugin_audit']['audit_fresh'])
        before={task:read_json(session,urls[0],{'name':task,'periodic':False,'limit':1000,'offset':0}) for task in TASKS}
        for task in TASKS:
            rows=complete_tasks(name,before[task],task)
            if any(x.get('status') not in {'success','error','timeout'} for x in rows):
                raise ValueError('prior_vnc_task_unresolved_no_cancel')
        return {'target':name,'ci_id':t['ci_id'],'agent_id':t['agent_id'],'core_version':CORE,
          'ready':all(plugins.values()),'plugins_loaded':plugins,'prior_tasks_terminal':True,
          'read_at':now(),'session_id':session.session_id,'mutation_executed':False,'business_pass':False}
    except Exception as e:
        return {'error':str(e)[:140] if isinstance(e,ValueError) else 'vnc_readiness_unavailable','mutation_executed':False}

# Guacamole protocol: receive/decode only, acknowledge sync/images, NEVER input.
FRAME_JS=r"""async (url) => await new Promise(resolve => {
 let done=false,buf='',ws,streams={},images=[],sizes=[],syncs=0,bytes=0,instructions=0,pending=0;
 const finish=(reason)=>{if(done)return;done=true;clearTimeout(timer);try{ws.close()}catch(e){}
   resolve({reason,decoded_images:images,surface_sizes:sizes,syncs,bytes,instructions,desktop_input:false});};
 const enc=(a)=>a.map(x=>String(x).length+'.'+String(x)).join(',')+';';
 const send=(a)=>{if(ws.readyState===1)ws.send(enc(a));};
 const timer=setTimeout(()=>finish('bounded_timeout'),20000);
 const handle=(a)=>{
   instructions++;if(instructions>100000||bytes>16777216){finish('bounded_limit');return;}
   if(a[0]==='size'&&a[1]==='0')sizes.push({width:Number(a[2]),height:Number(a[3])});
   if(a[0]==='sync'){syncs++;send(['sync',a[1]]);}
   if(a[0]==='img'&&a[3]==='0'&&['image/png','image/jpeg'].includes(a[4]))
       streams[a[1]]={mime:a[4],chunks:[]};
   if(a[0]==='blob'&&streams[a[1]]){
       bytes+=a[2].length;streams[a[1]].chunks.push(a[2]);send(['ack',a[1],'OK','0']);}
   if(a[0]==='end'&&streams[a[1]]){
       const stream=streams[a[1]];delete streams[a[1]];pending++;
       try {const raw=Uint8Array.from(atob(stream.chunks.join('')),c=>c.charCodeAt(0));
         const blob=new Blob([raw],{type:stream.mime});
         createImageBitmap(blob).then(async im=>{
           const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw))).map(x=>x.toString(16).padStart(2,'0')).join('');
           images.push({width:im.width,height:im.height,bytes:raw.length,sha256:digest,mime:stream.mime});im.close();
           pending--;if(images.length&&syncs)finish('decoded_remote_image');
         }).catch(()=>{pending--;});
       }catch(e){pending--;}
   }
   if(a[0]==='error')finish('remote_protocol_error');
 };
 const parse=()=>{while(buf.length&&!done){let pos=0,a=[];
   while(true){let dot=buf.indexOf('.',pos);if(dot<0)return;
     let nstr=buf.slice(pos,dot);if(!/^[0-9]{1,8}$/.test(nstr)){finish('invalid_protocol');return;}
     let n=Number(nstr);if(n>16777216){finish('bounded_limit');return;}
     let end=dot+1+n;if(buf.length<=end)return;a.push(buf.slice(dot+1,end));
     let term=buf[end];pos=end+1;if(term===';'){buf=buf.slice(pos);handle(a);break;}
     if(term!==','){finish('invalid_protocol');return;}
   }
 }};
 try{ws=new WebSocket(url,'guacamole');ws.onmessage=e=>{
   if(typeof e.data!=='string'){finish('unexpected_binary');return;}buf+=e.data;
   if(buf.length>16777216){finish('bounded_limit');return;}parse();};
   ws.onerror=()=>finish('connection_error');ws.onclose=()=>finish('connection_closed');
 }catch(e){finish('connection_unavailable');}
})"""

def validate_url(url):
    p=urlsplit(url if isinstance(url,str) else '')
    if (p.scheme!='wss' or p.hostname!=urlsplit(ORIGIN).hostname or p.port not in {None,443}
        or p.username or p.password or not p.path.endswith('/websocket-tunnel') or not p.query or p.fragment):
        raise ValueError('same_origin_private_vnc_tunnel_required')
    return True

def reviewed_attempt_allows(r,old,case,operations,before):
    """One exact operator-reviewed pre-dispatch failure, never general resend authority."""
    try:
        if r.get('prior_attempt_review')!=REPAIR_REVIEW:return False
        review=job_store.get_job(REPAIR_REVIEW['job_id'])
        evs=[e for c in review['test_cases'] for e in c.get('evidence',[]) if e['evidence_id']==REPAIR_REVIEW['evidence_id']]
        if len(evs)!=1:return False
        e=evs[0]
        if (e.get('source')!='operator_authorized_environment_repair_review'
            or e.get('type')!='operator_guacamole_repair_review' or e.get('execution_status')!='observed'
            or e.get('usable_for_pass') is not False or e.get('usable_for_verdict') is not False
            or hashlib.sha256(e['value'].encode()).hexdigest()!=REPAIR_REVIEW['sha256']):return False
        b=json.loads(e['value'])
        if (b.get('schema')!='uqa.authorized-vnc-url-repair-review.v1'
            or any(b.get(k) is not True for k in ['user_authorized_url_repair_and_continuation','old_ledger_unchanged',
              'public_DSN_unchanged','exact_live_environment_preserved_except_internal_url',
              'images_security_mounts_ports_unchanged','backend_healthy','guacamole_api_authenticated',
              'operator_prepared_continuation_not_uninterrupted_autonomy'])
            or b.get('internal_API_path')!='/guacamole/'
            or b.get('configuration_after_sha256')!='ac67fc2f2bb98b98b3c896d8d142fee9dd5272cd336300c4769938444f92151d'
            or b.get('continuation_scope')!='one_new_attempt_per_exact_target_after_fresh_native_absence_check'
            or b.get('new_agent_tasks')!=0 or b.get('business_pass') is not False):return False
        rows=[x for x in b['rows'] if x['target']==r['target']]
        if len(rows)!=1 or len(operations)!=1:return False
        row=rows[0];op=operations[0]
        if (row['prior_job_id']!=old['job_id'] or row['prior_case_id']!=case['case_id']
            or row['prior_operation_id']!=op['operation_id'] or op['case_id']!=case['case_id']
            or op['tool']!=CREATE or op['status']!='uncertain' or row['prior_operation_status']!='uncertain'
            or row['prior_created_at']!=op['created_at'] or row['no_tasks_in_prior_window'] is not True
            or any(row[k]!=r[k] for k in ['agent_id','ci_id'])
            or case['requirement']!=requirement(r['target'],'uqa-vnc-v442')):return False
        at=stamp(op['created_at'])
        for task in TASKS:
            if any(-120<=(stamp(x['created_at'])-at).total_seconds()<=180
                for x in complete_tasks(r['target'],before[task],task)):return False
        return True
    except (ValueError,TypeError,KeyError,AttributeError,IndexError):return False

def frame_ok(frame):
    return (isinstance(frame,dict) and frame.get('desktop_input') is False and frame.get('syncs',0)>0
      and any(type(x.get('width')) is int and 0<x['width']<=16384 and type(x.get('height')) is int
          and 0<x['height']<=16384 for x in frame.get('surface_sizes',[]))
      and any(type(x.get('bytes')) is int and 0<x['bytes']<=16777216 and x.get('mime') in {'image/png','image/jpeg'}
          and type(x.get('width')) is int and 0<x['width']<=16384 and type(x.get('height')) is int
          and 0<x['height']<=16384 and isinstance(x.get('sha256'),str) and len(x['sha256'])==64
          for x in frame.get('decoded_images',[])))

def create(session,name,jid,cid):
    try:
        if _configured_profile(job_store.get_job(jid)):
            from configured_vnc_session import create as configured_create
            return configured_create(session,name,jid,cid)
        _,current_requirement=validate_context(job_store.get_job(jid),cid)
        stage=admit(job_store.get_job(jid),cid,{'target':name})
        ops=list_operations(jid)
        own=[o for o in ops if o['case_id']==cid and o['status']=='sending'
           and all(o.get(k)==stage[k] for k in ['workflow_id','stage_id','resource_key','tool'])
           and o['arguments_fingerprint']==_fingerprint(stage['arguments'])
           and o['verification_fingerprint']==_fingerprint(stage['verification'])]
        if len(own)!=1 or any(o['status'] not in {'verified','not_sent'} and o['operation_id']!=own[0]['operation_id'] for o in ops):
            raise ValueError('unique_core_vnc_intent_required')
        validate_release_source(job_store.get_job(RELEASE_JOB))
        ready=read_ready(session,name,jid,cid)
        if ready.get('ready') is not True:raise ValueError(ready.get('error') or 'vnc_plugins_not_fresh_ready')
        t,_,urls=context(session,name)
        before={task:read_json(session,urls[0],{'name':task,'periodic':False,'limit':1000,'offset':0}) for task in TASKS}
        for task in TASKS:
            if any(x['status'] not in {'success','error','timeout'} for x in complete_tasks(name,before[task],task)):
                raise ValueError('prior_vnc_task_unresolved_no_cancel')
        # Across campaign replay guard: never create a second connected/uncertain attempt automatically.
        for old in job_store.list_jobs(limit=None):
            if old['job_id']==jid:continue
            for c in old.get('test_cases',[]):
                r=c.get('requirement') or {}
                if r.get('type')=='closed_vnc_session' and r.get('target')==name:
                    oldops=list_operations(old['job_id'])
                    if any(o['status'] not in {'not_sent','rejected'} for o in oldops) and not reviewed_attempt_allows(current_requirement,old,c,oldops,before):
                        raise ValueError('prior_vnc_attempt_requires_review_no_rekey')
        opid=own[0]['operation_id']
    except Exception as e:return refusal(str(e)[:140] if isinstance(e,ValueError) else 'vnc_preflight_refused')
    try:
        sent=now()
        response=session.context.request.post(urls[1]+'/remote/vnc',
            params={'remote_user_session':'_ACTIVE_USER_'},timeout=90000)
        received=now()
        if response.status!=200:raise ValueError('vnc_post_not_accepted_no_resend')
        body=response.json();validate_url(body.get('url'))
        display=(body.get('info') or {}).get('display_info') or {}
        if (not isinstance(display.get('displays'),list) or not display['displays']
            or not -120<=(stamp(display['processed_at'])-stamp(sent)).total_seconds()<=180):
            raise ValueError('fresh_vnc_display_info_required')
        after={task:read_json(session,urls[0],{'name':task,'periodic':False,'limit':1000,'offset':0}) for task in TASKS}
        tasks=linked_receipts(name,before,after,sent,now())
        # Private page evaluation receives token only in memory; return metadata/digests, not URL/pixels.
        frame=session.page.evaluate(FRAME_JS,body['url'])
        record={'target':name,'ci_id':t['ci_id'],'agent_id':t['agent_id'],'profile_id':PROFILE,
          'job_id':jid,'case_id':cid,'operation_id':opid,'session_id':session.session_id,
          'sent_at':sent,'received_at':received,'tasks':tasks,'display_processed_at':display['processed_at'],
          'display_count':len(display['displays']),'frame':frame,'frame_verified':bool(frame_ok(frame)),
          'desktop_input':False,'private_url_disclosed':False,'request_origin':ORIGIN}
        if not hasattr(session,'_owned_vnc_sessions'):session._owned_vnc_sessions={}
        session._owned_vnc_sessions[(jid,cid)]=record
        return {**record,'create_status':200,'executed':True,'mutation_executed':True,'business_pass':False}
    except Exception:
        return {'error':'vnc_dispatch_or_session_uncertain_no_resend','executed':False,
          'dispatch_may_have_occurred':True,'resend_authorized':False,'private_url_disclosed':False}

def read(session,name,jid,cid):
    try:
        if _configured_profile(job_store.get_job(jid)):
            from configured_vnc_session import read as configured_read
            return configured_read(session,name,jid,cid)
        _,r=validate_context(job_store.get_job(jid),cid)
        own=getattr(session,'_owned_vnc_sessions',{}).get((jid,cid))
        if (name!=r['target'] or not own or own['session_id']!=session.session_id or own['target']!=name):
            raise ValueError('own_vnc_session_receipt_required')
        t,_,urls=context(session,name);details=[]
        for receipt in own['tasks']:
            b=read_json(session,urls[0]+'/'+receipt['task_id']+'/full')
            if (b.get('id')!=receipt['task_id'] or b.get('agent_id')!=t['agent_id']
                or b.get('name')!=receipt['task_name'] or b.get('created_at')!=receipt['server_created_at']
                or b.get('period') is not None or b.get('run_as_user')!='_ACTIVE_USER_'):
                raise ValueError('own_vnc_full_identity_required')
            details.append({'task_id':b['id'],'task_name':b['name'],'status':b.get('status'),
                            'server_created_at':b['created_at']})
        return {**own,'own_full_reads':details,'native_result_verified':True,'read_at':now(),
          'session_observation_status':'PASS' if own['frame_verified'] else 'BLOCKED',
          'full_business_case_passed':False,'business_pass':False,'mutation_executed':False}
    except Exception as e:
        return {'error':str(e)[:140] if isinstance(e,ValueError) else 'vnc_own_read_unavailable','mutation_executed':False}

def evaluate(job,op,eid,contract):
    if _configured_profile(job):
        from configured_vnc_session import evaluate as configured_evaluate
        return configured_evaluate(job,op,eid,contract)
    try:
        c,r=validate_context(job,op['case_id']);stage=r['operation_stages'][0]
        if contract!=stage['verification'] or (op.get('receipt') or {}).get('acknowledged') is not True:
            raise ValueError('vnc_contract_receipt')
        def native(e,tool):
            if e.get('source')!='uqa_tool' or e.get('execution_status') not in {'observed','executed'}:
                raise ValueError('native_required')
            b=json.loads(e['value'])
            if b.get('tool')!=tool or b.get('arguments')!={'target':r['target']}:raise ValueError('native_scope')
            return b['result']
        ev=next(e for e in c['evidence'] if e['evidence_id']==eid);readback=native(ev,READ)
        candidates=[]
        for e in c['evidence']:
            if e.get('type')!=CREATE:continue
            b=native(e,CREATE)
            if b.get('operation_id')==op['operation_id']:candidates.append((e,b))
        if len(candidates)!=1:raise ValueError('unique_vnc_create_required')
        ce,created=candidates[0]
        for k,v in {'target':r['target'],'ci_id':r['ci_id'],'agent_id':r['agent_id'],'job_id':job['job_id'],
          'case_id':op['case_id'],'profile_id':PROFILE,'operation_id':op['operation_id'],
          'request_origin':ORIGIN,'desktop_input':False,'private_url_disclosed':False}.items():
            if created.get(k)!=v or readback.get(k)!=v:raise ValueError('own_vnc_proof_scope')
        if (created.get('executed') is not True or created.get('mutation_executed') is not True
            or created.get('create_status')!=200 or created.get('error') or readback.get('error')
            or not created.get('session_id') or readback.get('session_id')!=created['session_id']
            or readback.get('tasks')!=created.get('tasks') or readback.get('frame')!=created.get('frame')
            or readback.get('native_result_verified') is not True
            or len(readback.get('own_full_reads',[]))!=2
            or {x['task_id'] for x in readback['own_full_reads']}!={x['task_id'] for x in created['tasks']}
            or stamp(ce['created_at'])<stamp(op['created_at']) or stamp(ev['created_at'])<stamp(ce['created_at'])
            or not -5<=(stamp(now())-stamp(ev['created_at'])).total_seconds()<=300):
            raise ValueError('vnc_fresh_owned_pair_required')
        return {'verified':True,'evidence_id':eid,'receipt_evidence_id':ce['evidence_id'],
          'identifier_value':created['tasks'][1]['task_id'],'postcondition_verified':True,'resend_authorized':False,
          'verification_scope':'own_linked_vnc_tasks_and_frame_metadata_not_full_case',
          'frame_verified':bool(frame_ok(created['frame'])),'business_pass':False}
    except (ValueError,TypeError,KeyError,AttributeError,StopIteration,OverflowError):
        return {'verified':False,'reason':'vnc_evidence_insufficient','resend_authorized':False}
