"""Knowledge-only boundary and current source provenance; isolated fixtures."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import advisory_contract as advisory
import job_store
import knowledge_index as index
import operation_journal
import stands
import uqa
import static_source_facts

assert advisory.interleave_reviewed_results([[1, 2, 3, 4], [5, 6, 7], [8, 9, 10], [11]]) == [1, 5, 8, 2, 6, 9, 3, 7, 10]
assert advisory.interleave_reviewed_results([[], [1], None]) == [1]

with TemporaryDirectory(prefix='uqa-advisory-') as temp:
    root = Path(temp)
    source_root = root / 'source'; (source_root / 'UQA-experience').mkdir(parents=True)
    path = source_root / 'UQA-experience' / 'fixture.md'
    original = '# Fixture\n\n## Namespace\nThe current catalog uses fixture.field. job-static ev-static\n'
    path.write_text(original, encoding='utf-8')
    chunks = index.make_chunks(index.read_document(path))
    rows = [{'source': 'UQA-experience/fixture.md', 'chunk_no': i, **row}
            for i, row in enumerate(chunks, 1)]
    sources = advisory.recheck_source_chunks(rows, source_root)
    assert sources and sources[0]['source_sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert not sources[0]['current_runtime_verified']
    (source_root / 'other').mkdir()
    (source_root / 'other' / 'private.md').write_text(original, encoding='utf-8')
    for mode in ('stale', 'outside', 'namespace_escape', 'alias_path', 'backslash', 'unknown_source', 'wrong_number', 'bool_number', 'wrong_heading'):
        bad = deepcopy(rows)
        if mode == 'stale': bad[0]['content'] = 'made-up source'
        elif mode == 'outside': bad[0]['source'] = 'UQA-experience/../../private.md'
        elif mode == 'namespace_escape': bad[0]['source'] = 'UQA-experience/../other/private.md'
        elif mode == 'alias_path': bad[0]['source'] = 'UQA-experience/../UQA-experience/fixture.md'
        elif mode == 'backslash': bad[0]['source'] = 'UQA-experience/..\\other\\private.md'
        elif mode == 'unknown_source': bad[0]['source'] = 'unreviewed/fixture.md'
        elif mode == 'wrong_number': bad[0]['chunk_no'] = 99999
        elif mode == 'bool_number': bad[0]['chunk_no'] = True
        else: bad[0]['heading'] = 'made-up heading'
        assert not advisory.recheck_source_chunks(bad[:1], source_root), mode
    good = {'answer': 'Known behavior [S1].', 'citations': ['S1'], 'limitations': 'Not runtime verified.'}
    message = {'content': json.dumps(good)}
    validated = advisory.validate_answer(message, sources)
    assert not validated['evidence_for_pass'] and not validated['execution_authorized']
    assert not validated['factual_accuracy_verified']
    for mode in ('tool', 'citation', 'observation', 'test_json', 'empty_text', 'extra', 'duplicate', 'unknown_text_citation'):
        bad = deepcopy(message)
        if mode == 'tool': bad['tool_calls'] = [{'function': {'name': 'browser_click_semantic', 'arguments': {}}}]
        elif mode == 'test_json': bad['content'] = '[UQA_CHECKS_JSON]'
        elif mode == 'duplicate': bad['content'] = '{"answer":"one","answer":"two","citations":["S1"],"limitations":"unknown"}'
        else:
            payload = deepcopy(good)
            if mode == 'citation': payload['citations'] = ['S999']
            elif mode == 'observation': payload['answer'] = 'obs-forged'
            elif mode == 'empty_text': payload['answer'] = '   '
            elif mode == 'unknown_text_citation': payload['answer'] = 'Source [S999].'
            else: payload['status'] = 'passed'
            bad['content'] = json.dumps(payload)
        try: advisory.validate_answer(bad, sources)
        except ValueError: pass
        else: raise AssertionError(mode)

    with patch.object(job_store, 'JOBS_DIR', root / 'jobs'), \
         patch.object(index, 'SOURCE_DIR', source_root), \
         patch.object(stands, 'get_stand', return_value={'web_url': 'https://fixture.test'}), \
         patch.object(uqa, 'execute_tool', return_value={'results': rows}) as dispatch, \
         patch.object(uqa, 'ask_ollama', return_value={'message': message}) as model:
        for invalid_stand in (None, 'fixture ', '../fixture'):
            try: advisory.run_advisory_request('Explain.', invalid_stand)
            except ValueError: pass
            else: raise AssertionError('invalid stand reached Job creation')
        assert not list((root / 'jobs').glob('*.json')) and model.call_count == 0
        result = advisory.run_advisory_request('Explain the fixture catalog.', 'fixture')
        saved = job_store.get_job(result['job_id'])
        assert saved['status'] == 'blocked' and saved['advisory']['state'] == 'answered'
        assert saved['test_cases'] == [] and saved['resources'] == []
        assert operation_journal.list_operations(result['job_id']) == []
        assert result['sources'][0]['citation_id'] == 'S1'
        assert dispatch.call_count == 1 and model.call_count == 1
        assert model.call_args.kwargs['tools'] == []
        assert model.call_args.kwargs['response_schema']['additionalProperties'] is False
        assert model.call_args.kwargs['response_schema']['properties']['citations']['items']['enum'] == [s['citation_id'] for s in sources]
        assert advisory.valid_advisory_job(saved)
        assert not advisory.advisory_tool_allowed(saved, 'knowledge_search')  # No post-completion reuse.
        running = deepcopy(saved); running['status'] = 'running'; running['advisory']['state'] = 'running'
        assert advisory.advisory_tool_allowed(running, 'knowledge_search')
        for mode in ('request', 'stand', 'unlocked_tools', 'int_flags', 'case', 'resource', 'job_type'):
            bad = deepcopy(running)
            if mode == 'request': bad['request'] += ' changed'
            elif mode == 'stand': bad['stand'] = 'other'
            elif mode == 'unlocked_tools': bad['advisory']['contract']['allowed_tools'].append('browser_click_semantic')
            elif mode == 'int_flags': bad['advisory']['contract']['model_tools_enabled'] = 0
            elif mode == 'case': bad['test_cases'] = [{'planned_checks': [{'status': 'passed'}]}]
            elif mode == 'resource': bad['resources'] = [{'name': 'fixture'}]
            else: bad['job_type'] = 'regression'
            assert not advisory.valid_advisory_job(bad), mode
        job_store.save_job(running)
        before_dispatch = dispatch.call_count
        for tool, args in [('browser_click_semantic', {'name': 'Create'}),
                           ('browser_click_semantic', {'name': 'Delete'}),
                           ('browser_open_page', {'url': 'https://fixture.test'}),
                           ('ssh_run', {'command': 'anything'}), ('unknown_tool', {})]:
            blocked = uqa.execute_tool_with_policy(tool, args, [], job_id=saved['job_id'],
                                                    action_policy='confirm_mutations')
            assert blocked['action_policy_status'] == 'blocked_by_advisory_contract'
        assert dispatch.call_count == before_dispatch
        try: uqa.run_turn([], job_id=saved['job_id'])
        except ValueError: pass
        else: raise AssertionError('advisory Job entered test loop')

        model.return_value = {'message': {'content': '{}', 'tool_calls': [{'function': {'name': 'unknown_tool'}}]}}
        rejected = advisory.run_advisory_request('Explain without execution.', 'fixture')
        assert rejected['advisory_state'] == 'unavailable' and rejected['response'] is None
        assert job_store.get_job(rejected['job_id'])['advisory']['error_code'] == 'advisory_model_tool_call_rejected'
        assert job_store.get_job(rejected['job_id'])['test_cases'] == []
        model.return_value = {'message': message}
        def change_source(*args, **kwargs):
            path.write_text(original + 'Source changed during generation.\n', encoding='utf-8')
            return {'message': message}
        model.side_effect = change_source
        changed = advisory.run_advisory_request('Explain source freshness.', 'fixture')
        assert changed['advisory_state'] == 'unavailable' and changed['response'] is None
        path.write_text(original, encoding='utf-8')
        # Separately retained typed fact, never overwritten by a contradictory model paraphrase.
        typed = {'status': 'historical_candidate', 'stand': 'fixture',
            'source_job_id': 'job-static', 'source_evidence_id': 'ev-static',
            'source_case_id': 'case-static', 'evidence_sha256': 'a' * 64,
            'facts': [{'predicate': 'fixture.enabled', 'value': True,
                       'value_type': 'bool', 'source_sha256': 'b' * 64}], **static_source_facts.FLAGS}
        model.side_effect = None
        model.return_value = {'message': {'content': json.dumps({
            'answer': 'False [S1].', 'citations': ['S1'], 'limitations': 'Unverified model prose.'})}}
        with patch.object(static_source_facts, 'read_registered_static_facts', return_value=typed):
            grounded = advisory.run_advisory_request('Explain fixture.', 'fixture')
            assert grounded['historical_static_facts']['facts'][0]['value'] is True
            assert grounded['response']['answer'] == 'False [S1].'
            assert grounded['response']['factual_accuracy_verified'] is False
            assert grounded['historical_static_facts']['current_runtime_verified'] is False
            assert 'historical_static_facts' not in model.call_args.args[0][1]['content']
            assert job_store.get_job(grounded['job_id'])['advisory']['historical_static_facts'] == grounded['historical_static_facts']
        with patch.object(static_source_facts, 'read_registered_static_facts',
                          side_effect=[typed, {**typed, 'evidence_sha256': 'c' * 64}]):
            changed_static = advisory.run_advisory_request('Explain fixture.', 'fixture')
            assert changed_static['response'] is None and changed_static['historical_static_facts'] is None
            assert job_store.get_job(changed_static['job_id'])['advisory']['error_code'] == 'advisory_static_source_changed_during_model_call'
        model.return_value = {'message': message}
        # Use a captured creation ID rather than infer another request's Job.
        created = []
        original_create = job_store.create_job
        def capture_create(*args, **kwargs):
            job = original_create(*args, **kwargs); created.append(job['job_id']); return job
        def cancel_exact(*args, **kwargs):
            current = job_store.get_job(created[-1]); current['status'] = 'cancelled'
            job_store.save_job(current); return {'message': message}
        model.side_effect = cancel_exact
        with patch.object(job_store, 'create_job', capture_create):
            try: advisory.run_advisory_request('Explain without overriding cancellation.', 'fixture')
            except ValueError: pass
            else: raise AssertionError('cancelled Job overwritten')
        assert job_store.get_job(created[-1])['status'] == 'cancelled'
commands = iter(['/advice fixture Explain.', '/exit'])
with patch.object(uqa, 'banner'), patch.object(uqa, 'read_user_input', lambda: next(commands)), \
     patch.object(advisory, 'run_advisory_request', return_value={'job_id': 'fixture',
         'response': validated, 'sources': []}), patch.object(uqa.console, 'print') as printed:
    uqa.main()
    assert any('Точность объяснения и применимость' in str(call.args[0])
               for call in printed.call_args_list if call.args)

with patch.object(uqa, 'ensure_ollama_ready'), \
     patch.object(uqa, 'acquire_llm_gate', return_value=(None, 0)), \
     patch.object(uqa, 'release_llm_gate'), patch.object(uqa.httpx, 'Client') as client:
    transport = client.return_value.__enter__.return_value
    transport.post.return_value.is_error = False
    transport.post.return_value.json.return_value = {'message': {'role': 'assistant', 'content': '{"answer":"fixture"}'}}
    schema = {'type': 'object', 'properties': {'answer': {'type': 'string'}}}
    uqa.ask_ollama([], tools=[], response_schema=schema)
    assert transport.post.call_args.kwargs['json']['format'] == schema
    uqa.ask_ollama([], tools=[])
    assert 'format' not in transport.post.call_args.kwargs['json']
    count = transport.post.call_count
    for tools, invalid_schema in [([{'function': {'name': 'fixture'}}], schema), ([], 'json'), ([], {'large': 'x' * 9000})]:
        try: uqa.ask_ollama([], tools=tools, response_schema=invalid_schema)
        except ValueError: pass
        else: raise AssertionError('invalid or tool-enabled schema accepted')
    assert transport.post.call_count == count
print('advisory contract: PASS (no dispatch authority, no test verdict, exact source recheck, citation binding, tool-free schema, no silent mode change)')
