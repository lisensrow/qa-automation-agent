"""Pure contract/guard smoke: never contacts UC or creates a task."""
from copy import deepcopy
from tools.agent_update import pinned_update_payload, validate_locked_update_scope

uid = '71724f3b-41b9-449b-9075-1dd6c8e1c2df'
ci = {'id': 'ci', 'name': 'example', 'agent_id': uid}
agent = {'id': uid, 'status': 'online', 'version': '1.2.25'}
tasks = {'total': 0, 'offset': 0, 'items': []}
def rejected(callback):
    try:
        callback()
    except (ValueError, TypeError):
        return
    raise AssertionError('must fail closed')

assert pinned_update_payload(ci, agent, tasks, uid, '1.3.27') == {
    'name': 'updateAgent', 'period': None, 'ttl': None, 'run_as_user': '',
    'additional_params': {'version': '1.3.27'}}
for version in (None, '', 'latest', '1.3', '1.3.27/evil', '1.3.27\n', '1.2.25', '1.1.0'):
    rejected(lambda: pinned_update_payload(ci, agent, tasks, uid, version))
for changed in ({'status': 'offline'}, {'id': 'other'}, {'version': None}):
    rejected(lambda: pinned_update_payload(ci, {**agent, **changed}, tasks, uid, '1.3.27'))
for changed in ({'total': 1}, {'offset': 1}, {'items': None}, {'total': True}):
    rejected(lambda: pinned_update_payload(ci, agent, {**tasks, **changed}, uid, '1.3.27'))
rejected(lambda: pinned_update_payload({**ci, 'agent_id': 'other'}, agent, tasks, uid, '1.3.27'))
for status, params in [('created', {'version': '1.0.0'}), ('success', {'version': '1.3.27'}),
                       ('error', {'version': '1.3.27'}), ('timeout', None)]:
    existing = {'total': 1, 'items': [{'agent_id': uid, 'name': 'updateAgent',
                 'status': status, 'additional_params': params}]}
    rejected(lambda: pinned_update_payload(ci, agent, existing, uid, '1.3.27'))
scope = {'ci_name': 'example', 'agent_id': uid, 'version': '1.3.27'}
job = {'stand': 'lab', 'request': ' '.join(scope.values())}
case = {'requirement': {'locked': True, 'pinned_agent_update': scope}}
validate_locked_update_scope(job, case, scope)
rejected(lambda: validate_locked_update_scope({**job, 'stand': 'prod'}, case, scope))
rejected(lambda: validate_locked_update_scope({**job, 'request': 'update'}, case, scope))
rejected(lambda: validate_locked_update_scope(job, {}, scope))
rejected(lambda: validate_locked_update_scope(job, case, {**scope, 'version': 'latest'}))
rejected(lambda: validate_locked_update_scope(job, case, {**scope, 'extra': True}))
from uqa import classify_tool_action, execute_tool_with_policy, tool_policy_check
assert classify_tool_action('browser_create_pinned_agent_update_semantic', scope) == 'write'
assert execute_tool_with_policy('browser_create_pinned_agent_update_semantic', scope, [],
    action_policy='legacy')['executed'] is False
assert tool_policy_check('browser_create_pinned_agent_update_semantic', scope, [],
    force_read_only=True)['executed'] is False
from tools.registry import TOOLS
assert any(t['function']['name'] == 'browser_create_pinned_agent_update_semantic' for t in TOOLS)
from tools.browser import BrowserSession
from types import SimpleNamespace
class Response:
    def __init__(self, status, body):
        self.status, self.body = status, body
    def json(self):
        return self.body
class Requests:
    def __init__(self):
        self.sent = []
        self.receipt = Response(201, {'id': 'task', 'agent_id': uid, 'name': 'updateAgent',
                                     'additional_params': {'version': '1.3.27'}})
    def get(self, url, **kwargs):
        return Response(200, tasks if url.endswith('/tasks') else agent)
    def post(self, url, **kwargs):
        self.sent.append((url, kwargs))
        return self.receipt
requests = Requests()
session = object.__new__(BrowserSession)
session._ensure_started = lambda: None
session.context = SimpleNamespace(request=requests)
session._observed_agent_task_context = lambda name: (ci, tasks,
    'https://uc.lab.local/api/v1/u-auth/u-sys/api/v1/agents/' + uid + '/tasks', None)
session._same_https_origin_url = lambda url, path: 'https://uc.lab.local' + path
receipt = session.create_pinned_agent_update_semantic('example', uid, '1.3.27')
assert receipt['executed'] is True and receipt['business_pass'] is False
assert len(requests.sent) == 1
assert requests.sent[0][1]['data']['additional_params'] == {'version': '1.3.27'}
assert session.create_pinned_agent_update_semantic('example', uid, 'latest')['executed'] is False
assert len(requests.sent) == 1
requests.receipt = Response(200, {})
assert session.create_pinned_agent_update_semantic('example', uid, '1.3.27')['dispatch_may_have_occurred'] is True
assert len(requests.sent) == 2  # separate unit invocation, not a retry in the adapter
print('pinned_agent_update: PASS (pure compiler, locked scope, fail closed; no runtime acceptance)')
