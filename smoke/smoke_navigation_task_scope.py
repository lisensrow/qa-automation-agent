"""Observed explicit destinations outrank unrelated documentation or prohibitions."""
import uqa

labels = ['CMDB', 'Automation & Analytics']
assert uqa._deterministic_navigation_label(
    'Open CMDB. Do not start tasks or automation.', 'automation tasks documentation', labels) == 'CMDB'
assert uqa._deterministic_navigation_label(
    'Открой CMDB. Не запускай задачи.', 'automation tasks documentation', labels) == 'CMDB'
assert 'tasks' not in uqa._positive_navigation_context('Inspect fields; do not create, edit, delete, or start tasks.')
assert uqa._deterministic_navigation_label('Open CatalogX.', '', ['CatalogX', 'CatalogY']) == 'CatalogX'
assert uqa._deterministic_navigation_label('Open CatalogX and CatalogY.', '', ['CatalogX', 'CatalogY']) is None
assert uqa._deterministic_navigation_label('Do not open CatalogX.', '', ['CatalogX']) is None
execution = uqa._positive_navigation_context('Open CMDB with action-policy confirmation. The user explicitly authorized Add.')
assert 'policy' not in execution and 'user' not in execution
assert 'policy' in uqa._positive_navigation_context('Open the Policy settings.')
assert 'user' not in uqa._positive_navigation_context('Open CatalogX.\n[UQA CORE: RESOLVED STAND]\nssh_username: fixture')
messages = [{'role': 'user', 'content': 'Open CatalogX and inspect its Add form.'},
            {'role': 'tool', 'tool_name': 'browser_open_page', 'content': {
                'http_status': 200, 'current_url': 'https://fixture.test/catalogx', 'executed': True}}]
assert uqa._open_page_proves_named_route(messages)
assert uqa._managed_navigation_ready(messages)
from unittest.mock import patch
with patch.object(uqa, 'get_job', return_value={'request': 'Open Add in CatalogX.'}):
    result = uqa.add_managed_navigation_preflight_advisory(
        'browser_open_page', messages[-1]['content'], messages[:1],
        'confirm_mutations', 'fixture-job', 'fixture-case')
    assert result['navigation_preflight_status'] == 'completed'
    assert 'action_policy_status' not in result
    assert result['http_status'] == 200
with patch.object(uqa, 'get_job', return_value={'request': 'Read-only; do not create objects.'}):
    result = uqa.add_managed_navigation_preflight_advisory(
        'browser_open_page', messages[-1]['content'], messages[:1],
        'confirm_mutations', 'fixture-job', 'fixture-case')
    assert 'navigation_preflight_status' not in result
for change in ({'http_status': 404}, {'executed': False}, {'current_url': 'https://fixture.test/'},
               {'current_url': 'https://fixture.test/home'}, {'current_url': 'https://fixture.test/other'}):
    from copy import deepcopy
    variant = deepcopy(messages)
    variant[-1]['content'].update(change)
    assert not uqa._open_page_proves_named_route(variant)
assert uqa._request_is_read_only([{'role': 'user', 'content': 'Read-only; do not create objects.'}])
print('navigation task scope: PASS (positive destination only, observed exact labels, ambiguity preserved)')
