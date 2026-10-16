"""Closed GET-only recorded-pair value comparison; never complete drive regression."""
from copy import deepcopy
from datetime import datetime,timezone
import hashlib,json,math,re
import job_store
from command_probe_contract import target,validate_target_state,CORE
from command_stage_native import context,read_json
from operation_journal import list_operations
from plugin_preparation import stamp

TOOL='browser_compare_owned_drive_values_semantic'
PROFILE='owned-drive-recorded-value-comparison-v1'
OS_REF=('20261016-230402-2b8cc756','tc-c232c0a6','ev-b1caf3487dd8')
PLUGIN_REF=('20261016-231923-bb1700fc','tc-2d526eb5','ev-14b8b55e56f0')

def requirement(campaign):
    if not isinstance(campaign,str) or not re.fullmatch(r'[a-z0-9-]{1,80}',campaign):raise ValueError('comparison_campaign_required')
    t=target('astra')
    return {'type':'owned_drive_value_comparison','stand':'lab','locked':True,'action_profile':'read_only',
        'profile_id':PROFILE,'campaign_id':campaign,'target':'astra','ci_id':t['ci_id'],'agent_id':t['agent_id'],
        'ci_name':t['ci_name'],'core_version':CORE,'plugin_name':'driveDeviceAudit','plugin_version':'1.3.5',
        'os_source':list(OS_REF),'plugin_source':list(PLUGIN_REF),'max_observation_pair_seconds':1800,
        'expected_rules':['unique_record_for_each_os_mounted_point','exact_filesystem_text','numeric_capacity_equals_os_byte_count'],
        'recorded_pair_only':True,'all_disks_completeness_verified':False,'unit_semantics_verified':False,'business_pass':False}

def validate_context(job,cid,args):
    if not isinstance(job,dict) or len(job.get('test_cases',[]))!=1:raise ValueError('single_comparison_case_required')
    c=job['test_cases'][0];r=c.get('requirement') or {}
    if (c.get('case_id')!=cid or r!=requirement(r.get('campaign_id')) or args!={'target':'astra'}
        or job.get('stand')!='lab' or job.get('status')!='running' or c.get('status')!='running' or job.get('resources')):
        raise ValueError('locked_comparison_scope_required')
    if not all(r[k] in job.get('request','') for k in ['ci_id','agent_id','ci_name','profile_id']):raise ValueError('comparison_original_request_required')
    return r

def source_proof(ref,kind):
    jid,cid,eid=ref;j=job_store.get_job(jid);c=next(c for c in j['test_cases'] if c['case_id']==cid);r=c['requirement']
    e=next(e for e in c['evidence'] if e['evidence_id']==eid);envelope=json.loads(e['value']);v=envelope['result'];ops=list_operations(jid)
    if e.get('source')!='uqa_tool' or e.get('execution_status') not in {'observed','executed'}:raise ValueError('source_native_evidence_required')
    if len(ops)!=1 or ops[0]['status']!='verified' or ops[0]['verification']['evidence_id']!=eid:raise ValueError('source_verified_operation_required')
    if v.get('native_result_verified') is not True or v.get('agent_id')!=target('astra')['agent_id'] or v.get('machine_uid')!=target('astra')['ci_id']:
        raise ValueError('source_target_identity_required')
    if (v.get('task_id')!=ops[0]['verification']['identifier_value'] or v.get('task_status')!='success'):
        raise ValueError('source_task_binding_required')
    if kind=='os':
        if (envelope.get('tool')!='browser_inspect_closed_endpoint_metadata_semantic'
            or r.get('profile_id')!='owned-drive-os-baseline-v1' or r.get('core_version')!=CORE
            or r.get('plugin_version')!='1.4.0' or not v['summary']['os_query_complete']):raise ValueError('os_source_required')
    else:
        s=r.get('pinned_audit_task') or {}
        if (envelope.get('tool')!='browser_inspect_pinned_agent_audit_semantic' or s.get('task_name')!='driveDeviceAudit'
            or s.get('core_version')!=CORE or r.get('expected_profile',{}).get('plugin_version')!='1.3.5'
            or v.get('fresh_result') is not True or v.get('identity_verified') is not True):raise ValueError('plugin_source_required')
    return v

def compare_values(os_rows,plugin_rows):
    if not isinstance(os_rows,list) or not 0<len(os_rows)<=256 or not isinstance(plugin_rows,list) or len(plugin_rows)>256:
        raise ValueError('bounded_inventory_lists_required')
    if not all(isinstance(x,dict) for x in os_rows+plugin_rows):raise ValueError('inventory_objects_required')
    selected=[];mounts=set()
    for row in os_rows:
        mount=row.get('mount_point')
        if mount in (None,''):continue
        if (not isinstance(mount,str) or not mount.startswith('/') or len(mount)>1024 or '\x00' in mount or mount in mounts
            or not isinstance(row.get('fs_type'),str) or not 0<len(row['fs_type'])<=128
            or type(row.get('size_bytes'))!=int or not 0<=row['size_bytes']<2**63):
            raise ValueError('mounted_os_metadata_required')
        mounts.add(mount);matches=[x for x in plugin_rows if x.get('mountPoint')==mount]
        actual=matches[0] if len(matches)==1 else None
        size=actual.get('size') if actual else None
        numeric=type(size) in (int,float) and 0<=size<2**63 and math.isfinite(size) and size==int(size)
        fs=actual.get('fsType') if actual else None
        safe_fs=isinstance(fs,str) and len(fs)<=128 and '\x00' not in fs
        checks={'unique_mount_record':len(matches)==1,'filesystem_text_equal':bool(safe_fs and fs==row['fs_type']),
            'numeric_capacity_equal_to_os_bytes':bool(numeric and size==row['size_bytes'])}
        selected.append({'mount_point':mount,'expected_os':{'filesystem':row['fs_type'],'capacity_bytes':row['size_bytes']},
            'actual_plugin':{'filesystem':fs if safe_fs else None,'numeric_capacity':size if numeric else None,
                'filesystem_shape_valid':safe_fs,'numeric_shape_valid':numeric} if actual else None,
            'checks':checks,'ambiguous':len(matches)>1})
    if not selected:raise ValueError('nonempty_mounted_scope_required')
    status='BLOCKED' if any(x['ambiguous'] for x in selected) else 'MATCH' if all(all(x['checks'].values()) for x in selected) else 'MISMATCH'
    return {'mounted_value_comparison_status':status,'mounted_records_compared':len(selected),'comparisons':selected,
        'os_rows_total':len(os_rows),'plugin_rows_total':len(plugin_rows),
        'outside_mounted_scope_os_rows':len(os_rows)-len(selected),'serial_uid_semantics_verified':False,
        'unit_semantics_verified':False,'all_disks_completeness_verified':False,'live_current_state_verified':False,
        'comparison_scope':'Exact mount/filesystem/numeric-capacity observations only; equality to OS byte counts does not establish general plugin units.',
        'full_source_case_status':'BLOCKED','business_pass':False,'full_payload_emitted':False,'serial_uid_values_emitted':False}

def compact(parsed):
    """Preserve the actual value checks and negative coverage flags in model view."""
    if not isinstance(parsed,dict) or parsed.get('profile_id')!=PROFILE or parsed.get('target')!='astra':return {}
    if any(parsed.get(k) is not v for k,v in {'business_pass':False,'recorded_pair_only':True,'same_recorded_payload':True,
        'all_disks_completeness_verified':False,'unit_semantics_verified':False,'live_current_state_verified':False}.items()):return {}
    rows=parsed.get('comparisons')
    if not isinstance(rows,list) or not 0<len(rows)<=256 or parsed.get('mounted_records_compared')!=len(rows):return {}
    keys={'unique_mount_record','filesystem_text_equal','numeric_capacity_equal_to_os_bytes'}
    if any(not isinstance(x,dict) or not isinstance(x.get('checks'),dict) or set(x['checks'])!=keys or any(type(v)!=bool for v in x['checks'].values())
        or type(x.get('ambiguous'))!=bool for x in rows):return {}
    status='BLOCKED' if any(x['ambiguous'] for x in rows) else 'MATCH' if all(all(x['checks'].values()) for x in rows) else 'MISMATCH'
    if parsed.get('mounted_value_comparison_status')!=status:return {}
    selected=['target','profile_id','mounted_value_comparison_status','mounted_records_compared',
        'comparisons','os_rows_total','plugin_rows_total','outside_mounted_scope_os_rows','serial_uid_semantics_verified',
        'unit_semantics_verified','all_disks_completeness_verified','live_current_state_verified','comparison_scope',
        'full_source_case_status','business_pass','source_refs','plugin_task_id','os_observed_at','plugin_observed_at',
        'pair_seconds','read_at','source_payload_sha256','recorded_pair_only','same_recorded_payload','new_agent_tasks','resend_authorized']
    if any(k not in parsed for k in selected) or parsed['source_refs']!={'os':list(OS_REF),'plugin':list(PLUGIN_REF)}:return {}
    return {k:deepcopy(parsed[k]) for k in selected}

def inspect(session,args,jid,cid):
    try:
        r=validate_context(job_store.get_job(jid),cid,args);os=source_proof(OS_REF,'os');plugin=source_proof(PLUGIN_REF,'plugin')
        gap=(stamp(plugin['processed_at'])-stamp(os['processed_at'])).total_seconds()
        if not -5<=gap<=r['max_observation_pair_seconds']:raise ValueError('observation_pair_age_required')
        t,ci,urls=context(session,'astra');validate_target_state('astra',ci,read_json(session,urls[1]))
        full=read_json(session,urls[0]+'/'+plugin['task_id']+'/full');env=full.get('result')
        if (not isinstance(env,dict) or full.get('id')!=plugin['task_id'] or full.get('agent_id')!=r['agent_id']
            or full.get('name')!='driveDeviceAudit' or full.get('status')!='success' or env.get('machine_uid')!=r['ci_id']
            or env.get('result')!='success' or env.get('processed_at')!=plugin['processed_at']
            or full.get('created_at')!=plugin['server_created_at']):raise ValueError('same_owned_plugin_payload_required')
        digest=hashlib.sha256(json.dumps(env['data'],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        if digest!=plugin['audit_data_summary']['data_sha256']:raise ValueError('source_plugin_payload_changed')
        summary=compare_values(os['summary']['os_disk_rows'],env['data'])
        return {**summary,'target':'astra','profile_id':PROFILE,'core_version':CORE,'plugin_version':'1.3.5',
            'source_refs':{'os':list(OS_REF),'plugin':list(PLUGIN_REF)},'plugin_task_id':plugin['task_id'],
            'os_observed_at':os['processed_at'],'plugin_observed_at':plugin['processed_at'],'pair_seconds':gap,
            'read_at':datetime.now(timezone.utc).isoformat(),'source_payload_sha256':digest,
            'recorded_pair_only':True,'same_recorded_payload':True,'source_execution_verified':True,
            'new_agent_tasks':0,'mutation_executed':False,'resend_authorized':False,'jira_written':False}
    except (ValueError,KeyError,TypeError,AttributeError,StopIteration,OverflowError):
        return {'error':'owned_drive_comparison_unavailable','mounted_value_comparison_status':'BLOCKED',
            'business_pass':False,'mutation_executed':False,'new_agent_tasks':0,'resend_authorized':False}
