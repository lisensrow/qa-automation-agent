"""First-stage knowledge admission; isolated files/DB only, no stand mutation."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
sys.path.insert(0, os.getenv('UQA_SMOKE_ROOT', '/opt/uqa'))
import product_knowledge_records as k

def denied(fn):
    try:
        fn()
    except (ValueError, OSError, KeyError, TypeError, sqlite3.Error):
        return
    raise AssertionError('invalid input accepted')

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    docs = root / 'docs'; docs.mkdir()
    jobs = root / 'jobs'; jobs.mkdir()
    manual = docs / 'official.md'
    manual.write_text('# Fixture official source\nManual refresh uses manual launch type.\n', encoding='utf-8')
    digest = hashlib.sha256(manual.read_bytes()).hexdigest()
    spec = k.DocumentSource('fixture.manual', 'official.md', digest, 'official_document', 'Fixture publisher', 'r1')
    policy = k.SourcePolicy('fixture-project', docs, (spec,), jobs, ('fixture-product',))
    db = root / 'memory.db'
    with sqlite3.connect(db) as con:
        con.execute('CREATE TABLE facts (fact_key TEXT PRIMARY KEY, status TEXT)')
        con.execute("INSERT INTO facts VALUES('legacy-kept','verified')")
        con.execute('CREATE TABLE confirmations (id INTEGER PRIMARY KEY, body TEXT)')
        con.execute("INSERT INTO confirmations VALUES(1,'legacy proof')")
    k.initialize_schema(db); k.initialize_schema(db)
    base = {'schema_version': 1, 'event_id': 'evt-1', 'project_id': 'fixture-project',
            'product_namespace': 'fixture-product', 'concept_id': 'collections.refresh',
            'knowledge_kind': 'contract', 'source_level': 'declared_spec', 'execution_mode': 'document_review',
            'scope': {'document_revision': 'r1'},
            'claim': {'predicate': 'required_launch_type', 'conditions': [], 'value': 'manual'},
            'statement': 'Manual refresh requires manual mode.',
            'sources': [{'kind': 'document', 'source_id': spec.source_id, 'sha256': digest}]}
    first = k.ingest_record(base, policy, db)
    assert first['status'] == 'candidate' and not first['semantic_claim_verified']
    assert k.ingest_record(base, policy, db)['duplicate_event']
    changed = copy.deepcopy(base); changed['statement'] = 'Different event payload.'
    denied(lambda: k.ingest_record(changed, policy, db))
    # Same semantics, different wording/events: one variant, one independent source.
    for i in range(10000):
        r = copy.deepcopy(base); r['event_id'] = f'repeat-{i}'; r['statement'] = 'Same normalized claim, another phrasing.'
        result = k.ingest_record(r, policy, db)
        assert result['variant_id'] == first['variant_id'] and result['confirmation_group_count'] == 1
    other = copy.deepcopy(base); other['event_id'] = 'contradiction'; other['claim']['value'] = 'auto'
    assert k.ingest_record(other, policy, db)['status'] == 'conflict'
    # Different release/source scope is not a same-scope conflict or version transplant.
    other = copy.deepcopy(base); other['event_id'] = 'version-2'; other['scope']['server_version'] = 'explicit-version-2'
    denied(lambda: k.ingest_record(other, policy, db))
    scoped_spec = k.DocumentSource(spec.source_id, spec.relative_path, digest, spec.source_type, spec.publisher, spec.revision,
                                   (('server_version','explicit-version-2'),))
    assert k.ingest_record(other, k.SourcePolicy(policy.project_id,docs,(scoped_spec,),jobs,policy.allowed_namespaces), db)['status'] == 'candidate'
    conditions = [{'field': 'archived', 'operator': 'eq', 'value': False},
                  {'field': 'ci_class', 'operator': 'in', 'value': ['endpoint', 'vm', 'endpoint']}]
    a = copy.deepcopy(base); a['event_id'] = 'conditions-a'; a['claim']['conditions'] = conditions
    b = copy.deepcopy(a); b['event_id'] = 'conditions-b'; b['claim']['conditions'] = list(reversed(conditions)); b['claim']['conditions'][0]['value'] = ['vm','endpoint']
    assert k.ingest_record(a, policy, db)['variant_id'] == k.ingest_record(b, policy, db)['variant_id']
    # OS/release history and developer attribution are separate, not overwritten.
    dev_path = docs / 'developer.md'; dev_path.write_text('Fixture developer confirms issue and declares a fix.', encoding='utf-8')
    dev_hash = hashlib.sha256(dev_path.read_bytes()).hexdigest()
    dev = k.DocumentSource('fixture.developer', 'developer.md', dev_hash, 'developer_confirmation', 'Fixture developer', 'approval-r1',
                           (('os','ubuntu'),('os_version','22.04'),('agent_version','1.3.27')), 'developer')
    dev_policy = k.SourcePolicy(policy.project_id,docs,(dev,),jobs,policy.allowed_namespaces)
    issue = copy.deepcopy(base); issue.update(event_id='issue-confirmation',knowledge_kind='limitation',source_level='developer_confirmation',
                                            scope={'document_revision':'approval-r1','os':'ubuntu','os_version':'22.04','agent_version':'1.3.27'})
    issue['claim'] = {'predicate':'issue_classification','conditions':[],'value':'confirmed_bug','issue_id':'BUG-fixture'}
    issue['sources'] = [{'kind':'document','source_id':dev.source_id,'sha256':dev_hash}]
    assert k.ingest_record(issue,dev_policy,db)['status'] == 'candidate'
    no_role = k.DocumentSource(dev.source_id,dev.relative_path,dev.sha256,dev.source_type,dev.publisher,dev.revision,dev.applicability)
    denied(lambda:k.ingest_record(issue,k.SourcePolicy(policy.project_id,docs,(no_role,),jobs,policy.allowed_namespaces),db))
    unofficial = copy.deepcopy(base); unofficial['claim'] = issue['claim']; unofficial['knowledge_kind'] = 'limitation'
    denied(lambda:k.ingest_record(unofficial,policy,db))
    fixed = copy.deepcopy(issue); fixed['event_id'] = 'declared-fix'; fixed['claim']['predicate'] = 'declared_fix_version'; fixed['claim']['value'] = '1.3.28'
    assert k.ingest_record(fixed,dev_policy,db)['status'] == 'candidate'
    history = k.read_history(policy.project_id,base['product_namespace'],base['concept_id'],db,50)
    assert any(r['scope'].get('os') == 'ubuntu' and r['scope'].get('agent_version') == '1.3.27' for r in history['results'])
    assert history['upgrade_advice_authorized'] is False
    assert all(r['source_refs'] for r in history['results'])
    assert k.read_history('other-project',base['product_namespace'],base['concept_id'],db)['results'] == []
    denied(lambda:k.read_history(policy.project_id,base['product_namespace'],base['concept_id'],db,True))
    revision = docs / 'official-v2.md'; revision.write_text('Fixture second edition describes another launch mode.',encoding='utf-8')
    r2hash = hashlib.sha256(revision.read_bytes()).hexdigest()
    r2 = k.DocumentSource(spec.source_id,'official-v2.md',r2hash,spec.source_type,spec.publisher,'r2')
    new_doc = copy.deepcopy(base); new_doc['event_id']='official-revision-2'; new_doc['scope']={'document_revision':'r2'}
    new_doc['claim']['value']='auto'; new_doc['sources'][0]['sha256']=r2hash
    assert k.ingest_record(new_doc,k.SourcePolicy(policy.project_id,docs,(r2,),jobs,policy.allowed_namespaces),db)['status']=='candidate'
    historical = k.read_history(policy.project_id,base['product_namespace'],base['concept_id'],db,50)
    assert {'r1','r2'} <= {r['scope'].get('document_revision') for r in historical['results']}
    for change in [dict(schema_version=True), dict(status='verified'), dict(statement='password=fixture-secret'),
                   dict(execution_mode='isolated_fixture'), dict(scope={'server_version':'latest'}), dict(knowledge_kind={})]:
        invalid = copy.deepcopy(base); invalid.update(change)
        denied(lambda: k.ingest_record(invalid, policy, db))
    bad_source = copy.deepcopy(base); bad_source['sources'][0]['sha256'] = '0' * 64
    denied(lambda: k.ingest_record(bad_source, policy, db))
    denied(lambda: k.ingest_record(base, k.SourcePolicy('another-project', docs, (spec,), jobs,policy.allowed_namespaces), db))
    wrong_product = copy.deepcopy(base); wrong_product['product_namespace']='other-product'
    denied(lambda:k.ingest_record(wrong_product,policy,db))
    curated = k.DocumentSource(spec.source_id, spec.relative_path, digest, 'curated_note', 'Fixture', 'r1')
    denied(lambda: k.ingest_record(base, k.SourcePolicy(policy.project_id, docs, (curated,), jobs,policy.allowed_namespaces), db))
    manual.write_text('modified source', encoding='utf-8')
    denied(lambda: k.ingest_record(base, policy, db))
    manual.write_text('# Fixture official source\nManual refresh uses manual launch type.\n', encoding='utf-8')
    outside = root / 'outside.md'; outside.write_text('outside', encoding='utf-8')
    (docs / 'escape.md').symlink_to(outside)
    escaped = k.DocumentSource(spec.source_id, 'escape.md', digest, 'official_document', 'Fixture', 'r1')
    denied(lambda: k.ingest_record(base, k.SourcePolicy(policy.project_id, docs, (escaped,), jobs,policy.allowed_namespaces), db))
    # Native runtime source: exact case/evidence/observations and known identity.
    jid = '20261014-000000-deadbeef'
    envelope = {'tool':'browser_get_network_detail','arguments':{'request_id':'n1'},
                'result':{'method':'GET','status':200,'session_id':'s1','request_id':'n1','response_body':'{"items":[]}','response_body_truncated':False}}
    job = {'job_id':jid, 'stand_identity':{'status':'ok','server_version':'1.0'}, 'test_cases':[
        {'case_id':'tc-one','observations':[{'observation_id':'obs-one'}],
         'evidence':[{'evidence_id':'ev-one','usable_for_verdict':True,'observation_ids':['obs-one'],'value':json.dumps(envelope)}]}]}
    path = jobs / (jid + '.json'); path.write_text(json.dumps(job), encoding='utf-8')
    runtime = copy.deepcopy(base); runtime.update(event_id='runtime-one', knowledge_kind='observed_fact', source_level='runtime_observation', execution_mode='live_operator_assisted', scope={'server_version':'1.0'})
    runtime['sources'] = [{'kind':'runtime_evidence','job_id':jid,'case_id':'tc-one','evidence_id':'ev-one'}]
    assert k.ingest_record(runtime, policy, db)['status'] == 'candidate'
    wrong = copy.deepcopy(runtime); wrong['scope']['server_version'] = '2.0'
    denied(lambda: k.ingest_record(wrong, policy, db))
    wrong = copy.deepcopy(runtime); wrong['sources'][0]['case_id'] = 'tc-other'
    denied(lambda: k.ingest_record(wrong, policy, db))
    wrong = copy.deepcopy(runtime); wrong.update(knowledge_kind='contract', source_level='declared_spec')
    denied(lambda: k.ingest_record(wrong, policy, db))
    envelope['result']['response_body_truncated'] = True
    job['test_cases'][0]['evidence'][0]['value'] = json.dumps(envelope)
    path.write_text(json.dumps(job), encoding='utf-8')
    denied(lambda: k.ingest_record(runtime, policy, db))
    # Transaction rollback after new claim/support writes but before event ack.
    with sqlite3.connect(db) as con:
        before = {t:con.execute('SELECT COUNT(*) FROM ' + t).fetchone()[0] for t in
                  ('knowledge_v1_claims','knowledge_v1_variants','knowledge_v1_sources','knowledge_v1_supports','knowledge_v1_events')}
        con.execute("""CREATE TRIGGER fixture_failure BEFORE INSERT ON knowledge_v1_events
          WHEN NEW.event_id='["fixture-project","rollback"]' BEGIN SELECT RAISE(ABORT,'fixture'); END""")
    rollback = copy.deepcopy(base); rollback['event_id'] = 'rollback'; rollback['concept_id'] = 'rollback-concept'
    denied(lambda: k.ingest_record(rollback, policy, db))
    with sqlite3.connect(db) as con:
        assert all(con.execute('SELECT COUNT(*) FROM ' + t).fetchone()[0] == n for t,n in before.items())
        con.execute('DROP TRIGGER fixture_failure')
    with sqlite3.connect(db) as con:
        assert con.execute('SELECT * FROM facts').fetchall() == [('legacy-kept','verified')]
        assert con.execute('SELECT * FROM confirmations').fetchall() == [(1,'legacy proof')]
        assert con.execute('SELECT COUNT(*) FROM knowledge_v1_supports WHERE variant_id=?',(first['variant_id'],)).fetchone()[0] == 2
        assert con.execute('SELECT COUNT(*) FROM knowledge_v1_variants WHERE claim_id=?',(first['claim_id'],)).fetchone()[0] == 2
        assert con.execute('SELECT status FROM knowledge_v1_scopes WHERE variant_id=? AND scope_json=?',(first['variant_id'], k._json(base['scope']))).fetchone()[0] == 'conflict'
        assert con.execute('PRAGMA foreign_key_check').fetchall() == []
    print('product knowledge records: PASS (isolated; 10000 repeats; source integrity; OS/release/document history; developer gate; dedup; conflicts; rollback; legacy preservation; no promotion/advice)')
