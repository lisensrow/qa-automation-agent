"""Main input routing fixture only: no SSH/browser/model/UC execution."""
from contextlib import ExitStack
from unittest.mock import patch
import uqa
from schema_request_adapter import request_requirement

text=('На стенде lab прочитай из зарегистрированного снимка API параметры командной задачи '
      'и формат полного результата. Ничего не запускай.')
assert not uqa.request_is_regression(text)  # Precisely the old top-level gap.
for fail in [False,True]:
    inputs=iter([text,'/exit'])
    source_job={'request':text,'test_cases':[{'requirement':request_requirement(text,'lab'),
        'result':'# Fixture source answer\n\nprogramm; snapshot recency unknown; not business PASS.'}]}
    with ExitStack() as stack:
        stack.enter_context(patch.object(uqa,'banner'))
        stack.enter_context(patch.object(uqa,'read_user_input',lambda:next(inputs)))
        # Exercise real token extraction and canonical alias resolution together.
        stack.enter_context(patch.object(uqa,'resolve_stand',side_effect=lambda name:'uc.fixture.local' if name=='lab' else None))
        stack.enter_context(patch.object(uqa,'ensure_ollama_ready'))
        stack.enter_context(patch.object(uqa,'_recheck_product_blockers_once',side_effect=AssertionError('source-only must not probe stand')))
        stack.enter_context(patch.object(uqa,'request_needs_ssh',side_effect=AssertionError('source-only needs no SSH')))
        stack.enter_context(patch('ssh_worker.detect_stand_identity',side_effect=AssertionError('source-only needs no live identity')))
        stack.enter_context(patch.object(uqa,'run_turn',side_effect=AssertionError('must use the ordinary source-aware runner')))
        stack.enter_context(patch.object(uqa,'get_job',return_value=source_job))
        runner=stack.enter_context(patch.object(uqa,'run_regression_job',side_effect=RuntimeError('fixture failure') if fail else None,
                                              return_value='fixture-source'))
        uqa.main()
        runner.assert_called_once_with(original_request=text,safe_request=text,current_stand='lab',stand_identity=None)
print('PASS main source request route fixture: exact closed intent reaches source-aware runner before SSH/live probes; errors do not fall through; no real acceptance')
