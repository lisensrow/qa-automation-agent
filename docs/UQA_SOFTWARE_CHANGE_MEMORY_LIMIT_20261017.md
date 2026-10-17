# Ограничение воспроизведения опыта US-T114

REGCHANGERECALL691. После реального полного US-T114 Astra3/3 UQA неверно воспроизвела число шагов из корректно сохранённого источника REGCHANGE689. Это отдельный memory-interpretation FAIL, не отмена фактического прогона и не полный успех обучения.

Job20261017-133948-12a971a5/tc-b880d6c6, own knowledge_search ev-8ac913da6696, model review ev-d7d19df9824d, accepted=false. Получен source UQA-experience/UQA_SOFTWARE_CHANGE_CASE_20261017.md chunk1, truncated=false. В реально полученном тексте прямо указано «Один полный бизнес-сценарий US-T114: 3/3 шага на Astra», отдельно Windows0/21/Astra1/19/всего1/40 и непринятая свободная автономность. Недостатком retrieval/обрезкой ошибку объяснять нельзя.

Expected: source_case US-T114, os Astra, full_business_steps3, freeform_autonomy_accepted=false, full_matrix_complete=false. Actual: четыре поля корректны, full_business_steps=1. Не доказана точная внутренняя причина; результат согласуется со смешением счётчиков кейсов и шагов, это интерпретация, не установленный факт о reasoning модели. Не повторяли неизменный запрос, не вкладывали правильный ответ в новую подсказку, не переписывали исходный результат и pinned689 source/event.

Локатор/query и JSON-поля подготовлены framework; сама query не model-selected. Реальную интерпретацию получил qwen3:14b при неизменном context24576/RTX5070Ti, один ответ без correction loop,0agent tasks/Jira/Zephyr actions. Это ограниченная проверка памяти, не ещё один регрессионный кейс. Модельные веса не менялись; точная надёжность recall и свободный lifecycle остаются непринятыми.

Сохранять ограничение отдельным candidate/document_review событием, snapshot обеих БД/dedup/integrity/retrieval, без verified promotion. Полный бизнес-результат687 (parent20261017-132524-dd45d6c2/canonical ev-8c2d447afa2b/model ev-959882d99659) остаётся самостоятельным доказанным подготовленным сценарием3/3. Следующий критерий — надёжно различать case_count и source_step_count из структурированных собственных доказательств, а не наращивать prompt-only пробы.
