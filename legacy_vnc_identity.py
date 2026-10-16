"""Fixed read-only legacy identification, not uninstall authority or absence proof."""
import hashlib,json,re
PROFILE='legacy-vnc-identity-v1'
CODE=r'''import os,json,subprocess
out={'probe_version':1,'packages':[],'processes':[],'package_query_complete':False,'process_scan_complete':True,'uninstall_executed':False}
try:
 p=subprocess.run(['/usr/bin/dpkg-query','-W','-f=${binary:Package}\t${Version}\t${db:Status-Status}\n'],capture_output=True,text=True,timeout=15)
 if p.returncode==0 and len(p.stdout.encode())<=2097152:
  out['package_query_complete']=True
  for line in p.stdout.splitlines():
   fields=line.split('\t')
   if len(fields)==3 and 'tightvnc' in fields[0].casefold():
    out['packages'].append({'name':fields[0],'version':fields[1],'status':fields[2]})
except (OSError,subprocess.SubprocessError):pass
try:
 names=[x for x in os.listdir('/proc') if x.isdigit()]
 if len(names)>10000:out['process_scan_complete']=False;names=names[:10000]
 for pid in names:
  try:
   with open('/proc/'+pid+'/comm') as f:name=f.read(64).strip()
   if name.casefold() in ('xtightvnc','tightvncserver','tvnserver','tvnserver.exe'):
    try:exe=os.readlink('/proc/'+pid+'/exe')
    except OSError:exe=None
    package=None
    if exe and exe.startswith('/') and not exe.endswith(' (deleted)'):
     try:
      q=subprocess.run(['/usr/bin/dpkg-query','-S',exe],capture_output=True,text=True,timeout=5)
      if q.returncode==0 and len(q.stdout)<=4096:package=q.stdout.split(': ',1)[0].strip()
     except (OSError,subprocess.SubprocessError):pass
    out['processes'].append({'name':name,'executable':exe,'package_owner':package,
      'plugin_path':bool(exe and exe.startswith('/opt/usystem/usagent/'))})
  except FileNotFoundError:pass
  except OSError:out['process_scan_complete']=False
except OSError:out['process_scan_complete']=False
print(json.dumps(out,sort_keys=True))
'''
PROGRAM='/usr/bin/python3'
SHA=hashlib.sha256(CODE.encode()).hexdigest()
PAYLOAD={'name':'executeCommand','period':None,'ttl':None,'run_as_user':'',
 'additional_params':{'programm':PROGRAM,'arguments':['-c',CODE]}}

def summarize(b):
 if (not isinstance(b,dict) or set(b)!={'probe_version','packages','processes','package_query_complete','process_scan_complete','uninstall_executed'}
   or b['probe_version']!=1 or b['uninstall_executed'] is not False
   or any(type(b[k]) is not bool for k in ['package_query_complete','process_scan_complete'])
   or not isinstance(b['packages'],list) or len(b['packages'])>100
   or not isinstance(b['processes'],list) or len(b['processes'])>100):raise ValueError('legacy_identity_shape')
 packages=[]
 for p in b['packages']:
  if (not isinstance(p,dict) or set(p)!={'name','version','status'}
    or any(not isinstance(p[k],str) or not 1<=len(p[k])<=256 for k in p)
    or not re.fullmatch(r'[a-z0-9][a-z0-9+.:\-]*',p['name']) or 'tightvnc' not in p['name'].casefold()):
   raise ValueError('legacy_package_identity')
  packages.append(p)
 processes=[]
 for p in b['processes']:
  if (not isinstance(p,dict) or set(p)!={'name','executable','package_owner','plugin_path'}
    or not isinstance(p['name'],str) or p['name'].casefold() not in {'xtightvnc','tightvncserver','tvnserver','tvnserver.exe'}
    or type(p['plugin_path']) is not bool
    or any(v is not None and (not isinstance(v,str) or len(v)>4096) for v in [p['executable'],p['package_owner']])):
   raise ValueError('legacy_process_identity')
  if p['plugin_path']!=bool(p['executable'] and p['executable'].startswith('/opt/usystem/usagent/')):
   raise ValueError('legacy_plugin_ownership_mismatch')
  processes.append(p)
 servers=[p for p in packages if p['name'].split(':')[0]=='tightvncserver' and p['status']=='installed']
 return {'legacy_standalone_package_observed':bool(servers),'server_package_candidates':servers,
   'package_matches':packages,'process_matches':processes,
   'package_query_complete':b['package_query_complete'],'process_scan_complete':b['process_scan_complete'],
   'legacy_absence_proved':False,'uninstall_authorized_by_probe':False,'uninstall_executed':False,
   'observation_status':'COMPLETE' if b['package_query_complete'] and b['process_scan_complete'] else 'BLOCKED',
   'tray_desktop_verified':False,'business_pass':False}
