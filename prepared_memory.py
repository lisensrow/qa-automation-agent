"""Explicit opt-in memory context for a prepared read-only Job."""
from datetime import datetime, timezone
from product_knowledge_retrieval import retrieve_product_knowledge


def prepare_memory_context(job, case_id, detector, loader, saver, retriever=None):
    case = next((c for c in job.get('test_cases', []) if c.get('case_id') == case_id), {})
    requirement = case.get('requirement') or {}
    query = requirement.get('memory_query')
    if query is None:
        return job, None
    if (requirement.get('action_profile') != 'read_only' or not isinstance(query, str)
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
    }
    saver(latest)
    return latest, payload
