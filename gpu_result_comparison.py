"""GET-only strict recorded GPU-name hypothesis, not complete product acceptance."""
from copy import deepcopy
from datetime import datetime,timezone
import hashlib,json,re
import job_store
from command_probe_contract import target,validate_target_state,CORE
from command_stage_native import context,read_json
from plugin_preparation import stamp
from operation_journal import list_operations
TOOL='browser_compare_owned_gpu_names_semantic'
PROFILE='owned-gpu-recorded-name-comparison-v1'
OS_REF=('20261016-235301-aa2b9e7b','tc-4890b9ad','ev-9bf073d8994c')
PLUGIN_REF=('20261017-000011-29de159c','tc-a00b46d5','ev-67c83abcf88b')
RULE='one_unique_exact_vendor_space_device_name_for_each_os_pci_display_record'
LIMITS={'all_gpu_completeness_verified':False,'note_semantics_verified':False,'general_name_mapping_verified':False,
        'desktop_or_render_verified':False,'live_current_state_verified':False,'business_pass':False}

def requirement(campaign):
    if not isinstance(campaign,str) or not re.fullmatch('[a-z0-9-]{1,80}',campaign):raise ValueError('gpu_comparison_campaign_required')
    t=target('astra')
    return {'type':'owned_gpu_name_comparison','stand':'lab','locked':True,'action_profile':'read_only','profile_id':PROFILE,
        'campaign_id':campaign,'target':'astra',**{k:t[k] for k in ['ci_name','ci_id','agent_id']},'core_version':CORE,
        'plugin_name':'gpuDeviceAudit','plugin_version':'1.3.2','os_source':list(OS_REF),'plugin_source':list(PLUGIN_REF),
        'expected_rule':RULE,'max_observation_pair_seconds':1800,'recorded_pair_only':True,**LIMITS}
def validate_context(job,cid,args):
    if not isinstance(job,dict) or len(job.get('test_cases',[]))!=1:raise ValueError('single_gpu_comparison_case_required')
    c=job['test_cases'][0];r=c.get('requirement') or {}
    if (c.get('case_id')!=cid or r!=requirement(r.get('campaign_id')) or args!={'target':'astra'} or job.get('stand')!='lab'
        or job.get('status')!='running' or c.get('status')!='running' or job.get('resources')):raise ValueError('locked_gpu_comparison_scope_required')
    if not all(r[k] in job.get('request','') for k in ['ci_id','agent_id','ci_name','profile_id']):raise ValueError('gpu_comparison_original_request_required')
    return r
def _proof(ref,kind):
    jid,cid,eid=ref;j=job_store.get_job(jid);c=next(c for c in j['test_cases'] if c['case_id']==cid);r=c['requirement']
    e=next(e for e in c['evidence'] if e['evidence_id']==eid);env=json.loads(e['value']);v=env['result'];ops=list_operations(jid)
    matching=[o for o in ops if o['status']=='verified' and o['verification']['evidence_id']==eid and o['verification']['identifier_value']==v.get('task_id')]
    if (e.get('source')!='uqa_tool' or e.get('execution_status') not in {'executed','observed'} or not 1<=len(ops)<=2
        or any(o['status']!='verified' for o in ops) or len(matching)!=1 or not v.get('native_result_verified')
        or v.get('agent_id')!=target('astra')['agent_id'] or v.get('machine_uid')!=target('astra')['ci_id'] or v.get('task_status')!='success'):
        raise ValueError('gpu_owned_native_verified_proof_required')
    if kind=='os':
        from endpoint_metadata import requirement as endpoint_requirement,GPUS,READ
        if (len(ops)!=1 or r!=endpoint_requirement('astra',r.get('campaign_id'),GPUS) or env['tool']!=READ
            or not v['summary']['os_query_complete']):raise ValueError('gpu_os_source_required')
    else:
        from plugin_audit_profiles import profile
        scope=r.get('pinned_audit_task') or {}
        if (env['tool']!='browser_inspect_pinned_agent_audit_semantic' or scope.get('task_name')!='gpuDeviceAudit' or scope.get('core_version')!=CORE
            or r.get('expected_profile')!=profile('gpuDeviceAudit') or r.get('delivery_authorized_this_run') is not False
            or v.get('identity_verified') is not True or v.get('fresh_result') is not True or v.get('result_code')!='success'
            or not v['audit_data_summary']['structure_subset_matched']
            or any(o.get('stage_id') not in {'refresh-plugin-inventory','execute-audit'} for o in ops)):raise ValueError('gpu_plugin_source_required')
    return v,r,c
def expected_names(rows):
    if not isinstance(rows,list) or not 0<len(rows)<=16:raise ValueError('bounded_nonempty_gpu_os_rows_required')
    names=[]
    for row in rows:
        if not isinstance(row,dict) or not all(isinstance(row.get(k),str) and 0<len(row[k])<=1024 and '\x00' not in row[k] for k in ['vendor_name','device_name']):raise ValueError('gpu_os_names_required')
        names.append(row['vendor_name']+' '+row['device_name'])
    if len(names)!=len(set(names)):raise ValueError('gpu_os_name_ambiguity')
    return names
def source_proofs():
    os,_,_= _proof(OS_REF,'os');plugin,r,c=_proof(PLUGIN_REF,'plugin')
    expected={'rule':RULE,'expected_names':expected_names(os['summary']['os_gpu_rows']),'note_semantics_verified':False,
        'all_gpu_completeness_verified':False,'general_name_mapping_verified':False,'business_pass':False}
    baseline={'job_id':OS_REF[0],'case_id':OS_REF[1],'evidence_id':'ev-7c7621895e08','read_evidence_id':OS_REF[2],'max_pair_age_seconds':1800}
    prepared=[e for e in c['evidence'] if e['type']=='operator_gpu_comparison_preparation' and e['source']=='authorized_lab_operator']
    if (r.get('comparison_expected')!=expected or r.get('independent_os_baseline')!=baseline or len(prepared)!=1
        or json.loads(prepared[0]['value']).get('comparison_expected')!=expected
        or stamp(prepared[0]['created_at'])>stamp(plugin['server_created_at'])):raise ValueError('gpu_name_hypothesis_not_predeclared')
    return os,plugin
def compare_values(os_rows,plugin_rows):
    names=expected_names(os_rows)
    if not isinstance(plugin_rows,list) or len(plugin_rows)>16 or any(not isinstance(x,dict) or not isinstance(x.get('name'),str) or len(x['name'])>2048 or '\x00' in x['name'] for x in plugin_rows):raise ValueError('bounded_gpu_name_records_required')
    checks=[{'expected_os_vendor_device_name':name,'matching_plugin_records':sum(x['name']==name for x in plugin_rows)} for name in names]
    status='BLOCKED' if any(x['matching_plugin_records']>1 for x in checks) else 'MATCH' if all(x['matching_plugin_records']==1 for x in checks) else 'MISMATCH'
    result={'name_hypothesis_status':status,'named_records_compared':len(checks),'comparisons':checks,
        'plugin_name_observations':[x['name'] for x in plugin_rows],'plugin_rows_total':len(plugin_rows),
        'expected_rule':RULE,'hypothesis_only':True,'full_source_case_status':'BLOCKED','full_payload_emitted':False,**LIMITS}
    if len(json.dumps(result,ensure_ascii=False))>6000:raise ValueError('gpu_comparison_result_budget')
    return result
def compact(parsed):
    if not isinstance(parsed,dict) or parsed.get('profile_id')!=PROFILE or parsed.get('target')!='astra':return {}
    if any(parsed.get(k) is not v for k,v in LIMITS.items()) or parsed.get('hypothesis_only') is not True or parsed.get('recorded_pair_only') is not True or parsed.get('same_recorded_payload') is not True:return {}
    rows=parsed.get('comparisons')
    if not isinstance(rows,list) or not 0<len(rows)<=16 or parsed.get('named_records_compared')!=len(rows):return {}
    if any(not isinstance(x,dict) or type(x.get('matching_plugin_records'))!=int or x['matching_plugin_records']<0 for x in rows):return {}
    observed=parsed.get('plugin_name_observations')
    if (not isinstance(observed,list) or len(observed)>16 or any(not isinstance(x,str) or len(x)>2048 for x in observed)
        or parsed.get('plugin_rows_total')!=len(observed) or parsed.get('full_source_case_status')!='BLOCKED'
        or parsed.get('expected_rule')!=RULE or parsed.get('resend_authorized') is not False):return {}
    if any(x.get('matching_plugin_records')!=sum(y==x.get('expected_os_vendor_device_name') for y in observed) for x in rows):return {}
    status='BLOCKED' if any(x['matching_plugin_records']>1 for x in rows) else 'MATCH' if all(x['matching_plugin_records']==1 for x in rows) else 'MISMATCH'
    if status!=parsed.get('name_hypothesis_status') or parsed.get('source_refs')!={'os':list(OS_REF),'plugin':list(PLUGIN_REF)} or parsed.get('new_agent_tasks')!=0:return {}
    keys=['target','profile_id','name_hypothesis_status','named_records_compared','comparisons','plugin_name_observations','plugin_rows_total',
        'expected_rule','hypothesis_only','full_source_case_status','source_refs','plugin_task_id','pair_seconds','os_observed_at',
        'plugin_observed_at','read_at','source_payload_sha256','same_recorded_payload','recorded_pair_only','new_agent_tasks','resend_authorized',*LIMITS]
    if any(k not in parsed for k in keys) or len(json.dumps(parsed,ensure_ascii=False))>8000:return {}
    return {k:deepcopy(parsed[k]) for k in keys}
def inspect(session,args,jid,cid):
    try:
        r=validate_context(job_store.get_job(jid),cid,args);os,plugin=source_proofs()
        gap=(stamp(plugin['processed_at'])-stamp(os['processed_at'])).total_seconds()
        if not -5<=gap<=r['max_observation_pair_seconds']:raise ValueError('gpu_observation_pair_age_required')
        _,ci,urls=context(session,'astra');validate_target_state('astra',ci,read_json(session,urls[1]))
        full=read_json(session,urls[0]+'/'+plugin['task_id']+'/full');env=full.get('result')
        if (not isinstance(env,dict) or full.get('id')!=plugin['task_id'] or full.get('agent_id')!=r['agent_id'] or full.get('name')!='gpuDeviceAudit'
            or full.get('status')!='success' or full.get('created_at')!=plugin['server_created_at'] or env.get('result')!='success'
            or env.get('machine_uid')!=r['ci_id'] or env.get('processed_at')!=plugin['processed_at']):raise ValueError('same_gpu_owned_payload_required')
        digest=hashlib.sha256(json.dumps(env['data'],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        if digest!=plugin['audit_data_summary']['data_sha256']:raise ValueError('gpu_source_payload_changed')
        return {**compare_values(os['summary']['os_gpu_rows'],env['data']),'target':'astra','profile_id':PROFILE,
            'source_refs':{'os':list(OS_REF),'plugin':list(PLUGIN_REF)},'plugin_task_id':plugin['task_id'],'pair_seconds':gap,
            'os_observed_at':os['processed_at'],'plugin_observed_at':plugin['processed_at'],'read_at':datetime.now(timezone.utc).isoformat(),
            'source_payload_sha256':digest,'same_recorded_payload':True,'recorded_pair_only':True,
            'new_agent_tasks':0,'mutation_executed':False,'resend_authorized':False,'jira_written':False}
    except (ValueError,KeyError,TypeError,AttributeError,StopIteration,OverflowError):
        return {'error':'owned_gpu_comparison_unavailable','name_hypothesis_status':'BLOCKED','new_agent_tasks':0,'mutation_executed':False,'resend_authorized':False,**LIMITS}
