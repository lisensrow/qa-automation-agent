"""Closed nonsensitive DMI identity observations, NOT all SMBIOS hardware proof."""
import base64,hashlib,json
PROFILE='owned-dmi-identity-baseline-v1'
FILES={'system_manufacturer':'sys_vendor','system_product_name':'product_name','system_product_version':'product_version',
 'bios_vendor':'bios_vendor','bios_version':'bios_version','baseboard_manufacturer':'board_vendor','baseboard_product':'board_name','baseboard_version':'board_version'}
FIELDS={k:set(FILES) for k in ['windows','astra']}
PLACEHOLDERS={'none','unknown','not specified','not applicable','default string','to be filled by o.e.m.'}
ASTRA=r'''import os,json
fields={'system_manufacturer':'sys_vendor','system_product_name':'product_name','system_product_version':'product_version','bios_vendor':'bios_vendor','bios_version':'bios_version','baseboard_manufacturer':'board_vendor','baseboard_product':'board_name','baseboard_version':'board_version'}
o={'probe_version':1,'platform':'astra','query_complete':False,'values':{},'error':''}
try:
 for key,name in fields.items():
  value=''
  try:
   fd=os.open('/sys/class/dmi/id/'+name,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
   try:raw=os.read(fd,2049)
   finally:os.close(fd)
   if len(raw)>2048:raise ValueError('dmi_value_budget')
   value=raw.decode('utf-8').rstrip('\n')
   if len(value)>512 or any(ord(c)<32 for c in value):raise ValueError('dmi_value_shape')
  except (OSError,UnicodeError,ValueError):value=''
  o['values'][key]=value
 o['query_complete']=True
except (OSError,ValueError,TypeError):o.update(query_complete=False,values={},error='native_dmi_identity_query_failed')
print(json.dumps(o,sort_keys=True,separators=(',',':')))
'''
WINDOWS=r'''$ErrorActionPreference='Stop'
$o=@{probe_version=1;platform='windows';query_complete=$false;values=@{};error=''}
try {
 $system=@(Get-CimInstance -ClassName Win32_ComputerSystemProduct -Property Vendor,Name,Version -ErrorAction Stop)
 $bios=@(Get-CimInstance -ClassName Win32_BIOS -Property Manufacturer,SMBIOSBIOSVersion -ErrorAction Stop)
 $board=@(Get-CimInstance -ClassName Win32_BaseBoard -Property Manufacturer,Product,Version -ErrorAction Stop)
 if($system.Count -ne 1 -or $bios.Count -ne 1 -or $board.Count -ne 1){throw 'dmi_identity_not_unique'}
 $o.values=@{system_manufacturer=[string]($system[0].Vendor);system_product_name=[string]($system[0].Name);system_product_version=[string]($system[0].Version);
 bios_vendor=[string]($bios[0].Manufacturer);bios_version=[string]($bios[0].SMBIOSBIOSVersion);
 baseboard_manufacturer=[string]($board[0].Manufacturer);baseboard_product=[string]($board[0].Product);baseboard_version=[string]($board[0].Version)}
 $o.query_complete=$true
}catch{$o.values=@{};$o.query_complete=$false;$o.error='native_dmi_identity_query_failed'}
$o|ConvertTo-Json -Depth 4 -Compress
'''
LIMITS={'plugin_result_compared':False,'all_dmi_structures_verified':False,'cpu_or_memory_modules_verified':False,
 'serials_or_uuids_emitted':False,'hardware_ui_verified':False,'bios_or_settings_changed':False,'full_case_passed':False,'business_pass':False}
def code(name):
 if name not in FIELDS:raise ValueError('dmi_identity_platform')
 return WINDOWS if name=='windows' else ASTRA
def sha(name):return hashlib.sha256(code(name).encode()).hexdigest()
def payload(name):
 text=code(name);args=['-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(text.encode('utf-16-le')).decode()] if name=='windows' else ['-c',text]
 return {'name':'executeCommand','period':None,'ttl':None,'run_as_user':'','additional_params':{
  'programm':r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' if name=='windows' else '/usr/bin/python3','arguments':args}}
def summarize(obj,name):
 if name not in FIELDS or not isinstance(obj,dict) or set(obj)!={'probe_version','platform','query_complete','values','error'}:raise ValueError('dmi_identity_shape')
 if type(obj['probe_version'])!=int or obj['probe_version']!=1 or obj['platform']!=name or type(obj['query_complete'])!=bool or not isinstance(obj['error'],str):raise ValueError('dmi_identity_header')
 values=obj['values']
 if not obj['query_complete']:
  if values!={} or obj['error']!='native_dmi_identity_query_failed':raise ValueError('dmi_unknown_shape')
  return {'dmi_query_complete':False,'observation_status':'BLOCKED','native_values':None,'unknown_fields':sorted(FIELDS[name]),'values_sha256':None,**LIMITS}
 if obj['error'] or not isinstance(values,dict) or set(values)!=FIELDS[name]:raise ValueError('dmi_identity_fields')
 if any(not isinstance(v,str) or len(v)>512 or any(ord(c)<32 for c in v) for v in values.values()):raise ValueError('dmi_identity_value_budget')
 unknown=sorted(k for k,v in values.items() if not v.strip() or v.strip().casefold() in PLACEHOLDERS)
 return {'dmi_query_complete':True,'observation_status':'BLOCKED' if len(unknown)==len(FIELDS[name]) else 'OBSERVED_WITH_UNKNOWNS' if unknown else 'OBSERVED',
  'native_values':dict(values),'unknown_fields':unknown,'values_sha256':hashlib.sha256(json.dumps(values,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),**LIMITS}
