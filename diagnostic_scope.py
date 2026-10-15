"""Bind bounded read-only diagnostics to the persistent QA case stand."""
DIAGNOSTIC_TOOLS = frozenset({'ssh_docker_ps','ssh_docker_logs','ssh_find_backend_request','api_inspect_contract_page'})


def scope_diagnostic_arguments(name, arguments, job, case_id):
    arguments = dict(arguments or {})
    if name not in DIAGNOSTIC_TOOLS:
        return arguments, None
    job = job if isinstance(job,dict) else {}
    case = next((c for c in job.get('test_cases',[]) if c.get('case_id')==case_id),None)
    stand = job.get('stand')
    if not case or not isinstance(stand,str) or not stand.strip():
        return arguments, 'diagnostic_case_scope_missing'
    requirement = case.get('requirement') or {}
    if requirement.get('stand') not in (None,stand):
        return arguments, 'diagnostic_case_scope_inconsistent'
    requested = arguments.get('stand')
    if requested is not None and (not isinstance(requested,str) or requested.strip()!=stand):
        return arguments, 'diagnostic_stand_mismatch'
    arguments['stand']=stand
    if name=='api_inspect_contract_page' and 'api_contract_source_id' in requirement:
        locked=requirement['api_contract_source_id']
        if not isinstance(locked,str) or not locked or len(locked)>159:
            return arguments,'diagnostic_source_binding_invalid'
        if 'source_id' in arguments and arguments['source_id']!=locked:
            return arguments,'diagnostic_source_mismatch'
        arguments['source_id']=locked
    return arguments, None
