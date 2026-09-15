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
