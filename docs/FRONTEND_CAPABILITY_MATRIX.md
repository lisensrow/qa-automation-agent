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
- Выбор единственной точной option в поисковом ARIA autocomplete.
- Проверка фактического forward Tab focus order.
- Ограниченные keyboard actions с отдельной классификацией риска.
- Drag-and-drop между точными semantic endpoints.
- Resize панели или колонки с проверкой bounding box до и после.
- Структурированный снимок таблицы, сортировка, выбор точной строки и проверяемая пагинация.
- Проверка точной строки таблицы и работа с её context menu.
- Фиксация screenshot, browser state, XHR/fetch и console/network errors.
- Action policy v069 для OBSERVE, INTERACT, WRITE и DESTRUCTIVE.

## Следующие этапы frontend-покрытия

1. Составные ARIA multi-select и chip-based selectors.
2. Составные hotkeys/chords с отдельной безопасной моделью clipboard.
3. Специализированная проверка сохранённого порядка после drag-and-drop.
4. Составные column filters, select-all и проверка bulk action preview.
5. Date/time pickers, sliders, tree controls и complex popovers.
6. Upload/download с проверкой имени, типа и содержимого файла.
7. Modal/dialog, toast/notification и validation errors.
8. Responsive layout, visual comparison и accessibility checks.

Каждый новый control добавляется универсальным browser primitive без ветвлений по сущностям U-Connect и обязательно включается в action-policy, evidence pipeline и изолированный smoke-test.
