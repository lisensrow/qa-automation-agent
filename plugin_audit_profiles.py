"""Reviewed parameterless inventory subset; never a whole Zephyr-case oracle."""
import hashlib
import json
import math
from copy import deepcopy

PROFILES={
 'driveDeviceAudit':('1.3.5',1,{'fsType':'str','mountPoint':'str','serialNumber':'str','size':'number','type':'str','uid':'str'}),
 'gpuDeviceAudit':('1.3.2',2,{'name':'str','note':'str'}),
 'softAudit':('1.3.8',3,{'developer':'str','exePath':'str','installedAt':'str','name':'str','note':'str','owner':'str','version':'str'}),
 'smbiosAudit':('1.3.8',5,{'system_information':'list','processor_information':'list','memory_device':'list'}),
 'networkDeviceAudit':('1.5.1',6,{'name':'str','macAddress':'str','ipAddresses':'list','ipv4Dns':'list','ipv6Dns':'list',
     'ipv4Gateway':'list','ipv6Gateway':'list','dhcp4Enabled':'bool','dhcp6Enabled':'bool','is_default':'bool','is_physical':'bool'}),
 'serviceAudit':('1.3.2',7,{'command':'str','displayName':'str','name':'str','owner':'str','startMode':'str','uid':'str'}),
 'displayDeviceAudit':('1.3.2',8,{'diagonal':'number','manufacturer':'str','model':'str','name':'str','serial':'str'}),
 'processMonitoring':('1.3.2',9,{'command':'str','cpuUsagePercent':'number','executablePath':'str',
     'memoryResidential':'number','memoryUsagePercent':'number','memoryVirtual':'number','name':'str',
     'numThreads':'number','owner':'str','pid':'number','ppid':'number','uid':'str'}),
 'baseSystemMonitoring':('1.3.3',10,{'cpuUsage':'list','drives':'list','hostAddress':'str','ramUsage':'number',
     'ramUsagePercent':'number','uptime':'number','usersOnline':'list'})}

def profile(name):
    version,step,fields=PROFILES[name]
    return {'task_name':name,'plugin_version':version,'step':step,'required_fields':deepcopy(fields),
        'container':'dict' if name in {'smbiosAudit','baseSystemMonitoring'} else 'list',
        'oracle_kind':'legacy_template_structure_subset','full_case_passed':False,
        'value_completeness_verified':False}

def version_allowed(name,version):
    return name in PROFILES and PROFILES[name][0]==version

def summarize(name,data):
    p=profile(name)
    container='dict' if isinstance(data,dict) else 'list' if isinstance(data,list) else type(data).__name__
    rows=data if isinstance(data,list) else [data]
    checks={'container':container==p['container'],'bounded':len(rows)<=10000,'nonempty':bool(data)}
    counts={k:0 for k in p['required_fields']};malformed=0
    types={'str':lambda v:isinstance(v,str),'bool':lambda v:type(v) is bool,
        'list':lambda v:isinstance(v,list),'number':lambda v:type(v) in (int,float) and math.isfinite(v)}
    if checks['container'] and checks['bounded']:
        for row in rows:
            if not isinstance(row,dict): malformed+=1;continue
            for key,kind in p['required_fields'].items():
                counts[key]+=int(key in row and types[kind](row[key]))
    checks['object_rows']=malformed==0 and checks['container']
    for key,count in counts.items(): checks['field.'+key]=bool(rows) and count==len(rows) and checks['container'] and checks['bounded']
    return {'container':container,'item_count':len(rows) if checks['container'] else None,
        'checks':checks,'field_valid_counts':counts,'structure_subset_matched':all(checks.values()),
        'data_sha256':hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),
        'full_case_passed':False,'value_completeness_verified':False}

def scopes(req):
    s=req['pinned_audit_task'];p=profile(s['task_name'])
    audit={**s,'plugin_name':s['task_name'],'plugin_version':p['plugin_version']}
    delivery={'ci_name':s['ci_name'],'agent_id':s['agent_id'],'core_version':s['core_version'],
        'plugin_name':s['task_name'],'version':p['plugin_version']}
    return audit,delivery

def stages_for(req):
    audit,delivery=scopes(req);ci_id=req['ci_id'];name=audit['task_name']
    stages=[]
    for sid,tool,args,task in [
        ('deliver-plugin','browser_deliver_pinned_agent_plugin_semantic',delivery,'managePlugin'),
        ('refresh-plugin-inventory','browser_create_pinned_agent_audit_semantic',{**audit,'task_name':'pluginAudit'},'pluginAudit'),
        ('execute-audit','browser_create_pinned_agent_audit_semantic',audit,name)]:
        stages.append({'version':1,'workflow_id':'pinned-plugin-audit-v1','stage_id':sid,
            'resource_key':'agent-'+audit['agent_id']+'-'+name+'-'+sid,'tool':tool,'arguments':args,
            'verification':{'version':1,'kind':'owned_plugin_audit_execution','ci_id':ci_id,
                'agent_id':audit['agent_id'],'task_name':task,'plugin_name':name,
                'plugin_version':audit['plugin_version'],'origin':'https://uc.lab.local'}})
    return stages[1:] if req.get('prior_verified_delivery') else stages

def validate_prior_delivery(req,loader=None,operations=None):
    ref=req.get('prior_verified_delivery')
    if ref is None:return
    if loader is None:
        import job_store
        loader=job_store.get_job
    if operations is None:
        from operation_journal import list_operations
        operations=list_operations
    if not isinstance(ref,dict) or set(ref)!={'job_id','case_id','operation_id'}:raise ValueError('delivery_reference_invalid')
    old=loader(ref['job_id']) or {};c=next(c for c in old['test_cases'] if c['case_id']==ref['case_id']);r=c['requirement']
    ledger=operations(ref['job_id']);op=next(o for o in ledger if o['operation_id']==ref['operation_id'])
    from operation_journal import _fingerprint
    original={**req};original.pop('prior_verified_delivery',None);stage=stages_for(original)[0]
    proof=op.get('verification') or {}
    if (old.get('stand')!='lab' or r.get('type')!='pinned_plugin_audit' or r.get('locked') is not True
        or r.get('pinned_audit_task')!=req['pinned_audit_task'] or r.get('ci_id')!=req['ci_id']
        or r.get('pinned_plugin_delivery')!=scopes(req)[1]
        or op.get('case_id')!=ref['case_id'] or op.get('status')!='verified'
        or any(o['status'] not in {'verified','not_sent'} for o in ledger)
        or any(op.get(k)!=stage[k] for k in ('workflow_id','stage_id','resource_key','tool'))
        or op.get('arguments_fingerprint')!=_fingerprint(stage['arguments'])
        or op.get('verification_fingerprint')!=_fingerprint(stage['verification'])
        or proof.get('postcondition_verified') is not True or proof.get('business_pass') is not False
        or not any(e['evidence_id']==proof.get('evidence_id') and e.get('source')=='uqa_tool' for e in c['evidence'])):
        raise ValueError('prior_verified_delivery_required_no_rekey')

def validate_context(job,case_id):
    c=next(c for c in job['test_cases'] if c['case_id']==case_id);r=c['requirement'];s=r['pinned_audit_task']
    p=profile(s['task_name']);audit,delivery=scopes(r)
    if (job.get('stand')!='lab' or job.get('status')!='running' or job.get('resources')
        or c.get('status')!='running' or r.get('type')!='pinned_plugin_audit' or r.get('locked') is not True
        or r.get('action_profile')!='write_resource' or s.get('core_version')!='1.3.27'
        or set(s)!={'ci_name','agent_id','core_version','task_name'} or not r.get('ci_id')
        or r.get('expected_profile')!=p or r.get('allow_plugin_audit_refresh') is not True
        or r.get('pinned_plugin_delivery')!=delivery or r.get('operation_stages')!=stages_for(r)
        or any(str(v) not in job['request'] for v in audit.values()) or 'pluginAudit' not in job['request']
        or r.get('source_case') not in {'US-T79','US-T102'}
        or r.get('source_revision')!='1.0-read-2026-10-16'
        or any(e.get('type')=='pinned_plugin_runtime_started' for e in c.get('evidence',[]))):
        raise ValueError('locked_plugin_profile_context_invalid')
    validate_prior_delivery(r)
    return c,r

def build_report(job,case_id,task_id):
    c=next(c for c in job['test_cases'] if c['case_id']==case_id);r=c['requirement'];p=profile(r['pinned_audit_task']['task_name'])
    if r.get('locked') is not True or r.get('expected_profile')!=p: return {'error':'plugin_report_scope_invalid'}
    found=[]
    for e in c['evidence']:
        if e.get('source')!='uqa_tool' or e.get('execution_status') not in {'observed','executed'}: continue
        try: b=json.loads(e['value']);a=b['result']
        except (ValueError,KeyError,TypeError):continue
        if (b.get('tool')=='browser_inspect_pinned_agent_audit_semantic' and a.get('task_id')==task_id
            and a.get('task_name')==p['task_name'] and a.get('agent_id')==r['pinned_audit_task']['agent_id']
            and a.get('ci_id')==r['ci_id'] and a.get('native_result_verified') is True):found.append((e,a))
    if not found:return {'error':'native_own_plugin_result_required'}
    e,a=found[-1];summary=a.get('audit_data_summary') or {}
    if not summary.get('checks'):return {'error':'plugin_summary_required'}
    md=['# '+p['task_name']+': '+r['pinned_audit_task']['ci_name'],'','Вердикт: BLOCKED',
        'Task ID: '+task_id,'','| Проверка | Ожидание | Фактически | Статус |','| --- | --- | --- | --- |']
    md += ['| '+k+' | true | '+str(v)+' | '+('PASS' if v else 'BLOCKED')+' |' for k,v in summary['checks'].items()]
    md += ['', 'Получено объектов: '+str(summary.get('item_count')), 'Источник: '+r['source_case']+' v1.0, шаг '+str(p['step'])+'.',
        'BLOCKED: структура проверена как subset; независимая полнота данных/оборудования и UI ещё не проверены. '
        'Старые UUID/примеры не подставлены как точный эталон; расхождение не объявлено developer-confirmed bug.',
        'Доказательство: '+e['evidence_id']+'. Zephyr не изменялся.']
    return {'report_type':'locked_plugin_subset','verdict':'BLOCKED','task_id':task_id,
        'report_markdown':'\n'.join(md),'summary':summary,'source_evidence_ids':[e['evidence_id']],
        'full_case_passed':False,'zephyr_written':False,'product_mutation_executed':False}
