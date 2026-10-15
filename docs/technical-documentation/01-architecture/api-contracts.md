# Установленные API-контракты и Swagger

## Плагины и задания: уточнение v222–v226

Свежее операторское чтение установленной схемы подтвердило исходный raw hash197; это свежесть schema bytes в момент чтения, не инвентаризация/исполнение и не native source admission. Job20261015-051813-7970a59b/tc-6c03ce22 содержит7operations/root models и6reachable pages, без business calls. Старый registered historical reader не изменён: его enum_values_exported=false остаётся верным. Отдельный223profile экспортирует только declared values TaskStatus(created,error,success,progress,timeout) и AgentStatus(online,offline,archived), не подтверждая семантику/терминальность/эффект.

Inventory GET /api/v1/agents/{agent_id}/plugin не равен update POST .../plugin/update202. Task creation POST .../tasks201 не равна чтению GET .../tasks/{uid}/full200 или бизнес-PASS. AgentPluginDetail содержит plugin_name/version,load_status:boolean,load_error; совпадение версии без загрузки недостаточно. Task.enabled:integer и query enabled:boolean|null различаются. CommandAdditionalParams требует точное programm. Raw source-key review226 подтвердил TaskFull.result только с title, без required и явных структурных constraints; даже это не задаёт ожидаемый формат результата каждого плагина. Нужен plugin-specific oracle.

Reviewed UQA_PLUGIN_TASKS_KNOWLEDGE.md сохраняет methods/paths/fields и ограничения. Canonical память получает только derived uqa/test_experience/hypothesis test guidance через прежний gate, не фальшивый official/runtime source. Native225advice применил рецепт к гипотетическому load failure и правильно назвал GET inventory/full; ограничения ответа неточны, actual installation/current inventory/task execution не проверялись. Это ограниченное знание контракта, не полный Swagger или рабочий регресс.

## Источники и идентичность

UQA должна отличать общий релиз продукта, версии контейнеров и hash установленной OpenAPI. Операторское чтение текущей схемы v197 подтвердило OpenAPI3.1.0:386 путей,635 операций,766 моделей. Backend image4.9.0/frontend image2.21.0 не доказывают номер общего релиза. Схема сохранена как приватная структурная проекция с hash/Job/evidence; в Git и общий рецепт сырая схема/артефакт не попадают.

## Безопасный выбор

v206: штатный OBSERVE api_inspect_contract_page использует только операторски зарегистрированный исторический источник. Persistent Job/case фиксирует стенд; origin берётся из его конфигурации. Приватный manifest связывает source ID с точным Job/case/evidence и двумя hash; модель не задаёт файл, pins или evidence IDs. Source adapter заново читает первичный evidence и проверяет provenance, размер, hash и запреты PASS. Ответы инструмента принудительно непригодны для pass/verdict в Core; регистрация не доказывает текущую схему. Операции сети, авторизация, бизнес-диспетчер и canonical promotion отсутствуют. Свежий live-native API source adapter остаётся отдельным этапом.

Модельный интерфейс также не принимает source ID: операторская регистрация должна однозначно выбрать источник для стенда. Это исключает угадывание редакции; неоднозначность блокирует чтение. Native model trial подтвердил самостоятельный выбор инструмента и чтение root operation. Переход к request/action refs модель не выполнила; полная задача остаётся BLOCKED, несмотря на техническую работоспособность source reader. Операторский8/8 context-only разбор v204 не подменяет эту границу.

Идентичность операции — минимум schema revision/hash + метод + путь, затем operationId и параметры. В текущей схеме один operationId повторяется у GET/HEAD одного пути; выбор только по нему неоднозначен. HTTP-метод не заменяет action-policy: даже наблюдённый читающий POST таблицы не делает все POST безопасными.

Определение коллекции и её пересчёт различаются; определение политики, задание политики и запуск — отдельные объекты/операции. Сохранение процедуры не доказывает выполнение графа. Приём задачи обновления плагинов не доказывает её завершение или правильность версии/ОС. Required поля OpenAPI не заменяют бизнес-валидацию, nullable не разрешает любые сочетания. Отсутствие401/403 в declared responses не доказывает отсутствие авторизации.

## Граница готовности

v204 добавляет отдельный чистый inspect_api_contract_page: одна операция или одна schema page, цепочка до8 refs от root exact method/path. Каждая ссылка обязана присутствовать в предыдущей странице; нельзя запрашивать произвольную существующую модель. Не более20 прямых refs и32KiB ответа; прежние входные бюджеты/двойные hash pins неизменны. Обход цикла, внешние ссылки, missing schema, выбранная truncation и превышения — отказ. Непосещённые siblings не расширяются и не объявляются проверенными. complete_reference_closure=false, enum_values_exported=false и прежние permission/PASS/execution/current applicability/complete payload validation=false возвращаются явно. Это не HTTP executor, model tool, полный validator или source adapter.

На установленном snapshot контракт политики, всё ещё превышающий старый full-closure лимит, порционно раскрывает request model и три модели действия. Required полей достаточно для структурного разбора, но не для безопасного конструирования политики: значения enum и часть JSON Schema ограничений не экспортированы. Первый реальный model interpretation допустил ошибку в доступности enum values; исходный FAIL сохраняется, новая явная metadata граница проверяется тем же oracle. UI список политик прочитан отдельно и сейчас пуст, поэтому назначение, расписание и эффект применения не приняты.

v198 добавляет чистый машинный наблюдатель сохранённой проекции. Он сверяет два SHA256, точный method/path template, закрытый формат и counts; возвращает параметры, request/response модели и ограниченный плоский reference graph. Не читает файлы, не делает запросы и не получает credentials; pins передаёт доверенный вызывающий, а не модель. Совпадение pins не доказывает доверие к вызывающему или свежесть источника.

Лимиты: вход1MiB/100000узлов/depth24,20 связанных моделей,32KiB ответа. Ошибки/внешние refs/обрезка/неизвестная структура/несовпадение хэшей — отказ без частичного «полного» результата. Поддержаны циклические ссылки без разворачивания и поля с именами $ref/projection_truncated. В текущем replay восемь из девяти контрактов доступны, создание политики превышает лимит; нужен порционный просмотр, не рост контекста без границ.

Профиль и реальный context-only модельный тест7/7 прошли. Это ещё не новый model tool, не source adapter, не исполнение операций и не полный JSON Schema validator. Examples/defaults/descriptions/enum values и часть ограничений исходной схемы отсутствуют; permission/PASS/execution/current applicability/auth contract/complete payload validation остаются false.

Прочитанный контракт не означает покрытие635 операций или автономное владение Swagger. Текущая проекция не включает examples/defaults/descriptions/enum values и часть ограничений JSON Schema. Она полезна для поиска метода/пути/моделей, но не для слепой генерации payload. Обязателен bounded lookup точной текущей схемы и сверка actual/expected после исполнения разрешённой операции.

После явного enum_values_exported=false та же модельная проверка прошла8/8. Это понимание операторски подготовленных schema pages, не выполнение политик и не доказательство, что UQA сама выберет эти страницы в обычном workflow. Предыдущий7/8FAIL остаётся в истории.

Существующий canonical runtime source gate не принимает произвольный SSH artifact вместо native GET; не ослаблять его ради публикации. Reviewed recipe индексируется отдельно. Поддерживаемый source adapter установленного API-контракта и модельные end-to-end проверки ещё предстоят. STEP/AUTO, v069, locked oracle и replay protection неизменны.
