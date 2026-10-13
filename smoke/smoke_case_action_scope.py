"""Task-scoped instructions and denied mutation tracking; no live actions."""
import uqa

spec = {'title': 'Inspect', 'task': 'Inspect visible rows', 'expected': 'One row'}
for request, requirement in (
    ('Read-only. Inspect the table only.', None),
    ('Inspect the table.', {'action_profile': 'read_only'}),
):
    prompt = uqa._build_regression_case_prompt(
        request, request, 'fixture', 'case', 1, 1,
        dict(spec, requirement=requirement),
    )
    assert 'текущая задача read-only' in prompt
    assert 'resource_register' not in prompt
    assert 'До первого WRITE' not in prompt
    assert 'UQA_CHECKS_JSON' in prompt

instructions = uqa._case_action_instructions(
    'Create a test record; do not modify existing objects.',
    {'action_profile': 'write_resource'},
)
assert 'resource_register' in instructions and 'До первого WRITE' in instructions
for status in ('blocked', 'blocked_by_request_policy'):
    assert uqa._policy_denied_mutation({
        'status': 'blocked_by_policy', 'executed': False,
        'action_policy_status': status,
    })
for result in ({}, {'status': 'ok', 'executed': True},
               {'status': 'blocked_by_policy', 'executed': True,
                'action_policy_status': 'blocked'},
               {'status': 'blocked_by_policy', 'executed': False,
                'action_policy_status': 'auto_allowed'}):
    assert not uqa._policy_denied_mutation(result)
print('case action scope: PASS (read-only guidance, write guidance retained, request denials tracked)')

saved_get_job = uqa.get_job
key = ('fixture-readonly', 'case')
previous = uqa._PENDING_NAVIGATION_CANDIDATES.get(key)
try:
    uqa.get_job = lambda _: {'request': 'Read-only. Do not fill fields, toggle selections, submit forms, create, edit, delete.'}
    result = {'status': 'ok', 'executed': True}
    actual = uqa.add_managed_navigation_preflight_advisory(
        'browser_open_page', result,
        [{'role': 'user', 'content': 'Create a test object.'}],
        'confirm_mutations', *key,
    )
    assert actual is result
    assert uqa._PENDING_NAVIGATION_CANDIDATES.get(key) == previous
finally:
    uqa.get_job = saved_get_job
print('readonly navigation advisory: PASS (persistent task overrides create-like internal text)')
route = uqa._prepared_tabs_route_message({'arguments': {'name': 'fixture-row', 'tabs': '["Agent"]'}})
assert 'for this case before the observer' in route['content']
assert 'previous case' in route['content']
