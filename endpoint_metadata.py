"""Closed endpoint profiles: read-only Astra metadata or exact authorized MSI.

Destructive Windows removal has a distinct tool/profile and v069 policy class;
the default metadata tool cannot invoke it. No arbitrary payload or log writes.
"""
import hashlib,json
from copy import deepcopy
from uuid import UUID
import job_store
from command_probe_contract import target,validate_preflight,validate_target_state,validate_task_list,CORE,ORIGIN
from command_stage_native import context,read_json,refusal
from plugin_preparation import stamp,now,validate_release_source,RELEASE_JOB
from operation_journal import list_operations,_fingerprint
from tools.agent_update import audit_result_is_fresh
CREATE='browser_start_closed_endpoint_metadata_semantic'
READ='browser_inspect_closed_endpoint_metadata_semantic'
READY='browser_read_closed_endpoint_metadata_readiness_semantic'
PROFILE='agent-tray-log-metadata-v1'
from windows_legacy_msi import PROFILE as MSI,REMOVE,POST_PROFILE as POST_MSI
from user_session_census import PROFILE as SESSIONS
from drive_os_baseline import PROFILE as DISKS
from gpu_os_baseline import PROFILE as GPUS
from software_os_baseline import PROFILE as SOFTWARE
from os_identity_baseline import PROFILE as OS_IDENTITY
PROGRAM='/usr/bin/python3'
CODE=r"""import os,stat,time,json,hashlib
ROOT='/opt/usystem/usagent/var/log/usagent'
def sample():
 out={'status':'unknown','files':[],'bounded':True}
 try:
  fd=os.open(ROOT,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
  try:
   names=os.listdir(fd)
   if len(names)>1000:out['bounded']=False;names=names[:1000]
   for name in names:
    try:
     s=os.stat(name,dir_fd=fd,follow_symlinks=False)
     if stat.S_ISREG(s.st_mode):
      out['files'].append({'id':hashlib.sha256(name.encode()).hexdigest(),'size':s.st_size,'mtime_ns':s.st_mtime_ns})
    except OSError:out['status']='partial'
   if out['status']!='partial':out['status']='ok'
  finally:os.close(fd)
 except FileNotFoundError:out['status']='missing'
 except PermissionError:out['status']='denied'
 except OSError:out['status']='error'
 return out
a=sample();time.sleep(5);b=sample()
tray={'autostart_entry_present':os.path.isfile('/etc/xdg/autostart/usagenttray.desktop'),
      'declared_script_present':os.path.isfile('/opt/usystem/usagent/usAgentTray.sh'),
      'process_candidates':0,'process_scan_complete':True}
try:
 names=[x for x in os.listdir('/proc') if x.isdigit()]
 if len(names)>10000:tray['process_scan_complete']=False;names=names[:10000]
 for pid in names:
  try:
   with open('/proc/'+pid+'/comm') as f:name=f.read(64).strip().casefold()
   if name in ('usagenttray','usagenttray.sh'):tray['process_candidates']+=1
  except FileNotFoundError:pass
  except OSError:tray['process_scan_complete']=False
except OSError:tray['process_scan_complete']=False
print(json.dumps({'probe_version':1,'sample_interval_seconds':5,'first':a,'second':b,'tray':tray},sort_keys=True))
"""
PAYLOAD={'name':'executeCommand','period':None,'ttl':None,'run_as_user':'',
         'additional_params':{'programm':PROGRAM,'arguments':['-c',CODE]}}
SHA=hashlib.sha256(CODE.encode()).hexdigest()
POST_LOG='post-vnc-log-observation-v1'
LOG_BASELINE={'job_id':'20261016-093711-1336ce49','evidence_id':'ev-4df4a9246ce6',
 'task_id':'260602d7-e815-4114-ad19-deac82538eb3',
 'result_sha256':'44f13a66aef3212787512a43a98c053c8b4d050c87d58664f9f560abf467605b',
 'latest_log_mtime_ns':1792122555360242211}

def validate_log_baseline():
 j=job_store.get_job(LOG_BASELINE['job_id'])
 e=next(e for c in j['test_cases'] for e in c.get('evidence',[]) if e['evidence_id']==LOG_BASELINE['evidence_id'])
 if (e.get('source')!='operator_primary_proof_review' or e.get('type')!='operator_endpoint_metadata_review'
   or e.get('execution_status')!='observed'):raise ValueError('reviewed_log_baseline_required')
 b=json.loads(e['value']);a=b['operator_own_full_readback']
 if (b.get('error') is not None or a.get('own_full_readback_matched') is not True
   or a.get('own_task_id')!=LOG_BASELINE['task_id'] or a.get('result_sha256')!=LOG_BASELINE['result_sha256']
   or a.get('latest_log_mtime_ns')!=LOG_BASELINE['latest_log_mtime_ns']):raise ValueError('log_baseline_changed')
 oldops=list_operations('20261016-093351-aeec52e0')
 if len(oldops)!=1 or oldops[0]['status']!='verified':raise ValueError('log_baseline_execution_required')
 return True
def requirement(name,campaign,profile=PROFILE):
 if profile not in {PROFILE,'legacy-vnc-identity-v1',POST_LOG,MSI,POST_MSI,SESSIONS,DISKS,GPUS,SOFTWARE,OS_IDENTITY}:raise ValueError('endpoint_profile_required')
 from legacy_vnc_identity import PROFILE as LEGACY,SHA as LSHA
 t=target(name)
 if not isinstance(campaign,str) or not 1<=len(campaign)<=80 or not campaign.replace('-','').isalnum():
  raise ValueError('endpoint_campaign_required')
 r={'type':'closed_endpoint_metadata','stand':'lab','locked':True,'action_profile':'write_resource',
    'target':name,**{k:t[k] for k in ['ci_id','agent_id','ci_name']},'core_version':CORE,
    'plugin_name':'executeCommand','plugin_version':'1.4.0','profile_id':PROFILE,'campaign_id':campaign,
    'payload_sha256':SHA,'supported_os':'astra','source_release_job':RELEASE_JOB,
    'expected_profile':{'log_files_present':True,'write_between_samples':True,
      'tray_process_observation_only':True,'tray_desktop_verified':False,'log_contents_read':False,'file_writes':False}}
 r['operation_stages']=[{'version':1,'workflow_id':PROFILE,'stage_id':'metadata',
   'resource_key':'agent-'+t['agent_id']+'-tray-logs','tool':CREATE,'arguments':{'target':name},
   'verification':{'version':1,'kind':'owned_endpoint_metadata','origin':ORIGIN,'target':name,
     'ci_id':t['ci_id'],'agent_id':t['agent_id'],'profile_id':PROFILE,'payload_sha256':SHA}}]
 if profile==LEGACY:
  r.update(profile_id=LEGACY,payload_sha256=LSHA,
    expected_profile={'legacy_identity_observation':True,'uninstall_executed':False,'absence_proved':False})
  s=r['operation_stages'][0];s.update(workflow_id=LEGACY,resource_key='agent-'+t['agent_id']+'-legacy-vnc-identity')
  s['verification'].update(profile_id=LEGACY,payload_sha256=LSHA)
 if profile==POST_LOG:
  r.update(profile_id=POST_LOG,baseline=deepcopy(LOG_BASELINE),expected_profile={
   'log_files_present':True,'logs_advanced_since_reviewed_baseline':True,
   'tray_desktop_verified':False,'log_contents_read':False,'file_writes':False})
  s=r['operation_stages'][0];s.update(workflow_id=POST_LOG,resource_key='agent-'+t['agent_id']+'-post-vnc-log-observation')
  s['verification'].update(profile_id=POST_LOG)
 if profile==MSI:
  from windows_legacy_msi import SHA as MSHA,PRODUCT,VERSION as MVERSION
  if name!='windows':raise ValueError('legacy_msi_windows_only')
  r.update(profile_id=MSI,payload_sha256=MSHA,supported_os='windows',action_profile='destructive',
   expected_profile={'product_code':PRODUCT,'version':MVERSION,'identity_verified':True,
    'uninstall_started':True,'msi_exit_code':0,'registry_absent':True,'legacy_service_absent':True,
    'legacy_process_absent':True,'reboot_required':False,'full_source_case_passed':False})
  s=r['operation_stages'][0];s.update(workflow_id=MSI,tool=REMOVE,
   resource_key='agent-'+t['agent_id']+'-legacy-msi-removal')
  s['verification'].update(profile_id=MSI,payload_sha256=MSHA)
 if profile==POST_MSI:
  from windows_legacy_msi import POST_SHA,PRODUCT
  if name!='windows':raise ValueError('legacy_absence_windows_only')
  r.update(profile_id=POST_MSI,payload_sha256=POST_SHA,supported_os='windows',expected_profile={
   'product_code':PRODUCT,'registry_absent':True,'legacy_service_absent':True,'legacy_process_absent':True,
   'uninstall_performed':False,'full_source_case_passed':False})
  s=r['operation_stages'][0];s.update(workflow_id=POST_MSI,resource_key='agent-'+t['agent_id']+'-legacy-msi-absence')
  s['verification'].update(profile_id=POST_MSI,payload_sha256=POST_SHA)
 if profile in {SESSIONS,DISKS,GPUS,SOFTWARE,OS_IDENTITY}:
  if profile==SESSIONS:from user_session_census import sha
  elif profile==GPUS:from gpu_os_baseline import sha
  elif profile==SOFTWARE:from software_os_baseline import sha
  elif profile==OS_IDENTITY:from os_identity_baseline import sha
  else:from drive_os_baseline import sha
  r.update(profile_id=profile,payload_sha256=sha(name),supported_os=name,expected_profile={
   'registered_session_query_only':True,'usernames_emitted':False,'desktop_verified':False,
   'login_or_unlock_performed':False,'consent_setting_changed':False,'business_pass':False})
  if profile==DISKS:r['expected_profile']={'os_disk_query_only':True,'plugin_result_compared':False,'disk_or_config_changed':False,'business_pass':False}
  if profile==GPUS:r['expected_profile']={'os_gpu_query_only':True,'plugin_result_compared':False,'all_gpu_completeness_verified':False,'settings_or_drivers_changed':False,'business_pass':False}
  if profile==SOFTWARE:r['expected_profile']={'os_software_query_only':True,'plugin_result_compared':False,'all_installed_software_completeness_verified':False,'software_tab_verified':False,'software_installed_removed_or_repaired':False,'business_pass':False}
  if profile==OS_IDENTITY:r['expected_profile']={'os_identity_query_only':True,'plugin_result_compared':False,'all_os_fields_verified':False,'users_or_volumes_verified':False,'os_ui_verified':False,'settings_changed':False,'full_case_passed':False,'business_pass':False}
  s=r['operation_stages'][0];s.update(workflow_id=profile,resource_key='agent-'+t['agent_id']+('-user-session-census' if profile==SESSIONS else '-drive-os-baseline'))
  s['verification'].update(profile_id=profile,payload_sha256=sha(name))
  if profile==GPUS:s['resource_key']='agent-'+t['agent_id']+'-gpu-os-baseline'
  if profile==SOFTWARE:s['resource_key']='agent-'+t['agent_id']+'-software-os-baseline'
  if profile==OS_IDENTITY:s['resource_key']='agent-'+t['agent_id']+'-os-identity-baseline'
 return r
def validate_context(job,cid,starting=False):
 if not isinstance(job,dict) or len(job.get('test_cases',[]))!=1:raise ValueError('single_endpoint_case_required')
 c=job['test_cases'][0];r=c.get('requirement') or {}
 if (c.get('case_id')!=cid or r!=requirement(r.get('target'),r.get('campaign_id'),r.get('profile_id'))
   or job.get('stand')!='lab' or job.get('status')!='running' or c.get('status')!='running'
   or job.get('job_type') not in {'manual','regression'} or job.get('resources')):
  raise ValueError('locked_endpoint_context_required')
 if not all(r[k] in job.get('request','') for k in ['ci_id','agent_id','ci_name','profile_id','core_version']):
  raise ValueError('original_endpoint_request_required')
 if starting and any(e['type']=='endpoint_metadata_started' for e in c.get('evidence',[])):
  raise ValueError('endpoint_no_runtime_replay')
 return c,r
def admit(job,cid,args):
 _,r=validate_context(job,cid)
 if args!={'target':r['target']}:raise ValueError('endpoint_exact_target_required')
 return deepcopy(r['operation_stages'][0])
def read_ready(session,name,jid,cid):
 try:
  _,r=validate_context(job_store.get_job(jid),cid)
  if name!=r['target']:raise ValueError('endpoint_target_scope')
  t,ci,urls=context(session,name);agent=read_json(session,urls[1]);validate_target_state(name,ci,agent)
  tasks=read_json(session,urls[0],{'name':'executeCommand','periodic':False,'limit':100,'offset':0})
  validate_task_list(name,tasks,'executeCommand')  # Includes Windows historical unresolved commands; never cancel them.
  if name!='astra' and not (name=='windows' and r['profile_id'] in {MSI,POST_MSI,SESSIONS,DISKS,GPUS,SOFTWARE,OS_IDENTITY}):raise ValueError('windows_metadata_payload_not_implemented')
  validate_preflight(name,ci,agent,read_json(session,urls[2]),tasks)
  return {'target':name,'ci_id':t['ci_id'],'agent_id':t['agent_id'],'core_version':CORE,
    'ready':True,'payload_sha256':r['payload_sha256'],'read_at':now(),'session_id':session.session_id,'mutation_executed':False}
 except Exception as e:
  return {'error':str(e)[:150] if isinstance(e,ValueError) else 'endpoint_readiness_unavailable','mutation_executed':False}
def summarize(body):
 if not isinstance(body,dict) or set(body)!={'probe_version','sample_interval_seconds','first','second','tray'}:
  raise ValueError('endpoint_json_shape')
 if body['probe_version']!=1 or body['sample_interval_seconds']!=5:raise ValueError('endpoint_probe_version')
 snapshots=[]
 for key in ['first','second']:
  s=body[key]
  if (not isinstance(s,dict) or set(s)!={'status','files','bounded'} or s['status'] not in
    {'unknown','ok','partial','missing','denied','error'} or type(s['bounded']) is not bool
    or not isinstance(s['files'],list) or len(s['files'])>1000):raise ValueError('endpoint_log_snapshot')
  found={}
  for x in s['files']:
   if (not isinstance(x,dict) or set(x)!={'id','size','mtime_ns'} or not isinstance(x['id'],str)
       or len(x['id'])!=64 or any(c not in '0123456789abcdef' for c in x['id']) or x['id'] in found
       or type(x['size']) is not int or x['size']<0 or type(x['mtime_ns']) is not int or x['mtime_ns']<0):
    raise ValueError('endpoint_file_metadata_invalid')
   found[x['id']]=x
  snapshots.append(found)
 tray=body['tray']
 if (not isinstance(tray,dict) or set(tray)!={'autostart_entry_present','declared_script_present','process_candidates','process_scan_complete'}
   or any(type(tray[k]) is not bool for k in ['autostart_entry_present','declared_script_present','process_scan_complete'])
   or type(tray['process_candidates']) is not int or not 0<=tray['process_candidates']<=10000):
  raise ValueError('endpoint_tray_metadata_invalid')
 complete=all(body[k]['status']=='ok' and body[k]['bounded'] for k in ['first','second'])
 changed=any(k in snapshots[0] and (x['size']>snapshots[0][k]['size'] or x['mtime_ns']>snapshots[0][k]['mtime_ns'])
             for k,x in snapshots[1].items())
 return {'log_observation_complete':complete,'log_files_present':bool(snapshots[1]) if complete else None,
   'log_file_count':len(snapshots[1]) if complete else None,'log_root_status':body['second']['status'],
   'write_between_samples':bool(changed) if complete else None,
   'logging_status':'PASS' if complete and snapshots[1] and changed else 'BLOCKED',
   'tray':tray,'tray_desktop_verified':False,'log_contents_read':False,'file_writes':False,
   'independent_os_oracle':False,'business_pass':False}
def summarize_post_logs(raw):
 summary=summarize(raw)
 latest=max((x['mtime_ns'] for x in raw['second']['files']),default=0)
 advanced=bool(summary['log_observation_complete'] and latest>LOG_BASELINE['latest_log_mtime_ns'])
 if latest>int(stamp(now()).timestamp()*1000000000)+300000000000:raise ValueError('log_mtime_in_future')
 summary.update(latest_log_mtime_ns=latest,logs_advanced_since_reviewed_baseline=advanced,
   baseline=deepcopy(LOG_BASELINE),logging_status='PASS' if summary['log_files_present'] and advanced else 'BLOCKED',
   verification_scope='log_metadata_advanced_since_owned_baseline_not_exact_event_or_rotation')
 return summary

def create(session,name,jid,cid):
 try:
  stage=admit(job_store.get_job(jid),cid,{'target':name});ops=list_operations(jid)
  if stage['workflow_id']==POST_LOG:validate_log_baseline()
  candidates=[o for o in ops if o['status']=='sending' and o['case_id']==cid
    and all(o.get(k)==stage[k] for k in ['workflow_id','stage_id','resource_key','tool'])
    and o['arguments_fingerprint']==_fingerprint(stage['arguments'])
    and o['verification_fingerprint']==_fingerprint(stage['verification'])]
  if len(candidates)!=1:raise ValueError('endpoint_unique_core_intent_required')
  if any(o['operation_id']!=candidates[0]['operation_id'] and o['status'] not in {'verified','not_sent'} for o in ops):
   raise ValueError('endpoint_prior_operation_unresolved')
  ready=read_ready(session,name,jid,cid)
  if ready.get('ready') is not True:raise ValueError(ready.get('error') or 'endpoint_not_ready')
  validate_release_source(job_store.get_job(RELEASE_JOB))
  for j in job_store.list_jobs(limit=None):
   if j['job_id']==jid:continue
   if any((c.get('requirement') or {}).get('type')=='closed_endpoint_metadata'
      and c['requirement'].get('target')==name for c in j.get('test_cases',[])):
    if any((c.get('requirement') or {}).get('profile_id')==stage['workflow_id'] for c in j.get('test_cases',[])) and any(o['status'] not in {'not_sent','rejected'} for o in list_operations(j['job_id'])):
     raise ValueError('endpoint_prior_attempt_no_rekey')
  t,_,urls=context(session,name);opid=candidates[0]['operation_id']
 except Exception as e:return refusal(str(e)[:150] if isinstance(e,ValueError) else 'endpoint_preflight_refused')
 try:
  _,r=validate_context(job_store.get_job(jid),cid)
  from legacy_vnc_identity import PROFILE as LEGACY,PAYLOAD as LPAYLOAD
  from windows_legacy_msi import PAYLOAD as MPAYLOAD,POST_PAYLOAD
  payload=POST_PAYLOAD if r['profile_id']==POST_MSI else MPAYLOAD if r['profile_id']==MSI else LPAYLOAD if r['profile_id']==LEGACY else PAYLOAD
  if r['profile_id']==SESSIONS:
   from user_session_census import payload as session_payload
   payload=session_payload(name)
  if r['profile_id']==DISKS:
   from drive_os_baseline import payload as disk_payload
   payload=disk_payload(name)
  if r['profile_id']==GPUS:
   from gpu_os_baseline import payload as gpu_payload
   payload=gpu_payload(name)
  if r['profile_id']==SOFTWARE:
   from software_os_baseline import payload as software_payload
   payload=software_payload(name)
  if r['profile_id']==OS_IDENTITY:
   from os_identity_baseline import payload as identity_payload
   payload=identity_payload(name)
  program=payload['additional_params']['programm']
  sent=now();response=session.context.request.post(urls[0],data=deepcopy(payload),timeout=15000);received=now()
  if response.status!=201:raise ValueError('endpoint_create_status')
  b=response.json();params=b.get('additional_params') or {}
  if (str(UUID(b.get('id')))!=b['id'] or b.get('agent_id')!=t['agent_id'] or b.get('name')!='executeCommand'
    or 'period' not in b or b['period'] is not None or 'ttl' not in b or b['ttl'] is not None
    or b.get('run_as_user')!='' or params.get('programm')!=program or params.get('arguments')!=payload['additional_params']['arguments']
    or set(params)-{'programm','arguments','command'} or params.get('command') is not None
    or not -120<=(stamp(received)-stamp(b['created_at'])).total_seconds()<=300):
   raise ValueError('endpoint_receipt_scope')
  own={'target':name,'ci_id':t['ci_id'],'agent_id':t['agent_id'],'profile_id':r['profile_id'],'payload_sha256':r['payload_sha256'],
    'job_id':jid,'case_id':cid,'task_id':b['id'],'task_name':'executeCommand','operation_id':opid,
    'session_id':session.session_id,'sent_at':sent,'received_at':received,'server_created_at':b['created_at'],
    'request_origin':ORIGIN}
  if not hasattr(session,'_owned_endpoint_metadata'):session._owned_endpoint_metadata={}
  session._owned_endpoint_metadata[(jid,cid)]=own
  return {**own,'create_status':201,'executed':True,'mutation_executed':True,'business_pass':False}
 except Exception:
  return {'error':'endpoint_dispatch_uncertain_no_resend','executed':False,'dispatch_may_have_occurred':True,'resend_authorized':False}
def rebind_owned_receipt(session,name,jid,cid):
 """Read-only continuation from persisted native receipt, never a new dispatch."""
 c,r=validate_context(job_store.get_job(jid),cid)
 if name!=r['target']:raise ValueError('endpoint_recovery_target')
 stage=r['operation_stages'][0];ops=list_operations(jid)
 if (len(ops)!=1 or ops[0]['status']!='awaiting_verification' or ops[0]['case_id']!=cid
   or any(ops[0].get(k)!=stage[k] for k in ['workflow_id','stage_id','tool','resource_key'])
   or ops[0]['arguments_fingerprint']!=_fingerprint(stage['arguments'])
   or ops[0]['verification_fingerprint']!=_fingerprint(stage['verification'])):
  raise ValueError('endpoint_recovery_exact_awaiting_intent_required')
 create_tool=stage['tool']
 creates=[e for e in c.get('evidence',[]) if e['type']==create_tool and e.get('source')=='uqa_tool'
   and e.get('execution_status') in {'executed','observed'}]
 if len(creates)!=1:raise ValueError('endpoint_recovery_native_receipt_required')
 ce=creates[0];env=json.loads(ce['value']);a=env['result'];op=ops[0]
 if (env.get('tool')!=create_tool or env.get('arguments')!={'target':name}
   or a.get('executed') is not True or a.get('mutation_executed') is not True or a.get('create_status')!=201
   or a.get('error') or not a.get('session_id') or str(UUID(a.get('task_id')))!=a['task_id']
   or any(a.get(k)!=v for k,v in {'job_id':jid,'case_id':cid,'target':name,'ci_id':r['ci_id'],
      'agent_id':r['agent_id'],'profile_id':r['profile_id'],'payload_sha256':r['payload_sha256'],
      'operation_id':op['operation_id'],'task_name':'executeCommand','request_origin':ORIGIN}.items())
   or stamp(ce['created_at'])<stamp(op['created_at'])):raise ValueError('endpoint_recovery_receipt_scope')
 t,ci,urls=context(session,name);validate_target_state(name,ci,read_json(session,urls[1]))
 if getattr(session,'_owned_endpoint_metadata',{}).get((jid,cid)):raise ValueError('endpoint_receipt_already_bound')
 if not hasattr(session,'_owned_endpoint_metadata'):session._owned_endpoint_metadata={}
 session._owned_endpoint_metadata[(jid,cid)]={**a,'session_id':session.session_id,
   'original_session_id':a['session_id'],'recovery_receipt_evidence_id':ce['evidence_id'],
   'recovery_receipt_sha256':hashlib.sha256(ce['value'].encode()).hexdigest()}
 return {'rebound':True,'task_id':a['task_id'],'receipt_evidence_id':ce['evidence_id'],
   'mutation_executed':False,'resend_authorized':False,'business_pass':False}

def read(session,name,jid,cid):
 try:
  _,r=validate_context(job_store.get_job(jid),cid);own=getattr(session,'_owned_endpoint_metadata',{}).get((jid,cid))
  if not own or name!=r['target'] or own['target']!=name or own['session_id']!=session.session_id:
   raise ValueError('own_endpoint_receipt_required')
  t,_,urls=context(session,name);b=read_json(session,urls[0]+'/'+own['task_id']+'/full');env=b.get('result')
  if not isinstance(env,dict):raise ValueError('own_endpoint_result_not_ready')
  if (b.get('id')!=own['task_id'] or b.get('agent_id')!=t['agent_id'] or b.get('name')!='executeCommand'
    or b.get('created_at')!=own['server_created_at'] or b.get('status')!='success' or env.get('machine_uid')!=t['ci_id']):
   raise ValueError('own_endpoint_identity_freshness')
  fresh=audit_result_is_fresh(own['sent_at'],own['received_at'],own['server_created_at'],b.get('created_at'),env.get('processed_at'))
  historical=not fresh and bool(own.get('recovery_receipt_evidence_id'))
  if not fresh and not historical:raise ValueError('own_endpoint_identity_freshness')
  data=env.get('data')
  if isinstance(data,dict) and isinstance(data.get('stdout'),str):
   if 'stderr' not in data:raise ValueError('endpoint_stderr_missing')
   stdout,code,stderr=data['stdout'],data.get('errorlevel'),data['stderr']
  else:stdout,code,stderr=env.get('result'),env.get('error_code'),env.get('error_msg')
  from powershell_streams import inspect_stderr
  streams=inspect_stderr(stderr) if r['profile_id'] in {MSI,POST_MSI,SESSIONS,DISKS,GPUS,SOFTWARE,OS_IDENTITY} else {'kind':'empty' if stderr in ('',None) else 'unrecognized','progress_records':0}
  if not isinstance(stdout,str) or len(stdout.encode())>262144 or code not in (0,'0') or streams['kind'] not in {'empty','progress_only'}:
   raise ValueError('endpoint_command_output_invalid')
  from legacy_vnc_identity import PROFILE as LEGACY,summarize as summarize_legacy
  from windows_legacy_msi import summarize as summarize_msi,summarize_absence
  if r['profile_id'] in {MSI,POST_MSI} and historical:raise ValueError('msi_current_postcondition_freshness_required')
  if r['profile_id'] in {SESSIONS,DISKS,GPUS,SOFTWARE,OS_IDENTITY}:
   if historical:raise ValueError('session_current_observation_freshness_required')
   if r['profile_id']==SESSIONS:from user_session_census import summarize as summarize_sessions
   elif r['profile_id']==GPUS:from gpu_os_baseline import summarize as summarize_sessions
   elif r['profile_id']==SOFTWARE:from software_os_baseline import summarize as summarize_sessions
   elif r['profile_id']==OS_IDENTITY:from os_identity_baseline import summarize as summarize_sessions
   else:from drive_os_baseline import summarize as summarize_sessions
   summary=summarize_sessions(json.loads(stdout.lstrip('\ufeff')),name)
  else:
   summary=(summarize_absence if r['profile_id']==POST_MSI else summarize_msi if r['profile_id']==MSI else summarize_legacy if r['profile_id']==LEGACY else summarize)(json.loads(stdout.lstrip('\ufeff')))
  if r['profile_id']==POST_LOG:
   validate_log_baseline();summary=summarize_post_logs(json.loads(stdout))
  if historical:
   summary={**summary,'historical_logging_status':summary.get('logging_status'),
     'logging_status':'BLOCKED','current_postcondition_verified':False,'historical_result_only':True}
  return {**own,'summary':summary,'native_stderr_kind':streams['kind'],'native_progress_records':streams['progress_records'],'result_sha256':hashlib.sha256(stdout.encode()).hexdigest(),
    'native_result_verified':bool(fresh),'historical_result_verified':bool(historical),'read_at':now(),'processed_at':env['processed_at'],
    'machine_uid':t['ci_id'],'task_status':'success','mutation_executed':False,'business_pass':False}
 except Exception as e:
  return {'error':str(e)[:160] if isinstance(e,ValueError) else 'endpoint_read_unavailable','mutation_executed':False}
def evaluate(job,op,eid,contract):
 try:
  c,r=validate_context(job,op['case_id']);stage=r['operation_stages'][0]
  if contract!=stage['verification'] or (op.get('receipt') or {}).get('acknowledged') is not True:raise ValueError('contract')
  def native(e,tool):
   if e.get('source')!='uqa_tool' or e.get('execution_status') not in {'observed','executed'}:raise ValueError('native')
   b=json.loads(e['value'])
   if b.get('tool')!=tool or b.get('arguments')!={'target':r['target']}:raise ValueError('scope')
   return b['result']
  ev=next(e for e in c['evidence'] if e['evidence_id']==eid);b=native(ev,READ)
  create_tool=stage['tool']
  creates=[(e,native(e,create_tool)) for e in c['evidence'] if e.get('type')==create_tool]
  creates=[x for x in creates if x[1].get('operation_id')==op['operation_id']]
  if len(creates)!=1:raise ValueError('unique')
  ce,a=creates[0]
  for k,v in {'target':r['target'],'ci_id':r['ci_id'],'agent_id':r['agent_id'],'job_id':job['job_id'],
    'case_id':op['case_id'],'operation_id':op['operation_id'],'profile_id':r['profile_id'],'payload_sha256':r['payload_sha256'],
    'request_origin':ORIGIN}.items():
   if a.get(k)!=v or b.get(k)!=v:raise ValueError('identity')
  if (a.get('executed') is not True or a.get('create_status')!=201 or a.get('error') or b.get('error')
    or not a.get('task_id') or b.get('task_id')!=a['task_id']
    or not a.get('session_id') or b.get('native_result_verified') is not True or b.get('machine_uid')!=r['ci_id']
    or b.get('task_status')!='success' or not isinstance(b.get('summary'),dict) or not b.get('result_sha256')
    or stamp(ce['created_at'])<stamp(op['created_at']) or stamp(ev['created_at'])<stamp(ce['created_at'])
    or not -5<=(stamp(now())-stamp(ev['created_at'])).total_seconds()<=300):
   raise ValueError('owned proof')
  if b.get('session_id')!=a['session_id']:
   if (not b.get('session_id') or b.get('original_session_id')!=a['session_id']
     or b.get('recovery_receipt_evidence_id')!=ce['evidence_id']
     or b.get('recovery_receipt_sha256')!=hashlib.sha256(ce['value'].encode()).hexdigest()):
    raise ValueError('native_recovery_receipt_link_required')
  return {'verified':True,'evidence_id':eid,'receipt_evidence_id':ce['evidence_id'],
    'identifier_value':a['task_id'],'postcondition_verified':True,'resend_authorized':False,
    'verification_scope':('closed_exact_msi_execution_not_full_source_regression' if r['profile_id']==MSI
      else 'closed_readonly_endpoint_metadata_execution_not_tray_desktop'),'business_pass':False}
 except (ValueError,TypeError,KeyError,AttributeError,StopIteration):
  return {'verified':False,'reason':'endpoint_metadata_evidence_insufficient','resend_authorized':False}
