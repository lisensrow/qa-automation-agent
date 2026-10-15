"""Bounded audit task admission; no network or actual dispatch."""
from datetime import datetime, timezone
from tools.agent_update import pinned_audit_payload, validate_locked_update_scope
from uqa import classify_tool_action, tool_policy_check
from tools.registry import TOOLS
uid = '71724f3b-41b9-449b-9075-1dd6c8e1c2df'
ci = {'id': 'ci', 'name': 'example', 'agent_id': uid}
agent = {'id': uid, 'status': 'online', 'version': '1.3.27'}
tasks = {'total': 0, 'items': []}
audit = {'agent_id': uid, 'last_audit_at': datetime.now(timezone.utc).isoformat(),
         'detail': [{'plugin_name': 'osAudit', 'plugin_version': '1.3.4', 'load_status': True, 'load_error': ''}]}
def compile(task='pluginAudit', a=audit, t=tasks):
    return pinned_audit_payload(ci, agent, t, uid, '1.3.27', task, a)
def rejected(callback):
    try: callback()
    except (ValueError, TypeError): return
    raise AssertionError('must fail closed')
assert compile()['name'] == 'pluginAudit'
assert compile('osAudit')['additional_params'] == {}
for name in ('executeCommand', 'agentControl', 'updateAgent', '', None):
    rejected(lambda: compile(name))
rejected(lambda: compile('osAudit', None))
rejected(lambda: compile('osAudit', {**audit, 'last_audit_at': '2020-01-01T00:00:00Z'}))
rejected(lambda: compile('osAudit', {**audit, 'detail': [{**audit['detail'][0], 'load_error': 'failure'}]}))
rejected(lambda: compile(t={'total': 1, 'items': [{'agent_id': uid, 'name': 'pluginAudit', 'period': None, 'status': 'created'}]}))
scope = {'ci_name': 'example', 'agent_id': uid, 'core_version': '1.3.27', 'task_name': 'pluginAudit'}
validate_locked_update_scope({'stand': 'lab', 'request': ' '.join(scope.values())},
    {'requirement': {'locked': True, 'pinned_audit_task': scope}}, scope, 'pinned_audit_task')
tool = 'browser_create_pinned_agent_audit_semantic'
assert classify_tool_action(tool, scope) == 'write'
assert tool_policy_check(tool, scope, [], force_read_only=True)['executed'] is False
assert any(x['function']['name'] == tool for x in TOOLS)
print('pinned_audit_task: PASS (admission fixture only, no runtime PASS)')
