"""Bounded model-driven osAudit case runtime; no target IDs or operator script.

This is an explicitly prepared legacy-baseline profile, not general regression
planning. The model selects actions; Core owns permission, journal and oracle.
"""
import json
import re
from copy import deepcopy
import job_store as store
from operation_journal import list_operations, reconcile_operation
from audit_operation_recovery import stages_for
from tools.agent_update import validate_locked_update_scope

TOOL_NAMES = frozenset({'knowledge_search','browser_open_page','browser_get_state',
    'browser_open_agent_tasks_semantic','browser_inspect_pinned_agent_readiness_semantic',
    'browser_create_pinned_agent_audit_semantic','browser_inspect_pinned_agent_audit_semantic',
    'agent_build_pinned_audit_report'})
PROFILE_RULE = ('Typed audit profile: the canonical final expected/actual report is built by '
    'agent_build_pinned_audit_report from locked native evidence. Use that report for the final answer. '
    'Do not generate UQA_CHECKS_JSON or invent observation/evidence IDs in this profile. '
    'A legacy_baseline_contract_review_required result is BLOCKED, not a confirmed product FAIL. '
    'If current plugin inventory is stale, the declared workflow permits one pluginAudit refresh before osAudit. '
    'Read only the task_id actually returned by create. Core verifies execution journal entries from native readback; '
    'execution verification is not business PASS. This does not change expected or grant action permission.')


def admitted_catalog(tools, trace, scope):
    """Expose only a phase backed by native facts; never synthesize an action.

    This deterministic workflow admission is framework assistance, not freeform
    model planning. Native policy, current preflight and journal still decide.
    """
    names={'knowledge_search','browser_get_state'}
    pins={}
    creates=[t['result'] for t in trace if t['tool']=='browser_create_pinned_agent_audit_semantic'
             and t['result'].get('mutation_executed') is True]
    pending=next((r for r in reversed(creates) if not any(
        t['tool']=='browser_inspect_pinned_agent_audit_semantic'
        and t['result'].get('task_id')==r['task_id']
        and (t['result'].get('operation_verification') or {}).get('verified') is True for t in trace)),None)
    if pending:
        names.add('browser_inspect_pinned_agent_audit_semantic')
        pins={'task_id':pending['task_id'],'ci_name':scope['ci_name'],'agent_id':scope['agent_id']}
    elif any(r.get('task_name')=='osAudit' for r in creates):
        names.add('agent_build_pinned_audit_report')
    else:
        names.update({'browser_open_page','browser_open_agent_tasks_semantic',
            'browser_inspect_pinned_agent_readiness_semantic'})
        readiness=None
        for t in trace:
            if t['tool']=='browser_inspect_pinned_agent_readiness_semantic': readiness=t['result']
            elif t['tool']=='browser_inspect_pinned_agent_audit_semantic' and t['result'].get('plugin_readiness'):
                readiness=t['result']['plugin_readiness']
        if readiness and readiness.get('ready') is True:
            pins=scope
            names.add('browser_create_pinned_agent_audit_semantic')
        elif (readiness and (readiness.get('plugin_audit') or {}).get('reason')=='plugin_audit_stale'
                and not any(r.get('task_name')=='pluginAudit' for r in creates)):
            pins={**scope,'task_name':'pluginAudit'}
            names.add('browser_create_pinned_agent_audit_semantic')
    catalog=deepcopy([t for t in tools if t['function']['name'] in names])
    for t in catalog:
        if t['function']['name'] in {'browser_create_pinned_agent_audit_semantic','browser_inspect_pinned_agent_audit_semantic'}:
            for k,v in pins.items():
                t['function']['parameters']['properties'][k]['enum']=[v]
            if pins:
                schema=t['function']['parameters']
                schema['properties']={k:v for k,v in schema['properties'].items() if k in pins}
                schema['required']=list(pins)
    return catalog


def call_admitted(catalog, name, args):
    tool=next((t['function'] for t in catalog if t['function']['name']==name),None)
    if not tool or not isinstance(args,dict): return False
    schema=tool['parameters']; props=schema.get('properties',{})
    return (all(k in args for k in schema.get('required',[]))
        and (schema.get('additionalProperties') is not False or set(args)<=set(props))
        and all('enum' not in props.get(k,{}) or v in props[k]['enum'] for k,v in args.items()))


def admission_refusal(catalog):
    """Facts about current tool preconditions, not an injected operator prompt."""
    permitted=[]
    for t in catalog:
        fn=t['function'];props=fn['parameters'].get('properties',{})
        if fn['name'] in {'browser_create_pinned_agent_audit_semantic','browser_inspect_pinned_agent_audit_semantic'}:
            permitted.append({'tool':fn['name'],'exact_arguments':{
                k:v['enum'][0] for k,v in props.items() if len(v.get('enum',[]))==1}})
    return {'error':'audit_profile_tool_not_admitted','executed':False,'mutation_executed':False,
        'current_native_fact_bound_operations':permitted,'automatic_action_taken':False}


def validate_context(job, case_id):
    if (not isinstance(job, dict) or job.get('status') != 'running' or job.get('resources')
            or job.get('job_type') not in {'manual','regression'}):
        raise ValueError('pinned_audit_job_context_invalid')
    case = next((c for c in job.get('test_cases',[]) if c.get('case_id') == case_id), {})
    req = case.get('requirement') or {}
    if (case.get('status') != 'running' or req.get('type') != 'pinned_agent_audit'
            or req.get('action_profile') != 'write_resource'
            or req.get('oracle_kind') != 'legacy_os_baseline_comparison'
            or not isinstance(req.get('baseline_ref'),dict)
            or set(req['baseline_ref']) != {'job_id','case_id','evidence_id'}
            or not re.fullmatch(r'[0-9a-f]{64}', str(req.get('baseline_sha256') or ''))):
        raise ValueError('pinned_audit_case_context_invalid')
    scope = req.get('pinned_audit_task') or {}
    validate_locked_update_scope(job, case, scope, 'pinned_audit_task')
    expected = req.get('expected_subset')
    stage = req.get('operation_stage') or {}
    if (scope.get('task_name') != 'osAudit' or scope.get('core_version') != '1.3.27'
            or stage.get('version') != 1 or stage.get('tool') != 'browser_create_pinned_agent_audit_semantic'
            or stage.get('arguments') != scope
            or not {'workflow_id','stage_id','resource_key'} <= set(stage)
            or not isinstance(expected,dict)
            or set(expected) != {'host_name','machine_uid','os'}
            or expected.get('host_name') != scope['ci_name'] or not isinstance(expected.get('os'),dict)
            or set(expected['os']) != {'architecture','current_build_os','family','name','version'}
            or any(not isinstance(v,str) or not v or len(v)>256 for v in expected['os'].values())):
        raise ValueError('pinned_audit_oracle_or_stage_invalid')
    stages=stages_for(scope,expected['machine_uid'])
    if (req.get('allow_plugin_audit_refresh') is not True or 'pluginAudit' not in job.get('request','')
            or req.get('operation_stages')!=stages or stage!=stages[-1]):
        raise ValueError('declared_audit_execution_stages_required')
    if any(e.get('type') == 'pinned_audit_runtime_started' for e in case.get('evidence',[])):
        raise ValueError('pinned_audit_already_started_no_resend')
    return case, req


def validate_baseline(job, req, loader=store.get_job):
    """Bind expected to an earlier primary snapshot, not a model invented oracle."""
    ref=req['baseline_ref']
    patterns={'job_id':r'\d{8}-\d{6}-[0-9a-f]{8}','case_id':r'tc-[0-9a-f]{8}',
              'evidence_id':r'ev-[0-9a-f]{12}'}
    if any(not re.fullmatch(pattern,str(ref.get(k,''))) for k,pattern in patterns.items()):
        raise ValueError('historical_baseline_reference_invalid')
    if ref['job_id']==job['job_id']: raise ValueError('baseline_must_precede_current_job')
    prior=loader(ref['job_id']) or {}
    case=next((c for c in prior.get('test_cases',[]) if c.get('case_id')==ref['case_id']),{})
    e=next((e for e in case.get('evidence',[]) if e.get('evidence_id')==ref['evidence_id']),{})
    if (prior.get('job_id')!=ref['job_id'] or prior.get('stand')!=job.get('stand')
            or e.get('source')!='operator_existing_task_list_and_full_get'
            or e.get('execution_status')!='observed' or e.get('type')!='operator_historical_os_task_shape_v298'):
        raise ValueError('registered_historical_baseline_required')
    body=json.loads(e.get('value','{}')); full=body.get('full') or {}
    result=full.get('result') or {}; data=result.get('data') or {}
    expected=req['expected_subset']; os_data=data.get('os') or {}
    if (body.get('full_sha256')!=req['baseline_sha256'] or body.get('identity_correlated') is not True
            or body.get('historical_result_only') is not True or body.get('new_task_created') is not False
            or full.get('agent_id')!=req['pinned_audit_task']['agent_id'] or full.get('name')!='osAudit'
            or data.get('host_name')!=expected['host_name'] or result.get('machine_uid')!=expected['machine_uid']
            or {k:os_data.get(k) for k in expected['os']}!=expected['os']):
        raise ValueError('historical_baseline_hash_identity_or_expected_changed')


def run(api, messages, job_id, case_id, action_policy, force_read_only=False):
    if force_read_only or action_policy != 'confirm_mutations':
        return {'status':'blocked','reason':'pinned_audit_managed_policy_required','started':False}
    try:
        job = api.get_job(job_id)
        case, req = validate_context(job, case_id)
        validate_baseline(job,req)
        if list_operations(job_id):
            raise ValueError('pinned_audit_operation_exists_no_resend')
    except (ValueError,TypeError,KeyError,AttributeError,OSError) as exc:
        return {'status':'blocked','reason':str(exc),'started':False}
    from tools.browser import _session
    from tools.registry import TOOLS
    store.add_evidence(job_id,case_id,'pinned_audit_runtime_started',json.dumps({
        'mode':'bounded_model_legacy_audit_profile','prepared_scope_oracle_catalog':True,
        'ordinary_freeform_entry':False,'policy_replaced':False}),source='uqa_audit_runtime',
        execution_status='observed',usable_for_pass=False,usable_for_verdict=False,
        eligibility_reason='runtime_reservation_not_product_evidence')
    trace=[]; report=''; memory=[]; error_type=None; errors={}
    try:
        _session.reset_case_context()
        messages.append({'role':'system','content':PROFILE_RULE})
        memory=api.append_reviewed_product_memory(messages,job['request'],job_id,case_id,action_policy)
        for turn in range(22):
            catalog=admitted_catalog(TOOLS,trace,req['pinned_audit_task'])
            response=api.ask_ollama(messages,tools=catalog)
            message=response.get('message') or {}; calls=message.get('tool_calls') or []
            content=str(message.get('content') or '')
            messages.append({'role':'assistant','content':content,**({'tool_calls':calls} if calls else {})})
            if not calls: report=content; break
            for call in calls:
                fn=call.get('function') or {}; name=fn.get('name'); args=fn.get('arguments') or {}
                if isinstance(args,str): args=json.loads(args)
                # Recompute after each actual result, including multi-call turns.
                catalog=admitted_catalog(TOOLS,trace,req['pinned_audit_task'])
                if name not in TOOL_NAMES or not call_admitted(catalog,name,args):
                    result=admission_refusal(catalog)
                else:
                    result=api.execute_tool_with_policy(name,args,messages,action_policy=action_policy,
                        job_id=job_id,case_id=case_id)
                    obs=api.record_tool_observations(job_id,case_id,name,args,result)
                    e=api.record_tool_evidence(job_id,case_id,name,args,result,
                        observation_ids=[o['observation_id'] for o in obs])
                    if isinstance(e,dict): result['uqa_evidence_id']=e['evidence_id']
                    if (name=='browser_inspect_pinned_agent_audit_semantic'
                            and result.get('native_result_verified') is True and isinstance(e,dict)):
                        receipt=next((t['result'] for t in reversed(trace)
                            if t['tool']=='browser_create_pinned_agent_audit_semantic'
                            and t['result'].get('task_id')==result.get('task_id')),{})
                        if receipt.get('operation_id'):
                            proof=reconcile_operation(job_id,receipt['operation_id'],e['evidence_id'])
                            result['operation_verification']=proof
                            store.add_evidence(job_id,case_id,'audit_operation_verification',json.dumps(proof),
                                source='uqa_execution_journal',execution_status='observed',usable_for_pass=False,
                                usable_for_verdict=False,eligibility_reason='execution_bookkeeping_not_business_PASS')
                trace.append({'tool':name,'arguments':args,'result':result})
                print('MODEL_CYCLE_STEP='+json.dumps({'step':len(trace),'tool':name,'error':result.get('error')}),flush=True)
                messages.append({'role':'tool','tool_name':name,'content':json.dumps(api.tool_result_for_model(name,result),ensure_ascii=False)})
                if result.get('error'):
                    key=(name,json.dumps(args,sort_keys=True));errors[key]=errors.get(key,0)+1
                    if errors[key]>=2: raise RuntimeError('repeated_model_no_progress')
    except (Exception,KeyboardInterrupt) as exc:
        error_type=type(exc).__name__
    finally:
        created=[t for t in trace if t['tool']=='browser_create_pinned_agent_audit_semantic'
                 and t['result'].get('mutation_executed') is True and t['result'].get('task_name')=='osAudit']
        refreshes=[t for t in trace if t['tool']=='browser_create_pinned_agent_audit_semantic'
                   and t['result'].get('mutation_executed') is True and t['result'].get('task_name')=='pluginAudit']
        reads=[t for t in trace if t['tool']=='browser_inspect_pinned_agent_audit_semantic'
               and t['result'].get('native_result_verified') is True and t['result'].get('task_name')=='osAudit']
        reports=[t['result'] for t in trace if t['tool']=='agent_build_pinned_audit_report' and t['result'].get('report_type')=='locked_audit_subset']
        canonical=reports[-1] if reports else None
        recipe=any(r.get('source')=='UQA-experience/UQA_PLUGIN_TASKS_KNOWLEDGE.md' for m in memory for r in m.get('results',[]))
        oracle=reads[-1]['result'].get('locked_comparison',{}) if reads else {}
        verdict=oracle.get('status')
        ready=bool(created and created[0]['result'].get('native_preflight',{}).get('fresh_osAudit_1_3_4_loaded_checked') is True)
        consistent=bool(report and canonical and created and created[0]['result']['task_id'] in report
                        and isinstance(verdict,str) and verdict in report.upper())
        operations=list_operations(job_id)
        journal_verified=bool(created and all(o['status'] in {'verified','not_sent'} for o in operations)
            and any(o['operation_id']==created[0]['result'].get('operation_id') and o['status']=='verified' for o in operations))
        completed=bool(recipe and len(created)==1 and len(refreshes)<=1 and reads and canonical and ready and consistent and journal_verified
                       and canonical['verdict']==verdict and not error_type)
        payload={'trace':trace,'model_report':report,'canonical_report':canonical,'oracle':oracle,
            'memory_recipe_retrieved':recipe,'automatic_core_memory_reads':len(memory),
            'model_selected_case_cycle_completed':completed,'report_consistent':consistent,
            'prepared_scope_oracle_catalog':True,'ordinary_freeform_entry':False,
            'operator_runtime_hints':0,'operator_product_actions':0,'synthetic_product_action_calls':0,
            'framework_context_reset':True,'error_type':error_type,'zephyr_written':False}
        payload['framework_phase_admission']=True
        payload.update(journal_execution_verified=journal_verified,plugin_inventory_refresh_count=len(refreshes))
        e=store.add_evidence(job_id,case_id,'bounded_local_model_cycle_trace',json.dumps(payload,ensure_ascii=False),
            source='uqa_model_audit_runtime',execution_status='observed',usable_for_pass=False,usable_for_verdict=False,
            eligibility_reason='bounded_model_profile_not_full_product_regression')
        result=canonical['report_markdown'] if canonical else (report or 'Model cycle incomplete; inspect evidence, never resend blindly.')
        status=canonical['verdict'].lower() if completed else 'blocked'
        store.update_test_case(job_id,case_id,status=status,result=result)
        store.set_job_status(job_id,status)
        _session.close()
    return {'status':'completed' if completed else 'blocked','reason':None if completed else 'audit_model_cycle_incomplete',
            'completed':completed,'started':True,'business_verdict':canonical['verdict'] if canonical else None,
            'journal_execution_verified':journal_verified,'plugin_inventory_refresh_count':len(refreshes),
            'trace_evidence_id':e['evidence_id'],'ordinary_freeform_entry':False}
