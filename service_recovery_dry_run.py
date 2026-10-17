"""Owned one-off Windows recovery rehearsal. Never stops/restarts the agent.

Existing SYSTEM identity only; no credentials, ACL/elevation or service settings.
The new scheduled action only Start-Service on an already-running exact service.
Artifacts/tasks are retained; registration is never forced or replayed.
"""
import base64,hashlib,json
from datetime import datetime
REGISTER='owned-windows-service-recovery-dry-register-v1'
OBSERVE='owned-windows-service-recovery-dry-observe-v1'
PROFILES={REGISTER,OBSERVE}
FAILURES={'existing_system_required','exact_running_service_required','service_product_identity','scheduler_not_running','owned_task_exists','owned_fixture_exists','reparse','task_changed','callback_not_verified','artifact_budget','artifact_owner','native_query_failed'}
TASK_NAME='UQA-Regress-Service-Dry-v735'
ROOT=r'C:\Windows\System32\config\systemprofile\AppData\Local\UQARegression\service-dry-v735'
CALLBACK=r'''$ErrorActionPreference='Stop'
$taskProof=@{callback_complete=$false;identity_system=$false;outside_agent_tree=$false;service_running_after=$false;callback_pid=[int]$PID;service_pid=0;started_at=[DateTime]::UtcNow.ToString('o');finished_at='';error='';failure_reason=''}
try {
 $taskProof.identity_system=([Security.Principal.WindowsIdentity]::GetCurrent().User.Value -eq 'S-1-5-18')
 if(-not $taskProof.identity_system){throw 'identity'}
 $taskSvc=@(Get-CimInstance Win32_Service -Filter "Name='USystemAgentSystem'")
 if($taskSvc.Count -ne 1 -or $taskSvc[0].State -ne 'Running'){throw 'not_running_before_dry'}
 $taskProof.service_pid=[int]$taskSvc[0].ProcessId
 $taskCursor=[int]$PID;$taskSeen=@();$taskReachedRoot=$false
 for($taskN=0;$taskN -lt 20;$taskN++){
  if($taskCursor -eq 0){$taskReachedRoot=$true;break}
  if($taskCursor -eq $taskProof.service_pid -or $taskCursor -in $taskSeen){throw 'inside_agent_or_cycle'}
  $taskSeen+=@($taskCursor)
  $taskProc=@(Get-CimInstance Win32_Process -Filter "ProcessId=$taskCursor")
  if($taskProc.Count -ne 1){throw 'ancestry_unknown'}
  $taskCursor=[int]$taskProc[0].ParentProcessId
 }
 if(-not $taskReachedRoot){throw 'ancestry_budget'}
 $taskProof.outside_agent_tree=$true
 Start-Service -Name 'USystemAgentSystem' -ErrorAction Stop
 $taskProof.service_running_after=((Get-Service -Name 'USystemAgentSystem').Status -eq 'Running')
 $taskProof.callback_complete=$taskProof.service_running_after
}catch{
 $taskProof.error='dry_start_or_independence_unverified'
 $taskKnown=@('identity','not_running_before_dry','inside_agent_or_cycle','ancestry_unknown','ancestry_budget')
 $taskProof.failure_reason=if($_.Exception.Message -cin $taskKnown){$_.Exception.Message}else{'native_start_or_query_failed'}
}
$taskProof.finished_at=[DateTime]::UtcNow.ToString('o')
$taskBytes=[Text.Encoding]::UTF8.GetBytes(($taskProof | ConvertTo-Json -Depth 4 -Compress))
$taskFile=[IO.File]::Open('C:\Windows\System32\config\systemprofile\AppData\Local\UQARegression\service-dry-v735\proof.json',[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
try{$taskFile.Write($taskBytes,0,$taskBytes.Length)}finally{$taskFile.Dispose()}
if($taskProof.error){exit 1}
'''
ENCODED=base64.b64encode(CALLBACK.encode('utf-16-le')).decode()
COMMON=r'''$ErrorActionPreference='Stop'
$taskName='UQA-Regress-Service-Dry-v735'
$taskRoot='C:\Windows\System32\config\systemprofile\AppData\Local\UQARegression\service-dry-v735'
$taskFilePath=Join-Path $taskRoot 'proof.json'
$taskProgram='C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
$taskArgs='-NoLogo -NoProfile -NonInteractive -EncodedCommand __ENCODED__'
function Assert-PlainPath($taskPath){
 $taskNode=Get-Item -LiteralPath $taskPath -Force
 while($null -ne $taskNode){
  if(($taskNode.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'reparse'}
  $taskNode=$taskNode.Parent
 }
}
function Exact-Task($taskDef){
 return ($taskDef.TaskName -eq $taskName -and $taskDef.TaskPath -eq '\' -and
  @($taskDef.Actions).Count -eq 1 -and $taskDef.Actions[0].Execute -ieq $taskProgram -and
  $taskDef.Actions[0].Arguments -ceq $taskArgs -and @($taskDef.Triggers).Count -eq 1 -and
  [string]$taskDef.Principal.UserId -in @('SYSTEM','NT AUTHORITY\SYSTEM','S-1-5-18') -and
  [string]$taskDef.Principal.LogonType -eq 'ServiceAccount' -and [string]$taskDef.Principal.RunLevel -eq 'Limited')
}
$taskOut=@{probe_version=1;platform='windows';phase='__PHASE__';query_complete=$false;error='';failure_reason='';data=@{}}
try {
 if([Security.Principal.WindowsIdentity]::GetCurrent().User.Value -ne 'S-1-5-18'){throw 'existing_system_required'}
 $taskService=@(Get-CimInstance Win32_Service -Filter "Name='USystemAgentSystem'")
 if($taskService.Count -ne 1 -or $taskService[0].State -ne 'Running' -or [int]$taskService[0].ProcessId -le 0){throw 'exact_running_service_required'}
 if([string]$taskService[0].PathName -notmatch '^"?C:\\Program Files(?: \(x86\))?\\USystem\\agentServer\\bin\\usAgent\.exe"?(?:\s|$)'){throw 'service_product_identity'}
 if((Get-Service -Name 'Schedule').Status -ne 'Running'){throw 'scheduler_not_running'}
 __BODY__
}catch{
 $taskOut.data=@{};$taskOut.error='recovery_prerequisite_unverified'
 $taskKnown=@('existing_system_required','exact_running_service_required','service_product_identity','scheduler_not_running','owned_task_exists','owned_fixture_exists','reparse','task_changed','callback_not_verified','artifact_budget','artifact_owner')
 $taskOut.failure_reason=if($_.Exception.Message -cin $taskKnown){$_.Exception.Message}else{'native_query_failed'}
}
$taskOut | ConvertTo-Json -Depth 6 -Compress
'''
REGISTER_BODY=r'''if(@(Get-ScheduledTask -TaskName $taskName -TaskPath '\' -ErrorAction SilentlyContinue).Count -ne 0){throw 'owned_task_exists'}
 if(Test-Path -LiteralPath $taskRoot){throw 'owned_fixture_exists'}
 $taskBase=Split-Path $taskRoot -Parent
 $taskParent=Split-Path $taskBase -Parent
 Assert-PlainPath $taskParent
 if(-not (Test-Path -LiteralPath $taskBase)){[void][IO.Directory]::CreateDirectory($taskBase)}
 Assert-PlainPath $taskBase
 [void][IO.Directory]::CreateDirectory($taskRoot)
 Assert-PlainPath $taskRoot
 $taskAction=New-ScheduledTaskAction -Execute $taskProgram -Argument $taskArgs
 $taskTrigger=New-ScheduledTaskTrigger -Once -At ((Get-Date).AddSeconds(20))
 $taskPrincipal=New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Limited
 $taskSettings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Seconds 45) -MultipleInstances IgnoreNew -StartWhenAvailable
 $taskDefinition=New-ScheduledTask -Action $taskAction -Trigger $taskTrigger -Principal $taskPrincipal -Settings $taskSettings
 [void](Register-ScheduledTask -TaskName $taskName -TaskPath '\' -InputObject $taskDefinition)
 $taskSaved=Get-ScheduledTask -TaskName $taskName -TaskPath '\'
 $taskOut.data=@{new_owned_task_registered=$true;exact_task_definition=[bool](Exact-Task $taskSaved);existing_system_identity=$true;service_already_running=$true;stop_or_restart_executed=$false}
 $taskOut.query_complete=$true'''
OBSERVE_BODY=r'''Assert-PlainPath $taskRoot
 $taskSaved=Get-ScheduledTask -TaskName $taskName -TaskPath '\'
 if(-not (Exact-Task $taskSaved)){throw 'task_changed'}
 $taskReady=$false
 for($taskN=0;$taskN -lt 35;$taskN++){
  $taskInfo=Get-ScheduledTaskInfo -TaskName $taskName -TaskPath '\'
  $taskState=(Get-ScheduledTask -TaskName $taskName -TaskPath '\').State
  if((Test-Path -LiteralPath $taskFilePath) -and $taskState -ne 'Running' -and $taskInfo.LastTaskResult -ne 267009){$taskReady=$true;break}
  Start-Sleep -Seconds 1
 }
 if(-not $taskReady){throw 'callback_not_verified'}
 $taskMeta=Get-Item -LiteralPath $taskFilePath -Force
 if($taskMeta.PSIsContainer -or $taskMeta.Length -gt 4096){throw 'artifact_budget'}
 Assert-PlainPath $taskFilePath
 if((Get-Acl -LiteralPath $taskFilePath).GetOwner([Security.Principal.SecurityIdentifier]).Value -ne 'S-1-5-18'){throw 'artifact_owner'}
 $taskData=([IO.File]::ReadAllText($taskFilePath) | ConvertFrom-Json)
 $taskOut.data=@{callback_complete=$taskData.callback_complete;identity_system=$taskData.identity_system;outside_agent_tree=$taskData.outside_agent_tree;service_running_after=$taskData.service_running_after;callback_pid=$taskData.callback_pid;service_pid=$taskData.service_pid;started_at=$taskData.started_at;finished_at=$taskData.finished_at;callback_error=$taskData.error;callback_failure_reason=$taskData.failure_reason;exact_task_definition=$true;last_task_result_zero=[bool]($taskInfo.LastTaskResult -eq 0);stop_or_restart_executed=$false}
 $taskOut.query_complete=$true'''

def code(name,profile):
 if name!='windows' or profile not in PROFILES:raise ValueError('windows_recovery_dry_scope')
 return COMMON.replace('__ENCODED__',ENCODED).replace('__PHASE__','register' if profile==REGISTER else 'observe').replace('__BODY__',REGISTER_BODY if profile==REGISTER else OBSERVE_BODY)

def sha(name,profile):return hashlib.sha256(code(name,profile).encode()).hexdigest()

def payload(name,profile):
 text=code(name,profile)
 return {'name':'executeCommand','period':None,'ttl':None,'run_as_user':'','additional_params':{
  'programm':r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe','arguments':['-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(text.encode('utf-16-le')).decode()]}}

def require_own_registration(name):
 """Never adopt a pre-existing task/proof file as this campaign's rehearsal."""
 import job_store as store,endpoint_metadata as ep
 from operation_journal import list_operations,_fingerprint
 from plugin_preparation import stamp,now
 found=[]
 for job in store.list_jobs(limit=None):
  for case in job.get('test_cases',[]):
   r=case.get('requirement') or {}
   if r.get('profile_id')!=REGISTER or r.get('target')!=name:continue
   if r!=ep.requirement(name,r.get('campaign_id'),REGISTER) or job.get('stand')!='lab' or job.get('resources'):raise ValueError('recovery_registration_context')
   ops=list_operations(job['job_id'])
   if len(ops)!=1 or ops[0]['status']!='verified':raise ValueError('recovery_registration_not_verified')
   op=ops[0];stage=r['operation_stages'][0]
   if op['case_id']!=case['case_id'] or op['tool']!=ep.CREATE or op['verification_fingerprint']!=_fingerprint(stage['verification']):raise ValueError('recovery_registration_contract')
   eid=(op.get('verification') or {}).get('evidence_id')
   e=next((e for e in case.get('evidence',[]) if e.get('evidence_id')==eid),None)
   if not e or e.get('source')!='uqa_tool' or e.get('type')!=ep.READ:raise ValueError('recovery_registration_own_read')
   b=json.loads(e['value']);v=b.get('result') or {}
   if (b.get('tool')!=ep.READ or v.get('native_result_verified') is not True
    or v.get('target')!=name or v.get('agent_id')!=r['agent_id'] or v.get('ci_id')!=r['ci_id']
    or v.get('profile_id')!=REGISTER or v.get('payload_sha256')!=r['payload_sha256']
    or (v.get('summary') or {}).get('dry_registration_verified') is not True
    or not 0<=(stamp(now())-stamp(v['read_at'])).total_seconds()<=900):raise ValueError('recovery_registration_proof')
   found.append((job['job_id'],case['case_id'],eid))
 if len(found)!=1:raise ValueError('one_own_recovery_registration_required')
 return found[0]

def summarize(obj,name,profile):
 code(name,profile);phase='register' if profile==REGISTER else 'observe'
 if not isinstance(obj,dict) or set(obj)!={'probe_version','platform','phase','query_complete','error','failure_reason','data'}:raise ValueError('recovery_shape')
 if type(obj['probe_version']) is not int or obj['probe_version']!=1 or obj['platform']!=name or obj['phase']!=phase or type(obj['query_complete']) is not bool:raise ValueError('recovery_scope')
 if obj['error'] not in {'','recovery_prerequisite_unverified'} or not isinstance(obj['data'],dict) or obj['query_complete']!=(obj['error']==''):raise ValueError('recovery_status')
 result={'phase':phase,'query_complete':obj['query_complete'],'dry_registration_verified':False,'independent_callback_execution_verified':False,'agent_stopped':False,'actual_stopped_agent_recovery_verified':False,'full_case_passed':False}
 if obj['failure_reason'] not in FAILURES|{''} or obj['query_complete']!=(obj['failure_reason']==''):raise ValueError('recovery_failure_reason')
 result['failure_reason']=obj['failure_reason']
 d=obj['data']
 if not obj['query_complete']:
  if d:raise ValueError('recovery_failed_data')
  return result
 if profile==REGISTER:
  if set(d)!={'new_owned_task_registered','exact_task_definition','existing_system_identity','service_already_running','stop_or_restart_executed'} or any(type(v) is not bool for v in d.values()):raise ValueError('recovery_register_data')
  if d['stop_or_restart_executed']:raise ValueError('dry_run_must_not_stop')
  result['dry_registration_verified']=all(d[k] for k in d if k!='stop_or_restart_executed')
 else:
  flags={'callback_complete','identity_system','outside_agent_tree','service_running_after','exact_task_definition','last_task_result_zero','stop_or_restart_executed'}
  if set(d)!=flags|{'callback_pid','service_pid','started_at','finished_at','callback_error','callback_failure_reason'} or any(type(d[k]) is not bool for k in flags):raise ValueError('recovery_observe_data')
  if d['stop_or_restart_executed'] or d['callback_error'] not in {'','dry_start_or_independence_unverified'}:raise ValueError('recovery_callback_scope')
  if d['callback_failure_reason'] not in {'','identity','not_running_before_dry','inside_agent_or_cycle','ancestry_unknown','ancestry_budget','native_start_or_query_failed'} or bool(d['callback_error'])!=bool(d['callback_failure_reason']):raise ValueError('recovery_callback_failure')
  result['callback_failure_reason']=d['callback_failure_reason']
  for k in ('callback_pid','service_pid'):
   if type(d[k]) is not int or not 0<d[k]<2**31:raise ValueError('recovery_pid')
  if d['callback_pid']==d['service_pid']:raise ValueError('recovery_independence')
  a=datetime.fromisoformat(d['started_at'].replace('Z','+00:00'));b=datetime.fromisoformat(d['finished_at'].replace('Z','+00:00'))
  if not a.tzinfo or not b.tzinfo or not 0<=(b-a).total_seconds()<=60:raise ValueError('recovery_time')
  result['independent_callback_execution_verified']=all(d[k] for k in flags if k!='stop_or_restart_executed') and not d['callback_error']
 return result
