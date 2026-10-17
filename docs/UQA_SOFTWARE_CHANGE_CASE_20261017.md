# US-T114: полный сценарий изменения ПО на Astra

REGCHANGE689. Один полный бизнес-сценарий US-T114: 3/3 шага на Astra. Это подготовленный workflow с модельным выбором ограниченных действий, НЕ свободное самостоятельное планирование. Полные подготовленные сценарии: Windows0/21, Astra1/19, всего1/40. Остальные частичные чтения не становятся пройденными шагами; свободная автономность циклов не принята.

## Источник и oracle

US-C347, кейс5 US-T114 v1.0, три шага: установка нового ПО → softAudit → новое ПО через GET /api/v1/cis. Архив agent-1.3.27-20261016 неизменён, manifest SHA256 cd80d283ecace073ee80e36fc39274265f6c173948cec4d07374e64af7899ec8. Telegram — пример ПО, старые Windows-пути/версии не oracle Astra. Ни apt/dnf update, ни изменения существующего ПО, прав или безопасности не разрешались/не выполнялись.

UQA сама прочитала все3шага: Job20261017-125655-57c3f85e/tc-949a4b42, source ev-13d18d7578d7, coverage ev-bf7e0e5d1664/ev-79b11010693a/ev-fb9bfecc57a0. Первый unprivileged запуск не открыл LLM lock; тот же Job продолжен под штатной service execution identity, без изменения прав. Это вмешательство оператора, не навык модели.

## Принятый результат

Parent Job20261017-132524-dd45d6c2/tc-1605735c, canonical ev-8c2d447afa2b, принятый model report ev-959882d99659. Модель: PASS, source_steps3, ordinary_freeform_autonomy=false. Пакет uqa-regression-probe-20261017-v2, версия0.0.1, artifact SHA256 472a6dca9aa4a35a36a721a9bfa71b873feea6e5e0af1b6cd919b6e35bee978b.

| Проверка | Собственный Job/evidence | Actual |
| --- | --- | --- |
| До установки | Parent ev-8f3f3504f97c | Все2002 scoped software записи прочитаны, точной строки пакета нет ни в одном поле |
| Шаг1 | Job20261017-132524-7650bfd6/tc-eeae5bb3/ev-5d796978d6da | Task6fa4f904-8ab1-4fd6-b966-81947cecf00c: absent-before, dpkg0, installed exact version, harmless probe marker; journal VERIFIED |
| Шаг2 | Job20261017-132524-3384691f/tc-b6705060/ev-d2e0a3a42062 | Taske33cf258-a5f2-40b3-b869-15ab31e2d87e: свой fresh full softAudit с точными именем/версией; journal VERIFIED |
| Шаг3 | Parent ev-8c2d447afa2b | Новый software CI3cc9c1ba-0124-47f6-a32f-49cd6e46eee4, created2026-10-17T13:27:53.513456Z, exact detail.name/version и собственные detected_at_id/parent_id |

Native→softAudit44секунды, predeclared максимум1800. Install stdout SHA256 2eb654084faa4aa40d92103cdd43959bbc2ce39006c7e739a34f098d2b10bd7d; softAudit data SHA256 e6eb06ff1cadf9cfba4a144f34589062c512e5880bbff1de5329f9d3d2b2f4eab; CMDB rows SHA256 7293d6832db912b57f7f87d5c641a9dd69d80e6c00563b3b065356d2af3b1d134. GET сверяет те же own task IDs/machine_uid/created/processed_at/hashes. Не ACK/HTTP200/число строк/структура XML вместо бизнес-проверки.

## Рецепт и границы

1. Полностью прочитать source/expected/testdata/предусловия, проверить own coverage. Вопрос о способе не разрешает установку.
2. До мутации закрепить новый owned пакет, ОС/агента/КЕ, имя/версию, artifact/payload hashes и oracle. Только новый каталог и harmless executable, без deps/scripts/triggers. Существующий /opt не включать в архив как изменяемый каталог.
3. Реально проверить unpack/query/probe в disposable root до доставки; анализ tar сам по себе недостаточен. Сохранять артефакты.
4. Проверить online/core/ОС/точные loaded executeCommand и softAudit. При необходимости одна journaled pluginAudit; готовый плагин не доставлять заново.
5. Один Core WRITE/locked scope/journal CREATE и own fresh full. Pending — GET того же task; uncertain — STOP, без resend/rekey.
6. После native установки — одна свежая softAudit и own full, точные имя/версия. Прежний технический US-T102 subset adapter/report остаётся отдельным BLOCKED; parent US-T114 имеет собственный полный3step oracle.
7. CMDB GET /api/v1/cis, operationId get_cis_api_v1_cis_get, ci_class=software, detected_at_id=agent UUID, limit/offset/use_counter, полная пагинация. В установленной версии имя/версия в detail.name/detail.version; верхний name может быть null. parent_id=CI UUID. Первый name-only matcher не принят как отсутствие; затем проверены все поля всех scoped rows.
8. Требовать новую неархивную запись после baseline, exact version/agent/CI links и own verified receipts/hashes. Unknown/неполнота/расхождение — BLOCKED/FAIL без нормализации. Jira/Zephyr не открывать/не менять.

Текущий run: core1.3.27, executeCommand1.4.0, softAudit1.3.8 проверены readiness. Выделенная Astra1.8, точный текущий OS build не перепроверен; server/frontend unknown. qwen3:14b digest bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8/context24576/RTX5070Ti не менялись.

## Неудачная подготовка и вмешательства

Original parent Job20261017-130158-6c943e0e/tc-4d0fe295 BLOCKED. Мой v1 .deb не содержал directory entry. Install Job20261017-130158-92f80a6e/tc-479081b3, task7fab2b5b-503c-4909-8627-d4ecb4f52cdf: absent_before=true, install_attempted=true, dpkg_exit1, dpkg_install_failed_no_repair. Operator same-task READ diagnosis ev-4a01d860fdba. Ошибочный rejection штатного failure JSON исправлен, но success predicate не ослаблен; исходный CODE/SHA4003a2fb8c528bd7b64b246562405010c2169f2f41f9285f0fb83bc1164853f2c не изменён/не повторён. Старый awaiting_verification journal сохранён, не переаттестован задним числом.

Isolated root /tmp/uqa-case114-archive-p_ybe_3n воспроизвёл exact dpkg1/missing directory; исправленный НОВЫЙ v2 прошёл unpack/query/probe в /tmp/uqa-case114-archive-hmt60ski. Реальные системные пакеты UQA-server не менялись; корни/артефакты сохранены. Это ошибка моей fixture, не developer-confirmed UCbug. v1 объект на Astra не удалён/не переустановлен, не использовать как PASS; остаётся owned residue до будущей явно разрешённой уборки.

Operator: case/fixture/scope/oracle/code, source/child Jobs, служебный запуск, один v1 read-only разбор, standing Core confirmations (v1 pluginAudit+install, v2 install+softAudit). Не самосогласование модели. Framework: одноопционные фазы, compiled fixed payload, child handoff, допустимый каталог, journal, canonical comparison. Модель: собственное чтение/coverage, каждый tool selection, own fetch и корректный итог. Прямых операторских продуктовых мутаций нет; новый687 run без промежуточной операторской смены кода/инструкций после старта. Это не обычный human freeform prompt → самостоятельный выбор всего lifecycle.

## Предыдущая Astra-проверка и память

679 закончена: Job20261017-124159-3d0978d0/tc-983274f2/ev-938c69b30494, own US-T102step6 source/coverage/JSON inspector/cell; корректно выявлен невалидный старый JSON с inline comment. Windows679 Job20261017-124115-676f0c92/tc-3f88306b/ev-ded4c1cba18a — own чтение валидного JSON. Оба source-only/BLOCKED,0agent tasks, не runtime networkDeviceAudit/полные кейсы.

Сохранение: reviewed candidate/document_review в существующих product/index DB, snapshot/dedup/integrity/retrieval; не semantic verified promotion и не обновление весов. Старые669/другие events не повторять. Следующий критерий — перенос этого рецепта на собственный многоинструментальный выбор без next-tool диктата при том же oracle/safety. Другие кейсы/VNC/Tray/логи/collections/procedures/policies в этом заходе не запускались.
