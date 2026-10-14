"""Isolated declaration recall, source integrity, conflict and read-only gates."""
import hashlib
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from product_knowledge_records import DocumentSource, SourcePolicy, initialize_schema, ingest_record
from product_knowledge_context import retrieve_declared_context, reviewed_search_queries

assert reviewed_search_queries('Создай коллекцию; не запускай политики или процедуры.') == ['коллекции создание']
assert reviewed_search_queries('Как создать процедуру?') == ['процедуры создание']
assert reviewed_search_queries('Создай коллекцию. Никаких политик или процедур.') == ['коллекции создание']
assert reviewed_search_queries(None) == []

with TemporaryDirectory() as temp:
    root = Path(temp)
    source = root / 'manual.md'
    source.write_text('Fixture specification.', encoding='utf-8')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    spec = DocumentSource('fixture.guide', 'manual.md', digest, 'official_document', 'Fixture', 'r1')
    policy = SourcePolicy('fixture', root, (spec,), allowed_namespaces=('fixture',))
    db = root / 'memory.db'
    initialize_schema(db)
    record = {'schema_version': 1, 'event_id': 'fixture-event', 'project_id': 'fixture',
              'product_namespace': 'fixture', 'concept_id': 'fixture.collections',
              'knowledge_kind': 'contract', 'source_level': 'declared_spec',
              'execution_mode': 'document_review', 'scope': {'document_revision': 'r1'},
              'claim': {'predicate': 'mode', 'conditions': [], 'value': 'manual'},
              'statement': 'Arbitrary text never injected into context.',
              'sources': [{'kind': 'document', 'source_id': spec.source_id, 'sha256': digest}]}
    ingest_record(record, policy, db)
    concepts = {'fixture.collections': {'terms': ('коллекц', 'collection'), 'claims': {'mode': 'manual'}}}
    def recall(query='создай коллекцию'):
        return retrieve_declared_context(query, db, policy=policy, concepts=concepts)
    before = hashlib.sha256(db.read_bytes()).hexdigest()
    result = recall()
    assert len(result['results']) == 1
    assert result['evidence_for_pass'] is False and result['upgrade_advice_authorized'] is False
    assert result['current_runtime_applicability_verified'] is False
    assert 'statement' not in result['results'][0]
    assert result['results'][0]['source_refs'][0]['sha256'] == digest
    assert not recall('политика')['results'] and not recall('')['results']
    assert hashlib.sha256(db.read_bytes()).hexdigest() == before
    source.write_text('Changed source.', encoding='utf-8')
    assert not recall()['results']
    source.write_text('Fixture specification.', encoding='utf-8')
    wrong = SourcePolicy('another-project', root, (spec,), allowed_namespaces=('fixture',))
    assert not retrieve_declared_context('collection', db, policy=wrong, concepts=concepts)['results']
    empty = SourcePolicy('fixture', root, (spec,))
    assert not retrieve_declared_context('collection', db, policy=empty, concepts=concepts)['results']
    record['event_id'] = 'conflict-event'; record['claim']['value'] = 'auto'
    ingest_record(record, policy, db)
    assert not recall()['results']
    assert not retrieve_declared_context('collection', root / 'missing.db', policy=policy, concepts=concepts)['results']
    assert not (root / 'missing.db').exists()
    with sqlite3.connect(db) as con:
        assert con.execute('SELECT COUNT(*) FROM knowledge_v1_events').fetchone()[0] == 2
print('declaration recall: PASS (source hash, project isolation, no arbitrary prose, conflict, read-only)')
