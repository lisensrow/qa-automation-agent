# Проверки, покрытие и ограничения

Финал v195: технический runner226/226PASS, context-only задача AND/OR/RAM/None9/9PASS после предметного retrieval fix. Независимая обычная UI-задача v196 осталась BLOCKED: вместо Windows-коллекции модель прочитала общую таблицу CMDB; неподдерживаемый assertion field visible_row_count также отвергнут. Никаких изменений/ресурсов/операций. Поэтому знание рецепта и технические тесты не равны автономной навигации или готовности всего workflow.

Актуальный опыт коллекций: операторский readback десяти сохранённых коллекций проверил точные составы; All совпал с независимым списком четырёх Endpoint.16 RAM/CPU ячеек нечисловые, поэтому отображение метрик не принято. Редактор одного тестового Windows-фильтра открыт через прежнюю policy без сохранения/пересчёта; native GET подтверждает конкретную конфигурацию. Три source-bound candidate сохранены с узким scope, но это не автономное создание, не general verified promotion и не автоматическое знание всего конструктора. Production-код после226/226 не менялся.

Технический runner: run_smoke_v070.py. Tests в smoke/ в основном используют isolated fixtures/temporary state; число PASS не равно количеству автоматизированных продуктовых сценариев. Py_compile проверяет синтаксис, не бизнес-правильность.

Первый профиль v175 проверяет bounded record schema, отсутствие самостоятельной promotion, trusted source hash/revision/applicability, runtime evidence/case/identity, deterministic dedup, conflict handling, transactional rollback и сохранение legacy таблиц. 10000 повторных событий одного утверждения не создают 10000 variants и не увеличивают independent source count. История этих событий сохраняется отдельно.

Дополнены isolated проверки истории ОС/версий и редакций руководств, ограниченного read_history, project separation и developer gate: общий документ/нет подтверждённой роли не объявляют bug/fix; approved developer source допускает лишь candidate, без upgrade advice. Реальная смена версии UC и реальный исправленный баг этим fixture не тестируются.

## Реальные ограниченные доказательства

- Exact CI/card и вкладка Agent на Windows/Ubuntu: выбранные read-only сценарии.
- Prepared фильтр: разрешённые fill/read/clear/restore, не любой UI workflow.
- Add form open/read/close: без сохранения данных.
- Коллекции: десять созданных операторским bridge, exact membership; metric display RAM/CPU не принят из-за None-подобного текста.

Не закрыты arbitrary frontend, полный автономный owned lifecycle, исполнение всех plugins по ОС, automatic plugin installation, Jira/Zephyr запись, произвольный cleanup UI и общий безопасный multi-agent memory API.

## Критерии качества знаний

Не смешивать specification/static implementation/runtime/hypothesis, fixture/live/operator/autonomous и tested/declared compatibility. Не выдавать память вместо свежего evidence. Negative tests и конфликты полезны, но их источник и scope должны быть видны.

Актуальные результаты завершённого релизного набора фиксируются в [release verification](release-verification.md). Отсутствие продуктового сценария в coverage — явная граница, а не скрытый FAIL продукта.
