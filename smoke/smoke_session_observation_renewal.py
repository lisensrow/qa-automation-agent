"""Fresh observation contract: no endpoint, DB, network or model calls."""
from copy import deepcopy
import json
from unittest.mock import patch
import endpoint_metadata as ep
import session_observation_renewal as p
from operation_journal import _fingerprint

def main():
    ref = {'prior_job_id': 'old', 'prior_case_id': 'oldcase', 'prior_operation_id': 'op-old',
           'prior_read_evidence_id': 'ev-read', 'source_job_id': 'source',
           'source_case_id': 'sourcecase', 'source_case_key': 'US-T84'}
    oldr = ep.requirement('windows', 'old', ep.SESSIONS)
    r = ep.requirement('windows', 'new', ep.SESSIONS, ref)
    assert r['operation_stages'][0]['verification']['observation_renewal'] == ref
    assert 'observation_renewal' not in oldr
    proof = {'evidence_id': 'ev-read', 'identifier_value': 'old-task', 'postcondition_verified': True,
             'business_pass': False, 'resend_authorized': False}
    result = {k: oldr[k] for k in ('target', 'ci_id', 'agent_id', 'profile_id', 'payload_sha256')}
    result.update(job_id='old', case_id='oldcase', task_id='old-task', operation_id='op-old',
                  native_result_verified=True, result_sha256='a'*64,
                  read_at='2026-10-16T10:00:00+00:00', summary={'query_complete': True})
    e = {'evidence_id': 'ev-read', 'source': 'uqa_tool',
         'value': json.dumps({'tool': ep.READ, 'arguments': {'target': 'windows'}, 'result': result})}
    old = {'job_id': 'old', 'stand': 'lab', 'test_cases': [{'case_id': 'oldcase', 'requirement': oldr, 'evidence': [e]}]}
    op = {'operation_id': 'op-old', 'case_id': 'oldcase', 'workflow_id': ep.SESSIONS,
          'stage_id': 'metadata', 'tool': ep.CREATE, 'status': 'verified', 'verification': proof,
          'resource_key': oldr['operation_stages'][0]['resource_key'],
          'arguments_fingerprint': _fingerprint(oldr['operation_stages'][0]['arguments']),
          'verification_fingerprint': _fingerprint(oldr['operation_stages'][0]['verification']),
          'created_at': '2026-10-16T09:59:00+00:00'}
    sr = {'type': 'owned_regression_source_read', 'case_key': 'US-T84', 'campaign_id': 'source',
          'source_sha256': 'b'*64, 'source_manifest_sha256': 'c'*64}
    source = {'job_id': 'source', 'stand': 'lab', 'resources': [],
              'created_at': '2026-10-17T09:59:00+00:00',
              'test_cases': [{'case_id': 'sourcecase', 'requirement': sr, 'evidence': [{
                  'evidence_id': 'ev-source', 'source': 'uqa_tool', 'value': json.dumps({
                      'tool': 'knowledge_inspect_own_regression_read_coverage', 'result': {
                          'case_key': 'US-T84', 'source_sha256': 'b'*64, 'source_manifest_sha256': 'c'*64,
                          'complete_case_source_content_read': True}})}]}]}
    job = {'job_id': 'new', 'created_at': '2026-10-17T10:00:00+00:00', 'request': 'US-T84 source'}
    jobs = {'old': old, 'source': source}
    ops = {'old': [op], 'source': []}
    def run():
        return p.validate(job, r, jobs.__getitem__, lambda k: ops[k], list(jobs.values()),
                          '2026-10-17T10:01:00+00:00')
    def refuses():
        try: run()
        except (ValueError, KeyError, StopIteration): return
        raise AssertionError('unsafe renewal accepted')
    with patch('regression_read_coverage.requirement', return_value=sr):
        assert run()['new_observation_not_resend']
        for state in ['sending', 'uncertain', 'awaiting_verification', 'canceled', 'not_sent']:
            op['status'] = state; refuses()
        op['status'] = 'verified'
        for k in ['arguments_fingerprint', 'verification_fingerprint', 'resource_key']:
            original = op[k]; op[k] = 'wrong'; refuses(); op[k] = original
        for k, value in [('evidence_id', 'other'), ('postcondition_verified', False),
                         ('business_pass', True), ('resend_authorized', True)]:
            original = proof[k]; proof[k] = value; refuses(); proof[k] = original
        oldr['payload_sha256'] = 'x'*64; refuses(); oldr['payload_sha256'] = r['payload_sha256']
        original = job['created_at']; job['created_at'] = '2026-10-16T10:10:00+00:00'; refuses(); job['created_at'] = original
        source['resources'] = [{}]; refuses(); source['resources'] = []
        saved = source['test_cases'][0]['evidence']; source['test_cases'][0]['evidence'] = []; refuses()
        source['test_cases'][0]['evidence'] = saved
        ref2 = deepcopy(ref); ref2['source_case_key'] = 'US-T114'
        rr = ep.requirement('windows', 'new', ep.SESSIONS, ref2)
        savedr = r; r = rr; refuses(); r = savedr
        other = {'job_id': 'concurrent', 'test_cases': [{'requirement': oldr}]}
        jobs['concurrent'] = other; ops['concurrent'] = [{**op, 'status': 'sending'}]; refuses()
        ops['concurrent'] = [{**op, 'status': 'verified', 'operation_id': 'op-later',
                              'created_at': '2026-10-17T09:00:00+00:00'}]; refuses()
        del jobs['concurrent']; del ops['concurrent']; assert run()['prior_operation_id'] == 'op-old'
    for profile in [ep.SOFTWARE_CHANGE, ep.SOFTWARE_CHANGE_V2, ep.MSI, ep.DISKS]:
        try: p.declaration(ref, profile)
        except ValueError: pass
        else: raise AssertionError('side-effect/other profile renewal accepted')
    print('PASS explicit session observation renewal: old VERIFIED+own complete+new full source+age; unresolved/concurrent/latest/scope guards; no commands')

if __name__ == '__main__': main()
