"""Fixed independent OS identity queries, not an osAudit/full-case oracle."""
import base64,hashlib,json
PROFILE='owned-os-identity-baseline-v1'
FIELDS={
 'astra':{'host_name','kernel_name','kernel_release','machine_architecture','os_release_id','os_release_name','os_release_pretty_name','os_release_version_id'},
 'windows':{'host_name','os_caption','os_version','os_build_number','os_architecture'}}
ASTRA=r'''import os,socket,shlex,json
o={'probe_version':1,'platform':'astra','query_complete':False,'values':{},'error':''}
try:
 u=os.uname()
 with open('/etc/os-release',encoding='utf-8') as f:text=f.read(32769)
 if len(text)>32768:raise ValueError('release_budget')
 release={}
 for line in text.splitlines():
  if not line.strip() or line.lstrip().startswith('#') or '=' not in line:continue
  key,value=line.split('=',1)
  if key in {'ID','NAME','PRETTY_NAME','VERSION_ID'}:
   if key in release:raise ValueError('duplicate_release_key')
   words=shlex.split(value,comments=False,posix=True)
   if len(words)>1:raise ValueError('release_value_shape')
   release[key]=words[0] if words else ''
 o['values']={'host_name':socket.gethostname(),'kernel_name':u.sysname,'kernel_release':u.release,'machine_architecture':u.machine,
  'os_release_id':release.get('ID',''),'os_release_name':release.get('NAME',''),'os_release_pretty_name':release.get('PRETTY_NAME',''),'os_release_version_id':release.get('VERSION_ID','')}
 o['query_complete']=True
except (OSError,ValueError,UnicodeError):o.update(query_complete=False,values={},error='native_os_identity_query_failed')
print(json.dumps(o,sort_keys=True,separators=(',',':')))
'''
WINDOWS=r'''$ErrorActionPreference='Stop'
$o=@{probe_version=1;platform='windows';query_complete=$false;values=@{};error=''}
try {
 $items=@(Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction Stop)
 if($items.Count -ne 1){throw 'operating_system_identity_not_unique'}
 $v=$items[0]
 $o.values=@{host_name=[string]$v.CSName;os_caption=[string]$v.Caption;os_version=[string]$v.Version;os_build_number=[string]$v.BuildNumber;os_architecture=[string]$v.OSArchitecture}
 $o.query_complete=$true
}catch{$o.values=@{};$o.query_complete=$false;$o.error='native_os_identity_query_failed'}
$o|ConvertTo-Json -Depth 4 -Compress
'''
LIMITS={'plugin_result_compared':False,'all_os_fields_verified':False,'users_or_volumes_verified':False,'os_ui_verified':False,'settings_changed':False,'full_case_passed':False,'business_pass':False}
def code(name):
 if name not in FIELDS:raise ValueError('os_identity_platform_required')
 return WINDOWS if name=='windows' else ASTRA
def sha(name):return hashlib.sha256(code(name).encode()).hexdigest()
def payload(name):
 text=code(name)
 args=['-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(text.encode('utf-16-le')).decode()] if name=='windows' else ['-c',text]
 return {'name':'executeCommand','period':None,'ttl':None,'run_as_user':'','additional_params':{
  'programm':r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' if name=='windows' else '/usr/bin/python3','arguments':args}}
def summarize(obj,name):
 if name not in FIELDS or not isinstance(obj,dict) or set(obj)!={'probe_version','platform','query_complete','values','error'}:raise ValueError('os_identity_shape')
 if type(obj['probe_version'])!=int or obj['probe_version']!=1 or obj['platform']!=name or type(obj['query_complete'])!=bool or not isinstance(obj['error'],str):raise ValueError('os_identity_header')
 values=obj['values']
 if not obj['query_complete']:
  if values!={} or obj['error']!='native_os_identity_query_failed':raise ValueError('os_identity_unknown_shape')
  return {'os_query_complete':False,'observation_status':'BLOCKED','native_values':None,'unknown_fields':sorted(FIELDS[name]),'values_sha256':None,**LIMITS}
 if obj['error'] or not isinstance(values,dict) or set(values)!=FIELDS[name]:raise ValueError('os_identity_values_shape')
 if any(not isinstance(v,str) or len(v)>512 or any(ord(c)<32 for c in v) for v in values.values()):raise ValueError('os_identity_value_budget')
 unknown=sorted(k for k,v in values.items() if not v.strip())
 return {'os_query_complete':True,'observation_status':'OBSERVED_WITH_UNKNOWNS' if unknown else 'OBSERVED','native_values':dict(values),
  'unknown_fields':unknown,'values_sha256':hashlib.sha256(json.dumps(values,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),**LIMITS}
