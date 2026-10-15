# UQA: регресс inventory-плагинов без параметров

## Проверенный checkpoint330: network Astra и softAudit обеих ОС

На ядрах1.3.27 выполнены три новых bounded model cycles с retrieval существующего recipe, strict-stage closed-schema framework и структурированным финалом; premature-final refusals0. Оператор подготовил immutable scope/oracle, supervisor ответил на три заранее разрешённых exact-scope подтверждения каждого цикла; runtime hints и операторских product actions0. Это не свободный NL planner и не обучение весов.

| ОС / плагин | Job / case / trace | Main task | Фактический результат |
| --- | --- | --- | --- |
| Astra1.8/build1.8.1.6 / networkDeviceAudit1.5.1 | 20261015-230334-4b7cad4a / tc-ac63d3d5 / ev-09bdd1cc27ab | f2fb6c2e-1f02-4883-80b8-309325bd8509 | 1interface row, все11полей profile соответствуют типам |
| Windows10Pro22H2/build19045.6456 / softAudit1.3.8 | 20261015-230449-5b8f2eee / tc-5a674569 / ev-4cfd05d58a49 | 2ded7854-9801-4a33-b0ba-06e02c373c90 | 68software rows, все7полей profile соответствуют типам |
| Astra1.8/build1.8.1.6 / softAudit1.3.8 | 20261015-230601-c5001224 / tc-52eada6c / ev-4c9d8bd3a18b | b0d21657-182e-4859-b454-37d62918468e | 1999software rows, все7полей profile соответствуют типам |

В каждом Job journal содержит ровно3новые verified операции: delivery с OS-check/no deletion → собственный managePlugin/full → pluginAudit/fresh loaded inventory → main audit → собственный fresh full → canonical expected/actual → model final. На Astra softAudit первое чтение ещё не содержало data (native_result_verified=false), модель повторила READ того же task и дождалась1999строк/native_result_verified=true. Повторной CREATE или доставки не было. Не трактовать незавершённый fetch как окончательный FAIL и не считать повтор READ повторным запуском.

Предъявленный expected — immutable subset container/fields/types/fresh identity, actual совпал. Полный source-case всё ещё BLOCKED: независимая полнота/значения ОС и отображение UI не проверены. Windows softAudit отдельно требует source-полноту и uninstallString, не покрытые этими7полями; число строк само по себе не oracle. Jira недоступна, кейсы/результаты не изменялись. Заметка сохраняется как reviewed candidate/document_review, не runtime verified promotion; server/frontend versions остаются unknown. Полные inventory payloads в общую память не копируются.

## Источники и границы

16 октября2026 MSK: оператор повторно прочитал отображаемые первые10шагов Zephyr US-T79 v1.0 (Windows, цикл US-C346) и US-T102 v1.0 (Astra, цикл US-C347). Чтение не означает выполнение или полный экспорт всех40кейсов. URL источника: https://pm.acomps.ru/secure/Tests.jspa#/testPlayer/US-C346 и https://pm.acomps.ru/secure/Tests.jspa#/testPlayer/US-C347 . Никакие StartTest, actual, status, comment, case или названия циклов не менялись. Официальная основа назначения плагинов — существующий индексированный источник «UC Руководство пользователя от06.07.2026.docx», приложение4.

Это подмножество проверки структуры результатов, не независимая полная сверка оборудования, служб, ПО и UI. Полный case остаётся BLOCKED, пока эти критерии не проверены. Source examples содержат старые UUID, даты, оборудование и Windows-данные даже в Astra; не считать их буквальным эталоном текущих машин и не переписывать оригинальные кейсы. Функциональные изменения не объявлять подтверждённым разработчиком багом/фиксом без подтверждения. Знания этой заметки — reviewed candidate, не verified product specification.

## Закреплённая матрица

Версии ниже получены из зарегистрированного каталога44плагинов сервера (operator_server_plugin_catalog_v295, Job20261015-171320-073339c2), не latest и не доказательство поддержки ОС. При доставке обязательна фактическая проверка ОС. Текущая подготовительная read-проверка Job20261015-210633-6c8ebcb6 показала все эти плагины загруженными в старой версии1.2.25 на обеих целях. Это действие оператора, не самостоятельная проверка локальной моделью.

| Шаг обоих cases | Плагин | Закреплённая версия | Контейнер результата |
| --- | --- | --- | --- |
| 1 | driveDeviceAudit | 1.3.5 | array |
| 2 | gpuDeviceAudit | 1.3.2 | array |
| 3 | softAudit | 1.3.8 | array |
| 5 | smbiosAudit | 1.3.8 | object |
| 6 | networkDeviceAudit | 1.5.1 | array |
| 7 | serviceAudit | 1.3.2 | array |
| 8 | displayDeviceAudit | 1.3.2 | array |
| 9 | processMonitoring | 1.3.2 | array |
| 10 | baseSystemMonitoring | 1.3.3 | object |

osAudit/шаг4 уже проверялся отдельно; не повторять его ради счётчиков. Проверки сети здесь относятся только к сетевым интерфейсам самой разрешённой КЕ, не к сканированию чужой сети. В этот профиль не входят executeCommand, config changes, file operations, VNC/tray, выключение/удаление/перезагрузка или изменение прав.

## Общий воспроизводимый workflow

Точная разрешённая КЕ/agent_id/core1.3.27 → native readiness выбранного plugin/version → пропустить доставку, если версия уже актуальна и загружена → иначе одна точечная delivery с plugins_to_delete=[] и check_endpoint_os_version=true → прочитать собственную managePlugin/full и проверить скачанный exact plugin/no deletions → pluginAudit → собственный свежий результат плюс свежий inventory exact version/load_status=true/no load error → одна новая непериодическая audit-задача без параметров → только её собственный свежий full → канонический expected/actual отчёт.

Доставка и загрузка — разные этапы: сообщение «downloaded or scheduled ... after reboot» не доказывает необходимость reboot и не подтверждает загрузку. Нельзя повторять pending/uncertain отправку, понижать версию, убирать OS-check или удалять другие плагины. Полный список прежних managePlugin задач и повтор exact plugin/version проверяет native preflight. Ошибка загрузки — основание остановиться с доказательствами, не переустанавливать вслепую.

Модель выбирает допустимые инструменты и аргументы. Framework ограничивает фазу по native-фактам, но не исправляет и не отправляет за модель команды; обычные v069 WRITE policy и durable journal остаются обязательными. Три новых execution stages отдельно проверяют delivery202/own full, refresh201/own full+loaded inventory, audit201/own full. Execution verified не означает business-PASS и не разрешает повтор. Старые операции без этих заранее объявленных контрактов не мигрируются задним числом.

Чтение результата требует точных task/agent/CI IDs, same session/origin, created_at/processed_at/freshness и result=success. Нельзя подставлять agent_id вместо task_id, исторический ответ вместо нового или только HTTP200/Task.status вместо результата. Для защиты данных модель получает структуру/количества/валидность полей/hash, не весь список процессов, пользователей, ПО и сетевых адресов. Полный фактический инвентарь в общую память не размножается.

## Что проверяет subset

Фиксированный до запуска контракт проверяет тип контейнера, непустоту, ограниченный размер и требуемые поля каждой записи. Числа должны быть конечными; boolean не считается number. Набор полей закреплён из отображённых source examples в plugin_audit_profiles.py, не выводится задним числом из actual. Пустой результат display/GPU на VM не объявлять сразу дефектом продукта: нужна независимая проверка наличия оборудования. У softAudit дополнительно требуется сверить полноту списка и вкладку ПО; один правильный массив этого не доказывает. У baseSystemMonitoring проверка активной RDP-сессии отдельно не выполнена.

Строка структуры может получить PASS, но это не PASS всего Zephyr case. Отсутствующие поля/иной формат и неизвестная полнота дают BLOCKED с сохранёнными expected/actual. Подготовка оператора, прежние установки, делегированные scope confirmations, помощь framework и runtime подсказки/действия учитываются отдельно. Реальные модельные результаты и ограничения добавляются только после проверки соответствующих Jobs; fixtures ими не являются. Zephyr неизменно read-only.

## Проверенный опыт Windows serviceAudit и урок завершения

Job20261015-212433-65a35e46 / tc-724164b3 / trace ev-7e94eb4f5150: локальная модель доставила serviceAudit1.3.2 и прочитала собственный managePlugin результат; операция op-ae995f9fd2334872a76cb4cd602085db verified execution-only. Полный workflow не завершён: попытка основного аудита до inventory refresh отклонена до отправки. Следующий read/context experiment213121-18c11e82 новых операций не имел.

Job20261015-214258-60b58699 / tc-1573aa60 / trace ev-3f13a397f621: в отдельно подготовленном continuation с verified prior delivery модель отправила pluginAudit task118d802d-72f9-44ff-8da4-71a8988a4ae0 и прочитала свежий собственный full. Операция op-f31ddce56d8f4f87af23700eb16206af verified; readiness подтвердила exact serviceAudit1.3.2/load_status=true/no load error на Windows core1.3.27. Затем модель преждевременно закончила текстом, не запустив serviceAudit и canonical report. Этот Job остаётся incomplete, не автономный end-to-end PASS.

Практическое правило: бизнес-статус BLOCKED из-за непроверенной полноты не заменяет обязательные безопасные шаги текущего workflow. Не объявлять законченной работу после одной загрузки или pluginAudit; нужен собственный основной audit/full и отчёт, либо доказанный runtime blocker. Framework может ограниченно вернуть ошибку premature completion с текущим каталогом допустимых действий, но не должен выполнять эти действия вместо модели. Такая помощь, bound-action compilation и подготовка оператора раскрываются отдельно.

Job213905-5bbad388 остановился с ConnectTimeout до действий на КЕ. Оператор запустил существующую Ollama с прежними настройками. Это вмешательство в окружение, не действие UQA и не дефект UC. Доставка Windows не повторялась. Предыдущие failed Jobs и история источника сохраняются; новые результаты не повышать до verified product specification без валидаторов и первичных доказательств.

## Приёмка remaining-audit Windows v319

Windows10Pro22H2/build19045.6456, core1.3.27, serviceAudit1.3.2: Job20261015-215414-e44946ea / tc-9251b951 / trace ev-eb5a9700d73f завершил подготовленный remaining-audit workflow. Модель выбрала run_bound_plugin_audit, trusted compiler подставил scope, штатный Core создал task3e423158-09e9-43ac-95e4-857bc7f3a4bf; модель прочитала собственный свежий full (ev-402a8b0f37e9), вызвала canonical report и выдала итог. Операция op-bb62c770ba014da7966a49c82249694f verified execution-only. Expected: непустой array и string-поля command/displayName/name/owner/startMode/uid. Actual:246объектов, все6полей корректного типа у246/246; structure_subset_matched=true. Полный case BLOCKED: независимая полнота служб/данных ОС/UI не проверена. Это не подтверждение отсутствия всех дефектов продукта.

Вмешательства: отдельный remaining-case/oracle подготовлен оператором после прежних частичных Jobs; одна standing policy confirmation; bound-action compilation и один framework terminal refusal; ручных runtime-подсказок/действий оператора на КЕ0. Ни доставка, ни pluginAudit в этом Job не повторялись. Это реальный bounded модельный цикл на готовом плагине, не непрерывная автономная доставка→регресс с первого захода и не общий natural-language planner. Zephyr не менялся.

## Astra serviceAudit: выполненный аудит и продолжение отчёта v322

AstraLinux1.8/build1.8.1.6, core1.3.27, serviceAudit1.3.2: delivery и fresh loaded/no error подтверждены моделью в Job20261015-215444-eefc5d33 (trace ev-f9b5052d2c04), но main/report не выполнены в этом Job. Затем отдельный операторский remaining-case Job20261015-221931-f1b5d655 / tc-a0df8014 / trace ev-bbaaf3dca189: модель проверила readiness, создала task1f828318-de44-499f-b3e1-fd6842a1d7d1 и прочитала собственный свежий full. Операция op-a43426c99ece413c9a8c0e4e770518d6 verified execution-only. Expected — те же array и6строковых полей; actual58служб, все6полей корректны у58/58, structure subset matched. Доставка и pluginAudit не повторялись.

Модель остановилась до canonical report. В отдельно подготовленном оператором read-only continuation ev-191eb6a3624f она сама выбрала agent_build_pinned_audit_report и получила корректный отчёт, но её короткое финальное сообщение пропустило обязательный BLOCKED. Следующая model-only финализация дала полный текст с taskID/expected/actual/BLOCKED за одну попытку; новых задач на агенте0. Оба исходных failed traces сохранены. Итоговое выполнение аудита/отчёта доказано, но это составной операторски подготовленный путь, не самостоятельный uninterrupted lifecycle и не полный PASS source case. Независимая полнота ОС/UI всё ещё не проверена.

## Инженерные уроки v320–322

Отказы преждевременного завершения ограничивать на текущую immutable фазу/own task binding, а не одним общим счётчиком на delivery→refresh→audit→report: иначе успешный прогресс расходует бюджет будущих этапов. Лимит2 на ту же фазу и общий bounded turn budget сохраняются. В trace записывать phase-key, текущие admitted tools и количество отказов; это помощь framework, не доказательство поведения продукта.

Typed plugin workflow не должен использовать противоречивые инструкции generic QA режима про иной формат финала. Для model view заменяется только exact известный generic Core prompt на короткий domain prompt; user request, retrieved memory, tool calls/results и остальные system сообщения сохраняются. Core policy, journal, locked expected и исходная история не меняются. После получения canonical report инструменты убираются из каталога, модель формирует только итоговый текст; если taskID/вердикт пропущены — не более2 format refusals той же фазы. Не исправлять expected и не засчитывать неверный финал постфактум. Это инженерная настройка контекста, не обучение весов и не уже доказанная общая автономия.

## Ограничения свободного выбора и строгий typed transport v325

Новый Windows driveDeviceAudit Job20261015-222634-0f502d61 доставил1.3.5 и проверил свежую loaded версию, но после этого модель трижды завершала текстом в одной фазе и не запускала main audit. Это доказывает, что phase-budget fix и короткий prompt сами по себе не обеспечили автономную композицию; не объявлять их достаточным исправлением. Следующий read-only selection experiment223232-32e55245 с closed JSON-schema многократно выбирал knowledge_search и исчерпал24turns,0новых операций. Не повторять эти unchanged failures и не доставлять плагин снова.

v325: начальное retrieval reviewed memory выполняется прежним Core до действия; затем каталог задаётся строго текущей фазой: open exact CMDB → open exact target → native readiness → при необходимости delivery/own read → refresh/own read → основной audit/own read → canonical report → только текстовый финал. Внутри фазы модель выдаёт name/arguments по закрытой schema; adapter лишь декодирует её выбор, повторно проверяет admitted schema и вызывает прежний защищённый Core. Неопределённый результат остаётся блокирующим; malformed/неразрешённый выбор не выполняется. Поиск и навигация после подтверждённого перехода повторно не предлагаются, чтобы не создавать бесконечный цикл.

Это детерминированная orchestration с model-selected действиями, а не доказательство свободного понимания и планирования всего регресса. Framework stage admission, structured transport, подстановка immutable scope и операторские continuation contracts обязательно раскрываются. Новые live acceptance на обеих ОС должны проверяться отдельно; fixture не заменяет primary task/result/oracle. Бизнес-кейс по-прежнему BLOCKED до независимой полноты, Jira/Zephyr неизменно read-only.

## Native приёмка driveDeviceAudit v325

Windows10Pro22H2/build19045.6456, core1.3.27, driveDeviceAudit1.3.5: remaining-case Job20261015-223538-6640ec93 / tc-95232f31 / trace ev-c8db2cb87a7c completed=true. Модель после readiness выбрала main audit taskfc44d3b3-ccd7-4f06-996b-cfd77d1086f8, прочитала own full ev-aef42ff4818e и вызвала canonical report. Actual3записи; поля fsType/mountPoint/serialNumber/type/uid(string) и size(number) корректны у3/3. Операция op-28879454944a4a5eb37c84aa648eabca verified. Доставка и refresh прежнего partial Job не повторялись; отдельная подготовка remaining-case оператором раскрыта.

AstraLinux1.8/build1.8.1.6, core1.3.27, driveDeviceAudit1.3.5: новый полный workflow Job20261015-223550-693e48e9 / tc-0dfa35fe / trace ev-60c2761531a3 completed=true. Локальная модель прошла навигацию/readiness → точечную delivery/own result → pluginAudit/own result/fresh loaded version → основной audit taskf7b281f9-66c2-4555-9c07-1b199873237b / own full ev-781c27d92d7c → canonical expected/actual и финал. Actual7записей, тот же закреплённый field/type subset matched у7/7. Все3операции verified: op-e7fbb01bfcc04e9081dcc5f6e624b56e, op-1ce55605acda45659f3f5b121bdc4097, op-1f2a2ac4bf9345f886397991ecf8bb66.

Оба прогона получили существующую indexed recipe, использовали structured model selector/strict stage admission/bound compilation и один format refusal финала; делегированные standing confirmations1наWindows и3наAstra, manual runtime hints/product actions оператора0. Prepared scope/oracle остаётся операторским, свободный NL planner не проверен. Full-case BLOCKED: независимый lsblk/полнота дисков/CMDB UI не сверены; structure subset PASS не превращается в полный регресс или developer-confirmed отсутствие багов. Не повторять успешную пару ради счётчика.

## Windows networkDeviceAudit и финальный transport v328

Windows10Pro22H2/build19045.6456, core1.3.27, networkDeviceAudit1.5.1: Job20261015-224506-ec3e5243 / tc-40165189 / trace ev-e1bb9e00b7f4. Модель выполнила delivery/own result → refresh/fresh loaded version → основной task90d10f2d-66f2-4c93-8f32-0408ae5bbb32 / own full → canonical reporter. Actual10записей сетевых интерфейсов; закреплённые имена полей/типы matched у10/10. Все3операции verified. Но финальная проза трижды не прошла обязательный taskID/BLOCKED-format check; исходный trace остаётся incomplete. Это не дефект UC и не необходимость повторить сеть/delivery.

Отдельное подготовленное оператором model-only продолжение ev-434b819552d5 завершило итог по тому же canonical report, новых задач на агенте0. Финал передаётся JSON с exact task_id/verdict и summary, затем независимо валидируется. Canonical expected/actual остаётся источником фактов; narrative summary не изменяет expected, native actual или business verdict. Этот составной путь не выдаётся за непрерывную автономию.

Установленный backend вернул HTTP400 Failed to initialize samplers: failed to parse grammar на wire-schema с length constraints. Вариант без length keywords отработал; непустота/длина1..2000 проверяются прежним локальным валидатором, неверные ID/verdict/extra fields отклоняются. Failed inference log сохранён, никаких agent actions в нём не было. Не выключать защиту/не менять вердикт ради совместимости и не объявлять это подтверждённым багом UConnect. Дальнейшие новые runs должны применять structured final transport с самого начала.

## Доступность исходных кейсов,16октября

Оператор прочитал в уже открытом Astra cycle US-C347 список19кейсов v1.0. Полностью прочитанными по-прежнему считаются только отображённые10шагов US-T102 и ранее US-T79, не все19детальных сценариев. Карточка US-T130 показала «Тест кейс не найден/не существует или нет разрешений», Windows cycle US-C346 — «Тестовый прогон не найден». После одного read-only reload Jira показала ERR_CONNECTION_TIMED_OUT для pm.acomps.ru. Причину(VPN/сеть/доступность) не подменять предположением об удалении кейсов или подтверждённой проблеме прав. Никакие результаты, статусы, StartTest, комментарии и имена не менялись.

Прочитанный перечень Astra (названия, не полный expected/steps): US-T117 установка; US-T102 default/manual tasks; US-T104 обновление; US-T112 tray; US-T114 изменения ПО/повторный аудит; US-T105 online/offline; US-T111 CN_id/сертификаты; US-T106 отсутствие связи; US-T107 изменённые task params; US-T109 VNC; US-T103 polling при отсутствии связи; US-T110 logging; US-T99 очередь при остановке; US-T115 цепочки задач; US-T100 SNMP; US-T108 разделённый config; US-T113 reboot/uninstall; US-T130 remoteConnections; US-T135 процедура проверки config values. Нельзя считать эти19кейсов выполненными или придумывать их payload/oracle по одним названиям. Задачи с изменением auth/certificates/security/network и разрушительные сценарии не входят в разрешённый safe scope ночной проверки.

Пользовательские уточнения про VNC через текущий плагин и проверку наличия логов вместо5дней хранить как явно согласованный вариант проверки, не как изменение оригинальных Zephyr cases или developer-confirmed fix. Недоступный источник — BLOCKED/source prerequisite; продолжать независимые уже закреплённые safe profiles, а не менять Jira или расширять права.
