# Политики и процедуры: проверяемый опыт UQA

Источник опыта: UC lab, 15 октября 2026, live_operator_assisted. Это не официальное руководство, не автономная приёмка и не разрешение действия. Версии сервера/frontend в этих пробах отдельно не подтверждены; применимость к другому выпуску неизвестна. Перед действием нужен свежий UI/native receipt. Старый опыт и Jobs не заменяются.

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

Автономное создание политики, выбор целевой коллекции, сохранённые условия, действие на выделенной КЕ, расписание, отрицательный oracle и построение/запуск процедур не приняты. Для изменений нужны точный owned scope, immutable operation/oracle и свежий контроль фактического результата. Обычный ACK, enabled кнопка и сохранённый рецепт этого не заменяют.
