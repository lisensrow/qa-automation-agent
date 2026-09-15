# Матрица возможностей frontend-тестирования UQA

Статус документа: живой план покрытия ручных frontend-задач. Обновляется вместе с агентом.

## Реализовано

- Открытие страниц и безопасная семантическая навигация.
- Read-only inspection видимости, enabled/disabled и основных ARIA/DOM-состояний.
- Точное заполнение текстовых, поисковых и числовых полей.
- Выбор значения native select и ARIA combobox без ручного угадывания option.
- Идемпотентная установка checkbox/switch в `checked=true/false`.
- Проверка точной строки таблицы и работа с её context menu.
- Фиксация screenshot, browser state, XHR/fetch и console/network errors.
- Action policy v069 для OBSERVE, INTERACT, WRITE и DESTRUCTIVE.

## Следующие этапы frontend-покрытия

1. Radio groups и составные multi-select/autocomplete controls.
2. Клавиатурные действия, hotkeys, focus order и tab navigation.
3. Drag-and-drop, изменение порядка и размеров колонок/полей.
4. Табличные фильтры, сортировка, пагинация и массовый выбор.
5. Date/time pickers, sliders, tree controls и complex popovers.
6. Upload/download с проверкой имени, типа и содержимого файла.
7. Modal/dialog, toast/notification и validation errors.
8. Responsive layout, visual comparison и accessibility checks.

Каждый новый control добавляется универсальным browser primitive без ветвлений по сущностям U-Connect и обязательно включается в action-policy, evidence pipeline и изолированный smoke-test.
