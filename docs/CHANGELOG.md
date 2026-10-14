# История изменений UQA

Документ фиксирует завершённые архитектурные этапы и заметные исправления. Мелкие промежуточные патчи объединяются по возможности.

## v180 — короткие source-gated подсказки расположения контролов

- В атомарную память добавлены три reviewed guide declarations collections.form: name_field_panel, filter_panel, table_layout_panel. Candidate-only, explicit doc revision/hash, replay dedup; consistent DB backup и неизменность legacy rows проверены.
- При field-not-found в fill/select Core возвращает bounded control_location_hint из проверенного источника вместо переноса произвольной prose. Это данные о предполагаемой панели, не executable instruction, не permission, не role guarantee и не evidence PASS. Запрет на коллекции в task не становится collection hint.
- Domain aliases остаются в knowledge adapter, без U-Connect-specific if/else в Core; новые model tools не добавлены. STEP/AUTO, v069 и journal без изменений.
- Установленный py_compile, профиль и runner221/221 PASS (/tmp/v180-full-smoke.log). Live model trial начат отдельно; не считать его завершённым full collection workflow.

## v179 — не терять entry proof при открытии нового редактора

- В свежей operator-assisted инспекции Core сам выставлял устаревший parent navigation candidate после подтверждённого Add collection и блокировал Settings. Case tc-7ffa5738 сохранён BLOCKED, Save не нажимался.
- Generic same-session/same-origin proof теперь сохраняет навигационный контекст только при native подтверждённом клике в unsaved new/add/create descendant явно указанного раздела. Гадание URL, другой origin/session, сохранённый ID editor, ошибочный/неподтверждённый/destructive click не подходят.
- Это completion навигации, не владение ресурсом, не разрешение WRITE/commit и не бизнес-PASS. STEP/AUTO, v069 и journal/replay barriers не менялись.
- Установленный py_compile и профильный smoke PASS; полный runner и fresh live tab transition ещё проверяются.
- Fresh operator case tc-00adb3fd подтвердил Settings → config, Conditions → conditions, Table fields → view и Policies → policies без устаревшего parent candidate. Name — текстовая подпись/nearby input, не подтверждённый textbox accessible name; native required=false не доказывает business required. Пустой Name оставляет Save disabled, кнопка только инспектировалась.
- Первоначальный full runner выявил отсутствующую новую зависимость в AST-изолированном smoke_navigation_guard; whitelist обновлён без ослабления assertions. Следующий runner 220/220 PASS; финальный stable rerun после смены experience query проверяется отдельно.
- Старый запрос опыта ранжировал старый фрагмент и не находил свежую v179 карту. Выделен устойчивый раздел «Наблюдённый маршрут и поля коллекции», query без номера версии; поиск подтвердил два fresh фрагмента. Согласованные snapshots индекса сохранены до каждого обновления, остальные 1136 chunks неизменны. Полная автономная коллекция ещё не подтверждена.
- Финальная стабильная установленная версия: py_compile и runner 220/220 PASS (/tmp/v179-stable-full-smoke.log). Ошибка проверки no-Save в operator receipt helper исправлена: read-only инспекция Save не является кликом. Field/tab case PASSED только по location/entry; прежний BLOCKED case и overall campaign BLOCKED сохранены.

## v178 — свежий маршрут коллекций и recall опыта

- Guided-section model Job 20261014-202207-d0073163 BLOCKED: CMDB был придуман как container кнопки, повтор same missing click остановлен. Этот прогон не является самостоятельной навигацией или созданием.
- Operator-assisted entry Job 20261014-202554-5f8da88c: уникальный Add (button) без container → Add collection (menuitem) → /cmdb/collections/new/settings/composition. Пять вкладок наблюдены, Save не нажимался. Подтверждает только вход в новую несохранённую форму.
- Необъявленный browser_inspect_form_semantic корректно заблокирован как unknown; это ошибочное имя в диагностическом helper, не баг UC. Для отдельной native form inventory существует browser_inspect_form_validation_semantic, он здесь ещё не проверен.
- В reviewed рецепт добавлены fresh evidence IDs, объяснение section ≠ container и ограничения совместимости; коллекционный bootstrap запрашивает также indexed операторский опыт, не только руководство. Evidence_for_pass=false, STEP/AUTO и v069 без изменений.
- Установленный recall: профиль и полный runner 219/219 PASS (/tmp/v178-full-smoke.log). Повторная guided model проба 20261014-203126-d02151ff открыла новое окно правильными Add/button и Add collection/menuitem без выдуманного container, затем BLOCKED: Name отсутствует на Composition, модель не перешла на Settings и повторила неподходящий snapshot. Save не выполнялся, созданных ресурсов нет. Подтверждено использование опыта для entry, не самостоятельная навигация/создание.

## v177 — контекст политик и процедур и удержание исходной задачи

- Официальное руководство: шесть candidate declarations по типам/условиям политик и шаблонам/целям/составу на запуске/минимуму блоков процедур. Hash/revision recheck и exact replay dedup, без runtime applicability/semantic promotion.
- Первый live collection Job 20261014-195333-0cff9442 завершился BLOCKED: модель уходила в общий Add/Administration; ресурсов 0, unresolved operations 0. Это не подтверждённая способность создавать коллекции.
- Найден общий дефект: внутренние recovery сообщения user-role могли вытеснять исходную задачу навигации. Core фиксирует исходную цель на время turn; старый binding удаляется перед следующим turn. Tool payload не может стать authority. STEP/AUTO и policy не изменены.
- Профильная проверка удержания task authority PASS; полный runner и повторный live collection прогон проверяются отдельно.
- Предварительный runner 219/219 PASS. Последующее подключение коротких reviewed doc queries до managed turn и generic collections/procedures/CMDB vocabulary прошло профильные проверки/py_compile; финальный полный runner запущен отдельно. Отрицательные ограничения не являются поисковыми целями.
- Повторный Job 20261014-195822-3416e089 также BLOCKED: сохранён target, но отсутствует достаточное document grounding навигации. Новый прогон после grounding: 20261014-200343-6a9974e4; не заявлен PASS до результата.
- Финальная установленная версия: runner 219/219 PASS (/tmp/v177-final2-full-smoke.log). Jobs 20261014-200343-6a9974e4 и 20261014-201221-d9aca32c также BLOCKED по navigation/click ambiguity, созданных ресурсов нет. Следующий этап — источник опыта/known-route navigation и свежая инспекция; никаких заявлений об автономной готовности коллекций.

## v176 — ограниченное подключение declared knowledge

- knowledge_search дополнен отдельным source-rechecked declared_product_context; прежний version-scoped verified retrieval не изменён.
- Allowlisted concept/predicate/value, только candidate declared_spec без конфликта. Raw prose, bugs и upgrade advice не передаются. Изменённый source hash исключает подсказку.
- Два reviewed правила состава коллекций доступны с unknown runtime applicability, без semantic promotion и бизнес-PASS.
- Установленный py_compile и полный runner 218/218 PASS. Live model-context и автономная UI-приёмка — отдельные проверки, ещё не объявлены завершёнными.
- STEP/AUTO и v069 policy сохранены. Последовательный ночной план сохранён в UQA_OVERNIGHT_ACCEPTANCE.md.
- Live qwen3:14b context probe PASS: два правила извлечены верно, no_false_pass/recheck true. Длительность 23.12 s; не UI regression и не обучение весов. System prompt явно разделяет declared context и runtime evidence.

## v175 — формат знаний, источник, дедупликация и технический пакет

- Добавлен candidate-only atomic record v1, trusted source registry checks и additive knowledge_v1_* tables без изменения legacy facts/scopes/confirmations.
- Идемпотентные event IDs, semantic-key/value variants, bounded supports и явные conflicts; повторные runs не копируют знания.
- Официальные документы проверяются по hash/revision/applicability; native runtime источники — по exact case/evidence/observations и identity. Source integrity не является semantic promotion.
- Read-only история scope/OS/core/plugin/document versions и representative source refs; автоматически не выдаёт upgrade advice.
- Issue classification/declared fix требуют approved developer confirmation/issue ID. Fixture не становится продуктовым фактом; реальный фикс UC здесь не тестировался.
- Подготовлен self-contained technical-documentation пакет из 15 Markdown файлов, с обзором для руководителей, архитектурой, безопасностью, памятью, качеством и эксплуатацией. Основные architecture/foundation docs актуализированы.
- В профильном isolated тесте проверены 10000 повторов, provenance/developer gates, release/document history, rollback и legacy preservation. Нет новых model tools, automatic exporter, verified promotion или изменения STEP/AUTO/v069 policy.
- Установленная версия: py_compile и полный runner 217/217 PASS. Consistent production DB backup/integrity и fingerprints подтвердили неизменность legacy таблиц; два кандидата из официального руководства приняты с hash/revision, exact replay дедуплицирован. Новая схема не публикует candidate cards как verified знания.

## v172–v174 — контролируемые коллекции, целостные доказательства и общая память

- Дополнительное проектирование до внедрения: UQA_PRODUCT_KNOWLEDGE_DESIGN разделяет историю, канонические продуктовые знания и индексы; определяет дедупликацию, версии, code bindings, права и критерии приёмки. Это предложение, не реализованная capability и не новый продуктовый факт.

- Добавлена универсальная адресация контролов по строке/столбцу и нативное различение disabled до отправки от неопределённого результата после возможной отправки; STEP/AUTO и v069 policy сохранены.
- Durable журнал сохраняет auditable operator rejected/canceled reviews, без model-facing отмены и без автоматического разрешения повторов по HTTP-коду/таймауту. Исходные receipts и immutable oracle не удаляются.
- Большие JSON сохраняются целостно в пределах явных бюджетов; усечённый native response/evidence непригоден для verdict и reconciliation. Redaction сохранена.
- На lab созданы десять новых коллекций с независимой проверкой точных ID состава. Это live_operator_assisted, не автономная Ollama; старые объекты не редактировались. Отображение аппаратных RAM/CPU значений остаётся ограничением UC: None-подобный текст не принимается за число.
- По отдельному разрешению архивированы старые system journals и уменьшен journal до 256 MiB: RabbitMQ disk alarm снят без снижения порога. Удалённые старые журнальные записи восстановимы из проверенного архива; UC данные/Jobs/secrets/Docker не удалялись.
- Существующая SQLite FTS5 пополнена тремя reviewed источниками: рецепт коллекций, технический опыт и фундамент масштабирования для QA/документации/разработки/техподдержки. Штатный knowledge_search находит их; 22 новых чанка, прежние 1123 чанка не изменились; consistent backup проверен.
- index_document транзакционно обновляет один источник без пересборки остальных. Пустые/внешние/symlink источники отвергаются; knowledge не становится evidence для PASS.
- py_compile, профильные tests и полный runner 216/216 PASS. Это технические fixtures, не столько же live бизнес-кейсов и не обучение весов LLM. Автономная приёмка рецепта, typed experience schema и safe exporter всех test outcomes остаются в roadmap.
- Актуализированы QA_AGENT_ARCHITECTURE, технический план и отчёт коллекций; стратегические принципы — UQA_KNOWLEDGE_FOUNDATION.

## v078o — two-run periodic task evidence

- Для точной enabled periodic-задачи первый read-only `/full` фиксирует приватный baseline, а следующий вызов подтверждает новый запуск только при увеличившемся `processed_at`.
- Baseline связан с той же browser session, agent ID и task ID; одинаковый или более старый timestamp не считается вторым выполнением.
- В Job сохраняются только предыдущий/текущий timestamp, период и наблюдённый интервал. Результаты задачи не сохраняются.
- Режим доступен только если пользователь явно запросил periodic/два запуска; итоговый PASS формирует Core.

## v078n — user-authored private task-result assertions

- Инспектор `/full` умеет внутри trusted runtime проверить ожидаемую подстроку текстового результата и ожидаемый error code, не возвращая фактический вывод.
- Core разрешает ожидания только при их явном наличии в persistent пользовательском тексте Job; модель не может использовать инструмент для перебора скрытого результата.
- Сохраняются hash и длина ожидаемого текста, boolean-совпадения и безопасные метаданные. Фактический вывод, параметры и error message не попадают в evidence.
- PASS/FAIL формирует Core: совпавшее пользовательское ожидание даёт PASS, несовпавшее — FAIL, а простой metadata snapshot остаётся BLOCKED.

## v078m — bounded task result metadata

- На U-Connect frontend 2.21.0/backend 4.9.0 подтверждён штатный read-only GET `/agents/{agent_id}/tasks/{task_id}/full`; он возвращает сохранённый результат задачи, хотя строка списка не открывает детали.
- Новый инструмент принимает только UUID задачи из полного ранее наблюдённого списка выбранной КЕ, обращается только к тому же HTTPS origin и повторно связывает ответ с agent ID, task ID и именем.
- Модели и Job отдаются лишь безопасные метаданные результата. Произвольный вывод, параметры задачи и текст ошибки не копируются в evidence или отчёт.
- Core сохраняет metadata-only verdict: наличие результата не превращает execute command или periodic в PASS без отдельной содержательной проверки.

## v078l — exact agent task identity

- Инспектор списка задач принимает наблюдённый `task_id` для различения нескольких записей с одним именем.
- Пара `task_name` + `task_id` должна указывать на одну и ту же запись; неполный список и неоднозначность блокируются.
- Результат остаётся metadata-only: статус в списке не доказывает вывод execute command или два запуска periodic.
- На проверенной версии Agent → Tasks строка не открывает детали и клик по ней не дал нового ответа; инспекцию результата нельзя объявлять реализованной без отдельного наблюдаемого источника.

## v078k — read-only agent task-list observation

- Добавлена ограниченная инспекция Agent → Tasks по уже наблюдённому GET выбранного агента: точное имя, enabled, period, status и время последней обработки.
- Параметры задания и вывод команды не возвращаются из этого инструмента; task-list evidence не может само по себе доказать PASS выполнения или periodic.
- После прогона с отсутствующей `checkAlive` добавлены подсказки по фактически увиденным именам и защита от повтора неизменной инспекции.
- Инструкция UQA теперь направляет открывать табличную строку через доказанный exact-row маршрут; неполный вызов task-инструмента возвращает понятную ошибку вместо исключения.
- Отсутствие GET списка до открытия Agent → Tasks теперь обозначается отдельно от отсутствия задачи; Core не выдаёт одно за другое.
- Core формирует check по собственному наблюдению task-list и подавляет неверный текст модели в итоговом отчёте; без отдельного результата выполнения остаётся BLOCKED.
- Обзор списка без точного task_name свёрнут до уникальных имён и количества записей, без длинного повторения ID задач.

## v078j — inspected exact table-row navigation

- Живой read-only прогон показал, что модель после инспекции строки КЕ вызывала клик с ролью `row`, которую Runtime не поддерживал.
- Клик по `row` теперь допускается только после уникальной exact-инспекции на том же URL. Перед действием Runtime повторно находит ровно одну видимую ячейку с этим значением; неинспектированная или неоднозначная строка остаётся заблокированной.

## v078i — separate agent observation checks

- Read-only прогон Ubuntu-КЕ обнаружил смешение даты аудита плагинов со свежестью телеметрии в тексте отчёта.
- Сводки этих инструментов теперь сохраняются как отдельные структурированные observations. Core привязывает check к его собственному evidence/observation и выводит статус и факт самостоятельно; неподтверждённый текст модели не становится итоговым отчётом.

## v078h — managed self-container navigation retry

- Агентный read-only прогон дошёл до КЕ, но дважды не открыл Agent/Plugins из-за роли `tab` и container, совпадающего с самим именем цели.
- Core теперь однократно повторяет только неисполненный `INTERACT`-клик по строгому уникальному exact-name без этих неподтверждённых подсказок. Для WRITE/DESTRUCTIVE, неоднозначного элемента и чужого container fallback недоступен.

## v078f — page-scoped semantic loop guard

- Агентный прогон показал, что Core блокировал повторный поиск Plugins даже после успешного перехода в Agent.
- Защита от циклических exact-inspection теперь привязана к отпечатку текущей browser-страницы; без изменения страницы повтор по-прежнему останавливается.

## v078g — exact inspected target reuse

- Повторный прогон выявил, что модель меняла предполагаемую роль и добавляла self-container после успешной инспекции КЕ.
- Runtime повторно использует только доказанную точную цель на том же URL и делает строгую проверку единственного видимого текста непосредственно перед кликом; произвольный другой container не игнорируется.

## v078e — inspected semantic role fallback

- Read-only UQA-прогон показал: инспекция находила точную КЕ при неверной роли `link`, но следующий клик всё равно завершался `semantic_element_not_found`.
- Клик теперь допускает точный текстовый fallback только после успешной инспекции того же имени/роли/URL; неоднозначный элемент и самостоятельный клик без инспекции остаются заблокированными.

## v078d — scoped navigation preflight

- Реальный read-only прогон UQA выявил принудительный навигационный совет к generic Add даже при уже открытой CMDB; агент ушёл через меню и завершил case BLOCKED.
- Совет теперь создаётся только при явном положительном намерении Create/Add. Сохранение evidence/отчёта не считается изменением тестируемого стенда. Защита реальных операций создания сохранена.

## v078c — agent plugin audit observation

- В карточке Agent → Plugins добавлена read-only проверка наблюдённого plugin audit с точной привязкой к agent ID, имени, версии и состоянию загрузки.
- Давний audit и неполные/противоречивые данные возвращают BLOCKED, а не фиктивный PASS; текст ошибки загрузки не передаётся модели без фильтрации.
- Инструкции UQA различают загрузку пакета, установку на агенте, состояние плагина и фактическую работу VNC.

## v078b — Job-scoped artifact staging

- Добавлена проверяемая SHA-256 передача тестового пакета из ограниченного `uqa-input` сохранённого стенда в закрытое хранилище текущего Job.
- Источник связан со стендом Job; запрещены traversal, symlink-алиасы, нерегулярные и слишком большие файлы. Модель получает только artifact ID и метаданные.
- Браузер выбирает повторно проверенный пакет через точное file-поле или file chooser под существующей WRITE-policy. Сам факт выбора не считается подтверждением upload/deploy.
- Добавлены synthetic smoke-tests для регистрации, проверок целостности, ограничения стенда и выбора файла.

## v070 — Resource Lifecycle

- Добавлен универсальный persistent resource ledger внутри Job Store.
- Реализована регистрация тестовых ресурсов и восстановление cleanup после остановки процесса или модели.
- Добавлен Cleanup Manager с безопасным повтором навигации, порядком зависимостей и журналом попыток.
- Добавлена детерминированная проверка точного ресурса до и после cleanup.
- Реализованы точная работа со строкой таблицы и context menu.
- Добавлен metadata-driven REST cleanup без ветвлений по типам сущностей U-Connect.
- Destructive REST tools изолированы от обычного агента и доступны только Cleanup Manager.
- Добавлен persistent Product Blocker Registry и автоматическая постановка blocker на повторную проверку при изменении версии backend/frontend.
- Собран постоянный suite из 17 архитектурных smoke-tests.
- Добавлено ограниченное model-facing представление browser tool result: полные runtime-данные сначала обрабатываются evidence/observation pipeline, а повторяющийся UI payload больше не раздувает LLM-контекст до timeout.
- Старые browser states в LLM-истории автоматически сворачиваются до результатов действий и ссылок на evidence; подробным остаётся только последнее актуальное состояние страницы.
- Navigation preflight усилен привязкой к целевой странице: случайный успешный переход больше не разрешает generic Add/Create. Для справочных сущностей добавлена детерминированная иерархия через Dictionaries-подобные разделы.
- Browser Runtime научился однозначно связывать видимую текстовую метку поля с соседним input, даже если UI-компонент не объявил стандартные `for`/`id` или ARIA-связи. После строгой проверки общего DOM-контейнера используется ограниченная пространственная привязка к ближайшему выровненному полю.
- Managed browser-open защищён от смешения API и UI-маршрутов: первый придуманный deep link нормализуется до origin стенда, если пользователь явно не указал этот URL.
- Cleanup navigation recovery теперь использует подтверждённый URL успешного `browser_open_page` из observations, даже если пользователь сказал «текущий стенд» и URL отсутствует в тексте Job.
- Проверка REST cleanup различает удаление и архивирование: DELETE требует отсутствия точного объекта, а archive — того, что тот же единственный объект имеет подтверждённый архивный статус. Повторный cleanup уже архивного объекта завершается без второго изменяющего запроса.
- Реальный lifecycle Location подтвердил восстановление cleanup после остановки: созданный ресурс найден по точному ID, архивирован, повторно распознан как уже архивный и переведён ledger в `cleaned`. Сам test case честно завершён `BLOCKED` из-за отдельной ошибки model-side semantic role.
- `browser_inspect_semantic` теперь считает переданную role проверяемым сужающим hint: если DOM её не подтверждает, read-only inspection продолжает строгий поиск по тому же имени и явно сообщает о fallback. Это устраняет повторяющийся not-found цикл на выдуманной роли без ослабления точного совпадения имени.
- Core запоминает неуспешную точную semantic-проверку внутри case. Повтор того же имени, даже с другой придуманной role, не вызывает браузер второй раз: case детерминированно получает `BLOCKED / repeated_semantic_inspection` и сохраняет evidence первого поиска.
- Добавлен read-only `browser_inspect_table_row`: он требует единственную видимую строку с точным значением ячейки и возвращает структурированные `cells`, `headers` и `values_by_header` для evidence и verdict.
- `resource_register` больше не принимает придуманный `external_id`: Core сохраняет его только при наличии того же значения в ID-поле предыдущего tool result; иначе имя остаётся, а ID записывается как неизвестный.
- После отказа policy повтор идентичного WRITE/DESTRUCTIVE в том же case не показывает подтверждение снова и не достигает browser runtime: Core завершает case как `BLOCKED / repeated_blocked_mutation`.
- Planner Core распознаёт формулировки вида «один последовательный test case» и автоматически объединяет ошибочно разделённые моделью шаги lifecycle в один case с несколькими checks.
- Реальный Location Job подтвердил create, точное table-row evidence, persistent registration и успешный Cleanup Manager archive; ложный `external_id`, совпавший с именем, очищен из ledger. Verdict остался `BLOCKED` только из-за повторной direct-архивации после policy denial.
- Planned-check coverage допускает только детерминированное исправление ID: если модель заменила `planned-*` на свои `check-*`, но все точные уникальные titles совпадают один к одному, Core восстанавливает авторитетные IDs без fuzzy matching.
- Cleanup verifier принимает точный `browser_inspect_table_row / table_row_not_found` как post-action доказательство отсутствия табличного ресурса в активном списке. Найденная строка или неточный semantic result по-прежнему не позволяют пометить ресурс `cleaned`.
- Свежий end-to-end Location case впервые завершён с `PASS=1`: create, machine-locked table evidence и persistent registration прошли; обнаруженный разрыв table-row post-check исправлен отдельным regression smoke.
- Recovery cleanup запрещает вторую WRITE/DESTRUCTIVE-операцию, если история ledger уже содержит подтверждённую destructive mutation для этого ресурса. Повторный запуск может только подтвердить точное отсутствие или оставить ресурс pending.
- Для ресурса с provenance `table_row_exact_cell` recovery выполняет детерминированный `browser_inspect_table_row(exact=true)` до model-call: not-found закрывает ledger, найденная строка оставляет cleanup pending без повторной mutation.
- Destructive UI intent-click больше не равен выполненной мутации: если post-click state содержит одноимённую кнопку подтверждения, Core сохраняет `confirmation_pending=true` и разрешает отдельный policy-controlled confirm-click. Guard повторной mutation активируется только после `mutation_executed=true`.
- Если destructive intent-click открыл наблюдённую одноимённую confirm-кнопку, Core детерминированно вызывает её точными аргументами через второе v069-подтверждение. Модель больше не может пропустить обязательный второй шаг и преждевременно заявить cleanup.
- Browser Runtime возвращает `post_click_same_name_button_count`: этот Core-only признак обнаруживает confirm-popover даже когда общий список interactive elements пуст или сокращён.
- Для UI archive, который оставляет строку в таблице, Core выполняет точный post-check context menu и считает cleanup подтверждённым только при замене исходного действия на обратное `Unarchive`. Это не зависит от цвета статусной точки или текстового вывода модели.
- Контрольный Job `20260915-065244-a7d0dddf` завершён полностью зелёным lifecycle: case и все три planned checks — passed, resource — cleaned, cleanup — completed. Recovery подтвердил точную строку через обратное действие `Unarchive` без повторной mutation.

## v069 — General Action Policy

- Добавлена универсальная классификация `OBSERVE`, `INTERACT`, `WRITE`, `DESTRUCTIVE` и `UNKNOWN`.
- Наблюдение и безопасная навигация выполняются автоматически.
- Изменения и destructive-действия проходят через Core policy.
- Исправлен глобальный read-only detector: явно запрошенный managed workflow не блокируется из-за локального ограничения «не изменять существующие объекты».

## v047–v068 — Regression, Evidence и семантический Browser Runtime

- Добавлен regression runner с режимами STEP/AUTO и изоляцией контекста test case.
- Реализованы структурированные checks и машинный verdict `PASS`, `FAIL`, `BLOCKED`.
- Усилена связь verdict с runtime evidence; клик не считается доказательством результата.
- Добавлены observations, semantic binding, UI assertions и ограничения обязательных требований.
- Реализованы семантические browser tools, сетевые наблюдения и безопасная работа с сохранённой web-аутентификацией.
- Исправлено разбиение последовательного workflow: одна операция с несколькими критериями остаётся одним test case.

## v001–v046 — Базовое ядро и Product Knowledge

- Сформированы UQA Core, tool orchestration, управление контекстом и Job Store.
- Добавлено подключение к стендам, безопасное хранение credentials и определение идентичности стенда.
- Реализованы evidence и observation pipeline.
- Добавлены candidate facts, проверка конфликтов и продвижение подтверждённых Product Knowledge.
- Реализован индекс локальной документации с поиском по структурированным фрагментам.

## Открытые ограничения проверки

- На U-Connect backend 4.9.0 / frontend 2.21.0 отсутствует рабочий UI/API cleanup для Access Zone; blocker хранится в Product Blocker Registry.
- Контрольный lifecycle Location успешно создал и зарегистрировал точный тестовый ресурс. UI-верификация case остановлена из-за повторного предположения моделью несуществующей роли `option`; cleanup выполнил реальный archive, после чего потребовалось исправление post-check для сохранённой архивной строки.
# v071a — semantic form controls

- Добавлен универсальный выбор option для native select и ARIA combobox.
- Добавлена идемпотентная установка checkbox/switch.
- Новые действия классифицируются как WRITE и сохраняют policy v069.
- Read-only policy блокирует новые form mutations, а обязательный field/value constraint исполняется одним атомарным selection-вызовом.
- Повторный выбор уже активного значения native select не создаёт мутацию.
- Добавлен изолированный browser smoke без изменения данных тестового стенда.
- Добавлена живая матрица дальнейшего frontend-покрытия.
# v071b — radio, multi-select and autocomplete

- Добавлен идемпотентный выбор radio option с точным group scope.
- Добавлена точная установка native HTML multiple select.
- Одиночный semantic select поддерживает поисковый ARIA autocomplete.
- Все новые действия относятся к WRITE, блокируются read-only policy и входят в evidence pipeline.
- Добавлен изолированный advanced form-controls smoke.
# v071c — keyboard and focus order

- Добавлен закрытый whitelist клавиатурных действий.
- Добавлена risk-aware классификация: safe focus navigation, WRITE-capable keys и DESTRUCTIVE Delete.
- Добавлена проверка фактической последовательности Tab focus.
- Read-only задачи блокируют изменяющие keyboard events.
- Добавлен изолированный keyboard/focus smoke.
# v071d — drag-and-drop and resize

- Добавлен semantic drag-and-drop с точными source/target.
- Добавлен resize по правой, нижней и угловой границе с ограниченным delta.
- Resize проверяет фактическое изменение bounding box.
- Pointer mutations относятся к WRITE и блокируются read-only policy.
- Добавлен изолированный drag/resize smoke.
# v071e — table controls

- Добавлен ограниченный структурированный snapshot одной таблицы.
- Добавлена сортировка по точному header с проверкой aria-sort или изменения row order.
- Добавлен идемпотентный выбор checkbox точной строки без запуска bulk action.
- Добавлена пагинация с проверкой изменения row signature.
- Добавлен изолированный table-controls smoke.
# v071f — table filters and bulk preview

- Добавлен column filter, связанный с точным header по cell index.
- Добавлен идемпотентный select-all с проверкой всех видимых строк.
- Добавлен read-only bulk-action preview без возможности нажать массовую кнопку.
- Bulk mutation остаётся отдельным WRITE/DESTRUCTIVE policy action.
- Добавлен изолированный table filters/bulk smoke.
# v072a — compatibility fingerprint and history

- Добавлен read-only UI capability probe и version-independent contract fingerprint.
- Обнаруживаются HTML/ARIA adapters, semantic-name coverage, Shadow DOM и canvas.
- Compatibility snapshots сохраняются в Job Store и сравниваются с прошлыми jobs того же стенда/page key.
- Изменённые contract sections и capability gaps фиксируются явно.
- Добавлен изолированный compatibility-layer smoke.

# v072b — mandatory compatibility preflight

- После первого browser open основной regression case требует read-only capability probe до первой мутации.
- Отсутствующий snapshot возвращает обязательный OBSERVE-кандидат вместо выполнения WRITE/DESTRUCTIVE.
- Несовместимый snapshot блокирует мутацию fail-closed и сообщает capability gaps.
- Совместимый изменившийся fingerprint сохраняется в истории, но не останавливает сценарий.
- Cleanup Manager не переведён в этот guard и сохраняет собственный exact-target/v069 policy contour.
- Добавлен изолированный compatibility-guard smoke.

# v073a — ARIA multi-select and chips

- `browser_select_many_semantic` расширен с native multiple select на ARIA listbox и combobox/listbox contracts.
- Перед изменением проверяется полный набор доступных options и однозначность каждого запрошенного значения.
- Primitive атомарно добавляет отсутствующие и снимает лишние точные options, затем проверяет весь итоговый набор.
- Уже правильный набор возвращает `already_satisfied` без повторной мутации.
- Capability fingerprint теперь отдельно фиксирует ARIA multi-select contract.
- Добавлен изолированный smoke для постоянного listbox и раскрываемого chip-based combobox.

# v073b — keyboard chords and private clipboard

- Keyboard primitive получил закрытый allowlist Control+A, Undo/Redo, Shift+Enter и Alt+ArrowDown.
- Control-based chords требуют точный semantic target; неизвестные chords и прямые Control+C/X/V блокируются.
- Добавлен session-private clipboard, который не обращается к clipboard операционной системы.
- Copy не раскрывает содержимое модели, не сохраняет его на диск и блокирует sensitive-looking fields.
- Paste принимает данные только из private clipboard, проверяет exact editable target и проходит WRITE policy.
- Private clipboard ограничен 4096 символами и поддерживает явную очистку.
- Добавлен изолированный keyboard/private-clipboard smoke без доступа к пользовательскому clipboard.

# v073c — persisted drag order verification

- Добавлен read-only `browser_inspect_order_semantic` для порядка top-level list/row/option/tree/tab/draggable items.
- Inspector сравнивает полный exact order либо требуемую subsequence и возвращает первое расхождение.
- Drag primitive принимает exact order container и ожидаемый итоговый порядок, снимает order before/after и проверяет результат в том же действии.
- Несовпадение после drag возвращается как ошибка, не скрывая факт уже выполненной мутации.
- Архитектура отличает immediate UI order от persisted order: сохранение подтверждается только отдельной read-only проверкой после reload.
- Добавлен изолированный persisted-order smoke без обращения к тестовому стенду.

# v074a — table filter popovers and server totals

- Добавлен scoped filter-popover primitive для точного table header.
- Popover разрешается через `aria-controls` или единственный видимый overlay; неоднозначность блокируется.
- Поддержан точный native operator, единственное value field и точная Apply-кнопка.
- Результат разделяет submitted filter и фактическое изменение rows, не выдавая клик за доказательство server-side фильтрации.
- Добавлен read-only inspector server-side total, visible range, current page и pagination controls.
- Visible DOM row count больше не используется как замена server-side total.
- Header resolver умеет исключать вложенные buttons/inputs из имени колонки.
- Добавлен изолированный table popover/totals smoke.

# v074b — persistent cross-page table selection

- Row selection теперь сужается одной точной таблицей и не конфликтует с одноимёнными строками соседних таблиц.
- Для таблицы вычисляется устойчивый ключ из page scope без query, имени и headers; ключ сохраняется между страницами пагинации.
- Job Store получил persistent `table_selections` ledger с upsert выбора/снятия, hash полного набора ячеек, bounded page history и фильтрацией активных строк; одинаковые отображаемые имена на разных страницах не сливаются.
- После каждого успешного выбора Core возвращает полный набор выбранных строк этого case/table на всех уже посещённых страницах.
- Добавлен read-only `table_selection_list`; ledger помечен как bookkeeping-only и никогда не разрешает bulk action.
- v069 action-policy и архитектура STEP/AUTO не изменены.
- Добавлен изолированный smoke для выбора Alpha/Gamma на разных страницах, снятия Alpha и проверки нулевого числа bulk clicks.

# v075a — native temporal controls

- Добавлен semantic primitive для native `date`, `time`, `datetime-local`, `month` и `week`.
- Значение задаётся только в canonical HTML-формате и связывается с точным semantic label/metadata поля.
- До изменения проверяются browser validity, `min`, `max` и `step` на клоне control; невалидный запрос не меняет страницу.
- Повтор уже установленного значения идемпотентен, после fill проверяются фактическое value и validity.
- Primitive классифицируется как WRITE, не нажимает Save/Submit и сохраняет v069 policy.
- Добавлен изолированный temporal-controls smoke без обращения к тестовому стенду.

# v075b — native and ARIA sliders

- Добавлен semantic primitive для native range и ARIA slider.
- Проверяются exact semantic name, enabled state, min/max/current и дискретный step.
- Выход за диапазон, step mismatch, неизвестный numeric contract и более 500 шагов блокируются до изменения.
- Изменение выполняется Arrow-клавишами с учётом horizontal/vertical orientation и подтверждается повторным чтением значения.
- Primitive является WRITE и не нажимает Save/Apply.
- Добавлен изолированный smoke для native и кастомного ARIA slider.

# v075c — ARIA tree inspection and expansion

- Добавлен read-only snapshot видимых treeitems с level/expanded/selected/checked/disabled.
- Добавлен идемпотентный expand/collapse одного точного узла через ArrowRight/ArrowLeft.
- Leaf без `aria-expanded`, disabled item и неоднозначные tree/item блокируются до действия.
- Раскрытие дерева классифицируется как INTERACT и не считается выбором или Save.
- Добавлен изолированный tree-controls smoke.

# v075d — ARIA tree selection

- Добавлен идемпотентный выбор/снятие точного treeitem через Space.
- Поддерживаются только явные boolean contracts `aria-selected` и `aria-checked`.
- Отсутствующий selection contract, disabled item и неоднозначность блокируются до изменения.
- Selection классифицируется как WRITE; expand/collapse остаётся INTERACT, Save выполняется отдельно.
- Tree smoke расширен selected/checked, deselect и idempotency сценариями.

# v076a — controlled popover lifecycle

- Добавлены точное открытие, read-only inspection и закрытие popup через Escape.
- Требуется однозначная связь trigger с popup через `aria-controls`; неоднозначность блокируется.
- Инструменты не выполняют Apply/Save и проверяют фактическое открытие/исчезновение.
- Открытие наследует v069-классификацию фактического trigger: Delete остаётся DESTRUCTIVE, Apply — WRITE.
- Добавлен изолированный smoke с проверкой нулевого числа Apply clicks.

# v076b — scoped popover option selection

- Добавлен выбор единственной точной `role=option` внутри уже открытого popup, связанного через `aria-controls`.
- Требуется явный boolean `aria-selected`; disabled, отсутствие контракта и неоднозначность блокируются до клика.
- Повторный выбор идемпотентен; после клика проверяется фактический `aria-selected=true`.
- Обычный выбор — WRITE, destructive-имя option сохраняет DESTRUCTIVE; Apply/Save остаётся отдельным действием.
- Изолированный smoke расширен select, idempotency и fail-closed проверками.
- Read-only snapshot popup теперь показывает `aria-selected` для проверяемых options.

# v076c — scoped popover button action

- Добавлено точное нажатие единственной enabled-кнопки внутри уже открытого popup, связанного через `aria-controls`.
- Отсутствие popup, неоднозначная или disabled-кнопка блокируют действие до клика.
- Кнопка проходит WRITE-policy, destructive-имя сохраняет DESTRUCTIVE-policy.
- Возвращаются снимки до/после и факт клика; успешная бизнес-мутация требует отдельной проверки.
- Изолированный smoke и полный набор 34 smoke-тестов прошли без действий на тестовом стенде.

# v077a — controlled file-input fixture

- Добавлены read-only inspection точного нативного file input и выбор встроенного harmless fixture `sample-text`.
- Произвольные пути к файлам не принимаются; скрытое поле допускается только при видимой связанной метке.
- Несовпадение `accept`, disabled и неоднозначность блокируют действие до выбора файла.
- Выбор fixture классифицируется как WRITE, поскольку событие `change` может инициировать upload; backend-результат не объявляется успешным по одному факту выбора.
- Добавлен изолированный smoke без обращения к тестовому стенду.

# v077b — controlled download verification

- Добавлено ожидание фактического download от единственной точной enabled-кнопки или ссылки.
- Файл до 10 MiB сохраняется в приватных артефактах под случайным именем; содержимое не возвращается модели.
- Проверяются suggested filename, ограниченная сигнатура формата, размер и SHA-256. Без ожидаемого SHA-256 результат `metadata_only`, не `verified`.
- Действие проходит WRITE-policy; destructive-имя сохраняет DESTRUCTIVE.
- Добавлен изолированный smoke с проверкой содержимого fixture локально в тесте, без обращения к стенду.

# v077c — download structure and upload transport evidence

- Download теперь выдаёт session-only ID вместо пути; структурный inspector принимает только этот ID.
- CSV проверяется по точным заголовкам, диапазону строк и ширине записей; PDF — по числу страниц через pypdf. Содержимое не возвращается модели.
- После выбора встроенного fixture агент различает ответ 2xx/4xx на запрос, реально содержащий его байты, и отсутствие такого наблюдения.
- Наблюдённый HTTP-ответ не считается доказательством сохранения файла; нужен независимый read-only контроль после повторного открытия ресурса.
- Добавлены изолированные smoke для CSV/PDF и auto-upload через локальный fake server.

# v078a — CI agent observability

- Добавлен read-only инструмент для точной открытой КЕ: связывает UI-статус с CI/agent API и system monitoring response текущей browser session.
- Нормализует ОС, архитектуру, версию агента, идентификаторы и CPU/RAM-значения без вывода полных payload и секретных полей.
- Несогласованный статус, offline или устаревшая телеметрия дают `BLOCKED`; online со свежей телеметрией даёт PASS только для этого наблюдения.
- Добавлен изолированный smoke для online, offline, конфликта источников, stale sample и защиты от подмены CI ID.
