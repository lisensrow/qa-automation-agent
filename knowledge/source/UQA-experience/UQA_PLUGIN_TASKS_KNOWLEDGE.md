# UQA: плагины агента и результаты задач

## Чтение плагинов в CMDB: область поиска вкладки Agent

Reviewed experience v294, 15 октября 2026. Для проверки плагинов osAudit / inventory / plugin version / load_status в карточке КЕ важно не переносить container строки таблицы на вкладки открытой карточки. container в browser_click_semantic означает owner tr/[role=row], li или [role=treeitem], а не имя КЕ, заголовок карточки или раздел страницы.

Первичные неуспешные prepared local-model проверки: Windows Job20261015-170940-c6866286/tc-eb77f9b9 и Astra Job20261015-171119-ae15aa42/tc-dc70692d. Обе BLOCKED/repeated_missing_semantic_click, 0 операций и ресурсов. В Windows ev-93abd14b72a3 подтверждает уникальную видимую enabled вкладку Agent, semantic_strategy=role:tab и role_constraint_matched=true. Ошибка не в отсутствии вкладки или неверной роли tab. Ошибка — click с container=home-server-UC-windows10, отфильтровавшим вкладку за пределами строки таблицы; повтор после inspect остался с тем же неверным container. Это ограничение поведения UQA, не подтверждённый баг UConnect.

Рекомендация-кандидат для чтения плагинов: открыть точную карточку КЕ, заново наблюдать Agent через browser_inspect_semantic и использовать подтверждённые имя/роль без container, если owner строки/элемента списка не наблюдался. Так же заново наблюдать Plugins. Инструмент клика повторно проверяет уникальность и прежнюю policy; рекомендация не даёт разрешения ослабить неоднозначность, автоматически убрать явно требуемый scope или повторить тот же неудачный клик. После открытия Plugins вызвать штатный инспектор плагинов для точного ci_name/plugin_name. Успешная навигация и наличие записи не доказывают свежесть аудита, актуальную версию или исполнение плагина. Повторная модельная приёмка после индексирования этого рецепта оценивается отдельно.

Операторский API preflight Job20261015-171320-073339c2: Windows tc-8c6fb3e1/ev-0e541063873d, Astra tc-e860a5be/ev-03b0ccabc809. Оба reported core1.2.25/online; по45плагинов reported1.2.25/loaded=true, но audit14октября устарел. Для кампании1.3.27 готовность не подтверждена. Это исторический snapshot, не значения для подстановки в будущие тесты. Первичные ответы сохранены в evidence этого Job; обновления/задачи не выполнялись.

## Критерии текущей кампании, заданные пользователем

Zephyr-шаблоны и результаты сейчас только читаются. Названия циклов пользователь меняет сам; UQA не переименовывает их. Для логирования пользователь согласовал наличие актуальных логов и запись событий без ожидания5дней и без требования ротации50МБ. Это сокращённый критерий кампании, а не доказательство ротации. По сообщению пользователя VNC теперь работает через плагин: не устанавливать legacy TightVNC по старому шаблону; механизм ещё проверить на текущей версии. Исторические IDs/версии/данные заменять проверенными данными стенда с сохранением смысла проверки и фиксацией адаптации до исполнения. Tray-проверки этим не отменены. Пользовательское описание VNC не является runtime evidence или подтверждением разработчиком исправления бага.

Revision: installed-schema-2026-10-15-v222-v223. Reviewed installed-contract experience, не официальное руководство, не исполнение и не доказанная автономность. Первичный источник прочитан локальным GET /api/v1/docs/openapi.json; raw schema SHA256578c2f09bb95b1816b7d773209959f6e0c335abd31d2d6588406cd978a1e8082,978174bytes, OpenAPI3.1.0. При чтении15октября05:18UTC bytes совпали с v197. Product/backend/frontend/core/plugin/OS versions для этих диагностик: unknown; hash не заменяется latest или версией контейнера.

Source Job20261015-051813-7970a59b/tc-6c03ce22: ev-f694b7865fd9 (7operations/root models, SHA25679f48b13ab21b8bd365b19d87b3f98328ed296c4b8b850a4a1b4903cf0d3f539) и ev-1d857ed68da8 (6reachable model pages, SHA256e08bc65fc3cc2bc0530f3fbb62e046ee5fd037e1dc6b4fd7f7c3786fdc522e13). Execution mode operator read-only installed-schema review. Case BLOCKED,0resources/operations; бизнес-вызовы не выполнялись. Старый source197/registration не заменён.

## Плагины агента: инвентаризация, обновление и полный результат задачи

Это карта деклараций установленной схемы, не список разрешённых действий. Для реального теста нужны конкретные КЕ/агент/ОС, нужный плагин и версия из проверенного справочника, expected result и прежние policy/journal. Agent ID, CI ID, machine_uid и Task ID нельзя считать взаимозаменяемыми.

| Метод и путь | Объявленный ответ | Назначение и граница |
|---|---|---|
| GET /api/v1/agents/{uid} |200 Agent|Прочитать конкретного агента; actual version/status нужно получить отдельно.|
| GET /api/v1/agents/{agent_id}/plugin |200 AgentPlugin|Прочитать reported inventory, не запускать обновление.|
| POST /api/v1/agents/{agent_id}/plugin/update |202 Task|Запрос изменения плагинов;202 не доказывает установку.|
| GET /api/v1/agents/{agent_id}/tasks |200 Pagination_Task_|Найти задания с пагинацией, не путать чужие/старые результаты.|
| POST /api/v1/agents/{agent_id}/tasks |201 Task|Создать задание;201 не доказывает его выполнение.|
| GET /api/v1/agents/{agent_id}/tasks/{uid} |200 Task|Читать конкретное задание по двум точным IDs.|
| GET /api/v1/agents/{agent_id}/tasks/{uid}/full |200 TaskFull|Получить полный объект с result;200 и наличие поля не равны PASS.|

Все path IDs здесь объявлены string/uuid. Для list tasks присутствуют limit,offset,name,periodic,active,enabled,status,created_by. Envelope имеет count/items/limit/offset/total; одна страница не означает весь список. Отсутствие401/403 среди declared responses не доказывает отсутствия авторизации.

## Версия и загрузка плагина — разные проверки

AgentPlugin содержит agent_id,detail,last_audit_at; detail допускает array либо null. AgentPluginDetail объявляет file_name,plugin_name,plugin_version,load_status (boolean),load_error (string|null). Совпадение версии само по себе не доказывает успешную загрузку. Для actual inventory нужно сопоставить нужный plugin_name/version с load_status/error и свежестью last_audit_at по заранее заданному oracle; null не следует автоматически трактовать как доказательство отсутствия плагинов. Сами значения inventory в этих диагностических чтениях не получены.

ManageAgentPluginsPayload содержит plugins_to_update,plugins_to_delete,check_endpoint_os_version; required список пуст. Это не доказательство того, что пустой payload безопасно устанавливает все плагины. PluginToUpdate требует plugin_name и plugin_version; PluginToDelete требует plugin_name. Установка не должна незаметно превращаться в удаление. Совместимость ОС и ожидаемые версии не выводятся из названий файлов/статусов и не обходятся отключением проверки.

## Создание задания не является проверкой его результата

CreateTaskRequest объявляет required только name; additional_params/context_params допускают object|null, period/ttl — integer|null, start_ts/end_ts — date-time|null. Required{name} не заменяет правила конкретного плагина, единицы расписания или рабочий payload. Имя задания нельзя угадывать по отображаемому имени плагина.

Task.status ссылается на TaskStatus. Объявленные значения TaskStatus: created,error,success,progress,timeout; AgentStatus: online,offline,archived. Это enum declarations, не проверенная карта терминальности или бизнес-oracle. Даже status=success не доказывает совпадения actual с expected. Task.enabled в схеме integer, тогда как query enabled допускает boolean|null; не переносить типы автоматически между моделями.

TaskFull добавляет result без ограничивающей структуры в этой схеме. Нельзя заранее объявить универсальную форму JSON результата всех плагинов или считать arbitrary result корректным. Нужны совпавшие agent/task identity, фактический результат, отдельный oracle конкретного кейса и отчёт expected/actual/PASS/FAIL/BLOCKED. Не придумывать отдельный /fetch endpoint: здесь наблюдён конкретный GET .../full, а его связь с UI и фактическое получение ещё не проверены.

CommandAdditionalParams требует поле с точным написанием programm (не program); command допускает string|null, arguments — array<string>|string|null. Это структура декларации, не выбранное имя задачи, не разрешение execute command и не готовая команда для Windows/Linux. Полный набор ограничений/defaults/auth в этом профиле не экспортирован.

## Рецепт будущего ограниченного регресса

Инженерная рекомендация-кандидат: до изменения получить свежие agent identity/version/status/OS и reported plugin inventory; при точном совпадении версии и загрузки не обновлять вслепую. Если требуется установка — отдельное разрешённое изменение с точным scope/version и независимой последующей проверкой inventory/load. Затем отдельная безопасная задача, чтение её собственного результата и сравнение с locked expected. ACK/201/202/HTTP200/status=success не заменяют эту цепочку. Это план проверки, не выполненный регресс.

Complete reference closure/payload validation/authentication semantics/real inventory/installation/task execution/business PASS остаются false. Enum values экспортированы только для двух названных status моделей; семантика не подтверждена исполнением. Canonical runtime admission SSH-профиля не выполняется: существующий native GET gate не расширен. Общая память может хранить этот reviewed source и derived uqa/test_experience/hypothesis guidance, но не маскировать его под verified runtime факт продукта.
