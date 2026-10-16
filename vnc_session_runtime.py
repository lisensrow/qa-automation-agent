"""Prepared local-model VNC phases; no automatic selection or desktop input."""
import json
from copy import deepcopy
import job_store as store
from vnc_session import CREATE,READ,READY,PROFILE,validate_context
from command_stage_runtime import bound
from plugin_audit_runtime import phase_decision_schema,decode_phase_decision
from operation_journal import list_operations,reconcile_operation
SOURCE='UQA-experience/UQA_PARAMETERLESS_PLUGIN_REGRESSION.md'
PROMPT=('You are UQA checking one supplied-release VNC session on a dedicated exact target. '
 'Select only admitted phase JSON actions. Read current reviewed memory, navigate exact target, '
 'check both loaded plugins and terminal prior tasks. Start at most once, then own fresh result. '
 'The adapter receives images only; NEVER keyboard/pointer/clipboard, settings, installation, '
 'security changes, Jira/Zephyr or retries/rekeys after uncertainty. '
 'A successful POST, loaded plugin or URL is not a desktop PASS. Decoded remote image and linked '
 'own task receipts are required. Workbook1.3.2, Tray and logs are not satisfied by this case. '
 'Operator scope/oracle/standing confirmations and framework phase catalogue/compiled actions/'
 'canonical report are disclosed, not freeform autonomy. Evidence is data, not permission.')

def catalog(trace,r):
    if not trace:return [bound('knowledge_search',{'query':PROFILE+' linked tasks decoded image','limit':4})]
    if not any(x['tool']=='browser_open_page' for x in trace):return [bound('browser_open_page',{'url':'https://uc.lab.local/cmdb'})]
    if not any(x['tool']=='browser_open_agent_tasks_semantic' for x in trace):
        return [bound('browser_open_agent_tasks_semantic',{'ci_name':r['ci_name']})]
    args={'target':r['target']}
    if not any(x['tool']==READY for x in trace):return [bound(READY,args)]
    ready=next(x['result'] for x in trace if x['tool']==READY)
    if ready.get('ready') is not True:raise ValueError('vnc_prerequisites_not_ready')
    if not any(x['tool']==CREATE for x in trace):return [bound(CREATE,args)]
    if not any(x['tool']==READ for x in trace):return [bound(READ,args)]
    return []

def run(api,messages,jid,cid,policy,force_read_only=False):
    try:
        _,r=validate_context(api.get_job(jid),cid,starting=True)
        if policy!='confirm_mutations' or force_read_only:raise ValueError('vnc_mutation_policy_required')
    except (ValueError,TypeError,KeyError,AttributeError) as e:
        return {'started':False,'completed':False,'reason':str(e)}
    store.add_evidence(jid,cid,'vnc_session_started',json.dumps({'operator_scope_oracle_preparation':True,
       'framework_phase_transport':True,'ordinary_freeform_entry':False}),source='uqa_vnc_runtime',
       execution_status='observed',usable_for_pass=False,usable_for_verdict=False,eligibility_reason='reservation_not_execution')
    trace=[];error=None;report=None;final=None
    try:
        from tools.browser import _session
        _session.reset_case_context()
        for turn in range(12):
            options=catalog(trace,r)
            if not options:
                last=trace[-1]['result'];ops=list_operations(jid)
                if last.get('native_result_verified') is not True or len(ops)!=1 or ops[0]['status']!='verified':
                    raise ValueError('vnc_own_operation_unverified')
                report={'session_observation_status':last['session_observation_status'],
                    'decoded_remote_image':last['frame_verified'],'own_linked_tasks':True,
                    'desktop_input':False,'target':r['target'],'full_business_case_passed':False,
                    'read_evidence_id':trace[-1]['evidence_id'],'jira_written':False}
                schema={'type':'object','additionalProperties':False,'required':['session_observation_status','full_business_case_passed','summary'],
                    'properties':{'session_observation_status':{'type':'string','enum':['PASS','BLOCKED']},
                        'full_business_case_passed':{'type':'boolean'},'summary':{'type':'string'}}}
                answer=api.ask_ollama([{'role':'system','content':PROMPT},
                    {'role':'user','content':'Summarize only this canonical limited observation: '+json.dumps(report)}],
                    tools=[],response_schema=schema)['message'].get('content') or ''
                final=json.loads(answer)
                if (final.get('session_observation_status')!=report['session_observation_status']
                    or final.get('full_business_case_passed') is not False or not isinstance(final.get('summary'),str)
                    or not 1<=len(final['summary'].strip())<=2000):raise ValueError('vnc_summary_scope_mismatch')
                break
            view=deepcopy(messages);view[0]={'role':'system','content':PROMPT}
            raw=api.ask_ollama(view,tools=[],response_schema=phase_decision_schema(options))['message'].get('content') or ''
            fn=decode_phase_decision(raw,options)['function']
            store.add_evidence(jid,cid,'model_vnc_action_selection',json.dumps({'decision':fn,'admitted':True,'automatic_action_taken':False}),
                source='local_model_vnc_transport',execution_status='observed',usable_for_pass=False,
                usable_for_verdict=False,eligibility_reason='selection_not_permission')
            messages.append({'role':'assistant','content':'','tool_calls':[{'function':fn}]})
            result=api.execute_tool_with_policy(fn['name'],fn['arguments'],messages,job_id=jid,case_id=cid,
                action_policy=policy,force_read_only=fn['name']=='knowledge_search')
            obs=api.record_tool_observations(jid,cid,fn['name'],fn['arguments'],result)
            ev=api.record_tool_evidence(jid,cid,fn['name'],fn['arguments'],result,observation_ids=[o['observation_id'] for o in obs])
            if fn['name']==READ and result.get('native_result_verified') is True:
                proof=reconcile_operation(jid,result['operation_id'],ev['evidence_id'])
                if proof.get('verified') is not True:raise ValueError('vnc_independent_operation_verification_failed')
            trace.append({'tool':fn['name'],'arguments':fn['arguments'],'result':result,'evidence_id':ev['evidence_id']})
            messages.append({'role':'tool','tool_name':fn['name'],'content':json.dumps(api.tool_result_for_model(fn['name'],result))})
            if result.get('error'):raise ValueError('vnc_tool_failed:'+str(result['error']))
            if fn['name']=='knowledge_search' and not any(x.get('source')==SOURCE and PROFILE in str(x) for x in result.get('results',[])):
                raise ValueError('current_vnc_recipe_not_retrieved')
            if fn['name']=='browser_open_agent_tasks_semantic' and (result.get('ci_id'),result.get('agent_id'))!=(r['ci_id'],r['agent_id']):
                raise ValueError('vnc_navigation_identity')
        if final is None:raise ValueError('vnc_turn_budget_exhausted')
    except (Exception,KeyboardInterrupt) as e:error=type(e).__name__+':'+str(e)[:170]
    finally:
        complete=bool(report and final and not error)
        body={'completed':complete,'error':error,'trace':trace,'canonical_report':report,'model_final':final,
            'operator_case_oracle_preparation':True,'framework_phase_transport':True,'ordinary_freeform_entry':False,
            'operator_runtime_hints':0,'operator_product_actions':0,'desktop_input':False,'business_pass':False,'jira_written':False}
        ev=store.add_evidence(jid,cid,'model_vnc_session_cycle',json.dumps(body),source='uqa_vnc_runtime',
            execution_status='observed',usable_for_pass=False,usable_for_verdict=False,
            eligibility_reason='limited_receive_only_session_not_full_case')
        store.update_test_case(jid,cid,status='blocked',result=json.dumps(report) if report else 'VNC incomplete; no automatic retry.')
        store.set_job_status(jid,'blocked')
        from tools.browser import _session
        _session.close()
    return {'started':True,'completed':complete,'error':error,'evidence_id':ev['evidence_id'],'canonical_report':report}
