# Матрица возможностей frontend-тестирования UQA

Статус документа: живой план покрытия ручных frontend-задач. Обновляется вместе с агентом.

## Реализовано

- Открытие страниц и безопасная семантическая навигация.
- Read-only inspection видимости, enabled/disabled и основных ARIA/DOM-состояний.
- Точное заполнение текстовых, поисковых и числовых полей.
- Выбор значения native select и ARIA combobox без ручного угадывания option.
- Идемпотентная установка checkbox/switch в `checked=true/false`.
- Идемпотентный выбор radio option внутри именованной группы.
- Точная установка полного набора native HTML multi-select.
- Точная установка полного набора ARIA multi-select и chip-based combobox.
- Выбор единственной точной option в поисковом ARIA autocomplete.
- Native date/time/datetime-local/month/week с проверкой canonical value, min/max/step и фактического результата.
- Native range и ARIA slider с точным bounded keyboard stepping и проверкой итогового значения.
- Read-only ARIA tree snapshot и точный идемпотентный expand/collapse узлов.
- Идемпотентный WRITE-выбор treeitem через явный aria-selected/aria-checked contract.
- Lifecycle aria-controls popup: открыть, read-only inspect, закрыть через Escape без Apply.
- Scoped выбор единственной ARIA option внутри открытого popup с проверкой aria-selected и отдельной WRITE-policy.
- Точное нажатие единственной кнопки внутри открытого aria-controls popup с WRITE/DESTRUCTIVE-policy и снимком до/после.
- Read-only inspection нативного file input и WRITE-выбор встроенного безопасного текстового fixture с проверкой выбранного имени, MIME и размера.
- Контролируемое скачивание через точную кнопку/ссылку с проверкой имени, ограниченной сигнатуры формата, размера и SHA-256 без раскрытия содержимого.
- Проверка фактического forward Tab focus order.
- Ограниченные keyboard actions с отдельной классификацией риска.
- Закрытый allowlist keyboard chords и session-private clipboard для безопасных copy/paste проверок.
- Drag-and-drop между точными semantic endpoints.
- Exact/subsequence order snapshot и проверка порядка сразу после drag и после reload.
- Resize панели или колонки с проверкой bounding box до и после.
- Структурированный снимок таблицы, сортировка, выбор точной строки и проверяемая пагинация.
- Column filters, select-all и read-only bulk-action preview.
- Filter popovers и read-only server-side total/range/current-page metadata.
- Cross-page выбор точных строк с persistent selection ledger без запуска bulk action.
- UI-contract fingerprint, adapter discovery и persistent compatibility history.
- Обязательный compatibility preflight перед первой мутацией и fail-closed блокировка несовместимого UI.
- Проверка точной строки таблицы и работа с её context menu.
- Фиксация screenshot, browser state, XHR/fetch и console/network errors.
- Action policy v069 для OBSERVE, INTERACT, WRITE и DESTRUCTIVE.

## Следующие этапы frontend-покрытия

1. Другие типы выбора значений и многошаговые действия внутри complex popovers.
2. Кастомные calendar/time picker overlays.
3. Предметная проверка структуры скачанных CSV/PDF и фактической серверной загрузки; расширение каталога безопасных upload fixtures.
4. Modal/dialog, toast/notification, responsive и accessibility checks.

Каждый новый control добавляется универсальным browser primitive без ветвлений по сущностям U-Connect и обязательно включается в action-policy, evidence pipeline и изолированный smoke-test.
