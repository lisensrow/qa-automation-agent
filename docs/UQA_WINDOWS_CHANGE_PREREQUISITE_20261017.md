# Windows US-T84: пользовательское ПО и новый цикл наблюдения

REGUSER701. Полный кейс Windows US-T84 пока BLOCKED, не PASS. Источник требует ПО, устанавливаемое **для конкретного пользователя**. Нельзя переносить системный Debian-пакет из Astra или подменять пользовательскую установку регистрацией от SYSTEM. Подготовленные полные сценарии остаются Windows0/21, Astra1/19, всего1/40; единственный полный — Astra US-T1143/3. Свободная автономность обоих циклов не принята.

## Источник и собственное чтение UQA

US-C346, кейс5 US-T84 v1.0, source JSON SHA256 `7d3b086e6c61e38df9142a761080e87bca665d3f77718ad02a1532957091ce35`, manifest `cd80d283ecace073ee80e36fc39274265f6c173948cec4d07374e64af7899ec8`.

Job20261017-140637-47d6ddfc/tc-2589343d: модель сама выбрала полное окно1..3, source ev-cdbf90a020ed, own coverage ev-149b7b990076/ev-58d11255f03d/ev-bf17014194df. Вставки оператором тела источника и подсказок следующего инструмента не было. Все ячейки и предусловия прочитаны. Итог ev-f5d16f626578 — source-only,0операций, не выполненный сценарий. Финальный structured checks отсутствовал, повторные автоматические format reminders результата не дали; семантический финальный отчёт не принят. Не выдавать факт чтения за освоенный кейс.

Источник:1) новое per-user ПО;2) одна softAudit;3) новое ПО в scoped software CMDB через detected_at_id=agent UUID. Исторические пути/имена/версии — примеры, не текущий oracle. Не установлен новый per-user пакет, новая softAudit этого кейса не запускалась.

## Реальная проверка предусловия

Выделенный Windows: ci_name home-server-UC-windows10; agent71724f3b-41b9-449b-9075-1dd6c8e1c2df; CIc0951a10-3e93-58f9-9468-4702734b417f. Core1.3.27 и executeCommand1.4.0 проверены текущей готовностью. ОС известна как Windows10Pro22H2/build19045.6456 из прежнего источника; точный текущий build здесь не перепроверен. Server/frontend unknown. Модель qwen3:14b/digest bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8/context24576/RTX5070Ti не менялись.

| Этап | Job / evidence | Expected → actual |
| --- | --- | --- |
| Первая готовность | 20261017-140734-b2aff913/tc-8cc855c3/ev-a2f57435be32 | fresh loaded command plugin → отказ до отправки, inventory stale |
| Уточнение причины | 20261017-140941-e62d1c14/ev-27c50bb9ddf5 | установленная причина plugin_audit_stale; refresh request неполно связан оператором → Core отказал до мутации ev-271114f0fa85 |
| Исправленный refresh | 20261017-141102-7965a79f/tc-78c324d3 | один pluginAudit ev-613d636d8e72 → own full ev-f5619ac5753d, op-1e570ffacd0d4fa7b6c2fa99ec3e47b9 VERIFIED; ни доставки, ни softAudit |
| Старый запрет нового наблюдения | 20261017-141234-b475226b/tc-5dfe777f/ev-8b0ba5738261 | новый census → endpoint_prior_attempt_no_rekey; op-110eb1f7d8d245b792d33712fa8a1a1c NOT_SENT, исходный результат не переотправлен |
| Ошибка формулировки оператора | 20261017-141733-601566eb/tc-b5275d07/ev-34fb23db8ce6 | фраза «только read-only» заблокировала POST по read_only_request;0операций; policy не менялась |
| Явный новый наблюдающий цикл | 20261017-141932-4db5dc4e/tc-e26aecff/ev-33f18ab404e9 | COMPLETE query,3зарегистрированных/0активных пользовательских кандидатов, own task VERIFIED |

Новый task14cc9d53-f080-4f86-94d3-308a77bcc4b2: CREATE ev-f640a4e29899; pending own GET ev-25c6f8b233fb; fresh own full ev-b63cb851a2d8; op-c974ebb17f6c494895e0aa18b783bca0 VERIFIED. Result SHA256 `66d5a675fd003af6a3d4e5c0902f2ff911a6066af72fabeb02f46bfc92467435` совпал с историческим содержимым, но новый task ID/создание/processed/read timestamps и own journal подтверждают новое наблюдение, не replay. Итог модели корректно ограничен census, без business/desktop/Tray PASS.

Ноль кандидатов не означает отсутствия всех пользователей/процессов, не доказывает невозможность всякой per-user установки. Здесь нет подтверждённой целевой пользовательской идентичности, штатного запуска от её имени и безопасного нового per-user installer. Не угадывать имя, не входить/разблокировать, не создавать пользователя, не менять права/security и не подменять scope установкой от SYSTEM. До этих предусловий полный US-T84 BLOCKED.

## Новый контракт, не обход replay protection

`session_observation_renewal.py` допускается только для неизменённого `owned-user-session-census-v1` (WTS/logind). Новая закрытая requirement содержит exact prior Job/case/operation/own READ + новый полный source Job/case/key. Требуются одинаковые target/CI/agent/core/profile/payload, исходный locked contract и journal fingerprints, старый VERIFIED/postcondition/own complete native result, возраст минимум3600секунд, новая reservation не старше1800секунд. Источник должен быть полностью прочитан самим UQA после прошлого наблюдения; допустимы только профильные Windows/Astra кейсы software/Tray/VNC. Обязательная новая source-привязка в исходном запросе.

Все операции той же цели/профиля должны быть разрешены, reference — последнее VERIFIED наблюдение. Sending/uncertain/awaiting/canceled, конкурентная reservation, неправильный hash/scope/reference/source или слишком свежий старый результат запрещают POST. Старый task никогда не пересылается. Без явного renewal прежний no-rekey отказ неизменён. MSI/установка/диски/другие profiles renewal использовать не могут. STEP/AUTO, Core WRITE confirmation, locked oracle, OS/loaded-version guard и operation journal остаются.

## Роли, проверки и следующий шаг

Оператор: выбор парного кейса/источника, scope/oracle, разработка renewal, две ошибки подготовки запроса выше, служебный запуск и standing Core responses. Framework: одноопционные фазы census/refresh, payload compilation, проверки/журнал. Модель: собственные source/tool selections, retrieval старого census recipe, readiness, новый send/own fetch и корректный ограниченный итог. Это не свободный автономный Windows lifecycle.

Focused positive/negative fixture прошла; общий технический набор308/308 PASS `/tmp/v697-full-smoke-user.log`. Это не регресс301шага. Первый запуск suite под sudo не выполнился из-за истёкшего credential cache, затем обычный непривилегированный runner прошёл; настройки/права не менялись. После дополнительного усиления fingerprint-проверки нужен финальный suite; его результат фиксируется в CHANGELOG, не подменяется предыдущим.

Память: отдельный candidate/document_review event REGUSER701 с snapshot/dedup/integrity/retrieval; это не обновление весов/verified promotion. Последующее применение именно нового recipe локальной моделью ещё не принято (реальный699 использовал старый census recipe и подготовленный новый контракт). Источники689/691 не изменять/не переиндексировать.

Далее по порядку: закончить полноценный Windows per-user кейс после подтверждённых безопасных предусловий; текущие ранние install/update/Tray blockers не скрывать. Кейс6 обеих ОС требует удаление/переустановку, кейс7 сертификаты, Astra8 firewall — запрещённые части фиксируются BLOCKED, не выполняются буквально. Затем следующий разрешённый сценарий с новым oracle. Финальный «с нуля» означает новые Jobs/evidence/наблюдения в отдельной кампании без удаления истории/памяти/сертификатов или переустановки готовых ядер ради счётчика. Jira/Zephyr полностью не тронуты; automation остаётся PAUSED.
