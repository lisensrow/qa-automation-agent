"""Exact reviewed historical retirement, not generic pending-task suppression.

Native status remains progress. An immutable operator-reviewed primary proof
requires agent not-running feedback AND an elapsed delivery window with intact
cards/results. Any changed card, other task/agent/OS, missing/changed proof or
new unresolved command still fails closed. No dispatch or journal promotion.
"""
from datetime import datetime,timezone
import hashlib,json
import job_store
JOB='20261016-130954-777e672a'
CASE='tc-4d093259'
EVIDENCE='ev-482977d956e7'
SHA='7e8d61e37b63e06c92b565929719042859805dcb04478c3d444ec68f090e0003'
AGENT='71724f3b-41b9-449b-9075-1dd6c8e1c2df'
CI='c0951a10-3e93-58f9-9468-4702734b417f'
IDS=frozenset(('6b39f0a3-1edb-4713-9528-f188acaf87d4','da3121fa-e8de-49b3-ac0d-efb57d31d8fd',
 '2f315b00-68a7-44d7-8ccb-7b570ab26895','978bfb13-b5fe-4ab2-9f73-2dd32bea8568',
 'a66cd6e9-9b52-4ce3-b61c-d25ae292a5c7','a3d02561-1652-4f6c-be04-fa062ae32b47',
 'b3832adb-9843-4bf2-afca-a510a5a0c65b','8984ad61-7c5d-4367-9c54-a0e03dd0fcd8'))
KEYS=['id','agent_id','name','enabled','period','start_ts','end_ts','additional_params','context_params',
 'run_as_user','status','created_by','created_at','updated_at','last_processed_at','ttl']
def fingerprint(item):
 return hashlib.sha256(json.dumps({k:item.get(k) for k in KEYS},sort_keys=True,separators=(',',':')).encode()).hexdigest()
def stamp(value):
 d=datetime.fromisoformat(value.replace('Z','+00:00'))
 return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)
def validate_retired_item(name,item,observed_at=None):
 try:
  if (name!='windows' or not isinstance(item,dict) or item.get('id') not in IDS
   or item.get('agent_id')!=AGENT or item.get('name')!='executeCommand'
   or item.get('period') is not None or item.get('status')!='progress'
   or item.get('enabled')!=0 or type(item.get('enabled')) is not int):return False
  at=observed_at or datetime.now(timezone.utc)
  if at.tzinfo is None or stamp(item['end_ts'])>=at:return False
  job=job_store.get_job(JOB)
  case=next(c for c in job['test_cases'] if c['case_id']==CASE)
  ev=next(e for e in case['evidence'] if e['evidence_id']==EVIDENCE)
  if (ev.get('source')!='operator_native_retirement_review' or ev.get('type')!='operator_exact_legacy_retirement_review'
   or ev.get('execution_status')!='observed' or hashlib.sha256(ev['value'].encode()).hexdigest()!=SHA):return False
  b=json.loads(ev['value'])
  if (b['schema']!='uqa.exact-legacy-command-retirement.v1' or b['target']!='windows'
   or b['ci_id']!=CI or b['agent_id']!=AGENT or b['core_version']!='1.3.27' or b['fingerprint_keys']!=KEYS
   or b['all_eight_expired_disabled_and_agent_not_running'] is not True
   or b['terminal_status_not_forged'] is not True or b['card_result_preservation_verified'] is not True
   or len(b['rows'])!=8 or {r['task_id'] for r in b['rows']}!=IDS):return False
  row=next(r for r in b['rows'] if r['task_id']==item['id'])
  return (row['agent_id']==AGENT and row['agent_reports_not_running'] is True
   and row['card_retained'] is True and row['prior_result_preserved'] is True
   and row['enabled']==0 and row['server_status']=='progress' and row['end_ts']==item['end_ts']
   and row['task_fingerprint']==fingerprint(item) and set(row['changed_fields'])<={'end_ts','updated_at'})
 except (ValueError,TypeError,KeyError,AttributeError,StopIteration,OSError):return False
