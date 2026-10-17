"""Bounded CMDB GET for the exact additive US-T114 fixture; never a writer.

Preflight exposes raw response shape/scope, not a fabricated match. Final
acceptance is only possible after owned verified installation and softAudit.
"""
import hashlib,json,re
import job_store
from command_probe_contract import target,CORE,validate_target_state
from command_stage_native import context,read_json,now
from software_change_fixture import PACKAGE,VERSION,ARTIFACT_SHA,PROFILE
from operation_journal import list_operations
from plugin_preparation import stamp
TOOL='browser_inspect_owned_software_change_semantic'

def requirement(campaign,source_ref,install_ref,audit_ref,fixture_profile=None):
 if not isinstance(campaign,str) or not re.fullmatch('[a-z0-9-]{1,80}',campaign):raise ValueError('campaign')
 for ref in [source_ref,install_ref,audit_ref]:
  if not isinstance(ref,list) or len(ref)!=2 or not all(isinstance(x,str) and x for x in ref):raise ValueError('child_ref')
 from regression_read_coverage import load
 _,case,_=load('US-T114')
 import software_change_fixture as fixture
 if fixture_profile is not None:
  import software_change_fixture_v2 as fixture
  if fixture_profile!=fixture.PROFILE:raise ValueError('review_fixture_profile')
 result={'type':'owned_software_change_review','stand':'lab','locked':True,'action_profile':'read_only',
   'campaign_id':campaign,'source_ref':source_ref,'install_ref':install_ref,'audit_ref':audit_ref,
   'source_case':'US-T114','source_sha256':case['json_sha256'],'target':'astra',**target('astra'),
   'core_version':CORE,'package':fixture.PACKAGE,'version':fixture.VERSION,'artifact_sha256':fixture.ARTIFACT_SHA,
   'max_pair_seconds':1800,'jira_writes':False}
 if fixture_profile is not None:result['fixture_profile']=fixture_profile
 return result

def validate(job,cid,args):
 if args not in ({'phase':'before'},{'phase':'after'}):raise ValueError('exact_phase')
 if not isinstance(job,dict) or len(job.get('test_cases',[]))!=1:raise ValueError('single_case')
 c=job['test_cases'][0];r=c.get('requirement') or {}
 if (r!=requirement(r.get('campaign_id'),r.get('source_ref'),r.get('install_ref'),r.get('audit_ref'),r.get('fixture_profile'))
  or c['case_id']!=cid or c['status']!='running' or job.get('status')!='running' or job.get('stand')!='lab'
  or job.get('resources') or not all(r[k] in job.get('request','') for k in ['agent_id','ci_id','package'])):raise ValueError('locked_review_scope')
 return c,r

def _child(ref):
 j=job_store.get_job(ref[0]);c=next(c for c in j['test_cases'] if c['case_id']==ref[1])
 if j['stand']!='lab' or len(j['test_cases'])!=1 or j.get('resources'):raise ValueError('child_scope')
 return j,c

def _own(c,tool):
 found=[]
 for e in c.get('evidence',[]):
  if e.get('type')!=tool or e.get('source')!='uqa_tool':continue
  b=json.loads(e['value'])
  if b.get('tool')==tool and not b.get('result',{}).get('error'):found.append((e,b))
 return found

def _read_software(session,ci_id,scope,package=PACKAGE):
 # Path/params are from the installed registered GET /api/v1/cis contract and
 # the pinned source. The response itself must prove its filtering/pagination.
 from urllib.parse import urlsplit
 _,_,urls=context(session,'astra');path=urlsplit(urls[0]).path
 base=path.split('/agents/')[0]+'/cis'
 url=session._same_https_origin_url(urls[0],base)
 if not url:raise ValueError('same_origin_required')
 rows=[];total=None
 for offset in range(0,5000,100):
  b=read_json(session,url,{'ci_class':'software','detected_at_id':scope,'use_counter':True,'limit':100,'offset':offset})
  items=b.get('items')
  if not isinstance(items,list) or len(items)>100:raise ValueError('cmdb_items_shape')
  n=b.get('total')
  if type(n)!=int or n<0 or n>5000 or total is not None and total!=n:raise ValueError('cmdb_counter_required')
  total=n
  if 'offset' in b and b['offset']!=offset:raise ValueError('cmdb_offset')
  rows.extend(items)
  if len(rows)>=total:break
  if not items:raise ValueError('cmdb_pagination_gap')
 if total!=len(rows) or any(not isinstance(x,dict) for x in rows):raise ValueError('cmdb_incomplete')
 ids=[x.get('id') for x in rows]
 if any(not isinstance(x,str) or not x for x in ids) or len(set(ids))!=len(ids):raise ValueError('cmdb_duplicate_ids')
 def contains(value):
  if isinstance(value,str):return value==package
  if isinstance(value,dict):return any(contains(v) for v in value.values())
  if isinstance(value,list):return any(contains(v) for v in value)
  return False
 matches=[x for x in rows if contains(x)]
 def shape(v,depth=0):
  if depth>3:return type(v).__name__
  if isinstance(v,dict):return {k:shape(x,depth+1) for k,x in v.items()}
  return type(v).__name__
 return {'scope_id':scope,'total':total,'complete':True,'matches':matches,
  'rows_sha256':hashlib.sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),
  'sample_field_shapes':[{k:type(v).__name__ for k,v in x.items()} for x in rows[:1]],
  'fixture_absence_proved':not matches and bool(rows),'absence_rule':'no_exact_package_string_in_any_scoped_row_leaf',
  'sample_detail_shapes':[shape(x.get('detail')) for x in rows[:1]],
  'sample_link_fields':[{k:v for k,v in x.items() if k in {'agent_id','detected_at_id','ci_class','parent_id'}} for x in rows[:1]]}

def inspect(session,args,jid,cid):
 try:
  c,r=validate(job_store.get_job(jid),cid,args)
  import software_change_fixture as fixture
  if r.get('fixture_profile'):
   import software_change_fixture_v2 as fixture
  package,version=fixture.PACKAGE,fixture.VERSION
  _,ci,urls=context(session,'astra');validate_target_state('astra',ci,read_json(session,urls[1]))
  sj,sc=_child(r['source_ref'])
  from regression_read_coverage import requirement as source_requirement
  if sc.get('requirement')!=source_requirement('US-T114',sc['requirement']['campaign_id']):raise ValueError('source_child_binding')
  coverage=_own(sc,'knowledge_inspect_own_regression_read_coverage')
  proved={b['arguments'].get('step_number') for _,b in coverage if b['result'].get('step_cells_completely_read') is True}
  if proved!={1,2,3}:raise ValueError('all_three_own_source_steps_required')
  out={'phase':args['phase'],'package':package,'version':version,'read_at':now(),
       'agent_id':r['agent_id'],'ci_id':r['ci_id'],'mutation_executed':False,'business_pass':False,'full_case_passed':False}
  if args['phase']=='before':
   if list_operations(r['install_ref'][0]) or list_operations(r['audit_ref'][0]):raise ValueError('before_must_precede_mutations')
   # Both UUIDs are read explicitly so outdated source terminology cannot turn
   # an empty wrong-scope query into an absence proof. No ID substitution hidden.
   out['source_agent_filter']=_read_software(session,r['ci_id'],r['agent_id'],package)
   out['ci_filter']=_read_software(session,r['ci_id'],r['ci_id'],package)
   return out
  befores=[(e,b['result']) for e,b in _own(c,TOOL) if b.get('arguments')=={'phase':'before'}
    and b['result'].get('source_agent_filter',{}).get('fixture_absence_proved') is True]
  if len(befores)!=1:raise ValueError('one_valid_before_required')
  before_e,before=befores[0]
  ij,ic=_child(r['install_ref'])
  from endpoint_metadata import requirement as install_requirement,READ as INSTALL_READ
  if ic.get('requirement')!=install_requirement('astra',ic['requirement']['campaign_id'],fixture.PROFILE):raise ValueError('install_child_binding')
  installs=[(e,b['result']) for e,b in _own(ic,INSTALL_READ) if b['result'].get('native_result_verified') is True]
  if len(installs)!=1:raise ValueError('one_install_full_required')
  ie,install=installs[0];iops=list_operations(ij['job_id'])
  if (len(iops)!=1 or iops[0]['status']!='verified' or iops[0]['verification']['evidence_id']!=ie['evidence_id']
   or not install['summary'].get('fixture_install_verified') or install['agent_id']!=r['agent_id']
   or install['ci_id']!=r['ci_id'] or stamp(before['read_at'])>stamp(install['sent_at'])):raise ValueError('owned_install_or_order')
  aj,ac=_child(r['audit_ref'])
  from software_result_comparison import _proof,_same_full
  reads=[e for e,b in _own(ac,'browser_inspect_pinned_agent_audit_semantic')
    if b['result'].get('task_name')=='softAudit' and b['result'].get('native_result_verified') is True]
  if len(reads)!=1:raise ValueError('one_softaudit_full_required')
  pe=reads[0];plugin,_,_=_proof([aj['job_id'],ac['case_id'],pe['evidence_id']],'plugin')
  gap=(stamp(plugin['processed_at'])-stamp(install['processed_at'])).total_seconds()
  if (not 0<=gap<=r['max_pair_seconds'] or stamp(plugin['server_created_at'])<stamp(install['processed_at'])
   or not 0<=(stamp(now())-stamp(plugin['processed_at'])).total_seconds()<=r['max_pair_seconds']):raise ValueError('own_current_change_pair_age')
  # Same owned task IDs only; no new task or source adoption in this reader.
  full=read_json(session,urls[0]+'/'+install['task_id']+'/full')
  env=_same_full(full,install,'executeCommand',r);data=env.get('data')
  if isinstance(data,dict) and isinstance(data.get('stdout'),str):stdout,code,stderr=data['stdout'],data.get('errorlevel'),data.get('stderr')
  else:stdout,code,stderr=env.get('result'),env.get('error_code'),env.get('error_msg')
  if (not isinstance(stdout,str) or len(stdout.encode())>16384 or code not in (0,'0') or stderr not in ('',None)
    or hashlib.sha256(stdout.encode()).hexdigest()!=install['result_sha256']
    or fixture.summarize(json.loads(stdout))!=install['summary']):raise ValueError('same_install_output_required')
  penv=_same_full(read_json(session,urls[0]+'/'+plugin['task_id']+'/full'),plugin,'softAudit',r)
  pdata=penv.get('data')
  if (penv.get('result')!='success' or not isinstance(pdata,list)
   or hashlib.sha256(json.dumps(pdata,sort_keys=True,ensure_ascii=False).encode()).hexdigest()!=plugin['audit_data_summary']['data_sha256']):raise ValueError('same_plugin_payload_required')
  pm=[x for x in pdata if isinstance(x,dict) and x.get('name')==package]
  if len(pm)!=1 or pm[0].get('version')!=version:raise ValueError('new_package_softaudit_exact_name_version')
  cmdb=_read_software(session,r['ci_id'],r['agent_id'],package);matches=cmdb['matches']
  if len(matches)!=1:raise ValueError('new_package_cmdb_exactly_one_required')
  row=matches[0];detail=row.get('detail') or {}
  if (row.get('detected_at_id')!=r['agent_id'] or row.get('parent_id')!=r['ci_id']
    or row.get('ci_class')!='software' or row.get('is_archived') is not False
    or detail.get('name')!=package or detail.get('version')!=version
    or stamp(row.get('created_at'))<stamp(before['read_at'])):raise ValueError('new_cmdb_identity_version_link_creation')
  out.update(step1_install_verified=True,step2_fresh_softaudit_verified=True,step3_new_software_cmdb_verified=True,
   source_steps_completely_read=3,source_case='US-T114',full_case_passed=True,business_pass=True,
   case_scope='one_owned_software_change_fixture_not_all_software_or_all_regression',
   execution_mode='framework_assisted_model_selected_actions',ordinary_freeform_autonomy=False,
   source_ref=r['source_ref'],before_evidence_id=before_e['evidence_id'],
   install_ref=[ij['job_id'],ic['case_id'],ie['evidence_id']],softaudit_ref=[aj['job_id'],ac['case_id'],pe['evidence_id']],
   install_task_id=install['task_id'],softaudit_task_id=plugin['task_id'],cmdb_id=row['id'],
   cmdb_created_at=row['created_at'],pair_seconds=gap,
   install_result_sha256=install['result_sha256'],softaudit_data_sha256=plugin['audit_data_summary']['data_sha256'],
   cmdb_rows_sha256=cmdb['rows_sha256'],artifact_sha256=fixture.ARTIFACT_SHA,
   software_display_mapping='cmdb.detail.name/version (observed before mutation)',no_value_normalization=True)
  return out
 except (ValueError,TypeError,KeyError,AttributeError,StopIteration) as e:
  return {'error':str(e)[:160],'phase':args.get('phase'),'mutation_executed':False,'business_pass':False,'full_case_passed':False}
