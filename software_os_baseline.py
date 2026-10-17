"""Closed independent package/registry census; not all-software or plugin PASS."""
import base64,hashlib,json,re
PROFILE='owned-software-os-baseline-v1'
MAX_ROWS=2048
ASTRA=r'''import subprocess,json,os,re
o={'probe_version':1,'platform':'astra','query_complete':False,'rows':[],'error':''}
try:
 env=dict(os.environ,LC_ALL='C',LANG='C')
 p=subprocess.run(['/usr/bin/dpkg-query','-W','-f=${db:Status-Status}\t${binary:Package}\t${Version}\t${Architecture}\n'],capture_output=True,text=True,timeout=15,env=env)
 if p.returncode or p.stderr.strip() or len(p.stdout.encode())>220000:raise ValueError('query_failed_or_budget')
 seen=set()
 for line in p.stdout.splitlines():
  cells=line.split('\t')
  if len(cells)!=4:raise ValueError('query_shape')
  status,name,version,arch=cells
  if status!='installed':continue
  if not name or not version or not arch or name in seen:raise ValueError('missing_or_duplicate')
  seen.add(name);o['rows'].append({'record_ref':name,'name':name,'version':version,'architecture':arch})
  if len(o['rows'])>2048:raise ValueError('row_budget')
 o['rows'].sort(key=lambda x:x['record_ref']);o['query_complete']=True
 if len(json.dumps(o,separators=(',',':')).encode())>240000:raise ValueError('output_budget')
except (OSError,ValueError,subprocess.SubprocessError):o.update(query_complete=False,rows=[],error='native_software_query_failed')
print(json.dumps(o,sort_keys=True,separators=(',',':')))
'''
WINDOWS=r'''$ErrorActionPreference='Stop'
$o=@{probe_version=1;platform='windows';query_complete=$false;rows=@();error=''}
try {
 $rows=@();$seen=@{};$hash=[System.Security.Cryptography.SHA256]::Create()
 $specs=@(@('LocalMachine','Registry64','hklm64'),@('LocalMachine','Registry32','hklm32'),@('CurrentUser','Registry64','current-agent-hkcu64'))
 foreach($spec in $specs){
  $hive=[Microsoft.Win32.RegistryHive]::$($spec[0]);$view=[Microsoft.Win32.RegistryView]::$($spec[1])
  $root=[Microsoft.Win32.RegistryKey]::OpenBaseKey($hive,$view)
  try {
   $key=$root.OpenSubKey('Software\Microsoft\Windows\CurrentVersion\Uninstall',$false)
   if($null -eq $key){continue}
   try {
    $names=@($key.GetSubKeyNames());if($names.Count -gt 4096){throw 'key_budget'}
    foreach($sub in $names){
     $item=$key.OpenSubKey($sub,$false);if($null -eq $item){throw 'key_changed'}
     try {
      $name=[string]$item.GetValue('DisplayName','');if([string]::IsNullOrWhiteSpace($name)){continue}
      $version=[string]$item.GetValue('DisplayVersion','')
      $id=($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($spec[2]+':'+$sub))|ForEach-Object {$_.ToString('x2')}) -join ''
      if($seen.ContainsKey($id)){throw 'duplicate'};$seen[$id]=$true
      $rows+=@{record_ref=$id;name=$name;version=$version;architecture=[string]$spec[2]}
      if($rows.Count -gt 2048){throw 'row_budget'}
     }finally{$item.Dispose()}
    }
   }finally{$key.Dispose()}
  }finally{$root.Dispose()}
 }
 $hash.Dispose();$o.rows=@($rows|Sort-Object record_ref);$o.query_complete=$true
 if([Text.Encoding]::UTF8.GetByteCount(($o|ConvertTo-Json -Depth 5 -Compress)) -gt 240000){throw 'output_budget'}
}catch{$o.rows=@();$o.query_complete=$false;$o.error='native_software_query_failed'}
$o|ConvertTo-Json -Depth 5 -Compress
'''

def code(name):
    if name not in {'windows','astra'}:raise ValueError('owned_software_platform_required')
    return WINDOWS if name=='windows' else ASTRA

def sha(name):return hashlib.sha256(code(name).encode()).hexdigest()

def payload(name):
    text=code(name)
    args=['-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(text.encode('utf-16-le')).decode()] if name=='windows' else ['-c',text]
    return {'name':'executeCommand','period':None,'ttl':None,'run_as_user':'','additional_params':{
        'programm':r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' if name=='windows' else '/usr/bin/python3','arguments':args}}

def summarize(obj,name):
    code(name)
    if not isinstance(obj,dict) or set(obj)!={'probe_version','platform','query_complete','rows','error'}:raise ValueError('software_os_shape')
    if type(obj['probe_version'])!=int or obj['probe_version']!=1 or obj['platform']!=name or type(obj['query_complete'])!=bool:raise ValueError('software_os_scope')
    if not isinstance(obj['rows'],list) or len(obj['rows'])>MAX_ROWS or obj['error'] not in {'','native_software_query_failed'}:raise ValueError('software_os_budget_error')
    if obj['query_complete'] and obj['error']:raise ValueError('software_os_complete_conflict')
    if not obj['query_complete'] and (obj['rows'] or not obj['error']):raise ValueError('software_os_incomplete_shape')
    rows=[];seen=set()
    for row in obj['rows']:
        if not isinstance(row,dict) or set(row)!={'record_ref','name','version','architecture'}:raise ValueError('software_os_row_shape')
        if any(not isinstance(row[k],str) or len(row[k])>512 or any(ord(c)<32 for c in row[k]) for k in row):raise ValueError('software_os_text')
        if not row['record_ref'] or not row['name'].strip() or row['record_ref'] in seen:raise ValueError('software_os_duplicate_or_empty')
        if name=='astra' and (not re.fullmatch(r'[a-z0-9][a-z0-9+.-]*(?::[a-z0-9-]+)?',row['record_ref']) or row['record_ref']!=row['name'] or not row['version'] or not re.fullmatch(r'[a-z0-9-]+',row['architecture'])):raise ValueError('software_os_package_shape')
        if name=='windows' and (not re.fullmatch('[0-9a-f]{64}',row['record_ref']) or row['architecture'] not in {'hklm64','hklm32','current-agent-hkcu64'}):raise ValueError('software_os_registry_scope')
        seen.add(row['record_ref']);rows.append(dict(row))
    rows.sort(key=lambda x:x['record_ref'])
    digest=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    complete=obj['query_complete'] and not obj['error']
    return {'observation_status':'COMPLETE' if complete else 'BLOCKED','os_query_complete':complete,'row_count':len(rows) if complete else None,
        'enumeration_sha256':digest if complete else None,'sample_rows':rows[:12] if complete else [],'sample_is_full_enumeration':complete and len(rows)<=12,
        'full_enumeration_in_own_native_result':complete,'oracle_source':'dpkg installed-package database' if name=='astra' else 'Uninstall registry HKLM64/HKLM32 and current agent HKCU64',
        'enumeration_scope':'dpkg status installed only; not portable/snap/flatpak/manual apps' if name=='astra' else 'DisplayName registry entries only; HKCU is agent identity, not all users/MSIX/portable apps; view is not verified program bitness',
        'plugin_result_compared':False,'all_installed_software_completeness_verified':False,'software_tab_verified':False,
        'full_business_case_passed':False,'business_pass':False,'software_installed_removed_or_repaired':False,'uninstall_commands_emitted_or_executed':False}
