"""GET-only exact name/version comparison of an owned recorded OS/plugin pair."""
from copy import deepcopy
from datetime import datetime,timezone
import hashlib,json,re
import job_store
from command_probe_contract import target,validate_target_state,CORE
from command_stage_native import context,read_json
from plugin_preparation import stamp
from operation_journal import list_operations
TOOL='browser_compare_owned_software_values_semantic'
PROFILE='owned-software-recorded-values-v1'
OS_REF=('20261017-010544-df5238c8','tc-6c4eb452','ev-22394b203717')
PLUGIN_REF=('20261017-010755-c17c9090','tc-b47da8ab','ev-3cfe2de4476a')
RULE='exact_unique_binary_package_name_and_version_against_own_recorded_dpkg_census'
LIMITS={'all_installed_software_completeness_verified':False,'package_to_product_display_scope_verified':False,
 'software_tab_verified':False,'other_fields_verified':False,'live_current_state_verified':False,'full_case_passed':False,'business_pass':False}

def requirement(campaign):
    if not isinstance(campaign,str) or not re.fullmatch('[a-z0-9-]{1,80}',campaign):raise ValueError('software_comparison_campaign_required')
    t=target('astra')
    return {'type':'owned_software_value_comparison','stand':'lab','locked':True,'action_profile':'read_only','profile_id':PROFILE,
        'campaign_id':campaign,'target':'astra',**{k:t[k] for k in ['ci_name','ci_id','agent_id']},'core_version':CORE,
        'plugin_name':'softAudit','plugin_version':'1.3.8','os_source':list(OS_REF),'plugin_source':list(PLUGIN_REF),
        'expected_rule':RULE,'max_observation_pair_seconds':1800,'recorded_pair_only':True,**LIMITS}

def validate_context(job,cid,args):
    if not isinstance(job,dict) or len(job.get('test_cases',[]))!=1:raise ValueError('single_software_comparison_case_required')
    c=job['test_cases'][0];r=c.get('requirement') or {}
    if (c.get('case_id')!=cid or r!=requirement(r.get('campaign_id')) or args!={'target':'astra'} or job.get('stand')!='lab'
        or job.get('status')!='running' or c.get('status')!='running' or job.get('resources')):raise ValueError('locked_software_comparison_scope_required')
    if not all(r[k] in job.get('request','') for k in ['ci_id','agent_id','ci_name','profile_id']):raise ValueError('software_comparison_original_request_required')
    return r

def _proof(ref,kind):
    jid,cid,eid=ref;j=job_store.get_job(jid);c=next(c for c in j['test_cases'] if c['case_id']==cid);r=c['requirement']
    e=next(e for e in c['evidence'] if e['evidence_id']==eid);env=json.loads(e['value']);v=env['result'];ops=list_operations(jid);t=target('astra')
    matching=[o for o in ops if o['status']=='verified' and o['verification']['evidence_id']==eid and o['verification']['identifier_value']==v.get('task_id')]
    if (j.get('stand')!='lab' or e.get('source')!='uqa_tool' or e.get('execution_status') not in {'executed','observed'} or not 1<=len(ops)<=2
        or any(o['status']!='verified' for o in ops) or len(matching)!=1 or not v.get('native_result_verified')
        or v.get('agent_id')!=t['agent_id'] or v.get('ci_id')!=t['ci_id'] or v.get('machine_uid')!=t['ci_id'] or v.get('task_status')!='success'):
        raise ValueError('software_owned_verified_proof_required')
    if kind=='os':
        from endpoint_metadata import requirement as endpoint_requirement,SOFTWARE,READ
        if (len(ops)!=1 or r!=endpoint_requirement('astra',r.get('campaign_id'),SOFTWARE) or env['tool']!=READ or env['arguments']!={'target':'astra'}
            or not v['summary']['os_query_complete'] or not v['summary']['full_enumeration_in_own_native_result']):raise ValueError('software_os_source_required')
    else:
        from plugin_audit_profiles import profile
        scope=r.get('pinned_audit_task') or {}
        if (env['tool']!='browser_inspect_pinned_agent_audit_semantic' or env['arguments']!={'ci_name':t['ci_name'],'agent_id':t['agent_id'],'task_id':v['task_id']}
            or scope!={'ci_name':t['ci_name'],'agent_id':t['agent_id'],'core_version':CORE,'task_name':'softAudit'} or r.get('expected_profile')!=profile('softAudit')
            or r.get('delivery_authorized_this_run') is not False or v.get('identity_verified') is not True or v.get('fresh_result') is not True or v.get('result_code')!='success'
            or not v['audit_data_summary']['structure_subset_matched'] or any(o.get('stage_id') not in {'refresh-plugin-inventory','execute-audit'} for o in ops)):
            raise ValueError('software_plugin_source_required')
    return v,r,c

def source_proofs():
    os,_,_=_proof(OS_REF,'os');plugin,r,c=_proof(PLUGIN_REF,'plugin')
    expected={'rule':RULE,'enumeration_sha256':os['summary']['enumeration_sha256'],'installed_package_count':os['summary']['row_count'],
        'strip_architecture_qualifier_allowed':False,'normalize_version_allowed':False,'package_to_product_display_scope_verified':False,
        'all_apps_completeness_verified':False,'software_tab_verified':False,'business_pass':False}
    baseline={'job_id':OS_REF[0],'case_id':OS_REF[1],'evidence_id':'ev-d3a40031e30c','read_evidence_id':OS_REF[2],'max_pair_age_seconds':1800}
    prepared=[e for e in c['evidence'] if e['type']=='operator_software_comparison_preparation' and e['source']=='authorized_lab_operator']
    if (r.get('comparison_expected')!=expected or r.get('independent_os_baseline')!=baseline or len(prepared)!=1
        or json.loads(prepared[0]['value']).get('comparison_expected')!=expected or stamp(prepared[0]['created_at'])>stamp(plugin['server_created_at'])):
        raise ValueError('software_rule_not_predeclared')
    return os,plugin

def compare_values(os_rows,plugin_rows):
    buckets=[]
    for rows,limit in [(os_rows,2048),(plugin_rows,10000)]:
        if not isinstance(rows,list) or len(rows)>limit:raise ValueError('software_rows_budget')
        bucket={}
        for row in rows:
            if not isinstance(row,dict) or any(not isinstance(row.get(k),str) or len(row[k])>512 or any(ord(c)<32 for c in row[k]) for k in ['name','version']) or not row['name'].strip():raise ValueError('software_name_version_shape')
            bucket.setdefault(row['name'],[]).append(row['version'])
        buckets.append(bucket)
    a,b=buckets;counts={'matched_names':0,'version_mismatches':0,'os_only_names':0,'plugin_only_names':0,'ambiguous_names':0,'unknown_version_names':0}
    differences=[]
    for name in sorted(a.keys()|b.keys()):
        av,bv=a.get(name,[]),b.get(name,[])
        if len(av)>1 or len(bv)>1:reason='ambiguous_names'
        elif not av:reason='plugin_only_names'
        elif not bv:reason='os_only_names'
        elif not av[0] or not bv[0]:reason='unknown_version_names'
        elif av[0]!=bv[0]:reason='version_mismatches'
        else:reason='matched_names'
        counts[reason]+=1
        if reason!='matched_names':differences.append({'name':name,'reason':reason,'os_versions':av,'plugin_versions':bv})
    status='BLOCKED' if not a or counts['ambiguous_names'] or counts['unknown_version_names'] else 'MISMATCH' if differences else 'MATCH'
    sample=[]
    for x in differences[:12]:
        item={**x,'os_versions':x['os_versions'][:3],'plugin_versions':x['plugin_versions'][:3],
            'os_records_with_name':len(x['os_versions']),'plugin_records_with_name':len(x['plugin_versions'])}
        if len(json.dumps(sample+[item],ensure_ascii=False).encode())>5000:break
        sample.append(item)
    return {'comparison_status':status,'comparison_scope':'recorded_exact_name_version_only','expected_rule':RULE,
        'os_rows_total':len(os_rows),'plugin_rows_total':len(plugin_rows),'os_unique_names':len(a),'plugin_unique_names':len(b),
        'union_names_total':len(a.keys()|b.keys()),'shared_names_total':len(a.keys()&b.keys()),**counts,
        'differences_total':len(differences),'difference_sample':sample,'difference_sample_is_full':len(sample)==len(differences),
        'comparison_rows_sha256':hashlib.sha256(json.dumps([sorted(a.items()),sorted(b.items())],ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
        'full_payload_emitted':False,'full_source_case_status':'BLOCKED','normalization_applied':False,**LIMITS}

def compact(parsed):
    if not isinstance(parsed,dict) or parsed.get('profile_id')!=PROFILE or parsed.get('target')!='astra':return {}
    if any(parsed.get(k) is not v for k,v in LIMITS.items()) or any(parsed.get(k) is not v for k,v in {'recorded_pair_only':True,'same_recorded_payload':True,'resend_authorized':False,'normalization_applied':False,'full_payload_emitted':False}.items()):return {}
    if parsed.get('source_refs')!={'os':list(OS_REF),'plugin':list(PLUGIN_REF)} or parsed.get('expected_rule')!=RULE or parsed.get('new_agent_tasks')!=0 or parsed.get('full_source_case_status')!='BLOCKED' or parsed.get('comparison_scope')!='recorded_exact_name_version_only':return {}
    countkeys=['matched_names','version_mismatches','os_only_names','plugin_only_names','ambiguous_names','unknown_version_names']
    if any(type(parsed.get(k))!=int or not 0<=parsed[k]<=12048 for k in countkeys+['os_rows_total','plugin_rows_total','os_unique_names','plugin_unique_names','union_names_total','shared_names_total','differences_total']):return {}
    if not 0<parsed['os_rows_total']<=2048 or not parsed['os_unique_names']<=parsed['os_rows_total'] or not parsed['plugin_unique_names']<=parsed['plugin_rows_total']<=10000:return {}
    if parsed['differences_total']!=sum(parsed[k] for k in countkeys if k!='matched_names'):return {}
    if parsed['union_names_total']!=sum(parsed[k] for k in countkeys) or parsed['union_names_total']!=parsed['os_unique_names']+parsed['plugin_unique_names']-parsed['shared_names_total']:return {}
    if parsed['shared_names_total']>min(parsed['os_unique_names'],parsed['plugin_unique_names']):return {}
    status='BLOCKED' if parsed['ambiguous_names'] or parsed['unknown_version_names'] else 'MISMATCH' if parsed['differences_total'] else 'MATCH'
    if parsed.get('comparison_status')!=status:return {}
    sample=parsed.get('difference_sample')
    if not isinstance(sample,list) or len(sample)>12 or type(parsed.get('difference_sample_is_full'))!=bool or parsed['difference_sample_is_full']!=(len(sample)==parsed['differences_total']):return {}
    if any(not isinstance(x,dict) or x.get('reason') not in countkeys[1:] or not isinstance(x.get('name'),str) for x in sample):return {}
    if type(parsed.get('pair_seconds')) not in (int,float) or not -5<=parsed['pair_seconds']<=1800 or len(json.dumps(parsed,ensure_ascii=False).encode())>11000:return {}
    if any(not isinstance(parsed.get(k),str) or not re.fullmatch('[0-9a-f]{64}',parsed[k]) for k in ['comparison_rows_sha256','os_payload_sha256','plugin_payload_sha256']):return {}
    keys=['comparison_status','comparison_scope','expected_rule','os_rows_total','plugin_rows_total','os_unique_names','plugin_unique_names',
        'union_names_total','shared_names_total',*countkeys,'differences_total','difference_sample','difference_sample_is_full',
        'comparison_rows_sha256','full_payload_emitted','full_source_case_status','normalization_applied',*LIMITS,'target','profile_id','source_refs',
        'os_task_id','plugin_task_id','pair_seconds','os_observed_at','plugin_observed_at','read_at','os_payload_sha256','plugin_payload_sha256',
        'same_recorded_payload','recorded_pair_only','new_agent_tasks','resend_authorized']
    if any(k not in parsed for k in keys):return {}
    return {k:deepcopy(parsed[k]) for k in keys}

def _same_full(full,proof,name,req):
    env=full.get('result')
    if (not isinstance(env,dict) or full.get('id')!=proof['task_id'] or full.get('agent_id')!=req['agent_id'] or full.get('name')!=name
        or full.get('status')!='success' or full.get('created_at')!=proof['server_created_at'] or env.get('machine_uid')!=req['ci_id'] or env.get('processed_at')!=proof['processed_at']):raise ValueError('same_software_owned_payload_required')
    return env

def inspect(session,args,jid,cid):
    try:
        req=validate_context(job_store.get_job(jid),cid,args);os,plugin=source_proofs()
        gap=(stamp(plugin['processed_at'])-stamp(os['processed_at'])).total_seconds()
        if not -5<=gap<=req['max_observation_pair_seconds']:raise ValueError('software_observation_pair_age_required')
        _,ci,urls=context(session,'astra');validate_target_state('astra',ci,read_json(session,urls[1]))
        env=_same_full(read_json(session,urls[0]+'/'+os['task_id']+'/full'),os,'executeCommand',req)
        data=env.get('data')
        if isinstance(data,dict) and isinstance(data.get('stdout'),str):stdout,code,stderr=data['stdout'],data.get('errorlevel'),data.get('stderr')
        else:stdout,code,stderr=env.get('result'),env.get('error_code'),env.get('error_msg')
        from powershell_streams import inspect_stderr
        if not isinstance(stdout,str) or len(stdout.encode())>262144 or code not in (0,'0') or inspect_stderr(stderr)['kind'] not in {'empty','progress_only'}:raise ValueError('software_os_full_output_invalid')
        os_digest=hashlib.sha256(stdout.encode()).hexdigest()
        if os_digest!=os['result_sha256']:raise ValueError('software_os_payload_changed')
        obj=json.loads(stdout.lstrip('\ufeff'))
        from software_os_baseline import summarize
        if summarize(obj,'astra')!=os['summary']:raise ValueError('software_os_enumeration_changed')
        penv=_same_full(read_json(session,urls[0]+'/'+plugin['task_id']+'/full'),plugin,'softAudit',req)
        if penv.get('result')!='success':raise ValueError('software_plugin_not_success')
        plugin_digest=hashlib.sha256(json.dumps(penv['data'],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        if plugin_digest!=plugin['audit_data_summary']['data_sha256']:raise ValueError('software_plugin_payload_changed')
        out={**compare_values(obj['rows'],penv['data']),'target':'astra','profile_id':PROFILE,'source_refs':{'os':list(OS_REF),'plugin':list(PLUGIN_REF)},
            'os_task_id':os['task_id'],'plugin_task_id':plugin['task_id'],'pair_seconds':gap,'os_observed_at':os['processed_at'],'plugin_observed_at':plugin['processed_at'],
            'read_at':datetime.now(timezone.utc).isoformat(),'os_payload_sha256':os_digest,'plugin_payload_sha256':plugin_digest,'same_recorded_payload':True,
            'recorded_pair_only':True,'new_agent_tasks':0,'mutation_executed':False,'resend_authorized':False,'jira_written':False}
        if not compact(out):raise ValueError('software_projection_budget_or_scope')
        return out
    except (ValueError,KeyError,TypeError,AttributeError,StopIteration,OverflowError):
        return {'error':'owned_software_comparison_unavailable','comparison_status':'BLOCKED','new_agent_tasks':0,'mutation_executed':False,'resend_authorized':False,**LIMITS}
