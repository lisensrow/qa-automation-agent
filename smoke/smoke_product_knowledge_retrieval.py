"""Isolated version-scoped retrieval; no product or production DB writes."""
import hashlib
import json
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from product_knowledge_retrieval import retrieve_product_knowledge

identity = {'status': 'ok', 'installation_architecture': 'ansible', 'server_version': '1.0'}
with TemporaryDirectory() as directory:
    path = Path(directory) / 'memory.db'
    with sqlite3.connect(path) as connection:
        connection.executescript('''
            CREATE TABLE facts(fact_key TEXT, fact_type TEXT, data_json TEXT);
            CREATE TABLE fact_scopes(fact_key TEXT, status TEXT, installation_architecture TEXT,
                server_version TEXT, conflict_at TEXT, deprecated_at TEXT, verified_at TEXT, last_seen_at TEXT);
            CREATE TABLE confirmations(fact_key TEXT,job_id TEXT,case_id TEXT,installation_architecture TEXT,
                server_version TEXT,deployment_partial INTEGER,created_at TEXT);
        ''')
        for key, status, version, conflict in (
            ('good', 'verified', '1.0', None), ('candidate', 'candidate', '1.0', None),
            ('other', 'verified', '2.0', None), ('conflicted', 'verified', '1.0', 'now'),
        ):
            data = {'ui_field': 'Name', 'ui_action': 'filter', 'api_method': 'GET',
                    'api_endpoint': '/ci', 'query_parameter': 'token=private-fixture-only',
                    'backend_container': 'private-fixture-only'}
            connection.execute('INSERT INTO facts VALUES(?,?,?)', (key, 'ui_api_binding', json.dumps(data)))
            connection.execute('INSERT INTO fact_scopes VALUES(?,?,?,?,?,?,?,?)',
                               (key, status, 'ansible', version, conflict, None, 'now', 'now'))
            connection.execute('INSERT INTO confirmations VALUES(?,?,?,?,?,?,?)',
                               (key, 'job-fixture', 'case-fixture', 'ansible', version, 0, 'now'))
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    result = retrieve_product_knowledge('Name filter', identity, db_path=path)
    assert result['status'] == 'ok' and result['evidence_for_pass'] is False
    assert [item['fact_key'] for item in result['results']] == ['good']
    assert 'private-fixture-only' not in json.dumps(result)
    assert result['scope_excludes_frontend_version'] is True
    assert retrieve_product_knowledge('unrelated', identity, db_path=path)['results'] == []
    assert retrieve_product_knowledge('Name', dict(identity, server_version='3.0'), db_path=path)['results'] == []
    assert retrieve_product_knowledge('Name', dict(identity, installation_architecture='legacy'), db_path=path)['results'] == []
    for unavailable in ({}, dict(identity, deployment_partial=True), dict(identity, status='unknown')):
        assert retrieve_product_knowledge('Name', unavailable, db_path=path)['status'] == 'unavailable'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    absent = Path(directory) / 'absent.db'
    assert retrieve_product_knowledge('Name', identity, db_path=absent)['status'] == 'unavailable'
    assert not absent.exists()
print('version-scoped memory retrieval: PASS (readonly, no wrong-version or conflicting facts)')

# Verify the actual action-loop bridge; no model, Job, or product writes.
import uqa
import product_knowledge_retrieval as memory
saved = (uqa.ask_ollama, uqa.execute_tool_with_policy, memory.retrieve_product_knowledge)
seen = []

def ask(messages, tools):
    seen.append('inference')
    if len(seen) == 1:
        return {'message': {'tool_calls': [{'function': {
            'name': 'knowledge_search', 'arguments': {'query': 'Name filter'}}}]}}
    reply = next(m for m in reversed(messages) if m.get('tool_name') == 'knowledge_search')
    payload = json.loads(reply['content'])
    assert payload['product_memory']['reason'] == 'usable_version_identity_required'
    assert payload['product_memory']['results'] == []
    assert payload['results'] == []  # Existing documentation response preserved.
    return {'message': {'content': 'Fixture completed without runtime verdict.'}}

try:
    uqa.ask_ollama = ask
    uqa.execute_tool_with_policy = lambda *args, **kwargs: {'status': 'ok', 'results': []}
    uqa.run_turn([], action_policy='confirm_mutations')
    assert len(seen) == 2
finally:
    uqa.ask_ollama, uqa.execute_tool_with_policy, memory.retrieve_product_knowledge = saved
print('memory action-loop bridge: PASS (unknown identity safely unavailable)')
