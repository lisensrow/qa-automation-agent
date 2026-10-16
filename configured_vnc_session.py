"""Existing configured VNC path: no config writes, legacy resend or desktop input."""
import base64,hashlib,json,re
from copy import deepcopy
from urllib.parse import urlsplit,parse_qs,urlencode
from uuid import UUID
import job_store
from command_probe_contract import target,CORE,ORIGIN,validate_target_state
from command_stage_native import context,refusal,read_json
from plugin_preparation import readiness,requirement as preparation,now,stamp
from operation_journal import list_operations,_fingerprint
PROFILE='configured-vnc-receive-session-v1'
CREATE='browser_start_closed_vnc_session_semantic'
READ='browser_inspect_closed_vnc_session_semantic'
READY='browser_read_closed_vnc_readiness_semantic'
CONFIGS={'windows':'3eaa40fe-a10a-4a21-b121-5d980a86afd0','astra':'444deeaa-f232-467d-85e3-e10b4c905813'}
REVIEW_JOB='20261016-150527-d07d36b9'
REVIEW_EVIDENCE='ev-8ba3ff5ad6d3'
REVIEW_SHA='cfbe6da6ebf352c1a3cbc30f7a9fcb50d0881f60fc6337133236b4781829ad03'

def requirement(name,campaign):
 t=target(name)
 if name not in CONFIGS or not isinstance(campaign,str) or not 1<=len(campaign)<=80 or not campaign.replace('-','').isalnum():
  raise ValueError('configured_vnc_exact_campaign_required')
 r={'type':'closed_vnc_session','stand':'lab','locked':True,'action_profile':'write_resource',
  'target':name,**{k:t[k] for k in ['ci_id','agent_id','ci_name']},'core_version':CORE,
  'profile_id':PROFILE,'campaign_id':campaign,'config_id':CONFIGS[name],'protocol':'vnc','port':5900,
  'plugin_name':'vncServer','plugin_version':'1.5.5','remote_user_session':'_ACTIVE_USER_',
  'source_review':{'job_id':REVIEW_JOB,'evidence_id':REVIEW_EVIDENCE,'sha256':REVIEW_SHA},
  'expected_profile':{'own_open_tunnel':True,'decoded_remote_image':True,'desktop_input':False,
   'config_modified':False,'full_business_case_passed':False}}
 r['operation_stages']=[{'version':1,'workflow_id':PROFILE,'stage_id':'connect',
  'resource_key':'agent-'+t['agent_id']+'-configured-vnc','tool':CREATE,'arguments':{'target':name},
  'verification':{'version':1,'kind':'owned_vnc_session','origin':ORIGIN,'target':name,
   'ci_id':t['ci_id'],'agent_id':t['agent_id'],'profile_id':PROFILE,'config_id':CONFIGS[name]}}]
 return r

def validate_context(job,cid,starting=False):
 if not isinstance(job,dict) or len(job.get('test_cases',[]))!=1:raise ValueError('single_configured_vnc_case_required')
 c=job['test_cases'][0];r=c.get('requirement') or {}
 if (c.get('case_id')!=cid or r!=requirement(r.get('target'),r.get('campaign_id')) or job.get('stand')!='lab'
  or job.get('status')!='running' or c.get('status')!='running' or job.get('job_type') not in {'manual','regression'} or job.get('resources')):
  raise ValueError('locked_configured_vnc_context_required')
 if not all(r[k] in job.get('request','') for k in ['ci_id','agent_id','ci_name','core_version','profile_id','config_id']):
  raise ValueError('original_configured_vnc_request_required')
 if starting and any(e.get('type')=='vnc_session_started' for e in c.get('evidence',[])):raise ValueError('configured_vnc_no_replay')
 return c,r

def validate_source():
 j=job_store.get_job(REVIEW_JOB)
 es=[e for c in j['test_cases'] for e in c['evidence'] if e['evidence_id']==REVIEW_EVIDENCE]
 if len(es)!=1:raise ValueError('configured_vnc_review_required')
 e=es[0]
 if (e.get('type')!='operator_configured_vnc_prerequisites' or e.get('source')!='operator_native_readonly_review'
  or e.get('execution_status')!='observed' or hashlib.sha256(e['value'].encode()).hexdigest()!=REVIEW_SHA):
  raise ValueError('configured_vnc_review_changed')
 b=json.loads(e['value'])
 if b.get('session_start_invoked') is not False or b.get('config_writes') is not False or b.get('new_agent_tasks')!=0:
  raise ValueError('configured_vnc_review_scope')
 for name,uid in CONFIGS.items():
  t=target(name);rows=[x for x in b['rows'] if x['target']==name and x['agent_id']==t['agent_id']]
  if len(rows)!=1:raise ValueError('configured_vnc_review_target')
  cs=rows[0]['observations']['configs']
  if cs['http_status']!=200 or cs['rows']!=[next(x for x in cs['rows'] if x['id']==uid)]:raise ValueError('configured_vnc_review_config')
  x=cs['rows'][0]
  if any(x.get(k)!=v for k,v in {'agent_id':t['agent_id'],'protocol':'vnc','port':5900,'credential_bound':False,'is_protocol_allowed':True}.items()):
   raise ValueError('configured_vnc_review_config_scope')
 return True

def get(session,url):
 r=session.context.request.get(url,timeout=20000)
 if r.status!=200:raise ValueError('configured_vnc_native_get_failed')
 return r.json()

def checked_config(rows,r):
 if not isinstance(rows,list):raise ValueError('configured_vnc_config_list_required')
 found=[x for x in rows if x.get('id')==r['config_id']]
 if len(found)!=1:raise ValueError('configured_vnc_existing_config_required')
 x=found[0]
 if any(x.get(k)!=v for k,v in {'agent_id':r['agent_id'],'protocol':'vnc','port':5900,'credential_id':None,'is_protocol_allowed':True}.items()):
  raise ValueError('configured_vnc_config_scope_changed')
 # Preserve user and consent policy; never infer/create/modify either.
 return hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()

def tunnel_rows(body,r):
 rows=body.get('items') if isinstance(body,dict) else None
 if not isinstance(rows,list) or type(body.get('total')) is not int or body['total']!=len(rows) or body.get('offset',0)!=0 or len(rows)>1000:
  raise ValueError('configured_vnc_complete_tunnels_required')
 ids=set()
 for x in rows:
  if (x.get('agent_id')!=r['agent_id'] or x.get('name')!='openTunnel' or x.get('period') is not None
   or str(UUID(x.get('id')))!=x['id'] or x['id'] in ids):raise ValueError('configured_vnc_tunnel_scope')
  ids.add(x['id'])
 return rows

def read_ready(session,name,jid,cid):
 try:
  _,r=validate_context(job_store.get_job(jid),cid)
  if name!=r['target']:raise ValueError('configured_vnc_target_required')
  validate_source();t,ci,urls=context(session,name);validate_target_state(name,ci,read_json(session,urls[1]))
  p=readiness(session,preparation(name,'vncServer',r['campaign_id']))
  base=urls[1].rsplit('/agents/',1)[0]
  digest=checked_config(get(session,base+'/remote-data/config/'+r['agent_id']),r)
  infos=get(session,base+'/remote-data/info/'+r['agent_id'])
  if not isinstance(infos,list):raise ValueError('configured_vnc_protocol_list_required')
  info=[x for x in infos if x.get('agent_id')==r['agent_id'] and x.get('protocol')=='vnc']
  service=(len(info)==1 and info[0].get('is_installed') is True and info[0].get('is_service_running') is True
   and info[0].get('is_default_port_opened')=='True' and info[0].get('running_service_remote_port')==5900)
  rows=tunnel_rows(read_json(session,urls[0],{'name':'openTunnel','periodic':False,'limit':1000,'offset':0}),r)
  if any(x.get('status') not in {'success','error','timeout','terminated'} for x in rows):raise ValueError('configured_vnc_unresolved_tunnel')
  return {'target':name,'ci_id':t['ci_id'],'agent_id':t['agent_id'],'core_version':CORE,'profile_id':PROFILE,
   'ready':bool(service and p['ready'] and p['load_error_empty_observed'] and p['plugin_audit']['audit_fresh']),
   'service_running_observed':bool(service),'plugin_readiness':p,'config_sha256':digest,'config_id':r['config_id'],
   'read_at':now(),'session_id':session.session_id,'business_pass':False,'mutation_executed':False}
 except Exception as e:return {'error':str(e)[:140] if isinstance(e,ValueError) else 'configured_vnc_readiness_unavailable','mutation_executed':False}

def private_tunnel_url(url):
 """Transform native GuacUnit client URL using installed Guac.get_wss contract."""
 p=urlsplit(url if isinstance(url,str) else '')
 if p.scheme!='https' or p.netloc!=urlsplit(ORIGIN).netloc or p.username or p.password or p.query or p.path.rstrip('/')!='/guacamole':
  raise ValueError('same_origin_configured_guac_client_required')
 if not p.fragment.startswith('/client/'):raise ValueError('configured_guac_client_required')
 path,sep,query=p.fragment.partition('?');q=parse_qs(query,strict_parsing=True)
 if not sep or set(q)!={'token'} or len(q['token'])!=1 or not re.fullmatch(r'[A-Za-z0-9_-]{10,2048}',q['token'][0]):
  raise ValueError('configured_guac_private_token_required')
 try:parts=base64.b64decode(path[len('/client/'):],validate=True).decode().split('\0')
 except Exception:raise ValueError('configured_guac_identifier_invalid')
 if len(parts)!=3 or parts[1:]!=['c','postgresql'] or not re.fullmatch(r'[0-9]{1,20}',parts[0]):raise ValueError('configured_guac_identifier_scope')
 return 'wss://'+p.netloc+p.path.rstrip('/')+'/websocket-tunnel?'+urlencode({'token':q['token'][0],'GUAC_DATA_SOURCE':'postgresql','GUAC_ID':parts[0]})

def create(session,name,jid,cid):
 try:
  _,r=validate_context(job_store.get_job(jid),cid);stage=r['operation_stages'][0];ops=list_operations(jid)
  selected=[o for o in ops if o.get('case_id')==cid and o.get('status')=='sending'
   and all(o.get(k)==stage[k] for k in ['workflow_id','stage_id','resource_key','tool'])
   and o.get('arguments_fingerprint')==_fingerprint({'target':name}) and o.get('verification_fingerprint')==_fingerprint(stage['verification'])]
  if name!=r['target'] or len(selected)!=1 or len(ops)!=1:raise ValueError('configured_vnc_unique_core_intent_required')
  # Separate path, not permission to resend the old failed legacy task.
  for j in job_store.list_jobs(limit=None):
   if j['job_id']==jid:continue
   for c in j.get('test_cases',[]):
    old=c.get('requirement') or {}
    if old.get('profile_id')==PROFILE and old.get('target')==name and any(o['status'] not in {'not_sent','rejected'} for o in list_operations(j['job_id'])):
     raise ValueError('configured_vnc_prior_attempt_no_rekey')
  ready=read_ready(session,name,jid,cid)
  if ready.get('ready') is not True:raise ValueError(ready.get('error') or 'configured_vnc_prerequisites_not_ready')
  _,_,urls=context(session,name);base=urls[1].rsplit('/agents/',1)[0]
  before=tunnel_rows(read_json(session,urls[0],{'name':'openTunnel','periodic':False,'limit':1000,'offset':0}),r)
 except Exception as e:return refusal(str(e)[:140] if isinstance(e,ValueError) else 'configured_vnc_preflight_refused')
 try:
  sent=now()
  response=session.context.request.get(base+'/remote-data/start/'+r['config_id'],
   params={'remote_user_session':'_ACTIVE_USER_','wait_connection_seconds':30},timeout=60000)
  received=now()
  if response.status!=200:raise ValueError('configured_vnc_start_not_accepted')
  b=response.json()
  if b.get('status')!='ready':raise ValueError('configured_vnc_not_ready')
  wss=private_tunnel_url(b.get('url'))
  after=tunnel_rows(read_json(session,urls[0],{'name':'openTunnel','periodic':False,'limit':1000,'offset':0}),r)
  oldids={x['id'] for x in before};fresh=[x for x in after if x['id'] not in oldids]
  if len(fresh)!=1 or not oldids.issubset({x['id'] for x in after}):raise ValueError('configured_vnc_unique_new_tunnel_required')
  x=fresh[0];params=x.get('additional_params') or {}
  if (params.get('port')!=5900 or params.get('user')!='_ACTIVE_USER_' or str(UUID(params.get('session_id')))!=params['session_id']
   or not -120<=(stamp(x['created_at'])-stamp(sent)).total_seconds()<=180):raise ValueError('configured_vnc_new_tunnel_identity')
  if checked_config(get(session,base+'/remote-data/config/'+r['agent_id']),r)!=ready['config_sha256']:raise ValueError('configured_vnc_config_changed')
  from vnc_session import FRAME_JS,frame_ok
  frame=session.page.evaluate(FRAME_JS,wss)
  own={k:r[k] for k in ['target','ci_id','agent_id','profile_id','config_id']}
  own.update(job_id=jid,case_id=cid,operation_id=selected[0]['operation_id'],session_id=session.session_id,
   sent_at=sent,received_at=received,task_id=x['id'],server_created_at=x['created_at'],tunnel_session_id=params['session_id'],
   config_sha256=ready['config_sha256'],frame=frame,frame_verified=bool(frame_ok(frame)),desktop_input=False,
   private_url_disclosed=False,request_origin=ORIGIN)
  if not hasattr(session,'_configured_vnc_owned'):session._configured_vnc_owned={}
  session._configured_vnc_owned[(jid,cid)]=own
  return {**own,'executed':True,'mutation_executed':True,'create_status':200,'business_pass':False}
 except Exception:return {'error':'configured_vnc_start_uncertain_no_resend','executed':False,'dispatch_may_have_occurred':True,'resend_authorized':False}

def read(session,name,jid,cid):
 try:
  _,r=validate_context(job_store.get_job(jid),cid);own=getattr(session,'_configured_vnc_owned',{}).get((jid,cid))
  if not own or own['session_id']!=session.session_id or name!=own['target']:raise ValueError('configured_vnc_owned_receipt_required')
  _,_,urls=context(session,name);full=read_json(session,urls[0]+'/'+own['task_id']+'/full');params=full.get('additional_params') or {}
  if (any(full.get(k)!=v for k,v in {'id':own['task_id'],'agent_id':r['agent_id'],'name':'openTunnel','created_at':own['server_created_at'],'period':None,'status':'success'}.items())
   or params.get('port')!=5900 or params.get('session_id')!=own['tunnel_session_id'] or params.get('user')!='_ACTIVE_USER_'):
   raise ValueError('configured_vnc_owned_tunnel_not_successful')
  env=full.get('result') or {}
  if env.get('machine_uid')!=r['ci_id'] or env.get('result')!='success' or not -120<=(stamp(env.get('processed_at'))-stamp(own['sent_at'])).total_seconds()<=300:
   raise ValueError('configured_vnc_owned_fresh_result_required')
  base=urls[1].rsplit('/agents/',1)[0]
  if checked_config(get(session,base+'/remote-data/config/'+r['agent_id']),r)!=own['config_sha256']:raise ValueError('configured_vnc_config_changed')
  return {**own,'native_result_verified':True,'processed_at':env['processed_at'],'read_at':now(),
   'session_observation_status':'PASS' if own['frame_verified'] else 'BLOCKED','full_business_case_passed':False,'business_pass':False,'mutation_executed':False}
 except Exception as e:return {'error':str(e)[:140] if isinstance(e,ValueError) else 'configured_vnc_own_read_unavailable','mutation_executed':False}

def evaluate(job,op,eid,contract):
 try:
  c,r=validate_context(job,op['case_id']);stage=r['operation_stages'][0]
  if contract!=stage['verification'] or (op.get('receipt') or {}).get('acknowledged') is not True:raise ValueError('configured_vnc_contract')
  def native(e,tool):
   if e.get('source')!='uqa_tool' or e.get('type')!=tool or e.get('execution_status') not in {'executed','observed'}:raise ValueError('native_required')
   b=json.loads(e['value'])
   if b.get('tool')!=tool or b.get('arguments')!={'target':r['target']}:raise ValueError('native_scope')
   return b['result']
  ev=next(e for e in c['evidence'] if e['evidence_id']==eid);b=native(ev,READ)
  creates=[e for e in c['evidence'] if e.get('type')==CREATE]
  if len(creates)!=1:raise ValueError('unique_receipt')
  ce=creates[0];a=native(ce,CREATE)
  for k,v in {**{k:r[k] for k in ['target','ci_id','agent_id','profile_id','config_id']},'job_id':job['job_id'],'case_id':op['case_id'],
   'operation_id':op['operation_id'],'desktop_input':False,'private_url_disclosed':False,'request_origin':ORIGIN}.items():
   if a.get(k)!=v or b.get(k)!=v:raise ValueError('configured_vnc_proof_scope')
  if (a.get('executed') is not True or a.get('mutation_executed') is not True or a.get('create_status')!=200 or a.get('error') or b.get('error')
   or b.get('native_result_verified') is not True or not a.get('session_id') or b.get('session_id')!=a['session_id']
   or b.get('task_id')!=a.get('task_id') or str(UUID(a.get('task_id')))!=a['task_id']
   or any(b.get(k)!=a.get(k) for k in ['frame','frame_verified','config_sha256','server_created_at','tunnel_session_id','sent_at','received_at'])
   or len(bytes.fromhex(a.get('config_sha256','')))!=32 or stamp(ce['created_at'])<stamp(op['created_at'])
   or stamp(ev['created_at'])<stamp(ce['created_at']) or not -5<=(stamp(now())-stamp(ev['created_at'])).total_seconds()<=300
   or not -5<=(stamp(ev['created_at'])-stamp(b['read_at'])).total_seconds()<=60):raise ValueError('configured_vnc_owned_fresh_proof')
  from vnc_session import frame_ok
  return {'verified':True,'evidence_id':eid,'receipt_evidence_id':ce['evidence_id'],'identifier_value':a['task_id'],
   'postcondition_verified':True,'resend_authorized':False,'frame_verified':bool(frame_ok(a['frame'])),
   'verification_scope':'own_configured_openTunnel_and_frame_not_full_case','business_pass':False}
 except (ValueError,TypeError,KeyError,AttributeError,StopIteration,OverflowError):
  return {'verified':False,'reason':'configured_vnc_evidence_insufficient','resend_authorized':False}
