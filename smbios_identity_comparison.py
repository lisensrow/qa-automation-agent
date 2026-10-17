"""Eight declared raw DMI fields from owned recorded payloads; never whole hardware PASS."""
from copy import deepcopy
from datetime import datetime,timezone
import hashlib,json,re
import job_store
import smbios_os_baseline as baseline
from command_probe_contract import target,validate_target_state,CORE
from command_stage_native import context,read_json
from operation_journal import list_operations,_fingerprint
from plugin_preparation import stamp
from os_identity_comparison import _ref,_load,_same_full
TOOL='browser_compare_owned_dmi_identity_semantic'
PROFILE='owned-dmi-identity-recorded-raw-v1'
MAPPING={'system_manufacturer':'data.system_information[].manufacturer','system_product_name':'data.system_information[].product_name',
 'system_product_version':'data.system_information[].version','bios_vendor':'data.bios_information[].vendor','bios_version':'data.bios_information[].version',
 'baseboard_manufacturer':'data.baseboard_information[].manufacturer','baseboard_product':'data.baseboard_information[].product','baseboard_version':'data.baseboard_information[].version'}
LIMITS={k:False for k in ['normative_product_contract_verified','all_dmi_structures_verified','cpu_or_dimm_verified','hardware_ui_verified',
 'live_current_state_verified','normalization_applied','developer_confirmed_bug','full_case_passed','business_pass','resend_authorized','mutation_executed']}
STAGES={'scope','source_proofs','time_window','observed_context','target_readiness','native_payload','audit_payload','raw_comparison'}
def digest(data):return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def requirement(name,campaign,native_ref,audit_ref):
 if name not in baseline.FIELDS or type(campaign)!=str or not re.fullmatch('[a-z0-9-]{1,80}',campaign):raise ValueError('dmi_pair_scope')
 t=target(name)
 return {'type':'owned_dmi_identity_raw_comparison','stand':'lab','locked':True,'action_profile':'read_only','profile_id':PROFILE,'campaign_id':campaign,
  'target':name,**{k:t[k] for k in ['ci_name','ci_id','agent_id']},'core_version':CORE,'native_source':_ref(native_ref),'audit_source':_ref(audit_ref),
  'raw_mapping':dict(MAPPING),'max_pair_seconds':1800,'recorded_pair_only':True,**LIMITS}
def validate_context(job,cid,args):
 if not isinstance(job,dict) or len(job.get('test_cases',[]))!=1:raise ValueError('one_owned_dmi_case')
 c=job['test_cases'][0];r=c.get('requirement') or {}
 expected=requirement(r.get('target'),r.get('campaign_id'),r.get('native_source'),r.get('audit_source'))
 if r!=expected or cid!=c['case_id'] or args!={'target':r['target']} or job.get('stand')!='lab' or job.get('job_type') not in {'manual','regression'} or job.get('resources') or job.get('status')!='running' or c.get('status')!='running':raise ValueError('locked_dmi_pair_required')
 if not all(r[k] in job.get('request','') for k in ['ci_name','ci_id','agent_id','profile_id']):raise ValueError('original_dmi_pair_request')
 return r
def source_proofs(r):
 nj,nc,ne,nb=_load(r['native_source']);aj,ac,ae,ab=_load(r['audit_source']);name=r['target'];t=target(name)
 from endpoint_metadata import requirement as native_requirement,READ
 from plugin_audit_profiles import profile,scopes,stages_for,validate_prior_delivery,validate_context as validate_audit
 if nc['requirement']!=native_requirement(name,nc['requirement'].get('campaign_id'),baseline.PROFILE) or ne['source']!='uqa_tool' or nb.get('tool')!=READ or nb.get('arguments')!={'target':name}:raise ValueError('own_native_source')
 n=nb['result'];a=ab['result'];ar=ac['requirement']
 if ae['source']!='uqa_tool' or ab.get('tool')!='browser_inspect_pinned_agent_audit_semantic' or ab.get('arguments')!={'ci_name':t['ci_name'],'agent_id':t['agent_id'],'task_id':a.get('task_id')}:raise ValueError('own_audit_source')
 for j,e,v in [(nj,ne,n),(aj,ae,a)]:
  ops=list_operations(j['job_id']);matching=[o for o in ops if o['verification'].get('evidence_id')==e['evidence_id']]
  stages=j['test_cases'][0]['requirement']['operation_stages']
  for op in ops:
   declared=[s for s in stages if s['stage_id']==op['stage_id']]
   if len(declared)!=1 or op['case_id']!=j['test_cases'][0]['case_id'] or any(op.get(k)!=declared[0][k] for k in ['workflow_id','resource_key','tool']) or op.get('arguments_fingerprint')!=_fingerprint(declared[0]['arguments']) or op.get('verification_fingerprint')!=_fingerprint(declared[0]['verification']):raise ValueError('original_declared_operation_required')
  if len(matching)!=1 or any(o['status']!='verified' for o in ops) or matching[0]['verification'].get('identifier_value')!=v['task_id'] or matching[0]['verification'].get('postcondition_verified') is not True:raise ValueError('own_verified_operation')
  if v.get('native_result_verified') is not True or v.get('ci_id')!=t['ci_id'] or v.get('agent_id')!=t['agent_id'] or v.get('machine_uid')!=t['ci_id'] or v.get('task_status')!='success':raise ValueError('native_target_binding')
 if len(list_operations(nj['job_id']))!=1 or len(list_operations(aj['job_id'])) not in {1,2}:raise ValueError('bounded_owned_operations')
 ncycle_e=next(e for e in nc['evidence'] if e['type']=='model_endpoint_metadata_cycle');ncycle=json.loads(ncycle_e['value'])
 acycle=json.loads(next(e for e in ac['evidence'] if e['type']=='model_current_dmi_audit_capture')['value'])
 if ncycle.get('completed') is not True or ncycle['canonical_report']['read_evidence_id']!=ne['evidence_id'] or not n['summary']['dmi_query_complete'] or n['summary']['observation_status']=='BLOCKED' or a.get('task_name')!='smbiosAudit' or a.get('fresh_result') is not True or a.get('identity_verified') is not True:raise ValueError('verified_own_capture_required')
 # Data evidence and the model's terminal prose are independent assertions. A false
 # delivery claim must remain a failed report, not invalidate or resend a verified
 # already-created task. Never promote that failure to a completed workflow.
 canonical=acycle.get('canonical_report') or {};final=acycle.get('final') or {}
 if canonical.get('report_type')!='locked_plugin_subset' or canonical.get('verdict')!='BLOCKED' or canonical.get('task_id')!=a['task_id'] or canonical.get('source_evidence_ids')!=[ae['evidence_id']] or canonical.get('summary')!=a['audit_data_summary']:raise ValueError('original_canonical_receipt_required')
 final_ok=final.get('own_main_audit_verified') is True and final.get('whole_data_hash_observed') is True and all(final.get(k) is False for k in ['independent_value_comparison_done','plugin_delivered','full_case_passed']) and final.get('legacy_verdict')=='BLOCKED'
 if type(acycle.get('completed'))!=bool or acycle['completed']!=final_ok or (not final_ok and acycle.get('error')!='AssertionError:'):raise ValueError('explicit_terminal_report_failure_required')
 plans=[e for e in nc['evidence'] if e['type']=='operator_dmi_baseline_scope' and e['source']=='authorized_lab_operator']
 if len(plans)!=1:raise ValueError('prebaseline_plan_required')
 plan=json.loads(plans[0]['value'])['plan']
 wanted_plan={'mapping':MAPPING,'comparison_kind':'predeclared_raw_identity_hypothesis_not_product_contract','plugin_array_cardinality':1,'max_pair_seconds':1800,'normalization_allowed':False,
  'unknown_placeholder_tokens':sorted(baseline.PLACEHOLDERS),'fresh_audit_minimum_known_fields':['system_manufacturer','system_product_name','bios_vendor','bios_version'],'all_dmi_structures_verified':False,'full_case_passed':False}
 if plan!=wanted_plan or stamp(plans[0]['created_at'])>stamp(n['server_created_at']):raise ValueError('prebaseline_plan_changed')
 if set(plan['fresh_audit_minimum_known_fields'])&set(n['summary']['unknown_fields']):raise ValueError('minimum_known_anchors')
 # Revalidate the original immutable audit scope without changing its finished state.
 shadow=deepcopy(aj);shadow['status']='running';shadow['test_cases'][0]['status']='running';validate_audit(shadow,ac['case_id']);validate_prior_delivery(ar)
 audit_scope,_=scopes(ar)
 if ar['pinned_audit_task']['task_name']!='smbiosAudit' or ar['expected_profile']!=profile('smbiosAudit') or ar['operation_stages']!=stages_for(ar) or ar.get('delivery_authorized_this_run') is not False or any(o['stage_id']=='deliver-plugin' for o in list_operations(aj['job_id'])):raise ValueError('unchanged_legacy_no_delivery')
 cp=ar['dmi_comparison_preparation']
 wanted={'baseline_ref':{'job_id':nj['job_id'],'case_id':nc['case_id'],'cycle_evidence_id':ncycle_e['evidence_id'],'read_evidence_id':ne['evidence_id']},'baseline_plan_evidence_id':plans[0]['evidence_id'],
  'native_values_sha256':n['summary']['values_sha256'],'native_stdout_sha256':n['result_sha256'],'mapping':MAPPING,'expected_raw_fields':n['summary']['native_values'],'unknown_fields':n['summary']['unknown_fields'],
  'unknown_placeholder_tokens':sorted(baseline.PLACEHOLDERS),'plugin_array_cardinality':1,'max_pair_seconds':1800,'comparison_kind':plan['comparison_kind'],'normalization_allowed':False,'all_dmi_structures_verified':False,'full_case_passed':False}
 prep=[e for e in ac['evidence'] if e['type']=='operator_dmi_audit_preparation' and e['source']=='authorized_lab_operator']
 if cp!=wanted or acycle['comparison_preparation']!=cp or len(prep)!=1 or json.loads(prep[0]['value'])['comparison']!=cp or stamp(ne['created_at'])>stamp(prep[0]['created_at']) or stamp(prep[0]['created_at'])>stamp(a['server_created_at']):raise ValueError('preaudit_raw_rule_changed')
 if not re.fullmatch('[0-9a-f]{64}',a.get('audit_data_summary',{}).get('data_sha256','')) or acycle.get('first_entire_data_hash_captured_by_model') is not True:raise ValueError('original_model_whole_data_hash_required')
 return n,a,cp,{'source_audit_workflow_completed':acycle['completed'],'source_audit_final_report_accepted':final_ok}
def project(data):
 if not isinstance(data,dict):raise ValueError('dmi_data_object')
 out={}
 for key,path in MAPPING.items():
  category,field=path.removeprefix('data.').split('[].');items=data.get(category)
  out[key]=items[0].get(field) if type(items)==list and len(items)==1 and type(items[0])==dict else None
 return out
def compare_fields(expected,actual):
 if set(expected)!=set(MAPPING) or set(actual)!=set(MAPPING):raise ValueError('eight_fields_required')
 rows=[]
 for key in sorted(MAPPING):
  a,b=expected[key],actual[key]
  if any(v is not None and (type(v)!=str or len(v)>512 or any(ord(c)<32 for c in v)) for v in [a,b]):raise ValueError('bounded_raw_dmi_strings')
  unknown=any(v is None or not v.strip() or v.strip().casefold() in baseline.PLACEHOLDERS for v in [a,b])
  rows.append({'field':key,'plugin_path':MAPPING[key],'expected_raw':a,'actual_raw':b,'status':'UNKNOWN' if unknown else 'RAW_EQUAL' if a==b else 'RAW_DIFFERENT'})
 counts={k:sum(r['status']==v for r in rows) for k,v in [('raw_equal_fields','RAW_EQUAL'),('raw_different_fields','RAW_DIFFERENT'),('unknown_fields','UNKNOWN')]}
 return {'rows':rows,'field_count':8,**counts,'raw_hypothesis_status':'BLOCKED' if counts['unknown_fields'] else 'MISMATCH' if counts['raw_different_fields'] else 'MATCH'}
def blocked(stage):
 if stage not in STAGES:raise ValueError('safe_dmi_stage')
 return {'error':'owned_dmi_pair_unavailable','profile_id':PROFILE,'blocked_stage':stage,'independent_raw_value_comparison_done':False,'new_agent_tasks':0,**LIMITS}
def compact(value):
 try:
  if value.get('error')=='owned_dmi_pair_unavailable':return blocked(value['blocked_stage']) if all(type(value.get(k)) is type(v) and value[k]==v for k,v in blocked(value['blocked_stage']).items()) else {}
  if value.get('profile_id')!=PROFILE or value.get('target') not in baseline.FIELDS or any(value.get(k) is not v for k,v in LIMITS.items()):return {}
  if any(type(value.get(k))!=bool for k in ['source_audit_workflow_completed','source_audit_final_report_accepted']) or value['source_audit_workflow_completed']!=value['source_audit_final_report_accepted']:return {}
  flags={'recorded_pair_only':True,'same_native_payload_as_original_model_read':True,'same_entire_audit_data_as_original_model_read':True,'independent_raw_value_comparison_done':True}
  if any(value.get(k) is not v for k,v in flags.items()) or type(value.get('new_agent_tasks'))!=int or value['new_agent_tasks']!=0 or value.get('full_source_case_status')!='BLOCKED':return {}
  rows=value['rows'];assert type(rows)==list and len(rows)==8 and len({r['field'] for r in rows})==8
  calc=compare_fields({r['field']:r['expected_raw'] for r in rows},{r['field']:r['actual_raw'] for r in rows})
  if any(value.get(k)!=v for k,v in calc.items()) or any(type(value.get(k))!=int for k in ['field_count','raw_equal_fields','raw_different_fields','unknown_fields']):return {}
  if type(value.get('pair_seconds')) not in {int,float} or not -5<=value['pair_seconds']<=1800:return {}
  if abs((stamp(value['audit_observed_at'])-stamp(value['native_observed_at'])).total_seconds()-value['pair_seconds'])>0.000001:return {}
  for k in ['native_payload_sha256','audit_data_sha256']:
   if not re.fullmatch('[0-9a-f]{64}',str(value.get(k))):return {}
  for k in ['native_source','audit_source']:_ref(value[k])
  keys=['profile_id','target','rows','field_count','raw_equal_fields','raw_different_fields','unknown_fields','raw_hypothesis_status',*flags,*LIMITS,
   'source_audit_workflow_completed','source_audit_final_report_accepted','full_source_case_status','new_agent_tasks','native_source','audit_source','native_task_id','audit_task_id','native_observed_at','audit_observed_at','pair_seconds','native_payload_sha256','audit_data_sha256','read_at']
  out={k:deepcopy(value[k]) for k in keys};return out if len(json.dumps(out,ensure_ascii=False).encode())<=18000 else {}
 except (ValueError,KeyError,TypeError,AssertionError,AttributeError):return {}
def inspect(session,args,jid,cid):
 stage='scope'
 try:
  r=validate_context(job_store.get_job(jid),cid,args);name=r['target'];stage='source_proofs';n,a,cp,source_flags=source_proofs(r)
  stage='time_window';gap=(stamp(a['processed_at'])-stamp(n['processed_at'])).total_seconds()
  if not -5<=gap<=1800:raise ValueError('frozen_dmi_pair_expired')
  stage='observed_context';_,ci,urls=context(session,name)
  stage='target_readiness';validate_target_state(name,ci,read_json(session,urls[1]))
  stage='native_payload';env=_same_full(read_json(session,urls[0]+'/'+n['task_id']+'/full'),n,'executeCommand',r);data=env.get('data')
  if isinstance(data,dict) and isinstance(data.get('stdout'),str):stdout,code,stderr=data['stdout'],data.get('errorlevel'),data.get('stderr')
  else:stdout,code,stderr=env.get('result'),env.get('error_code'),env.get('error_msg')
  from powershell_streams import inspect_stderr
  if type(stdout)!=str or len(stdout.encode())>65536 or code not in (0,'0') or inspect_stderr(stderr)['kind'] not in {'empty','progress_only'}:raise ValueError('native_dmi_output_invalid')
  nh=hashlib.sha256(stdout.encode()).hexdigest()
  if nh!=n['result_sha256'] or baseline.summarize(json.loads(stdout.lstrip('\ufeff')),name)!=n['summary']:raise ValueError('native_original_payload_changed')
  stage='audit_payload';aenv=_same_full(read_json(session,urls[0]+'/'+a['task_id']+'/full'),a,'smbiosAudit',r);data=aenv.get('data')
  if type(data)!=dict or aenv.get('result')!='success' or len(json.dumps(data,ensure_ascii=False).encode())>1000000:raise ValueError('audit_dmi_data_shape')
  ah=digest(data)
  if ah!=a['audit_data_summary']['data_sha256']:raise ValueError('original_model_full_data_hash_changed')
  stage='raw_comparison';out={**compare_fields(cp['expected_raw_fields'],project(data)),**LIMITS,**source_flags,'profile_id':PROFILE,'target':name,
   'recorded_pair_only':True,'same_native_payload_as_original_model_read':True,'same_entire_audit_data_as_original_model_read':True,'independent_raw_value_comparison_done':True,
   'full_source_case_status':'BLOCKED','new_agent_tasks':0,'native_source':r['native_source'],'audit_source':r['audit_source'],'native_task_id':n['task_id'],'audit_task_id':a['task_id'],
   'native_observed_at':n['processed_at'],'audit_observed_at':a['processed_at'],'pair_seconds':gap,'native_payload_sha256':nh,'audit_data_sha256':ah,'read_at':datetime.now(timezone.utc).isoformat()}
  if not compact(out):raise ValueError('bounded_dmi_projection_failed')
  return out
 except (ValueError,KeyError,TypeError,AttributeError,StopIteration,OverflowError,OSError):return blocked(stage)
