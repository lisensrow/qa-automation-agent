# Компоненты UQA и ответственность

UQA сейчас — Python-система с локальным persistent state и браузерным runtime, не распределённая платформа со всеми целевыми сервисами.

| Компонент | Код/данные | Ответственность |
|---|---|---|
| CLI/Core | uqa.py | Пользовательский запрос, orchestration, policy, вызовы инструментов и подготовленные сценарии |
| Планирование | planner/normalizers внутри Core | Job/cases/checks; поддержанные locked workflow не превращать в независимые создания |
| Инструменты | tools/registry.py и tools/* | Каталог, progressive exposure и dispatch; скрытие схем не выдаёт разрешения действия |
| Browser runtime | tools/browser.py | Семантические UI действия, снимки состояния, native network receipts |
| Контракты проверок | frontend_check_contracts.py, form_lifecycle_contracts.py и поддержанные evaluators | Вычисление результата по связанным текущим фактам |
| Observations | observation_extractor.py и специализированные инспекторы | Структурированные наблюдения, а не только текст модели |
| Job Store | job_store.py, state/jobs | Cases, checks, evidence, observations, resources, результаты и блокеры |
| Operation journal | operation_journal.py | Намерение до commit, fingerprints, replay barrier, сохранение неопределённости |
| Recovery/workflow | operation_recovery.py, operation_workflow.py | Evidence-only reconciliation, locked stages и неизменность принятых ID |
| Resource lifecycle | ledger в Job и cleanup mechanisms | Учёт owned ресурсов, зависимости, область очистки и проверки результата |
| Документная память | knowledge_index.py, knowledge_tool.py | Индексация источников и knowledge_search |
| Продуктовые facts | product_knowledge_store.py, product_knowledge_retrieval.py | Scoped facts/confirmations и ограниченный проверенный retrieval |
| Новые knowledge records | product_knowledge_records.py | Additive candidate schema v1, trusted source admission, дедупликация/конфликты |
| Идентичность памяти | memory_identity.py, prepared_memory.py | Актуальные component identities и подготовленное чтение памяти |
| Подготовка плагинов | plugin_version_reference.py, distribution_catalog.py | Справочник версий/provenance и различение подготовки от реальной установки |
| Stand/SSH configuration | stands.py, ssh_worker.py | Управляемый доступ, секреты вне публичного корпуса; доверие к SSH host требует усиления |

## Границы

Продуктовые названия и рецепты должны быть в источниках, bindings и адаптерах, а не в универсальных if/else Core. Новая запись знания не даёт инструменту права изменять UC. LLM, источник документа и исполнитель проверки имеют разные уровни доверия.

Прямой общий API памяти, multi-tenant RBAC, структурный code index и распределённые workers ещё не реализованы. Текущий project_id в admission — граница доверенной операторской конфигурации, не полноценная система авторизации пользователей.

Далее: [исполнение](execution.md), [policy](../02-safety/action-policy.md), [память](../03-knowledge/architecture.md).
