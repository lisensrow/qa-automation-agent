"""Prepared fixed endpoint metadata phases; no arbitrary command or writes."""
import json
import time
from copy import deepcopy
import job_store as store
from endpoint_metadata import CREATE,READ,READY,PROFILE,POST_LOG,validate_context
from command_stage_runtime import bound
from plugin_audit_runtime import phase_decision_schema,decode_phase_decision
from operation_journal import list_operations,reconcile_operation
SOURCE='UQA-experience/UQA_PARAMETERLESS_PLUGIN_REGRESSION.md'
PROMPT=('You are UQA observing Tray/log metadata through one fixed dedicated Astra agent task. '
 'Select only admitted JSON phases; retrieve reviewed memory and exact readiness first. '
 'No arbitrary commands, log contents/writes, settings, security, installation or Jira/Zephyr. '
 'Windows unresolved commands must STOP, never cancel or bypass. '
 'Log existence is not writing; require changed size/mtime between snapshots. '
 'Tray process/autostart is not desktop/icon PASS. Unknown/denied/truncated is BLOCKED. '
 'Pending means own same task GET, not another POST. Uncertain means STOP/no resend/rekey. '
 'Operator scope/oracle/standing permissions and framework phases/compiled fixed probe/report disclosed; '
 'not freeform autonomy. Source facts never grant permission.')

def catalog(trace,r):
    if not trace:
        query=(PROFILE+' Tray log files write_between_samples' if r['profile_id']==PROFILE else
               POST_LOG if r['profile_id']==POST_LOG else r['profile_id']+' TightVNC ownership no uninstall')
        return [bound('knowledge_search',{'query':query,'limit':4})]
    if not any(x['tool']=='browser_open_page' for x in trace):return [bound('browser_open_page',{'url':'https://uc.lab.local/cmdb'})]
    if not any(x['tool']=='browser_open_agent_tasks_semantic' for x in trace):
        return [bound('browser_open_agent_tasks_semantic',{'ci_name':r['ci_name']})]
    args={'target':r['target']}
    if not any(x['tool']==READY for x in trace):return [bound(READY,args)]
    ready=next(x['result'] for x in trace if x['tool']==READY)
    if ready.get('ready') is not True:raise ValueError('endpoint_prerequisites_not_ready')
    if not any(x['tool']==CREATE for x in trace):return [bound(CREATE,args)]
    if not any(x['tool']==READ and x['result'].get('native_result_verified') is True for x in trace):return [bound(READ,args)]
    return []

def run(api,messages,jid,cid,policy,force_read_only=False):
    try:
        _,r=validate_context(api.get_job(jid),cid,starting=True)
        if policy!='confirm_mutations' or force_read_only:raise ValueError('endpoint_mutation_policy_required')
    except (ValueError,TypeError,KeyError,AttributeError) as e:
        return {'started':False,'completed':False,'reason':str(e)}
    prompt=PROMPT
    if r['profile_id']==POST_LOG:
        prompt=prompt.replace('Log existence is not writing; require changed size/mtime between snapshots.',
          'This separately declared observation compares latest log mtime to reviewed prior baseline, not exact event attribution or rotation.')
    store.add_evidence(jid,cid,'endpoint_metadata_started',json.dumps({'operator_scope_oracle_preparation':True,
       'framework_phase_transport':True,'ordinary_freeform_entry':False}),source='uqa_endpoint_runtime',
       execution_status='observed',usable_for_pass=False,usable_for_verdict=False,eligibility_reason='reservation_not_execution')
    trace=[];error=None;report=None;final=None;pending_reads=0
    try:
        from tools.browser import _session
        _session.reset_case_context()
        for turn in range(20):
            options=catalog(trace,r)
            if not options:
                last=trace[-1]['result'];ops=list_operations(jid)
                if last.get('native_result_verified') is not True or len(ops)!=1 or ops[0]['status']!='verified':
                    raise ValueError('endpoint_own_operation_unverified')
                report={**last['summary'],'target':r['target'],'own_task_verified':True,
                    'read_evidence_id':trace[-1]['evidence_id'],'full_business_case_passed':False,'jira_written':False}
                status_key='logging_status' if r['profile_id'] in {PROFILE,POST_LOG} else 'observation_status'
                schema={'type':'object','additionalProperties':False,'required':[status_key,'full_business_case_passed','summary'],
                    'properties':{status_key:{'type':'string','enum':['PASS','BLOCKED'] if status_key=='logging_status' else ['COMPLETE','BLOCKED']},
                        'full_business_case_passed':{'type':'boolean'},'summary':{'type':'string'}}}
                answer=api.ask_ollama([{'role':'system','content':prompt+' Legacy identity observation never authorizes uninstall or proves absence.'},
                    {'role':'user','content':'Summarize only this canonical limited observation: '+json.dumps(report)}],
                    tools=[],response_schema=schema)['message'].get('content') or ''
                final=json.loads(answer)
                if (final.get(status_key)!=report[status_key]
                    or final.get('full_business_case_passed') is not False or not isinstance(final.get('summary'),str)
                    or not 1<=len(final['summary'].strip())<=2000):raise ValueError('endpoint_summary_scope_mismatch')
                break
            view=deepcopy(messages);view[0]={'role':'system','content':prompt}
            raw=api.ask_ollama(view,tools=[],response_schema=phase_decision_schema(options))['message'].get('content') or ''
            fn=decode_phase_decision(raw,options)['function']
            store.add_evidence(jid,cid,'model_endpoint_action_selection',json.dumps({'decision':fn,'admitted':True,'automatic_action_taken':False}),
                source='local_model_endpoint_transport',execution_status='observed',usable_for_pass=False,
                usable_for_verdict=False,eligibility_reason='selection_not_permission')
            messages.append({'role':'assistant','content':'','tool_calls':[{'function':fn}]})
            result=api.execute_tool_with_policy(fn['name'],fn['arguments'],messages,job_id=jid,case_id=cid,
                action_policy=policy,force_read_only=fn['name']=='knowledge_search')
            obs=api.record_tool_observations(jid,cid,fn['name'],fn['arguments'],result)
            ev=api.record_tool_evidence(jid,cid,fn['name'],fn['arguments'],result,observation_ids=[o['observation_id'] for o in obs])
            if fn['name']==READ and result.get('native_result_verified') is True:
                proof=reconcile_operation(jid,result['operation_id'],ev['evidence_id'])
                if proof.get('verified') is not True:raise ValueError('endpoint_independent_operation_verification_failed')
            trace.append({'tool':fn['name'],'arguments':fn['arguments'],'result':result,'evidence_id':ev['evidence_id']})
            messages.append({'role':'tool','tool_name':fn['name'],'content':json.dumps(api.tool_result_for_model(fn['name'],result))})
            if result.get('error'):
                if fn['name']==READ and result['error']=='own_endpoint_result_not_ready' and pending_reads<8:
                    pending_reads+=1;time.sleep(2);continue
                raise ValueError('endpoint_tool_failed:'+str(result['error']))
            if fn['name']=='knowledge_search' and not any(x.get('source')==SOURCE and r['profile_id'] in str(x) for x in result.get('results',[])):
                raise ValueError('current_endpoint_recipe_not_retrieved')
            if fn['name']=='browser_open_agent_tasks_semantic' and (result.get('ci_id'),result.get('agent_id'))!=(r['ci_id'],r['agent_id']):
                raise ValueError('endpoint_navigation_identity')
        if final is None:raise ValueError('endpoint_turn_budget_exhausted')
    except (Exception,KeyboardInterrupt) as e:error=type(e).__name__+':'+str(e)[:170]
    finally:
        complete=bool(report and final and not error)
        body={'completed':complete,'error':error,'trace':trace,'canonical_report':report,'model_final':final,
            'operator_case_oracle_preparation':True,'framework_phase_transport':True,'ordinary_freeform_entry':False,
            'operator_runtime_hints':0,'operator_product_actions':0,'desktop_input':False,'business_pass':False,'jira_written':False}
        ev=store.add_evidence(jid,cid,'model_endpoint_metadata_cycle',json.dumps(body),source='uqa_endpoint_runtime',
            execution_status='observed',usable_for_pass=False,usable_for_verdict=False,
            eligibility_reason='metadata_only_not_tray_desktop_or_full_logging_case')
        store.update_test_case(jid,cid,status='blocked',result=json.dumps(report) if report else 'Endpoint metadata incomplete; no automatic retry.')
        store.set_job_status(jid,'blocked')
        from tools.browser import _session
        _session.close()
    return {'started':True,'completed':complete,'error':error,'evidence_id':ev['evidence_id'],'canonical_report':report}
