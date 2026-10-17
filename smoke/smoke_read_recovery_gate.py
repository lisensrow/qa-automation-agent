"""Synthetic finalization gate tests, not an autonomous regression acceptance."""
from copy import deepcopy
import json
import os_identity_comparison as g
from read_recovery_gate import (pending_context_recovery, continuation_message, refresh_progress,
                                partial_scope_reason, recovery_catalog, completed_read_refusal, next_framework_recovery,
                                partial_report)


def main():
    assert partial_scope_reason({'type': 'owned_regression_source_read'})
    assert partial_scope_reason({'type': 'owned_os_identity_raw_comparison', 'full_case_passed': True})
    assert not partial_scope_reason({'type': 'pinned_plugin_audit'})
    assert not partial_scope_reason(None)
    refs = [['20261017-000000-00000001', 'tc-00000001', 'ev-000000000001']] * 3
    for name in ['windows', 'astra']:
        r = g.requirement(name, 'fixture-read-recovery', *refs)
        c = {'case_id': 'tc-00000002', 'status': 'running', 'requirement': r, 'evidence': []}
        j = {'stand': 'lab', 'job_type': 'manual', 'status': 'running', 'resources': [],
             'request': ' '.join(r[k] for k in ['ci_name', 'ci_id', 'agent_id', 'profile_id']), 'test_cases': [c]}
        def receipt(result):
            return {'type': g.TOOL, 'source': 'uqa_tool', 'evidence_id': 'ev-000000000002',
                    'value': json.dumps({'tool': g.TOOL, 'arguments': {'target': name}, 'result': result})}
        assert pending_context_recovery(j, c['case_id']) is None
        assert 'status=BLOCKED' in partial_report(j, c['case_id'])
        assert 'raw_equal_fields' not in partial_report(j, c['case_id'])
        c['evidence'] = [receipt(g.blocked('observed_context', name))]
        assert 'full_case_passed=true' not in partial_report(j, c['case_id'])
        pending = pending_context_recovery(j, c['case_id'])
        assert pending['evidence_id'] == 'ev-000000000002'
        assert 'Choose' in continuation_message(pending)['content']
        # Durable own receipts survive reconstruction; no in-memory pending flag.
        assert pending_context_recovery(json.loads(json.dumps(j)), c['case_id']) == pending
        page, agent = pending['read_context_prerequisites']
        first = next_framework_recovery(j, c['case_id'])
        assert first['call'] == page and first['model_selected'] is False
        dispatch = {'type': 'read_recovery_dispatch', 'source': 'uqa_framework_read_recovery',
                    'value': json.dumps(first)}
        c['evidence'].append(dispatch)
        assert next_framework_recovery(j, c['case_id'])['blocked'] == 'read_context_recovery_not_verified'
        opened = {'type': page['tool'], 'source': 'uqa_tool', 'evidence_id': 'ev-000000000003',
                  'value': json.dumps({'tool': page['tool'], 'arguments': page['arguments'],
                                      'result': {'http_status': 200, 'current_url': page['arguments']['url'] + '?limit=50'}})}
        c['evidence'].append(opened)
        progress = pending_context_recovery(j, c['case_id'])
        assert progress['remaining_read_prerequisites'] == [agent]
        assert progress['completed_read_evidence'] == ['ev-000000000003']
        assert next_framework_recovery(j, c['case_id'])['call'] == agent
        catalog = [{'function': {'name': n}} for n in [page['tool'], agent['tool'], g.TOOL]]
        assert [t['function']['name'] for t in recovery_catalog(catalog, progress)] == [agent['tool']]
        assert len(catalog) == 3  # no mutation of the global registry
        assert recovery_catalog(catalog, None) is catalog
        denied = completed_read_refusal(j, c['case_id'], page['tool'], page['arguments'])
        assert denied['executed'] is False and denied['error'] == 'recovery_read_already_observed'
        assert completed_read_refusal(j, c['case_id'], agent['tool'], agent['arguments']) is None
        assert completed_read_refusal(j, 'tc-ffffffff', page['tool'], page['arguments']) is None
        discovery = [{'function': {'name': 'tool_catalog_select', 'parameters': {'properties': {
            'names': {'items': {'enum': [page['tool'], agent['tool'], g.TOOL]}}}}}}]
        assert page['tool'] not in recovery_catalog(discovery, progress)[0]['function']['parameters']['properties']['names']['items']['enum']
        messages = []
        refresh_progress(messages, progress); refresh_progress(messages, progress)
        assert len(messages) == 1
        refresh_progress(messages, None); assert not messages
        for result in [{'http_status': 403, 'current_url': page['arguments']['url']},
                       {'http_status': 200, 'current_url': 'https://other.invalid/cmdb'},
                       {'http_status': True, 'current_url': page['arguments']['url']}]:
            bad = deepcopy(j); bad['test_cases'][0]['evidence'][-1]['value'] = json.dumps({
                'tool': page['tool'], 'arguments': page['arguments'], 'result': result})
            assert len(pending_context_recovery(bad, c['case_id'])['remaining_read_prerequisites']) == 2
        c['evidence'].append({'type': agent['tool'], 'source': 'uqa_tool', 'evidence_id': 'ev-000000000004',
                             'value': json.dumps({'tool': agent['tool'], 'arguments': agent['arguments'],
                                                 'result': {'navigation_status': 'ready', 'task_list_observed': True}})})
        assert not pending_context_recovery(j, c['case_id'])['remaining_read_prerequisites']
        assert next_framework_recovery(j, c['case_id'])['call'] == {'tool': g.TOOL, 'arguments': {'target': name}}
        assert [t['function']['name'] for t in recovery_catalog(catalog, pending_context_recovery(j, c['case_id']))] == [g.TOOL]
        for stage in g.BLOCK_STAGES - {'observed_context'}:
            c['evidence'].append(receipt(g.blocked(stage, name)))
            assert pending_context_recovery(j, c['case_id']) is None
        for key, val in [('new_agent_tasks', 1), ('resend_authorized', True), ('full_case_passed', True)]:
            bad = g.blocked('observed_context', name); bad[key] = val
            c['evidence'] = [receipt(bad)]
            assert pending_context_recovery(j, c['case_id']) is None
        c['evidence'] = [receipt(g.blocked('observed_context', name))]
        c['evidence'][0]['source'] = 'operator'
        assert pending_context_recovery(j, c['case_id']) is None
        c['evidence'][0]['source'] = 'uqa_tool'
        for field, val in [('locked', False), ('target', 'other')]:
            bad = deepcopy(j); bad['test_cases'][0]['requirement'][field] = val
            assert pending_context_recovery(bad, c['case_id']) is None
        assert pending_context_recovery(j, 'tc-ffffffff') is None
    print('read recovery gate: PASS (canonical own scope, durable receipts, no source/time/hash recovery or authority; fixture only)')


if __name__ == '__main__':
    main()
