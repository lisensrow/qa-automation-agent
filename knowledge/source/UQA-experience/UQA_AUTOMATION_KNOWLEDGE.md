# Политики и процедуры: проверяемый опыт UQA

Источник опыта: UC lab, 15 октября 2026, live_operator_assisted. Это не официальное руководство, не автономная приёмка и не разрешение действия. Версии сервера/frontend в этих пробах отдельно не подтверждены; применимость к другому выпуску неизвестна. Перед действием нужен свежий UI/native receipt. Старый опыт и Jobs не заменяются.

## Свежий список политик и границы источника v203

15октября2026, operator read-only, Job20261015-023335-00ac7909/tc-40226b7f. После origin/probe оператор открыл точный маршрут из прежнего native click ev-f8d604df6ec9, не угаданную ссылку; свежий open ev-65bab790c69d подтвердил /automation/policies. Native GET списка ev-72d1944b7c77: HTTP200, полный envelope offset0/limit50/count0/total0/items[]. Текущий список пуст; это не доказательство отсутствия политик в другой версии/стенде или успешного создания. Native table ev-0dd30ff4f336 записан отдельно. Формы/назначения/запуски не открывались, журнал операций пуст, общий Job остаётся BLOCKED для автономной приёмки.

Первый case tc-70296c30 остановлен harness до клика plus: ограничение observe/interact не разрешило его классификацию. Это не отказ backend и не модельная ошибка; inspect ev-fc877ab49ee4 сам успешно наблюдал иконку. Второй case использует операторский путь, поэтому не является автономной навигацией и не отменяет первый BLOCKED. Старые uncertain/awaiting_verification операции v182 не повторялись и не переклассифицировались.

Руководство пользователя revision2026-07-06 (официальный исходный hash хранится в source registry), разделы «Список политик» и «Задания политик», описывает три типа действия, отдельное определение политики и задание со scope КЕ/коллекции и типом запуска. Условия аналогичны коллекциям. В тексте руководства есть повтор подписи «Обновление задач» перед полями плагинов: не выбирать action type по одной этой строке, сверять заголовок/текущий UI/установленный контракт. Документ является declared specification, не runtime-доказательством исполнения.

## Наблюдённый маршрут формы политики

Из стартового CMDB меню разделов открывается единственной безымянной иконкой plus. Затем видны Automation & policies → Policies → List of policies. Последний пункт разрешается как role link; без роли наблюдалась неоднозначность. Адрес списка после фактического клика: /automation/policies. Не придумывать container с именем раздела.

Первое открытие глубокого адреса после certificate login возвращалось на CMDB. Проверять current_url, а не только requested_url/HTTP200; повторное read-only открытие в уже авторизованной сессии вернуло нужный список. Это наблюдение, не подтверждённый разработчиком баг.

Job20261014-223727-54995264: ev-0e02ce621691 (раскрытие Automation & policies), ev-c88f592c0e1c (Policies), ev-ad0662ed8dc5 (уникальный link), ev-f8d604df6ec9 (список), ev-bcfe621e283f (правильное повторное открытие). Прежняя попытка Create policy на неверной странице ev-72a3c06f3ad5 оставила legacy uncertain operation; не считать её созданием, не переписывать задним числом в PASS.

## Наблюдённые поля новой политики

Job20261014-224740-b4304cbc, case tc-6421971a. В пустом списке Create policy (button) открывает модальную форму, сохраняя /automation/policies; это не окончательный Create внутри формы. ev-f13ae644370f подтверждает только открытие.

В форме наблюдены Name, Turn on, вкладки Action и Conditions. Три типа: Agent configuration, Agent task update, Agent plugin management. В Agent configuration показаны режим/иконка агента, адреса подключения, порты, журналирование и проверка сертификатов. Их значения не извлекались и не менялись. ev-0febd5ea9641: native census 15 controls, required=0, invalid=0 — это не доказательство бизнес-валидности.

ev-d9f2fc4ee71a: Conditions открывает конструктор Logical operator, Common/Component parameters, Endpoint/Agent/Software/RAM/CPU и другие категории, Attribute/Aggregation type/Operator/Value. Он похож на конструктор коллекций; конкретные настройки/результат применения ещё не проверены.

ev-030660cba441: окончательная Create (button) enabled=true даже при пустом имени. Не нажималась; ни успешное создание, ни серверный отказ не проверены. Модальная форма закрыта уходом на CMDB (ev-7446ef35120f), без fill/Create/Save/Apply/Run. Resources=0. Журнал консервативно считает launcher Create policy legacy unbound awaiting_verification; это открытая техническая граница, не бизнес-PASS.

## Наблюдённый маршрут формы процедуры

Job20261014-225056-18044f6f, case tc-da96d52d, live_operator_assisted. plus → Automation & policies → Procedures → List of procedures (role link). ev-11447a787c24 подтверждает раскрытие раздела, ev-96ddf36e5d15 — уникальный link, ev-a05a81da8959 — переход /automation/procedures. Список автоматически показал существующую VNC Install procedure; её блоки только отображались, не редактировались и не запускались.

Add (button) открывает Add procedure (menuitem): ev-f6b2cc7ab3ec и ev-1759c7a4c102. ev-5c98be533d99: menuitem открывает New procedure, сохраняя /automation/procedures. Это несохранённый новый редактор, не сохранённый шаблон и не выполненная задача.

ev-aba658c304cd и ev-8497956c0604: категории Logical, Variables, UC Agent имеют role treeitem; UC Agent uniquely inspected. Zoom controls имеют role button внутри SVG. Обычный form census ev-eee2824b10d2 обнаружил только Search procedures, а не поля блока/имя процедуры. Не придумывать обычную textbox форму или обходиться нажатием координат: нужен проверенный контракт блочного редактора, блоков, связей, параметров и сохранённого графа. В этом первом case категории не раскрывались, блоки не добавлялись, имя не менялось, Save/Run не выполнялись.

## Наблюдённый маршрут формы процедуры: категории и палитра

Повторный case tc-7ec67b72 того же Job, 15 октября 2026, operator-assisted, без добавления блоков или запуска. ev-191eba681507: browser_inspect_tree_semantic наблюдает три категории первого уровня, expanded=null, selected=false. Это selectable palette, не доказанный expandable tree; не придумывать aria-expanded=true.

ev-1d4217ad0d0f: точный browser_click_semantic с name UC Agent, role treeitem раскрывает палитру как INTERACT/auto_allowed по существующей v069. ev-0b9c2717d731: native tree snapshot selected=true только у UC Agent. Палитра предлагает отправку/удаление/скачивание файла, передачу директории, выполнение команды и запуск инсталлятора. Это описания доступных блоков, не разрешение их выполнять.

ev-bc1803e6c50a: «Выполнить команду» uniquely resolved через text; element.tag=text (SVG), role пуст, cursor=grab, geometry_actionable=true. Это не button и не обычный input. Инспекция не добавляет блок и не проверяет правильность параметров/связей.

ev-ef9a50468138: Logical показывает «Если / То» и predicate «Устройство endpoint_id онлайн». ev-473902dcd62d: Variables показывает «Присвоить X = …». ev-0d1f9c82d3a1: selected=true только у Variables. Наблюдены безопасные category selections, не построение графа. Не делать generic drag на угаданный заголовок: нужны уникальная рабочая область и проверяемые postconditions графа.

## Что пока не доказано

### Историческая атомарная память: интерпретация локальной моделью

v191 записал два runtime-observation кандидата procedures.saved_definition: сериализация block_xml_v1 и отдельный context. Новый native GET Job20261015-002529-066aab5d/tc-1452c037/ev-80089519fd84 имеет linked observation; source/hash/legacy preservation/dedup/readback проверены, версии и ОС неизвестны, режим operator-assisted. v192 выдаёт только типизированные значения после повторной проверки первичного источника и тела; не statement/XML, не разрешение или PASS. Новые произвольные кандидаты не публикуются автоматически.

Контекстная модельная проверка Job20261015-003603-a05c4261 полностью не прошла. Диагностический case tc-3871d0e3/ev-36fcf6a284ed сохранил5/6 правильных критериев: отдельный context, operator mode, неизвестную текущую применимость и запреты считать память выполнением/PASS. Точный format label не воспроизведён. Не подменять этот FAIL техническими226/226, не объявлять полное знание процедур и не трактовать модельную неточность как дефект UC.

### Чтение сохранённого графа локальной моделью

15октября, v190, live_local_model с операторской навигацией: Job20261015-001805-ba56b74e/tc-be9e3125. Модель вызвала browser_inspect_saved_block_graph_semantic на свежем native GET и exact_name; ev-6e51b552eb73 дал11блоков. Срок свежести фиксирован60секунд и не выбирается моделью, ответ должен быть полным и из текущей сессии/origin. Инструмент не выполняет новый запрос и не возвращает XML/значения. ev-0cf2ddfb7ed5: модель сообщила правильное количество, saved_only=true и отсутствие права утверждать запуск/полное создание. Resources0/operations[].

Это source inspection, не доказательство отображения выбранного графа или его правильности/выполнения. Инструмент сохраняет usable_for_pass/verdict=false. Первый trial20261015-001327-4ad7e23b был отклонён из-за предложенного моделью age0; public age-option снят, проверка не ослаблена. Не применять рецепт к неполному списку/другой версии без нового наблюдения; не записывать модельную ошибку как дефект UC.

### Сохранённый граф процедуры: наблюдённая структура, не исполнение

15 октября 2026, operator_readonly, Job20261014-235424-0de03747/case tc-34935085. Сначала origin/probe, затем ранее наблюдённый адрес Procedures/probe: существующие объекты не менялись. ev-8ff5b674bba4f: exposed SVG count0 — это отсутствие доступных SVG-имен, не отсутствие SVG. ev-b357ef938c39: canvas1 без имени/fallback; ev-6592e9664f08: tree_not_found в существующем редакторе, не в новой палитре.

ev-aede75cc4c39: DOM census показывает SVG6, одна большая область1627×865 с274 descendants, canvas1, native draggable0; среди атрибутов data-id/data-uqa-id. Это форма DOM, не доказанный unique workspace/block oracle. Нельзя делать вывод «редактор только canvas» или отождествлять все SVG с рабочим графом.

ev-8ac7d9fad984: прочитан уже полученный GET /api/v1/u-auth/u-sys/api/v1/procedures, HTTP200, body не обрезан. Envelope limit/offset/count/total/items; два элемента содержат id/name/description/xml/context/active/debug/created_at/updated_at. Значения команд/параметров не выводились. ev-71d616904abf: ограниченный offline XML census: root xml, block/next/field/value/variables/variable; два шаблона имеют11 и3 block. Разбор структуры не проверяет правильность команд, связей, параметров, выполнения или совместимость другой версии.

Следующий контракт должен связывать точный owned draft, наблюдённые block IDs, связи/параметры и сохранённый XML без исполнения. GET/schema/census не даёт разрешения POST/Save/Run. Конкретный graph validator и безопасный block editor ещё не реализованы.

### Повторяемая ошибка перехода из меню в редактор (модель, не баг UC)

15 октября, live_local_model qwen3:14b: Job20261014-233520-79fd039b/tc-dee5b4ec, ev-dd50a19a6941 наблюдает одно enabled Add procedure/menuitem. Модель пропустила пункт и искала категории до открытия редактора; BLOCKED. Дополнительная диагностическая подсказка в Job20261014-234619-f946db24/tc-cb5743c9 также не помогла: ev-1b9e97a97a75 Add menu, ev-ad70abd9591e Logical/treeitem missing, ev-aa89e4ccbae4 повтор Logical/menuitem blocked. Оба прогона resources0/operations[], без Save/Run. Второй эксперимент снят, production restored к195e9f6.

Это повтор того же ограничения автоматизации, не новый факт о дефекте продукта. Не менять роль искомой категории на menuitem из-за открытого меню: это разные поверхности. Проверять фактический переход Add procedure → New procedure перед чтением категорий. Наличие меню, enabled пункта и диагностической подсказки не доказывает переход; нужны свежие UI receipts. Полный graph workflow всё ещё не принят.

### Аудит первоначального открытия: нормализация Core, не доказанный auth bug

Job20261014-231617-60b0f47e/case tc-7c63a3aa, ev-5df0fd40953b: model_requested_url=/automation/procedures, но native requested_url=https://uc.lab.local. managed_initial_open.reason=inferred_deep_link_normalized_to_origin. Существующий Core намеренно открывает сначала origin, если пользователь не передал точный deep URL и browser state ещё не создан. Это защита от угаданных UI/API ссылок, её нельзя обходить по старому рецепту.

Предыдущая гипотеза о потере адреса в certificate login не объясняет этот прогон. Экспериментальная auth-правка не выпущена, исходный код восстановлен. Не записывать это как баг/фикс UC и не советовать обновление продукта.

Модель после восстановления навигации прошла plus → Automation & policies → Procedures → List of procedures и Add, но не выбрала Add procedure. Затем искала Logical в меню, не в новом редакторе, и была остановлена repeated semantic inspection. Это BLOCKED, resources0/operations0. Наличие Add procedure в меню ещё не означает, что открыт редактор: проверять свежий New procedure и дерево категорий перед их использованием.

Автономное создание политики, выбор целевой коллекции, сохранённые условия, действие на выделенной КЕ, расписание, отрицательный oracle и построение/запуск процедур не приняты. Для изменений нужны точный owned scope, immutable operation/oracle и свежий контроль фактического результата. Обычный ACK, enabled кнопка и сохранённый рецепт этого не заменяют.
