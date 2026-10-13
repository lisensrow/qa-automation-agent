"""Explicit opt-in memory hints for a prepared, policy-guarded Job."""
from datetime import datetime, timezone
from product_knowledge_retrieval import retrieve_product_knowledge


def prepare_memory_context(job, case_id, detector, loader, saver, retriever=None):
    case = next((c for c in job.get('test_cases', []) if c.get('case_id') == case_id), {})
    requirement = case.get('requirement') or {}
    query = requirement.get('memory_query')
    if query is None:
        return job, None
    profile = requirement.get('action_profile')
    allowed_profile = profile == 'read_only' or (
        profile == 'write_ui_state' and requirement.get('policy_required') is True
        and isinstance(requirement.get('cleanup_contract'), str) and bool(requirement['cleanup_contract'].strip()))
    if (not allowed_profile or not isinstance(query, str)
            or not 1 <= len(query.strip()) <= 1000):
        raise ValueError('prepared_memory_query_or_profile_invalid')
    stand = job.get('stand')
    if not stand or job.get('status') != 'created' or case.get('status') != 'pending':
        raise ValueError('prepared_memory_job_not_pending')
    # Always refresh: queued Jobs must not inherit the version from creation.
    try:
        detected = detector(stand)
        detected = detected if isinstance(detected, dict) else {}
        identity = {k: detected.get(k) for k in (
            'status', 'installation_architecture', 'server_version', 'deployment_partial')}
        if 'frontend_status' in detected:
            identity.update({k:detected.get(k) for k in ('frontend_status','frontend_version','frontend_version_source')})
    except Exception as error:
        identity = {'status': 'unknown', 'error_type': type(error).__name__}
    identity.update(stand=stand, checked_at=datetime.now(timezone.utc).isoformat())
    payload = (retriever or retrieve_product_knowledge)(query.strip(), identity)
    latest = loader(job['job_id'])
    current = next((c for c in (latest or {}).get('test_cases', []) if c.get('case_id') == case_id), {})
    if (not latest or latest.get('stand') != stand or latest.get('status') != 'created'
            or current.get('status') != 'pending' or current.get('requirement') != requirement):
        raise ValueError('prepared_memory_job_changed_during_detection')
    latest['stand_identity'] = identity
    current['memory_context'] = {
        'status': payload.get('status'), 'reason': payload.get('reason'),
        'fact_keys': [item['fact_key'] for item in payload.get('results', [])],
        'loaded_fact_count': len(payload.get('results', [])),
        'identity_checked_at': identity['checked_at'],
        'evidence_for_pass': False,
        'binding_reconfirmation': 'not_performed',
        'fact_reconfirmation': 'not_performed',
        'frontend_recheck_needed_count': payload.get('frontend_recheck_needed_count',0),
    }
    saver(latest)
    return latest, payload


def record_memory_reconfirmation(job_id, case_id, candidate, loader, saver):
    """Audit an ingested matching fact only with fresh case-local runtime proof."""
    job = loader(job_id)
    case = next((c for c in (job or {}).get('test_cases', []) if c.get('case_id') == case_id), {})
    context = case.get('memory_context') or {}
    key = candidate.get('fact_key')
    flags = candidate.get('verification') or {}
    if case.get('status') != 'passed' or key not in (context.get('fact_keys') or []):
        return False
    from knowledge_fact_contracts import RUNTIME_FLAGS
    kind = candidate.get('fact_type','ui_api_binding')
    if kind not in RUNTIME_FLAGS or not all(flags.get(k) is True for k in RUNTIME_FLAGS[kind]):
        return False
    refs = candidate.get('source_observation_ids') or []
    linked = [o for o in case.get('observations', []) if o.get('observation_id') in refs]
    types = {'ui_tab_navigation'} if kind == 'ui_navigation' else {'ui_state','api_exchange','backend_request'}
    if not types <= {o.get('type') for o in linked}:
        return False
    keys = context.setdefault('reconfirmed_fact_keys', [])
    if key not in keys:
        keys.append(key)
    context.update(fact_reconfirmation='runtime_confirmed', evidence_for_pass=False,
                   confirmation_job_id=job_id, confirmation_case_id=case_id)
    context['navigation_reconfirmation' if kind == 'ui_navigation' else 'binding_reconfirmation']='runtime_confirmed'
    saver(job)
    return True
