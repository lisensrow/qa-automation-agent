"""Isolated declaration recall, source integrity, conflict and read-only gates."""
import hashlib
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from product_knowledge_records import DocumentSource, SourcePolicy, initialize_schema, ingest_record
from product_knowledge_context import retrieve_declared_context, reviewed_search_queries

assert reviewed_search_queries('Создай коллекцию; не запускай политики или процедуры.') == ['коллекции создание','наблюдённый маршрут поля коллекции']
assert reviewed_search_queries('Как создать процедуру?') == ['процедуры создание','наблюдённый маршрут формы процедуры']
assert reviewed_search_queries('Открой политику; без процедур.') == ['политики создание','наблюдённый маршрут формы политики']
assert reviewed_search_queries('Не создавай политики или процедуры.') == []
assert reviewed_search_queries('Создай коллекцию. Никаких политик или процедур.') == ['коллекции создание','наблюдённый маршрут поля коллекции']
assert reviewed_search_queries(None) == []
ram_query='RAM агрегаты единицы отсутствие данных'
cpu_query='CPU не спутать CI ядра текущую нагрузку'
logic_query='логика условий состава коллекций'
assert reviewed_search_queries('Коллекция RAM не меньше 2 GiB') == [logic_query,ram_query,'наблюдённый маршрут поля коллекции']
assert reviewed_search_queries('Создай коллекцию по оперативной памяти') == [logic_query,ram_query,'наблюдённый маршрут поля коллекции']
assert reviewed_search_queries('Collection CPU cores') == [logic_query,cpu_query,'наблюдённый маршрут поля коллекции']
assert reviewed_search_queries('Коллекция RAM и CPU') == [logic_query,ram_query,cpu_query]
assert reviewed_search_queries('Коллекция. Не меняй RAM и CPU.') == ['коллекции создание','наблюдённый маршрут поля коллекции']
assert reviewed_search_queries('Не создавай коллекцию RAM') == []
assert reviewed_search_queries('Проверь CPU без коллекций') == []
read_query='просмотр существующей коллекции привязка таблицы'
assert reviewed_search_queries('Открой существующую коллекцию Windows') == [read_query]
assert reviewed_search_queries('Read existing collection. Do not create or edit.') == [read_query]
assert reviewed_search_queries('Прочитай коллекцию RAM и CPU') == [read_query,ram_query,cpu_query]
assert reviewed_search_queries('Не открывай существующую коллекцию') == []
assert reviewed_search_queries('Открой новую коллекцию') == ['коллекции создание','наблюдённый маршрут поля коллекции']
assert reviewed_search_queries('Создай коллекцию. Существующие коллекции не изменяй.') == ['коллекции создание','наблюдённый маршрут поля коллекции']
layout_query='колонки коллекции каталог полей'
assert reviewed_search_queries('Почему в коллекции Windows отсутствует колонка ОС?') == [layout_query]
assert reviewed_search_queries('Inspect collection table fields and RAM') == [read_query,layout_query,ram_query]
assert reviewed_search_queries('Коллекция: столбцы RAM и CPU') == [layout_query,ram_query,cpu_query]
assert reviewed_search_queries('Create a collection with CPU columns') == ['коллекции создание',layout_query,cpu_query]
assert reviewed_search_queries('Открой новую коллекцию и поля таблицы') == ['коллекции создание',layout_query]
assert reviewed_search_queries('Создай коллекцию по os_name') == ['коллекции создание','наблюдённый маршрут поля коллекции']
assert reviewed_search_queries('Открой коллекцию. Не изменяй колонки RAM и CPU.') == [read_query]
assert reviewed_search_queries('Не меняй колонки коллекции') == []
assert reviewed_search_queries('Inspect CPU table columns without collections') == []
assert reviewed_search_queries('Read collection layout. Do not create policies or procedures.') == [read_query,layout_query]
assert reviewed_search_queries('Why is the OS column missing from the collection?') == [layout_query]
assert reviewed_search_queries('Колонка ОС коллекции. Посмотри накопленный опыт; ничего не сохраняй.') == [layout_query]
policy_facet='политика открытие редактора отдельный submit активность по умолчанию'
plugin_base='плагины агента инвентаризация обновление полный результат задачи'
plugin_load='версия и загрузка плагина разные проверки'
plugin_result='создание задания не является проверкой его результата'
assert reviewed_search_queries('Проверь версию и загрузку плагина, результат задачи') == [plugin_base, plugin_load, plugin_result]
assert reviewed_search_queries('Inspect plugin version, load status and fetch result') == [plugin_base, plugin_load, plugin_result]
assert reviewed_search_queries('Read plugin inventory') == [plugin_base]
assert reviewed_search_queries('Не обновляй плагины') == []
assert reviewed_search_queries('Open collection layout without plugins') == [read_query, layout_query]
assert reviewed_search_queries('Плагин для коллекции')[:1] == [plugin_base]
assert reviewed_search_queries('Политика для плагина')[:1] == ['политики создание']
policy_queries=['политики создание',policy_facet,'наблюдённый маршрут формы политики']
assert reviewed_search_queries('Политика включена по умолчанию?') == policy_queries
assert reviewed_search_queries('Explain policy default activation and launcher versus submit') == policy_queries
assert reviewed_search_queries('Создай неактивную политику') == policy_queries
assert reviewed_search_queries('Объясни отличие открытия редактора политики от сохранения') == policy_queries
assert reviewed_search_queries('Открой политику; не меняй активность.') == ['политики создание','наблюдённый маршрут формы политики']
assert reviewed_search_queries('Не включай политики по умолчанию') == []
assert reviewed_search_queries('Submit collection layout without policies') == [layout_query]
assert reviewed_search_queries('Explain inactive policy') == policy_queries
assert reviewed_search_queries('Политика по умолчанию только для тестовой коллекции') == policy_queries
assert reviewed_search_queries('Сначала процедура, затем политика') == ['процедуры создание','наблюдённый маршрут формы процедуры','политики создание']
assert reviewed_search_queries('Сначала коллекция, затем политика по умолчанию') == ['коллекции создание','наблюдённый маршрут поля коллекции','политики создание']

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
