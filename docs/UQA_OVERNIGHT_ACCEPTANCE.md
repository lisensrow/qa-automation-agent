# Разработка и проверка UQA до утра

До 09:00 Europe/Moscow 15 октября 2026. Пользователь разрешил тестовые действия в локальной лабе без повторных вопросов. STEP/AUTO и v069 policy сохраняются. Существующие рабочие объекты не менять; новые owned объекты маркировать uqa-test и регистрировать точный ID. Не выполнять разрушительные команды ОС. Проверка — часть разработки, а не остановка между этапами.

## Последовательность

1. Память: source-validated bounded context в knowledge_search. v176 установлен; fixture и py_compile PASS; полный runner 218/218 PASS. Production recall вернул два проверенных по hash правила состава коллекций. Candidate не становится verified или evidence PASS.
2. Live model-context probe: PASS, 23.12 seconds, composition/recompute/no_false_pass/recheck все true. Receipt /tmp/v176-model-context-receipt.json. Это не сквозная UI-приёмка и не обучение весов.
3. Официальное руководство: коллекции, политики, процедуры. Сохранять revision/hash, разделять declared_spec, runtime actual и операторский опыт. Не объявлять confirmed bug без developer confirmation.

Статус v177: шесть дополнительных candidate declarations из официального guide приняты, exact replay dedup проверен; recall политики=2, процедуры=4. Первые collection Jobs 20261014-195333-0cff9442 и 20261014-195822-3416e089 BLOCKED, созданных ресурсов/unknown operations нет. Исправлен task authority, добавлен generic vocabulary и короткий source-grounding до managed turn. Финальный suite /tmp/v177-final-full-smoke.log и live Job 20261014-200343-6a9974e4 ещё проверить. Shell 88516 может ждать existing policy prompt: не подтверждать неподходящий раздел/изменение существующих объектов.
4. Автономная коллекция Windows по обычному промпту: одна новая коллекция, exact CI membership и фильтры по свежему ответу. ACK недостаточен.
5. Ubuntu и Linux nested OR: AND/OR, archived false и endpoint scope.
6. RAM/CPU: сравнение component inventory с условиями; известное отсутствие чисел в таблице не считать PASS метрик. Inventory не равен текущей нагрузке.
7. Сохранение опыта и повторный recall: без дублей и без перезаписи прежних версий.
8. Политики: inspect/manual → одна owned политика на точном тестовом scope. Не связывать с рабочей all. Конфигурация и фактическое действие проверяются отдельно.
9. Политики: отрицательный oracle, расписание/условия и защита от повторов. Неподдерживаемое — BLOCKED, не придуманная настройка.
10. Процедуры: изучить реальные блоки/связи; безопасная диагностика на выделенной КЕ, результат и отчёт. Никаких разрушающих ОС команд.
11. Запрос «как автоматизировать…»: только рекомендация без запуска; после согласия — owned процедура с проверенной конфигурацией и результатом.
12. Отчёт к утру: expected/actual/evidence, честный статус каждого блока, незавершённые операции и остаток. Обновить архитектуру/CHANGELOG; commit/push только code/tests/docs. После цепочки — следующий безопасный незавершённый этап основной программы.

## Возобновление

Закрытие текущего turn v178: 20261014-203126-d02151ff BLOCKED после Name-not-found на Composition и повторной неподходящей table observation. Save не выполнялся, ресурсов нет. Session 88516 вернулась к shell. Следующий безопасный шаг — свежая operator-assisted инспекция Settings и Conditions в новом несохранённом editor, уточнение reviewed последовательности вкладок/полей, затем повтор model probe с тем же ordinary business intent. Не считать вход в форму полной capability. Полученное знание должно содержать document vs runtime provenance; не добавлять U-Connect-specific if/else в Core.

Последний checkpoint v178: /tmp/v178-full-smoke.log 219/219 PASS. Model Job 20261014-203126-d02151ff, case tc-34c9dff94, owned_name uqa-test-v176-windows-20261014-203126, session 88516. Guided section hint CMDB; модель после recall опыта открыла правильный новый editor (ev-cc21733509af), затем Name на Composition не найден (ev-db0d6dd9f2a3). Следить за этим текущим turn, не начинать второй create. Перед подтверждением Save проверить новый editor/точное имя/отсутствие существующего target и immutable oracle; при unknown intent читать свежие receipts, не отправлять повтор. После условий — политики и процедуры, с отдельным строгим test scope.

v178: Job 20261014-202207-d0073163 guided-section model BLOCKED (выдуманный container CMDB). Operator-assisted entry Job 20261014-202554-5f8da88c PASSED только по открытию нового несохранённого editor, Save не нажимался, ресурсов нет. Блок unknown browser_inspect_form_semantic сохранён как ошибочное имя helper; реальный form inventory tool — browser_inspect_form_validation_semantic. Обновлён UQA_COLLECTIONS_KNOWLEDGE.md, index backup /opt/uqa/backups/v175-knowledge-data-20261014/document-index.before-v178-collections.db; остальные 1136 chunks неизменны. Collection bootstrap добавляет experience query «коллекция Manual Table fields»; профиль PASS, финальный /tmp/v178-full-smoke.log ещё проверить. Новый guided model turn запущен на session 88516 с UQA_MAX_TOOL_STEPS=48; прочитать последний Job/журнал перед любым повтором, не создать второй объект при timeout. Архитектура/policy не ослаблялись.

Контрольная точка v177: финальный installed runner /tmp/v177-final2-full-smoke.log — 219/219 PASS. Последний collection Job 20261014-201221-d9aca32c также BLOCKED без ресурсов; plus с role=button не найден, Add не прошёл navigation preflight. Следующее действие: свежая инспекция CMDB entry и создание по known-route/manual-grounded контексту, не повторять старые семантические клики. Проверить существующий опыт: knowledge_search("коллекция Manual Table fields") находит indexed UQA_COLLECTIONS_KNOWLEDGE.md; запрос по имени файла не находил. Если общий navigation blocker требует отдельной доработки, зафиксировать его и проверить независимые безопасные формы политик/процедур, не объявляя коллекции готовыми.

Каждый заход читать этот план, архитектуру, CHANGELOG и проверять diff/Jobs. Не повторять создание после таймаута: сначала журнал и exact-ID reconciliation. Автоматическое возвращение каждые 15 минут только если текущая работа закончилась; внутри захода выполнять последовательность без ожидания. Уведомлять о проверенном этапе или значимом сбое, не повторять неизменный статус. В 09:00 не начинать новые действия, составить отчёт и завершить ночную автоматизацию. Незавершённое не объявлять готовым.
