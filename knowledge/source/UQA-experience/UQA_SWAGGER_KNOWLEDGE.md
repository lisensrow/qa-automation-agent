# U-Connect: установленная схема Swagger OpenAPI

## Установленная схема Swagger OpenAPI: источник и область

15октября2026, v197, execution_mode=operator_installed_schema_read, validation_status=structural_census_only, evidence_for_pass=false. Источник — HTTP200 фактически установленного backend по пути /api/v1/docs/openapi.json; адрес установлен чтением api/app.py, не перебором endpoint. Backend container u-backend:4.9.0, frontend container u-frontend-prime-ui:2.21.0; product_release/ОС/версии ядра/плагинов unknown. Container tag не равен номеру общего релиза продукта.

Raw schema SHA256: 578c2f09bb95b1816b7d773209959f6e0c335abd31d2d6588406cd978a1e8082, bytes978174, OpenAPI3.1.0. Получены386 paths,635 operations,766 component schemas: GET302,POST153,PUT99,DELETE80,HEAD1. Job20261015-012947-b938acd8/tc-3fa058b8/ev-90768490c112 содержит безопасную структурную проекцию. Её SHA256 6cf003311a91b9e9725c9843f5416d03bf7056360fcc78626ca48e14d0cada5f. Runtime artifact приватный, не коммитится; examples/defaults/descriptions/auth values не экспортировались. Это не проверка работы635 операций.

## Выбор операции: метод плюс путь, не только operationId

В схеме есть один повтор operationId: get_update_api_v1_agents_update_head используется для GET и HEAD /api/v1/agents/update. Поэтому operationId не является однозначным ключом вызова: сверять также метод, путь, параметры и текущий scope. Это наблюдение схемы, не developer-confirmed bug. Ни GET, ни наличие операции в Swagger сами по себе не дают разрешения на её выполнение.

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
