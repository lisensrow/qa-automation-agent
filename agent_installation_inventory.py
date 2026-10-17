"""Case1 pre/post metadata only. No contents, identity reset, installer or PASS."""
import base64,hashlib,json
PROFILE='owned-agent-installation-file-inventory-v1'
WINDOWS_PATHS=[('identity','C:\\ProgramData\\USystem\\etc\\machine_uid.txt'),('legacy_dot_directory','C:\\ProgramData\\.Usystem')]
COMMON=['bin/3rdparty/7zip','bin/updater','etc/usagent/cert/cacert.pem','etc/usagent/cert/clientCert.pem','etc/usagent/cert/clientPrivateKey.pem','etc/usagent/cert/clientRequest.csr','etc/usagent/usagent.conf','etc/usagent/sys_usagent.conf','lib/plugins/tasks','var/log/usagent/usagent.log','var/usb-devices.json','var/usagent/downloads']
EXTRA={'windows':['bin/3rdparty/TightVNC','bin/3rdparty/Nmap','bin/3rdparty/PowerCLI.zip','bin/plugins/bearer','bin/plugins/iconengines','bin/plugins/imageformats','bin/plugins/platforms','bin/plugins/platformthemes','bin/plugins/styles','var/log/usagent/usexecutor.log'],
 'astra':['bin/3rdparty/TigerVNC','lib','plugins','plugins/iconengines','plugins/imageformats','plugins/platforms','plugins/xcbglintegrations','usAgent.sh','usAgentTray.sh','usExecutor.sh']}

def relative_paths(name):
 if name not in EXTRA:raise ValueError('installation_inventory_platform')
 return COMMON+EXTRA[name]

def code(name):
 rel=relative_paths(name)
 if name=='astra':
  return '''import json,os,stat
root='/opt/usystem/usagent'
paths=JSON_PATHS
rows=[]
for key in paths:
 p=root+'/'+key
 state='missing'
 try:
  for ancestor in ['/opt','/opt/usystem',root]+[root+'/'+ '/'.join(key.split('/')[:i]) for i in range(1,len(key.split('/'))+1)]:
   s=os.lstat(ancestor)
   if stat.S_ISLNK(s.st_mode):state='link_blocked';break
  else:state='file' if stat.S_ISREG(s.st_mode) else 'directory' if stat.S_ISDIR(s.st_mode) else 'other'
 except FileNotFoundError:pass
 except OSError:state='unavailable'
 rows.append({'key':key,'state':state})
print(json.dumps({'probe_version':1,'platform':'astra','root':root,'rows':rows}))
'''.replace('JSON_PATHS',repr(rel))

 return r'''$ErrorActionPreference='Stop'
$svc=Get-CimInstance Win32_Service -Filter "Name='USystemAgentSystem'"
if(-not $svc){throw 'exact_service_missing'}
$command=[string]$svc.PathName
if($command -match '^"([^\"]+)"'){$exe=$matches[1]}elseif($command -match '^(.*?\.exe)(?:\s|$)'){$exe=$matches[1]}else{throw 'service_path'}
$bin=[IO.Path]::GetDirectoryName($exe)
if([IO.Path]::GetFileName($bin) -ine 'bin'){throw 'service_bin'}
$root=[IO.Path]::GetDirectoryName($bin)
$allowed=@()
foreach($prefix in @($env:ProgramFiles,${env:ProgramFiles(x86)})){if($prefix){$allowed+=(Join-Path $prefix 'USystem\agentServer')}}
if($root.TrimEnd('\') -notin $allowed){throw 'product_root'}
$rows=@()
$rel=ConvertFrom-Json -InputObject 'REL_JSON'
$extra=ConvertFrom-Json -InputObject 'EXTRA_JSON'
$items=@()
foreach($key in $rel){$items+=@{key=[string]$key;path=(Join-Path $root $key)}}
foreach($pair in $extra){$items+=@{key=[string]$pair[0];path=[string]$pair[1]}}
foreach($item in $items){
 $state='missing';$p=[string]$item.path
 try{
  $current=$p
  while($current){
   $entry=$null
   try{$entry=Get-Item -LiteralPath $current -Force -ErrorAction Stop}catch [System.Management.Automation.ItemNotFoundException]{}
   if($entry -and ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint)){$state='link_blocked';break}
   $parent=[IO.Path]::GetDirectoryName($current)
   if($parent -eq $current){break};$current=$parent
  }
  if($state -ne 'link_blocked'){
   $entry=$null
   try{$entry=Get-Item -LiteralPath $p -Force -ErrorAction Stop}catch [System.Management.Automation.ItemNotFoundException]{}
   if($entry){$state=if($entry.PSIsContainer){'directory'}else{'file'}}
  }
 }catch{$state='unavailable'}
 $rows+=@{key=$item.key;state=$state}
}
@{probe_version=1;platform='windows';root=$root;rows=@($rows)} | ConvertTo-Json -Depth 5 -Compress
'''.replace('REL_JSON',json.dumps(rel)).replace('EXTRA_JSON',json.dumps(WINDOWS_PATHS))

def sha(name):return hashlib.sha256(code(name).encode()).hexdigest()
def payload(name):
 text=code(name)
 return {'name':'executeCommand','period':None,'ttl':None,'run_as_user':'','additional_params':{
  'programm':r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' if name=='windows' else '/usr/bin/python3',
  'arguments':['-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(text.encode('utf-16-le')).decode()] if name=='windows' else ['-c',text]}}

def summarize(obj,name):
 expected=relative_paths(name)+(['identity','legacy_dot_directory'] if name=='windows' else [])
 if not isinstance(obj,dict) or set(obj)!={'probe_version','platform','root','rows'} or type(obj['probe_version'])!=int or obj['probe_version']!=1 or obj['platform']!=name:raise ValueError('installation_inventory_shape')
 roots=[r'C:\Program Files\USystem\agentServer',r'C:\Program Files (x86)\USystem\agentServer'] if name=='windows' else ['/opt/usystem/usagent']
 if not isinstance(obj['root'],str) or (obj['root'].casefold() not in [r.casefold() for r in roots] if name=='windows' else obj['root'] not in roots) or not isinstance(obj['rows'],list) or len(obj['rows'])!=len(expected):raise ValueError('installation_inventory_scope')
 for row,key in zip(obj['rows'],expected):
  if not isinstance(row,dict) or set(row)!={'key','state'} or row['key']!=key or row['state'] not in {'file','directory','missing','link_blocked','unavailable','other'}:raise ValueError('installation_inventory_row')
 return {'observation_status':'BLOCKED' if any(x['state'] in {'link_blocked','unavailable','other'} for x in obj['rows']) else 'COMPLETE','root':obj['root'],'file_metadata':obj['rows'],
  'installation_executed':False,'identity_changed':False,'file_contents_read':False,'tray_desktop_verified':False,'full_case_passed':False,'business_pass':False}
