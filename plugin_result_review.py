"""Closed GET-only historical content checks, NOT independent OS correctness.

No new task, source adoption, delivery, recovery or permission. Expectations are
explicit intrinsic invariants, not literals learned from the observed payload.
"""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib, ipaddress, json, re
import job_store
from command_probe_contract import target, validate_target_state, CORE
from command_stage_native import context, read_json
from operation_journal import list_operations
from plugin_discovery import shape

TOOL = 'browser_review_plugin_result_semantic'
PROFILE = 'historical-plugin-content-review-v1'
VNC_PROFILE='historical-vnc-start-content-review-v1'
TRAY_PROFILE='historical-tray-start-content-review-v1'
REFS = {
 ('windows','storageAudit'): ('20261016-053350-c9bd531c','tc-54ef84e3','1.3.4'),
 ('astra','storageAudit'): ('20261016-053528-ef0debfc','tc-1a855850','1.3.4'),
 ('windows','defaultNetworkDeviceAudit'): ('20261016-053703-1a9a7b72','tc-c03a6d9b','1.3.5'),
 ('astra','defaultNetworkDeviceAudit'): ('20261016-053853-3e5bc458','tc-2ca30eca','1.3.5'),
 ('windows','vncServer'): ('20261016-154154-eb0465d0','tc-e316ea6c','1.5.5'),
 ('windows','trayControl'): ('20261016-170447-1897a798','tc-bee66593','1.0.1'),
 ('astra','trayControl'): ('20261016-171602-d1f8cb9e','tc-47c91b6e','1.0.1')}
RULES = {
 'storageAudit': ['nonempty_devices','unique_device_ids','positive_integer_capacity',
   'partition_count_matches','nonnegative_integer_partition_lengths','partition_sum_within_capacity',
   'partition_parent_links_match'],
 'defaultNetworkDeviceAudit': ['default_flag_true','interface_name_nonempty','mac_syntax_valid',
   'nonempty_valid_unique_ip_addresses']}

VNC_RULES=['self_reported_version_matches_catalogue','native_plugin_error_not_reported','native_plugin_error_empty']
TRAY_RULES=['start_action_echo_matches','reported_user_lists_well_formed','at_least_one_user_reported_started_or_running']
TRAY_REPLAY_GATE={'same_start_admitted':False,'reason':'owned_start_already_dispatched','framework_policy_replaced':False}
def rules_for(plugin):return TRAY_RULES if plugin=='trayControl' else VNC_RULES if plugin=='vncServer' else RULES[plugin]

def requirement(name, campaign,profile=PROFILE):
    t=target(name)
    if profile not in {PROFILE,VNC_PROFILE,TRAY_PROFILE} or profile==VNC_PROFILE and name!='windows':raise ValueError('review_profile_scope_required')
    selected={'trayControl':TRAY_RULES} if profile==TRAY_PROFILE else {'vncServer':VNC_RULES} if profile==VNC_PROFILE else RULES
    if not isinstance(campaign,str) or not re.fullmatch(r'[a-z0-9-]{1,80}',campaign):
        raise ValueError('review_campaign_required')
    return {'type':'historical_plugin_content_review','locked':True,'stand':'lab',
      'action_profile':'read_only','target':name,'ci_id':t['ci_id'],'agent_id':t['agent_id'],
      'ci_name':t['ci_name'],'core_version':CORE,'profile_id':profile,'campaign_id':campaign,
      'source_refs':{p:list(REFS[name,p]) for p in selected},
      'expected_invariants':deepcopy(selected),'independent_os_oracle':False,
      'historical_only':True,'business_pass':False}

def validate_context(job,cid,args):
    if not isinstance(job,dict) or len(job.get('test_cases',[]))!=1:raise ValueError('single_review_case_required')
    c=job['test_cases'][0];r=c.get('requirement') or {}
    if (c.get('case_id')!=cid or r!=requirement(r.get('target'),r.get('campaign_id'),r.get('profile_id'))
        or job.get('stand')!='lab' or job.get('job_type') not in {'manual','regression'}
        or job.get('status')!='running' or c.get('status')!='running'
        or job.get('resources') or not isinstance(args,dict) or set(args)!={'target','plugin_name'}
        or args.get('target')!=r['target'] or args.get('plugin_name') not in r['expected_invariants']):
        raise ValueError('locked_result_review_required')
    if not isinstance(job.get('request'),str) or not all(r[k] in job['request'] for k in
            ['ci_id','agent_id','ci_name','profile_id']):raise ValueError('original_review_request_required')
    return r

def integer(v):
    # Explicit OS representation mapping; bool, NaN, exponent strings and blanks refused.
    if type(v) not in {str,int,float}:raise ValueError('integer_representation_required')
    if isinstance(v,str) and not re.fullmatch(r'[0-9]+',v):raise ValueError('decimal_integer_string_required')
    try:n=Decimal(str(v))
    except InvalidOperation:raise ValueError('integer_representation_required')
    if not n.is_finite() or n!=n.to_integral_value() or n<0 or n>2**64-1:
        raise ValueError('bounded_nonnegative_integer_required')
    return int(n)

def content_checks(plugin,data):
    """No raw IP/MAC/serial/device names are returned, including failures."""
    checks=[]
    def add(rule,fn):
        try:passed=bool(fn());state='PASS' if passed else 'FAIL'
        except (ValueError,TypeError,KeyError,AttributeError,OverflowError):state='BLOCKED'
        checks.append({'rule':rule,'status':state})
    if plugin=='defaultNetworkDeviceAudit':
        add('default_flag_true',lambda:type(data['isDefault']) is bool and data['isDefault'] is True)
        add('interface_name_nonempty',lambda:isinstance(data['name'],str) and bool(data['name'].strip()))
        add('mac_syntax_valid',lambda:isinstance(data['macAddress'],str) and bool(re.fullmatch(
            r'(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}|(?:[0-9A-Fa-f]{2}-){5}[0-9A-Fa-f]{2}',data['macAddress'])))
        def ips():
            values=data['ipAddresses']
            if not isinstance(values,list) or not 0<len(values)<=256 or not all(isinstance(v,str) for v in values):return False
            # CIDR/zone are not silently removed; mapping requires a separate contract.
            if any('/' in v or '%' in v for v in values):raise ValueError('address_representation_unmapped')
            try:parsed=[ipaddress.ip_address(v) for v in values]
            except ValueError:return False
            return len(set(parsed))==len(parsed)
        add('nonempty_valid_unique_ip_addresses',ips)
    elif plugin=='storageAudit':
        add('nonempty_devices',lambda:isinstance(data,list) and 0<len(data)<=256 and all(isinstance(d,dict) for d in data))
        add('unique_device_ids',lambda:all(isinstance(d['device_id'],str) and d['device_id'] for d in data)
            and len({d['device_id'] for d in data})==len(data))
        add('positive_integer_capacity',lambda:all(integer(d['size'])>0 for d in data))
        def partitions(d):
            parts=d['disk']['partitions']
            if not isinstance(parts,list) or len(parts)>4096 or not all(isinstance(p,dict) for p in parts):
                raise ValueError('partition_array_required')
            return parts
        add('partition_count_matches',lambda:all(integer(d['disk']['partitions_quantity'])==len(partitions(d)) for d in data))
        add('nonnegative_integer_partition_lengths',lambda:all(integer(p['partition_length'])>=0 for d in data for p in partitions(d)))
        # Schema names alone do NOT prove byte units or parent-key semantics.
        # Preserve these desired checks as explicitly BLOCKED until source/OS proof.
        checks.extend({'rule':rule,'status':'BLOCKED'} for rule in
                      ['partition_sum_within_capacity','partition_parent_links_match'])
    elif plugin=='vncServer':
        add('self_reported_version_matches_catalogue',lambda:data['plugin']=='VncServer' and data['version']=='1.5.5')
        # Only the observed explicit error representation is grounded here.
        # Other result tokens are not invented positive-success contracts.
        checks.append({'rule':'native_plugin_error_not_reported',
            'status':'FAIL' if isinstance(data,dict) and data.get('result')=='error' else 'BLOCKED'})
        add('native_plugin_error_empty',lambda:data['error'] in ('',None))
    elif plugin=='trayControl':
        add('start_action_echo_matches',lambda:data['action']=='start')
        def lists():
            return all(isinstance(data[k],list) and len(data[k])<=10000 for k in ['started','already_running'])
        add('reported_user_lists_well_formed',lists)
        def any_user():
            if not lists():raise ValueError('reported_user_lists_required')
            return bool(data['started'] or data['already_running'])
        add('at_least_one_user_reported_started_or_running',any_user)
    else:raise ValueError('review_plugin_not_admitted')
    assert [c['rule'] for c in checks]==rules_for(plugin)
    return {'checks':checks,'intrinsic_status':'FAIL' if any(c['status']=='FAIL' for c in checks) else
        'BLOCKED' if any(c['status']=='BLOCKED' for c in checks) else 'PASS',
        'independent_os_correctness':'BLOCKED','full_source_case_status':'BLOCKED',
        'business_pass':False,'raw_values_emitted':False}

def compact_review(parsed):
    """Bounded historical model context, no raw values or permission authority."""
    if not isinstance(parsed,dict):return {}
    name,plugin=parsed.get('target'),parsed.get('plugin_name')
    if (name,plugin) not in REFS:return {}
    sj,sc,version=REFS[name,plugin]
    if (parsed.get('source_job_id'),parsed.get('source_case_id'),parsed.get('plugin_version'))!=(sj,sc,version):return {}
    if any(parsed.get(k) is not v for k,v in {'business_pass':False,'historical_only':True,'same_recorded_payload':True}.items()):return {}
    checks=parsed.get('checks')
    if not isinstance(checks,list) or len(checks)!=len(rules_for(plugin)):return {}
    if [x.get('rule') for x in checks if isinstance(x,dict)]!=rules_for(plugin):return {}
    if any(x.get('status') not in {'PASS','FAIL','BLOCKED'} for x in checks):return {}
    expected='FAIL' if any(x['status']=='FAIL' for x in checks) else 'BLOCKED' if any(x['status']=='BLOCKED' for x in checks) else 'PASS'
    if (parsed.get('intrinsic_status')!=expected or parsed.get('independent_os_correctness')!='BLOCKED'
        or parsed.get('full_source_case_status')!='BLOCKED'):return {}
    extra={}
    if plugin=='trayControl':
        if parsed.get('replay_gate')!=TRAY_REPLAY_GATE:return {}
        extra['replay_gate']=deepcopy(TRAY_REPLAY_GATE)
    return {**extra,'target':name,'plugin_name':plugin,'plugin_version':version,'source_job_id':sj,'source_case_id':sc,
      'checks':[{'rule':x['rule'],'status':x['status']} for x in checks],
      'intrinsic_status':expected,'independent_os_correctness':'BLOCKED','full_source_case_status':'BLOCKED',
      'historical_only':True,'business_pass':False,'historical_projection_not_permission':True}

def inspect(session,name,plugin,jid,cid):
    try:
        r=validate_context(job_store.get_job(jid),cid,{'target':name,'plugin_name':plugin})
        source_jid,source_cid,version=REFS[name,plugin]
        source=job_store.get_job(source_jid);c=next(c for c in source['test_cases'] if c['case_id']==source_cid)
        req=c['requirement']
        if (req['target'],req['plugin_name'],req['plugin_version'])!=(name,plugin,version):raise ValueError('source_scope_changed')
        cycles=[e for e in c['evidence'] if e['type']=='model_plugin_discovery_cycle']
        if len(cycles)!=1:raise ValueError('unique_source_runtime_required')
        cycle=json.loads(cycles[0]['value']);report=cycle['canonical_report'];ops=list_operations(source_jid)
        if cycle.get('completed') is not True or len(ops)!=1 or ops[0]['status']!='verified':raise ValueError('verified_source_required')
        if plugin=='trayControl' and req.get('profile_id')!='supplied-tray-plugin-start-v1':raise ValueError('tray_start_replay_scope_required')
        task=report['task_id']
        if ops[0]['verification']['identifier_value']!=task or ops[0]['verification']['evidence_id']!=report['read_evidence_id']:
            raise ValueError('source_own_receipt_link_required')
        t,ci,urls=context(session,name);validate_target_state(name,ci,read_json(session,urls[1]))
        full=read_json(session,urls[0]+'/'+task+'/full');env=full.get('result')
        task_name='VncServer' if plugin=='vncServer' else plugin
        if (full.get('id'),full.get('agent_id'),full.get('name'),full.get('status'))!=(task,r['agent_id'],task_name,'success'):
            raise ValueError('historical_full_identity_required')
        if not isinstance(env,dict) or env.get('machine_uid')!=r['ci_id'] or env.get('result')!='success':raise ValueError('historical_envelope_required')
        census=shape(env['data'])
        if census!=report['response_shape']:raise ValueError('historical_result_changed')
        result=content_checks(plugin,env['data'])
        if plugin=='trayControl':
            # Source is an already-dispatched owned start. Its existing create
            # guard rejects another campaign; expose that gate, do not grant it.
            result['replay_gate']=deepcopy(TRAY_REPLAY_GATE)
        return {**result,'target':name,'plugin_name':plugin,'plugin_version':version,'core_version':CORE,
          'source_job_id':source_jid,'source_case_id':source_cid,'source_runtime_evidence_id':cycles[0]['evidence_id'],
          'source_full_evidence_id':report['read_evidence_id'],'task_id':task,'processed_at':env.get('processed_at'),
          'read_at':datetime.now(timezone.utc).isoformat(),'source_sha256':census['sha256'],
          'same_recorded_payload':True,'historical_only':True,'new_agent_tasks':0,'mutation_executed':False}
    except Exception:
        # Never echo exception values from remote payloads.
        return {'error':'result_review_unavailable','intrinsic_status':'BLOCKED','business_pass':False,'mutation_executed':False}
