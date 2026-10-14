"""Durable per-Job mutation intents; never grants permission or performs a mutation.

Separate snapshots prevent legacy whole-Job saves from erasing intents.
POSIX locks serialize claims, not remote requests. Uncertain outcomes fail closed.
"""
import hashlib
import json
import os
import re
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

UNRESOLVED = {'sending', 'uncertain', 'awaiting_verification'}


def _token(value):
    value = str(value or '')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}', value):
        raise ValueError('invalid operation context token')
    return value


def _paths(job_id):
    import job_store
    job_id = _token(job_id)
    root = job_store.JOBS_DIR / 'operations'
    root.mkdir(mode=0o770, parents=True, exist_ok=True)
    os.chmod(root, 0o770)
    return root / (job_id + '.json'), root / (job_id + '.lock')


@contextmanager
def _locked(job_id):
    # Fail closed on an unsupported runtime; UQA's current host is Linux.
    import fcntl
    path, lock_path = _paths(job_id)
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o660)
    try:
        os.fchmod(fd, 0o660)
        deadline = time.monotonic() + 5
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError('operation journal busy')
                time.sleep(.01)
        try:
            yield path
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def _load(path, job_id):
    if not path.exists():
        return {'version': 1, 'job_id': job_id, 'operations': []}
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('version') != 1 or data.get('job_id') != job_id or not isinstance(data.get('operations'), list):
        raise ValueError('invalid operation journal')
    seen = set()
    for operation in data['operations']:
        if (not isinstance(operation, dict) or operation.get('status') not in UNRESOLVED | {'verified', 'not_sent'}
                or not re.fullmatch(r'[0-9a-f]{64}', str(operation.get('arguments_fingerprint') or ''))
                or operation.get('operation_id') in seen):
            raise ValueError('invalid operation record')
        for key in ('operation_id', 'case_id', 'workflow_id', 'stage_id', 'resource_key', 'tool'):
            _token(operation.get(key))
        seen.add(operation['operation_id'])
    return data


def _context(job_id, case_id):
    import job_store
    job = job_store.get_job(_token(job_id))
    if not job or not any(c.get('case_id') == case_id for c in job.get('test_cases', [])):
        raise ValueError('operation Job/case missing')
    return job


def _fingerprint(arguments):
    # Persist no field values, credentials, request bodies or raw arguments.
    return hashlib.sha256(json.dumps(arguments, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _match(data, case_id, workflow_id, stage_id, resource_key):
    return next((o for o in reversed(data['operations']) if o['case_id'] == case_id
                 and o['workflow_id'] == workflow_id and o['stage_id'] == stage_id
                 and o['resource_key'] == resource_key), None)


def _readiness(data, case_id, workflow_id, stage_id, resource_key, fingerprint, tool=None, verification_contract=None):
    old = _match(data, case_id, workflow_id, stage_id, resource_key)
    if old and (old['status'] != 'not_sent' or old['arguments_fingerprint'] != fingerprint
                or old['tool'] != tool
                or old.get('verification_fingerprint') != (_fingerprint(verification_contract) if verification_contract is not None else None)):
        reason = 'operation_arguments_changed' if old['arguments_fingerprint'] != fingerprint else 'operation_replay_blocked'
        return {'allowed': False, 'reason': reason, 'operation_id': old['operation_id'], 'operation_status': old['status']}
    # Changing the tool, stage or workflow must not bypass an unresolved send.
    pending = next((o for o in data['operations'] if o['status'] in UNRESOLVED), None)
    if pending:
        return {'allowed': False, 'reason': 'operation_reconciliation_required',
                'operation_id': pending['operation_id'], 'operation_status': pending['status']}
    return {'allowed': True}


def inspect_operation(job_id, case_id, workflow_id, stage_id, resource_key, arguments, tool=None, verification_contract=None):
    _context(job_id, case_id)
    workflow_id, stage_id, resource_key = map(_token, (workflow_id, stage_id, resource_key))
    with _locked(job_id) as path:
        return _readiness(_load(path, job_id), case_id, workflow_id, stage_id, resource_key, _fingerprint(arguments), tool, verification_contract)


def begin_operation(job_id, case_id, workflow_id, stage_id, resource_key, tool, arguments, verification_contract=None):
    import job_store
    _context(job_id, case_id)
    workflow_id, stage_id, resource_key, tool = map(_token, (workflow_id, stage_id, resource_key, tool))
    fingerprint = _fingerprint(arguments)
    with _locked(job_id) as path:
        data = _load(path, job_id)
        ready = _readiness(data, case_id, workflow_id, stage_id, resource_key, fingerprint, tool, verification_contract)
        if not ready['allowed']:
            return ready
        if len(data['operations']) >= 10000:
            raise ValueError('operation journal limit reached')
        operation = {'operation_id': 'op-' + uuid.uuid4().hex, 'case_id': case_id,
                     'workflow_id': workflow_id, 'stage_id': stage_id, 'resource_key': resource_key,
                     'tool': tool, 'arguments_fingerprint': fingerprint, 'status': 'sending',
                     'verification_fingerprint': _fingerprint(verification_contract) if verification_contract is not None else None,
                     'created_at': job_store._now(), 'updated_at': job_store._now(), 'receipt': None}
        data['operations'].append(operation)
        job_store._atomic_write(path, data)  # Must finish BEFORE callback/send.
        return {'allowed': True, 'operation_id': operation['operation_id'], 'operation_status': 'sending'}


def record_receipt(job_id, operation_id, result=None, error_type=None):
    import job_store
    with _locked(job_id) as path:
        data = _load(path, job_id)
        operation = next(o for o in data['operations'] if o['operation_id'] == operation_id)
        if operation['status'] != 'sending':
            raise ValueError('operation not sending')
        valid_result = isinstance(result, dict)
        from native_dispatch import DisabledBeforeDispatch
        not_sent = (type(result) is DisabledBeforeDispatch and not error_type
                    and operation['tool'] == 'browser_click_semantic'
                    and result.get('error') == 'element_disabled'
                    and result.get('click_status') == 'not_executed')
        result = result if valid_result else {}
        acknowledged = (valid_result and not error_type and not result.get('error')
                        and result.get('executed') is not False and (
                            result.get('executed') is True or result.get('mutation_executed') is True
                            or result.get('click_status') == 'executed' or result.get('status') == 'ok'))
        operation['status'] = 'not_sent' if not_sent else ('awaiting_verification' if acknowledged else 'uncertain')
        # An ACK or click is NOT a verified product postcondition or PASS.
        operation['receipt'] = {'acknowledged': bool(acknowledged),
                                'error_type': str(error_type or '')[:80] or None,
                                'native_pre_dispatch_refusal': bool(not_sent)}
        operation['updated_at'] = job_store._now()
        job_store._atomic_write(path, data)
        return {'operation_id': operation_id, 'operation_status': operation['status']}


def list_operations(job_id):
    import job_store
    if job_store.get_job(_token(job_id)) is None:
        raise ValueError('operation Job missing')
    with _locked(job_id) as path:
        return _load(path, job_id)['operations']


def reconcile_operation(job_id, operation_id, evidence_id):
    import job_store
    from operation_recovery import evaluate_recovery
    with _locked(job_id) as path:
        data = _load(path, job_id)
        operation = next(o for o in data['operations'] if o['operation_id'] == operation_id)
        if operation['status'] == 'not_sent':
            return {'verified': False, 'reason': 'operation_was_not_sent',
                    'operation_id': operation_id, 'operation_status': 'not_sent',
                    'resend_authorized': False, 'bookkeeping_only': True, 'product_evidence': False}
        if operation['status'] == 'verified':
            # A later same-name object must not replace the accepted identity.
            proof = operation.get('verification') or {}
            if proof.get('evidence_id') != evidence_id:
                return {'verified': False, 'reason': 'operation_verification_immutable',
                        'operation_id': operation_id, 'operation_status': 'verified',
                        'resend_authorized': False, 'bookkeeping_only': True, 'product_evidence': False}
            return {**proof, 'operation_id': operation_id, 'operation_status': 'verified',
                    'resend_authorized': False, 'bookkeeping_only': True, 'product_evidence': False}
        job = _context(job_id, operation['case_id'])
        case = next(c for c in job['test_cases'] if c['case_id'] == operation['case_id'])
        requirement = case.get('requirement') or {}
        from operation_workflow import active_stage
        stage = active_stage(data, operation['case_id']) or requirement.get('operation_stage') or {}
        contract = stage.get('verification')
        if (requirement.get('locked') is not True or operation.get('verification_fingerprint') is None
                or _fingerprint(contract) != operation['verification_fingerprint']
                or any(stage.get(k) != operation[k] for k in ('workflow_id', 'stage_id', 'resource_key', 'tool'))
                or _fingerprint(stage.get('arguments')) != operation['arguments_fingerprint']):
            return {'verified': False, 'reason': 'recovery_contract_missing_or_changed', 'resend_authorized': False}
        proof = evaluate_recovery(job, operation, evidence_id, contract)
        if proof['verified']:
            operation['status'] = 'verified'
            operation['verification'] = proof
            operation['updated_at'] = job_store._now()
            job_store._atomic_write(path, data)
        return {**proof, 'operation_id': operation_id, 'operation_status': operation['status'],
                'bookkeeping_only': True, 'product_evidence': False}


def execute_journaled(context, callback):
    """Caller already passed unchanged action policy; journal never confirms it."""
    claim = begin_operation(**context)
    if not claim['allowed']:
        return {'error': claim['reason'], 'status': 'blocked_by_policy', 'executed': False,
                'action_policy_status': 'blocked_by_operation_journal', **claim}
    try:
        result = callback()
    except BaseException as exc:
        # os._exit/power loss instead leaves durable 'sending', also blocking.
        record_receipt(context['job_id'], claim['operation_id'], error_type=type(exc).__name__)
        raise
    receipt = record_receipt(context['job_id'], claim['operation_id'], result=result)
    return {**result, **receipt} if isinstance(result, dict) else result
