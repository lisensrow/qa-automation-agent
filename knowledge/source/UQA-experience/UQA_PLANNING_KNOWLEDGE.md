# UQA: опыт структурного планирования

## Whole-request entry без заранее созданного кейса — v284

Второй ordinary run Windows Job20261015-144239-c74933d1/tc-50c3cc9f/ev-d81003fde504 также PASSED6cells/5Y0N/noTimeout/0resources/operations, без operator-prepared case/browser. Оба результата относятся к одному узкому whole-request grammar; это не general freeform routing.

Reviewed derived UQA guidance/candidate/document_review; не официальный факт продукта, не баг/фикс и не full business acceptance. Scope server/frontend/core/plugin/os unknown. Ubuntu/Windows — литералы условия, а не доказанная ОС живой КЕ.

Обычный regression entry распознаёт только целый запрос: «На стенде lab проверь в CMDB в новой несохранённой коллекции AND-условия: неархивные Endpoint с Ubuntu. Не сохраняй.» Также поддержан Windows. Host expected из original request существует до модели, содержит boolean false/enum endpoint/Contains plain OS literal, один case/check; request SHA и повторный разбор сверяются каждым runtime guard. Лишние критерии/OR/Save/другой stand/неизвестная ОС/отсутствие явного CMDB не отбрасываются — supported adapter не выбирается, работает прежний planner. STEP/AUTO и policy неизменны; parser не разрешает actions.

Expected:6ячеек unsaved AND, no Save. Actual ordinary Ubuntu Job20261015-144053-e6af5d4c/tc-119b9053/ev-3f22b4a374cd PASSED6cells/5Y0N/noTimeout/0resources/operations, operator_prepared_case=false/operator_browser_preparation=false. Старый no-CMDB Job142845-b9c8c036 BLOCKED navigation, затем143643-aac9eda7 BLOCKED из-за временного import shadow в harness; history сохранена, guard не обходился. Контролёр нужно запускать из production import context, а не загружать старые /tmp modules. Это limited supported ordinary entry, не произвольный prompt, nesting, saved AST/member, политика или процедура.

## Логические типы вместо UI-форматирования — v270–v280

Reviewed UQA guidance, namespace uqa/document_review/hypothesis, не официальная спецификация продукта и не developer-confirmed bug/fix. Версии server/frontend/agent/plugin/os unknown. Ubuntu/Windows ниже — литералы фильтра, не доказанная ОС реальной КЕ.

В supported caller-prepared uc.collections.os-family.v4 модель предлагает Archived=false(boolean), CI class=endpoint(enum), OS name Contains Ubuntu/Windows(plain literal). Trusted profile отдельно задаёт UI No/Endpoint, Operator Wildcard и *literal*, точный row_label Endpoint.OS name. Не давать модели выбирать pins/mappings/UI encodings или выводить expected из её ответа. String false/No вместо boolean, неизвестные enum, wildcard metacharacters и несовпадение expected отвергаются. Прежний v2 остаётся самостоятельной совместимой схемой.

Expected: три логических условия flat AND и независимые6cell hashes до генерации. Actual: normal prepared Ubuntu Job20261015-124128-54229803/tc-1c4b0c0e/ev-dac624844853 и Windows Job20261015-124453-b6a01a17/tc-78c2194f PASSED6cells/5Y0N/noTimeout/0resources/operations/no operator browser preparation. Предыдущий v3 Job20261015-123408-12c2551c BLOCKED до condition writes из-за string false; история не переписана. Это узкая unsaved UI phase, не Save/AST/member/nested filters/freeform CLI routing. Общий Core не содержит UC-specific value if/else; mapping принадлежит product profile. Fixture tests не заменяют эти native observations.

## Типизированный компилятор условий и свежее чтение v248

15октября2026, experimental_model_plan_recipe_execution, Job20261015-090636-f0bcfc48/tc-6f85d97a. В caller requirement до генерации закреплены профиль/hash, expected logical plan и6expected cell hashes. Отдельный production pure condition_plan строит field-specific typed response schema, проверяет plan против caller expected/profile pin и компилирует только UI-аргументы; выполнение остаётся у экспериментального harness. Модельный план ev-7731c01e09ec, compiled plan ev-61fcce85baf5, applied rows ev-417edce74e84/ev-008efffc8593/ev-73b0aaf714db. После всех строк независимый DOM readback ev-c0bbe21510c0 прочитал6ячеек и подтвердил all_matched=true, включая Equal для Archived и CI class.3строки/4установленных значения,5Y0N/noTimeout. Фаза подтверждена, но общий caseBLOCKED0resources/operations/browserclosed; noSave/noAST/member oracle, нет общего production runtime или самостоятельного входа.

Перед этим Job20261015-090143-87d5bef0 остановился ValueError без сохранённого точного ответа; причину не угадывать. Следующий20261015-090405-cf4287dd сохранил план с Wildcard у Archived/CI class и был отклонён condition_plan_unknown_operator до настройки. Исправлена схема: допустимые операторы привязаны к конкретному полю, а не общему списку; независимый валидатор не ослаблен. Чистая компиляция не даёт разрешений, не подтверждает текущую применимость и не освобождает journal. Доказан узкий prepared эксперимент, не статистическая надёжность, не developer-confirmed bug/fix и не переносимость на все версии/поля. Версии продукта/frontend/ядра/плагинов/ОС unknown. Предыдущий245 без final DOM остаётся отдельным историческим этапом.

## Конструктор условий: логический план и ограниченный исполнитель v245

15 октября2026, experimental_model_plan_recipe_execution, Job20261015-085016-4004ece3/tc-5792940c. Предварительно заданы три условия и hashes четырёх expected values; оператор открыл новый несохранённый Conditions. Локальная модель qwen3:14b получила человеческое задание и обычный indexed recipe через tool-free structured response: logic и field/operator/value. Схема предлагала AND/OR, Equal/Wildcard и три поддержанных поля, но значения модель выбирала сама. Независимая проверка сравнила AND/Archived Equal No/CI class Equal Endpoint/OS name Wildcard *Windows* с заранее заданным expected, прежде чем разрешать компиляцию UI-действий. Plan evidence ev-c6caee568b63 matches_predeclared_expected=true.

Экспериментальный trusted compiler сам определял parents/source/target и колонки; модель НЕ составляла низкоуровневые tool arguments. Через прежнюю policy и точный scope supervisor выполнены три browser_add_tree_row_semantic: ev-94246c241e98, ev-ffbfa4bda970, ev-382bf77f43b4; четыре значения matched по native receipts/hashes.5Y0N/noTimeout, phase_configured=true. Сохранения/новых ресурсов/journal operations нет, browser закрыт; общий Job BLOCKED. Это НЕ production-интеграция, не самостоятельная навигация, не saved AST/member oracle и не проверка итогового DOM после всех строк. Отдельные receipts подтверждают значения на момент соответствующего действия. Версии продукта/frontend/ядра/плагинов/ОС unknown.

Контрпримеры сохраняются: tool-choice phase243 Job20261015-084217-44affedc и244 Job20261015-084623-5589aa60 выбрали композит, но смешали дерево/leaf/колонку; scope supervisor отклонил3предложения каждого до выполнения,0verified cells. Уточнение описания аргументов не доказало исправление. Это не строгий A/B benchmark моделей. Вывод-кандидат: для узкого поддержанного профиля разделять извлечение логического намерения и проверяемую компиляцию UI-аргументов; перенос на новые поля/вложенные AND/OR, политики и процедуры требует новых catalog/schema/oracle/runtime проверок. Не обходить действие-политику и не выдавать prototype за общую автономность.

Revision: v218-v220-2026-10-15. Namespace: uqa. Это reviewed technical experience/candidate guidance, не официальная спецификация UConnect, не developer confirmation и не runtime acceptance продукта. Версии продукта/frontend/ядра/плагина и ОС для применимости этой рекомендации: unknown.

## Обязательные зависимости плана задаёт код

Инженерная рекомендация-кандидат: обязательный порядок узкого supported profile следует задавать проверяемым кодом, а не доверять порядку свободного текста или JSON модели. Это не общий автоматический planner и не решение для произвольного workflow. Модельные предложения необходимо проверять независимо; структура предложения не доказывает выполнение предусловий.

Поддержанный proposal-only профиль disabled_scoped_create_proposal v1: prepare_disabled_draft → verify_disabled_draft → verify_exact_scope → commit_create → verify_saved_disabled_scope. Caller задаёт точные stand/campaign/resource/name/scope/target IDs; desired_enabled должен быть boolean false. Подготовка должна предшествовать проверкам; обе проверки — фиксации. Активация, расписание, запуск, неизвестный payload и произвольные команды в этот профиль не входят.

## Что ожидалось и что действительно наблюдалось

- v218, Job20261015-045753-78c259aa/tc-0a1b16b9/ev-0d7a1b4cfcd9: operator-bound native model proposal, обычный reviewed-memory retrieval, исторический Windows scope. Ожидалось структурно допустимое предложение; получено rejected/ValueError. Подробная причина не сохранена, её нельзя восстанавливать догадкой.
- v219, Job20261015-050114-0425550c/tc-1887d141/ev-c9e9c3da489f: отдельный Ubuntu outline, binding остаётся у caller. Ожидался правильный порядок; safe diagnostic показал verify_disabled_draft, verify_exact_scope перед prepare_disabled_draft. Результат rejected/proposal_unsafe_or_unsupported_order. desired_enabled=false не делает неправильный порядок безопасным. Эти прогоны не являются контролируемым сравнением качества моделей.
- v220, тот же Job/case, ev-e4e7651d7157: отдельный operator-compiled supported-profile skeleton по hash-pinned исторической области; модель повторно не запускалась. Структурный результат valid_proposal_only, model_plan_accepted=false. Pin: 441287bfe906d0556884577f97a82dbfd386660577549eca32c7e3e40f97c4b8. Оригинальное отклонённое evidence сохранило свои bytes/hash.

Все эти cases остаются BLOCKED как QA, без новых ресурсов, journal operations или UC actions. Execution modes operator-bound/model diagnostic и operator-compiled различаются; автономной приёмки нет. Исторические target IDs не являются текущим scope/permission.

## Что ещё не доказано

Нет свежего доказательства выключенного текущего draft, ownership/current membership, UI lifecycle, принятого backend payload или эффекта исполнения. Все execution/runtime/precondition/schema/PASS/replay flags false. Pure validator и deterministic skeleton ещё не подключены как новый production CLI/executor; STEP/AUTO, v069 и fixed operation_workflow не менялись. Старые uncertain/awaiting_verification операции не освобождены. Новое исполнение требует отдельного поддержанного контракта и прежней policy/journal.

Эта заметка может поддерживать только hypothesis/test_experience candidate в общей памяти UQA. Её нельзя продвигать как runtime факт UConnect, официальное руководство, доказанный баг/фикс или обещание готовности администратора.
