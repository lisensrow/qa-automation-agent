"""Fixed independent GPU metadata prerequisite, not plugin correctness/completeness."""
import base64,hashlib,re
PROFILE='owned-gpu-os-baseline-v1'
WINDOWS=r'''$ErrorActionPreference='Stop'
$o=@{probe_version=1;platform='windows';query_complete=$false;rows=@();error=''}
try {
 $items=@(Get-CimInstance -ClassName Win32_VideoController -Property DeviceID,Name,PNPDeviceID)
 if($items.Count -gt 256){throw 'row_budget'}
 $rows=@()
 foreach($x in $items){
  $vendor=$null;$device=$null
  if([string]$x.PNPDeviceID -match 'VEN_([0-9A-Fa-f]{4})&DEV_([0-9A-Fa-f]{4})'){$vendor=$Matches[1].ToLowerInvariant();$device=$Matches[2].ToLowerInvariant()}
  $rows+=@{device_ref=[string]$x.DeviceID;device_name=[string]$x.Name;vendor_name=$null;vendor_id=$vendor;device_id=$device;class_id=$null;device_kind='video_controller'}
 }
 $o.rows=@($rows);$o.query_complete=$true
}catch{$o.rows=@();$o.error='native_gpu_query_failed'}
$o | ConvertTo-Json -Depth 5 -Compress
'''
ASTRA=r'''import subprocess,json,re
o={'probe_version':1,'platform':'astra','query_complete':False,'rows':[],'error':''}
try:
 p=subprocess.run(['/usr/bin/lspci','-D','-vmm','-nn'],capture_output=True,text=True,timeout=15)
 if p.returncode!=0 or len(p.stdout.encode())>131072 or p.stderr.strip():raise ValueError('query_failed_or_budget')
 required={'Slot','Class','Vendor','Device'}
 def tagged(value):
  m=re.fullmatch(r'(.*?)\s+\[([0-9a-fA-F]{4})\]',value)
  if not m:raise ValueError('numeric_tag_missing')
  return m.group(1).strip(),m.group(2).lower()
 records=[x for x in re.split(r'\n\s*\n',p.stdout.strip()) if x.strip()]
 if len(records)>1024:raise ValueError('pci_row_budget')
 for record in records:
  fields={}
  for line in record.splitlines():
   if ':' not in line:raise ValueError('line_shape')
   key,value=line.split(':',1)
   if key in required:
    if key in fields:raise ValueError('duplicate_tag')
    fields[key]=value.strip()
  if set(fields)!=required:raise ValueError('missing_required_tag')
  _,class_id=tagged(fields['Class'])
  if not class_id.startswith('03'):continue
  vendor,vendor_id=tagged(fields['Vendor']);device,device_id=tagged(fields['Device'])
  if not re.fullmatch(r'[0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-7]',fields['Slot']):raise ValueError('slot_shape')
  o['rows'].append({'device_ref':fields['Slot'].lower(),'device_name':device,'vendor_name':vendor,
   'vendor_id':vendor_id,'device_id':device_id,'class_id':class_id,'device_kind':'pci_display_class'})
  if len(o['rows'])>256:raise ValueError('gpu_row_budget')
 o['query_complete']=True
except (OSError,ValueError,subprocess.SubprocessError):o['rows']=[];o['error']='native_gpu_query_failed'
print(json.dumps(o,sort_keys=True))
'''

def code(name):
    if name not in {'windows','astra'}:raise ValueError('owned_gpu_platform_required')
    return WINDOWS if name=='windows' else ASTRA
def sha(name):return hashlib.sha256(code(name).encode()).hexdigest()
def payload(name):
    text=code(name)
    args=['-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(text.encode('utf-16-le')).decode()] if name=='windows' else ['-c',text]
    return {'name':'executeCommand','period':None,'ttl':None,'run_as_user':'','additional_params':{
        'programm':r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' if name=='windows' else '/usr/bin/python3','arguments':args}}
def summarize(obj,name):
    code(name)
    if not isinstance(obj,dict) or set(obj)!={'probe_version','platform','query_complete','rows','error'}:raise ValueError('gpu_os_shape')
    if type(obj['probe_version'])!=int or obj['probe_version']!=1 or obj['platform']!=name or type(obj['query_complete'])!=bool:
        raise ValueError('gpu_os_scope')
    if not isinstance(obj['rows'],list) or len(obj['rows'])>256 or obj['error'] not in {'','native_gpu_query_failed'}:raise ValueError('gpu_os_budget_error')
    if obj['query_complete'] and obj['error']:raise ValueError('gpu_os_completeness_conflict')
    if not obj['query_complete'] and obj['rows']:raise ValueError('gpu_os_partial_rows_not_complete')
    rows=[];seen=set()
    for row in obj['rows']:
        if not isinstance(row,dict) or set(row)!={'device_ref','device_name','vendor_name','vendor_id','device_id','class_id','device_kind'}:raise ValueError('gpu_os_row_shape')
        if any(not isinstance(row[k],str) or not 0<len(row[k])<=1024 or '\x00' in row[k] for k in ['device_ref','device_name','device_kind']):raise ValueError('gpu_os_text')
        if row['device_ref'] in seen:raise ValueError('gpu_os_duplicate');
        seen.add(row['device_ref'])
        if row['vendor_name'] is not None and (not isinstance(row['vendor_name'],str) or not 0<len(row['vendor_name'])<=1024 or '\x00' in row['vendor_name']):raise ValueError('gpu_os_vendor_text')
        if any(row[k] is not None and (not isinstance(row[k],str) or not re.fullmatch('[0-9a-f]{4}',row[k])) for k in ['vendor_id','device_id','class_id']):raise ValueError('gpu_os_ids')
        if (row['vendor_id'] is None)!=(row['device_id'] is None):raise ValueError('gpu_os_id_pair')
        if name=='windows' and (row['device_kind']!='video_controller' or row['class_id'] is not None or row['vendor_name'] is not None):raise ValueError('gpu_os_windows_scope')
        if name=='astra' and (row['device_kind']!='pci_display_class' or not row['vendor_name'] or row['vendor_id'] is None or not (row['class_id'] or '').startswith('03')
            or not re.fullmatch(r'[0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]',row['device_ref'])):raise ValueError('gpu_os_astra_scope')
        rows.append(dict(row))
    complete=obj['query_complete'] and not obj['error']
    return {'observation_status':'COMPLETE' if complete else 'BLOCKED','os_query_complete':complete,
        'row_count':len(rows) if complete else None,'os_gpu_rows':rows if complete else [],
        'oracle_source':'Win32_VideoController' if name=='windows' else 'lspci -D -vmm -nn PCI class03',
        'enumeration_scope':'Windows reported video controllers' if name=='windows' else 'PCI display-class devices only; names depend on local pci.ids',
        'plugin_result_compared':False,'all_gpu_completeness_verified':False,'plugin_name_note_semantics_verified':False,
        'desktop_or_render_verified':False,'full_business_case_passed':False,'business_pass':False,
        'settings_or_drivers_changed':False,'file_contents_read':False}
