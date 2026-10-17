"""Fixed metadata-only log presence variant; never five-day/rotation acceptance."""
import base64, hashlib
PROFILE = 'owned-current-agent-log-presence-v1'
LIMITS = {'file_contents_read': False, 'rotation_verified': False,
          'five_day_retention_verified': False, 'tray_verified': False,
          'full_source_case_passed': False}
ASTRA = r'''import os,stat,json,hashlib
o={'probe_version':1,'platform':'astra','query_complete':False,'files':[],'error':''}
try:
 fd=os.open('/opt/usystem/usagent/var/log/usagent',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:
  names=os.listdir(fd)
  if len(names)>128:raise ValueError('budget')
  for name in names:
   s=os.stat(name,dir_fd=fd,follow_symlinks=False)
   if stat.S_ISREG(s.st_mode):
    o['files'].append({'id':hashlib.sha256(os.fsencode(name)).hexdigest(),'size':s.st_size,'mtime_ms':s.st_mtime_ns//1000000})
  o['query_complete']=True
 finally:os.close(fd)
except (OSError,ValueError):o['files']=[];o['error']='log_metadata_unavailable'
print(json.dumps(o,sort_keys=True))
'''
WINDOWS = r'''$ErrorActionPreference='Stop'
$o=@{probe_version=1;platform='windows';query_complete=$false;files=@();error=''}
try {
 $s=@(Get-CimInstance Win32_Service -Filter "Name='USystemAgentSystem'")
 if($s.Count -ne 1){throw 'service_identity'}
 $p=[string]$s[0].PathName
 if($p -match '^"([^\"]+\.exe)"(?:\s|$)'){$exe=$Matches[1]}
 elseif($p -match '^(.+?\.exe)(?:\s|$)'){$exe=$Matches[1]}else{throw 'service_path'}
 $exe=[IO.Path]::GetFullPath($exe)
 if([IO.Path]::GetFileName($exe) -notin @('usAgentSystem.exe','usAgent.exe')){throw 'binary_identity'}
 $allowed=$false
 foreach($prefix in @($env:ProgramFiles,${env:ProgramFiles(x86)})){
  if($prefix -and $exe.StartsWith(([IO.Path]::GetFullPath($prefix).TrimEnd('\')+'\USystem\'),[StringComparison]::OrdinalIgnoreCase)){$allowed=$true}
 }
 if(-not $allowed){throw 'product_root'}
 $root=Join-Path ([IO.Path]::GetDirectoryName($exe)) 'var\log\usagent'
 $d=Get-Item -LiteralPath $root -Force
 if(-not $d.PSIsContainer){throw 'not_directory'}
 $current=$d
 while($null -ne $current){
  if(($current.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'reparse_root'}
  $current=$current.Parent
 }
 $items=@(Get-ChildItem -LiteralPath $root -Force)
 if($items.Count -gt 128){throw 'budget'}
 $sha=[Security.Cryptography.SHA256]::Create()
 try {
  $rows=@()
  foreach($f in $items){
   if(-not $f.PSIsContainer -and ($f.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0){
    $id=([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($f.Name)))).Replace('-','').ToLowerInvariant()
    $rows+=@{id=$id;size=[long]$f.Length;mtime_ms=([DateTimeOffset]$f.LastWriteTimeUtc).ToUnixTimeMilliseconds()}
   }
  }
  $o.files=@($rows);$o.query_complete=$true
 }finally{$sha.Dispose()}
}catch{$o.files=@();$o.error='log_metadata_unavailable'}
$o | ConvertTo-Json -Depth 5 -Compress
'''

def code(name):
    if name not in {'windows','astra'}: raise ValueError('log_presence_platform')
    return WINDOWS if name == 'windows' else ASTRA

def sha(name): return hashlib.sha256(code(name).encode()).hexdigest()

def payload(name):
    text=code(name)
    args=['-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(text.encode('utf-16-le')).decode()] if name=='windows' else ['-c',text]
    program=r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' if name=='windows' else '/usr/bin/python3'
    return {'name':'executeCommand','period':None,'ttl':None,'run_as_user':'',
            'additional_params':{'programm':program,'arguments':args}}

def summarize(obj,name):
    code(name)
    if not isinstance(obj,dict) or set(obj)!={'probe_version','platform','query_complete','files','error'}: raise ValueError('log_presence_shape')
    if type(obj['probe_version']) is not int or obj['probe_version']!=1 or obj['platform']!=name or type(obj['query_complete']) is not bool: raise ValueError('log_presence_scope')
    if not isinstance(obj['files'],list) or len(obj['files'])>128 or obj['error'] not in {'','log_metadata_unavailable'}: raise ValueError('log_presence_budget')
    if obj['query_complete'] != (obj['error']=='') or (not obj['query_complete'] and obj['files']): raise ValueError('log_presence_complete')
    seen=set()
    for row in obj['files']:
        if not isinstance(row,dict) or set(row)!={'id','size','mtime_ms'}: raise ValueError('log_presence_row')
        ident=row['id']
        if not isinstance(ident,str) or len(ident)!=64 or any(c not in '0123456789abcdef' for c in ident) or ident in seen: raise ValueError('log_presence_id')
        seen.add(ident)
        if any(type(row[k]) is not int or not 0<=row[k]<2**63 for k in ('size','mtime_ms')): raise ValueError('log_presence_metadata')
    complete=obj['query_complete']; count=len(seen) if complete else None
    nonempty=sum(x['size']>0 for x in obj['files']) if complete else None
    return {'query_complete':complete,'regular_file_count':count,'nonempty_file_count':nonempty,
            'adapted_presence_status':('PASS' if nonempty else 'FAIL') if complete else 'BLOCKED',
            'acceptance_variant':'user_authorized_nonempty_agent_log_files_only',**LIMITS}
