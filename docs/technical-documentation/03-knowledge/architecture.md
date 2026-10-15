# Архитектура общей памяти

## Три слоя

Предметная выборка v195 сохраняет прежний бюджет трёх запросов. Для задачи коллекции с RAM/CPU выбираются разделы логики условий и аппаратных единиц/агрегатов; общий маршрут открытия используется при оставшемся бюджете. Отрицательные ограничения не считаются просьбой изучать тему. Это настройка продуктового адаптера, не разрешение действий и не новая модель знаний в Core. Свежий context-only тест локальной модели прошёл9/9 после исправления пропущенного RAM-раздела (раньше8/9, RAM unknown). Он подтверждает применение извлечённого источника в справочной задаче, но не автономное построение/сохранение фильтра через UI и не исправление None в таблицах.

1. Источники и история: официальные руководства, разрешённый код в будущем, Jobs/evidence и результаты.
2. Канонические знания: атомарные утверждения, scope, происхождение, варианты и подтверждения.
3. Индексы: нынешний FTS5 документов; будущие semantic/code/relationship projections после оценки качества.

Документный knowledge_search уже работает. Старый product store содержит facts/scopes/confirmations; безопасный retrieval поддерживает только подтверждённые ui_navigation/ui_api_binding текущей идентичности. Новые knowledge_v1_* таблицы первого этапа добавляются в ту же product knowledge DB, не заменяя прежние таблицы.

Новые записи v1 не попадают автоматически в существующий verified retrieval/FTS. Candidate не равен verified; unknown scope не означает совместимость с latest. Никакой новый model tool, automatic exporter или promotion не подключён.

v176–v177 подключают отдельный declared_product_context к существующему knowledge_search: восемь reviewed правил из официального руководства по коллекциям, политикам и процедурам. Source bytes/hash перепроверяются, конфликты исключаются; произвольная prose не переносится. Runtime applicability остаётся непроверенной, evidence_for_pass=false. Короткое documentary grounding перед managed turn помогает выбирать раздел; оно не предоставляет WRITE. Live model-context проверка прошла, но первые автономные collection прогоны BLOCKED по навигации, поэтому полный UI-регресс не объявлен готовым.

## Рост

v192: два runtime-кандидата формата процедуры доступны через отдельный historical observed_product_context в knowledge_search. Перед выдачей проверяются source hash, native eligibility, связанные наблюдения и фактическая структура тела. Конфликты и неподдерживаемый scope/значения/режимы исключаются; произвольный текст/команды/XML не передаются. История возвращает execution_modes, но кандидаты не превращаются в verified факты или доказательство текущей совместимости.

Технические проверки226/226 и wiring прошли. Контекстная проверка локальной модели полностью не прошла:5/6 критериев в диагностическом повторе, точный format label неверен, ограничения сохранены. Это ограничение точности ответа, не доказанный баг продукта или разрешение ослабить verifier. Shared read API/ACL для других агентов и общий automatic exporter ещё не реализованы.

v191: первые два runtime-observation кандидата формата сохранённой процедуры записаны в каноническую product knowledge DB, не только в Markdown/FTS. Источник — новый native GET с наблюдением; versions/OS явно unknown, operator-assisted mode сохранён. Consistent snapshot, legacy preservation, dedup и history readback проверены. Автоматическая выдача этих кандидатов модели пока не подключена: нельзя подменять source integrity семантической проверкой или применимостью к текущей версии. Индексированный опыт по-прежнему отдельный слой.

v186: native активное меню — кратковременный UI-контекст, не новый продуктовый факт и не самостоятельный источник verified knowledge. Названия/роли/disabled-state bounded и проверяются; состояние прошлого turn не применяется. Предложенный click vocabulary не выполняет действие, не меняет policy и не доказывает готовность редактора. Live model увидела Add procedure, но пропустила переход; Job20261014-233520-79fd039b BLOCKED без ресурсов/операций. Это отрицательный опыт текущего исполнения, не подтверждённый баг UC и не основание рекомендовать обновление продукта.

v183: reviewed policy/procedure field maps находятся через indexed experience queries, отдельно от source-rechecked official declarations. Индекс обновлён одним источником с consistent snapshot, 1148 остальных chunks неизменны. Operator-only provenance и unknown runtime applicability не дают business PASS. Procedure SVG/treeitem редактор требует отдельного block/edge/save contract; обычный form census недостаточен. Context-only local model probe обнаружил неточные labels/role, хотя safety limits удержаны; полноценный автономный workflow не объявлен готовым.

v181–v182 сохраняют bounded location hints при history compaction и различают native отказ до клика от uncertain send. Только in-process marker может дать not_sent, не JSON; retry сохраняет policy и exact binding. Installed runner222/222PASS. Операторская форма политики подтверждает лишь текущую карту полей; не автономное создание. Отдельные старые uncertain/unbound launcher операции сохраняются для аудита, не переписываются задним числом. Runtime версия frontend здесь не подтверждена.

v179–v180: наблюдённая карта коллекционного editor выделена в отдельный устойчивый раздел и находится по semantic query без номера релиза. Три дополнительные candidate declarations дают bounded control-location hint при ошибке поиска поля; источник повторно проверяется по hash, unknown applicability не становится permission или PASS. Generic new-editor navigation сохраняет только same-session/origin native entry proof, не authority на данные. Full runner221/221 проверяет технический слой; это не число принятых реальных тест-кейсов UC.

Повторное событие с тем же ID/payload не добавляется. Новый run с тем же утверждением добавляет историю/подтверждение, но не копию variant. При том же document hash повтор не увеличивает число независимых источников. Runtime confirmations группируются по Job, а не числу evidence внутри одного прогона.

История событий всё равно растёт; её размер измеряется отдельно от knowledge cards. Retention/архивирование требуют согласования и не разрешают очистку Jobs/секретов. Индексы перестраиваемы, первичные источники не должны зависеть от одного FTS файла.

Подробнее: [контракт](record-contract-v1.md), [источники и официальные документы](sources-and-official-documents.md), [границы следующего этапа](roadmap.md).
