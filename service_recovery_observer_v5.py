"""Own V4 continuation: localized SYSTEM name must resolve to exact SYSTEM SID."""
import base64,gzip,hashlib,json,re
from copy import deepcopy
from datetime import datetime
import service_recovery_dry_run as old
import service_recovery_dry_v4 as v4
PROFILE='owned-windows-service-recovery-dry-observe-v5'
OBSERVE=PROFILE;REGISTER=None;PROFILES={PROFILE}
ARGUMENT_SHA=hashlib.sha256(('-NoLogo -NoProfile -NonInteractive -EncodedCommand '+base64.b64encode(old.CALLBACK.removesuffix('\n').encode('utf-16-le')).decode()).encode()).hexdigest()
def code(name,profile):
 if name!='windows' or profile!=PROFILE:raise ValueError('owned_observer_scope')
 text=v4.code(name,v4.OBSERVE)
 before="[string]$taskDef.Principal.UserId -in @('SYSTEM','NT AUTHORITY\\SYSTEM','S-1-5-18')"
 assert text.count(before)==1
 function="function Exact-System($taskIdentity){try{return ((New-Object Security.Principal.NTAccount([string]$taskIdentity)).Translate([Security.Principal.SecurityIdentifier]).Value -ceq 'S-1-5-18')}catch{return ([string]$taskIdentity -ceq 'S-1-5-18')}}\n"
 return '# own localized SID observer v5\n'+text.replace('function Exact-Task',function+'function Exact-Task').replace(before,'(Exact-System $taskDef.Principal.UserId)')
def sha(name,profile):return hashlib.sha256(code(name,profile).encode()).hexdigest()
def wrapper(name,profile):
 packed=base64.b64encode(gzip.compress(code(name,profile).encode(),mtime=0)).decode()
 return "$ErrorActionPreference='Stop';$m=[IO.MemoryStream][Convert]::FromBase64String('"+packed+"');$g=New-Object IO.Compression.GZipStream($m,[IO.Compression.CompressionMode]::Decompress);$r=New-Object IO.StreamReader($g);$s=$r.ReadToEnd();$r.Dispose();([ScriptBlock]::Create($s)).Invoke()"
def payload(name,profile):
 text=wrapper(name,profile)
 if len(text)>7800 or any(x in text for x in ('"','\n','\r','%','!','&','|','<','>')):raise ValueError('observer_transport')
 return {'name':'executeCommand','period':None,'ttl':None,'run_as_user':'','additional_params':{'programm':r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe','arguments':['-NoLogo','-NoProfile','-NonInteractive','-Command',text]}}
def require_own_registration(name):
 import job_store as s,service_recovery_diagnostic as diagnostic
 from operation_journal import list_operations
 from plugin_preparation import now,stamp
 antecedent=diagnostic.require_own_registration(name)
 j=s.get_job('20261017-192147-f73f7589');c=j['test_cases'][0];ops=list_operations(j['job_id'])
 assert len(ops)==1 and ops[0]['status']=='verified'
 e=next(e for e in c['evidence'] if e['evidence_id']==ops[0]['verification']['evidence_id'])
 b=json.loads(e['value']);r=b['result'];d=r['summary']
 assert e['source']=='uqa_tool' and r['native_result_verified'] is True and r['profile_id']==diagnostic.PROFILE
 assert 0<=(stamp(now())-stamp(r['read_at'])).total_seconds()<=900
 assert d['task_name']==old.TASK_NAME and d['task_path']=='\\' and d['action_count']==d['trigger_count']==1
 assert d['principal_sid']=='S-1-5-18' and d['logon_type']=='ServiceAccount' and d['run_level']=='Limited'
 assert d['executable'].casefold()==r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'.casefold()
 assert d['argument_sha256']==ARGUMENT_SHA
 return antecedent
def summarize(obj,name,profile):
 code(name,profile)
 # .NET roundtrip timestamps carry seven fractional digits; Python3.10 accepts6.
 # Enforce the ORIGINAL <=60s bound in exact 100ns ticks before structural check.
 normalized=deepcopy(obj)
 if isinstance(obj,dict) and obj.get('query_complete') is True:
  ticks=[]
  for key in ('started_at','finished_at'):
   value=obj.get('data',{}).get(key)
   m=re.fullmatch(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,7}))?(Z|[+-]\d{2}:\d{2})',value) if isinstance(value,str) else None
   if not m:raise ValueError('recovery_dotnet_timestamp')
   seconds=datetime.fromisoformat(m[1]+m[3].replace('Z','+00:00'))
   fraction=(m[2] or '').ljust(7,'0')
   ticks.append(int(seconds.timestamp())*10**7+int(fraction))
   normalized['data'][key]=m[1]+'.'+fraction[:6]+m[3].replace('Z','+00:00')
  if not 0<=ticks[1]-ticks[0]<=60*10**7:raise ValueError('recovery_time')
 return old.summarize(normalized,name,old.OBSERVE)
