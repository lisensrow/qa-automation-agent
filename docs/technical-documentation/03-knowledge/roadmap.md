# Следующие блоки памяти

Первый этап: атомарный формат, source integrity, candidate-only admission, deterministic dedup/conflict и сохранение legacy DB. Не меняет существующий факт retrieval и не утверждает semantic truth.

Дальше, по проверяемым этапам:

1. Типозависимые semantic validators/promotion, подтверждение применимости и отзыва оснований; отдельный acceptance recipe.
2. Safe post-run exporter/outbox всех нужных исходов. Delivery at least once + idempotent sink, без повторного запуска теста из-за сбоя knowledge worker.
3. Версионированное read API с актуальными ACL/status/scope gates и ограниченными context budgets; не прямой shared DB dump.
4. Импорт редакций официальных руководств с byte snapshots, diff/provenance и selective recheck.
5. Один разрешённый репозиторий: commit/symbol/definitions/references, связь feature → API → implementation → test → runtime result.
6. Semantic/relationship retrieval после оценки пропусков FTS, не вместо oracle/version filters.

Целевая общая память обслуживает QA, документацию, разработчиков и техподдержку. Разные представления не должны порождать четыре независимо переписанные энциклопедии. Доступ к памяти не предоставляет stand WRITE, а статическая ссылка на код не доказывает выполнение ветки или root cause.

Структурный code index, общая авторизация агентов, automated document updates и semantic search сейчас не реализованы. Ориентир для переносимых code links — [SCIP](https://github.com/scip-code/scip); для provenance — [W3C PROV](https://www.w3.org/TR/prov-overview/). Это направления развития, не заявления о внедрённой совместимости.
