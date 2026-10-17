"""Read exact campaign Scheduler definition after its own registered-task receipt."""
import base64,hashlib,json
PROFILE='owned-windows-service-dry-definition-diagnostic-v1'
PROFILES={PROFILE};REGISTER=None;OBSERVE=PROFILE
CODE=r'''$ErrorActionPreference='Stop'
$t=Get-ScheduledTask -TaskName 'UQA-Regress-Service-Dry-v735' -TaskPath '\'
$a=@($t.Actions)
$sid=try{(New-Object Security.Principal.NTAccount([string]$t.Principal.UserId)).Translate([Security.Principal.SecurityIdentifier]).Value}catch{''}
$d=@{task_name=[string]$t.TaskName;task_path=[string]$t.TaskPath;action_count=$a.Count;trigger_count=@($t.Triggers).Count;principal_user=[string]$t.Principal.UserId;principal_sid=$sid;logon_type=[string]$t.Principal.LogonType;run_level=[string]$t.Principal.RunLevel;executable=[string]$a[0].Execute;argument_sha256=[BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes([string]$a[0].Arguments))).Replace('-','').ToLower()}
$d | ConvertTo-Json -Compress
'''
def code(name,profile):
 if name!='windows' or profile!=PROFILE:raise ValueError('owned_definition_windows_only')
 return CODE
def sha(name,profile):return hashlib.sha256(code(name,profile).encode()).hexdigest()
def payload(name,profile):return {'name':'executeCommand','period':None,'ttl':None,'run_as_user':'','additional_params':{'programm':r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe','arguments':['-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(code(name,profile).encode('utf-16-le')).decode()]}}
def require_own_registration(name):
 import job_store as s,endpoint_metadata as ep,service_recovery_dry_v4 as v4
 from operation_journal import list_operations
 j=s.get_job('20261017-191807-5bc5f38d');c=j['test_cases'][0];r=c['requirement']
 assert name=='windows' and r==ep.requirement(name,r['campaign_id'],v4.REGISTER)
 ops=list_operations(j['job_id']);assert len(ops)==1 and ops[0]['status']=='verified'
 e=next(e for e in c['evidence'] if e['evidence_id']==ops[0]['verification']['evidence_id'])
 b=json.loads(e['value']);assert b['tool']==ep.READ and b['result']['native_result_verified'] is True
 summary=b['result']['summary'];assert summary['phase']=='register' and summary['query_complete'] is True
 return j['job_id'],c['case_id'],e['evidence_id']
def summarize(obj,name,profile):
 code(name,profile)
 keys={'task_name','task_path','action_count','trigger_count','principal_user','principal_sid','logon_type','run_level','executable','argument_sha256'}
 if not isinstance(obj,dict) or set(obj)!=keys:raise ValueError('definition_diagnostic_shape')
 if obj['task_name']!='UQA-Regress-Service-Dry-v735' or obj['task_path']!='\\':raise ValueError('definition_diagnostic_identity')
 for k in keys-{'action_count','trigger_count'}:
  if not isinstance(obj[k],str) or len(obj[k])>240:raise ValueError('definition_diagnostic_budget')
 for k in ('action_count','trigger_count'):
  if type(obj[k]) is not int or not 0<=obj[k]<=10:raise ValueError('definition_diagnostic_count')
 return {**obj,'diagnostic_complete':True,'independent_callback_execution_verified':False,'actual_stopped_agent_recovery_verified':False,'full_case_passed':False}
