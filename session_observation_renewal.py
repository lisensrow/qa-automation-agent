"""Explicit fresh session observation, never replay an unresolved command.

Only the immutable read-only WTS/logind census may use this contract. A new
source-reading Job must require the observation after a >=1h-old VERIFIED
result. The original no-rekey rule remains the default for every profile.
"""
import json
from plugin_preparation import stamp, now
from user_session_census import PROFILE

KEYS = {'prior_job_id', 'prior_case_id', 'prior_operation_id', 'prior_read_evidence_id',
        'source_job_id', 'source_case_id', 'source_case_key'}
FIELDS = ('target', 'ci_id', 'agent_id', 'ci_name', 'core_version', 'profile_id', 'payload_sha256')

def declaration(value, profile):
    if (profile != PROFILE or type(value) is not dict or set(value) != KEYS
        or any(type(v) is not str or not 1 <= len(v) <= 100 for v in value.values())):
        raise ValueError('session_renewal_exact_reference_required')
    return dict(value)

def validate(job, requirement, loader, operations, jobs, current_time=None):
    ref = declaration(requirement.get('observation_renewal'), requirement.get('profile_id'))
    old = loader(ref['prior_job_id'])
    c = next(c for c in old['test_cases'] if c['case_id'] == ref['prior_case_id'])
    previous = c['requirement']
    from endpoint_metadata import requirement as endpoint_requirement
    from operation_journal import _fingerprint
    if previous != endpoint_requirement(previous.get('target'), previous.get('campaign_id'),
                                         previous.get('profile_id'), previous.get('observation_renewal')):
        raise ValueError('session_renewal_prior_locked_contract_required')
    stage = previous['operation_stages'][0]
    if (old['job_id'] == job['job_id'] or old.get('stand') != 'lab'
        or previous.get('type') != 'closed_endpoint_metadata' or previous.get('locked') is not True
        or any(previous.get(k) != requirement.get(k) for k in FIELDS)):
        raise ValueError('session_renewal_same_immutable_scope_required')
    ops = operations(old['job_id'])
    op = next(o for o in ops if o['operation_id'] == ref['prior_operation_id'])
    proof = op.get('verification') or {}
    e = next(e for e in c['evidence'] if e['evidence_id'] == ref['prior_read_evidence_id'])
    b = json.loads(e['value']); result = b['result']
    if (any(o['status'] not in {'verified', 'not_sent', 'rejected'} for o in ops)
        or op.get('status') != 'verified' or op.get('case_id') != c['case_id']
        or op.get('workflow_id') != PROFILE or op.get('stage_id') != 'metadata'
        or op.get('tool') != 'browser_start_closed_endpoint_metadata_semantic'
        or op.get('arguments_fingerprint') != _fingerprint(stage['arguments'])
        or op.get('verification_fingerprint') != _fingerprint(stage['verification'])
        or op.get('resource_key') != stage['resource_key']
        or proof.get('evidence_id') != e['evidence_id'] or proof.get('postcondition_verified') is not True
        or proof.get('business_pass') is not False or proof.get('resend_authorized') is not False
        or proof.get('identifier_value') != result.get('task_id')
        or e.get('source') != 'uqa_tool' or b.get('tool') != 'browser_inspect_closed_endpoint_metadata_semantic'
        or b.get('arguments') != {'target': requirement['target']} or result.get('error')
        or result.get('native_result_verified') is not True or not result.get('result_sha256')
        or result.get('job_id') != old['job_id'] or result.get('case_id') != c['case_id']
        or result.get('operation_id') != op['operation_id']
        or any(result.get(k) != requirement.get(k) for k in ('target', 'ci_id', 'agent_id', 'profile_id', 'payload_sha256'))
        or (result.get('summary') or {}).get('query_complete') is not True):
        raise ValueError('session_renewal_verified_own_complete_result_required')
    read_at = stamp(result['read_at']); created = stamp(job['created_at'])
    current = stamp(current_time or now())
    if (created - read_at).total_seconds() < 3600 or not -5 <= (current - created).total_seconds() <= 1800:
        raise ValueError('session_renewal_old_observation_new_job_time_required')
    source = loader(ref['source_job_id'])
    sc = next(c for c in source['test_cases'] if c['case_id'] == ref['source_case_id'])
    from regression_read_coverage import requirement as source_requirement
    sr = sc.get('requirement') or {}
    allowed_sources = {'windows': {'US-T84', 'US-T83', 'US-T89'},
                       'astra': {'US-T114', 'US-T112', 'US-T130'}}
    if (ref['source_case_key'] not in allowed_sources.get(requirement['target'], set())
        or ref['source_case_key'] not in job.get('request', '')
        or ref['source_job_id'] not in job.get('request', '')
        or source.get('stand') != 'lab' or source.get('resources')
        or sr != source_requirement(ref['source_case_key'], sr.get('campaign_id'))
        or operations(source['job_id']) or stamp(source['created_at']) <= read_at
        or stamp(source['created_at']) > created):
        raise ValueError('session_renewal_new_own_source_required')
    coverage = []
    for se in sc.get('evidence', []):
        if se.get('source') != 'uqa_tool': continue
        sb = json.loads(se['value']); sv = sb.get('result') or {}
        if (sb.get('tool') == 'knowledge_inspect_own_regression_read_coverage'
            and sv.get('case_key') == ref['source_case_key']
            and sv.get('source_sha256') == sr['source_sha256']
            and sv.get('source_manifest_sha256') == sr['source_manifest_sha256']
            and sv.get('complete_case_source_content_read') is True):
            coverage.append(se['evidence_id'])
    if not coverage: raise ValueError('session_renewal_complete_source_receipts_required')
    # A new observation is not permission to repeat another historical operation.
    # All same-scope commands must be resolved; the reference must be the latest
    # actual verified observation. Concurrent reservations stop the new POST.
    history = []
    for other in jobs:
        if other['job_id'] == job['job_id']: continue
        if not any((c.get('requirement') or {}).get('type') == 'closed_endpoint_metadata'
                   and c['requirement'].get('target') == requirement['target']
                   and c['requirement'].get('profile_id') == PROFILE for c in other.get('test_cases', [])): continue
        for other_op in operations(other['job_id']):
            if other_op['status'] in {'not_sent', 'rejected'}: continue
            if other_op['status'] != 'verified': raise ValueError('session_renewal_unresolved_history_no_replay')
            history.append((stamp(other_op['created_at']), other_op['operation_id']))
    if not history or max(history)[1] != op['operation_id']:
        raise ValueError('session_renewal_latest_verified_reference_required')
    return {'prior_operation_id': op['operation_id'], 'prior_result_sha256': result['result_sha256'],
            'source_coverage_evidence_ids': coverage, 'new_observation_not_resend': True}
