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

1. Выбор значений в tree controls и complex popovers.
2. Кастомные calendar/time picker overlays.
3. Upload/download с проверкой имени, типа и содержимого файла.
4. Modal/dialog, toast/notification, responsive и accessibility checks.

Каждый новый control добавляется универсальным browser primitive без ветвлений по сущностям U-Connect и обязательно включается в action-policy, evidence pipeline и изолированный smoke-test.
