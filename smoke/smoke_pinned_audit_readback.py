"""Fake transport only; proves identity/freshness and immutable subset comparison."""
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from tools.browser import BrowserSession
from tools.agent_update import compare_audit_readback
from uqa import classify_tool_action
now = datetime.now(timezone.utc)
scope = {'ci_name': 'example', 'agent_id': 'agent', 'task_id': 'task'}
os_data = {'architecture': '64', 'current_build_os': '1', 'family': 'windows', 'name': 'windows', 'version': 'edition'}
expected = {'host_name': 'example', 'machine_uid': 'ci', 'os': os_data}
body = {'id': 'task', 'agent_id': 'agent', 'name': 'osAudit', 'status': 'success',
        'created_at': now.isoformat(),
        'result': {'machine_uid': 'ci', 'processed_at': now.isoformat(),
                   'data': {'host_name': 'example', 'os': os_data}}}
class Response:
    status = 200
    def json(self): return body
s = object.__new__(BrowserSession)
s._ensure_started = lambda: None
s.session_id = 'session'
s.context = SimpleNamespace(request=SimpleNamespace(get=lambda *a, **kw: Response()))
s._pinned_audit_tasks = {'task': {'ci_name': 'example', 'agent_id': 'agent', 'ci_id': 'ci',
    'session_id': 'session', 'task_name': 'osAudit', 'sent_at': (now-timedelta(seconds=1)).isoformat(),
    'received_at':now.isoformat(), 'server_created_at':now.isoformat()}}
s._observed_agent_task_context = lambda name: ({'id': 'ci', 'agent_id': 'agent'}, {},
    'https://uc.lab.local/api/agents/agent/tasks', None)
s._same_https_origin_url = lambda url, path: 'https://uc.lab.local' + path
actual = s.inspect_pinned_agent_audit_semantic(**scope)
assert actual['native_result_verified'] is True
assert compare_audit_readback(expected, actual)['status'] == 'PASS'
changed = {**actual, 'os_subset': {**os_data, 'name': 'Windows 10 Pro'}}
result = compare_audit_readback(expected, changed)
assert result['status'] == 'BLOCKED' and result['differences']['name']['expected'] == 'windows'
assert result['developer_confirmed_bug'] is False
assert compare_audit_readback(None, actual)['status'] == 'BLOCKED'
assert compare_audit_readback(expected, {**actual, 'native_result_verified': False})['status'] == 'BLOCKED'
assert s.inspect_pinned_agent_audit_semantic(**{**scope, 'task_id': 'old'})['native_result_verified'] is False
body['result']['machine_uid'] = 'other'
assert s.inspect_pinned_agent_audit_semantic(**scope)['native_result_verified'] is False
from tools.agent_update import audit_result_is_fresh
assert audit_result_is_fresh((now-timedelta(seconds=1)).isoformat(),now.isoformat(),now.isoformat(),now.isoformat(),
    (now-timedelta(seconds=2)).isoformat(),now=now) is True
assert audit_result_is_fresh((now-timedelta(seconds=1)).isoformat(),now.isoformat(),now.isoformat(),
    (now-timedelta(seconds=3)).isoformat(),now.isoformat(),now=now) is False
body['result']['machine_uid'] = 'ci'
body['result']['processed_at'] = (now-timedelta(days=1)).isoformat()
assert s.inspect_pinned_agent_audit_semantic(**scope)['native_result_verified'] is False
assert classify_tool_action('browser_inspect_pinned_agent_audit_semantic', scope) == 'observe'
ready_agent={'id':'agent','version':'1.3.27','status':'online'}
ready_audit={'agent_id':'agent','last_audit_at':datetime.now(timezone.utc).isoformat(),
    'detail':[{'plugin_name':'osAudit','plugin_version':'1.3.4','load_status':True,'load_error':''}]}
s._observed_agent_task_context=lambda name: ({'id':'ci','name':'example','agent_id':'agent'}, {},
    'https://uc.lab.local/api/agents/agent/tasks',None)
def ready_get(url, **kwargs):
    return SimpleNamespace(status=200,json=lambda: ready_audit if url.endswith('/plugin') else ready_agent)
s.context.request.get=ready_get
assert s.inspect_pinned_agent_readiness_semantic('example','agent')['ready'] is True
ready_agent['version']='1.2.25'
assert s.inspect_pinned_agent_readiness_semantic('example','agent')['ready'] is False
ready_agent['version']='1.3.27';ready_audit['detail'][0]['load_error']='failed'
assert s.inspect_pinned_agent_readiness_semantic('example','agent')['ready'] is False
assert classify_tool_action('browser_inspect_pinned_agent_readiness_semantic', {})=='observe'
print('pinned_audit_readback: PASS (fixture only, no autonomous runtime acceptance)')
