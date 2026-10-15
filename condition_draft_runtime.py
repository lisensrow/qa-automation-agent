"""Explicit caller-locked condition phase; normal policy/verifier, never Save."""
import json
from urllib.parse import urlsplit
from condition_plan import compile_condition_plan, fingerprint, response_schema, plan_instruction
import condition_draft_profiles as profiles
from frontend_check_contracts import evaluate_contract, normalized_origin


def _case(job,case_id):
    return next((c for c in job.get('test_cases',[]) if c.get('case_id')==case_id),{})


def validate_context(job,case_id,preparing=False):
    case=_case(job,case_id); req=case.get('requirement') or {}; planned=case.get('planned_checks') or []
    if (job.get('job_type')!='regression' or job.get('status')!=('created' if preparing else 'running')
            or case.get('status')!=('pending' if preparing else 'running')
            or job.get('stand')!=req.get('stand') or job.get('resources') or len(planned)!=1
            or req.get('type')!='bounded_condition_draft' or not req.get('locked') is True):
        raise ValueError('condition_draft_context_invalid')
    if preparing and case.get('condition_draft_state'):
        raise ValueError('condition_draft_already_attempted')
    expected=profiles.requirement_for_plan(req.get('expected_plan'),planned[0]['check_id'],req.get('condition_profile_id'))
    if 'condition_request_binding' in req:
        from condition_request_adapter import request_requirement
        expected=request_requirement(job.get('request'),job.get('stand'),planned[0]['check_id'])
        if expected is None or len(job.get('test_cases',[]))!=1:
            raise ValueError('condition_draft_request_binding_invalid')
    if profiles.immutable_requirement(req)!=expected:
        raise ValueError('condition_draft_requirement_changed')
    if not profiles.source_current():raise ValueError('condition_draft_source_changed')
    return case,req,fingerprint(expected)


def run(api,messages,job_id,case_id,action_policy,force_read_only=False):
    if force_read_only or action_policy!='confirm_mutations':
        return {'status':'blocked','reason':'condition_draft_policy_required'}
    from operation_journal import list_operations
    started=False
    try:
        job=api.get_job(job_id); case,req,pin=validate_context(job,case_id)
        if list_operations(job_id) or case.get('condition_draft_state'):
            raise ValueError('condition_draft_already_attempted')
        entry=(api.get_stand(job['stand']) or {}).get('web_url')
        origin=normalized_origin(entry)
        def store(phase,**extra):
            fresh=api.get_job(job_id); c=_case(fresh,case_id)
            c['condition_draft_state']={'phase':phase,'requirement_sha256':pin,'ui_state_only':True,
                'saved_filter_verified':False,'membership_verified':False,**extra}
            from job_store import save_job
            save_job(fresh)
        def guard():
            fresh=api.get_job(job_id); _,r,current=validate_context(fresh,case_id)
            if current!=pin or list_operations(job_id):raise ValueError('condition_draft_context_changed')
            return r
        def call(tool,args,expected_path=None):
            guard()
            result=api.execute_tool_with_policy(tool,args,messages,action_policy=action_policy,
                job_id=job_id,case_id=case_id,require_compatibility_probe=True)
            result={**result,'bounded_condition_runtime':{'model_selected_action':False,'ui_arguments_from':'caller_profile_compiler'}}
            obs=api.record_tool_observations(job_id,case_id,tool,args,result)
            api.record_tool_evidence(job_id,case_id,tool,args,result,observation_ids=[o['observation_id'] for o in obs])
            messages.extend([{'role':'assistant','content':'','tool_calls':[{'function':{'name':tool,'arguments':args}}]},
                {'role':'tool','tool_name':tool,'content':json.dumps(api.tool_result_for_model(tool,result),ensure_ascii=False)}])
            if result.get('error'):raise ValueError('condition_draft_native_action_unavailable')
            if tool.startswith('browser_'):
                if normalized_origin(result.get('current_url'))!=origin:raise ValueError('condition_draft_origin_changed')
                login_challenge=tool=='browser_open_page' and any(
                    isinstance(e,dict) and e.get('type')=='password' and e.get('enabled') is not False
                    for e in result.get('interactive_elements',[]))
                if expected_path and not login_challenge and urlsplit(result['current_url']).path!=expected_path:
                    raise ValueError('condition_draft_editor_changed')
            return result
        store('started');started=True
        for tool,args,path in profiles.preparation(entry):
            state=call(tool,args,path)
            if tool=='browser_open_page' and any(isinstance(e,dict) and e.get('type')=='password'
                    and e.get('enabled') is not False for e in state.get('interactive_elements',[])):
                candidate=state.get('required_action_candidate') or {}
                auth_args=candidate.get('arguments') or {}
                if (candidate.get('tool')!='browser_authenticate_saved_stand' or set(auth_args)!={'stand'}
                        or not isinstance(auth_args['stand'],str) or not 0<len(auth_args['stand'])<=160):
                    raise ValueError('condition_draft_authentication_required')
                auth_stand=api.get_stand(auth_args['stand']) or {}
                if normalized_origin(auth_stand.get('web_url'))!=origin:
                    raise ValueError('condition_draft_auth_origin_changed')
                state=call('browser_authenticate_saved_stand',auth_args,path)
                if any(isinstance(e,dict) and e.get('type')=='password'
                        for e in state.get('interactive_elements',[])):
                    raise ValueError('condition_draft_authentication_required')
        if not state.get('session_id'):raise ValueError('condition_draft_session_missing')
        fresh=api.get_job(job_id); c=_case(fresh,case_id)
        c['requirement']['bindings'].update(grid_session=state['session_id'],grid_url=state['current_url'])
        from job_store import save_job,add_evidence
        save_job(fresh); req=guard()
        store('planning')
        from product_knowledge_context import reviewed_search_queries
        guidance=[]
        for query in reviewed_search_queries(job.get('request','')):
            guidance.append(call('knowledge_search',{'query':query,'limit':3}))
        p=profiles.profile(req['condition_profile_id']); schema=response_schema(p)
        schema['properties']['conditions'].update(minItems=len(req['expected_plan']['conditions']),
                                                 maxItems=len(req['expected_plan']['conditions']))
        response=api.ask_ollama([{'role':'system','content':plan_instruction(p)},
            {'role':'user','content':job['request']+'\nReviewed guidance (not execution evidence):\n'+json.dumps(guidance,ensure_ascii=False)}],
            tools=[],response_schema=schema)
        reply=response.get('message') or {}
        if reply.get('tool_calls'):raise ValueError('condition_draft_unexpected_model_tools')
        plan=json.loads(reply.get('content') or '')
        add_evidence(job_id,case_id,'condition_logical_proposal',json.dumps({'logical_plan':plan,'execution_authorized':False}),
            source='local_model_tool_free',usable_for_pass=False,usable_for_verdict=False,execution_status='observed',eligibility_reason='unvalidated_plan_only')
        req=guard(); compiled=compile_condition_plan(plan,p,req['expected_plan'],req['condition_profile_sha256'])
        add_evidence(job_id,case_id,'condition_compiled_plan',json.dumps(compiled),source='condition_plan_v1',
            usable_for_pass=False,usable_for_verdict=False,execution_status='observed',eligibility_reason='compiled_not_execution_permission')
        store('applying')
        for step in compiled['ui_steps']:
            r=guard(); binding=r['bindings']
            args={**step['arguments'],'session_id':binding['grid_session'],'current_url':binding['grid_url']}
            result=call(step['tool'],args,profiles.EDITOR_PATH)
            if result.get('tree_row_status')!='applied':raise ValueError('condition_draft_row_not_verified')
        binding=guard()['bindings']; expected_cells=json.loads(binding['grid_expected'])
        call('browser_inspect_labeled_grid_values_semantic',{
            'cells':[{'row':c['row'],'column':c['column']} for c in expected_cells],
            'session_id':binding['grid_session'],'current_url':binding['grid_url']},profiles.EDITOR_PATH)
        store('observed')
        return {'status':'observed_ui_draft','ui_state_only':True}
    except (Exception,KeyboardInterrupt) as exc:
        reason=str(exc) if isinstance(exc,ValueError) and str(exc).startswith(('condition_','grid_')) and len(str(exc))<120 else 'condition_draft_unavailable'
        if started:
            try:store('blocked',reason=reason,error_type=type(exc).__name__)
            except Exception:pass
        return {'status':'blocked','reason':reason}


def completed_checks(api,job,case_id):
    case=_case(job or {},case_id); req=case.get('requirement') or {}
    if req.get('type')!='bounded_condition_draft':return None
    if (case.get('condition_draft_state') or {}).get('phase')!='observed':return None
    validate_context(job,case_id)
    if (case['condition_draft_state'].get('requirement_sha256')!=fingerprint(profiles.immutable_requirement(req))):
        raise ValueError('condition_draft_requirement_changed')
    saved=(api.get_stand(job['stand']) or {}).get('web_url'); checks=[]
    for planned in case['planned_checks']:
        check,error=evaluate_contract(case,req,dict(planned,status='blocked'),saved)
        checks.append(check)
    return checks
