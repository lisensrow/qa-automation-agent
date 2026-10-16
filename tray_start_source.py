"""Pinned supplied Tray start candidate; no install/stop/restart/consent setter.

Only one attempt per target across campaigns. Static literals are a bounded
probe contract, NOT a complete API or desktop oracle. No operator installation.
"""
import hashlib,json
import job_store,ssh_worker
from operation_journal import list_operations
PROFILE='supplied-tray-plugin-start-v1'
JOB='20261016-141140-a11eded3'
EVIDENCE='ev-efd8c4a720c6'
SHA='1da5de3fbd878ce899f19fbc10af1a4df6f90e9436fe8080b98e4e1c203a067f'
BINARIES={
 'windows':('windows_x64/libTrayControl.dll','f8d05358b63f4bd439a8c103540eb5d252950996bb9b9a17ac1d405e58461fa9'),
 'astra':('debian_x64/libTrayControl.so','94b43341ae31426439298998305d07896d1006f495b5d99bf1bf16bfd47fd4a7')}
assert all(len(s)==64 and all(c in '0123456789abcdef' for c in s) for s in [SHA,*[x[1] for x in BINARIES.values()]])

def outcome(data):
 """Only explicit root errors; unknown schema never becomes start/desktop PASS."""
 result={'explicit_native_error':False,'native_result_token':'unknown','error_text_sha256':None,
  'functional_start_status':'BLOCKED','desktop_verified':False,'complete_payload_contract_known':False,
  'reported_started_count':None,'reported_already_running_count':None,'user_selector_empty':None}
 if not isinstance(data,dict):return result
 token=data.get('result')
 if isinstance(token,str) and token.casefold() in {'success','error','failed','failure'}:
  result['native_result_token']=token.casefold()
 error=data.get('error')
 if data.get('action')=='start':
  for key,outkey in [('started','reported_started_count'),('already_running','reported_already_running_count')]:
   if isinstance(data.get(key),list):result[outkey]=len(data[key])
  if isinstance(data.get('user'),str):result['user_selector_empty']=not bool(data['user'].strip())
 nonempty=isinstance(error,str) and bool(error.strip())
 result['explicit_native_error']=bool(nonempty or result['native_result_token'] in {'error','failed','failure'})
 if nonempty:result['error_text_sha256']=hashlib.sha256(error.encode()).hexdigest()
 if result['explicit_native_error']:result['functional_start_status']='FAIL'
 return result

def validate_start_prerequisites(r,jid):
 if (r.get('profile_id'),r.get('plugin_name'),r.get('plugin_version'))!=(PROFILE,'trayControl','1.0.1') or r.get('target') not in BINARIES:
  raise ValueError('exact_supplied_tray_scope_required')
 source=job_store.get_job(JOB)
 e=next(e for c in source['test_cases'] for e in c['evidence'] if e['evidence_id']==EVIDENCE)
 if (e.get('source')!='operator_supplied_binary_static_review' or e.get('type')!='operator_tray_start_contract_candidate'
     or e.get('execution_status')!='observed' or hashlib.sha256(e['value'].encode()).hexdigest()!=SHA):
  raise ValueError('reviewed_tray_candidate_source_required')
 body=json.loads(e['value'])
 if body.get('candidate_payload')!={'name':'trayControl','period':None,'ttl':None,'run_as_user':'','additional_params':{'action':'start'}}:
  raise ValueError('tray_source_payload_changed')
 for old in job_store.list_jobs(limit=None):
  if old['job_id']==jid:continue
  if any((c.get('requirement') or {}).get('profile_id')==PROFILE and c['requirement'].get('target')==r['target'] for c in old.get('test_cases',[])):
   if any(o['status'] not in {'not_sent','rejected'} for o in list_operations(old['job_id'])):
    raise ValueError('tray_start_prior_attempt_no_rekey')
 leaf,sha=BINARIES[r['target']]
 platform=leaf.split('/')[0]
 if (body.get('platforms',{}).get(platform,{}).get('sha256')!=sha
     or not all(x in body['platforms'][platform].get('literal_tokens',[]) for x in ['trayControl','action','start','action is required in additional_params'])):
  raise ValueError('tray_source_platform_contract_required')
 out=ssh_worker._run('lab','sha256sum /home/adminacc/uconnect-update-2.8.1-20261015/plugins/trayControl/1.0.1/'+leaf,sudo=True)
 if out['exit_code']!=0 or not out['stdout'].startswith(sha+'  '):raise ValueError('tray_supplied_binary_changed')
 return {'candidate_source_checked':True,'supplied_binary_sha256':sha,'desktop_oracle_known':False,'business_pass':False}
