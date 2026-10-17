"""Compare owned recorded raw OS fields, NOT a normative product naming oracle."""
from copy import deepcopy
from datetime import datetime,timezone
from uuid import UUID
import hashlib,json,re
import job_store
from command_probe_contract import target,validate_target_state,CORE
from command_stage_native import context,read_json
from operation_journal import list_operations
from plugin_preparation import stamp
import os_identity_baseline as baseline
TOOL='browser_compare_owned_os_identity_semantic'
PROFILE='owned-os-identity-recorded-raw-v1'
RULES={'windows':{'data.host_name':'native.Win32_OperatingSystem.CSName_exact'},
 'astra':{'data.host_name':'native.socket.gethostname_exact','data.os.kernel_version':'native.uname.release_exact'}}
LIMITS={'product_naming_contract_verified':False,'all_os_fields_verified':False,'users_or_volumes_verified':False,
 'os_ui_verified':False,'live_current_state_verified':False,'developer_confirmed_bug':False,'full_case_passed':False,'business_pass':False}
def _ref(ref):
 if type(ref) not in (list,tuple) or len(ref)!=3 or any(type(x)!=str for x in ref):raise ValueError('owned_pair_reference_shape')
 if not all(re.fullmatch(p,v) for p,v in zip([r'[0-9]{8}-[0-9]{6}-[0-9a-f]{8}',r'tc-[0-9a-f]{8}',r'ev-[0-9a-f]{12}'],ref)):raise ValueError('owned_pair_reference_format')
 return list(ref)
def requirement(name,campaign,os_ref,audit_ref,digest_ref):
 if name not in RULES or not isinstance(campaign,str) or not re.fullmatch('[a-z0-9-]{1,80}',campaign):raise ValueError('owned_pair_campaign_target')
 t=target(name)
 return {'type':'owned_os_identity_raw_comparison','stand':'lab','locked':True,'action_profile':'read_only','profile_id':PROFILE,'campaign_id':campaign,
  'target':name,**{k:t[k] for k in ['ci_name','ci_id','agent_id']},'core_version':CORE,'os_meta_source':_ref(os_ref),'audit_source':_ref(audit_ref),
  'operator_digest_source':_ref(digest_ref),'raw_mapping':deepcopy(RULES[name]),'max_pair_seconds':1800,'recorded_pair_only':True,'normalization_allowed':False,**LIMITS}
def validate_context(job,cid,args):
 if not isinstance(job,dict) or len(job.get('test_cases',[]))!=1:raise ValueError('single_owned_pair_case')
 c=job['test_cases'][0];r=c.get('requirement') or {}
 expected=requirement(r.get('target'),r.get('campaign_id'),r.get('os_meta_source'),r.get('audit_source'),r.get('operator_digest_source'))
 if c.get('case_id')!=cid or r!=expected or args!={'target':r['target']} or job.get('stand')!='lab' or job.get('job_type') not in {'manual','regression'} or job.get('status')!='running' or c.get('status')!='running' or job.get('resources'):raise ValueError('locked_owned_pair_scope')
 if not all(r[k] in job.get('request','') for k in ['ci_name','ci_id','agent_id','profile_id']):raise ValueError('owned_pair_original_request')
 return r
def _load(ref):
 jid,cid,eid=_ref(ref);j=job_store.get_job(jid);c=next(c for c in j['test_cases'] if c['case_id']==cid);e=next(e for e in c['evidence'] if e.get('evidence_id')==eid)
 if j.get('stand')!='lab' or j.get('status')=='running' or e.get('execution_status') not in {'observed','executed'}:raise ValueError('finished_owned_source_required')
 return j,c,e,json.loads(e['value'])
def source_proofs(r):
 name=r['target'];t=target(name)
 oj,oc,oe,ob=_load(r['os_meta_source']);aj,ac,ae,ab=_load(r['audit_source']);dj,dc,de,cap=_load(r['operator_digest_source'])
 from endpoint_metadata import requirement as endpoint_requirement,OS_IDENTITY,READ
 if oc['requirement']!=endpoint_requirement(name,oc['requirement'].get('campaign_id'),OS_IDENTITY) or oe['source']!='uqa_tool' or ob.get('tool')!=READ or ob.get('arguments')!={'target':name}:raise ValueError('owned_native_identity_source')
 os=ob['result'];audit=ab['result']
 if ae['source']!='uqa_tool' or ab.get('tool')!='browser_inspect_pinned_agent_audit_semantic' or ab.get('arguments')!={'ci_name':t['ci_name'],'agent_id':t['agent_id'],'task_id':audit.get('task_id')}:raise ValueError('owned_os_audit_source')
 for j,e,v in [(oj,oe,os),(aj,ae,audit)]:
  ops=list_operations(j['job_id'])
  if len(ops)!=1 or ops[0]['status']!='verified' or ops[0]['verification'].get('evidence_id')!=e['evidence_id'] or ops[0]['verification'].get('identifier_value')!=v.get('task_id'):raise ValueError('owned_pair_verified_operation')
  if v.get('native_result_verified') is not True or v.get('ci_id')!=t['ci_id'] or v.get('agent_id')!=t['agent_id'] or v.get('machine_uid')!=t['ci_id'] or v.get('task_status')!='success' or str(UUID(v.get('task_id')))!=v['task_id']:raise ValueError('owned_pair_native_identity')
 oscycle=json.loads(next(e for e in oc['evidence'] if e['type']=='model_endpoint_metadata_cycle')['value'])
 auditcycle=json.loads(next(e for e in ac['evidence'] if e['type']=='model_current_os_audit_capture')['value'])
 if oscycle['completed'] is not True or auditcycle['completed'] is not True or os['summary']['os_query_complete'] is not True or audit.get('task_name')!='osAudit' or audit['fresh_result'] is not True or audit['identity_verified'] is not True:raise ValueError('owned_pair_completed_capture')
 plans=[e for e in oc['evidence'] if e['type']=='operator_os_identity_scope' and e['source']=='authorized_lab_operator']
 if len(plans)!=1 or json.loads(plans[0]['value']).get('planned_future_comparison_field_rule')!=RULES[name] or json.loads(plans[0]['value']).get('normalization_allowed') is not False or stamp(plans[0]['created_at'])>stamp(os['server_created_at']):raise ValueError('raw_mapping_not_declared_before_native_query')
 ar=ac['requirement'];cp=ar['current_os_comparison_preparation']
 from agent_audit_runtime import validate_baseline
 from audit_operation_recovery import stages_for
 validate_baseline(aj,ar)
 scope={'ci_name':t['ci_name'],'agent_id':t['agent_id'],'core_version':CORE,'task_name':'osAudit'}
 if ar.get('type')!='pinned_agent_audit' or ar.get('locked') is not True or ar.get('pinned_audit_task')!=scope or ar.get('operation_stages')!=stages_for(scope,t['ci_id']) or cp!=auditcycle['comparison_preparation']:raise ValueError('unchanged_legacy_audit_source')
 expected={'data.host_name':os['summary']['native_values']['host_name']}
 if name=='astra':expected['data.os.kernel_version']=os['summary']['native_values']['kernel_release']
 prep=[e for e in ac['evidence'] if e['type']=='operator_os_pair_preparation' and e['source']=='authorized_lab_operator']
 baseline_ref={'job_id':oj['job_id'],'case_id':oc['case_id'],'evidence_id':next(e['evidence_id'] for e in oc['evidence'] if e['type']=='model_endpoint_metadata_cycle'),'read_evidence_id':oe['evidence_id']}
 wanted={'baseline_ref':baseline_ref,'native_values_sha256':os['summary']['values_sha256'],'native_result_sha256':os['result_sha256'],'mapping':RULES[name],'expected_raw_fields':expected,
  'max_pair_seconds':1800,'normalization_allowed':False,'product_naming_contract_verified':False,'comparison_kind':'predeclared_raw_field_hypothesis_not_business_oracle','full_case_passed':False}
 if cp!=wanted or len(prep)!=1 or json.loads(prep[0]['value']).get('comparison')!=cp or stamp(prep[0]['created_at'])>stamp(audit['server_created_at']) or stamp(oe['created_at'])>stamp(prep[0]['created_at']):raise ValueError('raw_pair_rule_not_predeclared')
 flags={'recorded_task_only':True,'live_current_state_verified':False,'full_payload_unchanged_since_original_model_read_proved':False,'first_full_data_hash_capture_by_operator':True,
  'model_selected_capture':False,'independent_value_comparison_done':False,'product_naming_contract_verified':False,'normalization_allowed':False,'product_mutation_executed':False,'new_agent_tasks':0,'full_case_passed':False}
 if de.get('type')!='operator_recorded_os_full_digest' or de.get('source')!='operator_primary_os_full_digest' or list_operations(dj['job_id']) or any(type(cap.get(k)) is not type(v) or cap[k]!=v for k,v in flags.items()):raise ValueError('explicit_operator_digest_preparation_required')
 for k,v in {'target':name,'source_job_id':aj['job_id'],'source_case_id':ac['case_id'],'source_read_evidence_id':ae['evidence_id'],'task_id':audit['task_id'],'agent_id':t['agent_id'],'ci_id':t['ci_id'],'server_created_at':audit['server_created_at'],'processed_at':audit['processed_at']}.items():
  if cap.get(k)!=v:raise ValueError('operator_digest_source_link')
 if not re.fullmatch('[0-9a-f]{64}',str(cap.get('data_sha256'))) or set(cap.get('projected_raw_fields',{}))!=set(RULES[name]) or stamp(cap['captured_at'])<stamp(audit['read_at']):raise ValueError('operator_digest_shape_time')
 return os,audit,cp,cap
def compare_fields(expected,actual,name):
 if name not in RULES or set(expected)!=set(RULES[name]) or set(actual)!=set(expected):raise ValueError('raw_field_scope')
 rows=[]
 for field in sorted(expected):
  a,b=expected[field],actual[field]
  if any(v is not None and (type(v)!=str or len(v)>2048) for v in [a,b]):raise ValueError('raw_field_value_shape')
  status='UNKNOWN' if any(v is None or not v.strip() for v in [a,b]) else 'RAW_EQUAL' if a==b else 'RAW_DIFFERENT'
  rows.append({'field':field,'expected_raw':a,'actual_raw':b,'status':status})
 counts={k:sum(x['status']==v for x in rows) for k,v in [('raw_equal_fields','RAW_EQUAL'),('raw_different_fields','RAW_DIFFERENT'),('unknown_fields','UNKNOWN')]}
 status='BLOCKED' if counts['unknown_fields'] else 'MISMATCH' if counts['raw_different_fields'] else 'MATCH'
 return {'raw_hypothesis_status':status,'rows':rows,'field_count':len(rows),**counts}
def compact(value):
 if not isinstance(value,dict) or value.get('profile_id')!=PROFILE or value.get('target') not in RULES or any(value.get(k) is not v for k,v in LIMITS.items()):return {}
 expected_flags={'recorded_pair_only':True,'normalization_applied':False,'resend_authorized':False,'independent_raw_value_comparison_done':True,'same_os_payload_as_original_read':True,'same_audit_data_as_operator_capture':True,'same_audit_full_payload_as_original_model_read_proved':False}
 if any(value.get(k) is not v for k,v in expected_flags.items()) or value.get('new_agent_tasks')!=0 or value.get('full_source_case_status')!='BLOCKED' or value.get('comparison_scope')!='predeclared_raw_mapping_hypothesis_not_product_contract':return {}
 try:
  rows=value['rows'];assert isinstance(rows,list) and len(rows)==len(RULES[value['target']]) and len({r['field'] for r in rows})==len(rows)
  calculated=compare_fields({r['field']:r['expected_raw'] for r in rows},{r['field']:r['actual_raw'] for r in rows},value['target'])
  if any(value.get(k)!=v for k,v in calculated.items()):return {}
  if any(type(value.get(k))!=int for k in ['field_count','raw_equal_fields','raw_different_fields','unknown_fields','new_agent_tasks']):return {}
  for key in ['os_meta_source','audit_source','operator_digest_source']:_ref(value[key])
  if type(value['pair_seconds']) not in (float,int) or not -5<=value['pair_seconds']<=1800:return {}
  if abs((stamp(value['audit_observed_at'])-stamp(value['os_observed_at'])).total_seconds()-value['pair_seconds'])>0.000001 or stamp(value['read_at'])<stamp(value['operator_digest_capture_at']):return {}
  if any(not re.fullmatch('[0-9a-f]{64}',str(value.get(k))) for k in ['os_payload_sha256','audit_data_sha256']):return {}
  keys=['profile_id','target','comparison_scope','raw_hypothesis_status','rows','field_count','raw_equal_fields','raw_different_fields','unknown_fields',*LIMITS,*expected_flags,
   'new_agent_tasks','full_source_case_status','os_meta_source','audit_source','operator_digest_source','os_task_id','audit_task_id','os_observed_at','audit_observed_at','pair_seconds','read_at','os_payload_sha256','audit_data_sha256','operator_digest_capture_at']
  result={k:deepcopy(value[k]) for k in keys}
  return result if len(json.dumps(result,ensure_ascii=False).encode())<=12000 else {}
 except (ValueError,TypeError,KeyError,AssertionError):return {}
def _same_full(full,proof,name,r):
 env=full.get('result')
 if not isinstance(env,dict) or full.get('id')!=proof['task_id'] or full.get('agent_id')!=r['agent_id'] or full.get('name')!=name or full.get('status')!='success' or full.get('created_at')!=proof['server_created_at'] or env.get('machine_uid')!=r['ci_id'] or env.get('processed_at')!=proof['processed_at']:raise ValueError('same_recorded_os_task_required')
 return env
def inspect(session,args,jid,cid):
 try:
  r=validate_context(job_store.get_job(jid),cid,args);os,audit,cp,cap=source_proofs(r);name=r['target']
  gap=(stamp(audit['processed_at'])-stamp(os['processed_at'])).total_seconds()
  if not -5<=gap<=r['max_pair_seconds']:raise ValueError('raw_pair_time_window')
  _,ci,urls=context(session,name);validate_target_state(name,ci,read_json(session,urls[1]))
  env=_same_full(read_json(session,urls[0]+'/'+os['task_id']+'/full'),os,'executeCommand',r);data=env.get('data')
  if isinstance(data,dict) and isinstance(data.get('stdout'),str):stdout,code,stderr=data['stdout'],data.get('errorlevel'),data.get('stderr')
  else:stdout,code,stderr=env.get('result'),env.get('error_code'),env.get('error_msg')
  from powershell_streams import inspect_stderr
  if not isinstance(stdout,str) or len(stdout.encode())>262144 or code not in (0,'0') or inspect_stderr(stderr)['kind'] not in {'empty','progress_only'}:raise ValueError('os_identity_full_output_invalid')
  os_sha=hashlib.sha256(stdout.encode()).hexdigest()
  if os_sha!=os['result_sha256'] or baseline.summarize(json.loads(stdout.lstrip('\ufeff')),name)!=os['summary']:raise ValueError('os_identity_original_data_changed')
  aenv=_same_full(read_json(session,urls[0]+'/'+audit['task_id']+'/full'),audit,'osAudit',r);data=aenv.get('data')
  if not isinstance(data,dict) or not isinstance(data.get('os'),dict) or aenv.get('result')!='success' or len(json.dumps(data,ensure_ascii=False).encode())>1000000:raise ValueError('os_audit_data_shape')
  audit_sha=hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
  if audit_sha!=cap['data_sha256'] or data.get('host_name')!=audit['host_name'] or {k:data['os'].get(k) for k in audit['os_subset']}!=audit['os_subset']:raise ValueError('os_audit_operator_digest_or_original_subset_changed')
  projected={'data.host_name':data.get('host_name')}
  if name=='astra':projected['data.os.kernel_version']=data['os'].get('kernel_version')
  if projected!=cap['projected_raw_fields']:raise ValueError('os_audit_projection_changed')
  out={**compare_fields(cp['expected_raw_fields'],projected,name),'profile_id':PROFILE,'target':name,'comparison_scope':'predeclared_raw_mapping_hypothesis_not_product_contract',
   **LIMITS,'recorded_pair_only':True,'normalization_applied':False,'resend_authorized':False,'independent_raw_value_comparison_done':True,
   'same_os_payload_as_original_read':True,'same_audit_data_as_operator_capture':True,'same_audit_full_payload_as_original_model_read_proved':False,
   'new_agent_tasks':0,'mutation_executed':False,'full_source_case_status':'BLOCKED','os_meta_source':r['os_meta_source'],'audit_source':r['audit_source'],'operator_digest_source':r['operator_digest_source'],
   'os_task_id':os['task_id'],'audit_task_id':audit['task_id'],'os_observed_at':os['processed_at'],'audit_observed_at':audit['processed_at'],'pair_seconds':gap,
   'read_at':datetime.now(timezone.utc).isoformat(),'os_payload_sha256':os_sha,'audit_data_sha256':audit_sha,'operator_digest_capture_at':cap['captured_at']}
  if not compact(out):raise ValueError('raw_pair_projection_rejected')
  return out
 except (ValueError,TypeError,KeyError,AttributeError,StopIteration,OverflowError,OSError):
  return {'error':'owned_os_identity_pair_unavailable','raw_hypothesis_status':'BLOCKED','independent_raw_value_comparison_done':False,'new_agent_tasks':0,'mutation_executed':False,'resend_authorized':False,**LIMITS}
