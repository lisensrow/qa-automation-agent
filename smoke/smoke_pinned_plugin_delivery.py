"""No UC access: admitted plugin payload, scope and fake transport only."""
from tools.agent_update import pinned_plugin_payload, validate_locked_update_scope
from tools.browser import BrowserSession
from types import SimpleNamespace
from uqa import classify_tool_action, tool_policy_check
from tools.registry import TOOLS
uid = '71724f3b-41b9-449b-9075-1dd6c8e1c2df'
ci = {'id': 'ci', 'name': 'example', 'agent_id': uid}
agent = {'id': uid, 'status': 'online', 'version': '1.3.27'}
tasks = {'total': 0, 'items': [], 'offset': 0}
expected = {'plugins_to_update': [{'plugin_name': 'osAudit', 'plugin_version': '1.3.4'}],
            'plugins_to_delete': [], 'check_endpoint_os_version': True}
def rejected(callback):
    try:
        callback()
    except (ValueError, TypeError):
        return
    raise AssertionError('must fail closed')
def compile(a=agent, t=tasks, name='osAudit', version='1.3.4'):
    return pinned_plugin_payload(ci, a, t, uid, '1.3.27', name, version)
assert compile() == expected
for name, version in [('executeCommand', '1.4.0'), ('osAudit', 'latest'), ('osAudit', '1.2.25')]:
    rejected(lambda: compile(name=name, version=version))
rejected(lambda: compile(a={**agent, 'version': '1.2.25'}))
rejected(lambda: compile(a={**agent, 'status': 'offline'}))
rejected(lambda: compile(t={'total': 1, 'items': []}))
for status, params in [('created', {}), ('success', expected), ('error', expected), ('timeout', None)]:
    rejected(lambda: compile(t={'total': 1, 'items': [{'name': 'managePlugin', 'agent_id': uid,
                                                     'status': status, 'additional_params': params}]}))
scope = {'ci_name': 'example', 'agent_id': uid, 'core_version': '1.3.27', 'plugin_name': 'osAudit', 'version': '1.3.4'}
job = {'stand': 'lab', 'request': ' '.join(scope.values())}
case = {'requirement': {'locked': True, 'pinned_plugin_delivery': scope}}
validate_locked_update_scope(job, case, scope, 'pinned_plugin_delivery')
rejected(lambda: validate_locked_update_scope(job, case, {**scope, 'delete': True}, 'pinned_plugin_delivery'))
tool = 'browser_deliver_pinned_agent_plugin_semantic'
assert classify_tool_action(tool, scope) == 'write'
assert tool_policy_check(tool, scope, [], force_read_only=True)['executed'] is False
assert any(t['function']['name'] == tool for t in TOOLS)
class Response:
    def __init__(self, status, body): self.status, self.body = status, body
    def json(self): return self.body
class Requests:
    def __init__(self):
        self.sent = []
        self.receipt = Response(202, {'id': 'task', 'agent_id': uid, 'name': 'managePlugin', 'additional_params': expected})
    def get(self, url, **kwargs):
        body = tasks if url.endswith('/tasks') else ({'agent_id': uid, 'detail': []} if url.endswith('/plugin') else agent)
        return Response(200, body)
    def post(self, url, **kwargs):
        self.sent.append((url, kwargs))
        return self.receipt
requests = Requests()
s = object.__new__(BrowserSession)
s._ensure_started = lambda: None
s.context = SimpleNamespace(request=requests)
s._observed_agent_task_context = lambda name: (ci, tasks,
    'https://uc.lab.local/api/v1/u-auth/u-sys/api/v1/agents/' + uid + '/tasks', None)
s._same_https_origin_url = lambda url, path: 'https://uc.lab.local' + path
receipt = s.deliver_pinned_agent_plugin_semantic(**scope)
assert receipt['executed'] is True and receipt['business_pass'] is False
assert len(requests.sent) == 1 and requests.sent[0][0].endswith('/plugin/update')
assert requests.sent[0][1]['data'] == expected
assert s.deliver_pinned_agent_plugin_semantic(**{**scope, 'version': 'latest'})['executed'] is False
assert len(requests.sent) == 1
requests.receipt = Response(200, {})
assert s.deliver_pinned_agent_plugin_semantic(**scope)['dispatch_may_have_occurred'] is True
assert len(requests.sent) == 2
print('pinned_plugin_delivery: PASS (fixture only; no installation or runtime acceptance)')
