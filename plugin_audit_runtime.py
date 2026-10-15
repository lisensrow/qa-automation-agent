"""Model-selected bounded plugin lifecycle, with disclosed framework admission."""
from copy import deepcopy
from datetime import datetime,timezone
import json
import hashlib
import job_store as store
from operation_journal import list_operations,reconcile_operation
from plugin_audit_profiles import validate_context,stages_for,scopes
from tools.agent_update import audit_result_is_fresh
from agent_audit_runtime import call_admitted

CREATE='browser_create_pinned_agent_audit_semantic';DELIVER='browser_deliver_pinned_agent_plugin_semantic'
READ='browser_inspect_pinned_agent_audit_semantic';READY='browser_inspect_pinned_agent_readiness_semantic'
REPORT='agent_build_pinned_audit_report'
REFRESH='refresh_bound_plugin_inventory'
RUN_AUDIT='run_bound_plugin_audit'

DOMAIN_PROMPT=('You are UQA executing a prepared, immutable, bounded inventory-plugin case on an authorized lab agent. '
    'Choose tools only from the currently admitted catalogue and copy exact own task IDs from native results. '
    'Core policy, locked expected, journal, OS compatibility and replay protection are mandatory. '
    'Delivery is not load verification; pluginAudit is not the main plugin audit. Complete each admitted remaining stage. '
    'After reading the main audit, first call agent_build_pinned_audit_report for that exact task, then return its '
    'expected/actual report with task ID and verdict. Do not skip that call by answering in prose. '
    'A whole-case BLOCKED for independent completeness is not a reason to omit executable safe stages or the canonical report. '
    'If a real tool/prerequisite fails, do not invent facts or resend uncertain actions. No UQA_CHECKS_JSON: this typed '
    'workflow has its own canonical report contract. No Jira/Zephyr write, unrelated agent, downgrade, deletion, '
    'security change or arbitrary OS command. Historical samples are not literal current-machine expectations.')

def scoped_model_messages(messages,generic_prompt):
    """Typed workflow prompt, not generic QA-report instructions from other modes.

    Preserve all user requests, retrieved memory, tool calls/results and feedback.
    Only replace the exact known generic Core prompt in the model view; Core
    permissions, execution messages, evidence and expected are unchanged.
    """
    view=deepcopy(messages)
    if view and view[0].get('role')=='system' and view[0].get('content')==generic_prompt:
        view[0]['content']=DOMAIN_PROMPT
    return view

def phase_decision_schema(catalog):
    """Closed transport for a MODEL-selected action; not automatic dispatch."""
    if not catalog:raise ValueError('no_admitted_action')
    return {'oneOf':[{'type':'object','additionalProperties':False,'required':['name','arguments'],
        'properties':{'name':{'type':'string','enum':[t['function']['name']]},
            'arguments':deepcopy(t['function']['parameters'])}} for t in catalog]}

def decode_phase_decision(content,catalog):
    decision=json.loads(content)
    if (not isinstance(decision,dict) or set(decision)!={'name','arguments'}
        or not isinstance(decision['arguments'],dict)
        or not call_admitted(catalog,decision['name'],decision['arguments'])):
        raise ValueError('model_phase_decision_not_admitted')
    return {'function':{'name':decision['name'],'arguments':decision['arguments']}}

def final_summary_schema(canonical):
    if canonical.get('report_type')!='locked_plugin_subset' or canonical.get('verdict')!='BLOCKED' or not canonical.get('task_id'):
        raise ValueError('canonical_plugin_report_required')
    return {'type':'object','additionalProperties':False,'required':['task_id','verdict','summary'],
        'properties':{'task_id':{'type':'string','enum':[canonical['task_id']]},
            'verdict':{'type':'string','enum':[canonical['verdict']]},
            # Length stays enforced by decode_final_summary. Large maxLength
            # grammar generation is not compatible with the installed backend.
            'summary':{'type':'string'}}}

def decode_final_summary(content,canonical):
    final_summary_schema(canonical)
    value=json.loads(content)
    if (not isinstance(value,dict) or set(value)!={'task_id','verdict','summary'}
        or value['task_id']!=canonical['task_id'] or value['verdict']!=canonical['verdict']
        or not isinstance(value['summary'],str) or not 1<=len(value['summary'].strip())<=2000):
        raise ValueError('model_final_summary_invalid')
    return value

def compile_bound_action(name,args,req):
    if name in {REFRESH,RUN_AUDIT}:
        if args!={}:raise ValueError('bound_action_has_no_overrides')
        audit,_=scopes(req)
        return CREATE,({**audit,'task_name':'pluginAudit'} if name==REFRESH else audit)
    return name,args

def incomplete_terminal_feedback(canonical,catalog,text=''):
    """Do not accept prose as completion of an unfinished task workflow.

    This is disclosed framework feedback, not an executed or synthetic action.
    BLOCKED is a business verdict, not permission to omit the audit/report.
    """
    if canonical:
        if canonical.get('task_id') and canonical['task_id'] in text and 'BLOCKED' in text.upper():return None
        return {'error':'canonical_report_summary_incomplete','automatic_action_taken':False,
            'required_summary':{'task_id':canonical.get('task_id'),'verdict':canonical.get('verdict')},
            'admitted_tools':[]}
    return {'error':'plugin_workflow_incomplete','automatic_action_taken':False,
        'business_BLOCKED_does_not_complete_workflow':True,
        'admitted_tools':[t['function']['name'] for t in catalog]}

def terminal_phase_key(catalog):
    """Budget refusal per immutable admitted phase, not per whole lifecycle.

    In particular, delivery/full, refresh/full and main/full have distinct own
    task bindings. The key is only bookkeeping, not new evidence or authority.
    """
    phase=sorted([{'name':t['function']['name'],'parameters':t['function']['parameters']}
        for t in catalog],key=lambda x:x['name'])
    return hashlib.sha256(json.dumps(phase,sort_keys=True).encode()).hexdigest()

def consume_terminal_refusal(counts,catalog):
    key=terminal_phase_key(catalog)
    counts[key]=counts.get(key,0)+1
    if counts[key]>2:raise RuntimeError('premature_model_termination')
    return key

def catalog_for(tools,trace,req):
    audit,delivery=scopes(req);name=audit['task_name'];pins={};names=set()
    created=[t['result'] for t in trace if t['tool'] in {CREATE,DELIVER} and t['result'].get('mutation_executed') is True]
    pending=next((a for a in reversed(created) if not any(t['tool']==READ and t['result'].get('task_id')==a['task_id']
        and (t['result'].get('operation_verification') or {}).get('verified') is True for t in trace)),None)
    if pending:
        names.add(READ);pins[READ]={'ci_name':audit['ci_name'],'agent_id':audit['agent_id'],'task_id':pending['task_id']}
    elif any(a.get('task_name')==name for a in created):
        names.add(REPORT);pins[REPORT]={'task_id':next(a['task_id'] for a in created if a.get('task_name')==name)}
    else:
        pins[READY]={'ci_name':audit['ci_name'],'agent_id':audit['agent_id'],
            'plugin_name':name,'plugin_version':audit['plugin_version']}
        ready=None
        for t in trace:
            if t['tool']==READY:ready=t['result']
            elif t['tool']==READ and t['result'].get('task_name')=='pluginAudit':ready=t['result'].get('plugin_readiness')
        delivered=bool(req.get('prior_verified_delivery')) or any(a.get('task_name')=='managePlugin' for a in created)
        refreshed=any(a.get('task_name')=='pluginAudit' for a in created)
        if ready is None:
            opened=any(t['tool']=='browser_open_page' and not t['result'].get('error') for t in trace)
            targeted=any(t['tool']=='browser_open_agent_tasks_semantic' and not t['result'].get('error') for t in trace)
            if not opened:
                names.add('browser_open_page');pins['browser_open_page']={'url':'https://uc.lab.local/cmdb'}
            elif not targeted:
                names.add('browser_open_agent_tasks_semantic');pins['browser_open_agent_tasks_semantic']={'ci_name':audit['ci_name']}
            else:names.add(READY)
        elif delivered and not refreshed and ready and ready.get('core_version')=='1.3.27' and ready.get('agent_status')=='online':
            names.add(CREATE);pins[CREATE]={**audit,'task_name':'pluginAudit'}
        elif ready and ready.get('ready') is True:
            names.add(CREATE);pins[CREATE]=audit
        elif ready and ready.get('core_version')=='1.3.27' and ready.get('agent_status')=='online':
            matched=(ready.get('plugin_audit') or {}).get('matched_plugins') or []
            mismatch=len(matched)==0 or (len(matched)==1 and matched[0].get('version')!=audit['plugin_version'])
            if mismatch and not delivered:
                names.add(DELIVER);pins[DELIVER]=delivery
            elif not refreshed and (ready.get('plugin_audit') or {}).get('reason')=='plugin_audit_stale':
                names.add(CREATE);pins[CREATE]={**audit,'task_name':'pluginAudit'}
            else:names.add(READY)
        else:names.add(READY)
    catalog=deepcopy([t for t in tools if t['function']['name'] in names])
    for t in catalog:
        fn=t['function'];args=pins.get(fn['name'])
        if args:
            fn['parameters']={'type':'object','additionalProperties':False,'required':list(args),
                'properties':{k:{'type':'string','enum':[v]} for k,v in args.items()}}
        if fn['name']==CREATE:
            refreshing=pins[CREATE]['task_name']=='pluginAudit'
            fn['name']=REFRESH if refreshing else RUN_AUDIT
            fn['description']=(('Обновить inventory плагинов через одну новую pluginAudit задачу' if refreshing
                else 'Запустить одну новую '+name+' задачу')+' на уже закреплённой КЕ '+audit['ci_name']+
                ', плагин '+name+' версии '+audit['plugin_version']+'. WRITE: scope берётся только из locked case, '
                'переопределения отсутствуют. Обычная policy/journal обязательны; затем прочитай возвращённый task_id.')
            fn['parameters']={'type':'object','additionalProperties':False,'properties':{},'required':[]}
    return catalog

def evaluate_execution(job,op,eid,contract):
    try:
        c=next(c for c in job['test_cases'] if c['case_id']==op['case_id']);r=c['requirement']
        stage=next(s for s in stages_for(r) if s['stage_id']==op['stage_id'])
        if (job['stand']!='lab' or r.get('type')!='pinned_plugin_audit' or r.get('locked') is not True
            or r.get('operation_stages')!=stages_for(r) or stage['verification']!=contract
            or any(op.get(k)!=stage[k] for k in ('workflow_id','stage_id','resource_key','tool'))
            or op.get('receipt',{}).get('acknowledged') is not True):raise ValueError('contract')
        def stamp(v):
            at=datetime.fromisoformat(str(v).replace('Z','+00:00'))
            if at.tzinfo is None:raise ValueError('timezone')
            return at
        def native(e,tool):
            if e.get('source')!='uqa_tool' or e.get('execution_status') not in {'observed','executed'} or stamp(e['created_at'])<stamp(op['created_at']):raise ValueError('native')
            b=json.loads(e['value'])
            if b['tool']!=tool:raise ValueError('tool')
            return b
        e=next(e for e in c['evidence'] if e['evidence_id']==eid);b=native(e,READ);read=b['result']
        receipts=[]
        for ce in c['evidence']:
            if ce.get('source')!='uqa_tool':continue
            try:cb=json.loads(ce['value'])
            except (ValueError,TypeError):continue
            if cb.get('tool')==stage['tool'] and (cb.get('result') or {}).get('operation_id')==op['operation_id']:
                receipts.append((ce,native(ce,stage['tool'])))
        if len(receipts)!=1:raise ValueError('unique receipt')
        ce,cb=receipts[0];sent=cb['result'];task=contract['task_name'];now=datetime.now(timezone.utc)
        if (cb['arguments']!=stage['arguments'] or sent.get('create_status')!=(202 if task=='managePlugin' else 201)
            or sent.get('mutation_executed') is not True or sent.get('error') or read.get('error')
            or sent.get('task_id')!=read.get('task_id') or not sent.get('task_id')
            or b['arguments']!={'ci_name':r['pinned_audit_task']['ci_name'],'agent_id':contract['agent_id'],'task_id':sent['task_id']}
            or any(sent.get(k)!=read.get(k) for k in ('session_id','agent_id','task_name','request_origin'))
            or not sent.get('session_id') or read.get('request_origin')!='https://uc.lab.local'
            or read.get('agent_id')!=contract['agent_id'] or read.get('task_name')!=task
            or read.get('ci_id')!=contract['ci_id'] or read.get('machine_uid')!=contract['ci_id']
            or read.get('native_result_verified') is not True or read.get('identity_verified') is not True
            or read.get('fresh_result') is not True or read.get('task_status')!='success' or read.get('result_code')!='success'
            or stamp(e['created_at'])<stamp(ce['created_at']) or not -5<=(now-stamp(e['created_at'])).total_seconds()<=300
            or not -5<=(stamp(e['created_at'])-stamp(read['read_at'])).total_seconds()<=60
            or not audit_result_is_fresh(sent.get('sent_at'),sent.get('received_at'),sent.get('server_created_at'),
                read.get('server_created_at'),read.get('processed_at'),now=now)):raise ValueError('identity or freshness')
        if task=='managePlugin' and (read.get('delivery_verified') is not True
            or read.get('plugin_name')!=contract['plugin_name'] or read.get('plugin_version')!=contract['plugin_version']):raise ValueError('delivery')
        if task=='pluginAudit':
            ready=read.get('plugin_readiness') or {};audit=ready.get('plugin_audit') or {};plugins=audit.get('matched_plugins') or []
            if (ready.get('ready') is not True or ready.get('agent_id')!=contract['agent_id'] or ready.get('ci_id')!=contract['ci_id']
                or ready.get('core_version')!='1.3.27' or ready.get('agent_status')!='online'
                or audit.get('audit_agent_id')!=contract['agent_id'] or audit.get('audit_fresh') is not True
                or len(plugins)!=1 or plugins[0].get('name')!=contract['plugin_name']
                or plugins[0].get('version')!=contract['plugin_version'] or plugins[0].get('load_status') is not True
                or plugins[0].get('load_error_present') is not False
                or (stamp(audit['last_audit_at'])-stamp(sent['server_created_at'])).total_seconds() < -120):raise ValueError('loaded inventory')
        return {'verified':True,'evidence_id':eid,'receipt_evidence_id':ce['evidence_id'],'identifier_value':sent['task_id'],
            'postcondition_verified':True,'resend_authorized':False,'business_pass':False,
            'verification_scope':'owned_plugin_task_execution_not_business_PASS'}
    except (KeyError,ValueError,TypeError,StopIteration,AttributeError,OverflowError):
        return {'verified':False,'reason':'plugin_execution_proof_insufficient','resend_authorized':False}

def run(api,messages,job_id,case_id,action_policy,force_read_only=False):
    if action_policy!='confirm_mutations' or force_read_only:return {'started':False,'reason':'managed_policy_required'}
    try:
        job=api.get_job(job_id);case,req=validate_context(job,case_id)
        if list_operations(job_id):raise ValueError('operation_exists_no_resend')
    except (ValueError,KeyError,TypeError,StopIteration):return {'started':False,'reason':'plugin_context_invalid'}
    from tools.browser import _session
    from tools.registry import TOOLS
    store.add_evidence(job_id,case_id,'pinned_plugin_runtime_started',json.dumps({'prepared_scope_oracle':True,
        'framework_phase_admission':True,'ordinary_freeform_entry':False}),source='uqa_plugin_runtime',
        execution_status='observed',usable_for_pass=False,usable_for_verdict=False,eligibility_reason='reservation_only')
    trace=[];report='';canonical=None;error=None;memory=[];repeats={};terminal_refusals=0
    terminal_phase_refusals={};terminal_refusal_events=[];structured_decisions=[]
    try:
        _session.reset_case_context()
        messages.append({'role':'system','content':'Bounded plugin inventory subset. Select only currently admitted tools/argument enums. '
            'Use only returned task IDs. Delivery success is not plugin load. Read delivery, pluginAudit and final audit. '
            'Use agent_build_pinned_audit_report for final expected/actual; BLOCKED completeness is not PASS or a confirmed bug. '
            'Do not generate UQA_CHECKS_JSON, invent IDs, change expected, use Zephyr, or repeat uncertain sends.'})
        memory=api.append_reviewed_product_memory(messages,job['request'],job_id,case_id,action_policy)
        for turn in range(24):
            catalog=[] if canonical else catalog_for(TOOLS,trace,req)
            model_view=scoped_model_messages(messages,api.SYSTEM_PROMPT)
            if catalog:
                model_view.append({'role':'system','content':'Select the next admitted action using only the supplied JSON schema: '
                    'name and arguments. This selects an action, it does not execute it. Do not return a final answer before '
                    'the canonical report. Core still validates scope, policy and execution evidence.'})
                response=api.ask_ollama(model_view,tools=[],response_schema=phase_decision_schema(catalog))
                content=str((response.get('message') or {}).get('content') or '')
                call=decode_phase_decision(content,catalog);calls=[call];text=''
                structured_decisions.append({'after_step':len(trace),'name':call['function']['name'],
                    'argument_keys':sorted(call['function']['arguments']),'automatic_action_taken':False})
            else:
                model_view.append({'role':'system','content':'Return only the final summary JSON from the supplied schema. '
                    'Copy canonical task_id/verdict exactly; summarize actual result and the incomplete independent checks. '
                    'The canonical expected/actual report remains authoritative; no new action is permitted.'})
                response=api.ask_ollama(model_view,tools=[],response_schema=final_summary_schema(canonical))
                m=response.get('message') or {};calls=m.get('tool_calls') or [];text=str(m.get('content') or '')
                decode_final_summary(text,canonical)
            messages.append({'role':'assistant','content':text,**({'tool_calls':calls} if calls else {})})
            if not calls:
                feedback=incomplete_terminal_feedback(canonical,catalog,text)
                if feedback is None:report=text;break
                terminal_refusals+=1
                phase_key=terminal_phase_key(catalog)
                terminal_refusal_events.append({'after_step':len(trace),'phase_key':phase_key,
                    'admitted_tools':feedback['admitted_tools'],'automatic_action_taken':False})
                consume_terminal_refusal(terminal_phase_refusals,catalog)
                messages.append({'role':'system','content':json.dumps(feedback,ensure_ascii=False)})
                continue
            for call in calls:
                fn=call.get('function') or {};name=fn.get('name');args=fn.get('arguments') or {}
                selected_name=name
                if isinstance(args,str):args=json.loads(args)
                catalog=[] if canonical else catalog_for(TOOLS,trace,req)
                if not call_admitted(catalog,name,args):
                    result={'error':'plugin_phase_not_admitted','executed':False,'automatic_action_taken':False,
                        'current_native_fact_bound_operations':[{'tool':t['function']['name'],'arguments':{
                            k:v['enum'][0] for k,v in t['function']['parameters'].get('properties',{}).items() if len(v.get('enum',[]))==1}}
                            for t in catalog if t['function']['name'] in {CREATE,DELIVER,READ,READY,REPORT,REFRESH,RUN_AUDIT}]}
                else:
                    name,args=compile_bound_action(name,args,req)
                    result=api.execute_tool_with_policy(name,args,messages,action_policy=action_policy,job_id=job_id,case_id=case_id)
                    obs=api.record_tool_observations(job_id,case_id,name,args,result)
                    e=api.record_tool_evidence(job_id,case_id,name,args,result,observation_ids=[o['observation_id'] for o in obs])
                    if name==READ and result.get('native_result_verified') is True:
                        receipt=next((t['result'] for t in reversed(trace) if t['tool'] in {CREATE,DELIVER} and t['result'].get('task_id')==result.get('task_id')), {})
                        if receipt.get('operation_id'):
                            result['operation_verification']=reconcile_operation(job_id,receipt['operation_id'],e['evidence_id'])
                    if name==REPORT and result.get('report_type')=='locked_plugin_subset':canonical=result
                trace.append({'tool':name,'arguments':args,'result':result,'model_selected_tool':selected_name,
                    'framework_bound_action_compiled':selected_name in {REFRESH,RUN_AUDIT}})
                print('MODEL_PLUGIN_STEP='+json.dumps({'step':len(trace),'tool':name,'error':result.get('error')}),flush=True)
                messages.append({'role':'tool','tool_name':selected_name,'content':json.dumps(api.tool_result_for_model(name,result),ensure_ascii=False)})
                if result.get('error'):
                    key=(name,json.dumps(args,sort_keys=True));repeats[key]=repeats.get(key,0)+1
                    if repeats[key]>=2:raise RuntimeError('repeated_model_no_progress')
    except (Exception,KeyboardInterrupt) as exc:error=type(exc).__name__
    finally:
        ops=list_operations(job_id);name=req['pinned_audit_task']['task_name']
        created=[t['result'] for t in trace if t['tool']==CREATE and t['result'].get('mutation_executed') is True and t['result'].get('task_name')==name]
        recipe=any(r.get('source')=='UQA-experience/UQA_PARAMETERLESS_PLUGIN_REGRESSION.md' for m in memory for r in m.get('results',[]))
        completed=bool(canonical and len(created)==1 and report and created[0]['task_id'] in report and 'BLOCKED' in report.upper()
            and recipe and not error and ops and all(o['status']=='verified' for o in ops))
        body={'trace':trace,'canonical_report':canonical,'model_report':report,'model_selected_case_cycle_completed':completed,
            'journal_execution_verified':bool(ops and all(o['status']=='verified' for o in ops)),
            'memory_recipe_retrieved':recipe,'framework_phase_admission':True,'prepared_scope_oracle_catalog':True,
            'ordinary_freeform_entry':False,'operator_runtime_hints':0,'operator_product_actions':0,
            'synthetic_product_action_calls':0,'error_type':error,'zephyr_written':False}
        body['framework_bound_actions']=True
        body['framework_typed_domain_prompt']=True
        body['framework_structured_decision_transport']=True
        body['framework_strict_stage_admission']=True
        body['framework_structured_final_summary']=True
        body['model_structured_decisions']=structured_decisions
        body['framework_terminal_refusals']=terminal_refusals
        body['framework_terminal_phase_refusals']=terminal_phase_refusals
        body['framework_terminal_refusal_events']=terminal_refusal_events
        e=store.add_evidence(job_id,case_id,'bounded_local_model_plugin_trace',json.dumps(body,ensure_ascii=False),
            source='uqa_plugin_model_runtime',execution_status='observed',usable_for_pass=False,usable_for_verdict=False,
            eligibility_reason='workflow_and_structure_subset_not_whole_case_PASS')
        store.update_test_case(job_id,case_id,status='blocked',result=canonical['report_markdown'] if canonical else 'Incomplete model plugin cycle; no blind resend.')
        store.set_job_status(job_id,'blocked');_session.close()
    return {'started':True,'completed':completed,'business_verdict':'BLOCKED','trace_evidence_id':e['evidence_id'],'error_type':error}
