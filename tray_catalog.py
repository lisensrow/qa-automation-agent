"""GET-only installed Tray catalogue, not installation/compatibility/session proof."""
from datetime import datetime,timezone
from urllib.parse import urlsplit
import hashlib,json,re
import job_store
from command_probe_contract import target,validate_target_state,CORE,ORIGIN
from command_stage_native import context,read_json

TOOL='browser_inspect_tray_catalog_semantic'
PROFILE='tray-support-catalog-read-v1'
SOURCE='lab-installed-contract-20261015-v260-post-update'
SCHEMA_SHA='292242e76b9e8c40208e39d9841ffbc0cefcba96bc7ab688a67f53895f33acbb'
WITNESS_SHA='0bd5ba1424d48ff19bea129cc6f118980e34095c2caa77d6333a1e9900d13aee'
WITNESS_JOB='20261016-043137-67a2b218'
WITNESS_CASE='tc-a6936a75'
WITNESS_EVIDENCE='ev-33c0d54a3d5d'
PATHS={'versions':'/agents/tray/versions','dependencies':'/agents/tray/version/dependency'}

def requirement(name,campaign):
    t=target(name)
    if not isinstance(campaign,str) or not re.fullmatch(r'[a-z0-9-]{1,80}',campaign):raise ValueError('catalog_campaign_required')
    return {'type':'tray_catalog_observation','locked':True,'stand':'lab','action_profile':'read_only',
        'target':name,'ci_id':t['ci_id'],'agent_id':t['agent_id'],'ci_name':t['ci_name'],'core_version':CORE,
        'campaign_id':campaign,'profile_id':PROFILE,'source_manifest':{'source_id':SOURCE,'schema_sha256':SCHEMA_SHA,
            'witness_job_id':WITNESS_JOB,'witness_case_id':WITNESS_CASE,'witness_evidence_id':WITNESS_EVIDENCE,
            'profile_sha256':WITNESS_SHA},'expected_profile':{'available_catalog_only':True,'installation_verified':False,
                'core_plugin_compatibility_verified':False,'remote_session_executed':False,'business_pass':False}}

def validate_context(job,cid,args):
    if not isinstance(job,dict) or len(job.get('test_cases',[]))!=1:raise ValueError('single_catalog_case_required')
    c=job['test_cases'][0];r=c.get('requirement') or {}
    if (c.get('case_id')!=cid or r!=requirement(r.get('target'),r.get('campaign_id')) or job.get('stand')!='lab'
        or job.get('job_type') not in {'manual','regression'} or job.get('status')!='running' or c.get('status')!='running'
        or job.get('resources') or not isinstance(args,dict) or set(args)!={'target','kind'}
        or args.get('target')!=r['target'] or args.get('kind') not in PATHS):raise ValueError('locked_catalog_scope_required')
    if not isinstance(job.get('request'),str) or not all(r[k] in job['request'] for k in ['ci_id','agent_id','ci_name','profile_id']):
        raise ValueError('original_catalog_request_required')
    return r

def validate_witness(job,current):
    if not isinstance(job,dict) or job.get('job_id')!=WITNESS_JOB or job.get('stand')!='lab':raise ValueError('catalog_source_job_required')
    c=next(c for c in job['test_cases'] if c['case_id']==WITNESS_CASE)
    e=next(e for e in c['evidence'] if e['evidence_id']==WITNESS_EVIDENCE)
    if (e.get('source')!='operator_installed_schema_read' or e.get('type')!='operator_installed_agent_task_profile'
        or e.get('execution_status')!='observed' or e.get('usable_for_pass') is not False or e.get('usable_for_verdict') is not False
        or not isinstance(e.get('value'),str) or len(e['value'].encode())>65536
        or hashlib.sha256(e['value'].encode()).hexdigest()!=WITNESS_SHA):raise ValueError('catalog_source_integrity_required')
    source=json.loads(e['value'])['source'];at=datetime.fromisoformat(source['read_at_utc'].replace('Z','+00:00'))
    if (at.tzinfo is None or not -5<=(current-at).total_seconds()<=3600 or source.get('schema_sha256')!=SCHEMA_SHA
        or source.get('openapi')!='3.1.0'):raise ValueError('catalog_source_hash_recheck_required')
    return source['read_at_utc']

def text(value,maximum):
    if (not isinstance(value,str) or not 0<len(value)<=maximum or any(ord(c)<32 for c in value)
        or re.search(r'(?i)(bearer\s|://|password\s*[:=]|token\s*[:=]|secret\s*[:=])',value)):
        raise ValueError('catalog_string_invalid_or_sensitive')
    return value

def project(raw,kind):
    if not isinstance(raw,list) or len(raw)>128:raise ValueError('catalog_complete_array_required')
    out=[];versions=set()
    for row in raw:
        key='version' if kind=='versions' else 'trays_version';children='trays_info' if kind=='versions' else 'dependency'
        if not isinstance(row,dict) or set(row)!={key,children}:raise ValueError('catalog_row_schema_changed')
        version=text(row[key],64)
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._+-]{0,63}',version) or version in versions:raise ValueError('catalog_version_ambiguous')
        versions.add(version);items=row[children]
        if not isinstance(items,list) or len(items)>32:raise ValueError('catalog_os_budget')
        projected=[];oses=set()
        for item in items:
            if not isinstance(item,dict) or set(item)!=({'os'} if kind=='versions' else {'os','files'}):raise ValueError('catalog_os_schema_changed')
            os_name=text(item['os'],80)
            if os_name in oses:raise ValueError('catalog_os_ambiguous')
            oses.add(os_name);entry={'os':os_name}
            if kind=='dependencies':
                files=item['files']
                if not isinstance(files,list) or len(files)>128:raise ValueError('catalog_files_budget')
                entry['files']=[text(f,260) for f in files]
                if len(set(entry['files']))!=len(entry['files']):raise ValueError('catalog_duplicate_file')
            projected.append(entry)
        out.append({key:version,children:projected})
    return out

def inspect(session,name,kind,jid,cid):
    try:
        r=validate_context(job_store.get_job(jid),cid,{'target':name,'kind':kind})
        witness_at=validate_witness(job_store.get_job(WITNESS_JOB),datetime.now(timezone.utc))
        t,ci,urls=context(session,name);validate_target_state(name,ci,read_json(session,urls[1]))
        path=urlsplit(urls[0]).path;suffix='/agents/'+t['agent_id']+'/tasks'
        if not path.endswith(suffix):raise ValueError('catalog_origin_context_required')
        url=session._same_https_origin_url(urls[0],path[:-len(suffix)]+PATHS[kind])
        if not url:raise ValueError('catalog_same_origin_required')
        response=session.context.request.get(url,timeout=15000)
        if response.status!=200:raise ValueError('catalog_get_unavailable')
        raw=response.json()
        if len(json.dumps(raw,ensure_ascii=False).encode())>65536:raise ValueError('catalog_body_budget')
        catalog=project(raw,kind)
        return {'target':name,'ci_id':t['ci_id'],'agent_id':t['agent_id'],'core_version':CORE,'kind':kind,
            'catalog':catalog,'catalog_entries':len(catalog),'complete_array_observed':True,
            'session_id':session.session_id,'read_at':datetime.now(timezone.utc).isoformat(),
            'source_schema_sha256':SCHEMA_SHA,'operator_schema_hash_rechecked_at':witness_at,
            'available_catalog_only':True,'installation_verified':False,'core_plugin_compatibility_verified':False,
            'remote_session_executed':False,'task_executed':False,'mutation_executed':False,'business_pass':False}
    except Exception as e:return {'error':str(e)[:160] if isinstance(e,ValueError) else 'catalog_observation_unavailable',
        'mutation_executed':False,'business_pass':False}
