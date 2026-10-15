# Ресурсы, журнал операций и восстановление

Resource ledger хранится в Job. Тестовый объект имеет тип, имя, внешний ID, case-владельца, статус, metadata и зависимость на другие ресурсы. Идентичность известного объекта нельзя заменить другим ID только потому, что имя совпало.

Очищать можно только разрешённые owned/disposable объекты, по проверенному ID и предикатам области. Dependency order, пустота/связи и результат удаления должны проверяться. Ledger переживает сбой, но наличие ledger не гарантирует универсальный cleanup любого продукта.

Перед commit journal пишет intent с workflow/stage/resource, tool/arguments fingerprints и immutable oracle. Uncertain не означает «ничего не произошло». Сначала fresh native read и reconciliation, а не resend. Даже verified state не доказывает причинность отправки.

Native disabled до начала клика может дать not_sent; обычный JSON executed=false или timeout этого не доказывает. Operator-reviewed rejected/canceled сохраняют историю, не дают повторять ту же stage и не становятся verified/PASS.

## Учёт начала сетевых запросов v212

Дополнительный browser-context observer считает request-start, completion/failure events, методы и типы ресурсов внутри окна UI-действия. В отличие от списка последних30 fetch/XHR ответов он замечает отправленный запрос без ответа и учитывает трафик дочерних страниц. Запись привязана к action_execution_id и переносится в observation; счётчики не зависят от усечения прежнего списка ответов. До256 pending объектов хранятся только в памяти; переполнение, неизвестный метод/тип, потерянное completion и замена незакрытого окна выставляют sticky tracking_incomplete до нового context. Observer не читает URL, headers/body и credentials.

Это НЕ доказательство отсутствия изменений: покрыто только наблюдённое окно браузерного context, не будущие запросы, WebSocket frames, полное поведение service worker или backend effects. Фоновый трафик включён; причинность действию не приписывается. pending_at_begin и pending_at_finish показываются отдельно, completion events могут относиться к запросам до начала действия. Нулевой счётчик и network_window_closed не освобождают journal; resend_authorized и business_effect_verified всегда false. Статусы старых операций и recovery oracle не менялись.

Изолированный native fixture проверяет failed/pending POST,41start против30response preview, переполнение и отсутствие чувствительных данных. Read-only lab receipt join проверил передачу счётчиков в evidence/observations:8request starts (7GET/1POST),0pending, tracking complete для этого окна. POST здесь — наблюдённый запрос данных таблицы, не разрешение произвольных POST. Это операторская техническая проверка, не автономное создание/применение политики. Для launcher lifecycle ещё нужен отдельный immutable профиль UI и типизированная проверка перехода; текущий response-only список не является таким oracle.

Трёхстадийный explicit owned protocol существует, но полная автономная бизнес-приёмка, произвольный UI cleanup и legacy/unknown autosave остаются ограничениями. Удерживаемые пользователем демонстрационные коллекции не disposable и не удаляются автоматически.

## Следующий UI-launcher contract: ещё не реализован

Read-only обзор установленного frontend v213 различил локальный handler открытия PolicyDialog и отдельный submit form automation-policy-form. Source hashes и selected markers сохранены отдельно. Это только кандидат для будущего trusted implementation profile, не разрешение освободить старый intent. Отсутствие autosave во всех зависимостях не доказано; source labels/defaults не равны текущему runtime.

Перед реализацией нужны два неизменяемых вида стадий: UI preparation и business commit. UI стадия всё равно проходит существующую policy и durable intent до клика; критерий завершения — точный source/profile-bound переход поверхности в той же session/origin/route, а не наличие произвольной формы. Профиль должен различать launcher вне формы и конечный submit внутри формы, фиксировать control scope и ожидаемую поверхность, проверять полные native receipts и request-start accounting. Отказ, потеря наблюдения, неожиданный non-read request или неизвестный профиль сохраняют pending/uncertain. Нулевой network counter, type=button, кнопочная подпись и видимость modal по отдельности не могут закрыть такую стадию.

Immutable binding и план нескольких стадий должны сохраняться до начала, а не переписываться между Open и Save. Завершение UI стадии не даёт business PASS, не создаёт ledger resource и не разрешает повторить тот же launcher. Для commit требуется свой locked oracle и последующее текущее доказательство. Старые legacy/unbound операции нельзя автоматически перевести в новый протокол. После fixtures нужен новый реальный local-model workflow, не операторская подготовка формы. Этот контракт пока описан, но не подключён к journal.

Отдельный выявленный риск профиля: initial form values задают is_active=true и пустой execution_condition.items. Это статический default, не доказанное применение к КЕ. В будущем перед тестовым commit надо явно доказать inactive и точный owned scope; создавать активную политику с условиями по умолчанию недопустимо. Установленные frontend type ids не заменяют enum-валидацию Swagger/backend.
