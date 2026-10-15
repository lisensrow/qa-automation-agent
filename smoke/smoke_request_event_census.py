"""Bounded pure accounting plus native isolated request events; no lab writes."""
import json
from types import SimpleNamespace
from unittest.mock import patch
from request_event_census import RequestEventCensus

def request(method='GET', kind='fetch'):
    return SimpleNamespace(method=method, resource_type=kind)

c = RequestEventCensus()
old = request()
c.started(old)
c.begin('fixture-action')
post = request('POST')
c.started(post)
c.completed(old)
c.completed(post, failed=True)
r = c.finish('fixture-action')
assert r['pending_at_begin'] == 1 and r['pending_at_finish'] == 0
assert r['request_started_count'] == 1 and r['method_counts'] == {'POST': 1}
assert r['completion_event_count'] == 2 and r['failed_event_count'] == 1
assert not r['tracking_incomplete'] and not r['capture_active']
for field in ('future_traffic_covered', 'websocket_frames_covered', 'service_worker_coverage_verified',
              'causal_attribution_verified', 'business_effect_verified', 'resend_authorized'):
    assert r[field] is False
assert c.finish('absent') is None
c.begin('after-missing'); assert c.finish('after-missing')['tracking_incomplete']

for mode in ('duplicate', 'unknown_completion', 'unknown_method', 'unknown_type', 'overflow', 'nested'):
    c = RequestEventCensus(); c.begin('a')
    if mode == 'duplicate':
        obj = request(); c.started(obj); c.started(obj)
    elif mode == 'unknown_completion':
        c.completed(request())
    elif mode == 'unknown_method':
        c.started(request('PRIVATE-DO-NOT-EXPORT'))
    elif mode == 'unknown_type':
        c.started(request(kind='PRIVATE-DO-NOT-EXPORT'))
    elif mode == 'overflow':
        for _ in range(c.MAX_PENDING + 20): c.started(request())
    else:
        c.begin('a')
    result = c.finish('a')
    assert result['tracking_incomplete'] and len(c._pending) <= c.MAX_PENDING
    assert 'PRIVATE-DO-NOT-EXPORT' not in json.dumps(result)

# No access to URLs, headers or request bodies, even in private callbacks.
class PrivateRequest:
    method = 'GET'
    resource_type = 'document'
    def __getattr__(self, name):
        raise AssertionError('unexpected request data access: ' + name)
c = RequestEventCensus(); c.begin('private'); obj = PrivateRequest()
c.started(obj); c.completed(obj)
assert c.finish('private')['method_counts'] == {'GET': 1}

from playwright.sync_api import sync_playwright
from tools.browser import BrowserSession
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    session = BrowserSession(); session.browser = browser
    with patch.object(session, '_context_kwargs', return_value={}):
        session._create_context()
    held = []
    def route_fixture(route):
        if route.request.url.endswith('/abort'):
            route.abort('failed')
        elif route.request.url.endswith('/hold'):
            held.append(route)
        else:
            route.fulfill(status=200, content_type='text/html', body='<html>fixture</html>')
    session.context.route('https://census.test/**', route_fixture)
    page = session.page
    page.goto('https://census.test/')
    page.wait_for_timeout(50)
    session._begin_action_execution()
    page.evaluate("() => { void fetch('/abort', {method:'POST', body:'PRIVATE-DO-NOT-EXPORT'}).catch(()=>{}); }")
    page.wait_for_timeout(100)
    result = session._finish_action_execution({})
    census = result['request_event_census']
    assert census['capture_active'] and not census['tracking_incomplete']
    assert census['method_counts'] == {'POST': 1} and census['failed_event_count'] == 1
    assert census['pending_at_finish'] == 0 and not session.network_events

    session._reset_diagnostics(); session._begin_action_execution()
    page.evaluate("async () => { await Promise.all([fetch('/write', {method:'POST'}), ...Array.from({length:40},(_,i)=>fetch('/read'+i))]); }")
    page.wait_for_timeout(100)
    census = session._finish_action_execution({})['request_event_census']
    assert census['request_started_count'] == 41 and census['method_counts'] == {'POST': 1, 'GET': 40}
    assert len(session._filtered_network_events('fixture')) == 30
    assert census['pending_at_finish'] == 0 and not census['tracking_incomplete']

    session._begin_action_execution()
    page.evaluate("() => { void fetch('/hold', {method:'POST'}).catch(()=>{}); }")
    page.wait_for_timeout(100)
    census = session._finish_action_execution({})['request_event_census']
    assert census['pending_at_finish'] == 1 and census['method_counts'] == {'POST': 1}
    assert len(held) == 1
    held[0].abort('failed'); page.wait_for_timeout(50)
    assert census['pending_at_finish'] == 1  # Receipt remains a snapshot.
    assert 'PRIVATE-DO-NOT-EXPORT' not in json.dumps(census)
    session.close()
print('request event census: PASS (native failed/pending POST, >30 responses, bounded loss, no secrets, no replay authority)')
