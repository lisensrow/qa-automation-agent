"""Fixed local session queries, never login/unlock/start/change a session.

Only hashed session refs and candidate flags leave the endpoint. WTS/logind
registered sessions are a prerequisite observation, NOT desktop/Tray proof.
PowerShell Add-Type may use normal compiler temporary files; no explicit file
or registry writes, log reads, credentials or permission changes are requested.
"""
import base64,hashlib,re
PROFILE='owned-user-session-census-v1'
WINDOWS=r'''$ErrorActionPreference='Stop'
$o=[ordered]@{probe_version=1;platform='windows';query_complete=$false;sessions=@();error=''}
$p=[IntPtr]::Zero
try {
 Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
[StructLayout(LayoutKind.Sequential)]
public struct UqaWtsInfo { public int Id; public IntPtr Name; public int State; }
public static class UqaWts {
 [DllImport("wtsapi32.dll", EntryPoint="WTSEnumerateSessionsW", SetLastError=true)]
 public static extern bool Enumerate(IntPtr server,int reserved,int version,out IntPtr info,out int count);
 [DllImport("wtsapi32.dll", EntryPoint="WTSQuerySessionInformationW", SetLastError=true)]
 public static extern bool Query(IntPtr server,int id,int infoClass,out IntPtr buffer,out int bytes);
 [DllImport("wtsapi32.dll", EntryPoint="WTSFreeMemory")]
 public static extern void Free(IntPtr memory);
}
'@
 $count=0
 if(-not [UqaWts]::Enumerate([IntPtr]::Zero,0,1,[ref]$p,[ref]$count)){throw 'enumeration_failed'}
 if($count -lt 0 -or $count -gt 64){throw 'session_budget'}
 $size=[Runtime.InteropServices.Marshal]::SizeOf([type][UqaWtsInfo])
 $rows=@();$complete=$true
 for($i=0;$i -lt $count;$i++){
  $s=[Runtime.InteropServices.Marshal]::PtrToStructure([IntPtr]::Add($p,$i*$size),[type][UqaWtsInfo])
  if($s.Id -lt 0 -or $s.State -lt 0 -or $s.State -gt 9){throw 'session_shape'}
  $u=[IntPtr]::Zero;$bytes=0;$present=$false
  try {
   if($s.Id -gt 0){
    if([UqaWts]::Query([IntPtr]::Zero,$s.Id,5,[ref]$u,[ref]$bytes) -and $bytes -ge 2 -and $bytes -le 4096){
     $present=-not [string]::IsNullOrWhiteSpace([Runtime.InteropServices.Marshal]::PtrToStringUni($u))
    }else{$complete=$false}
   }
  } finally {if($u -ne [IntPtr]::Zero){[UqaWts]::Free($u)}}
  $h=[Security.Cryptography.SHA256]::Create()
  try{$ref=([BitConverter]::ToString($h.ComputeHash([Text.Encoding]::UTF8.GetBytes([string]$s.Id)))).Replace('-','').ToLowerInvariant()}finally{$h.Dispose()}
  $rows+=@{session_ref=$ref;kind='wts';candidate=($s.Id -gt 0 -and $s.State -eq 0 -and $present)}
 }
 $o.sessions=@($rows);$o.query_complete=$complete
 if(-not $complete){$o.error='session_query_incomplete'}
}catch{$o.error='native_session_query_failed'}finally{if($p -ne [IntPtr]::Zero){[UqaWts]::Free($p)}}
$o | ConvertTo-Json -Depth 5 -Compress
'''
ASTRA=r'''import subprocess,json,hashlib,time,re
out={'probe_version':1,'platform':'astra','query_complete':False,'sessions':[],'error':''}
try:
 deadline=time.monotonic()+20
 def run(args):
  remaining=deadline-time.monotonic()
  if remaining<=0:raise ValueError('time_budget')
  p=subprocess.run(['/usr/bin/loginctl',*args],capture_output=True,text=True,timeout=min(3,remaining))
  if p.returncode!=0 or len(p.stdout.encode())>65536:raise ValueError('query_failed')
  return p.stdout
 lines=run(['list-sessions','--no-legend','--no-pager']).splitlines()
 ids=[line.split()[0] for line in lines if line.strip()]
 if len(ids)>64 or len(set(ids))!=len(ids) or any(not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}',x) for x in ids):raise ValueError('session_budget_or_identity')
 for sid in ids:
  text=run(['show-session',sid,'--no-pager','-p','Type','-p','Class','-p','Active','-p','State','-p','Name'])
  fields={}
  for line in text.splitlines():
   key,sep,value=line.partition('=')
   if not sep or key in fields:raise ValueError('property_shape')
   fields[key]=value
  if set(fields)!={'Type','Class','Active','State','Name'} or fields['Active'] not in {'yes','no'}:raise ValueError('property_set')
  kind=fields['Type'] if fields['Type'] in {'x11','wayland'} else 'other'
  candidate=kind in {'x11','wayland'} and fields['Class']=='user' and fields['Active']=='yes' and fields['State']=='active' and bool(fields['Name'].strip())
  out['sessions'].append({'session_ref':hashlib.sha256(sid.encode()).hexdigest(),'kind':kind,'candidate':candidate})
 out['query_complete']=True
except (OSError,ValueError,subprocess.SubprocessError):out['error']='native_session_query_failed'
print(json.dumps(out,sort_keys=True))
'''

def code(name):
 if name not in {'windows','astra'}:raise ValueError('dedicated_session_platform_required')
 return WINDOWS if name=='windows' else ASTRA

def sha(name):return hashlib.sha256(code(name).encode()).hexdigest()

def payload(name):
 if name=='windows':
  program=r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
  args=['-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(code(name).encode('utf-16le')).decode()]
 else:program='/usr/bin/python3';args=['-c',code(name)]
 return {'name':'executeCommand','period':None,'ttl':None,'run_as_user':'','additional_params':{'programm':program,'arguments':args}}

def summarize(b,name):
 if (not isinstance(b,dict) or set(b)!={'probe_version','platform','query_complete','sessions','error'}
  or type(b['probe_version']) is not int or b['probe_version']!=1 or b['platform']!=name
  or type(b['query_complete']) is not bool or b['error'] not in {'','session_query_incomplete','native_session_query_failed'}
  or not isinstance(b['sessions'],list) or len(b['sessions'])>64):raise ValueError('session_census_shape')
 refs=set()
 for row in b['sessions']:
  kinds={'wts'} if name=='windows' else {'x11','wayland','other'}
  if (not isinstance(row,dict) or set(row)!={'session_ref','kind','candidate'}
   or not isinstance(row['session_ref'],str) or not re.fullmatch('[0-9a-f]{64}',row['session_ref'])
   or row['session_ref'] in refs or row['kind'] not in kinds or type(row['candidate']) is not bool
   or row['candidate'] and row['kind']=='other'):raise ValueError('session_census_row')
  refs.add(row['session_ref'])
 complete=b['query_complete'] and not b['error']
 count=sum(row['candidate'] for row in b['sessions']) if complete else None
 return {'observation_status':'COMPLETE' if complete else 'BLOCKED','query_complete':bool(complete),
  'registered_session_count':len(refs) if complete else None,'candidate_user_session_count':count,
  'no_candidate_user_session_reported':count==0 if complete else None,
  'observation_scope':'local_wts_or_logind_registered_sessions_only','usernames_emitted':False,
  'desktop_verified':False,'tray_desktop_verified':False,'login_or_unlock_performed':False,
  'consent_setting_changed':False,'business_pass':False}
