# UQA: опыт структурного планирования

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
