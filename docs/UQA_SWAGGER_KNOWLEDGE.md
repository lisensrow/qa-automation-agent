# U-Connect: установленная схема Swagger OpenAPI

## Редакции после обновления и явный выбор источника v260–v268

После обновления 15 октября 2026 зарегистрирована отдельная редакция lab-installed-contract-20261015-v260-post-update:426paths/681operations/839schemas. Raw schema SHA256292242e76b9e8c40208e39d9841ffbc0cefcba96bc7ab688a67f53895f33acbb, projection SHA256fdb521fb5220e4d9fc38740f05c4208789304882c3101c4db072660af8b9bbe3; Job20261015-120022-69c9d724/tc-390bb2ac/ev-4d24d6b6f8bf. Старый v197 источник сохранён. Это две исторические operator-installed-schema редакции; свежесть текущего runtime, execution, semantic/PASS и совместимость другой версии не подтверждены. Версии продукта/frontend/ядра/плагинов/ОС новой редакции unknown.

С v268 OBSERVE api_inspect_contract_page имеет optional source_id: только точный зарегистрированный ID того же стенда. При нескольких редакциях вызов без source_id возвращает not_unique и available_source_ids. Выбери требуемую редакцию по задаче и повтори только read-only lookup с этим ID; сохраняй тот же ID при обходе request/response refs. Не выбирать latest молча, не смешивать схемы разных редакций и не выдавать выбор исторической записи за текущую применимость. Если caller закрепил api_contract_source_id в requirement, Core подставляет его и отклоняет замену. Stand также привязан к persistent Job/case. Модель не передаёт пути файлов, pins, исходные Job/evidence или URL; эти связи остаются операторскими.

Первый native lookup после добавления второй редакции Job20261015-121146-fb7855bc вернул два not_unique: тогда model schema не давала source_id, хотя Python reader его поддерживал. Этот BLOCKED не свидетельствует о недоступности UC; исправлено подключение выбора зарегистрированной редакции, не защита источников. Новая модельная проверка оценивается отдельно, без переписывания старого результата.

Root request модели обеих редакций: POST /api/v1/policy → CreatePolicyPayload (required name/type/action), POST /api/v1/procedures → CreateProcedureRequestPayload (name/xml). Свежий отдельный raw-schema read подтвердил defaults is_active=true/active=true; структурный lookup по-прежнему defaults НЕ экспортирует, поэтому нельзя приписывать ему это знание. Для будущего создания нужны explicit false, точный scope и самостоятельные saved/execution oracle, не только валидная структура.

## Установленная схема Swagger OpenAPI: источник и область

15октября2026, v197, execution_mode=operator_installed_schema_read, validation_status=structural_census_only, evidence_for_pass=false. Источник — HTTP200 фактически установленного backend по пути /api/v1/docs/openapi.json; адрес установлен чтением api/app.py, не перебором endpoint. Backend container u-backend:4.9.0, frontend container u-frontend-prime-ui:2.21.0; product_release/ОС/версии ядра/плагинов unknown. Container tag не равен номеру общего релиза продукта.

Raw schema SHA256: 578c2f09bb95b1816b7d773209959f6e0c335abd31d2d6588406cd978a1e8082, bytes978174, OpenAPI3.1.0. Получены386 paths,635 operations,766 component schemas: GET302,POST153,PUT99,DELETE80,HEAD1. Job20261015-012947-b938acd8/tc-3fa058b8/ev-90768490c112 содержит безопасную структурную проекцию. Её SHA256 6cf003311a91b9e9725c9843f5416d03bf7056360fcc78626ca48e14d0cada5f. Runtime artifact приватный, не коммитится; examples/defaults/descriptions/auth values не экспортировались. Это не проверка работы635 операций.

## Выбор операции: метод плюс путь, не только operationId

### Зарегистрированный исторический источник: штатный lookup v206

История v206: api_inspect_contract_page был OBSERVE инструментом одного зарегистрированного исторического источника; его модельные аргументы ограничивались method/path/reference_chain и optional stand. Source ID тогда отсутствовал в model schema, неоднозначность давала отказ. С v268 это ограничение выбора редакции изменено, см. раздел выше. Запрет model filesystem paths/pins/исходного evidence и обязательная привязка stand сохранены.

Source adapter сверяет origin конфигурации стенда, точные исходные Job/case/evidence, provenance operator_installed_schema_read и два SHA256. Содержимое первичного evidence читается заново; его собственные pass/verdict flags должны быть false. Нет HTTP/fetch/authentication/отправки задач. Tool result содержит reference page и источник; current_schema_recency_verified=false, execution_mode=registered_historical_operator_schema_snapshot. source_registration_verified означает регистрацию/проверку байтов, не текущую совместимость. Source gates атомарной памяти не изменяются. Core явно сохраняет usable_for_pass/verdict=false для ВСЕХ ответов этого инструмента, включая отказ и успешный lookup.

Поддерживается только исторический operator-schema профиль, не live native schema ingest. Регистрация lab snapshot v197 опирается на Job20261015-012947-b938acd8/tc-3fa058b8/ev-90768490c112 с прежними schema/projection hash; это не публикация самого артефакта в Git и не пересчёт свежести по времени регистрации. Модель должна читать operation root, затем переходить только по фактически раскрытым refs; required/nullable/enum_count не разрешают произвольные payload или действия. Не представлять технический source lookup как самостоятельное создание/применение политики.

Native Core trial после удаления модельного source_id: Job20261015-025942-d516fede/tc-53f3adf8. Tool ev-4234259db288 самостоятельно выбран моделью через каталог и успешно прочитал root POST /api/v1/policy; audit ev-b22970b173e3. У Core evidence usable_for_pass/verdict=false. Модель не сделала следующего lookup раскрытых request/action refs, поэтому обязательные поля по этим страницам в данном прогоне не доказаны. Общий Job BLOCKED, resources0/journal0; это ограниченный native lookup, не полная автономная работа со Swagger или политикой. Предыдущие source_id=lab failures сохранены отдельно.

Актуализация v206: более ранние разделы о том, что model tool/source adapter ещё отсутствует, описывают v197–v204. Теперь реализован только зарегистрированный ИСТОРИЧЕСКИЙ source tool с запретом verdict; свежий live-native schema adapter и полная автономная цепочка reference pages остаются незавершёнными.

## Выбор операции: метод плюс путь, не только operationId — правило

### Диагностика режима рассуждения v207: не улучшение автономного lookup

Job20261015-030909-843fa440/tc-fb302ca3, audit ev-cda2e37d0442: тот же user request, process-local UQA_THINK=1, никаких новых hints/операторской подготовки страниц/постоянной конфигурации. API tool calls=0, все source/action execution claims false, Job BLOCKED/resources0/journal0. Захвачены неизменённые ответы модели для аудита, а не только её итоговый текст. Индекс рецепта обновлялся после baseline v206, поэтому это не изолированное причинное сравнение режима. Нельзя приписывать различие только think или включать режим повсеместно по этому результату.

Модель вместо lookup построила BLOCKED-report и смешала документные concept labels с точными API enum names, хотя значения enum не экспортированы. Отсутствие успешного вызова не объяснять недоступностью сервера: tool не был вызван. Source registration и parser от этого не стали неработоспособными. Не повторять тот же прогон и не записывать неточный ответ как подтверждённый факт о продукте. Default think-off не изменён; лучший прежний native результат всё ещё root-only, не полная reference-chain приёмка.

В схеме есть один повтор operationId: get_update_api_v1_agents_update_head используется для GET и HEAD /api/v1/agents/update. Поэтому operationId не является однозначным ключом вызова: сверять также метод, путь, параметры и текущий scope. Это наблюдение схемы, не developer-confirmed bug. Ни GET, ни наличие операции в Swagger сами по себе не дают разрешения на её выполнение.

## Большой контракт политики: ограниченные страницы v204

inspect_api_contract_page читает одну operation page или одну schema page по цепочке локальных refs, проверенных от operation текущей pinned проекции. Method+path и оба hash обязательны в каждом вызове. Пустая цепочка возвращает operation/root refs; следующий ref должен быть непосредственно доступен с предыдущей страницы. Максимум8 звеньев,20 прямых refs на страницу,32KiB output; вход1MiB/100000nodes/depth24. Запрещены jumps к произвольной существующей схеме, внешние/missing refs, выбранная truncation и циклическая цепочка. Брать другую ветвь можно только начиная с её корректного общего префикса. Непрочитанные ветви не объявляются проверенными: complete_reference_closure=false; enum_values_exported=false явно указывает, что enum_count не раскрывает допустимые значения. Все прежние permission/PASS/execution/current applicability/complete payload validation flags=false. Нет filesystem/HTTP/dispatch/model tool/source adapter; pins не доказывают свежесть или authority.

Snapshot replay той же установленной схемы v197, source Job20261015-012947-b938acd8/ev-90768490c112, после metadata audit: Job20261015-023335-00ac7909/tc-d2535a5e/ev-98c0c9d68243. Старый full closure по-прежнему отклоняет POST /api/v1/policy как reference_closure_budget: лимит20 не поднят. Порционно прочитаны operation, CreatePolicyPayload и пять прямых моделей. Required создания: name,type,action; action предлагает PolicyActionAgentConfig/PolicyActionAgentPlugin/PolicyActionAgentTask. Plugin action требует force_update; task action name/data; LogicalModule-Input operator/items. Наличие остальных optional полей не доказывает допустимость любого payload. PolicyType содержит enum_count, не значения: не придумывать числовой/string discriminator из количества, имени модели или старого UI.

Первый context-only qwen trial tc-07e22ea7/ev-75cf53bee90b дал7/8: ошибочно объявил значения enum доступными. Исходный FAIL сохранён; после добавления явного enum_values_exported=false повторяется тот же oracle, не более мягкий. Это не execution test и не developer-confirmed баг UC. Версии/ОС/ядро/плагин для текущей применимости неизвестны; старые container tags не заменяют свежую проверку.

Итог повторной проверки того же oracle с явным enum_values_exported=false: tc-5c5ca907/ev-ae4e013959d6,8/8 context-only checks PASS, без действий, не автономная API-приёмка. Первый7/8FAIL не переписывается; это исправление полноты машинного описания проекции, не новое знание допустимых enum значений и не разрешение конструировать/исполнять payload.

## Коллекции политики процедуры плагины: карта контрактов

| Метод и путь backend | Назначение контракта | Body / ответ по схеме |
|---|---|---|
| GET /api/v1/ci-collection | Список коллекций | limit,offset и фильтры;200/422 |
| POST /api/v1/ci-collection | Создание коллекции | CreateCICollectionRequestPayload;201/422 |
| GET /api/v1/ci-collection/{uid} | Одна сохранённая коллекция | path uid UUID;200/422 |
| PUT /api/v1/ci-collection/{uid} | Изменение конфигурации | UpdateCICollectionRequestPayload;200/422 |
| POST /api/v1/ci-collection/{uid} | Пересчёт состава, не редактирование | body не объявлен;202/422 |
| POST /api/v1/ci-collection/{uid}/table | Таблица коллекции | optional body, limit/offset;200/422 |
| GET /api/v1/ci-filters/{uid} | Сохранённый фильтр | uid UUID;200/422 |
| GET /api/v1/policy | Список политик: singular policy | limit/offset, id/name/type/is_active и другие фильтры;200/422 |
| POST /api/v1/policy | Создание определения политики | CreatePolicyPayload;201/422 |
| POST /api/v1/policy-job | Создание задания политики | CreatePolicyJobRequestPayload; отдельный объект |
| POST /api/v1/policy-job/{uid}/run | Отдельная операция запуска задания | Не проверялась исполнением |
| GET /api/v1/procedures | Список шаблонов процедур | order_by,limit,offset,id,active,name;200/422 |
| POST /api/v1/procedures | Сохранение шаблона процедуры | CreateProcedureRequestPayload;201/422 |
| POST /api/v1/agents/{agent_id}/plugin/update | Отправка задачи управления плагинами | ManageAgentPluginsPayload;202/422 |

В браузере ранее наблюдался proxy prefix /api/v1/u-auth/u-sys перед backend /api/v1/... . Это разделение адресов, не право выдумывать новые proxy routes: перед вызовом сверить фактический UI network/схему, origin и авторизацию. POST таблицы нельзя распространить на остальные POST как «только чтение». Пересчёт202 и отправка plugin task202 означают приём команды, не бизнес-PASS; нужны завершение, fetch/результат и точный oracle.

## Требуемые поля не равны всей бизнес-валидации

CreateCICollectionRequestPayload требует name/launch_type; содержит ci_filter_id,clear_on_update,layout. Это не отменяет требований UI к вкладкам и не доказывает допустимость произвольного фильтра.

CreatePolicyPayload требует name/type/action; action — одно из PolicyActionAgentTask/PolicyActionAgentPlugin/PolicyActionAgentConfig. is_active и execution_condition присутствуют. Не считать новый объект неактивным по умолчанию: defaults в проекцию не включены. Создание определения, назначение/расписание PolicyJob и реальный запуск — разные проверки.

CreatePolicyJobRequestPayload требует policy_id/launch_type; содержит ci_collection_id,ci_id,crontab,one_off,run_at. Наличие nullable полей не доказывает допустимость любого сочетания целей/расписаний.

CreateProcedureRequestPayload требует name/xml; содержит active/debug/description. Сохранённый XML не доказывает запуск, соответствие контекста блоков или результат на КЕ.

ManageAgentPluginsPayload содержит check_endpoint_os_version,plugins_to_delete,plugins_to_update; required список отсутствует. Это НЕ разрешение отправить пустой body или обновить всё. Точные типы, значения, совместимость ОС/ядра/плагина и семантика пустого списка должны быть проверены перед разрешённым scoped WRITE. Никаких плагинов в v197 не обновляли.

## Ограничения и продолжение

Проекция содержит типы, required, refs, параметр names/in, request/response структуры и коды. Enum values, defaults, examples, descriptions, часть JSON Schema constraints и глубокие конструкции намеренно не экспортированы; она не заменяет полный валидатор payload.401/403/runtime errors могут не быть перечислены в OpenAPI: отсутствие кода не доказывает отсутствие проверки доступа.

Это операторское чтение контракта, не автономная работа модели со Swagger. В FTS публикуется только reviewed рецепт; native runtime source gate канонической DB не ослабляется ради SSH-снимка. Прямой canonical admission такого контракта и bounded schema lookup для модели требуют отдельного поддерживаемого source adapter. Не маскировать этот artifact под browser_get_network_detail и не объявлять635 endpoint проверенными. Следующий шаг — безопасный read-only выбор операции локальной моделью с проверкой method/path/parameters и последующим реальным чтением разрешённого scope; WRITE только через прежние policy/journal.
