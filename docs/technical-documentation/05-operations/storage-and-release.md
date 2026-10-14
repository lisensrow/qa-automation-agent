# Хранение, обновление и эксплуатация

| Категория | Правило |
|---|---|
| Source code и docs | Git/GitHub, понятные логические commits после проверок; без force push |
| Официальные документы | Versioned sources и hashes; старую редакцию сохранять, не считать замену файла обновлением всех знаний |
| Runtime state | Jobs, operations, observations/evidence, ledger; сохраняется вне Git |
| Базы памяти | Document FTS и product knowledge DB; consistent SQLite backup с учётом WAL перед migration |
| Secrets/sessions/artifacts | Приватные данные, не публичные docs, не shared knowledge corpus |

## Добавочное обновление памяти

До schema migration сверить clean source state и сохранить согласованную backup product DB. Добавлять только knowledge_v1_* таблицы. Сравнить schema/content fingerprints прежних таблиц и документного индекса до/после. Не выполнять backfill/переклассификацию старых verified facts в этом этапе.

Runtime ingestion записывает candidates/manifest/support/event транзакцией. При ошибке нет частично принятого event; exact retry не дублирует запись. Восстановление не должно возвращать всю БД из backup поверх новых чужих изменений без анализа и разрешения.

## Риски

Нехватка диска может блокировать очереди/запросы продукта. Диагностика должна отличать infrastructure от session expiration и дефекта функции. Очистка журналов/данных требует отдельного разрешения и проверяемого recoverable scope; защитные thresholds не понижаются для продолжения теста.

Общие concurrent Job RMW и unknown legacy/autosave paths остаются отдельными ограничениями. SSH host-key trust текущего MVP требует усиления перед эксплуатацией вне лаборатории. Новая source policy не является заменой authentication/RBAC.

Для shared документации передавать папку этого пакета или утверждённые Git docs, не полный checkout с Jobs/secrets/backups. Документы пакета сами по себе не выполняют команды и не предоставляют доступ к стенду.
