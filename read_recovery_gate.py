"""Own-receipt progress, bounded Core READ recovery and partial report boundaries.

The model originates the comparator intent. Core may compile canonical context
reads and its retry, explicitly attributed to framework rather than model choice.
No new permission, endpoint mutation, oracle change or business PASS is granted.
"""
import json
from copy import deepcopy
from urllib.parse import urlsplit


def pending_context_recovery(job, case_id):
    from os_identity_comparison import TOOL, compact, validate_context
    try:
        case = next(c for c in job['test_cases'] if c['case_id'] == case_id)
        requirement = validate_context(job, case_id, {'target': case['requirement']['target']})
        pending = None
        for evidence in case.get('evidence', []):
            if evidence.get('source') != 'uqa_tool':
                continue
            receipt = json.loads(evidence['value'])
            if pending and evidence.get('type') == receipt.get('tool'):
                result = receipt.get('result') or {}
                for call in list(pending['remaining_read_prerequisites']):
                    if receipt.get('tool') != call['tool'] or receipt.get('arguments') != call['arguments'] or result.get('error'):
                        continue
                    if call['tool'] == 'browser_open_page':
                        actual = urlsplit(str(result.get('current_url') or ''))
                        expected = urlsplit(call['arguments']['url'])
                        done = (type(result.get('http_status')) is int and result['http_status'] == 200
                                and (actual.scheme, actual.netloc, actual.path) == (expected.scheme, expected.netloc, expected.path))
                    else:
                        done = result.get('navigation_status') == 'ready' and result.get('task_list_observed') is True
                    if done:
                        pending['remaining_read_prerequisites'].remove(call)
                        pending['completed_read_evidence'].append(evidence['evidence_id'])
            if receipt.get('tool') != TOOL or receipt.get('arguments') != {'target': requirement['target']}:
                continue
            if evidence.get('type') != TOOL:
                continue
            result = compact(receipt.get('result'))
            # Only the canonical stage-tagged missing-context refusal is recoverable.
            # A subsequent comparison/error supersedes it; source/time/hash/readiness
            # failures must never become permission to navigate or resend commands.
            pending = None
            if result.get('blocked_stage') == 'observed_context' and result.get('read_context_prerequisites'):
                pending = {'evidence_id': evidence['evidence_id'], 'blocked_stage': 'observed_context',
                           'read_context_prerequisites': result['read_context_prerequisites'],
                           'remaining_read_prerequisites': list(result['read_context_prerequisites']),
                           'completed_read_evidence': []}
        return pending
    except (KeyError, ValueError, TypeError, AttributeError, StopIteration):
        return None


def continuation_message(pending):
    return {'role': 'user', 'content': (
        '[UQA CORE: UNRESOLVED RECOVERABLE READ]\n'
        'Your own receipt reports a missing observation, not a terminal environment failure. '
        'A final explanation of the prerequisite does not perform it. Choose the supported '
        'read/navigation tools yourself, obtain the required context, then retry the original '
        'read. Do not repeat an unchanged refusal. No commands, delivery, permission upgrade, '
        'expected changes or PASS are authorized. If an attempted prerequisite itself fails, '
        'report its actual evidence and BLOCKED; do not invent success. Recovery is bounded.\n'
        + json.dumps(pending, ensure_ascii=False))}


def refresh_progress(messages, pending):
    """Replace a bounded trusted progress view; no accumulated reminder history."""
    messages[:] = [m for m in messages if not m.get('uqa_read_recovery_progress')]
    if pending:
        messages.append({'role': 'user', 'uqa_read_recovery_progress': True, 'content': (
            '[UQA CORE: OWN READ RECOVERY PROGRESS]\n'
            'Completed prerequisite receipts are already obtained: do not repeat those actions. '
            'Choose a remaining read yourself; when none remain, retry the original comparison. '
            'This records navigation only, not a comparison, execution authority or PASS. '
            'If a prerequisite fails, report its actual evidence; never resend endpoint commands.\n'
            + json.dumps(pending, ensure_ascii=False))})


def partial_scope_reason(requirement):
    """Do not promote partial observer Jobs to a full source-case PASS.

    Individual checked observations remain untouched; this only constrains the
    case-level verdict and prevents success-triggered knowledge generation.
    """
    if isinstance(requirement, dict) and requirement.get('type') in {
        'owned_regression_source_read', 'owned_os_identity_raw_comparison',
        'owned_dmi_identity_raw_comparison',
    }:
        return 'partial_source_or_recorded_comparison_not_full_regression_case'
    return None


def recovery_catalog(catalog, pending):
    """Do not offer a completed prerequisite again during the same recovery.

    Other tools and final BLOCKED remain model choices; this dispatches nothing.
    Only exact own canonical receipt state can retire a prerequisite tool.
    """
    if not pending:
        return catalog
    from os_identity_comparison import TOOL
    # This is a framework prerequisite protocol, not unrestricted UI planning.
    # Keep source lookup / state inspection available, but do not substitute a
    # generic table observation for the declared own-agent context operation.
    allowed = {'browser_get_state', 'knowledge_search',
               'knowledge_read_indexed_source_window'}
    remaining = pending['remaining_read_prerequisites']
    allowed |= {call['tool'] for call in remaining} if remaining else {TOOL}
    result = []
    for tool in deepcopy(catalog):
        fn = tool['function']
        if fn['name'] != 'tool_catalog_select' and fn['name'] not in allowed:
            continue
        if fn['name'] == 'tool_catalog_select':
            values = fn['parameters']['properties']['names']['items']['enum']
            fn['parameters']['properties']['names']['items']['enum'] = [n for n in values if n in allowed]
        result.append(tool)
    return result


def completed_read_refusal(job, case_id, name, arguments):
    pending = pending_context_recovery(job, case_id)
    if pending:
        for call in pending['read_context_prerequisites']:
            if call['tool'] == name and call['arguments'] == arguments and call not in pending['remaining_read_prerequisites']:
                return {'error': 'recovery_read_already_observed', 'executed': False,
                        'completed_read_evidence': pending['completed_read_evidence'],
                        'remaining_read_prerequisites': pending['remaining_read_prerequisites'],
                        'resend_authorized': False, 'full_case_passed': False}
    return None


def next_framework_recovery(job, case_id):
    """Recover the model's original READ intent, never originate a new intent.

    Each dispatch is durably attributed to Core, not model-selected. At most the
    two canonical reads plus one retry; a failed prerequisite is not replayed.
    """
    pending = pending_context_recovery(job, case_id)
    if not pending:
        return None
    from os_identity_comparison import TOOL
    case = next(c for c in job['test_cases'] if c['case_id'] == case_id)
    events = [json.loads(e['value']) for e in case.get('evidence', [])
              if e.get('source') == 'uqa_framework_read_recovery'
              and e.get('type') == 'read_recovery_dispatch']
    target = case['requirement']['target']
    call = (pending['remaining_read_prerequisites'][0] if pending['remaining_read_prerequisites']
            else {'tool': TOOL, 'arguments': {'target': target}})
    if len(events) >= 3 or any(e.get('call') == call for e in events):
        return {'blocked': 'read_context_recovery_not_verified', 'origin_evidence_id': pending['evidence_id']}
    return {'call': deepcopy(call), 'origin_evidence_id': pending['evidence_id'],
            'dispatch_origin': 'framework_read_context_recovery', 'model_selected': False}


def partial_report(job, case_id):
    """Publish only canonical partial facts; rejected model prose stays evidence.

    Not a model reasoning score or business oracle. No result means UNKNOWN.
    """
    case = next(c for c in job['test_cases'] if c['case_id'] == case_id)
    requirement = case.get('requirement') or {}
    if not partial_scope_reason(requirement):
        raise ValueError('partial_report_scope_required')
    lines = ['[UQA CORE: PARTIAL READ REPORT]', 'status=BLOCKED',
             'reason=partial_source_or_recorded_comparison_not_full_regression_case',
             'Full source-case execution and business PASS are not established.',
             'Model narrative is retained separately as unaccepted evidence, not published as a verified conclusion.']
    kind = requirement.get('type')
    if kind in {'owned_os_identity_raw_comparison', 'owned_dmi_identity_raw_comparison'}:
        if kind == 'owned_os_identity_raw_comparison':
            from os_identity_comparison import TOOL, compact
        else:
            from smbios_identity_comparison import TOOL, compact
        for evidence in reversed(case.get('evidence', [])):
            if evidence.get('source') != 'uqa_tool' or evidence.get('type') != TOOL:
                continue
            try:
                receipt = json.loads(evidence['value'])
                if receipt.get('tool') != TOOL or receipt.get('arguments') != {'target': requirement.get('target')}:
                    continue
                result = compact(receipt.get('result'))
                if result.get('independent_raw_value_comparison_done') is True:
                    lines += ['recorded_pair_only=true; current_state_and_product_naming_contract_unverified=true',
                              'evidence_id=' + evidence['evidence_id'],
                              json.dumps({k: result.get(k) for k in ['raw_hypothesis_status', 'field_count',
                                  'raw_equal_fields', 'raw_different_fields', 'unknown_fields']}, ensure_ascii=False)]
                    break
            except (ValueError, TypeError, AttributeError):
                continue
    return '\n'.join(lines)
