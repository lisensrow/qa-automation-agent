# Контракт атомарной записи v1

Реализация: product_knowledge_records.py. Вход ограничен 16384 UTF-8 байтами; неизвестные поля/schema versions отклоняются. Это внутренний trusted operator API, не публичный REST API или инструмент LLM.

| Поле | Смысл |
|---|---|
| schema_version | Только integer 1, не boolean |
| event_id | Стабильный ID события/outcome revision, до 128 символов |
| project_id / product_namespace | Разделение проекта и продукта; fixture не утверждает поведение UC |
| concept_id | Устойчивая функция/понятие, не случайное имя test-resource |
| knowledge_kind | contract, observed_fact, limitation, test_experience |
| source_level | declared_spec, runtime_observation, hypothesis, developer_confirmation |
| execution_mode | document_review, live_operator_assisted, live_autonomous, isolated_fixture |
| scope | Явные версия/архитектура/ОС/profile/document_revision; unknown сохраняется, latest/* запрещены |
| claim | predicate, conditions, value и необязательные unit/issue_id |
| statement | Краткий недоверенный текст, до 1024 символов, не semantic key |
| sources | От 1 до 4 точных зарегистрированных document refs или runtime evidence refs |

Conditions — не более 16 атомов field/operator/value/unit. Operators: eq/ne/lt/lte/gt/gte/in. Они соединяются AND; произвольный код/выражения и сложный recipe здесь не допускаются. Порядок условий не влияет на identity; in-list сортируется/дедуплицируется. Единицы сохраняются явно, автоматического пересчёта GiB/bytes нет. Bool не смешивается с integer, NaN/Infinity запрещены.

Canonical claim ID определяется project/namespace/concept/kind/predicate/conditions/unit, variant ID — дополнительно typed value. Текстовая перефразировка не создаёт variant. Scope и source level хранятся отдельно; противоположные values в одной области/уровне получают conflict, без молчаливой замены.

## Internal API

- validate_record(record): ограниченный формат/нормализация, без объявления истины.
- validate_sources(record, policy): trusted registry и фактическая целостность источников.
- initialize_schema(db_path): явная добавочная миграция, без backfill/переклассификации legacy facts.
- ingest_record(record, policy, db_path): транзакционный candidate-only sink; exact replay возвращает duplicate_event, изменённый payload того же event ID отклоняется.
- read_history(project_id, product_namespace, concept_id, db_path, limit): read-only выдача до 50 scoped вариантов; no PASS/no upgrade advice, без automatic verified retrieval.

v192 добавляет в read_history поле execution_modes: ограниченный список режимов событий данного variant/scope/source level. Типизированный исторический adapter отдельно разрешает только два reviewed runtime predicate с повторной проверкой native источника; это не автоматическая публикация всех кандидатов, не verified retrieval и не право выполнить действие. Исходный statement и значения XML в модельный context не экспортируются.

DocumentSource/SourcePolicy задаёт доверенный оператор, а не входной JSON модели. project_id должен совпадать с policy, product_namespace — входить в её явно заданный allowed_namespaces; пустая allowlist запрещает admission. Текущий код не реализует end-user RBAC. Все результаты admission имеют evidence_for_pass=false; кандидат не публикуется в search и не разрешает действий.

Recipe и code_binding/static_implementation спроектированы, но не приняты этим первым validator. Новые типы потребуют отдельного versioned контракта и tests; текущая схема не превращается в произвольный JSON-мешок.

История имеет отдельные os/os_version/agent_architecture/core/plugin/component версии. Зарезервированные issue_classification и declared_fix_version требуют approved developer source; fix_verification требует runtime источника. Это source admission, не semantic promotion или автоматический совет обновиться. [История и баги](product-history-and-bugs.md).
