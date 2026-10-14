# Опыт технических тестов v172 v173 v174

## Метаданные и классификация

record_id: uqa.technical.experience.2026-10-14.v1; schema_version: 1; knowledge_kind: test_experience; execution_mode: isolated_fixture; validation_status: observed; evidence_for_pass: false.
Источник: профильные smoke scripts и полный runner установленной UQA, 14 октября 2026. v173 runner 215/215 PASS; v174 py_compile, профильный incremental index test и полный runner 216/216 PASS. Это изолированные технические тесты, не столько же реальных тест-кейсов UC. Число успешных тестов не означает поддержку произвольного UI, автономного регресса или тренировку весов.

## Disabled, not_sent и защита от повторов

Native in-process отказ disabled-кнопки до начала клика отличается от неизвестного результата после отправки. Fixture проверяет disabled в настоящем браузерном adapter без клика. Журнал сохраняет отказ и новую попытку; разрешение Core запрашивается снова. JSON с executed=false, строка ошибки, timeout и отсутствие ответа не создают not_sent и не освобождают replay barrier.
Operator-reviewed rejected/canceled требуют provenance/явного решения; не выставляются автоматически из HTTP400. Исходные receipts и oracle сохранены, тот же stage заблокирован. Модель не получила инструмента отмены intent. Эти состояния не превращаются в verified/PASS.

## Большие JSON и недопустимость усечённого доказательства

Раньше evidence text обрезался на 6000 символах, а native response body — на 8000; JSON мог стать невалидным. Теперь writer сохраняет валидный JSON до 262144 UTF-8 байт, native response до 65536 символов, request до 8000. Oversize хранит валидную metadata-заглушку с явным truncated флагом/хешем, а не сырой префикс и не выдуманный executed=false.
Fixture вызывает production network getter с изолированными HTTP-response объектами: полный большой JSON сохраняется; sensitive fields и headers redacted; превышение native/UTF-8 бюджета непригодно для verdict. Reconciliation отвергает truncated response. Эти fixtures не отправляют реальные запросы UC.

## Однодокументная индексация и сохранение знаний

v174 index_document обновляет только один reviewed источник внутри SOURCE_DIR транзакцией. Fixture создаёт временный SQLite FTS5 и Markdown, проверяет поиск через настоящий knowledge_search, идемпотентную повторную индексацию, сохранение другого документа и его row IDs. Пустой документ, внешний путь и symlink за пределы source отвергаются, прежние чанки остаются. Реальная база перед импортом резервируется SQLite backup API, не копированием одного DB-файла без WAL.
Эта функция не является безопасным автоматическим редактором любого входного текста: curate/redaction/provenance обязательны до вызова. Raw Jobs, secrets и stdout не индексировать.

## Правило для будущего опыта

В индекс попадать должны не только успешные live сценарии, но и ограничения, FAIL/BLOCKED и полезные технические проверки. Режим live_operator_assisted/live_autonomous/isolated_fixture и версии не смешивать. Историческое наблюдение даёт подсказку для следующего действия, а не право объявить новый PASS. Автоматический exporter всех run types ещё предстоит сделать и проверить; текущая запись — reviewed импорт выбранного опыта, не полный импорт всей истории.
