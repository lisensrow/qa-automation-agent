# История изменений UQA

Документ фиксирует завершённые архитектурные этапы и заметные исправления. Мелкие промежуточные патчи объединяются по возможности.

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
