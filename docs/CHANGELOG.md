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
- Собран постоянный suite из 16 архитектурных smoke-tests.
- Добавлено ограниченное model-facing представление browser tool result: полные runtime-данные сначала обрабатываются evidence/observation pipeline, а повторяющийся UI payload больше не раздувает LLM-контекст до timeout.
- Старые browser states в LLM-истории автоматически сворачиваются до результатов действий и ссылок на evidence; подробным остаётся только последнее актуальное состояние страницы.
- Navigation preflight усилен привязкой к целевой странице: случайный успешный переход больше не разрешает generic Add/Create. Для справочных сущностей добавлена детерминированная иерархия через Dictionaries-подобные разделы.
- Browser Runtime научился однозначно связывать видимую текстовую метку поля с единственным соседним input, даже если UI-компонент не объявил стандартные `for`/`id` или ARIA-связи.

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
- Контрольный lifecycle Location дошёл до правильного пути `Dictionaries → Locations` и открыл точную форму `Create location`, но был безопасно остановлен до Save: Browser Runtime не мог связать видимую метку `Name` с textbox без accessibility-связи. Добавлен универсальный fallback и отдельный regression smoke; полный lifecycle нужно повторить.
