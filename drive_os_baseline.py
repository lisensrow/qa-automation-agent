"""Fixed read-only OS disk enumeration, not a plugin audit or full regression PASS."""
import base64,hashlib
PROFILE='owned-drive-os-baseline-v1'
WINDOWS=r'''$ErrorActionPreference='Stop'
$o=@{probe_version=1;platform='windows';query_complete=$false;rows=@();error=''}
try {
 $items=@(Get-CimInstance -ClassName Win32_LogicalDisk -Property DeviceID,FileSystem,Size,DriveType)
 if($items.Count -gt 256){throw 'row_budget'}
 $rows=@()
 foreach($x in $items){
  $rows+=@{device_name=[string]$x.DeviceID;mount_point=[string]$x.DeviceID;fs_type=[string]$x.FileSystem;
    size_bytes=if($null -eq $x.Size){$null}else{[long]$x.Size};device_kind='logical';drive_type=[int]$x.DriveType}
 }
 $o.rows=@($rows);$o.query_complete=$true
}catch{$o.error='native_disk_query_failed'}
$o | ConvertTo-Json -Depth 5 -Compress
'''
ASTRA=r'''import subprocess,json
o={'probe_version':1,'platform':'astra','query_complete':False,'rows':[],'error':''}
try:
 p=subprocess.run(['/usr/bin/lsblk','--json','--bytes','--output','NAME,TYPE,SIZE,FSTYPE,MOUNTPOINT'],capture_output=True,text=True,timeout=15)
 if p.returncode!=0 or len(p.stdout.encode())>131072:raise ValueError('query_failed_or_budget')
 data=json.loads(p.stdout)
 if not isinstance(data,dict) or not isinstance(data.get('blockdevices'),list):raise ValueError('shape')
 def visit(items,depth=0):
  if depth>16 or len(o['rows'])+len(items)>256:raise ValueError('row_budget')
  for x in items:
   if not isinstance(x,dict) or any(k not in x for k in ['name','type','size','fstype','mountpoint']):raise ValueError('row_shape')
   size=x['size']
   if isinstance(size,str) and size.isdigit():size=int(size)
   if type(size)!=int or not 0<=size<2**63:raise ValueError('size_shape')
   o['rows'].append({'device_name':x['name'],'mount_point':x['mountpoint'],'fs_type':x['fstype'],
    'size_bytes':size,'device_kind':x['type'],'drive_type':None})
   children=x.get('children',[])
   if not isinstance(children,list):raise ValueError('children_shape')
   visit(children,depth+1)
 visit(data['blockdevices']);o['query_complete']=True
except (OSError,ValueError,subprocess.SubprocessError):o['rows']=[];o['error']='native_disk_query_failed'
print(json.dumps(o,sort_keys=True))
'''

def code(name):
    if name not in {'windows','astra'}:raise ValueError('owned_drive_platform_required')
    return WINDOWS if name=='windows' else ASTRA

def sha(name):return hashlib.sha256(code(name).encode()).hexdigest()

def payload(name):
    text=code(name)
    args=['-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(text.encode('utf-16-le')).decode()] if name=='windows' else ['-c',text]
    program=r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' if name=='windows' else '/usr/bin/python3'
    return {'name':'executeCommand','period':None,'ttl':None,'run_as_user':'','additional_params':{'programm':program,'arguments':args}}

def summarize(obj,name):
    code(name)
    if not isinstance(obj,dict) or set(obj)!={'probe_version','platform','query_complete','rows','error'}:
        raise ValueError('drive_os_result_shape')
    if type(obj['probe_version'])!=int or obj['probe_version']!=1 or obj['platform']!=name or type(obj['query_complete'])!=bool or not isinstance(obj['rows'],list) or len(obj['rows'])>256:
        raise ValueError('drive_os_result_scope')
    if obj['error'] not in {'','native_disk_query_failed'}:raise ValueError('drive_os_error_shape')
    rows=[];seen=set()
    for row in obj['rows']:
        if not isinstance(row,dict) or set(row)!={'device_name','mount_point','fs_type','size_bytes','device_kind','drive_type'}:
            raise ValueError('drive_os_row_shape')
        if any(row[k] is not None and (not isinstance(row[k],str) or len(row[k])>1024 or '\x00' in row[k]) for k in ['device_name','mount_point','fs_type','device_kind']):
            raise ValueError('drive_os_text_shape')
        if not row['device_name'] or row['device_name'] in seen:raise ValueError('drive_os_identity')
        seen.add(row['device_name'])
        if row['size_bytes'] is not None and (type(row['size_bytes'])!=int or not 0<=row['size_bytes']<2**63):raise ValueError('drive_os_capacity_shape')
        if row['drive_type'] is not None and (type(row['drive_type'])!=int or not 0<=row['drive_type']<=6):raise ValueError('drive_os_type_shape')
        if not row['device_kind']:raise ValueError('drive_os_kind_missing')
        if name=='windows' and (row['device_kind']!='logical' or row['drive_type'] is None or row['mount_point']!=row['device_name']):
            raise ValueError('drive_os_windows_scope')
        if name=='astra' and (row['drive_type'] is not None or row['size_bytes'] is None):
            raise ValueError('drive_os_astra_scope')
        rows.append(row)
    complete=obj['query_complete'] and not obj['error']
    if obj['query_complete'] and obj['error']:raise ValueError('drive_os_completeness_conflict')
    return {'observation_status':'COMPLETE' if complete else 'BLOCKED','os_query_complete':complete,
        'row_count':len(rows) if complete else None,'os_disk_rows':rows if complete else [],
        'oracle_source':'Win32_LogicalDisk' if name=='windows' else 'lsblk',
        'comparison_scope':'OS enumeration only; compare mount/filesystem/capacity with own fresh driveDeviceAudit separately',
        'plugin_result_compared':False,'full_business_case_passed':False,'business_pass':False,
        'file_contents_read':False,'disk_or_config_changed':False}
