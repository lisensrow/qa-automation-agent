"""Versioned fixed-script compression for the agent's cmd.exe transport budget.

V1 remains immutable. Same owned task/path and no-overwrite guards; no cleanup.
No untrusted script input, download, policy bypass, privilege or service changes.
"""
import base64,gzip,hashlib,json
import service_recovery_dry_run as old
REGISTER='owned-windows-service-recovery-dry-register-v2'
OBSERVE='owned-windows-service-recovery-dry-observe-v2'
PROFILES={REGISTER,OBSERVE}

def original(profile):
 if profile not in PROFILES:raise ValueError('recovery_v2_profile')
 return old.REGISTER if profile==REGISTER else old.OBSERVE

def code(name,profile):
 return '# fixed reviewed transport v2, no caller-supplied script\n'+old.code(name,original(profile))

def sha(name,profile):return hashlib.sha256(code(name,profile).encode()).hexdigest()

def wrapper(name,profile):
 packed=base64.b64encode(gzip.compress(code(name,profile).encode('utf-8'),mtime=0)).decode()
 return ("$b=[Convert]::FromBase64String('"+packed+"');$m=New-Object IO.MemoryStream(,$b);"
         "$g=New-Object IO.Compression.GZipStream($m,[IO.Compression.CompressionMode]::Decompress);"
         "$r=New-Object IO.StreamReader($g,[Text.Encoding]::UTF8);"
         "try{$s=$r.ReadToEnd()}finally{$r.Dispose();$m.Dispose()};"
         "& ([ScriptBlock]::Create($s))")

def payload(name,profile):
 text=wrapper(name,profile)
 if any(c in text for c in ('"','\n','\r','%','!')):raise ValueError('recovery_wrapper_quoting')
 args=['-NoLogo','-NoProfile','-NonInteractive','-Command','"'+text+'"']
 # Agent uses cmd.exe: stricter than Win32's 32767-character limit.
 if sum(len(a)+1 for a in args)+100>8000:raise ValueError('recovery_transport_budget')
 return {'name':'executeCommand','period':None,'ttl':None,'run_as_user':'','additional_params':{
  'programm':r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe','arguments':args}}

def summarize(obj,name,profile):return old.summarize(obj,name,original(profile))

def require_own_registration(name):
 import job_store as store,endpoint_metadata as ep
 from operation_journal import list_operations,_fingerprint
 from plugin_preparation import stamp,now
 found=[]
 for job in store.list_jobs(limit=None):
  for case in job.get('test_cases',[]):
   r=case.get('requirement') or {}
   if r.get('profile_id')!=REGISTER or r.get('target')!=name:continue
   if r!=ep.requirement(name,r.get('campaign_id'),REGISTER) or job.get('stand')!='lab' or job.get('resources'):raise ValueError('recovery_registration_context')
   ops=list_operations(job['job_id'])
   if len(ops)!=1 or ops[0]['status']!='verified':raise ValueError('recovery_registration_not_verified')
   op=ops[0];stage=r['operation_stages'][0]
   if op['case_id']!=case['case_id'] or op['tool']!=ep.CREATE or op['verification_fingerprint']!=_fingerprint(stage['verification']):raise ValueError('recovery_registration_contract')
   eid=(op.get('verification') or {}).get('evidence_id')
   e=next((e for e in case.get('evidence',[]) if e.get('evidence_id')==eid),None)
   if not e or e.get('source')!='uqa_tool' or e.get('type')!=ep.READ:raise ValueError('recovery_registration_own_read')
   b=json.loads(e['value']);v=b.get('result') or {}
   if (b.get('tool')!=ep.READ or v.get('native_result_verified') is not True
    or v.get('target')!=name or v.get('agent_id')!=r['agent_id'] or v.get('ci_id')!=r['ci_id']
    or v.get('profile_id')!=REGISTER or v.get('payload_sha256')!=r['payload_sha256']
    or (v.get('summary') or {}).get('dry_registration_verified') is not True
    or not 0<=(stamp(now())-stamp(v['read_at'])).total_seconds()<=900):raise ValueError('recovery_registration_proof')
   found.append((job['job_id'],case['case_id'],eid))
 if len(found)!=1:raise ValueError('one_own_recovery_registration_required')
 return found[0]
