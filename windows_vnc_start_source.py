"""Pinned supplied startup candidate and bounded unchanged-state prerequisites.

Baseline absence is historical, NOT a new fresh registry observation. Reject any
subsequent agent command/delivery and any already-running VNC before startup.
No execution of MSI or extracted vendor binaries by the operator/framework.
"""
import hashlib,json
import job_store,ssh_worker
from operation_journal import list_operations
from plugin_preparation import stamp
from command_stage_native import context,read_json
from configured_vnc_session import get,checked_config,requirement as configured_requirement
from task_page_preflight import complete_task_list
JOB='20261016-135746-d77c7e36'
EVIDENCE='ev-06588d0bab0c'
SHA='a7d2f307838d798822925b44c4ffa03aed226bc66689bbf89ac1bc382e27a0c0'
BINARY='/home/adminacc/uconnect-update-2.8.1-20261015/plugins/vncServer/1.5.5/windows_x64/libVncServer.dll'
BINARY_SHA='48e16c228a862b727332b6fa3e5dc39cefdc7cba1e007c60ca7431c8ed0d3695'

def validate_start_prerequisites(session,r):
 if (r['target'],r['plugin_name'],r['plugin_version'],r['profile_id'])!=('windows','vncServer','1.5.5','supplied-vnc-plugin-start-v1'):
  raise ValueError('exact_vnc_start_scope_required')
 old=job_store.get_job(JOB);c=old['test_cases'][0]
 e=next(e for e in c['evidence'] if e['evidence_id']==EVIDENCE)
 if (e.get('source')!='uqa_tool' or e.get('type')!='browser_inspect_closed_endpoint_metadata_semantic'
  or e.get('execution_status') not in {'observed','executed'} or hashlib.sha256(e['value'].encode()).hexdigest()!=SHA):
  raise ValueError('vnc_start_absence_baseline_changed')
 b=json.loads(e['value'])['result'];summary=b['summary']
 if (b.get('target')!='windows' or b.get('ci_id')!=r['ci_id'] or b.get('agent_id')!=r['agent_id']
  or b.get('native_result_verified') is not True or summary.get('absence_status')!='PASS'
  or summary.get('uninstall_performed') is not False or not all(summary.get(k) is True for k in
   ['registry_absent','legacy_service_absent','legacy_process_absent'])):raise ValueError('vnc_start_absence_baseline_scope')
 ops=list_operations(JOB)
 if len(ops)!=1 or ops[0]['status']!='verified' or ops[0]['verification']['evidence_id']!=EVIDENCE:
  raise ValueError('vnc_start_verified_absence_required')
 _,_,urls=context(session,'windows')
 # No silent re-uninstall or replay. A newer command/delivery invalidates this baseline.
 for task in ['executeCommand','managePlugin']:
  items,_=complete_task_list(session,urls[0],'windows',task)
  if any(stamp(x['created_at'])>stamp(b['server_created_at']) for x in items):
   raise ValueError('vnc_start_state_changed_since_absence')
 cr=configured_requirement('windows',r['campaign_id']);base=urls[1].rsplit('/agents/',1)[0]
 checked_config(get(session,base+'/remote-data/config/'+r['agent_id']),cr)
 infos=get(session,base+'/remote-data/info/'+r['agent_id'])
 found=[x for x in infos if x.get('agent_id')==r['agent_id'] and x.get('protocol')=='vnc'] if isinstance(infos,list) else []
 if len(found)!=1 or found[0].get('is_service_running') is not False:raise ValueError('vnc_start_existing_service_or_unknown')
 out=ssh_worker._run('lab','sha256sum '+BINARY,sudo=True)
 if out['exit_code']!=0 or not out['stdout'].startswith(BINARY_SHA+'  '):raise ValueError('vnc_start_supplied_binary_changed')
 return {'historical_verified_absence':True,'no_newer_agent_command_or_delivery':True,
  'current_service_running':False,'supplied_binary_sha256':BINARY_SHA,'current_registry_recheck_performed':False}
