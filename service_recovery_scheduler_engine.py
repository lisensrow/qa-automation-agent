"""New owned dry instance: native Scheduler engine anchor, not missing PID=proof.

Microsoft RunningTask EnginePID/InstanceGuid/Path read-only properties:
https://learn.microsoft.com/en-us/windows/win32/taskschd/runningtask
No service stop/restart or changes to old tasks/proofs/security.
"""
import base64,gzip,hashlib,json
from copy import deepcopy
from uuid import UUID
import service_recovery_dry_run as old
import service_recovery_dry_v4 as v4
import service_recovery_observer_v5 as v5
REGISTER='owned-windows-service-engine-dry-register-v1'
OBSERVE='owned-windows-service-engine-dry-observe-v1'
PROFILES={REGISTER,OBSERVE}
TASK_NAME='UQA-Regress-Service-Dry-v750'
ANCHOR=r'''$taskSchedule=New-Object -ComObject 'Schedule.Service'
 $taskSchedule.Connect()
 $taskRunning=@($taskSchedule.GetRunningTasks(0) | Where-Object {$_.Path -ceq '\UQA-Regress-Service-Dry-v750'})
 if($taskRunning.Count -ne 1){throw 'ancestry_unknown'}
 $taskProof.scheduler_engine_pid=[int]$taskRunning[0].EnginePID
 $taskProof.scheduler_instance=([Guid]([string]$taskRunning[0].InstanceGuid)).ToString('D')
 if($taskProof.scheduler_engine_pid -le 0 -or $taskProof.scheduler_engine_pid -eq $taskProof.service_pid -or $taskProof.scheduler_instance -eq [Guid]::Empty.ToString('D')){throw 'ancestry_unknown'}
 $taskProof.scheduler_instance_verified=$true
 $taskCursor=[int]$PID;$taskSeen=@();$taskReachedRoot=$false'''
def original(profile):
 if profile not in PROFILES:raise ValueError('scheduler_engine_profile')
 return v4.REGISTER if profile==REGISTER else v4.OBSERVE
def code(name,profile):
 text=v4.code(name,original(profile)).replace('v735','v750')
 text=text.replace("$taskProof=@{callback_complete=$false;","$taskProof=@{scheduler_engine_pid=0;scheduler_instance='';scheduler_instance_verified=$false;callback_complete=$false;")
 before='$taskCursor=[int]$PID;$taskSeen=@();$taskReachedRoot=$false'
 assert text.count(before)==1
 text=text.replace(before,ANCHOR).replace("if($taskCursor -eq 0){$taskReachedRoot=$true;break}","if($taskCursor -eq $taskProof.scheduler_engine_pid){$taskReachedRoot=$true;break}")
 # PID0/missing ancestor is never a success. Reach the native running-task engine.
 assert 'if($taskCursor -eq 0){$taskReachedRoot=$true' not in text
 label="[string]$taskDef.Principal.UserId -in @('SYSTEM','NT AUTHORITY\\SYSTEM','S-1-5-18')"
 function="function Exact-System($taskIdentity){try{return ((New-Object Security.Principal.NTAccount([string]$taskIdentity)).Translate([Security.Principal.SecurityIdentifier]).Value -ceq 'S-1-5-18')}catch{return ([string]$taskIdentity -ceq 'S-1-5-18')}}\n"
 text=text.replace('function Exact-Task',function+'function Exact-Task').replace(label,'(Exact-System $taskDef.Principal.UserId)')
 if profile==OBSERVE:
  text=text.replace('$taskOut.data=@{callback_complete=',"$taskOut.data=@{scheduler_engine_pid=$taskData.scheduler_engine_pid;scheduler_instance=$taskData.scheduler_instance;scheduler_instance_verified=$taskData.scheduler_instance_verified;callback_complete=")
 return '# independent native Scheduler engine dry proof v750\n'+text
def sha(name,profile):return hashlib.sha256(code(name,profile).encode()).hexdigest()
def wrapper(name,profile):
 packed=base64.b64encode(gzip.compress(code(name,profile).encode(),mtime=0)).decode()
 return "$ErrorActionPreference='Stop';$m=[IO.MemoryStream][Convert]::FromBase64String('"+packed+"');$g=New-Object IO.Compression.GZipStream($m,[IO.Compression.CompressionMode]::Decompress);$r=New-Object IO.StreamReader($g);$s=$r.ReadToEnd();$r.Dispose();([ScriptBlock]::Create($s)).Invoke()"
def payload(name,profile):
 text=wrapper(name,profile)
 if len(text)>7800 or any(x in text for x in ('"','\n','\r','%','!','&','|','<','>')):raise ValueError('scheduler_engine_transport')
 return {'name':'executeCommand','period':None,'ttl':None,'run_as_user':'','additional_params':{'programm':r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe','arguments':['-NoLogo','-NoProfile','-NonInteractive','-Command',text]}}
def summarize(obj,name,profile):
 original(profile);code(name,profile)
 if profile==REGISTER:return old.summarize(obj,name,old.REGISTER)
 normalized=deepcopy(obj);extra=None
 if isinstance(obj,dict) and obj.get('query_complete') is True:
  d=normalized.get('data',{});keys={'scheduler_engine_pid','scheduler_instance','scheduler_instance_verified'}
  if not keys<=set(d):raise ValueError('scheduler_instance_proof_missing')
  extra={k:d.pop(k) for k in keys}
  if type(extra['scheduler_engine_pid']) is not int or not 0<=extra['scheduler_engine_pid']<2**31 or type(extra['scheduler_instance_verified']) is not bool:raise ValueError('scheduler_instance_types')
  if extra['scheduler_instance_verified']:
   uid=UUID(extra['scheduler_instance'])
   if str(uid)!=extra['scheduler_instance'] or uid.int==0 or extra['scheduler_engine_pid']==d.get('service_pid') or extra['scheduler_engine_pid']==0:raise ValueError('scheduler_instance_identity')
  elif d.get('outside_agent_tree') is True or d.get('callback_complete') is True:raise ValueError('scheduler_engine_unverified_success')
 result=v5.summarize(normalized,name,v5.PROFILE)
 result['scheduler_instance_verified']=bool(extra and extra['scheduler_instance_verified'])
 result['independent_callback_execution_verified'] &= result['scheduler_instance_verified']
 return result
def require_own_registration(name):
 import job_store as s,endpoint_metadata as ep
 from operation_journal import list_operations,_fingerprint
 from plugin_preparation import stamp,now
 found=[]
 for j in s.list_jobs(limit=None):
  for c in j.get('test_cases',[]):
   r=c.get('requirement') or {}
   if r.get('profile_id')!=REGISTER or r.get('target')!=name:continue
   assert r==ep.requirement(name,r['campaign_id'],REGISTER) and j.get('stand')=='lab' and not j.get('resources') and len(j['test_cases'])==1
   ops=list_operations(j['job_id']);assert len(ops)==1 and ops[0]['status']=='verified'
   assert ops[0]['case_id']==c['case_id'] and ops[0]['tool']==ep.CREATE and ops[0]['verification_fingerprint']==_fingerprint(r['operation_stages'][0]['verification'])
   e=next(e for e in c['evidence'] if e['evidence_id']==ops[0]['verification']['evidence_id'])
   b=json.loads(e['value']);v=b['result']
   assert b['tool']==ep.READ and e['source']=='uqa_tool' and v['native_result_verified'] is True
   assert v['profile_id']==REGISTER and v['payload_sha256']==sha(name,REGISTER) and v['summary']['dry_registration_verified'] is True
   assert v['agent_id']==r['agent_id'] and v['ci_id']==r['ci_id'] and v['target']==name and 0<=(stamp(now())-stamp(v['read_at'])).total_seconds()<=900
   found.append((j['job_id'],c['case_id'],e['evidence_id']))
 if len(found)!=1:raise ValueError('one_own_engine_registration_required')
 return found[0]
