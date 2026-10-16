"""Evidence-bound postcondition checks. Never sends requests or authorizes retries."""
import json
from datetime import datetime, timezone
from urllib.parse import urlsplit


def _time(value):
    parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('timestamp timezone missing')
    return parsed


def _origin(value):
    url = urlsplit(value)
    return url.scheme.lower(), url.netloc.lower()


def _read(case, evidence_id, contract, before=None, after=None):
    evidence = next(e for e in case.get('evidence', []) if e.get('evidence_id') == evidence_id)
    if (evidence.get('type') != 'browser_get_network_detail' or evidence.get('source') != 'uqa_tool'
            or evidence.get('usable_for_verdict') is not True or evidence.get('execution_status') not in {'executed', 'observed'}):
        raise ValueError('unusable native network evidence')
    envelope = json.loads(evidence['value'])
    if envelope.get('tool') != 'browser_get_network_detail':
        raise ValueError('wrong evidence tool')
    result = envelope['result']
    status = result.get('status')
    if (result.get('error') or result.get('response_body_truncated') is True or result.get('method') != 'GET' or type(status) is not int
            or not 200 <= status < 300 or not result.get('session_id') or not result.get('request_id')
            or envelope.get('arguments', {}).get('request_id') != result['request_id']):
        raise ValueError('invalid read receipt')
    received = _time(result.get('received_at'))
    started = _time(result.get('request_started_at'))
    if started > received:
        raise ValueError('invalid request timing')
    if before is not None and received > before:
        raise ValueError('baseline after intent')
    if after is not None:
        if started < after or received < after or not -5 <= (datetime.now(timezone.utc) - received).total_seconds() <= 300:
            raise ValueError('stale read')
    url = urlsplit(result.get('url') or '')
    if (url.path.rstrip('/') != contract['endpoint'].rstrip('/') or url.fragment
            or _origin(result.get('response_origin') or '') != _origin(contract['origin'])
            or (url.netloc and _origin(result['url']) != _origin(contract['origin']))):
        raise ValueError('endpoint/origin mismatch')
    observations = {o['observation_id']: o for o in case.get('observations', [])}
    linked = [observations[i] for i in evidence.get('observation_ids', []) if i in observations]
    if not any(o.get('type') == 'api_exchange' and o.get('source') == 'browser_xhr'
               and o.get('data', {}).get('request_id') == result['request_id']
               and o.get('data', {}).get('session_id') == result['session_id'] for o in linked):
        raise ValueError('network observation link missing')
    if not any(o.get('type') == 'ui_state' and o.get('source') == 'browser'
               and o.get('data', {}).get('session_id') == result['session_id']
               and _origin(o.get('data', {}).get('url') or '') == _origin(contract['origin'])
               for o in case.get('observations', [])):
        raise ValueError('browser origin witness missing')
    raw = result.get('response_body')
    if not isinstance(raw, str) or len(raw) > 65536:
        raise ValueError('response size/type')
    body = json.loads(raw)
    items = body.get('items') if isinstance(body, dict) else None
    if (not isinstance(items, list) or type(body.get('total')) is not int or type(body.get('count')) is not int
            or body['total'] != len(items) or body['count'] != len(items)
            or type(body.get('offset')) is not int or body['offset'] != 0 or any(not isinstance(i, dict) for i in items)):
        raise ValueError('incomplete collection')
    return items


def evaluate_recovery(job, operation, evidence_id, contract):
    """Requires explicit locked immutable oracle + complete before/after GETs."""
    if isinstance(contract,dict) and contract.get('kind')=='owned_plugin_discovery':
        from plugin_discovery import evaluate
        return evaluate(job,operation,evidence_id,contract)
    if isinstance(contract,dict) and contract.get('kind')=='owned_plugin_preparation':
        from plugin_preparation_recovery import evaluate
        return evaluate(job,operation,evidence_id,contract)
    if isinstance(contract,dict) and contract.get('kind')=='owned_command_stage_execution':
        from command_stage_recovery import evaluate
        return evaluate(job,operation,evidence_id,contract)
    if isinstance(contract,dict) and contract.get('kind')=='owned_agent_audit_execution':
        from audit_operation_recovery import evaluate
        return evaluate(job,operation,evidence_id,contract)
    if isinstance(contract,dict) and contract.get('kind')=='owned_plugin_audit_execution':
        from plugin_audit_runtime import evaluate_execution
        return evaluate_execution(job,operation,evidence_id,contract)
    try:
        if (not isinstance(contract, dict) or type(contract.get('version')) is not int or contract['version'] != 1
                or contract.get('kind') not in {'member_present', 'member_absent'}
                or not isinstance(contract.get('endpoint'), str) or not contract['endpoint'].startswith('/')
                or contract['endpoint'].startswith('//') or urlsplit(contract['endpoint']).query
                or _origin(contract.get('origin') or '')[0] not in {'http', 'https'}):
            raise ValueError('invalid recovery contract')
        case = next(c for c in job['test_cases'] if c['case_id'] == operation['case_id'])
        baseline = _read(case, contract['baseline_evidence_id'], contract, before=_time(operation['created_at']))
        current = _read(case, evidence_id, contract, after=_time(operation['created_at']))
        id_key = contract.get('identifier_key', 'id')
        selector = contract['selector']
        if not isinstance(selector, dict) or len(selector) != 1 or not all(isinstance(v, (str, int)) and not isinstance(v, bool) for v in selector.values()):
            raise ValueError('exact selector required')
        def matches(items):
            return [i for i in items if all(type(i.get(k)) is type(v) and i.get(k) == v for k, v in selector.items())]
        old, new = matches(baseline), matches(current)
        if contract['kind'] == 'member_absent':
            if set(selector) != {id_key} or len(old) != 1 or new:
                raise ValueError('owned absence not proved')
            resource = next(r for r in job.get('resources', []) if r['resource_id'] == contract['resource_id'])
            if (resource.get('created_by_case') != case['case_id'] or resource.get('metadata', {}).get('disposable') is not True
                    or str(resource.get('external_id')) != str(selector[id_key])):
                raise ValueError('owned identifier mismatch')
            identifier = str(selector[id_key])
            identifier_scalar = selector[id_key]
        else:
            if len(new) != 1 or type(new[0].get(id_key)) not in (str, int) or not str(new[0][id_key]).strip():
                raise ValueError('exact current member not proved')
            expected = contract.get('expected_fields')
            if not isinstance(expected, dict) or not expected:
                raise ValueError('expected fields missing')
            for key, value in expected.items():
                if any(marker in key.casefold() for marker in ('password', 'secret', 'token', 'cookie', 'credential')):
                    raise ValueError('secret assertion prohibited')
                if type(new[0].get(key)) is not type(value) or new[0].get(key) != value:
                    raise ValueError('expected state not proved')
            if id_key in selector:
                resource = next(r for r in job.get('resources', []) if r['resource_id'] == contract['resource_id'])
                if len(old) != 1 or str(resource.get('external_id')) != str(selector[id_key]) or resource.get('created_by_case') != case['case_id']:
                    raise ValueError('owned baseline mismatch')
                allowed = contract.get('allowed_changed_fields')
                if not isinstance(allowed, list) or not allowed:
                    raise ValueError('change allowlist missing')
                if any(old[0].get(k) != new[0].get(k) for k in set(old[0]) | set(new[0]) if k not in allowed):
                    raise ValueError('unrelated field changed')
            elif old:
                raise ValueError('creation baseline was not absent')
            identifier = str(new[0][id_key])
            identifier_scalar = new[0][id_key]
        return {'verified': True, 'evidence_id': evidence_id, 'baseline_evidence_id': contract['baseline_evidence_id'],
                'identifier_value': identifier, 'postcondition_verified': True,
                'identifier_scalar': identifier_scalar,
                'resend_authorized': False, 'causal_execution_proven': False}
    except (ValueError, TypeError, KeyError, StopIteration, AttributeError):
        # Missing/negative/stale evidence NEVER releases a pending send to retry.
        return {'verified': False, 'reason': 'recovery_evidence_insufficient', 'resend_authorized': False}
