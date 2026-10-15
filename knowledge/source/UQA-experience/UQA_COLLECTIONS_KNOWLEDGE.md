# U-Connect: создание коллекций, RAM CPU и опыт проверки

## Просмотр существующей коллекции: привязка таблицы

Задача «открой существующую коллекцию и проверь строки» отличается от создания новой и от просмотра общей таблицы CMDB. Сначала получить текущую страницу стенда, найти точное видимое имя нужной коллекции, прочитать semantic inspector и перейти обычным кликом по этому имени. Не придумывать role/container и не открывать Add/Edit/Update ради простого просмотра. Историческое имя не доказывает текущее наличие; неоднозначность — BLOCKED, не первый match.

После перехода проверить фактический current_url: наблюдённый маршрут просмотра — /cmdb/collections/<id>. Сверить id/имя выбранной коллекции с её свежей конфигурацией и response таблицы именно этого id. Только после этого проверять строки и os_name. Общая таблица на /cmdb, даже содержащая Windows, не доказывает состав отдельной коллекции. Не копировать число строк из истории и не строить PASS по неподдерживаемым ui_assertion fields; использовать текущие observation/evidence и штатный контракт проверки.

Первичный operator-assisted proof: Job20261015-004404-02cac4d4/tc-a91b3f23, Windows-name click ev-fa7f6ef72000 (executed), saved configuration ev-9850e2ef2496, table ev-f1cfa004c66a. Оба источника текущей проверки относились к одному выбранному объекту. Это не обход action-policy и не разрешение редактировать/пересчитывать коллекцию. Версии unknown; execution_mode=live_operator_assisted_readback, evidence_for_pass=false для этого исторического рецепта.

Контрпример автономной проверки: Job20261015-011946-a64684b5/tc-949d3649 прочитал корневую CMDB-таблицу, не нажав имя нужной коллекции; итог BLOCKED, не PASS. Этот пробел нельзя считать исправленным одной публикацией рецепта: нужен новый native run локальной модели после конкретного изменения выбора памяти.

## Сохранённый Windows-фильтр и переход редактирования v194

15октября2026, live_operator_assisted, Job20261015-010502-d0b6d605/tc-6633cdea. После cog с точным owner treeitem выбрать Edit collection, role=menuitem. WRITE-подтверждение прежней v069 относится только к открытию редактора тестового объекта, не Save/Update/пересчёту. Маршрут /cmdb/collections/<owned-id>/settings/composition, затем Conditions. Ничего не заполнялось/сохранялось/пересчитывалось; resources0/operations0. Не автономная приёмка.

GET сохранённого фильтра загружается при открытии editor; последующий click Conditions может уже не содержать его. Читать фактически наблюдённый request_id в той же сессии, не угадывать endpoint. Native GET ev-b7fe086a2751 с linked observation/полным200-телом: filter.operator=must, leaves is_archived/equal/"false", ci_class/equal/"endpoint", os_name/wildcard/"*Windows*". Это конкретная сохранённая конфигурация, не доказательство всей семантики конструктора.

В каноническую product DB добавлены три observed_fact candidate collections.saved_filter: saved_root_operator, saved_leaf_fields, saved_os_wildcard. Scope unknownверсии/ОС, конкретный filter_id в conditions, feature_profile=owned-windows-collection-saved-filter. Consistent snapshot/source validation/legacy unchanged/integrity/history/exact replay dedup PASS. Нет verified promotion, business PASS или автоматического model bootstrap этих predicate. Частный пример не является универсальным определением Windows/Linux.

## Повторная проверка составов и меню редактирования v193

15 октября 2026, execution_mode=live_operator_assisted_readback. Job20261015-004404-02cac4d4; актуальные версии сервера/frontend/ядра/плагинов unknown, прежние версии не переносились. Native GET списка подтвердил десять campaign-owned коллекций, все manual/clear_on_update=true. Case tc-a91b3f23 прочитал полный ответ таблицы каждой коллекции; audit ev-3496342a49b5 проверил уникальные ID и count/total. All=4, Windows=1, Ubuntu=1, Linux=3, Astra=1, RED OS=1; четыре аппаратные коллекции содержат те же четыре ID. ОС-подмножества непересекаются и покрывают All; Linux равен Ubuntu/Astra/RED именно в этой лабе, не всем возможным Linux. Независимый свежий полный GET Endpoint tc-c325f40a/ev-fc5460c6de0f подтвердил точное совпадение четырёх ID с All.

Все16 ячеек ram.size/cpu.core_count четырёх аппаратных коллекций содержат None-подобный текст, не числа. Состав не доказывает отображление метрик или пороги; условия и исходный RAM/CPU inventory заново не проверены. Это наблюдаемое ограничение, не developer-confirmed bug/fix.

Шестерёнка существующей коллекции открывает меню, не Settings. В tc-c325f40a диагностическая DOM-привязка ev-16b93a2ff3b4 установила owner li/role=treeitem с точным именем тестовой Windows-коллекции. Голый cog неоднозначен (два native matches): нельзя брать первый match. Штатный клик с фактически наблюдённым owner container открыл Edit collection и Update collection, оба menuitem (ev-cd9542aeaeb9). Update collection не является переходом редактирования. Edit collection по прежней policy — WRITE; его не нажимали. Save/Update/пересчёт не выполнялись. Исторический рецепт не отменяет текущую инспекцию/policy.

Новых ресурсов/операций изменения нет; autonomous_acceptance=false, business_oracle_complete=false, evidence_for_pass=false. Job остаётся BLOCKED для полной приёмки. Это операторское чтение и рецепт, не самостоятельное создание коллекции локальной моделью.

## Метаданные и границы рецепта

record_id: uc.collections.recipe.2026-10-14.v1; schema_version: 1; knowledge_kind: recipe/test_experience; execution_mode: live_operator_assisted; validation_status: observed exact membership; evidence_for_pass: false; review_date: 2026-10-14.
Область: текущий lab, четыре Endpoint Windows/Ubuntu/Astra/RED OS. Наблюдённые container tags backend 4.9.0 и frontend 2.21.0, ядра агентов 1.2.25; это не доказательство общей версии продукта или совместимости любой будущей версии. Перед выполнением заново проверить текущие UI/API, права, версии и данные.
Источники: «UC Руководство пользователя от 06.07.2026», раздел коллекций; «UC API svn от 29.06.2026»; native network evidence Job 20261014-141458-054a6654; серверные схемы и renderer прочитаны без изменений. Ни рецепт, ни этот опыт не разрешают WRITE и не доказывают автономное выполнение LLM.

## Наблюдённый маршрут и поля коллекции

Порядок вкладок, свежая operator-assisted инспекция v179: Job 20261014-202554-5f8da88c, case tc-00adb3fd. После открытия нового editor сначала точным наблюдённым текстом Settings перейти на /settings/config (ev-ddf697dc70b5): там Name, Launch type, Group и Clear when update. Не искать Name или фильтр CI class на Composition — это таблица состава, не настройки фильтра. Name в этой версии найден как текстовая подпись, requested textbox role не подтверждён; native inventory имеет input type=text с label_hint=name, не доказанный accessible name. Native required=false и отсутствие invalid controls не доказывают бизнес-валидность Save (ev-249ad4e7f2da).

Условия задаются на Conditions (/settings/conditions, ev-01013983afb7): отображаются Logical operator, группы атрибутов Common/Component parameters/Endpoint/Agent и аппаратные классы, затем Attribute/Aggregation type/Operator/Value. Native inventory показывает Search for attributes, а не готовый CI Class combobox (ev-b78b9f88a3c4); сначала исследовать реальные доступные атрибуты, после выбора — соответствующую строку условий, не выдумывать поля. Table fields (/settings/view, ev-6b70034c6f3d) задаёт Columns отдельно от фильтра; Policies (/settings/policies, ev-e1023d9fbe9f) в этой инспекции показывает пустую историю. Save с пустым Name после посещения Table fields был visible=true, enabled=false (ev-959cf2803926). Все вкладки просмотрены без заполнения, сохранения, создания или назначения политики. Это наблюдение текущего editor, не гарантия другой frontend версии, не автономный полный workflow.

Свежая операторская проверка v178, 14 октября 2026: Job 20261014-202554-5f8da88c. На странице /cmdb уникальная кнопка Add найдена browser_inspect_semantic с role=button (ev-58894473c8ac). Клик этой кнопки без container открыл меню Add group / Add collection (ev-79f5c40662cf). Уникальный пункт Add collection найден как role=menuitem (ev-337031fd7305), затем обычный подтверждённый клик открыл /cmdb/collections/new/settings/composition и вкладки Composition, Conditions, Table fields, Settings, Policies (ev-35e2db47e942). Save не нажимался, запись не создавалась. CMDB — название раздела/маршрут, а не доказанный labelled container кнопки; нельзя придумывать container="CMDB" или role="button" для пункта меню. Перед кликом заново инспектировать точное имя/роль в текущем UI, не считать исторический рецепт доказательством совместимости другой версии. Это operator-assisted entry proof, не автономное создание коллекции.

## Как создать коллекцию через фронт

Коллекции: назвать новое уникальное имя; проверить отсутствие этого имени в полном исходном списке. Указать Archived = No и CI class = Endpoint. Посетить Composition, Conditions, Table fields, Settings и Policies. Не назначать политику без отдельного разрешения. Table fields должны инициализировать layout; просто открыть форму и заполнить имя недостаточно — Save может оставаться disabled.
В наблюдённой форме после просмотра Table fields кнопка Save стала активной. Disabled означает отказ до отправки, но только нативное доказательство адаптера позволяет not_sent. Нельзя повторять Save из-за обычной строки ошибки или отсутствия XHR-ответа.
Выбор Manual подходит для явного пересчёта. Auto не заменяет Manual: текущий backend отвергает POST пересчёта немануальной коллекции до отправки команды. Auto-обновление в этом опыте не проверено.
После сохранения получить новый ID, записать ресурс и новый фильтр в ledger; зависимость collection → filter. Сохранение/ACK не равно PASS: отдельно проверить настройки, полный состав и строки таблицы по точным CI ID. При timeout не повторять мутацию, сначала читать состояние и разрешать intent по его immutable oracle.

## Логика условий и состава

Состав = автоматический набор плюс ручные включения минус исключения. clear_on_update=true пересчитывает состав; false накапливает ранее вошедшие машины. Не использовать накопление для точного моментного фильтра. must — все условия; should — хотя бы одно; must_not — исключения. Сгруппировать OS-альтернативы внутри общего must, чтобы не включить архивные или не-Endpoint объекты.
All: is_archived equal "false" AND ci_class equal "endpoint". Windows: дополнительно os_name wildcard *Windows*. Ubuntu: *Ubuntu*. Linux в наблюдённом стенде: should(*Ubuntu*, *Astra*, *RED*) внутри общего must. Это три наблюдённых Linux-дистрибутива, а не универсальное распознавание всех будущих Linux; при добавлении ОС обновить правило по текущим данным.
Аналогично Astra *Astra*, RED OS *RED*. Wildcard выбирать после чтения реальных os_name, а не предполагать значения. Сейчас составы: All 4, Windows 1, Ubuntu 1, Linux 3, Astra 1, RED OS 1.

## RAM: агрегаты, единицы и отсутствие данных

RAM Size в наблюдённом CMDB — байты, поля дочернего CI detail.size. У всех четырёх машин один наблюдённый RAM CI size=2147483648. Для суммарной памяти использовать SUM(size) по дочерним ram с is_archived=false; порог 2 GiB = 2147483648 байт. Не складывать память разных компьютеров в одно сравнение.
RAM inventory: value_count(size) >= 1, ram child filter. RAM 2GiBPlus: sum(size) >= 2147483648, тот же child filter. Оба фактически включили ровно четыре ожидаемых ID. Это аппаратный объём, НЕ процент загрузки RAM. Отсутствие значения не равно нулю и не даёт права домыслить объём.

## CPU: не спутать CI, ядра и текущую нагрузку

CPU inventory: value_count(core_count) >= 1 по дочерним cpu с is_archived=false. CPU 4PlusCoresPerCI: max(core_count) >= 4 по тому же фильтру. У каждой машины наблюдены четыре CPU CI, каждый с core_count=4. Не объявлять это 16 физическими ядрами: семантика этих записей отдельно не подтверждена. MAX проверяет характеристику одной дочерней записи. Оба фильтра включили четыре ожидаемых машины.
Текущий процент нагрузки CPU, временная серия и freshness телеметрии здесь не тестировались. Для условия по нагрузке нужны отдельные источник/единицы/время/oracle; аппаратный фильтр его не заменяет.

## API наблюдения, а не универсальная встроенная команда

Текущий фронт использует proxy /api/v1/u-auth/u-sys/api/v1. Native GET /cis?ci_class=ram|cpu&parent_id=<root>&is_archived=false&limit=0 даёт аппаратный inventory. GET /ci-collection?limit=0 и /ci-filters?limit=0 дают списки; проверять offset=0,total=count=len(items). Новые filter/collection создавались POST; POST /ci-collection/<new-owned-ID> пересчитывал только новую коллекцию, ACK 202. GET /ci-collection/<ID>/items?limit=0 проверяет весь состав, CI membership IDs находятся в ci_id, order начинается с 1.
POST /ci-collection/<ID>/table?offset=0&limit=50 в наблюдённом frontend — read query, не команда агента. POST вообще нельзя автоматически считать read-only; требуется подтверждённый контракт конкретного endpoint. Условия агрегатов: field,size или core_count; type=sum/value_count/max; operator=gte; value numeric; вложенный filter ограничивает класс дочернего CI.

## Важное ограничение полей таблицы RAM CPU

Префикс child_ в advanced search НЕ является именем столбца коллекции. Renderer таблицы использует class.field: ram.size и cpu.core_count, а условия и table layout — разные контракты. Простое HTTP200 и наличие ключа столбца не доказывают отображение метрики.
В этом lab после выбора ram.size и cpu.core_count таблица возвращает текст "None" или "None, None, None, None", хотя отдельный native RAM/CPU inventory содержит числа. Это наблюдённое ограничение отображения, не подтверждение нулевой памяти/ядер, не успешный показ метрик. Причина окончательно не установлена; UQA не меняла backend/frontend UC. Составы аппаратных фильтров проверены отдельно; отображение значений требует доработки/перепроверки продукта. Запрещено принимать None-подобный текст за заполненное числовое поле.

## Инфраструктурная ошибка, восстановление и неудачные гипотезы

В ходе работы истекла web-сессия (419/428/login); повторное открытие/auth восстановило доступ. Другой блокер — RabbitMQ disk alarm: 4.6 GiB свободно при пороге 5000000000 байт, publishers blocked/blocking, пересчёт timeout. Refresh страницы это не устраняет. После отдельного разрешения архивированы старые system journals, journal сокращён до 256 MiB; свободно 5.4 GiB, alarm исчез, 23 соединения running. Уже отправленный refresh завершился, не отправлялся повторно. Не копировать очистку как автоматический рецепт; сначала диагностика, конкретное разрешение, проверяемый архив и сохранение защитных порогов.
Native confirm probe dialogs=[] не доказывает отсутствие мутации. XHR response list не является списком всех начатых запросов. Старый oracle order=0 был ошибочным; он сохранён, а не переписан для PASS. Исторический intent завершён auditable operator cancellation, текущее состояние доказано отдельным native GET. Последующие intents используют наблюдённый order=1 и независимо сравнивают весь набор ID.

## Результат опыта и следующий прогон

Десять новых uqa-test-collections-01–10 сохранены для пользователя, Manual/clear_on_update=true. Старые объекты не редактировались, политики не применялись, задачи агентов не запускались. Создание помогал выполнять оператор через настоящие Core approvals/journal, не автономная Ollama. Этот рецепт доступен через knowledge_search после индексации; повторное чтение рецепта и его автономное исполнение — разные проверки.
Для следующего LLM прогона: получить разрешение и точный expected; найти рецепт; перепроверить identity, поля и значения на текущем стенде; использовать semantic controls и штатную policy; сохранять intent до отправки; при неопределённости не дублировать; сравнить точные ID и фактические значения; сформировать expected/actual/статус. Не добавлять новые коллекции только ради повторного обучения без разрешения.
