# REGDMI651 — собственные DMI/SMBIOS данные и отдельное качество отчёта

REGDMI651 browser_compare_owned_dmi_identity_semantic / owned-dmi-identity-recorded-raw-v1: восемь заранее объявленных сырых identity-полей системы, BIOS и baseboard. Это ограниченная гипотеза сопоставления, НЕ нормативный UC contract, не всё оборудование/CPU/DIMM/UI и не полный кейс US-T79/US-T102. Исходный полный регресс 40 кейсов/301 шаг не увеличивается от технических smoke или этого subset.

REGDMI651 итог для повторного применения:650Windows и650Astra — каждый8полей:6RAW_EQUAL/0RAW_DIFFERENT/2UNKNOWN, raw BLOCKED. None в baseboard_version/system_product_version не считать совпадением. 647обеих ОС: payload/journal/own full hash подтверждены, но terminal plugin_delivered=true ошибочен, workflows completed=false; новых доставок647не было. 650сохранила source_audit_workflow_completed=false/source_audit_final_report_accepted=false, не исправляла оригиналы и не отправляла новых задач. Все данные из тех же записанных пар/собственных первоначальных хешей; не live, не весь hardware/full case/business PASS. Оператор scope/refs/oracle/код/standing approval transport, framework phases/hash/comparison, модель own memory/tools/read/report — раздельно. Это подготовленное выполнение, не ordinary freeform end-to-end autonomy.

## Проверенные наблюдения до сравнения

Все перечисленные действия — на двух ранее выделенных Windows/Astra, core1.3.27, executeCommand1.4.0 и smbiosAudit1.3.8 по собственной readiness. Остальные неизвестные версии не latest. Модель qwen3:14b/исходный digest, контекст24576/RTX5070Ti не менялись. Jira/Zephyr не открывались. Доставка/обновление плагина, ядра или настройки не выполнялись.

| Этап | Windows | Astra |
| --- | --- | --- |
| Только нужная инвентаризация641 | Job20261017-043044-89c7c8eb / tc-91f8d9c5 / ev-21572cb63bda | Job20261017-044037-60142961 / tc-3f3d9026 / ev-142458de70c7 |
| Независимый DMI646 | Job20261017-043748-95f6d6e5 / tc-5c3e3e5a / ev-860f95c62e90 | Job20261017-044527-4c1025e6 / tc-51508cb1 / ev-0438cacfcdff |
| Собственный native READ | ev-6ce22facd84c | ev-958a02291324 |
| Свежий SMBIOS647 | Job20261017-044727-2becd140 / tc-3a5a1957 / ev-497c30c9c06f | Job20261017-044859-c37d1b6a / tc-bd79a29f / ev-f37377188a80 |
| Собственный audit READ | ev-bd77acf20a1f | ev-0ac607096c73 |

641 обеих ОС обновили только действительно stale inventory, по одному verified pluginAudit; не доставка/main/OS query. Astra до refresh: last_audit_at02:36:42.392Z, age7466.2s, ready=false/plugin_audit_stale. Лимит freshness3600s не менялся. Старая операторская отметка часа inventory была неверной; первичные timestamps выше приоритетнее. 646 обеих ОС по одной verified executeCommand: восемь строк, OBSERVED_WITH_UNKNOWNS, два placeholder `None` в system_product_version/baseboard_version. Это UNKNOWN, не конкретная версия и не совпадение.

Windows native processed04:39:26.199Z / stdout SHA bc0fabcc4e7fdc97d8c1f1f1285e2020e161125e2d2dd275656c1001c2e64298 / values SHA10b9e38f6f796cf73cfe6dde84b926971ff62287b9ef91cf716771d1c74ad906. Astra native processed04:46:20.274Z / stdout SHA627439054c3722c7e40d7b52825747461f6548707a82484ac941dc406c2a0b25 / values SHAb8f105af7799b4ff1e7c032f496fd43493c686a1690b66f3f23913d5c77b5ad2.

647 обеих ОС — ровно одна verified smbiosAudit, собственный fresh full и canonical legacy BLOCKED report. Windows processed04:48:18.043Z / entire data SHAc924b1df0d242f0f0cfc32e998b938a1f407558bb810043667e72f38a877d9d3. Astra processed04:50:09.264Z / entire data SHA0cc0b17b507ae0c54d8321aef1fca28fc72ea2ff503b203ef69d9b0e0ebf1aac. Это именно хеш полного data при первоначальном модельном READ, не впервые захваченный оператором позже. Повторный refresh не понадобился, delivery отсутствует.

ОБА итоговых модельных JSON647 ошибочны: plugin_delivered=true при единственном execute-audit в текущем Job. completed=false/AssertionError сохранены. Статус установленного ранее плагина не равен новой доставке в текущем запуске. Возможная языковая неоднозначность поля не отменяет провал исходного ожидаемого ответа. Нельзя переотправлять аудит из-за ошибки prose, переписать исходный ответ, назвать эти workflows полностью успешными или считать дальнейшую правильную интерпретацию исправлением истории.

Исходный640Windows остановлен fresh_command_plugin_not_loaded до POST/0ops. После641refresh следующий643Windows остановлен Core read_only_request/0ops: оператор ошибочно назвал весь запрос read-only, хотя хотел разрешённое создание диагностической карточки. Это корректный отказ Core, не ошибка безопасности. В646 уточнён новый операторский запрос создания task; policy не менялась, фактической команды из640/643 не было. Не маскировать отдельное продолжение под один самостоятельный lifecycle.

## Контракт read-only сверки648

Оператор заранее закрепил mapping восьми полей, singleton1 для system_information/bios_information/baseboard_information, max_pair_seconds1800, exact raw case/spaces, unknown/placeholder критерии. Эти правила записаны ДО native query; фактические own refs/raw expected/hashes — ДО audit POST. Старый legacy oracle трёх list fields не менялся. Исторические примеры не текущий expected; Astra пример имеет invalid JSON, source archive не исправляется.

Новый Core OBSERVE требует точный locked READ Job/case/target, завершённые источники, собственные uqa_tool READ receipts, оригинальные native scope/payload, canonical audit receipt, prior verified delivery, точные journal stage/tool/resource/arguments/verification fingerprints и verified task IDs. Не принимает операторский первый hash как модельный. GET перечитывает ТЕ ЖЕ два full payload, сверяет task/agent/CI/server_created_at/processed_at и оба исходных хеша; дополнительные необследуемые поля audit тоже защищены полным data hash. Пара заморожена по processed_at, не объявляется live-current; source age-now не обходится новым POST.

Качество исходного итогового ответа — отдельная проверяемая ось, не условие существования already verified payload. Для647 canonical receipt/journal/hash остаются доказательствами данных, но source_audit_workflow_completed=false/source_audit_final_report_accepted=false обязаны явно сохраняться в сравнении. При прочих незавершённых/неподтверждённых captures отказ. Это не ослабление raw expected, unknown/cardinality/time/hash и не promotion старого workflow. Проверка исходного model JSON не меняется ради PASS.

Всегда восемь строк. Missing/ambiguous/nonstring/empty/placeholder не становятся равными по умолчанию; `None` остаётся UNKNOWN даже если с двух сторон одинаково. Любой unknown → общий raw BLOCKED, при известных различиях они также сохраняются отдельными строками. Без нормализации/выбора подходящей строки из нескольких/исключения неудобных полей. Сырые различия не developer-confirmed bug. Все full-case/business/нормативные/CPU-DIMM/UI/live/security/replay claims false, новых endpoint tasks0. Служебные bounded errors называют только безопасный этап отказа, без секретов/полного payload.

## Роли и проверка

Оператор: исследование OS references, код, scope/refs/oracle, подготовка отдельных продолжений/phase catalogue и передача standing-разрешений. Ровно шесть ручных Core WRITE `y`:641W/A,646W/A,647W/A, только новые точные задачи; это не самоавторизация модели. Framework: fixed payload/compiled bound actions/phase gates, полный hash/verification/comparison/бюджеты. Модель: собственное чтение памяти/источника, вызовы readiness/task/own fresh READ и последующая интерпретация своих receipts. Это operator/framework-assisted выполнение, не обычный человеческий freeform end-to-end регресс.

Focused648 synthetic fixtures: обе ОС, восемь полей/регистр/пробелы/placeholder/cardinality, Core READ/no ops, cross-target refusal, hash изменения в исследуемом и постороннем поле, временное окно, bounded errors/projection, false исходного отчёта не заменяется true. Read-only проверка реальных source proof graphs: обе допустимы, по шесть in-memory подмен fingerprints/status/time-rule/raw-values/agent/legacy profile отвергнуты; оригиналы не менялись. Полный648:302/302 технических smoke PASS, не302 source шага/кейса. Отдельный638:301/301 technical PASS. Это проверки кода, не регресс продукта.

## Actual650 — интерпретация записанной пары

Windows Job20261017-045439-29e60f1b / tc-49dbbc91 / ev-14b957e5a0a1: completed=true для отдельного подготовленного READ continuation. Модель сама вызвала memory search→свою CI→GET-сравнение двух прежних payload. Все8полей учтены:6 RAW_EQUAL,0 RAW_DIFFERENT,2 UNKNOWN, общий raw BLOCKED; None/None не стали совпадением. Pair531.844s в заранее закреплённом1800s. Собственные первоначальные хеши обоих payload совпали, новых endpoint tasks/ops0. Модель правильно сохранила source_audit_workflow_completed=false/source_audit_final_report_accepted=false и full-case/business/normalization/live/bug=false. Prose limitations в основном повторяет общий контракт; это не доказательство развёрнутого самостоятельного объяснения конкретной ошибки647. Original647 не исправлен и не принят.

Astra Job20261017-045536-800fa318 / tc-ac1ec0c0 / ev-370754f2d377: completed=true, также6RAW_EQUAL/0RAW_DIFFERENT/2UNKNOWN, raw/full source BLOCKED. Pair228.99s, собственные первоначальные хеши unchanged, новых задач/ops0, исходный647workflow/report false. Prose называет оба unknown-поля,6совпадений/непринятый исходный отчёт/отсутствие full-case/normalization. Обе650 — отдельные подготовленные GET continuation, не один непрерывный автономный lifecycle, не full regression acceptance. Ни одно неизвестное поле не исключено ради PASS.
