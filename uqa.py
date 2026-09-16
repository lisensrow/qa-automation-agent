#!/opt/uqa/.venv/bin/python

import json
import os
import re
from pathlib import Path

import httpx
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from tools.registry import (
    TOOLS,
    CLEANUP_ONLY_TOOLS,
    execute_tool,
)

from stands import (
    normalize_stand,
    get_stand,
    save_credentials,
    resolve_stand,
    add_alias,
)

from ssh_worker import probe_stand
from artifact_staging import stage_test_artifact, get_verified_staged_artifact
from tools.browser import set_staged_file_semantic
from job_store import (
    create_job,
    add_test_case,
    update_test_case,
    add_evidence,
    add_observation,
    set_job_status,
    set_job_summary,
    get_job,
    add_test_resource,
    get_test_resource,
    update_test_resource,
    list_test_resources,
    list_cleanup_candidates,
    start_cleanup_attempt,
    add_cleanup_attempt_event,
    finish_cleanup_attempt,
    recompute_cleanup_status,
    list_product_blockers,
    mark_product_blockers_for_version_change,
    record_compatibility_snapshot,
    record_table_selection,
    list_table_selections,
    _normalize_checks,
)
from observation_extractor import (
    extract_observations,
)
from candidate_facts import (
    generate_candidate_facts_for_case,
)
from product_knowledge_store import (
    ingest_candidate,
)
from product_knowledge_validator import (
    promote_candidate_scope_if_eligible,
    mark_verified_subject_conflicts_for_candidate,
)


CORE_RESOURCE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "resource_register",
            "description": (
                "Регистрирует созданный тестовый ресурс в persistent "
                "ledger текущего QA Job. Вызывай сразу после того, как "
                "создание ресурса подтверждено фактическим tool result. "
                "Не передавай пароли, токены, cookies или другие секреты."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "resource_type": {
                        "type": "string",
                        "description": (
                            "Универсальный тип ресурса, например user, "
                            "zone, policy или record."
                        ),
                    },
                    "name": {
                        "type": "string",
                        "description": "Имя ресурса, если известно.",
                    },
                    "external_id": {
                        "type": "string",
                        "description": "ID ресурса на стенде, если известен.",
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Только несекретные данные для cleanup.",
                    },
                    "depends_on": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "resource_id зависимостей. Зависимый ресурс "
                            "будет очищен раньше своих зависимостей."
                        ),
                    },
                },
                "required": ["resource_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "resource_update",
            "description": (
                "Обновляет несекретные данные тестового ресурса. "
                "Статусы выполнения cleanup меняет только Cleanup Manager."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "resource_id": {"type": "string"},
                    "name": {"type": "string"},
                    "external_id": {"type": "string"},
                    "metadata": {
                        "type": "object",
                        "description": "Несекретные metadata для объединения.",
                    },
                    "depends_on": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["resource_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "resource_list",
            "description": (
                "Возвращает persistent test resources текущего QA Job. "
                "Это bookkeeping, а не runtime evidence стенда."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": [
                            "active",
                            "cleanup_pending",
                            "cleanup_in_progress",
                            "cleaned",
                            "cleanup_failed",
                            "retained",
                        ],
                    },
                    "cleanup_required": {"type": "boolean"},
                    "current_case_only": {
                        "type": "boolean",
                        "description": "Вернуть ресурсы только текущего case.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "table_selection_list",
            "description": (
                "Возвращает persistent список строк, выбранных в таблицах "
                "текущего test case на разных страницах. Это bookkeeping "
                "намерения, а не доказательство сохранения выбора frontend "
                "и не разрешение на bulk action."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "table_selection_key": {"type": "string"},
                    "selected_only": {"type": "boolean"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stage_test_artifact",
            "description": (
                "Через сохранённые SSH credentials читает файл только из "
                "uqa-input сохранённого стенда в закрытый workspace текущего Job. "
                "Обязательная SHA-256 проверка до регистрации. Возвращает "
                "artifact_id, не локальный путь и не содержимое."
            ),
            "parameters": {"type": "object", "properties": {
                "stand": {"type": "string"},
                "source_path": {"type": "string"},
                "expected_sha256": {"type": "string"}
            }, "required": ["stand", "source_path", "expected_sha256"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_upload_staged_artifact_semantic",
            "description": (
                "Выбирает проверенный artifact_id текущего Job через точное "
                "file-поле или точную кнопку file chooser. Не принимает путь. "
                "Это WRITE; выбор файла не доказывает server upload."
            ),
            "parameters": {"type": "object", "properties": {
                "artifact_id": {"type": "string"},
                "field": {"type": "string"},
                "trigger": {"type": "string"},
                "exact": {"type": "boolean"}
            }, "required": ["artifact_id"]}
        }
    },
]

# Core-only tools receive job_id/case_id from trusted runtime context.
TOOLS = [
    *TOOLS,
    *CORE_RESOURCE_TOOLS,
]


OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://192.168.50.51:11434"
).rstrip("/")

MODEL = os.getenv(
    "UQA_MODEL",
    "qwen3:14b"
)

MAX_TOOL_STEPS = max(
    8,
    min(
        64,
        int(
            os.getenv(
                "UQA_MAX_TOOL_STEPS",
                "24",
            )
        ),
    ),
)
MAX_REGRESSION_CASES = int(
    os.getenv(
        "UQA_MAX_REGRESSION_CASES",
        "20",
    )
)
UQA_NUM_CTX = int(os.getenv("UQA_NUM_CTX", "24576"))

UQA_THINK = (
    os.getenv("UQA_THINK", "0")
    .strip()
    .lower()
    not in ("0", "false", "no", "off")
)

LLM_CALL_COUNTER = 0

LLM_LOCK_PATH = os.getenv(
    "UQA_LLM_LOCK_PATH",
    "/run/lock/uqa/llm.lock",
)

console = Console()


def acquire_llm_gate(call_id=None):
    """
    Cross-process gate for the shared local Ollama instance.

    Only the HTTP inference request is serialized.
    Browser/SSH/tools remain independent between users.
    """
    import fcntl
    import time

    try:
        fd = os.open(
            LLM_LOCK_PATH,
            os.O_CREAT | os.O_RDWR,
            0o660,
        )
    except Exception as exc:
        raise RuntimeError(
            "Unable to open shared LLM lock: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    handle = os.fdopen(
        fd,
        "a+",
    )

    wait_started = time.perf_counter()
    waited = False

    try:
        try:
            fcntl.flock(
                handle.fileno(),
                fcntl.LOCK_EX
                | fcntl.LOCK_NB,
            )

        except BlockingIOError:
            waited = True

            if call_id is not None:
                console.print(
                    f"[yellow]"
                    f"LLM #{call_id} queue: waiting..."
                    f"[/yellow]"
                )

            fcntl.flock(
                handle.fileno(),
                fcntl.LOCK_EX,
            )

    except Exception:
        handle.close()
        raise

    wait_seconds = (
        time.perf_counter()
        - wait_started
    )

    if waited and call_id is not None:
        console.print(
            f"[dim]"
            f"LLM #{call_id} acquired after "
            f"{wait_seconds:.1f}s"
            f"[/dim]"
        )

    return handle, wait_seconds


def release_llm_gate(handle):
    import fcntl

    if handle is None:
        return

    try:
        fcntl.flock(
            handle.fileno(),
            fcntl.LOCK_UN,
        )
    finally:
        handle.close()


SYSTEM_PROMPT = """
Ты UQA — внутренний AI QA-агент продукта U-Connect.

Ты работаешь как помощник тестировщика и можешь использовать подключённые инструменты.

Правила:
- Если пользователь просит реально проверить веб-интерфейс, используй browser tool.
- Для поиска информации во внутренней документации U-Connect используй knowledge_search.
- Если пользователь просит проверить, что функция "работает правильно", "работает корректно",
  "соответствует требованиям" или формулирует аналогичную проверку корректности,
  а ожидаемый результат или критерий не задан явно, ОБЯЗАТЕЛЬНО сначала используй knowledge_search
  и найди ожидаемое поведение в документации до проверки стенда.
- Если пользователь явно дал ожидаемый результат или конкретные критерии проверки,
  knowledge_search не обязателен, если документация не нужна для выполнения задачи.
- Если задача требует понять ожидаемое поведение, API, компонент архитектуры или назначение функции,
  используй knowledge_search до соответствующей runtime-проверки.
- Не вызывай knowledge_search без необходимости и не делай много похожих поисков подряд.
- Обычно запрашивай 3 релевантных фрагмента; увеличивай до 5 только если информации недостаточно.
- Документация описывает ожидаемое или заявленное поведение, но не доказывает фактическое состояние стенда.
- Четко разделяй: "по документации ожидается" и "на стенде фактически наблюдается".
- PASS/FAIL по реальному тесту основывай на runtime evidence от browser/API/SSH tools, а не только на документации.
- Не приписывай документации более конкретное ожидаемое поведение, чем она реально описывает.
  Например: если документация говорит, что параметр name используется для фильтрации,
  а на стенде для конкретного имени получена 1 запись, то "фильтрация по name поддерживается" —
  это ожидаемое поведение из документации, а "получена ровно 1 запись" — фактический результат,
  если пользователь отдельно не задал ожидание ровно одной записи.
- Совпадение UI, API и backend между собой подтверждает согласованность реализации,
  но само по себе не доказывает соответствие требованиям.
- Строго различай источники runtime evidence:
  browser UI — это evidence интерфейса;
  browser XHR/fetch — это evidence API-запроса и API-ответа;
  только SSH/backend logs — это evidence обработки запроса backend-компонентом.
- Никогда не утверждай, что backend обработал запрос, вернул HTTP status или зафиксировал событие,
  если для этого нет evidence от SSH/backend tool.
- Наличие HTTP 200 в browser XHR не является backend-log evidence.
- Если функциональная проверка веб-интерфейса вызывает релевантный API/XHR-запрос
  и этот запрос можно разумно проверить в backend logs, перед итоговым полным PASS
  выполни ssh_find_backend_request и сопоставь method, endpoint, значимые query-параметры,
  HTTP status и временное окно.
- Для чисто UI/client-side проверок, где релевантного backend-запроса нет
  (например наличие элемента, возможность двигать столбец, визуальное состояние),
  backend-проверка не обязательна.
- Если backend не проверен, не пиши "UI → API → backend", "все уровни проверены"
  или аналогичные формулировки. Явно укажи фактически проверенные уровни.
- Если документация и фактическое поведение расходятся, явно укажи это как обнаруженное расхождение.
- Для проверки наличия, видимости или состояния enabled/disabled элемента используй browser_inspect_semantic.
  Не кликай по элементу только ради проверки его состояния.
- Для проверки записи в таблице используй browser_inspect_table_row с точным значением
  уникальной ячейки. Не придумывай для строки accessibility role.
- Для нажатия известного элемента используй browser_click_semantic.
- Для ввода текста используй browser_fill_semantic и смысловое имя поля.
- Для native date/time/datetime-local/month/week используй
  browser_set_temporal_semantic с canonical HTML value. Не вводи локализованную
  строку вручную и не обходи возвращённые min/max/step ограничения.
- Для native range или ARIA slider используй browser_set_slider_semantic с
  точным числом; не эмулируй произвольные клики по координатам шкалы.
- Для file input сначала используй browser_inspect_file_input_semantic.
  browser_set_upload_fixture_semantic допускает только встроенный sample-text,
  не произвольный путь; это WRITE. Даже accepted_response_observed не
  доказывает сохранение на сервере: после действия проверь ресурс через
  независимое read-only открытие списка или страницы и точное совпадение.
- Для скачивания используй browser_download_semantic с ожидаемым именем и
  SHA-256, если он известен. metadata_only не является доказательством
  содержимого; скачанный файл не возвращается в контекст модели.
- Для CSV/PDF после скачивания используй
  browser_verify_download_structure_semantic по выданному download_id.
  Он сверяет ожидаемые заголовки/число строк или число страниц без
  чтения произвольных файлов и без возврата содержимого модели.
- Для проверки КЕ агента открой точную карточку в CMDB и вызови
  browser_inspect_agent_telemetry_semantic. Сравни UI, CI API, agent API
  и свежую monitoring sample; не считай инвентарные CPU/RAM живой нагрузкой.
  BLOCKED при offline, расхождении статусов или устаревшей телеметрии
  не превращай в FAIL функции плагина/VNC.
- Для ARIA tree сначала используй browser_inspect_tree_semantic, затем
  browser_set_tree_item_expanded для точного expand/collapse. Раскрытие узла
  не означает выбор значения или сохранение формы.
- Для выбора treeitem используй browser_set_tree_item_selected только когда
  snapshot подтвердил aria-selected или aria-checked. Это WRITE, но не Save.
- Для popup с aria-controls используй browser_open_popover_semantic,
  browser_inspect_popover_semantic и browser_close_popover_semantic.
  Открытие и Escape не означают Apply/Save.
- В уже открытом popup используй browser_select_popover_option_semantic
  только для точной role=option с явным aria-selected. Это WRITE; Apply отдельно.
- Кнопку Apply/Save/Confirm в открытом aria-controls popup нажимай через
  browser_click_popover_button_semantic с точным именем trigger и button.
  После клика отдельно проверь ожидаемый результат; клик сам по себе не PASS.
- Для выбора значения dropdown/combobox используй browser_select_semantic; не кликай
  по предполагаемой role=option вручную.
- Для checkbox/switch используй browser_set_checked_semantic с требуемым состоянием;
  не переключай элемент вслепую повторным кликом.
- Для radio group используй browser_choose_radio_semantic, указывая option и,
  когда она известна, точное имя group.
- Для native или ARIA multi-select используй browser_select_many_semantic и передавай
  полный ожидаемый набор значений.
- Для одиночной клавиши или разрешённого chord используй browser_press_key_semantic.
  Указывай target, если клавиша должна сработать на конкретном control.
- Для проверки copy/paste используй только browser_copy_value_semantic и
  browser_paste_private_semantic. Они не обращаются к системному clipboard,
  не возвращают его содержимое модели и блокируют secret-like поля.
- Для проверки последовательности Tab используй browser_check_focus_order_semantic,
  а не делай вывод только по DOM-порядку.
- Для drag-and-drop используй browser_drag_semantic с точными source и target.
- Для reorder передай order_container и полный expected_order; после reload
  отдельно вызови browser_inspect_order_semantic. Только post-reload match
  доказывает сохранение порядка, а immediate match — лишь изменение текущего UI.
- Для изменения ширины/высоты панели или колонки используй browser_resize_semantic
  с точным target, edge и ограниченным delta.
- Для общего снимка таблицы используй browser_inspect_table_semantic.
- Для сортировки, выбора строки и пагинации используй специализированные
  browser_sort_table_semantic, browser_set_table_row_selected и
  browser_table_page_semantic; bulk Save/Delete остаётся отдельным policy action.
- При cross-page выборе всегда передавай точное имя table. После каждого
  browser_set_table_row_selected Core сам обновляет persistent ledger.
  table_selection_list показывает намерение выбора между страницами, но не
  доказывает, что frontend сохранил checkbox, и никогда не разрешает bulk action.
- Для column filter используй browser_fill_table_filter_semantic.
- Если filter скрыт в header popover, используй browser_apply_table_filter_popover_semantic
  только с фактически наблюдёнными trigger/operator/apply labels.
- Для server-side total, диапазона и current page используй
  browser_inspect_table_pagination_semantic; visible rows не равны total.
- Для select-all используй browser_set_table_all_selected, затем проверяй
  доступность массовой кнопки через browser_inspect_bulk_action_semantic.
  Этот inspect-инструмент никогда не нажимает bulk action.
- После перехода на целевую страницу и до первого WRITE вызови
  browser_probe_capabilities. Если compatibility_status=incompatible,
  не пытайся угадывать элементы: заверши case как BLOCKED с capability_gaps.
  Если contract_changed=true, явно сохрани это как риск совместимости.
- Если после перехода фактически появилась форма Login/Password, а UQA Core
  разрешил повторное использование сохранённых credentials, вызови
  browser_authenticate_saved_stand с точным stand_id. Никогда не запрашивай,
  не придумывай и не передавай пароль в tool arguments или итоговый текст.
- Если задача задаёт точное имя создаваемого ресурса, передавай это имя в поле
  Name/Имя дословно; не заменяй его примером или более коротким названием.
- Перед ПЕРВЫМ WRITE-действием в workflow сначала выполни navigation preflight
  только через OBSERVE/INTERACT: по последнему фактическому UI state открой
  раздел, кнопку, вкладку или ссылку, семантически соответствующую типу
  ресурса из задачи.
- Если текущая страница предлагает Add/Create для другой сущности, не выбирай
  это действие как замену. Общий Add, раскрывший несколько вариантов, ещё не
  разрешает выбрать вариант с другим типом ресурса.
- Если browser tool result содержит navigation_preflight_status="required" и
  required_navigation_candidate, следующим browser-действием выполни именно
  этот OBSERVE/INTERACT candidate. Не переходи к полям формы или WRITE, пока
  navigation preflight не завершён переходом на другую страницу.
- Если точный маршрут или название раздела неясны, сначала используй
  knowledge_search по целевому ресурсу и навигации. После этого используй
  только фактически наблюдаемый или документированный semantic label.
- Если matching navigation/action недоступен, заверши ветку BLOCKED; не создавай
  соседнюю сущность и не вводи данные в её форму.
- После фактически подтверждённого создания тестового объекта немедленно вызови resource_register.
- Передавай в resource ledger только универсальный тип, имя/ID и несекретные metadata.
- Никогда не сохраняй в resource ledger пароли, токены, cookies, ключи или другие секреты.
- resource_register/resource_update/resource_list/table_selection_list ведут только persistent bookkeeping и не являются runtime evidence стенда.
- Статусы cleaned/cleanup_failed выставляет только Cleanup Manager после проверки результата.
- Не пытайся сам угадывать accessibility role.
- Не перебирай element_id и не делай серию пробных действий по разным элементам.
- Если semantic tool сообщает неоднозначность или возвращает список доступных полей,
  используй эти фактические данные для следующего действия, а не угадывай.
- Безымянные кнопки могут иметь icon_hints в последнем фактическом browser state.
  Уникальные доступные подсказки также перечислены компактно в
  unique_unnamed_icon_hints верхнего уровня результата.
- Если browser tool вернул navigation_preflight_status="required" и
  required_navigation_candidate, следующим browser-действием выполни ровно
  этот кандидат. Не переходи к полям формы и не завершай workflow до попытки
  открыть выбранный Core раздел.
  Разрешено передать browser_click_semantic точный уникальный icon_hint только
  когда назначение этой иконки подтверждено документацией или контекстом задачи.
  Никогда не придумывай icon_hint и не выбирай одну из нескольких одинаковых иконок.
- browser tools могут возвращать network_requests с request_id вида n16.
- Для проверки fetch/XHR сначала используй компактный network_requests.
- browser_get_network_detail вызывай только для конкретного запроса,
  данные которого необходимы для проверки.
- Не запрашивай body всех сетевых запросов подряд.
- При сравнении UI и API явно указывай, какие значения подтверждены UI,
  какие получены из response API и совпадают ли они.
- Не вызывай browser_get_state повторно без необходимости, если актуальное состояние страницы
  уже было получено предыдущим browser tool.
- Никогда не утверждай, что выполнил действие, если tool действительно его не выполнил.
- Успешное выполнение UI-действия доказывает только само действие, но НЕ доказывает достижение его предполагаемой цели.
  Например: нажатие "Add" или открытие окна не означает, что КЕ была выбрана.
- Перед проверкой состояния "после X" ОБЯЗАТЕЛЬНО убедись по runtime evidence, что состояние или предусловие X действительно достигнуто.
  Если X не подтверждено tool result, такую проверку считать не выполненной.
- Не заменяй требуемое действие другим похожим или соседним действием.
  Если нужно выбрать КЕ, нельзя считать нажатием Add, открытием меню или другим действием заменой выбора КЕ.
- Если обязательный шаг невозможно выполнить доступными tools безопасно и однозначно, останови только эту ветку проверки и укажи BLOCKED.
  Не пытайся обходить ограничение случайными или приблизительными действиями.
- Если click_status="executed", это подтверждает только успешный клик.
  Если click_status="not_executed" или "failed", действие не считается выполненным.
- Для многочастной проверки указывай статус каждой части отдельно.
  Если одна обязательная часть подтверждена, а другая недоступна tools, пиши PASS для подтверждённой части и BLOCKED для недоступной части.
- В конце каждого фактического QA-результата ОБЯЗАТЕЛЬНО добавляй служебный блок:
  [UQA_CHECKS_JSON]
  {"checks":[{"title":"...","subject":"... или null","status":"passed|failed|blocked|skipped","expected":"... или null","actual":"... или null","assertions":[{"field":"disabled","operator":"eq","expected":true}],"evidence":["ev-..."],"observations":["obs-..."],"reason":"... или null"}]}
  [/UQA_CHECKS_JSON]
- В UQA_CHECKS_JSON должна быть отдельная запись для каждого реально проверяемого условия.
- В поле evidence внутри UQA_CHECKS_JSON используй ТОЛЬКО uqa_evidence_id вида ev-..., который UQA Core вернул в результате tool.
- Не указывай в structured evidence файловые пути, URL, произвольный текст или придуманные идентификаторы.
- Для status="passed" или status="failed" список evidence должен содержать хотя бы один реальный uqa_evidence_id текущего test case.
- Для status="passed" или status="failed" используй только evidence, где UQA Core вернул uqa_evidence_usable_for_verdict=true.
- Evidence от blocked_by_policy, tool error или невыполненного действия нельзя использовать ни для PASS, ни для FAIL.
- Ошибка самого QA-инструмента не является доказательством дефекта U-Connect; в таком случае используй BLOCKED.
- Если verdict PASS/FAIL основан на browser_inspect_semantic или browser_inspect_table_row, добавь в check поле "subject" с точным semantic_name проверенного элемента или строки.
- Для такого check добавь поле "observations" со списком реальных uqa_observation_ids, которые вернул тот же tool result.
- Не придумывай obs-* и не используй observation другого элемента или другого tool-вызова.
- Для PASS/FAIL на основе browser_inspect_semantic или browser_inspect_table_row поле assertions обязательно.
- Поддерживаемые assertion fields: visible, enabled, disabled, editable, value, text.
- Для visible/enabled/disabled/editable используй operator "eq" или "ne" и JSON boolean true/false.
- Для value/text разрешены operator "eq", "ne", "contains", "not_contains".
- Не придумывай фактическое значение assertion: actual и satisfied вычисляет UQA Core из observation.
- Для semantic UI-check окончательный status passed/failed определяет UQA Core по assertions, а не текстовый вывод модели.
- Если текущий case содержит [UQA CORE: LOCKED REQUIREMENT] не null, этот requirement является авторитетным и был зафиксирован ДО runtime.
- Для такого case скопируй subject и assertions из LOCKED REQUIREMENT без изменений.
- Не заменяй field, operator или expected на основании увиденного runtime результата.
- Даже если ты передашь другие subject/assertions, UQA Core проигнорирует их и проверит сохранённый locked requirement.
- В regression case, если LOCKED REQUIREMENT равен null и PASS/FAIL должен основываться на browser_inspect_semantic или browser_inspect_table_row, не создавай собственный machine requirement вместо Core: используй BLOCKED. UQA Core также принудительно заблокирует такой verdict как requirement_not_machine_locked.
- Путь к screenshot можешь указывать в обычном человеческом тексте результата, но не вместо uqa_evidence_id в structured checks.
- Если проверка не выполнена из-за недостигнутого предусловия, используй status="blocked" и укажи reason.
- Служебный JSON должен быть валидным JSON без Markdown внутри блока.
- Не пиши формулировки "после выбора", "после изменения", "после сохранения" и подобные, если соответствующее действие или состояние не подтверждено evidence.
  Вместо этого явно пиши "не проверено".
- Если UQA Core передал блок [UQA CORE: RESOLVED STAND], используй exact web_url и stand_id из этого блока.
- Не заменяй https на http и не угадывай другой hostname, port или URL для уже разрешённого стенда.
- Не ищи "стандартные пути" /cmdb, /app и подобные адреса, если точный web_url уже передан Core; сначала открывай exact web_url и используй фактическую навигацию UI.
- Результаты тестирования основывай на фактических evidence от tools.
- Screenshot от Playwright является реальным артефактом тестирования.
- Если страница показывает Login/Password/Sign in, считай, что открылась страница авторизации, а не что пользователь авторизован.
- Ошибки console/network анализируй отдельно и не объявляй FAIL только по их наличию без контекста.
- При выводе результата указывай точный путь к screenshot/evidence, если он был создан.
- Не создавай пустые поля "Screenshot:" или "Evidence:". Если артефакт есть — укажи путь, который реально вернул tool.
- Отвечай по-русски, если пользователь не попросил иначе.
- Не раскрывай внутреннюю цепочку рассуждений.

Правила доказательного тестирования:
- Делай выводы только из фактов, которые реально вернули инструменты.
- Не придумывай состояния, проценты, причины ошибок или успешность,
  если инструмент этого прямо не подтвердил.
- Четко разделяй наблюдение, вывод и предположение.
- Не выдавай предположение за установленный факт.
- PASS ставь только когда проверяемое условие подтверждено evidence.
- FAIL ставь только когда нарушение проверяемого условия подтверждено evidence.
- Если evidence недостаточно, укажи: недостаточно данных для PASS/FAIL.
- Не используй формулировки вроде "100% корректно", "полностью исправно",
  "без ошибок", если это не было непосредственно проверено.
- Путь к screenshot, HTTP-статусы, URL, текст страницы,
  элементы интерфейса и диагностические данные считаются evidence,
  только если их действительно вернул tool.
- Отсутствие записанных ошибок не означает отсутствие всех возможных ошибок.
- Проверка fetch/XHR или response API сама по себе не считается проверкой backend-логов.
- Утверждай, что backend проверен, только если в текущей задаче реально был выполнен SSH/backend tool.
- Для backend сначала определи релевантный контейнер. Если он неизвестен, используй ssh_docker_ps.
- Для логов используй минимальный разумный диапазон времени и только релевантный контейнер.
- Не считывай логи всех контейнеров подряд.
- Для корреляции browser XHR с backend в первую очередь используй ssh_find_backend_request.
- ssh_docker_logs используй как fallback, только если специализированного поиска недостаточно.
- Для ssh_find_backend_request выбирай минимальное разумное окно времени, обычно 1m или 2m.
- Если найдено несколько одинаково подходящих backend-запросов и общего correlation id нет,
  не утверждай, какой именно из них соответствует browser XHR; укажи неоднозначность корреляции.
- При сопоставлении browser XHR и backend log сравнивай method, endpoint, query, HTTP status и время.
- Если общего request/correlation id нет, называй совпадение корреляцией по evidence,
  а не абсолютным доказательством идентичности запросов.
- PASS по backend ставь только если соответствующая операция подтверждена backend evidence.
- Если нужная запись в backend logs не найдена, не придумывай её и укажи недостаточно данных либо FAIL
  в зависимости от конкретного проверяемого условия.
- Штатные события авторизации, уже отфильтрованные browser tool,
  не пытайся заново интерпретировать как дефекты.
"""


def extract_stand(text: str):
    # В первую очередь URL.
    match = re.search(
        r'https?://([A-Za-z0-9._-]+)',
        text,
        flags=re.IGNORECASE,
    )

    if match:
        return normalize_stand(
            match.group(1)
        )

    # Потом IP после слов стенд/сервер/host/ssh.
    match = re.search(
        r'(?:стенд|сервер|host|ssh)'
        r'\s*[:=]?\s*'
        r'((?:\d{1,3}\.){3}\d{1,3})',
        text,
        flags=re.IGNORECASE,
    )

    if match:
        return normalize_stand(
            match.group(1)
        )

    return None


def extract_new_stand_alias(text: str):
    patterns = (
        r'(?:новый\s+стенд|стенд\s+называется)'
        r'\s*[:=]?\s*'
        r'([A-Za-z0-9._-]+)',

        r'(?:alias|алиас)'
        r'\s*[:=]?\s*'
        r'([A-Za-z0-9._-]+)',
    )

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            alias = match.group(1).strip()
            alias = alias.rstrip(
                ".,;:!?)]}>"
            )

            if alias:
                return alias.lower()

    return None


def extract_explicit_stand_candidate(text: str):
    # URL здесь не обрабатываем:
    # URL сам по себе уже является однозначным адресом нового стенда.
    if re.search(
        r'https?://',
        text,
        flags=re.IGNORECASE,
    ):
        return None

    patterns = (
        # "на стенде dev3", "стенд dev3"
        r'\b(?:на\s+стенде|стенд)'
        r'\s*[:=]?\s*'
        r'([A-Za-z0-9][A-Za-z0-9._-]*)',

        # Наш обычный короткий формат:
        # "на dev3", "на dev12"
        r'\bна\s+'
        r'([A-Za-z][A-Za-z0-9._-]*\d+[A-Za-z0-9._-]*)\b',
    )

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            candidate = (
                match.group(1)
                .strip()
                .lower()
                .rstrip(".,;:!?)]}>")
            )

            if candidate:
                return candidate

    return None


def extract_known_stand(text: str):
    # URL/hostname/IP имеет приоритет.
    direct = extract_stand(text)

    if direct:
        try:
            resolved = resolve_stand(direct)
        except (ValueError, TypeError):
            resolved = None

        if resolved:
            return resolved

        return direct

    # Иначе ищем известный alias/canonical hostname
    # среди обычных слов пользовательской фразы.
    tokens = re.findall(
        r'[A-Za-z0-9._-]+',
        str(text or "").lower(),
    )

    tokens = sorted(
        {
            token.strip()
            for token in tokens
            if token.strip()
        },
        key=len,
        reverse=True,
    )

    for token in tokens:
        try:
            resolved = resolve_stand(token)
        except (ValueError, TypeError):
            # Bad/empty alias inside stand store must not
            # terminate the interactive UQA session.
            continue

        if resolved:
            return resolved

    return None


def extract_ssh_host(text: str):
    patterns = (
        r'(?:ssh(?:[-_ ]?host)?|ssh[-_ ]?ip)'
        r'\s*[:=]?\s*'
        r'((?:\d{1,3}\.){3}\d{1,3})',

        r'(?:сервер|server|хост|host)'
        r'\s*[:=]?\s*'
        r'((?:\d{1,3}\.){3}\d{1,3})',
    )

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(1)

    return None


def extract_credentials(text: str):
    login_match = re.search(
        r'(?:логин|login|user|username)'
        r'\s*[:=]?\s*'
        r'([^\s,;]+)',
        text,
        flags=re.IGNORECASE,
    )

    password_match = re.search(
        r'(?:пароль|password|passwd)'
        r'\s*[:=]?\s*'
        r'([^\s,;]+)',
        text,
        flags=re.IGNORECASE,
    )

    if not login_match or not password_match:
        return None

    return {
        "username": login_match.group(1),
        "password": password_match.group(1),
    }


def redact_credentials(text: str):
    text = re.sub(
        r'((?:пароль|password|passwd)'
        r'\s*[:=]?\s*)'
        r'([^\s,;]+)',
        r'\1<redacted>',
        text,
        flags=re.IGNORECASE,
    )

    return text




def sanitize_onboarding_message(text: str):
    safe = redact_credentials(text)

    # Убираем пароль целиком вместе с меткой.
    safe = re.sub(
        r'(?i)'
        r'(?:пароль|password|passwd|пасс)'
        r'\s*[:=]?\s*'
        r'<redacted>',
        '[SSH password stored securely]',
        safe,
    )

    # Логин не является секретом, но модели достаточно
    # знать, что SSH credentials уже доступны.
    safe = re.sub(
        r'(?i)'
        r'(?:логин|login|user|username|юзер)'
        r'\s*[:=]?\s*'
        r'[^\s,;]+',
        '[SSH login stored]',
        safe,
    )

    return safe.strip()


def build_stand_context(stand: str):
    info = get_stand(stand)

    if not info:
        return None

    return (
        "\n\n"
        "[UQA CORE: RESOLVED STAND]\n"
        f"stand_id: {info['stand_id']}\n"
        f"web_url: {info.get('web_url')}\n"
        f"ssh_host: {info.get('ssh_host')}\n"
        f"ssh_username: {info.get('ssh_username')}\n"
        f"ssh_credentials_available: "
        f"{bool(info.get('has_ssh_credentials'))}\n"
        "Rules:\n"
        "- This stand was resolved by UQA Core.\n"
        "- Use the exact web_url above for browser tools.\n"
        "- Do not invent another protocol, hostname, port or path.\n"
        "- Use stand_id above for SSH tools.\n"
        "- Do not ask for SSH credentials when "
        "ssh_credentials_available is true.\n"
    )


def request_needs_ssh(text: str):
    lowered = text.lower()

    words = (
        "регресс",
        "ssh",
        "backend",
        "бэкенд",
        "бекенд",
        "лог",
        "docker",
        "контейнер",
        "сервер",
    )

    return any(
        word in lowered
        for word in words
    )


def _latest_user_text(messages):
    for message in reversed(messages):
        if message.get("role") == "user":
            return str(
                message.get("content")
                or ""
            )

    return ""


def _request_has_explicit_mutation_intent(text):
    """
    Return True when the request contains a positive, explicit mutation verb.

    A scoped guard such as "do not modify existing objects" must not turn a
    workflow that also says "create one test object" into a globally
    read-only request. Negated mutation verbs are ignored clause by clause.
    """
    value = str(text or "").lower()

    action_pattern = re.compile(
        r"(?iu)\b(?:"
        r"создай(?:те)?|создать|"
        r"добавь(?:те)?|добавить|"
        r"измени(?:те)?|изменить|"
        r"обнови(?:те)?|обновить|"
        r"удали(?:те)?|удалить|"
        r"архивируй(?:те)?|архивировать|"
        r"сохрани(?:те)?|сохранить|"
        r"примени(?:те)?|применить|"
        r"назначь(?:те)?|назначить|"
        r"переименуй(?:те)?|переименовать|"
        r"включи(?:те)?|включить|"
        r"выключи(?:те)?|выключить|"
        r"create|add|update|change|delete|remove|archive|"
        r"save|apply|assign|rename|enable|disable"
        r")\b"
    )

    negation_before_action = re.compile(
        r"(?iu)(?:"
        r"\bне\b|\bнельзя\b|\bбез\b|"
        r"\bdo\s+not\b|\bdon't\b|\bnever\b|\bwithout\b"
        r")(?:\s+[\w-]+){0,3}\s*$"
    )

    for clause in re.split(
        r"[\n\r.!?;]+",
        value,
    ):
        for match in action_pattern.finditer(clause):
            prefix = clause[
                max(0, match.start() - 80):match.start()
            ]

            if negation_before_action.search(prefix):
                continue

            return True

    return False


def _request_is_read_only(messages):
    text = _latest_user_text(messages).lower()

    # Explicit create/update/delete intent wins over a scoped protection such
    # as "do not modify existing objects". The individual action still passes
    # through the existing MANAGED_ACTIONS classification and confirmation.
    if _request_has_explicit_mutation_intent(text):
        return False

    markers = (
        "ничего не изменяй",
        "не изменяй на стенде",
        "без изменений",
        "ничего не меняй",
        "не создавай",
        "только проверь",
        "только проверить",
        "read-only",
        "readonly",
        "do not modify",
        "do not change",
    )

    return any(
        marker in text
        for marker in markers
    )


def _semantic_action_is_mutating(name):
    value = re.sub(
        r"\s+",
        " ",
        str(name or "").strip().lower(),
    )

    patterns = (
        r"^(add|save|create|delete|remove|edit|apply|submit|confirm|install|archive|restore|enable|disable|start|stop|restart)\b",
        r"^(добав|сохран|созда|удал|измен|примен|подтверд|установ|архив|восстанов|включ|выключ|запуст|останов|перезап)",
    )

    return any(
        re.search(pattern, value)
        for pattern in patterns
    )



def classify_tool_action(
    name,
    arguments=None,
):
    """
    Generic action classification.

    This layer must describe WHAT kind of action a tool call is.
    It must not contain U-Connect-specific entities or test cases.

    Classes:
      observe      - read-only inspection
      interact     - UI interaction that is not known to mutate data
      write        - create/update/apply/save-like operation
      destructive  - delete/archive/remove-like operation
      system       - privileged/system-changing operation
      unknown      - Core cannot classify safely
    """
    arguments = (
        arguments
        if isinstance(arguments, dict)
        else {}
    )

    observe_tools = {
        "knowledge_search",
        "ssh_docker_ps",
        "ssh_find_backend_request",
        "ssh_docker_logs",
        "browser_open_page",
        "browser_get_state",
        "browser_probe_capabilities",
        "browser_get_network_detail",
        "browser_inspect_semantic",
        "browser_inspect_table_row",
        "browser_inspect_table_semantic",
        "browser_inspect_table_pagination_semantic",
        "browser_inspect_order_semantic",
        "browser_inspect_bulk_action_semantic",
        "browser_inspect_tree_semantic",
        "browser_inspect_popover_semantic",
        "browser_inspect_file_input_semantic",
        "browser_verify_download_structure_semantic",
        "browser_inspect_agent_telemetry_semantic",
        "resource_list",
        "table_selection_list",
    }

    if name in observe_tools:
        return "observe"

    if name == "browser_check_focus_order_semantic":
        return "interact"

    if name == "browser_set_tree_item_expanded":
        return "interact"

    if name == "browser_open_popover_semantic":
        return classify_tool_action(
            "browser_click_semantic",
            {"name": arguments.get("trigger")},
        )

    if name == "browser_close_popover_semantic":
        return "interact"

    if name == "browser_select_popover_option_semantic":
        option_action = classify_tool_action(
            "browser_click_semantic",
            {"name": arguments.get("option")},
        )
        return "destructive" if option_action == "destructive" else "write"

    if name == "browser_download_semantic":
        trigger_action = classify_tool_action(
            "browser_click_semantic",
            {"name": arguments.get("name")},
        )
        return "destructive" if trigger_action == "destructive" else "write"

    if name in {"stage_test_artifact", "browser_upload_staged_artifact_semantic"}:
        return "write"

    if name == "browser_click_popover_button_semantic":
        button_action = classify_tool_action(
            "browser_click_semantic",
            {"name": arguments.get("button")},
        )
        return "destructive" if button_action == "destructive" else "write"

    if name in {
        "browser_sort_table_semantic",
        "browser_set_table_row_selected",
        "browser_table_page_semantic",
        "browser_fill_table_filter_semantic",
        "browser_apply_table_filter_popover_semantic",
        "browser_set_table_all_selected",
    }:
        return "interact"

    # Ledger updates are internal QA bookkeeping. They do not mutate
    # the tested stand and need no second confirmation after the
    # already-confirmed stand action that created or changed a resource.
    if name in {
        "browser_copy_value_semantic",
        "browser_clear_private_clipboard",
        "resource_register",
        "resource_update",
        "browser_authenticate_saved_stand",
        "browser_context_menu_semantic",
    }:
        return "interact"

    if name in {
        "browser_delete_json_resource",
        "browser_archive_json_resource",
    }:
        return "destructive"

    if name == "browser_fill_semantic":
        field = " ".join(
            str(
                arguments.get("field")
                or ""
            )
            .strip()
            .casefold()
            .split()
        )

        safe_input_markers = (
            "search",
            "filter",
            "find",
            "query",
            "поиск",
            "фильтр",
        )

        if any(
            marker in field
            for marker in safe_input_markers
        ):
            return "interact"

        return "write"

    if name == "browser_press_key_semantic":
        key = str(arguments.get("key") or "").strip().casefold()
        if key in {"tab", "shift+tab", "escape", "control+a", "ctrl+a"}:
            return "interact"
        if key == "delete":
            return "destructive"
        if key in {
            "enter",
            "space",
            "arrowup",
            "arrowdown",
            "arrowleft",
            "arrowright",
            "home",
            "end",
            "pageup",
            "pagedown",
            "backspace",
            "control+z",
            "ctrl+z",
            "control+y",
            "ctrl+y",
            "control+shift+z",
            "ctrl+shift+z",
            "shift+enter",
            "alt+arrowdown",
        }:
            return "write"
        return "unknown"

    if name in {
        "browser_paste_private_semantic",
        "browser_set_upload_fixture_semantic",
        "browser_set_temporal_semantic",
        "browser_set_slider_semantic",
        "browser_set_tree_item_selected",
        "browser_select_semantic",
        "browser_set_checked_semantic",
        "browser_choose_radio_semantic",
        "browser_select_many_semantic",
        "browser_drag_semantic",
        "browser_resize_semantic",
    }:
        return "write"

    if name == "browser_click_semantic":
        semantic_name = " ".join(
            str(
                arguments.get("name")
                or ""
            )
            .strip()
            .casefold()
            .split()
        )

        destructive_patterns = (
            r"^(delete|remove|archive|purge|drop|wipe)\b",
            r"^(удал|архив|очист|стер)",
        )

        if any(
            re.search(
                pattern,
                semantic_name,
            )
            for pattern in destructive_patterns
        ):
            return "destructive"

        write_patterns = (
            r"^(add|create|save|apply|submit|confirm|install|"
            r"restore|enable|disable|start|stop|restart|edit|"
            r"update|rename|assign)\b",
            r"^(добав|созда|сохран|примен|подтверд|установ|"
            r"восстанов|включ|выключ|запуст|останов|перезап|"
            r"измен|переимен|назнач)",
        )

        if any(
            re.search(
                pattern,
                semantic_name,
            )
            for pattern in write_patterns
        ):
            return "write"

        return "interact"

    return "unknown"


def tool_policy_check(
    name,
    arguments,
    messages,
    force_read_only=False,
):
    read_only = (
        force_read_only
        or _request_is_read_only(messages)
    )

    if not read_only:
        return None

    # Regression v1 strict mode:
    # никакие semantic clicks не исполняются.
    # Это intentionally conservative.
    if force_read_only and name == "browser_click_semantic":
        return {
            "error": "tool_policy_blocked",
            "status": "blocked_by_policy",
            "policy": "strict_read_only",
            "tool": name,
            "executed": False,
            "requested_semantic_name": (
                arguments.get("name")
                or ""
            ),
            "reason": (
                "STRICT_READ_ONLY regression mode "
                "forbids browser clicks."
            ),
        }

    if (
        name == "browser_press_key_semantic"
        and classify_tool_action(name, arguments)
        in {"write", "destructive", "unknown"}
    ):
        return {
            "error": "tool_policy_blocked",
            "status": "blocked_by_policy",
            "policy": (
                "strict_read_only"
                if force_read_only
                else "read_only_request"
            ),
            "tool": name,
            "executed": False,
            "requested_key": arguments.get("key") or "",
            "reason": (
                "This keyboard action can change UI or application state "
                "and is forbidden by the current read-only QA request."
            ),
        }

    # Ввод разрешён только в очевидные поля
    # поиска/фильтра. В формы данных ввод запрещён.
    if force_read_only and name == "browser_fill_semantic":
        field = str(
            arguments.get("field")
            or ""
        ).lower()

        safe_markers = (
            "search",
            "filter",
            "find",
            "query",
            "поиск",
            "фильтр",
        )

        if not any(
            marker in field
            for marker in safe_markers
        ):
            return {
                "error": "tool_policy_blocked",
                "status": "blocked_by_policy",
                "policy": "strict_read_only",
                "tool": name,
                "executed": False,
                "requested_semantic_name": field,
                "reason": (
                    "STRICT_READ_ONLY regression mode "
                    "allows text input only in "
                    "search/filter fields."
                ),
            }

    if name in {
        "browser_select_semantic",
        "browser_set_checked_semantic",
        "browser_choose_radio_semantic",
        "browser_select_many_semantic",
    }:
        return {
            "error": "tool_policy_blocked",
            "status": "blocked_by_policy",
            "policy": (
                "strict_read_only"
                if force_read_only
                else "read_only_request"
            ),
            "tool": name,
            "executed": False,
            "requested_semantic_name": (
                arguments.get("field")
                or ""
            ),
            "reason": (
                "Form state changes are forbidden by the current "
                "read-only QA request."
            ),
        }

    if name in {
        "browser_drag_semantic",
        "browser_resize_semantic",
    }:
        return {
            "error": "tool_policy_blocked",
            "status": "blocked_by_policy",
            "policy": (
                "strict_read_only"
                if force_read_only
                else "read_only_request"
            ),
            "tool": name,
            "executed": False,
            "reason": (
                "Pointer mutation is forbidden by the current "
                "read-only QA request."
            ),
        }

    if name == "browser_click_semantic":
        semantic_name = (
            arguments.get("name")
            or ""
        )

        if _semantic_action_is_mutating(
            semantic_name
        ):
            return {
                "error": "tool_policy_blocked",
                "status": "blocked_by_policy",
                "policy": "read_only_request",
                "tool": name,
                "executed": False,
                "requested_semantic_name": (
                    semantic_name
                ),
                "reason": (
                    "Potentially mutating UI action "
                    "is forbidden by the current "
                    "read-only QA request."
                ),
            }

    return None


def _confirm_managed_action(
    name,
    arguments,
    action_class,
):
    destructive = (
        action_class == "destructive"
    )

    if destructive:
        console.print(
            "\n[bold red]"
            "UQA Core: DESTRUCTIVE action"
            "[/bold red]"
        )
    else:
        console.print(
            "\n[bold yellow]"
            "UQA Core: WRITE action"
            "[/bold yellow]"
        )

    console.print(
        f"Tool: [cyan]{name}[/cyan]"
    )

    console.print(
        f"Class: [magenta]"
        f"{action_class.upper()}"
        f"[/magenta]"
    )

    args_text = json.dumps(
        arguments or {},
        ensure_ascii=False,
    )

    if len(args_text) > 1200:
        args_text = (
            args_text[:1200]
            + "...[truncated]"
        )

    console.print(
        f"Arguments: [dim]{args_text}[/dim]"
    )

    if destructive:
        console.print(
            "[red]"
            "Действие может удалить, архивировать "
            "или иным образом разрушительно изменить данные."
            "[/red]"
        )

    console.print(
        "[bold]"
        "[Y] выполнить   "
        "[Enter/N] блокировать"
        "[/bold]"
    )

    try:
        raw = read_user_input()
    except (
        EOFError,
        KeyboardInterrupt,
    ):
        return False

    value = sanitize_terminal_input(
        raw
    ).strip().casefold()

    return value in (
        "y",
        "yes",
        "д",
        "да",
    )


def managed_action_policy_decision(
    name,
    arguments,
    action_class,
    action_policy,
):
    if action_policy in (
        None,
        "",
        "legacy",
    ):
        return {
            "allow": True,
            "status": "legacy",
        }

    if action_policy != "confirm_mutations":
        return {
            "allow": False,
            "status": "blocked",
            "reason": (
                "Unknown UQA action policy: "
                f"{action_policy}"
            ),
        }

    if action_class in (
        "observe",
        "interact",
    ):
        return {
            "allow": True,
            "status": "auto_allowed",
        }

    if action_class in (
        "write",
        "destructive",
    ):
        approved = _confirm_managed_action(
            name,
            arguments,
            action_class,
        )

        if approved:
            return {
                "allow": True,
                "status": "confirmed",
            }

        return {
            "allow": False,
            "status": "blocked",
            "reason": (
                f"{action_class.upper()} action "
                "was not approved by the user."
            ),
        }

    if action_class == "system":
        return {
            "allow": False,
            "status": "blocked",
            "reason": (
                "SYSTEM action is not enabled "
                "in the current pilot policy."
            ),
        }

    return {
        "allow": False,
        "status": "blocked",
        "reason": (
            "UQA Core cannot safely classify "
            "this tool action."
        ),
    }


def _generic_create_requires_navigation_preflight(
    name,
    arguments,
    action_class,
):
    if (
        name != "browser_click_semantic"
        or action_class != "write"
    ):
        return False

    semantic_name = re.sub(
        r"\s+",
        " ",
        str(
            (arguments or {}).get("name")
            or ""
        ).strip().casefold(),
    )

    return bool(
        re.fullmatch(
            r"(?:add|create|new|добавить|добавь|создать|создай|новый)",
            semantic_name,
            flags=re.IGNORECASE,
        )
    )


def _history_has_successful_interact_navigation(messages):
    previous_url = None

    for message in messages or []:
        if message.get("role") != "tool":
            continue

        content = message.get("content")

        if isinstance(content, str):
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                continue
        elif isinstance(content, dict):
            result = content
        else:
            continue

        current_url = str(
            result.get("current_url")
            or ""
        ).strip()

        is_interact_click = (
            message.get("tool_name")
            == "browser_click_semantic"
            and result.get("action_class")
            == "interact"
        )

        if is_interact_click:
            successful = (
                result.get("executed") is not False
                and str(
                    result.get("status")
                    or ""
                ).casefold() not in {
                    "error",
                    "failed",
                    "blocked_by_policy",
                }
                and str(
                    result.get("click_status")
                    or ""
                ).casefold() not in {
                    "failed",
                    "not_executed",
                }
            )

            if (
                successful
                and previous_url
                and current_url
                and current_url != previous_url
            ):
                return True

        if current_url:
            previous_url = current_url

    return False


NAVIGATION_CONCEPT_GROUPS = (
    ("access", "доступ", "zone", "зон"),
    ("administr", "администр"),
    ("manage", "management", "управлен"),
    ("user", "пользоват"),
    ("role", "рол"),
    ("security", "безопас"),
    ("setting", "настрой"),
    ("server", "сервер"),
    ("agent", "агент"),
    ("integrat", "интеграц"),
    ("policy", "политик"),
    ("repositor", "репозитор"),
    ("computer", "компьют", "свт"),
    (
        "location",
        "локац",
        "местопол",
        "dictionar",
        "справоч",
        "словар",
    ),
)


def _latest_browser_state_for_navigation(messages):
    for message in reversed(messages or []):
        if (
            message.get("role") != "tool"
            or not str(message.get("tool_name") or "").startswith("browser_")
        ):
            continue

        content = message.get("content")

        if isinstance(content, str):
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                continue
        elif isinstance(content, dict):
            result = content
        else:
            continue

        if any(
            str(result.get(key) or "").strip()
            for key in ("current_url", "title", "text_preview")
        ):
            return result

    return None


def _latest_state_matches_navigation_target(messages):
    task_text = _navigation_task_text(messages).casefold()
    target_groups = [
        group
        for group in NAVIGATION_CONCEPT_GROUPS
        if any(term in task_text for term in group)
    ]

    if not target_groups:
        return None

    state = _latest_browser_state_for_navigation(messages)

    if not state:
        return False

    state_text = " ".join(
        str(state.get(key) or "")
        for key in ("current_url", "title", "text_preview")
    ).casefold()
    return any(
        any(term in state_text for term in group)
        for group in target_groups
    )


def _managed_navigation_ready(messages):
    if not _history_has_successful_interact_navigation(messages):
        return False

    target_match = _latest_state_matches_navigation_target(messages)
    return True if target_match is None else target_match


def _successful_clicked_semantic_names(messages):
    clicked_names = set()

    for message in messages or []:
        if (
            message.get("role") != "tool"
            or message.get("tool_name")
            != "browser_click_semantic"
        ):
            continue

        content = message.get("content")

        if isinstance(content, str):
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                continue
        elif isinstance(content, dict):
            result = content
        else:
            continue

        semantic_name = str(
            result.get("semantic_name") or ""
        ).strip().casefold()

        if not semantic_name:
            continue

        if (
            result.get("executed") is False
            or result.get("error")
            or str(result.get("status") or "").casefold()
            in {"error", "failed", "blocked_by_policy"}
            or str(result.get("click_status") or "").casefold()
            in {"failed", "not_executed"}
        ):
            continue

        clicked_names.add(semantic_name)

    return clicked_names


def _latest_unique_unnamed_icon_hints(messages):
    clicked_names = _successful_clicked_semantic_names(
        messages
    )

    for message in reversed(messages or []):
        if message.get("role") != "tool":
            continue

        content = message.get("content")

        if isinstance(content, str):
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                continue
        elif isinstance(content, dict):
            result = content
        else:
            continue

        hints = result.get(
            "unique_unnamed_icon_hints"
        )

        if not isinstance(hints, list):
            continue

        normalized = []
        for hint in hints:
            value = str(hint or "").strip().casefold()

            if (
                value
                and value not in clicked_names
                and value not in normalized
            ):
                normalized.append(value)

        return normalized

    return []


def _latest_navigation_labels(messages):
    clicked_names = _successful_clicked_semantic_names(
        messages
    )
    observed_label_sets = []

    for message in messages or []:
        if message.get("role") != "tool":
            continue

        content = message.get("content")

        if isinstance(content, str):
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                continue
        elif isinstance(content, dict):
            result = content
        else:
            continue

        labels = result.get("navigation_labels")

        if not isinstance(labels, list):
            continue

        normalized = [
            str(label).strip()
            for label in labels
            if str(label or "").strip()
            and "\n" not in str(label)
            and len(str(label).strip()) <= 80
        ][:50]

        if normalized:
            observed_label_sets.append(normalized)

    if not observed_label_sets:
        return []

    latest = observed_label_sets[-1]
    candidates = latest

    if len(observed_label_sets) > 1:
        previous = {
            label.casefold()
            for label in observed_label_sets[-2]
        }
        newly_revealed = [
            label
            for label in latest
            if label.casefold() not in previous
        ]

        if newly_revealed:
            candidates = newly_revealed

    return [
        label
        for label in candidates
        if label.casefold() not in clicked_names
    ]


def _latest_navigation_role(messages, label):
    wanted = str(label or "").strip().casefold()

    if not wanted:
        return None

    role_priority = {
        "menuitem": 0,
        "tab": 1,
        "link": 2,
        "button": 3,
    }

    for message in reversed(messages or []):
        if message.get("role") != "tool":
            continue

        content = message.get("content")

        if isinstance(content, str):
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                continue
        elif isinstance(content, dict):
            result = content
        else:
            continue

        elements = result.get("interactive_elements")

        if not isinstance(elements, list):
            continue

        roles = []

        for item in elements:
            if not isinstance(item, dict):
                continue

            if (
                item.get("enabled") is False
                or item.get("disabled_attribute") is True
                or str(item.get("aria_disabled") or "")
                .strip()
                .casefold()
                == "true"
            ):
                continue

            item_label = next(
                (
                    str(item.get(key) or "").strip()
                    for key in ("aria_label", "text", "label")
                    if str(item.get(key) or "").strip()
                ),
                "",
            )

            if item_label.casefold() != wanted:
                continue

            role = str(item.get("role") or "").strip().casefold()

            if role in role_priority and role not in roles:
                roles.append(role)

        if roles:
            return min(
                roles,
                key=lambda value: role_priority[value],
            )

    return None


def _parse_navigation_resolver_choice(content, labels):
    text = str(content or "").strip()
    first = text.find("{")
    last = text.rfind("}")

    if first < 0 or last < first:
        return None

    try:
        payload = json.loads(text[first:last + 1])
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    selected = str(
        payload.get("label")
        or ""
    ).strip().casefold()

    if not selected:
        return None

    for label in labels:
        if str(label).strip().casefold() == selected:
            return str(label).strip()

    return None


def _latest_navigation_knowledge(messages):
    for message in reversed(messages or []):
        if (
            message.get("role") != "tool"
            or message.get("tool_name") != "knowledge_search"
        ):
            continue

        content = message.get("content")

        if isinstance(content, dict):
            return json.dumps(
                content,
                ensure_ascii=False,
            )[:6000]

        text = str(content or "").strip()

        if text:
            return text[:6000]

    return ""


def _navigation_task_text(messages):
    patterns = (
        r"(?:^|\n)Задача:\s*(.+?)(?=\nОжидаемый результат:)",
        r"(?:^|\n)Task:\s*(.+?)(?=\nExpected(?: result)?:)",
    )

    # Core may append user-role continuation messages after a blocked or
    # constrained action. Keep the original structured regression task as
    # the authority instead of letting those internal prompts replace it.
    for message in reversed(messages or []):
        if message.get("role") != "user":
            continue

        text = str(message.get("content") or "")

        for pattern in patterns:
            match = re.search(
                pattern,
                text,
                flags=re.IGNORECASE | re.DOTALL,
            )

            if match:
                parts = [match.group(1).strip()]
                shared_context = re.search(
                    r"Общий\s+контекст\s+regression\s+job\s*"
                    r"(?:\([^\n]*\))?\s*:\s*(.+?)"
                    r"(?=\n\nСформируй|\Z)",
                    text,
                    flags=re.IGNORECASE | re.DOTALL,
                )

                if shared_context:
                    parts.append(shared_context.group(1).strip())

                return "\n".join(parts)[:12000]

    return _latest_user_text(messages)[:8000]


def _deterministic_navigation_label(
    task_text,
    knowledge,
    labels,
):
    """
    Prefer a unique cross-language semantic match before asking the LLM.

    The concepts are generic navigation vocabulary, not product routes.  A
    label wins only when its concept also occurs in the task or the observed
    documentation; ties remain unresolved for the model to decide.
    """
    task_context = str(task_text or "").casefold()
    knowledge_context = str(knowledge or "").casefold()
    scored = []

    for label in labels or []:
        normalized = str(label or "").strip().casefold()
        score = 0

        for group in NAVIGATION_CONCEPT_GROUPS:
            if not any(
                term in normalized
                for term in group
            ):
                continue

            if any(
                term in task_context
                for term in group
            ):
                score += 2

            if any(
                term in knowledge_context
                for term in group
            ):
                score += 1

        scored.append((score, str(label).strip()))

    best_score = max(
        (score for score, _ in scored),
        default=0,
    )

    if best_score <= 0:
        return None

    winners = [
        label
        for score, label in scored
        if score == best_score
    ]

    if len(winners) == 1:
        return winners[0]

    return None


def _resolve_navigation_label(messages, labels):
    if not labels:
        return None

    task_text = _navigation_task_text(messages)
    knowledge = _latest_navigation_knowledge(messages)

    if not knowledge:
        try:
            lookup = execute_tool(
                "knowledge_search",
                {
                    "query": task_text[:1000],
                    "limit": 3,
                },
            )
        except Exception:
            lookup = None

        if isinstance(lookup, dict):
            knowledge = json.dumps(
                lookup,
                ensure_ascii=False,
            )[:6000]

    deterministic = _deterministic_navigation_label(
        task_text,
        knowledge,
        labels,
    )

    if deterministic:
        return deterministic

    context = ""

    if knowledge:
        context = (
            "\n\nRelevant product documentation already observed "
            "in this case:\n"
            + knowledge
        )

    resolver_messages = [
        {
            "role": "system",
            "content": (
                "You are UQA Core Navigation Resolver. Always choose the "
                "single best enabled label from the supplied observed "
                "navigation candidates that most likely leads toward the "
                "resource requested by the task. The exact resource name may "
                "not be present yet, so select its closest plausible parent "
                "section. Infer cross-language meaning and category hierarchy. "
                "The task may be in Russian while labels are in English: "
                "translate the requested resource mentally before choosing. "
                "For example, zones, users, roles, permissions, and other "
                "configuration resources commonly belong under an "
                "Administration-like parent when no exact label is present. "
                "Do not choose Add/Create/New actions. Return null only when "
                "every candidate is clearly unrelated to the requested "
                "resource. Return only JSON: "
                '{"label":"exact candidate or null"}'
            ),
        },
        {
            "role": "user",
            "content": (
                "Task:\n"
                + task_text
                + "\n\nObserved navigation candidates:\n"
                + json.dumps(
                    labels,
                    ensure_ascii=False,
                )
                + context
            ),
        },
    ]

    try:
        data = ask_ollama(
            resolver_messages,
            tools=[],
        )
    except Exception:
        return None

    message = data.get("message") or {}

    if message.get("tool_calls"):
        return None

    return _parse_navigation_resolver_choice(
        message.get("content"),
        labels,
    )


def managed_navigation_preflight_check(
    name,
    arguments,
    messages,
    action_class,
    action_policy,
    job_id,
    case_id,
):
    if (
        action_policy != "confirm_mutations"
        or not job_id
        or not case_id
        or not _generic_create_requires_navigation_preflight(
            name,
            arguments,
            action_class,
        )
        or _managed_navigation_ready(
            messages
        )
    ):
        return None

    blocked = {
        "error": "managed_navigation_preflight_required",
        "status": "blocked_by_policy",
        "policy": action_policy,
        "tool": name,
        "executed": False,
        "action_class": action_class,
        "action_policy_status": "blocked_by_navigation_preflight",
        "reason": (
            "A generic create action cannot be the first WRITE in a managed "
            "regression case. First use OBSERVE/INTERACT to open the section "
            "that semantically matches the requested resource, then retry."
        ),
    }

    hints = _latest_unique_unnamed_icon_hints(
        messages
    )

    navigation_labels = _latest_navigation_labels(
        messages
    )

    if navigation_labels:
        blocked["available_navigation_labels"] = (
            navigation_labels
        )

    if len(hints) == 1:
        blocked["required_navigation_candidate"] = {
            "tool": "browser_click_semantic",
            "arguments": {
                "name": hints[0],
                "exact": True,
            },
            "action_class": "interact",
            "basis": (
                "The latest browser state exposed exactly one unique "
                "enabled unnamed icon hint. Use it only when its meaning "
                "matches the documented navigation context."
            ),
        }

    elif navigation_labels:
        label = _resolve_navigation_label(
            messages,
            navigation_labels,
        )

        if label:
            candidate_arguments = {
                "name": label,
                "exact": True,
            }
            candidate_role = _latest_navigation_role(
                messages,
                label,
            )

            if candidate_role:
                candidate_arguments["role"] = candidate_role

            blocked["required_navigation_candidate"] = {
                "tool": "browser_click_semantic",
                "arguments": candidate_arguments,
                "action_class": "interact",
                "basis": (
                    "UQA Core Navigation Resolver selected one exact label "
                    "from the latest observed navigation candidates."
                ),
            }

    return blocked


_PENDING_NAVIGATION_CANDIDATES = {}
_MANAGED_BROWSER_OPENED_CASES = set()
_COMPATIBILITY_PREFLIGHT_BY_CASE = {}


def _managed_initial_browser_open_url(
    requested_url,
    task_text="",
    already_opened=False,
):
    """Keep an inferred first browser open at the stand origin.

    Models can mistake a documented API endpoint for a UI deep link. A deep
    link is preserved only after browser state already exists or when the user
    explicitly supplied that exact URL. This is origin-generic and does not
    encode product routes.
    """
    from urllib.parse import urlsplit

    requested = str(requested_url or "").strip()

    if already_opened or not requested:
        return requested, None

    if requested in str(task_text or ""):
        return requested, None

    try:
        parts = urlsplit(requested)
    except ValueError:
        return requested, None

    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return requested, None

    if parts.path in {"", "/"} and not parts.query and not parts.fragment:
        return requested, None

    origin = f"{parts.scheme}://{parts.netloc}"
    return origin, "inferred_deep_link_normalized_to_origin"
_PENDING_CONSTRAINED_ACTIONS = {}
_PENDING_OMISSION_CONTINUATIONS = {}
_PENDING_SELECTION_COMPLETIONS = {}
_PENDING_SELECTION_FIELD_TRANSITIONS = {}
_COMPLETED_REQUIRED_SELECTIONS = {}
_PENDING_SELECTION_CONTINUATIONS = {}


def add_saved_web_auth_advisory(
    name,
    result,
    action_policy,
    job_id,
    case_id,
):
    """Require the secret-safe Core auth tool before business actions."""
    if (
        not isinstance(result, dict)
        or not str(name or "").startswith("browser_")
        or name == "browser_authenticate_saved_stand"
        or action_policy != "confirm_mutations"
        or not job_id
        or not case_id
        or result.get("executed") is False
        or result.get("error")
        or (
            os.getenv("UQA_USE_SSH_CREDS_FOR_WEB", "0")
            .strip()
            .casefold()
            not in {"1", "true", "yes", "on"}
        )
    ):
        return result

    elements = result.get("interactive_elements") or []
    password_visible = any(
        isinstance(item, dict)
        and str(item.get("type") or "").casefold() == "password"
        and item.get("enabled") is not False
        for item in elements
    )
    preview = str(result.get("text_preview") or "").casefold()
    login_visible = (
        "login" in preview
        and "password" in preview
        and "sign in" in preview
    )

    if not password_visible or not login_visible:
        return result

    from urllib.parse import urlsplit

    stand_id = urlsplit(
        str(
            result.get("current_url")
            or result.get("final_url")
            or ""
        )
    ).hostname

    if not stand_id:
        return result

    candidate = {
        "tool": "browser_authenticate_saved_stand",
        "arguments": {"stand": stand_id},
        "action_class": "interact",
        "basis": (
            "UQA Core detected a visible Login/Password challenge and "
            "will keep credentials outside model context and evidence."
        ),
    }
    _PENDING_CONSTRAINED_ACTIONS[(str(job_id), str(case_id))] = candidate
    updated = dict(result)
    updated["auth_challenge_status"] = "required"
    updated["required_action_candidate"] = candidate
    return updated


def add_managed_navigation_preflight_advisory(
    name,
    result,
    messages,
    action_policy,
    job_id,
    case_id,
):
    if (
        not isinstance(result, dict)
        or not str(name or "").startswith("browser_")
        or action_policy != "confirm_mutations"
        or not job_id
        or not case_id
        or result.get("executed") is False
        or result.get("error")
    ):
        return result

    augmented_messages = list(messages or [])
    augmented_messages.append(
        {
            "role": "tool",
            "tool_name": name,
            "content": result,
        }
    )

    navigation_state_key = (
        str(job_id),
        str(case_id),
    )

    if _managed_navigation_ready(
        augmented_messages
    ):
        _PENDING_NAVIGATION_CANDIDATES.pop(
            navigation_state_key,
            None,
        )
        return result

    advisory = managed_navigation_preflight_check(
        "browser_click_semantic",
        {"name": "Add", "exact": True},
        augmented_messages,
        "write",
        action_policy,
        job_id,
        case_id,
    )

    candidate = (
        advisory.get("required_navigation_candidate")
        if isinstance(advisory, dict)
        else None
    )

    if not candidate:
        _PENDING_NAVIGATION_CANDIDATES.pop(
            navigation_state_key,
            None,
        )
        return result

    _PENDING_NAVIGATION_CANDIDATES[
        navigation_state_key
    ] = candidate

    labels = advisory.get("available_navigation_labels")
    updated = {
        "navigation_preflight_status": "required",
        "required_navigation_candidate": candidate,
    }

    if labels:
        updated["available_navigation_labels"] = labels

    updated.update(result)

    return updated


def _latest_required_navigation_candidate(messages):
    """Return a pending Core navigation candidate from the latest tool result."""
    for message in reversed(messages or []):
        if message.get("role") != "tool":
            continue

        content = message.get("content")

        if isinstance(content, str):
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                return None
        elif isinstance(content, dict):
            result = content
        else:
            return None

        if (
            result.get("navigation_preflight_status")
            != "required"
        ):
            return None

        candidate = result.get(
            "required_navigation_candidate"
        )

        if not isinstance(candidate, dict):
            return None

        if (
            candidate.get("tool")
            != "browser_click_semantic"
            or not isinstance(
                candidate.get("arguments"),
                dict,
            )
        ):
            return None

        return candidate

    return None


def _navigation_candidate_matches(
    name,
    arguments,
    candidate,
):
    if not isinstance(candidate, dict):
        return False

    if str(name or "") != str(candidate.get("tool") or ""):
        return False

    expected = candidate.get("arguments")

    if not isinstance(expected, dict):
        return False

    actual = arguments or {}

    if (
        candidate.get("constraint_kind")
        in {"required_selection_field", "required_selection_value"}
        and "role" not in expected
        and actual.get("role")
    ):
        allowed_roles = {
            str(value).strip().casefold()
            for value in candidate.get("allowed_roles", [])
            if str(value).strip()
        }

        if (
            str(actual.get("role")).strip().casefold()
            not in allowed_roles
        ):
            return False

    for key, expected_value in expected.items():
        actual_value = actual.get(key)

        if key in {"name", "role"}:
            if (
                str(actual_value or "").strip().casefold()
                != str(expected_value or "").strip().casefold()
            ):
                return False
        elif actual_value != expected_value:
            return False

    return True


def _exact_resource_name_constraint(messages, task_text=None):
    text = str(task_text or _navigation_task_text(messages))
    patterns = (
        r"(?:с\s+точным\s+именем|с\s+именем|точное\s+имя)\s+"
        r"[`'\"«»]?([^\s,;!?]+)",
        r"(?:with\s+the\s+exact\s+name|exact\s+name|named)\s+"
        r"[`'\"«»]?([^\s,;!?]+)",
    )

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        value = match.group(1).strip(
            "`'\"«»()[]{}.:"
        )

        if value:
            return value[:200]

    return None


def _required_name_fill_candidate(
    name,
    arguments,
    messages,
    task_text=None,
):
    if name != "browser_fill_semantic":
        return None

    field = str(
        (arguments or {}).get("field")
        or ""
    ).strip().casefold()

    if field not in {"name", "имя"}:
        return None

    required_name = _exact_resource_name_constraint(
        messages,
        task_text=task_text,
    )

    if not required_name:
        return None

    actual = str(
        (arguments or {}).get("text")
        or ""
    )

    if actual == required_name:
        return None

    required_arguments = dict(arguments or {})
    required_arguments["text"] = required_name

    return {
        "tool": "browser_fill_semantic",
        "arguments": required_arguments,
        "action_class": "write",
        "basis": (
            "The regression task explicitly requires an exact resource name."
        ),
    }


def _blank_field_constraint_violation(
    name,
    arguments,
    messages,
    task_text=None,
):
    """Return the constrained field when the task says it must stay blank."""
    if name != "browser_fill_semantic":
        return None

    arguments = arguments or {}
    proposed_text = str(arguments.get("text") or "")

    if not proposed_text:
        return None

    field = re.sub(
        r"\s+",
        " ",
        str(arguments.get("field") or "").strip(),
    ).casefold()

    if not field:
        return None

    task_text = str(task_text or _navigation_task_text(messages))
    patterns = (
        r"\bполе\s+[`'\"«]?([^.;!?\n]{1,80}?)[`'\"»]?\s+"
        r"(?:оставь|оставить|оставьте|оставляем|должно\s+остаться)\s+"
        r"пуст(?:ым|ой|ое)",
        r"\b(?:leave|keep)\s+(?:the\s+)?(?:field\s+)?"
        r"[`'\"]?([^.;!?\n]{1,80}?)[`'\"]?\s+(?:field\s+)?"
        r"(?:blank|empty)\b",
        r"\bfield\s+[`'\"]?([^.;!?\n]{1,80}?)[`'\"]?\s+"
        r"must\s+(?:remain|be)\s+(?:blank|empty)\b",
    )

    for pattern in patterns:
        for match in re.finditer(
            pattern,
            task_text,
            flags=re.IGNORECASE,
        ):
            constrained_field = re.sub(
                r"\s+",
                " ",
                match.group(1).strip(" `\t\r\n'\"«»:;,."),
            ).casefold()

            if constrained_field == field:
                return str(arguments.get("field") or "").strip()

    return None


def _required_selection_constraints(task_text):
    """Extract generic required field/value selections from operator text."""
    text = str(task_text or "")
    patterns = (
        (
            r"\b(?:в\s+)?обязательном\s+поле\s+"
            r"[`'\"«]?([^,.;!?\n]{1,60}?)[`'\"»]?\s+"
            r"(?:выбери|выбрать|выберите|укажи|указать|укажите)\s+"
            r"(?:существующ\w+\s+"
            r"(?:зон\w*|объект\w*|ресурс\w*|значени\w*)\s+)?"
            r"[`'\"«]?([^,.;!?\n]{1,80}?)[`'\"»]?"
            r"(?=\s*,|\s+не\s+изменяя|[.;!?]|$)"
        ),
        (
            r"\bin\s+(?:the\s+)?required\s+"
            r"(?:field\s+)?[`'\"]?([^,.;!?\n]{1,60}?)[`'\"]?\s+"
            r"(?:field\s+)?(?:select|choose|set)\s+"
            r"(?:the\s+)?(?:existing\s+"
            r"(?:zone|object|resource|value)\s+)?"
            r"[`'\"]?([^,.;!?\n]{1,80}?)[`'\"]?"
            r"(?=\s*,|\s+without\s+modifying|[.;!?]|$)"
        ),
    )
    result = []

    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            field = re.sub(
                r"\s+",
                " ",
                match.group(1).strip(" `\t\r\n'\"«»"),
            )
            value = re.sub(
                r"\s+",
                " ",
                match.group(2).strip(" `\t\r\n'\"«»"),
            )

            if field and value:
                item = {"field": field, "value": value}

                if item not in result:
                    result.append(item)

    return result


def _selection_key(field, value):
    return (
        str(field or "").strip().casefold(),
        str(value or "").strip().casefold(),
    )


def _is_form_commit_action(name, arguments):
    if name not in {"browser_click_semantic", "browser_click_role"}:
        return False

    label = str((arguments or {}).get("name") or "").strip().casefold()
    return label in {
        "save",
        "submit",
        "apply",
        "сохранить",
        "отправить",
        "применить",
    }


def record_required_selection_result(
    job_id,
    case_id,
    result,
    name=None,
    arguments=None,
):
    state_key = (str(job_id), str(case_id))
    field_transition = _PENDING_SELECTION_FIELD_TRANSITIONS.pop(
        state_key,
        None,
    )
    result_succeeded = (
        isinstance(result, dict)
        and result.get("status") != "blocked_by_policy"
        and result.get("executed") is not False
        and not result.get("error")
    )

    if (
        result_succeeded
        and name == "browser_select_semantic"
    ):
        direct_selection = {
            "field": str((arguments or {}).get("field") or "").strip(),
            "value": str((arguments or {}).get("option") or "").strip(),
        }
        if direct_selection["field"] and direct_selection["value"]:
            completed = _COMPLETED_REQUIRED_SELECTIONS.setdefault(
                state_key,
                set(),
            )
            completed.add(
                _selection_key(
                    direct_selection["field"],
                    direct_selection["value"],
                )
            )
            _PENDING_SELECTION_CONTINUATIONS[state_key] = direct_selection

    if field_transition:
        if result_succeeded:
            _PENDING_CONSTRAINED_ACTIONS[state_key] = {
                "tool": "browser_click_semantic",
                "arguments": {
                    "name": field_transition["value"],
                    "exact": True,
                },
                "action_class": "interact",
                "constraint_kind": "required_selection_value",
                "allowed_roles": ["option", "treeitem"],
                "selection_field": field_transition["field"],
                "selection_value": field_transition["value"],
                "basis": (
                    "The persistent regression request requires this exact "
                    "selection before the form can be committed."
                ),
            }

        return

    completion = _PENDING_SELECTION_COMPLETIONS.pop(
        state_key,
        None,
    )

    if not completion:
        return

    if not result_succeeded:
        return

    completed = _COMPLETED_REQUIRED_SELECTIONS.setdefault(
        state_key,
        set(),
    )
    completed.add(
        _selection_key(
            completion.get("field"),
            completion.get("value"),
        )
    )
    _PENDING_SELECTION_CONTINUATIONS[state_key] = dict(completion)


def execute_resource_tool(
    name,
    arguments,
    job_id,
    case_id,
):
    if not job_id:
        return {
            "error": "resource_context_missing",
            "status": "error",
            "executed": False,
            "reason": "Resource ledger tools require an active QA Job.",
        }

    try:
        if name == "stage_test_artifact":
            return stage_test_artifact(
                job_id,
                arguments.get("stand"),
                arguments.get("source_path"),
                arguments.get("expected_sha256"),
            )

        if name == "browser_upload_staged_artifact_semantic":
            item = get_verified_staged_artifact(
                job_id,
                arguments.get("artifact_id"),
            )
            return set_staged_file_semantic(
                item["artifact_id"],
                item["filename"],
                Path(item["path"]).read_bytes(),
                arguments.get("field"),
                arguments.get("trigger"),
                arguments.get("exact", True),
            )

        if name == "resource_register":
            resource = add_test_resource(
                job_id=job_id,
                resource_type=arguments.get("resource_type"),
                name=arguments.get("name"),
                external_id=arguments.get("external_id"),
                created_by_case=case_id,
                cleanup_required=True,
                metadata=arguments.get("metadata"),
                depends_on=arguments.get("depends_on"),
            )

            return {
                "status": "ok",
                "executed": True,
                "resource_id": resource["resource_id"],
                "resource": resource,
            }

        if name == "resource_update":
            if (
                "status" in arguments
                or "cleanup_required" in arguments
            ):
                raise ValueError(
                    "cleanup state is managed by Cleanup Manager"
                )

            resource = update_test_resource(
                job_id=job_id,
                resource_id=arguments.get("resource_id"),
                name=arguments.get("name"),
                external_id=arguments.get("external_id"),
                metadata=arguments.get("metadata"),
                depends_on=arguments.get("depends_on"),
                updated_by_case=case_id,
            )

            return {
                "status": "ok",
                "executed": True,
                "resource_id": resource["resource_id"],
                "resource": resource,
            }

        if name == "resource_list":
            resources = list_test_resources(
                job_id=job_id,
                status=arguments.get("status"),
                cleanup_required=arguments.get("cleanup_required"),
                created_by_case=(
                    case_id
                    if arguments.get("current_case_only")
                    else None
                ),
            )

            return {
                "status": "ok",
                "executed": True,
                "count": len(resources),
                "resources": resources,
            }

        if name == "table_selection_list":
            selections = list_table_selections(
                job_id=job_id,
                case_id=case_id,
                table_selection_key=arguments.get("table_selection_key"),
                selected_only=arguments.get("selected_only", False),
            )

            return {
                "status": "ok",
                "executed": True,
                "count": len(selections),
                "selections": selections,
                "bookkeeping_only": True,
                "bulk_action_authorized": False,
            }

        return {
            "error": "unknown_resource_tool",
            "status": "error",
            "executed": False,
            "tool": name,
        }

    except Exception as exc:
        return {
            "error": "resource_ledger_error",
            "status": "error",
            "executed": False,
            "tool": name,
            "reason": f"{type(exc).__name__}: {str(exc)[:500]}",
        }


def _tool_history_observed_identifier(messages, candidate):
    wanted = str(candidate or "").strip()

    if not wanted:
        return False

    identifier_keys = {
        "id",
        "uid",
        "uuid",
        "external_id",
        "identifier_value",
    }

    def contains_identifier(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if (
                    str(key).strip().casefold() in identifier_keys
                    and str(item or "").strip() == wanted
                ):
                    return True

                if contains_identifier(item):
                    return True

        elif isinstance(value, list):
            return any(contains_identifier(item) for item in value)

        return False

    for message in reversed(messages or []):
        if message.get("role") != "tool":
            continue

        content = message.get("content")

        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                continue

        if contains_identifier(content):
            return True

    return False


def execute_tool_with_policy(
    name,
    arguments,
    messages,
    force_read_only=False,
    action_policy="legacy",
    job_id=None,
    case_id=None,
    require_compatibility_probe=False,
):
    action_class = classify_tool_action(
        name,
        arguments,
    )

    authoritative_task_text = None

    if (
        action_policy == "confirm_mutations"
        and job_id
    ):
        try:
            authoritative_task_text = str(
                (get_job(job_id) or {}).get("request")
                or ""
            ).strip() or None
        except Exception:
            authoritative_task_text = None

    pending_navigation = (
        _PENDING_NAVIGATION_CANDIDATES.get(
            (
                str(job_id),
                str(case_id),
            )
        )
        or _latest_required_navigation_candidate(
            messages
        )
        if action_policy == "confirm_mutations"
        and job_id
        and case_id
        else None
    )

    if (
        pending_navigation
        and name == "browser_click_semantic"
        and not _navigation_candidate_matches(
            name,
            arguments,
            pending_navigation,
        )
    ):
        return {
            "error": "managed_navigation_candidate_mismatch",
            "status": "blocked_by_policy",
            "policy": action_policy,
            "tool": name,
            "executed": False,
            "action_class": action_class,
            "action_policy_status": (
                "blocked_by_navigation_preflight"
            ),
            "navigation_preflight_status": "required",
            "required_navigation_candidate": (
                pending_navigation
            ),
            "reason": (
                "A different navigation click was requested while UQA Core "
                "has one exact observed INTERACT candidate pending."
            ),
        }

    constrained_state_key = (
        str(job_id),
        str(case_id),
    )
    pending_constrained_action = (
        _PENDING_CONSTRAINED_ACTIONS.get(
            constrained_state_key
        )
        if action_policy == "confirm_mutations"
        and job_id
        and case_id
        else None
    )

    if pending_constrained_action:
        if not _navigation_candidate_matches(
            name,
            arguments,
            pending_constrained_action,
        ):
            return {
                "error": "managed_action_constraint_mismatch",
                "status": "blocked_by_policy",
                "policy": action_policy,
                "tool": name,
                "executed": False,
                "action_class": action_class,
                "action_policy_status": (
                    "blocked_by_task_constraint"
                ),
                "required_action_candidate": (
                    pending_constrained_action
                ),
                "reason": (
                    "The requested action does not match one exact action "
                    "required by the regression task."
                ),
            }

        _PENDING_CONSTRAINED_ACTIONS.pop(
            constrained_state_key,
            None,
        )

        if (
            pending_constrained_action.get("constraint_kind")
            == "required_selection_field"
        ):
            _PENDING_SELECTION_FIELD_TRANSITIONS[
                constrained_state_key
            ] = {
                "field": pending_constrained_action["selection_field"],
                "value": pending_constrained_action["selection_value"],
            }
        elif (
            pending_constrained_action.get("constraint_kind")
            == "required_selection_direct"
        ):
            _PENDING_SELECTION_COMPLETIONS[
                constrained_state_key
            ] = {
                "field": pending_constrained_action["selection_field"],
                "value": pending_constrained_action["selection_value"],
            }
        elif (
            pending_constrained_action.get("constraint_kind")
            == "required_selection_value"
        ):
            _PENDING_SELECTION_COMPLETIONS[
                constrained_state_key
            ] = {
                "field": pending_constrained_action["selection_field"],
                "value": pending_constrained_action["selection_value"],
            }

    required_name_candidate = (
        _required_name_fill_candidate(
            name,
            arguments,
            messages,
            task_text=authoritative_task_text,
        )
        if action_policy == "confirm_mutations"
        and job_id
        and case_id
        else None
    )

    if required_name_candidate:
        _PENDING_CONSTRAINED_ACTIONS[
            constrained_state_key
        ] = required_name_candidate

        return {
            "error": "managed_exact_name_required",
            "status": "blocked_by_policy",
            "policy": action_policy,
            "tool": name,
            "executed": False,
            "action_class": action_class,
            "action_policy_status": (
                "blocked_by_task_constraint"
            ),
            "required_action_candidate": (
                required_name_candidate
            ),
            "reason": (
                "The proposed Name/Имя does not match the exact resource "
                "name required by the regression task."
            ),
        }

    blank_field = (
        _blank_field_constraint_violation(
            name,
            arguments,
            messages,
            task_text=authoritative_task_text,
        )
        if action_policy == "confirm_mutations"
        and job_id
        and case_id
        else None
    )

    if blank_field:
        _PENDING_OMISSION_CONTINUATIONS[
            constrained_state_key
        ] = {
            "field": blank_field,
            "reason": "field_must_remain_blank",
        }

        return {
            "error": "managed_blank_field_required",
            "status": "blocked_by_policy",
            "policy": action_policy,
            "tool": name,
            "executed": False,
            "action_class": action_class,
            "action_policy_status": (
                "blocked_by_task_constraint"
            ),
            "field": blank_field,
            "reason": (
                "The regression task explicitly requires this field to "
                "remain blank. Continue without filling it."
            ),
        }

    _PENDING_OMISSION_CONTINUATIONS.pop(
        constrained_state_key,
        None,
    )

    required_selections = _required_selection_constraints(
        authoritative_task_text
    )
    completed_selections = _COMPLETED_REQUIRED_SELECTIONS.get(
        constrained_state_key,
        set(),
    )
    missing_selections = [
        item
        for item in required_selections
        if _selection_key(item["field"], item["value"])
        not in completed_selections
    ]

    if (
        missing_selections
        and _is_form_commit_action(name, arguments)
    ):
        required = missing_selections[0]
        candidate = {
            "tool": "browser_select_semantic",
            "arguments": {
                "field": required["field"],
                "option": required["value"],
                "exact": True,
            },
            "action_class": "write",
            "constraint_kind": "required_selection_direct",
            "selection_field": required["field"],
            "selection_value": required["value"],
            "basis": (
                "The persistent regression request requires this field/value "
                "selection before the form can be committed."
            ),
        }
        _PENDING_CONSTRAINED_ACTIONS[
            constrained_state_key
        ] = candidate

        return {
            "error": "managed_required_selection_missing",
            "status": "blocked_by_policy",
            "policy": action_policy,
            "tool": name,
            "executed": False,
            "action_class": action_class,
            "action_policy_status": "blocked_by_task_constraint",
            "required_action_candidate": candidate,
            "reason": (
                "The form cannot be committed until an exact required "
                "field/value selection from the regression task is complete."
            ),
        }

    # Preserve explicit user restrictions.
    # If the request itself says not to modify anything,
    # the existing protection still wins.
    blocked = tool_policy_check(
        name,
        arguments,
        messages,
        force_read_only=force_read_only,
    )

    if blocked is not None:
        blocked = dict(blocked)
        blocked["action_class"] = (
            action_class
        )
        blocked["action_policy_status"] = (
            "blocked_by_request_policy"
        )
        return blocked

    blocked = managed_navigation_preflight_check(
        name,
        arguments,
        messages,
        action_class,
        action_policy,
        job_id,
        case_id,
    )

    if blocked is not None:
        return blocked

    compatibility_key = (
        str(job_id),
        str(case_id),
    )
    compatibility_state = _COMPATIBILITY_PREFLIGHT_BY_CASE.get(
        compatibility_key
    )

    if (
        require_compatibility_probe
        and action_policy == "confirm_mutations"
        and name != "stage_test_artifact"
        and job_id
        and case_id
        and compatibility_key in _MANAGED_BROWSER_OPENED_CASES
        and action_class in {"write", "destructive"}
    ):
        if compatibility_state is None:
            return {
                "error": "managed_compatibility_probe_required",
                "status": "blocked_by_policy",
                "policy": action_policy,
                "tool": name,
                "executed": False,
                "action_class": action_class,
                "action_policy_status": (
                    "blocked_by_compatibility_preflight"
                ),
                "compatibility_preflight_status": "required",
                "required_action_candidate": {
                    "tool": "browser_probe_capabilities",
                    "arguments": {},
                    "action_class": "observe",
                    "basis": (
                        "The current frontend contract must be observed "
                        "before the first managed mutation."
                    ),
                },
                "reason": (
                    "UQA Core has not verified the current frontend "
                    "capabilities after navigation."
                ),
            }

        if compatibility_state.get("status") != "compatible":
            return {
                "error": "managed_frontend_incompatible",
                "status": "blocked_by_policy",
                "policy": action_policy,
                "tool": name,
                "executed": False,
                "action_class": action_class,
                "action_policy_status": (
                    "blocked_by_compatibility_preflight"
                ),
                "compatibility_preflight_status": "incompatible",
                "capability_gaps": compatibility_state.get(
                    "capability_gaps",
                    [],
                ),
                "contract_fingerprint": compatibility_state.get(
                    "contract_fingerprint"
                ),
                "reason": (
                    "The current frontend does not satisfy the semantic "
                    "automation contract. No mutation was executed."
                ),
            }

    decision = (
        managed_action_policy_decision(
            name,
            arguments,
            action_class,
            action_policy,
        )
    )

    if not decision.get("allow"):
        return {
            "error": "tool_policy_blocked",
            "status": "blocked_by_policy",
            "policy": action_policy,
            "tool": name,
            "executed": False,
            "action_class": action_class,
            "action_policy_status": (
                decision.get("status")
                or "blocked"
            ),
            "reason": decision.get(
                "reason"
            )
            or "Action blocked by UQA Core.",
        }

    managed_open_key = (
        str(job_id),
        str(case_id),
    )
    effective_arguments = arguments
    managed_open_normalization = None

    if (
        name == "browser_open_page"
        and action_policy == "confirm_mutations"
        and job_id
        and case_id
    ):
        normalized_url, normalization_reason = (
            _managed_initial_browser_open_url(
                arguments.get("url"),
                authoritative_task_text or _latest_user_text(messages),
                managed_open_key in _MANAGED_BROWSER_OPENED_CASES,
            )
        )

        if normalization_reason:
            effective_arguments = dict(arguments)
            effective_arguments["url"] = normalized_url
            managed_open_normalization = {
                "model_requested_url": arguments.get("url"),
                "opened_url": normalized_url,
                "reason": normalization_reason,
            }

    resource_arguments = arguments
    ignored_external_id = None

    if name == "resource_register":
        proposed_external_id = str(
            arguments.get("external_id") or ""
        ).strip()

        if (
            proposed_external_id
            and not _tool_history_observed_identifier(
                messages,
                proposed_external_id,
            )
        ):
            resource_arguments = dict(arguments)
            resource_arguments["external_id"] = None
            ignored_external_id = proposed_external_id

    if name in {
        "resource_register",
        "resource_update",
        "resource_list",
        "table_selection_list",
        "stage_test_artifact",
        "browser_upload_staged_artifact_semantic",
    }:
        result = execute_resource_tool(
            name,
            resource_arguments,
            job_id,
            case_id,
        )
    else:
        result = execute_tool(
            name,
            effective_arguments,
        )

    if (
        require_compatibility_probe
        and name == "browser_probe_capabilities"
        and job_id
        and case_id
        and isinstance(result, dict)
        and not result.get("error")
    ):
        _COMPATIBILITY_PREFLIGHT_BY_CASE[compatibility_key] = {
            "status": str(
                result.get("compatibility_status") or "unknown"
            ).strip().casefold(),
            "capability_gaps": list(
                result.get("capability_gaps") or []
            ),
            "contract_fingerprint": result.get(
                "contract_fingerprint"
            ),
        }

    if isinstance(result, dict):
        result = dict(result)

        if ignored_external_id is not None:
            result["external_id_ignored"] = "not_observed_in_tool_history"

        if (
            name == "browser_open_page"
            and action_policy == "confirm_mutations"
            and job_id
            and case_id
            and not result.get("error")
        ):
            _MANAGED_BROWSER_OPENED_CASES.add(managed_open_key)

        if managed_open_normalization:
            result["managed_initial_open"] = managed_open_normalization

        result["action_class"] = (
            action_class
        )
        result["action_policy_status"] = (
            decision.get("status")
            or "allowed"
        )

        result = add_saved_web_auth_advisory(
            name,
            result,
            action_policy,
            job_id,
            case_id,
        )

        result = add_managed_navigation_preflight_advisory(
            name,
            result,
            messages,
            action_policy,
            job_id,
            case_id,
        )

    return result

def _tool_names():
    return [
        item["function"]["name"]
        for item in TOOLS
        if item.get("type") == "function"
        and item.get("function", {}).get("name")
    ]


def _container_image_version(image):
    image = str(image or "").strip()

    if not image or "@" in image:
        return None

    _, separator, candidate = image.rpartition(":")

    if not separator or not candidate or "/" in candidate:
        return None

    return candidate


def _product_versions_from_containers(result):
    if not isinstance(result, dict) or result.get("status") != "ok":
        return {}

    component_markers = {
        "backend": ("backend",),
        "frontend": ("frontend",),
    }
    versions = {}

    for container in result.get("containers") or []:
        if not isinstance(container, dict):
            continue

        image = str(container.get("image") or "").strip()
        name = str(container.get("name") or "").strip()
        searchable = f"{name} {image.rsplit('/', 1)[-1]}".casefold()
        version = _container_image_version(image)

        if not version:
            continue

        for component, markers in component_markers.items():
            if component in versions:
                continue

            if any(marker in searchable for marker in markers):
                versions[component] = version

    return versions


def recheck_product_blockers_for_stand(stand):
    try:
        result = execute_tool(
            "ssh_docker_ps",
            {"stand": stand},
        )
    except Exception as exc:
        return {
            "status": "unavailable",
            "versions": {},
            "changed": [],
            "error_type": type(exc).__name__,
        }

    versions = _product_versions_from_containers(result)

    if not versions:
        return {
            "status": "unavailable",
            "versions": {},
            "changed": [],
        }

    changed = mark_product_blockers_for_version_change(
        versions
    )
    return {
        "status": "ok",
        "versions": versions,
        "changed": changed,
    }


def _recheck_product_blockers_once(stand, checked_stands):
    stand = str(stand or "").strip()

    if not stand or stand in checked_stands:
        return None

    result = recheck_product_blockers_for_stand(stand)

    if result.get("status") != "ok":
        return result

    checked_stands.add(stand)
    changed = result.get("changed") or []

    if changed:
        console.print(
            "[yellow]Версия продукта изменилась. "
            "Нужно повторно проверить blockers: "
            + ", ".join(changed)
            + "[/yellow]"
        )

    return result


def banner():
    tool_names = _tool_names()

    console.print(
        Panel(
            f"[bold]UQA Pilot[/bold]\n"
            f"Model: {MODEL}\n"
            f"Context: {UQA_NUM_CTX}\n"
            f"Thinking: {'ON' if UQA_THINK else 'OFF'}\n"
            f"Ollama: {OLLAMA_URL}\n"
            f"Tools: {len(tool_names)} available\n\n"
            f"/clear  /status  /blockers  /exit",
            title="U-Connect QA Agent",
        )
    )


def ask_ollama(
    messages,
    tools=TOOLS,
):
    import time

    global LLM_CALL_COUNTER

    LLM_CALL_COUNTER += 1
    call_id = LLM_CALL_COUNTER

    model_messages = messages_for_model(messages)

    tool_messages = sum(
        1
        for message in model_messages
        if message.get("role") == "tool"
    )

    input_chars = sum(
        len(
            str(
                message.get("content")
                or ""
            )
        )
        for message in model_messages
    )

    llm_lock = None

    try:
        (
            llm_lock,
            queue_seconds,
        ) = acquire_llm_gate(
            call_id
        )

        console.print(
            f"[dim]"
            f"LLM #{call_id} started: "
            f"ctx={UQA_NUM_CTX}, "
            f"think={'on' if UQA_THINK else 'off'}, "
            f"messages={len(model_messages)}, "
            f"tool_messages={tool_messages}, "
            f"content_chars={input_chars}"
            f"[/dim]"
        )

        started = time.perf_counter()

        with httpx.Client(
            timeout=httpx.Timeout(
                600.0,
                connect=10.0,
            )
        ) as client:
            response = client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": MODEL,
                    "messages": model_messages,
                    "tools": tools,
                    "stream": False,
                    "think": UQA_THINK,
                    "keep_alive": "30m",
                    "options": {
                        "num_ctx": UQA_NUM_CTX,
                    },
                },
            )

        wall_seconds = (
            time.perf_counter()
            - started
        )

    finally:
        release_llm_gate(
            llm_lock
        )

    if response.is_error:
        body = response.text.strip()

        if len(body) > 4000:
            body = (
                body[:4000]
                + "...<truncated>"
            )

        console.print(
            f"[yellow]"
            f"LLM #{call_id} failed: "
            f"wall={wall_seconds:.1f}s"
            f"[/yellow]"
        )

        raise RuntimeError(
            f"Ollama API HTTP "
            f"{response.status_code}: "
            f"{body or '<empty response body>'}"
        )

    data = response.json()

    message = (
        data.get("message")
        or {}
    )

    thinking = (
        message.get("thinking")
        or data.get("thinking")
        or ""
    )

    content = (
        message.get("content")
        or ""
    )

    tool_calls = (
        message.get("tool_calls")
        or []
    )

    prompt_tokens = data.get(
        "prompt_eval_count"
    )

    output_tokens = data.get(
        "eval_count"
    )

    prompt_ns = data.get(
        "prompt_eval_duration"
    )

    eval_ns = data.get(
        "eval_duration"
    )

    load_ns = data.get(
        "load_duration"
    )

    total_ns = data.get(
        "total_duration"
    )

    def seconds(value):
        if not isinstance(
            value,
            (int, float),
        ):
            return None

        return value / 1_000_000_000

    def rate(tokens, duration_ns):
        duration = seconds(
            duration_ns
        )

        if (
            not isinstance(
                tokens,
                (int, float),
            )
            or not duration
        ):
            return None

        return tokens / duration

    prompt_seconds = seconds(
        prompt_ns
    )

    eval_seconds = seconds(
        eval_ns
    )

    load_seconds = seconds(
        load_ns
    )

    total_seconds = seconds(
        total_ns
    )

    prompt_rate = rate(
        prompt_tokens,
        prompt_ns,
    )

    eval_rate = rate(
        output_tokens,
        eval_ns,
    )

    def fmt_seconds(value):
        return (
            f"{value:.1f}s"
            if value is not None
            else "?"
        )

    def fmt_rate(value):
        return (
            f"{value:.1f} tok/s"
            if value is not None
            else "?"
        )

    console.print(
        f"[dim]"
        f"LLM #{call_id} done: "
        f"wall={wall_seconds:.1f}s | "
        f"total={fmt_seconds(total_seconds)} | "
        f"load={fmt_seconds(load_seconds)} | "
        f"prompt={prompt_tokens or '?'} tok/"
        f"{fmt_seconds(prompt_seconds)} "
        f"({fmt_rate(prompt_rate)}) | "
        f"output={output_tokens or '?'} tok/"
        f"{fmt_seconds(eval_seconds)} "
        f"({fmt_rate(eval_rate)}) | "
        f"thinking_chars={len(str(thinking))} | "
        f"content_chars={len(str(content))} | "
        f"tool_calls={len(tool_calls)} | "
        f"done_reason={data.get('done_reason')}"
        f"[/dim]"
    )

    return data


def compact_completed_history(messages):
    """
    Удаляет тяжёлые tool calls/results из уже завершённых
    пользовательских запросов.

    В истории остаются:
    - system prompt
    - обычные сообщения пользователя
    - финальные текстовые ответы ассистента
    """

    if not messages:
        return

    compacted = []

    for index, message in enumerate(messages):
        role = message.get("role")

        if index == 0 and role == "system":
            compacted.append(message)
            continue

        if role == "tool":
            continue

        if (
            role == "assistant"
            and message.get("tool_calls")
        ):
            continue

        content = message.get("content", "")

        if (
            role in ("user", "assistant")
            and isinstance(content, str)
            and content.strip()
        ):
            compacted.append(
                {
                    "role": role,
                    "content": content,
                }
            )

    # Не держим бесконечный обычный чат:
    # system + последние 6 user/assistant сообщений.
    if len(compacted) > 7:
        compacted = [
            compacted[0],
            *compacted[-6:],
        ]

    messages[:] = compacted


def request_is_qa_job(text: str):
    lowered = str(text).lower()

    markers = (
        "проверь",
        "проверить",
        "протест",
        "тестир",
        "регресс",
        "check ",
        "test ",
        "regression",
    )

    return any(
        marker in lowered
        for marker in markers
    )


def request_is_regression(text: str):
    lowered = str(
        text or ""
    ).lower()

    markers = (
        "регресс",
        "regression",
    )

    return any(
        marker in lowered
        for marker in markers
    )


def infer_case_status(content: str):
    """
    Определяет статус только по явному
    вердикту модели.

    Перед разбором нормализует Markdown,
    чтобы варианты вроде:

        **Вердикт: PASS**
        ### Результат: ✅ PASS
        **Result:** **FAIL**

    обрабатывались так же, как обычный текст.

    Не реагирует на:
        failed requests: 0
        fail count: 0
        no failures
    """

    import re

    raw_text = str(content)

    normalized_lines = []

    for raw_line in raw_text.splitlines():
        line = raw_line.replace(
            "\u00a0",
            " ",
        )

        # Markdown heading / blockquote.
        line = re.sub(
            r"^\s*#{1,6}\s*",
            "",
            line,
        )

        line = re.sub(
            r"^\s*>\s*",
            "",
            line,
        )

        # Markdown emphasis / inline-code markers.
        line = re.sub(
            r"[*_`~]+",
            "",
            line,
        )

        normalized_lines.append(
            line.strip()
        )

    text = "\n".join(
        normalized_lines
    )

    labeled_pattern = re.compile(
        r"(?im)^\s*"
        r"(?:"
        r"итог(?:\s+проверки)?|"
        r"результат(?:\s+проверки)?|"
        r"вердикт|"
        r"result|"
        r"verdict|"
        r"status"
        r")"
        r"\s*[:=\-–—]\s*"
        r"[^\w\r\n]*"
        r"(PASS|FAILED|FAIL|BLOCKED)\b"
    )

    bare_pattern = re.compile(
        r"(?im)^\s*"
        r"[^\w\r\n]*"
        r"(PASS|FAILED|FAIL|BLOCKED)\b"
        r"[^\w\r\n]*$"
    )

    verdicts = []

    for pattern in (
        labeled_pattern,
        bare_pattern,
    ):
        for match in pattern.finditer(text):
            verdicts.append(
                (
                    match.start(),
                    match.group(1).upper(),
                )
            )

    if not verdicts:
        return None

    verdict = max(
        verdicts,
        key=lambda item: item[0],
    )[1]

    if verdict == "PASS":
        return "passed"

    if verdict in (
        "FAIL",
        "FAILED",
    ):
        return "failed"

    if verdict == "BLOCKED":
        return "blocked"

    return None

def record_tool_observations(
    job_id,
    case_id,
    tool_name,
    arguments,
    result,
):
    if not job_id or not case_id:
        return []

    if tool_name in {
        "resource_register",
        "resource_update",
        "resource_list",
        "table_selection_list",
    }:
        return []

    created = []

    try:
        if (
            tool_name == "browser_set_table_row_selected"
            and isinstance(result, dict)
            and not result.get("error")
            and result.get("table_selection_key")
            and isinstance(result.get("selected"), bool)
        ):
            stored_selection = record_table_selection(
                job_id,
                case_id,
                result,
            )
            active_selections = list_table_selections(
                job_id,
                case_id=case_id,
                table_selection_key=result.get("table_selection_key"),
                selected_only=True,
            )
            result["table_selection_ledger_entry_id"] = (
                stored_selection.get("selection_id")
            )
            result["cross_page_selected_rows"] = [
                item.get("row_name")
                for item in active_selections
            ]
            result["cross_page_selected_entries"] = [
                {
                    "selection_id": item.get("selection_id"),
                    "row_name": item.get("row_name"),
                    "table_row_key": item.get("table_row_key"),
                }
                for item in active_selections
            ]
            result["cross_page_selected_count"] = len(active_selections)
            result["selection_bookkeeping_only"] = True
            result["bulk_action_authorized"] = False

        if (
            tool_name == "browser_probe_capabilities"
            and isinstance(result, dict)
            and not result.get("error")
        ):
            stored_snapshot = record_compatibility_snapshot(
                job_id,
                case_id,
                result,
            )
            result["compatibility_snapshot_id"] = stored_snapshot.get(
                "snapshot_id"
            )
            result["contract_changed"] = stored_snapshot.get("changed")
            result["baseline_fingerprint"] = stored_snapshot.get(
                "baseline_fingerprint"
            )
            result["changed_contract_sections"] = stored_snapshot.get(
                "changed_contract_sections"
            )
            result["compatibility_status"] = stored_snapshot.get("status")

        observations = (
            extract_observations(
                tool_name,
                arguments,
                result,
            )
        )

        for observation in observations:
            stored = add_observation(
                job_id,
                case_id,
                observation_type=(
                    observation["type"]
                ),
                source=(
                    observation["source"]
                ),
                data=(
                    observation["data"]
                ),
            )

            created.append(
                stored
            )

    except Exception as exc:
        console.print(
            f"[yellow]Observation warning: "
            f"{exc}[/yellow]"
        )

    return created


def classify_tool_evidence(result):
    """
    Determine whether a tool result may be used as
    positive evidence for a PASS verdict.

    This checks execution quality only.
    It does NOT prove semantic relevance of the evidence.
    """
    if not isinstance(result, dict):
        return {
            "usable_for_pass": False,
            "execution_status": "invalid_result",
            "reason": "tool_result_not_dict",
        }

    status = str(
        result.get("status")
        or ""
    ).strip().lower()

    if status == "blocked_by_policy":
        return {
            "usable_for_pass": False,
            "execution_status": "blocked_by_policy",
            "reason": (
                result.get("reason")
                or "blocked_by_policy"
            ),
        }

    if result.get("error"):
        return {
            "usable_for_pass": False,
            "execution_status": "tool_error",
            "reason": "tool_result_contains_error",
        }

    if result.get("executed") is False:
        return {
            "usable_for_pass": False,
            "execution_status": "not_executed",
            "reason": "executed_false",
        }

    click_status = str(
        result.get("click_status")
        or ""
    ).strip().lower()

    if click_status in (
        "not_executed",
        "failed",
    ):
        return {
            "usable_for_pass": False,
            "execution_status": click_status,
            "reason": (
                "click_status="
                + click_status
            ),
        }

    if result.get("success") is False:
        return {
            "usable_for_pass": False,
            "execution_status": "failed",
            "reason": "success_false",
        }

    if result.get("ok") is False:
        return {
            "usable_for_pass": False,
            "execution_status": "failed",
            "reason": "ok_false",
        }

    if status in (
        "error",
        "failed",
        "failure",
        "not_executed",
    ):
        return {
            "usable_for_pass": False,
            "execution_status": status,
            "reason": (
                "status=" + status
            ),
        }

    return {
        "usable_for_pass": True,
        "execution_status": (
            "executed"
            if result.get("executed") is True
            else "observed"
        ),
        "reason": None,
    }


def record_tool_evidence(
    job_id,
    case_id,
    tool_name,
    arguments,
    result,
    observation_ids=None,
):
    if not job_id or not case_id:
        return None

    if tool_name in {
        "resource_register",
        "resource_update",
        "resource_list",
        "table_selection_list",
    }:
        return None

    payload = {
        "tool": tool_name,
        "arguments": arguments,
        "result": result,
    }

    value = json.dumps(
        payload,
        ensure_ascii=False,
        default=str,
    )

    # Job history хранится на диске,
    # но всё равно не раздуваем её бесконечно
    # одним огромным response/log.
    if len(value) > 6000:
        value = (
            value[:6000]
            + "...<truncated>"
        )

    eligibility = (
        classify_tool_evidence(
            result
        )
    )

    return add_evidence(
        job_id,
        case_id,
        evidence_type=tool_name,
        value=value,
        source="uqa_tool",
        observation_ids=(
            observation_ids
            or []
        ),
        usable_for_pass=(
            eligibility[
                "usable_for_pass"
            ]
        ),
        usable_for_verdict=(
            eligibility[
                "usable_for_pass"
            ]
        ),
        execution_status=(
            eligibility[
                "execution_status"
            ]
        ),
        eligibility_reason=(
            eligibility.get(
                "reason"
            )
        ),
    )


def _compact_model_browser_record(record, string_limit=240):
    if not isinstance(record, dict):
        return str(record)[:string_limit]

    compacted = {}

    for key, value in record.items():
        if value is None or value == "" or value == [] or value == {}:
            continue

        if key == "table_context" and isinstance(value, dict):
            table_context = {
                field: value.get(field)
                for field in (
                    "section",
                    "row_text",
                    "data_cell_count",
                    "header_cell_count",
                )
                if value.get(field) not in (None, "", [], {})
            }

            if "row_text" in table_context:
                table_context["row_text"] = str(
                    table_context["row_text"]
                )[:string_limit]

            if table_context:
                compacted[key] = table_context

            continue

        if isinstance(value, str):
            compacted[key] = value[:string_limit]
        elif isinstance(value, list):
            compacted[key] = [
                str(item)[:80]
                for item in value[:10]
            ]
        elif isinstance(value, (bool, int, float)):
            compacted[key] = value

    return compacted


def _browser_element_model_priority(item):
    if not isinstance(item, dict):
        return 9

    role = str(item.get("role") or "").casefold()
    tag = str(item.get("tag") or "").casefold()

    if role in {"menuitem", "option"}:
        return 0

    if tag in {"input", "select", "textarea"} or role in {
        "textbox",
        "combobox",
        "checkbox",
        "radio",
    }:
        return 1

    if tag == "button" or role == "button":
        return 2

    if tag == "a" or role in {"link", "tab"}:
        return 3

    return 4


def tool_result_for_model(tool_name, result, max_chars=14000):
    """Return a bounded model view while evidence keeps the original result."""
    if not isinstance(result, dict):
        return result

    if not str(tool_name or "").startswith("browser_"):
        return result

    compacted = {}
    bulky_keys = {
        "interactive_elements",
        "network_requests",
        "console_errors",
        "http_errors",
        "failed_requests",
        "text_preview",
    }

    for key, value in result.items():
        if key in bulky_keys:
            continue

        if isinstance(value, str):
            compacted[key] = value[:1000]
        else:
            compacted[key] = value

    text_preview = str(result.get("text_preview") or "")
    compacted["text_preview"] = text_preview[:2500]

    for key in (
        "network_requests",
        "console_errors",
        "http_errors",
        "failed_requests",
    ):
        values = result.get(key) or []
        compacted[key] = [
            _compact_model_browser_record(item)
            for item in values[-12:]
        ]
        compacted[f"{key}_total"] = len(values)

    elements = result.get("interactive_elements") or []
    prioritized = sorted(
        enumerate(elements),
        key=lambda pair: (
            _browser_element_model_priority(pair[1]),
            pair[0],
        ),
    )
    selected = []

    for _, item in prioritized:
        candidate = _compact_model_browser_record(item)
        proposed = [*selected, candidate]
        compacted["interactive_elements"] = proposed

        if len(json.dumps(compacted, ensure_ascii=False, default=str)) > max_chars:
            break

        selected = proposed

    compacted["interactive_elements"] = selected
    compacted["interactive_elements_total"] = len(elements)
    compacted["model_view_compacted"] = True

    while (
        len(json.dumps(compacted, ensure_ascii=False, default=str)) > max_chars
        and len(compacted["text_preview"]) > 500
    ):
        compacted["text_preview"] = compacted["text_preview"][:-500]

    return compacted


def _historical_browser_result_summary(tool_name, content):
    parsed = content

    if isinstance(content, str):
        try:
            parsed = json.loads(content)
        except (TypeError, ValueError):
            parsed = {}

    if not isinstance(parsed, dict):
        parsed = {}

    summary_keys = (
        "status",
        "error",
        "executed",
        "action",
        "current_url",
        "final_url",
        "url",
        "title",
        "http_status",
        "click_status",
        "filled_element",
        "clicked_element",
        "semantic_name",
        "semantic_role",
        "semantic_container",
        "context_menu_name",
        "exact_match_count",
        "matched_count",
        "selection_status",
        "pressed_key",
        "keyboard_target",
        "focus_order_status",
        "focus_order_mismatch",
        "drag_source",
        "drag_target",
        "drag_status",
        "resized_target",
        "resize_status",
        "table_inspection_status",
        "sorted_column",
        "sort_status",
        "table_row_name",
        "row_selection_status",
        "table_page_control",
        "table_page_status",
        "filtered_column",
        "filter_status",
        "select_all_status",
        "bulk_action_name",
        "bulk_action_status",
        "bulk_action_enabled",
        "selected_row_count",
        "compatibility_probe_status",
        "compatibility_status",
        "contract_fingerprint",
        "contract_changed",
        "capability_gaps",
        "compatibility_snapshot_id",
        "action_policy_status",
        "auth_challenge_status",
        "network_request_count",
        "uqa_evidence_id",
    )
    summary = {
        key: parsed.get(key)
        for key in summary_keys
        if parsed.get(key) not in (None, "", [], {})
    }
    summary["tool"] = tool_name
    summary["model_history_compacted"] = True
    return summary


def messages_for_model(messages, keep_latest_browser_results=1):
    browser_indices = [
        index
        for index, message in enumerate(messages or [])
        if message.get("role") == "tool"
        and str(message.get("tool_name") or "").startswith("browser_")
    ]
    keep_count = max(0, int(keep_latest_browser_results))
    keep = set(browser_indices[-keep_count:] if keep_count else [])
    prepared = []

    for index, message in enumerate(messages or []):
        copied = dict(message)

        if index in browser_indices and index not in keep:
            copied["content"] = json.dumps(
                _historical_browser_result_summary(
                    copied.get("tool_name"),
                    copied.get("content"),
                ),
                ensure_ascii=False,
            )

        prepared.append(copied)

    return prepared


def _normalize_semantic_subject(
    value,
):
    return " ".join(
        str(
            value
            or ""
        )
        .strip()
        .casefold()
        .split()
    )


UI_ASSERTION_FIELDS = {
    "visible",
    "enabled",
    "disabled",
    "editable",
    "value",
    "text",
}

UI_BOOLEAN_ASSERTION_FIELDS = {
    "visible",
    "enabled",
    "disabled",
    "editable",
}

UI_ASSERTION_OPERATORS = {
    "eq",
    "ne",
    "contains",
    "not_contains",
}


def _evaluate_ui_assertions(
    raw_assertions,
    observation,
):
    if raw_assertions is None:
        return (
            [],
            ["ui_assertions_missing"],
            None,
        )

    if isinstance(
        raw_assertions,
        dict,
    ):
        raw_assertions = [
            raw_assertions
        ]

    if not isinstance(
        raw_assertions,
        list,
    ):
        return (
            [],
            ["ui_assertions_invalid"],
            None,
        )

    if not raw_assertions:
        return (
            [],
            ["ui_assertions_missing"],
            None,
        )

    data = (
        observation.get("data")
        if isinstance(
            observation,
            dict,
        )
        else {}
    ) or {}

    observation_id = observation.get(
        "observation_id"
    )

    normalized = []
    issues = []

    for index, item in enumerate(
        raw_assertions,
        start=1,
    ):
        if not isinstance(
            item,
            dict,
        ):
            issues.append(
                f"ui_assertion_{index}_invalid"
            )
            continue

        field = str(
            item.get("field")
            or ""
        ).strip()

        operator = str(
            item.get("operator")
            or "eq"
        ).strip().lower()

        expected = item.get(
            "expected"
        )

        if field not in UI_ASSERTION_FIELDS:
            issues.append(
                f"ui_assertion_{index}_unsupported_field={field}"
            )
            continue

        if operator not in UI_ASSERTION_OPERATORS:
            issues.append(
                f"ui_assertion_{index}_unsupported_operator={operator}"
            )
            continue

        actual = data.get(
            field
        )

        if field in UI_BOOLEAN_ASSERTION_FIELDS:
            if operator not in {
                "eq",
                "ne",
            }:
                issues.append(
                    f"ui_assertion_{index}_invalid_operator_for_boolean={operator}"
                )
                continue

            if not isinstance(
                expected,
                bool,
            ):
                issues.append(
                    f"ui_assertion_{index}_expected_must_be_boolean"
                )
                continue

            if not isinstance(
                actual,
                bool,
            ):
                issues.append(
                    f"ui_assertion_{index}_actual_not_boolean"
                )
                continue

            if operator == "eq":
                satisfied = (
                    actual == expected
                )
            else:
                satisfied = (
                    actual != expected
                )

        else:
            if expected is None:
                issues.append(
                    f"ui_assertion_{index}_expected_missing"
                )
                continue

            if actual is None:
                issues.append(
                    f"ui_assertion_{index}_actual_missing"
                )
                continue

            actual_text = str(
                actual
            )

            expected_text = str(
                expected
            )

            if operator == "eq":
                satisfied = (
                    actual_text
                    == expected_text
                )

            elif operator == "ne":
                satisfied = (
                    actual_text
                    != expected_text
                )

            elif operator == "contains":
                satisfied = (
                    expected_text
                    in actual_text
                )

            else:
                satisfied = (
                    expected_text
                    not in actual_text
                )

        normalized.append(
            {
                "field": field,
                "operator": operator,
                "expected": expected,
                "actual": actual,
                "satisfied": satisfied,
                "observation_id": (
                    observation_id
                ),
            }
        )

    if issues:
        return (
            normalized,
            issues,
            None,
        )

    return (
        normalized,
        [],
        all(
            item["satisfied"]
            for item in normalized
        ),
    )


def verify_structured_check_evidence(
    job_id,
    case_id,
    checks,
):
    """
    Bind model-declared check evidence to evidence that
    UQA Core actually recorded for this exact Job/Case.

    This validates provenance, not semantic sufficiency.
    """
    from copy import deepcopy

    job = get_job(job_id)

    if not job:
        raise FileNotFoundError(
            job_id
        )

    case = next(
        (
            item
            for item in job.get(
                "test_cases",
                [],
            )
            if item.get("case_id") == case_id
        ),
        None,
    )

    if case is None:
        raise FileNotFoundError(
            case_id
        )

    job_type = str(
        job.get("job_type")
        or "generic"
    ).strip().lower()

    evidence_by_id = {
        str(item.get("evidence_id")): item
        for item in case.get(
            "evidence",
            [],
        )
        if item.get("evidence_id")
    }

    valid_ids = set(
        evidence_by_id
    )

    observation_by_id = {
        str(
            item.get(
                "observation_id"
            )
        ): item
        for item in case.get(
            "observations",
            [],
        )
        if item.get(
            "observation_id"
        )
    }

    locked_requirement = (
        case.get("requirement")
        if isinstance(
            case.get("requirement"),
            dict,
        )
        else None
    )

    locked_ui_requirement = None
    locked_requirement_error = None

    if (
        locked_requirement
        and locked_requirement.get(
            "locked"
        ) is True
        and locked_requirement.get(
            "type"
        ) == "ui_semantic"
    ):
        locked_subject = str(
            locked_requirement.get(
                "subject"
            )
            or ""
        ).strip()

        locked_assertions = (
            locked_requirement.get(
                "assertions"
            )
        )

        if (
            not locked_subject
            or not isinstance(
                locked_assertions,
                list,
            )
            or not locked_assertions
        ):
            locked_requirement_error = (
                "locked_requirement_invalid"
            )

        else:
            locked_ui_requirement = (
                locked_requirement
            )

    verified = deepcopy(
        checks
    )

    errors = []

    for check in verified:
        status = str(
            check.get("status")
            or ""
        ).lower()

        if (
            status in (
                "passed",
                "failed",
            )
            and locked_ui_requirement
        ):
            check["subject"] = str(
                locked_ui_requirement[
                    "subject"
                ]
            )

            check["assertions"] = (
                deepcopy(
                    locked_ui_requirement[
                        "assertions"
                    ]
                )
            )

        refs = [
            str(value).strip()
            for value in (
                check.get("evidence")
                or []
            )
            if str(value).strip()
        ]

        observation_refs = [
            str(value).strip()
            for value in (
                check.get(
                    "observations"
                )
                or []
            )
            if str(value).strip()
        ]

        subject = str(
            check.get(
                "subject"
            )
            or ""
        ).strip()

        issues = []

        if (
            status in (
                "passed",
                "failed",
            )
            and locked_requirement_error
        ):
            issues.append(
                locked_requirement_error
            )

        if (
            status in (
                "passed",
                "failed",
            )
            and not refs
        ):
            issues.append(
                "evidence_missing"
            )

        invalid = [
            ref
            for ref in refs
            if ref not in valid_ids
        ]

        if invalid:
            issues.append(
                "unknown_evidence_ids="
                + ",".join(
                    invalid[:10]
                )
            )

        # PASS and FAIL both require successfully obtained
        # runtime evidence. A QA-tool failure, policy block or
        # non-executed action is infrastructure evidence only
        # and cannot prove product behaviour.
        if (
            status in (
                "passed",
                "failed",
            )
            and refs
        ):
            unusable = [
                ref
                for ref in refs
                if (
                    ref in evidence_by_id
                    and evidence_by_id[
                        ref
                    ].get(
                        "usable_for_verdict",
                        evidence_by_id[
                            ref
                        ].get(
                            "usable_for_pass"
                        ),
                    )
                    is not True
                )
            ]

            if unusable:
                issues.append(
                    "evidence_not_usable_for_verdict="
                    + ",".join(
                        unusable[:10]
                    )
                )

        # ----------------------------------------------------
        # Semantic binding for browser semantic and table-row inspections.
        #
        # Evidence tells us which observations were created
        # by that exact tool call. A check may therefore not
        # borrow another observation from the same case.
        # ----------------------------------------------------

        linked_observation_ids = set()
        linked_ui_observation_ids = set()

        for ref in refs:
            evidence_item = (
                evidence_by_id.get(
                    ref
                )
            )

            if not evidence_item:
                continue

            for observation_id in (
                evidence_item.get(
                    "observation_ids"
                )
                or []
            ):
                observation_id = str(
                    observation_id
                ).strip()

                if not observation_id:
                    continue

                linked_observation_ids.add(
                    observation_id
                )

                observation = (
                    observation_by_id.get(
                        observation_id
                    )
                )

                if (
                    observation
                    and observation.get(
                        "type"
                    )
                    == "ui_element"
                ):
                    linked_ui_observation_ids.add(
                        observation_id
                    )

        # Regression must never silently fall back from
        # a deterministic locked UI requirement to a
        # model-defined semantic assertion.
        #
        # Generic/non-regression UQA conversations retain
        # the existing behaviour.
        if (
            status in (
                "passed",
                "failed",
            )
            and job_type == "regression"
            and linked_ui_observation_ids
            and locked_ui_requirement is None
            and locked_requirement_error is None
        ):
            issues.append(
                "requirement_not_machine_locked"
            )

        if (
            status in (
                "passed",
                "failed",
            )
            and linked_ui_observation_ids
        ):
            if not subject:
                issues.append(
                    "semantic_subject_missing"
                )

            if not observation_refs:
                issues.append(
                    "semantic_observation_missing"
                )

            unknown_observations = [
                ref
                for ref in observation_refs
                if ref not in observation_by_id
            ]

            if unknown_observations:
                issues.append(
                    "unknown_observation_ids="
                    + ",".join(
                        unknown_observations[
                            :10
                        ]
                    )
                )

            unlinked_observations = [
                ref
                for ref in observation_refs
                if (
                    ref in observation_by_id
                    and ref
                    not in linked_observation_ids
                )
            ]

            if unlinked_observations:
                issues.append(
                    "observation_not_linked_to_evidence="
                    + ",".join(
                        unlinked_observations[
                            :10
                        ]
                    )
                )

            semantic_refs = [
                ref
                for ref in observation_refs
                if ref
                in linked_ui_observation_ids
            ]

            if (
                observation_refs
                and not semantic_refs
            ):
                issues.append(
                    "semantic_observation_missing"
                )

            if subject and semantic_refs:
                expected_subject = (
                    _normalize_semantic_subject(
                        subject
                    )
                )

                mismatched = []

                for ref in semantic_refs:
                    observation_subject = (
                        observation_by_id[
                            ref
                        ]
                        .get(
                            "data",
                            {},
                        )
                        .get(
                            "subject"
                        )
                    )

                    if (
                        _normalize_semantic_subject(
                            observation_subject
                        )
                        != expected_subject
                    ):
                        mismatched.append(
                            ref
                        )

                if mismatched:
                    issues.append(
                        "semantic_evidence_mismatch="
                        + ",".join(
                            mismatched[:10]
                        )
                    )

            if len(
                semantic_refs
            ) > 1:
                issues.append(
                    "semantic_observation_ambiguous="
                    + ",".join(
                        semantic_refs[:10]
                    )
                )

            elif (
                len(semantic_refs) == 1
                and subject
            ):
                semantic_observation = (
                    observation_by_id[
                        semantic_refs[0]
                    ]
                )

                (
                    normalized_assertions,
                    assertion_issues,
                    assertion_satisfied,
                ) = _evaluate_ui_assertions(
                    check.get(
                        "assertions"
                    ),
                    semantic_observation,
                )

                check[
                    "assertions"
                ] = normalized_assertions

                issues.extend(
                    assertion_issues
                )

                if (
                    not assertion_issues
                    and assertion_satisfied
                    is not None
                ):
                    model_status = status

                    derived_status = (
                        "passed"
                        if assertion_satisfied
                        else "failed"
                    )

                    check[
                        "status"
                    ] = derived_status

                    status = derived_status

                    if (
                        derived_status
                        == "failed"
                    ):
                        failed_assertions = [
                            item
                            for item
                            in normalized_assertions
                            if item.get(
                                "satisfied"
                            )
                            is False
                        ]

                        check["reason"] = (
                            "UQA CORE: "
                            "deterministic_ui_assertion_mismatch "
                            + json.dumps(
                                failed_assertions,
                                ensure_ascii=False,
                            )[:1500]
                        )

                    elif (
                        model_status
                        == "failed"
                    ):
                        check[
                            "reason"
                        ] = None

        if not issues:
            continue

        original_status = status

        check["status"] = "blocked"

        core_reason = (
            "UQA CORE: "
            + "; ".join(issues)
        )

        existing_reason = (
            check.get("reason")
            or ""
        ).strip()

        if existing_reason:
            check["reason"] = (
                existing_reason
                + " | "
                + core_reason
            )
        else:
            check["reason"] = (
                core_reason
            )

        errors.append(
            {
                "check_id": check.get(
                    "check_id"
                ),
                "title": check.get(
                    "title"
                ),
                "original_status": (
                    original_status
                ),
                "issues": issues,
            }
        )

    return verified, errors


UQA_CHECKS_START = "[UQA_CHECKS_JSON]"
UQA_CHECKS_END = "[/UQA_CHECKS_JSON]"


def extract_structured_checks(content: str):
    """
    Возвращает:
      checks        -> list | None
      visible_text  -> текст без служебного JSON
      error         -> str | None

    None checks означает, что structured block вообще
    отсутствовал — для обратной совместимости тогда
    работает старый verdict parser.
    """
    text = str(content or "")

    start = text.rfind(
        UQA_CHECKS_START
    )

    if start < 0:
        return None, text.strip(), None

    end = text.find(
        UQA_CHECKS_END,
        start + len(UQA_CHECKS_START),
    )

    if end < 0:
        visible = text[:start].strip()

        return (
            None,
            visible,
            "structured_result_missing_end_marker",
        )

    raw = text[
        start + len(UQA_CHECKS_START):
        end
    ].strip()

    visible = (
        text[:start]
        + text[
            end + len(UQA_CHECKS_END):
        ]
    ).strip()

    try:
        payload = json.loads(raw)
    except Exception as exc:
        return (
            None,
            visible,
            (
                "structured_result_invalid_json:"
                f"{type(exc).__name__}"
            ),
        )

    if isinstance(payload, dict):
        checks = payload.get("checks")
    else:
        checks = None

    if not isinstance(checks, list):
        return (
            None,
            visible,
            "structured_result_checks_missing",
        )

    if not checks:
        return (
            None,
            visible,
            "structured_result_checks_empty",
        )

    try:
        checks = _normalize_checks(
            checks
        )
    except Exception as exc:
        return (
            None,
            visible,
            (
                "structured_result_invalid_checks:"
                f"{str(exc)}"
            ),
        )

    return checks, visible, None


def infer_case_status_from_checks(checks):
    if not checks:
        return None

    statuses = [
        str(check.get("status") or "").lower()
        for check in checks
    ]

    # FAIL имеет максимальный приоритет.
    if "failed" in statuses:
        return "failed"

    # Если хотя бы обязательная часть BLOCKED,
    # весь case пока BLOCKED.
    if "blocked" in statuses:
        return "blocked"

    # Полностью skipped case не считаем PASS.
    if all(
        status == "skipped"
        for status in statuses
    ):
        return "blocked"

    if all(
        status in {"passed", "skipped"}
        for status in statuses
    ):
        return "passed"

    return None


def infer_case_status_v2(content: str):
    """
    Сначала использует старый строгий parser.
    Затем распознаёт явный BLOCKED в естественном
    итоговом тексте модели.
    """
    status = infer_case_status(content)

    if status:
        return status

    text = str(content or "")
    text = re.sub(
        r"[*_`~]+",
        "",
        text,
    )

    blocked_patterns = (
        r"(?i)\bсчита(?:ется|ть)\s+BLOCKED\b",
        r"(?i)\b(?:проверка|часть|этап)"
        r"[^\n]{0,300}\bBLOCKED\b",
        r"(?i)\b(?:overall|итог|вердикт|результат|status)"
        r"[^\n]{0,300}\bBLOCKED\b",
    )

    if any(
        re.search(pattern, text)
        for pattern in blocked_patterns
    ):
        return "blocked"

    return None


def recompute_job_status(job_id: str):
    """
    Job status вычисляется из всех test cases.

    Пока есть pending/running — Job running.
    После завершения всех cases:
      failed  имеет приоритет над blocked;
      blocked имеет приоритет над passed;
      passed/skipped -> passed;
      только skipped -> blocked.
    """
    job = get_job(job_id)

    if not job:
        return None

    if job.get("status") == "cancelled":
        return "cancelled"

    statuses = [
        str(case.get("status") or "").lower()
        for case in job.get("test_cases", [])
    ]

    if not statuses:
        target = "created"

    elif any(
        status in {"pending", "running"}
        for status in statuses
    ):
        target = "running"

    elif "failed" in statuses:
        target = "failed"

    elif "blocked" in statuses:
        target = "blocked"

    elif all(
        status == "skipped"
        for status in statuses
    ):
        target = "blocked"

    elif all(
        status in {"passed", "skipped"}
        for status in statuses
    ):
        target = "passed"

    else:
        target = "blocked"

    set_job_status(
        job_id,
        target,
    )

    return target


def finalize_case_blocked(
    job_id: str,
    case_id: str,
    reason_code: str,
    detail: str = "",
):
    detail = str(detail or "").strip()

    result = (
        "[UQA CORE]\n"
        "status=BLOCKED\n"
        f"reason={reason_code}"
    )

    if detail:
        result += (
            "\n"
            f"detail={detail[:1500]}"
        )

    update_test_case(
        job_id,
        case_id,
        status="blocked",
        result=result,
    )

    return recompute_job_status(
        job_id
    )


REGRESSION_PLANNER_PROMPT = """
Ты UQA Regression Planner.

Твоя задача — преобразовать один пользовательский запрос
в независимые QA test cases и проверки внутри каждого case.

Ты НЕ выполняешь тестирование.
Ты НЕ вызываешь tools.
Ты только составляешь план.

Верни ТОЛЬКО валидный JSON такого вида:

{
  "cases": [
    {
      "title": "Краткое название проверки",
      "task": "Точная задача одного test case",
      "expected": "Общий ожидаемый результат или null",
      "checks": [
        {
          "title": "Критерий внутри текущего case",
          "expected": "Ожидаемое состояние или null"
        }
      ]
    }
  ]
}

Правила:
- Один case = одно логически самостоятельное проверяемое условие.
- Не объединяй много независимых условий в один case.
- Последовательные шаги, которые используют один и тот же созданный или
  изменённый объект, зависят от состояния предыдущего шага либо вместе
  образуют один жизненный цикл, — это ОДИН case.
- Несколько критериев под вводной фразой "проверь, что" / "verify that"
  относятся к текущему workflow и должны быть элементами checks этого case,
  а не отдельными cases.
- Разделяй на несколько cases только проверки, которые можно выполнить
  независимо в чистом контексте без состояния соседнего case.
- Не придумывай требований, которых нет в запросе.
- Если пользователь явно задал критерий или ожидаемое состояние, сохраняй его смысл точно и не расширяй альтернативами.
  Например: "кнопка недоступна/disabled" нельзя превращать в "неактивна или скрыта".
  "отображается" нельзя превращать в "отображается или доступна".
- Один case должен проверять именно тот критерий, который сформулирован пользователем.
- Если expected явно не задан, используй null.
- Если отдельных критериев нет, используй пустой список checks.
- Если expected потребуется определить по документации,
  укажи это в task; исполнитель сможет использовать knowledge_search.
- Сохраняй ограничения пользователя:
  read-only, ничего не изменять, не создавать и т.п.
- Не добавляй тесты, не относящиеся к запросу.
- Максимум 20 cases.
- Никакого Markdown вокруг JSON.
"""


def _parse_regression_plan(content: str):
    text = str(
        content or ""
    ).strip()

    first = text.find("{")
    last = text.rfind("}")

    if first < 0 or last < first:
        raise ValueError(
            "regression planner returned no JSON object"
        )

    payload = json.loads(
        text[first:last + 1]
    )

    if not isinstance(payload, dict):
        raise ValueError(
            "regression plan must be object"
        )

    raw_cases = payload.get("cases")

    if not isinstance(raw_cases, list):
        raise ValueError(
            "regression plan cases missing"
        )

    cases = []
    seen = set()

    for index, item in enumerate(
        raw_cases,
        start=1,
    ):
        if not isinstance(item, dict):
            continue

        title = str(
            item.get("title")
            or f"Case {index}"
        ).strip()

        task = str(
            item.get("task")
            or title
        ).strip()

        expected = item.get("expected")

        if expected is not None:
            expected = str(
                expected
            ).strip() or None

        if not task:
            continue

        dedupe_key = (
            title.lower(),
            task.lower(),
        )

        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)

        checks = _normalize_planned_checks(
            item.get("checks")
        )

        cases.append(
            {
                "title": title[:500],
                "task": task,
                "expected": expected,
                "checks": checks,
            }
        )

        if len(cases) >= MAX_REGRESSION_CASES:
            break

    if not cases:
        raise ValueError(
            "regression planner returned zero valid cases"
        )

    return cases


def _normalize_planned_checks(raw_checks):
    if not isinstance(raw_checks, list):
        return []

    checks = []

    for index, item in enumerate(raw_checks, start=1):
        if isinstance(item, str):
            title = item.strip().rstrip(".;")
            expected = title or None
            check_id = f"planned-{index:03d}"

        elif isinstance(item, dict):
            title = str(
                item.get("title")
                or item.get("task")
                or f"Check {index}"
            ).strip().rstrip(".;")

            check_id = str(
                item.get("check_id")
                or f"planned-{index:03d}"
            ).strip()

            expected = item.get("expected")

            if expected is not None:
                expected = str(expected).strip() or None

        else:
            continue

        if not title:
            continue

        checks.append(
            {
                "check_id": check_id[:200],
                "title": title[:500],
                "expected": expected,
            }
        )

        if len(checks) >= MAX_REGRESSION_CASES:
            break

    return checks


def _planned_check_lifecycle_kind(check):
    """Classify only Core-owned resource-ledger/cleanup assertions."""
    if not isinstance(check, dict):
        return None

    text = " ".join(
        str(check.get(key) or "")
        for key in ("title", "expected")
    ).casefold()

    has_cleanup = bool(
        re.search(
            r"(?:\bcleanup\b|\bclean[- ]?up\b|очист\w*)",
            text,
        )
    )
    has_absence = bool(
        re.search(
            r"(?:не\s+существ\w*|не\s+отображ\w*|"
            r"отсутств\w*|\bnot\s+(?:exist|present|visible)\b|"
            r"\babsent\b|\bno\s+longer\s+exists?\b)",
            text,
        )
    )

    if has_cleanup and has_absence:
        return "cleanup_absence"

    if has_cleanup and re.search(
        r"(?:удал\w*|очищ\w*|\bdelet\w*|\bremov\w*|\bcleaned\b)",
        text,
    ):
        return "cleanup_deleted"

    if (
        re.search(r"(?:ресурс\w*|\bresource\b|\bledger\b)", text)
        and re.search(
            r"(?:зарегистр\w*|\bregister\w*|\brecorded\b|\bstored\b)",
            text,
        )
    ):
        return "ledger_registered"

    return None


def verify_planned_check_coverage(job_id, case_id, checks):
    """Bind result checks one-to-one to the authoritative case plan."""
    from copy import deepcopy

    job = get_job(job_id)

    if not job:
        raise FileNotFoundError(job_id)

    case = next(
        (
            item
            for item in job.get("test_cases", [])
            if item.get("case_id") == case_id
        ),
        None,
    )

    if case is None:
        raise FileNotFoundError(case_id)

    planned = _normalize_planned_checks(
        case.get("planned_checks")
    )
    verified = deepcopy(checks)

    if not planned:
        return verified, []

    def normalized_title(item):
        return " ".join(
            str(item.get("title") or "")
            .strip()
            .casefold()
            .split()
        )

    planned_by_title = {}

    for item in planned:
        title_key = normalized_title(item)

        if not title_key:
            continue

        planned_by_title.setdefault(title_key, []).append(item)

    actual_title_counts = {}

    for item in verified:
        title_key = normalized_title(item)

        if title_key:
            actual_title_counts[title_key] = (
                actual_title_counts.get(title_key, 0) + 1
            )

    expected_id_set = {
        item["check_id"]
        for item in planned
    }
    already_claimed_ids = {
        str(item.get("check_id") or "").strip()
        for item in verified
        if str(item.get("check_id") or "").strip()
        in expected_id_set
    }

    # Models sometimes preserve every planned title exactly but replace the
    # authoritative IDs with check-001/check-002. A unique exact title gives
    # Core a deterministic one-to-one repair without fuzzy matching.
    for item in verified:
        current_id = str(item.get("check_id") or "").strip()

        if current_id in expected_id_set:
            continue

        title_key = normalized_title(item)
        candidates = planned_by_title.get(title_key) or []

        if (
            title_key
            and actual_title_counts.get(title_key) == 1
            and len(candidates) == 1
            and candidates[0]["check_id"] not in already_claimed_ids
        ):
            item["model_check_id"] = current_id or None
            item["check_id"] = candidates[0]["check_id"]
            already_claimed_ids.add(candidates[0]["check_id"])

    expected_ids = [item["check_id"] for item in planned]
    actual_ids = [
        str(item.get("check_id") or "").strip()
        for item in verified
    ]
    duplicates = sorted({
        value
        for value in actual_ids
        if value and actual_ids.count(value) > 1
    })
    missing = [
        value
        for value in expected_ids
        if value not in actual_ids
    ]
    unexpected = [
        value
        for value in actual_ids
        if value not in expected_ids
    ]
    errors = []

    if len(verified) != len(planned):
        errors.append({
            "issue": "planned_check_count_mismatch",
            "expected": len(planned),
            "actual": len(verified),
        })

    if missing:
        errors.append({
            "issue": "planned_check_ids_missing",
            "check_ids": missing,
        })

    if unexpected:
        errors.append({
            "issue": "unexpected_check_ids",
            "check_ids": unexpected,
        })

    if duplicates:
        errors.append({
            "issue": "duplicate_check_ids",
            "check_ids": duplicates,
        })

    actual_by_id = {
        str(item.get("check_id") or "").strip(): item
        for item in verified
        if str(item.get("check_id") or "").strip()
    }
    ordered = []

    for planned_item in planned:
        check_id = planned_item["check_id"]
        item = actual_by_id.get(check_id)

        if item is None:
            item = {
                "check_id": check_id,
                "title": planned_item["title"],
                "status": "blocked",
                "expected": planned_item.get("expected"),
                "actual": None,
                "evidence": [],
                "observations": [],
                "assertions": [],
                "reason": "UQA CORE: planned_check_missing",
            }
        else:
            item["title"] = planned_item["title"]
            item["expected"] = planned_item.get("expected")

        item["_planned_lifecycle_kind"] = (
            _planned_check_lifecycle_kind(planned_item)
        )
        ordered.append(item)

    for item in verified:
        if str(item.get("check_id") or "").strip() not in expected_ids:
            item["status"] = "blocked"
            item["reason"] = "UQA CORE: unexpected_check_id"
            ordered.append(item)

    if errors:
        for item in ordered:
            item["status"] = "blocked"
            reason = str(item.get("reason") or "").strip()
            core_reason = "UQA CORE: planned_check_coverage_mismatch"
            item["reason"] = (
                reason + " | " + core_reason
                if reason
                else core_reason
            )

    return ordered, errors


def _resource_cleanup_absence_confirmed(resource):
    for attempt in reversed(resource.get("cleanup_attempts", [])):
        if attempt.get("status") != "cleaned":
            continue

        destructive_seen = False

        for event in attempt.get("events", []):
            data = event.get("data") or {}
            result = data.get("result") or {}

            if (
                result.get("action_class") == "destructive"
                and result.get("action_policy_status") == "confirmed"
                and result.get("executed") is not False
                and not result.get("error")
            ):
                destructive_seen = True
                continue

            if (
                destructive_seen
                and data.get("tool") == "browser_inspect_semantic"
                and result.get("error") == "semantic_element_not_found"
            ):
                return True

    return False


def verify_resource_lifecycle_checks(
    job_id,
    case_id,
    checks,
    phase="case",
):
    """Derive Core-owned ledger and cleanup checks from persisted facts."""
    from copy import deepcopy

    job = get_job(job_id)

    if not job:
        raise FileNotFoundError(job_id)

    verified = deepcopy(checks)
    resources = [
        item
        for item in job.get("resources", [])
        if item.get("created_by_case") == case_id
    ]
    cleanup_resources = [
        item
        for item in resources
        if item.get("cleanup_required")
    ]
    lifecycle_ids = set()

    for check in verified:
        kind = check.get("_planned_lifecycle_kind")

        if not kind:
            continue

        lifecycle_ids.add(check.get("check_id"))
        check["evidence"] = []
        check["observations"] = []
        check["assertions"] = []

        if kind == "ledger_registered":
            if resources:
                check["status"] = "passed"
                check["actual"] = (
                    f"UQA Core ledger contains {len(resources)} "
                    "resource(s) created by this case."
                )
                check["reason"] = "UQA CORE: resource_ledger_verified"
            else:
                check["status"] = "blocked"
                check["actual"] = "No resource was registered by this case."
                check["reason"] = "UQA CORE: resource_not_registered"

        elif kind == "cleanup_deleted":
            cleaned = bool(cleanup_resources) and all(
                item.get("status") == "cleaned"
                and any(
                    attempt.get("status") == "cleaned"
                    for attempt in item.get("cleanup_attempts", [])
                )
                for item in cleanup_resources
            )

            if cleaned:
                check["status"] = "passed"
                check["actual"] = (
                    "Cleanup Manager marked every case resource cleaned."
                )
                check["reason"] = "UQA CORE: cleanup_ledger_verified"
            else:
                failed = any(
                    item.get("status") == "cleanup_failed"
                    for item in cleanup_resources
                )
                check["status"] = (
                    "failed" if phase == "cleanup" and failed else "blocked"
                )
                check["actual"] = (
                    "Cleanup has not completed for every case resource."
                )
                check["reason"] = (
                    "UQA CORE: cleanup_failed"
                    if phase == "cleanup" and failed
                    else "UQA CORE: cleanup_pending"
                )

        elif kind == "cleanup_absence":
            confirmed = bool(cleanup_resources) and all(
                item.get("status") == "cleaned"
                and _resource_cleanup_absence_confirmed(item)
                for item in cleanup_resources
            )

            if confirmed:
                check["status"] = "passed"
                check["actual"] = (
                    "Post-cleanup semantic lookup confirmed absence."
                )
                check["reason"] = (
                    "UQA CORE: post_cleanup_absence_verified"
                )
            else:
                failed = any(
                    item.get("status") == "cleanup_failed"
                    for item in cleanup_resources
                )
                check["status"] = (
                    "failed" if phase == "cleanup" and failed else "blocked"
                )
                check["actual"] = (
                    "No completed post-cleanup absence proof is stored."
                )
                check["reason"] = (
                    "UQA CORE: cleanup_verification_failed"
                    if phase == "cleanup" and failed
                    else "UQA CORE: cleanup_verification_pending"
                )

    return verified, lifecycle_ids


def reconcile_resource_lifecycle_checks(job_id):
    """Recompute Core-owned lifecycle checks after Cleanup Manager."""
    job = get_job(job_id)

    if not job:
        raise FileNotFoundError(job_id)

    updated_case_ids = []

    for case in job.get("test_cases", []):
        checks = case.get("checks") or []

        if not checks:
            continue

        bound, coverage_errors = verify_planned_check_coverage(
            job_id,
            case.get("case_id"),
            checks,
        )

        if coverage_errors:
            continue

        verified, lifecycle_ids = verify_resource_lifecycle_checks(
            job_id,
            case.get("case_id"),
            bound,
            phase="cleanup",
        )

        if not lifecycle_ids:
            continue

        status = infer_case_status_from_checks(verified) or "blocked"
        update_test_case(
            job_id,
            case.get("case_id"),
            status=status,
            checks=verified,
        )
        updated_case_ids.append(case.get("case_id"))

    recompute_job_status(job_id)
    return updated_case_ids


def _numbered_items_are_workflow_checks(lines, first_item_index):
    """Detect a numbered checklist introduced by "verify/check that"."""
    intro = ""

    for line in reversed(lines[:first_item_index]):
        candidate = line.strip()

        if candidate:
            intro = candidate
            break

    return bool(
        re.search(
            r"(?iu)(?:"
            r"(?:проверь(?:те)?|проверить|убедись|убедитесь)"
            r"\s*,?\s*что|"
            r"(?:verify|check|ensure)\s+that"
            r")\s*:?\s*$",
            intro,
        )
    )


def _workflow_case_title(request):
    for line in str(request or "").splitlines():
        title = line.strip()

        if not title or re.match(r"^\s*\d+\s*[.)]\s+", title):
            continue

        return title.rstrip(".")[:500]

    return "Последовательный regression workflow"


def _request_declares_single_workflow(request):
    value = re.sub(
        r"\s+",
        " ",
        str(request or "").strip().lower(),
    )

    patterns = (
        r"\bод(?:ин|на|но)\s+(?:[\w-]+\s+){0,3}"
        r"(?:сценари\w*|workflow|воркфлоу|операци\w+|"
        r"жизненн\w+\s+цикл\w*)\b",
        r"\bone\s+(?:[\w-]+\s+){0,3}"
        r"(?:scenario|workflow|operation|lifecycle)\b",
        r"\bодн(?:ом|ого)\s+(?:test\s*case|тестов\w+\s+кейс\w*)\b",
        r"\bод(?:ин|на|но)\s+(?:[\w-]+\s+){0,3}"
        r"(?:test\s*case|тестов\w+\s+кейс\w*|кейс\w*)\b",
        r"\b(?:one|single)\s+test\s*case\b",
        r"\bодн(?:ого|ому|им)\s+и\s+тому\s+же\s+"
        r"(?:объект\w*|ресурс\w*|сущност\w*)\b",
        r"\bsame\s+(?:created\s+)?"
        r"(?:object|resource|entity)\b",
    )

    return any(
        re.search(pattern, value, re.IGNORECASE)
        for pattern in patterns
    )


def _coalesce_declared_single_workflow(request, plan):
    """Repair an LLM plan that split an explicitly single workflow."""
    if (
        not isinstance(plan, list)
        or len(plan) <= 1
        or not _request_declares_single_workflow(request)
    ):
        return plan

    raw_checks = []

    for spec in plan:
        if not isinstance(spec, dict):
            continue

        nested = _normalize_planned_checks(
            spec.get("checks")
        )

        if nested:
            raw_checks.extend(nested)
            continue

        title = str(
            spec.get("title")
            or spec.get("task")
            or ""
        ).strip()

        if not title:
            continue

        raw_checks.append(
            {
                "title": title,
                "expected": spec.get("expected"),
            }
        )

    checks = _normalize_planned_checks(raw_checks)

    return [
        {
            "title": _workflow_case_title(request),
            "task": str(request or "").strip(),
            "expected": None,
            "checks": checks,
        }
    ]


def _lock_regression_plan_stand(plan, current_stand):
    """Keep planner-generated URLs on the Core-resolved stand origin."""
    from copy import deepcopy
    from urllib.parse import urlsplit, urlunsplit

    if not isinstance(plan, list) or not current_stand:
        return plan

    stand_info = get_stand(current_stand) or {}
    canonical_url = str(
        stand_info.get("web_url") or ""
    ).strip().rstrip("/")

    if not canonical_url:
        return plan

    canonical = urlsplit(canonical_url)

    if not canonical.scheme or not canonical.hostname:
        return plan

    def lock_text(value):
        if value is None:
            return None

        def replace(match):
            raw = match.group(0)
            candidate_text = raw.rstrip(".,;:!?)】]}")
            suffix = raw[len(candidate_text):].replace(":", "")
            candidate = urlsplit(candidate_text)

            if candidate.hostname != canonical.hostname:
                return raw

            locked = urlunsplit((
                canonical.scheme,
                canonical.netloc,
                candidate.path,
                candidate.query,
                candidate.fragment,
            ))
            return locked.rstrip("/") + suffix

        return re.sub(
            r"https?://[^\s<>\"']+",
            replace,
            str(value),
            flags=re.IGNORECASE,
        )

    locked_plan = deepcopy(plan)

    for spec in locked_plan:
        if not isinstance(spec, dict):
            continue

        for key in ("title", "task", "expected"):
            spec[key] = lock_text(spec.get(key))

        for check in spec.get("checks") or []:
            if not isinstance(check, dict):
                continue

            for key in ("title", "expected"):
                check[key] = lock_text(check.get(key))

    return locked_plan


def extract_explicit_regression_cases(
    request: str,
):
    """
    Если пользователь сам дал нумерованный список:
      1. ...
      2. ...
      3. ...

    Core считает этот список authoritative scope.
    Нумерация под "проверь, что" является списком checks одного
    последовательного workflow, а не списком независимых cases.
    LLM Planner в этом случае вообще не вызывается.
    """
    items = []
    lines = str(request or "").splitlines()
    first_item_index = None

    for line_index, line in enumerate(lines):
        match = re.match(
            r"^\s*\d+\s*[.)]\s*(.+?)\s*$",
            line,
        )

        if not match:
            continue

        text = match.group(1).strip()

        if not text:
            continue

        if first_item_index is None:
            first_item_index = line_index

        expected = None

        expected_match = re.match(
            r"(?i)^\s*"
            r"(?:проверь|проверить)"
            r"\s*,?\s*что\s+(.+?)\s*[.]?\s*$",
            text,
        )

        if expected_match:
            expected = (
                expected_match.group(1)
                .strip()
                .rstrip(".")
            )

        title = re.sub(
            r"(?i)^\s*"
            r"(?:проверь|проверить)"
            r"\s*,?\s*что\s+",
            "",
            text,
        ).strip().rstrip(".")

        items.append(
            {
                "title": title[:500],
                "task": text,
                "expected": expected,
                "checks": [],
            }
        )

        if len(items) >= MAX_REGRESSION_CASES:
            break

    if (
        items
        and first_item_index is not None
        and _numbered_items_are_workflow_checks(
            lines,
            first_item_index,
        )
    ):
        checks = _normalize_planned_checks(
            [
                {
                    "title": item["title"],
                    "expected": (
                        item.get("expected")
                        or item["title"]
                    ),
                }
                for item in items
            ]
        )

        return [
            {
                "title": _workflow_case_title(request),
                "task": str(request or "").strip(),
                "expected": None,
                "checks": checks,
            }
        ]

    return items


def plan_regression_cases(
    request: str,
):
    explicit = extract_explicit_regression_cases(
        request
    )

    if explicit:
        return _coalesce_declared_single_workflow(
            request,
            explicit,
        )
    planner_messages = [
        {
            "role": "system",
            "content": REGRESSION_PLANNER_PROMPT,
        },
        {
            "role": "user",
            "content": str(request),
        },
    ]

    data = ask_ollama(
        planner_messages,
        tools=[],
    )

    message = data.get(
        "message"
    ) or {}

    if message.get("tool_calls"):
        raise ValueError(
            "regression planner attempted tool call"
        )

    plan = _parse_regression_plan(
        message.get("content")
        or ""
    )

    return _coalesce_declared_single_workflow(
        request,
        plan,
    )


def _regression_shared_context(text: str):
    """
    Общий контекст Regression Job без явно перечисленных
    test cases. Сохраняем стенд, вводную часть и ограничения,
    но соседние пункты 1./2./3. в case context не попадают.
    """
    result = []

    for line in str(text or "").splitlines():
        if re.match(
            r"^\s*\d+\s*[.)]\s+",
            line,
        ):
            continue

        result.append(line)

    return "\n".join(result).strip()


def _build_regression_case_prompt(
    original_request: str,
    safe_request: str,
    job_id: str,
    case_id: str,
    index: int,
    total: int,
    case_spec: dict,
):
    expected = (
        case_spec.get("expected")
        or "Не задан явно."
    )

    shared_context = _regression_shared_context(
        safe_request
    )

    planned_checks = _normalize_planned_checks(
        case_spec.get("checks")
    )

    if planned_checks:
        checks_block = (
            "Плановые проверки внутри текущего test case:\n"
            + json.dumps(
                planned_checks,
                ensure_ascii=False,
                indent=2,
            )
            + "\nКаждую плановую проверку отрази отдельной записью "
            "в UQA_CHECKS_JSON, дословно скопируй её check_id и "
            "подкрепи фактическим evidence. Не добавляй и не пропускай "
            "checks. Ledger/cleanup checks вычисляет UQA Core по "
            "persistent state; не подменяй их browser evidence.\n\n"
        )
    else:
        checks_block = ""

    requirement = case_spec.get(
        "requirement"
    )

    if requirement:
        requirement_block = (
            "[UQA CORE: LOCKED REQUIREMENT]\n"
            + json.dumps(
                requirement,
                ensure_ascii=False,
            )
            + "\n"
            "[/UQA CORE: LOCKED REQUIREMENT]\n\n"
        )
    else:
        requirement_block = (
            "[UQA CORE: LOCKED REQUIREMENT]\n"
            "null\n"
            "[/UQA CORE: LOCKED REQUIREMENT]\n\n"
        )

    return (
        "[UQA CORE: REGRESSION CASE]\n"
        f"job_id: {job_id}\n"
        f"case_id: {case_id}\n"
        f"case_number: {index}/{total}\n\n"
        "Выполни ТОЛЬКО текущий test case. "
        "Не выполняй и не оценивай соседние cases.\n"
        "В UQA_CHECKS_JSON включай проверки ТОЛЬКО "
        "текущего test case.\n"
        "До первого WRITE выполни navigation preflight: открой точный раздел "
        "целевого ресурса через OBSERVE/INTERACT. Не выбирай Add/Create для "
        "другого типа сущности; если точный маршрут неясен, сначала используй "
        "knowledge_search.\n"
        "Режим действий UQA Core: MANAGED_ACTIONS. "
        "Выполняй необходимые действия для текущего test case. "
        "UQA Core самостоятельно классифицирует tool-вызовы. "
        "Некоторые изменяющие или разрушительные действия могут "
        "потребовать подтверждения пользователя. "
        "Если Core заблокировал действие — не пытайся обходить "
        "ограничение другим способом. "
        "Учитывай явно заданные пользователем ограничения "
        "на изменение данных. "
        "Каждый фактически созданный test resource сразу регистрируй "
        "через resource_register; ledger не является evidence.\n\n"
        f"Название: {case_spec['title']}\n"
        f"Задача: {case_spec['task']}\n"
        f"Ожидаемый результат: {expected}\n\n"
        f"{checks_block}"
        f"{requirement_block}"
        "Locked requirement задан UQA Core до выполнения "
        "test case. Не изменяй его subject, field, operator "
        "или expected по результатам runtime evidence.\n\n"
        "Общий контекст regression job "
        "(соседние test cases удалены Core):\n"
        f"{shared_context}\n\n"
        "Сформируй обычный QA-результат и обязательный "
        "UQA_CHECKS_JSON по правилам system prompt."
    )


def _regression_summary(job: dict):
    cases = job.get(
        "test_cases",
        []
    )

    counts = {
        "passed": 0,
        "failed": 0,
        "blocked": 0,
        "skipped": 0,
        "running": 0,
        "pending": 0,
    }

    for case in cases:
        status = str(
            case.get("status")
            or "pending"
        ).lower()

        counts[status] = (
            counts.get(status, 0)
            + 1
        )

    return (
        f"Regression: {len(cases)} case(s) | "
        f"PASS={counts.get('passed', 0)} | "
        f"FAIL={counts.get('failed', 0)} | "
        f"BLOCKED={counts.get('blocked', 0)} | "
        f"SKIPPED={counts.get('skipped', 0)}"
    )


def _normalize_regression_mode(value: str):
    value = sanitize_terminal_input(
        value
    ).strip().lower()

    if value in (
        "",
        "s",
        "step",
    ):
        return "step"

    if value in (
        "a",
        "auto",
    ):
        return "auto"

    return None


def _normalize_regression_step_action(value: str):
    value = sanitize_terminal_input(
        value
    ).strip().lower()

    if value in (
        "",
        "n",
        "next",
    ):
        return "next"

    if value in (
        "a",
        "auto",
    ):
        return "auto"

    if value in (
        "q",
        "quit",
        "stop",
    ):
        return "stop"

    return None


def _ask_regression_execution_mode():
    while True:
        try:
            console.print(
                "\n[bold cyan]Режим регресса[/bold cyan]"
            )
            console.print(
                "[Enter/S] STEP — подтверждать каждый case"
            )
            console.print(
                "[A] AUTO — выполнить все cases автоматически"
            )

            raw = read_user_input()
        except (EOFError, KeyboardInterrupt):
            console.print()
            return "step"

        mode = _normalize_regression_mode(
            raw
        )

        if mode:
            return mode

        console.print(
            "[yellow]"
            "Введите S/Enter для STEP "
            "или A для AUTO."
            "[/yellow]"
        )


def _ask_regression_step_action():
    while True:
        try:
            console.print(
                "\n[bold cyan]"
                "[Enter] следующий case   "
                "[A] AUTO до конца   "
                "[Q] остановить regression"
                "[/bold cyan]"
            )

            raw = read_user_input()
        except (EOFError, KeyboardInterrupt):
            console.print()
            return "stop"

        action = (
            _normalize_regression_step_action(
                raw
            )
        )

        if action:
            return action

        console.print(
            "[yellow]"
            "Enter = следующий, "
            "A = AUTO, "
            "Q = остановить."
            "[/yellow]"
        )


def _regression_artifact_user_root():
    import os
    from pathlib import Path

    username = (
        os.getenv("UQA_USER")
        or os.getenv("USER")
        or "unknown"
    )

    safe_username = "".join(
        ch if ch.isalnum() or ch in "._-"
        else "_"
        for ch in username
    )

    return (
        Path("/opt/uqa/artifacts/browser")
        / safe_username
    ).resolve()


def _collect_case_artifacts(value):
    """
    Recursively collect real artifact files referenced
    anywhere inside stored case/check/evidence structures.
    """
    from pathlib import Path

    user_root = (
        _regression_artifact_user_root()
    )

    found = []

    def walk(obj):
        if isinstance(obj, dict):
            for item in obj.values():
                walk(item)

        elif isinstance(obj, (list, tuple)):
            for item in obj:
                walk(item)

        elif isinstance(obj, str):
            if not obj.startswith(
                "/opt/uqa/artifacts/browser/"
            ):
                return

            try:
                path = Path(obj).resolve()

                if (
                    path.is_relative_to(user_root)
                    and path.is_file()
                ):
                    if path not in found:
                        found.append(path)

            except Exception:
                pass

    walk(value)

    return found


def _write_private_text(path, text):
    import os

    path.write_text(
        text,
        encoding="utf-8",
    )

    os.chmod(
        path,
        0o600,
    )


def _write_private_json(path, value):
    import json
    import os

    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    os.chmod(
        path,
        0o600,
    )


def export_regression_case_artifacts(
    job_id,
    case_id,
    index,
):
    import json
    import os
    import zipfile

    job = get_job(job_id)

    if not job:
        return None

    case = next(
        (
            item
            for item in job.get(
                "test_cases",
                [],
            )
            if item.get("case_id") == case_id
        ),
        None,
    )

    if not case:
        return None

    user_root = (
        _regression_artifact_user_root()
    )

    report_root = (
        user_root
        / "reports"
        / job_id
        / (
            f"case-{index:03d}-"
            f"{case_id}"
        )
    )

    report_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    os.chmod(
        report_root,
        0o700,
    )

    checks = case.get("checks") or []

    lines = [
        f"# UQA Test Case {index}",
        "",
        f"- Job: `{job_id}`",
        f"- Case: `{case_id}`",
        f"- Status: **{str(case.get('status')).upper()}**",
        f"- Title: {case.get('title') or ''}",
        "",
        "## Result",
        "",
        case.get("result") or "No textual result.",
        "",
        "## Checks",
        "",
    ]

    if checks:
        for check_index, check in enumerate(
            checks,
            1,
        ):
            lines.extend(
                [
                    f"### Check {check_index}",
                    "",
                    f"- Title: {check.get('title') or ''}",
                    f"- Status: **{str(check.get('status')).upper()}**",
                    f"- Expected: {check.get('expected')}",
                    f"- Actual: {check.get('actual')}",
                    f"- Reason: {check.get('reason')}",
                    "",
                ]
            )
    else:
        lines.extend(
            [
                "No structured checks stored.",
                "",
            ]
        )

    evidence = _collect_case_artifacts(
        case
    )

    lines.extend(
        [
            "## Evidence",
            "",
        ]
    )

    if evidence:
        for item in evidence:
            lines.append(
                f"- `{item.name}`"
            )
    else:
        lines.append(
            "No file evidence."
        )

    lines.append("")

    md_path = (
        report_root
        / "result.md"
    )

    json_path = (
        report_root
        / "result.json"
    )

    zip_path = (
        report_root
        / f"case-{index:03d}.zip"
    )

    _write_private_text(
        md_path,
        "\n".join(lines),
    )

    _write_private_json(
        json_path,
        case,
    )

    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:

        archive.write(
            md_path,
            "result.md",
        )

        archive.write(
            json_path,
            "result.json",
        )

        for evidence_index, item in enumerate(
            evidence,
            1,
        ):
            archive.write(
                item,
                (
                    "evidence/"
                    f"{evidence_index:03d}-"
                    f"{item.name}"
                ),
            )

    os.chmod(
        zip_path,
        0o600,
    )

    return {
        "report_path": str(md_path),
        "json_path": str(json_path),
        "zip_path": str(zip_path),
        "report_url": artifact_public_url(
            md_path
        ),
        "zip_url": artifact_public_url(
            zip_path,
            download=True,
        ),
    }


def export_regression_job_artifacts(
    job_id,
):
    import json
    import os
    import zipfile

    job = get_job(job_id)

    if not job:
        return None

    user_root = (
        _regression_artifact_user_root()
    )

    report_root = (
        user_root
        / "reports"
        / job_id
    )

    report_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    os.chmod(
        report_root,
        0o700,
    )

    cases = (
        job.get("test_cases")
        or []
    )

    lines = [
        "# UQA Regression Report",
        "",
        f"- Job: `{job_id}`",
        f"- Status: **{str(job.get('status')).upper()}**",
        f"- Stand: `{job.get('stand')}`",
        f"- Summary: {job.get('summary') or ''}",
        "",
        "## Test Cases",
        "",
    ]

    for index, case in enumerate(
        cases,
        1,
    ):
        lines.extend(
            [
                (
                    f"### {index}. "
                    f"{case.get('title') or case.get('case_id')}"
                ),
                "",
                f"- Case: `{case.get('case_id')}`",
                f"- Status: **{str(case.get('status')).upper()}**",
                "",
            ]
        )

        for check in (
            case.get("checks")
            or []
        ):
            lines.extend(
                [
                    f"- Check: {check.get('title')}",
                    f"  - Status: {str(check.get('status')).upper()}",
                    f"  - Expected: {check.get('expected')}",
                    f"  - Actual: {check.get('actual')}",
                    f"  - Reason: {check.get('reason')}",
                ]
            )

        lines.append("")

    resources = job.get("resources") or []
    lines.extend(
        [
            "## Test Resources",
            "",
            f"Cleanup status: **{str(job.get('cleanup_status') or 'not_required').upper()}**",
            "",
        ]
    )

    if resources:
        for resource in resources:
            lines.append(
                "- "
                f"`{resource.get('resource_id')}` "
                f"type=`{resource.get('type')}` "
                f"name=`{resource.get('name') or resource.get('external_id')}` "
                f"status=**{str(resource.get('status') or 'active').upper()}**"
            )
    else:
        lines.append("No test resources.")

    lines.append("")

    evidence = _collect_case_artifacts(
        cases
    )

    lines.extend(
        [
            "## Evidence",
            "",
        ]
    )

    if evidence:
        for item in evidence:
            lines.append(
                f"- `{item.name}`"
            )
    else:
        lines.append(
            "No file evidence."
        )

    lines.append("")

    md_path = (
        report_root
        / "regression-report.md"
    )

    json_path = (
        report_root
        / "regression-result.json"
    )

    zip_path = (
        report_root
        / "regression-evidence.zip"
    )

    _write_private_text(
        md_path,
        "\n".join(lines),
    )

    _write_private_json(
        json_path,
        job,
    )

    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:

        archive.write(
            md_path,
            "regression-report.md",
        )

        archive.write(
            json_path,
            "regression-result.json",
        )

        for evidence_index, item in enumerate(
            evidence,
            1,
        ):
            archive.write(
                item,
                (
                    "evidence/"
                    f"{evidence_index:03d}-"
                    f"{item.name}"
                ),
            )

    os.chmod(
        zip_path,
        0o600,
    )

    return {
        "report_path": str(md_path),
        "json_path": str(json_path),
        "zip_path": str(zip_path),
        "report_url": artifact_public_url(
            md_path
        ),
        "zip_url": artifact_public_url(
            zip_path,
            download=True,
        ),
    }


def _print_case_artifact_links(
    artifacts,
):
    if not artifacts:
        return

    report_url = artifacts.get(
        "report_url"
    )

    zip_url = artifacts.get(
        "zip_url"
    )

    console.print()

    if report_url:
        console.print(
            "[cyan]Case report:[/cyan] "
            f"{report_url}"
        )

    if zip_url:
        console.print(
            "[cyan]Download case:[/cyan] "
            f"{zip_url}"
        )


def _clean_requirement_subject(
    value,
):
    subject = str(
        value or ""
    ).strip()

    subject = subject.strip(
        ' "\'«»'
    )

    subject = re.sub(
        r"(?i)^(?:"
        r"кнопка|поле|вкладка|"
        r"button|field|tab"
        r")\s+",
        "",
        subject,
    ).strip()

    return subject


def compile_locked_ui_requirement(
    spec,
):
    """
    Deterministically compile only simple and unambiguous
    semantic UI requirements.

    Anything contextual/ambiguous remains text-only.
    No LLM is involved.
    """
    if not isinstance(
        spec,
        dict,
    ):
        return None

    candidates = [
        spec.get("expected"),
        spec.get("title"),
        spec.get("task"),
    ]

    state_pattern = (
        r"(?P<subject>.+?)"
        r"\s+"
        r"(?:(?:должен|должна|должно)"
        r"\s+быть\s+)?"
        r"(?P<state>"
        r"не\s+отображается|"
        r"не\s+видима|"
        r"не\s+видим|"
        r"не\s+видимо|"
        r"скрыта|"
        r"скрыт|"
        r"скрыто|"
        r"hidden|"
        r"не\s+редактируема|"
        r"не\s+редактируемо|"
        r"только\s+для\s+чтения|"
        r"read[- ]?only|"
        r"недоступна|"
        r"недоступен|"
        r"недоступно|"
        r"неактивна|"
        r"неактивен|"
        r"неактивно|"
        r"disabled|"
        r"доступна|"
        r"доступен|"
        r"доступно|"
        r"enabled|"
        r"отображается|"
        r"видима|"
        r"видим|"
        r"visible|"
        r"редактируема|"
        r"редактируемо|"
        r"editable"
        r")"
        r"\s*[.]?\s*$"
    )

    for candidate in candidates:
        if not candidate:
            continue

        text = str(
            candidate
        ).strip()

        text = re.sub(
            r"(?i)^\s*"
            r"(?:проверь|проверить)"
            r"\s*,?\s*что\s+",
            "",
            text,
        ).strip()

        match = re.match(
            state_pattern,
            text,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        subject = (
            _clean_requirement_subject(
                match.group(
                    "subject"
                )
            )
        )

        if not subject:
            continue

        # Contextual requirements need explicit precondition
        # modelling. Do not silently reduce them to one bool.
        if re.search(
            r"(?i)\b(?:"
            r"без|после|до|при|"
            r"если|когда|перед"
            r")\b",
            subject,
        ):
            continue

        if len(subject) > 160:
            continue

        state = " ".join(
            match.group("state")
            .strip()
            .casefold()
            .split()
        )

        if state in {
            "недоступна",
            "недоступен",
            "недоступно",
            "неактивна",
            "неактивен",
            "неактивно",
            "disabled",
        }:
            assertion = {
                "field": "disabled",
                "operator": "eq",
                "expected": True,
            }

        elif state in {
            "доступна",
            "доступен",
            "доступно",
            "enabled",
        }:
            assertion = {
                "field": "enabled",
                "operator": "eq",
                "expected": True,
            }

        elif state in {
            "не отображается",
            "не видима",
            "не видим",
            "не видимо",
            "скрыта",
            "скрыт",
            "скрыто",
            "hidden",
        }:
            assertion = {
                "field": "visible",
                "operator": "eq",
                "expected": False,
            }

        elif state in {
            "отображается",
            "видима",
            "видим",
            "visible",
        }:
            assertion = {
                "field": "visible",
                "operator": "eq",
                "expected": True,
            }

        elif state in {
            "редактируема",
            "редактируемо",
            "editable",
        }:
            assertion = {
                "field": "editable",
                "operator": "eq",
                "expected": True,
            }

        elif state in {
            "не редактируема",
            "не редактируемо",
            "только для чтения",
            "read-only",
            "read only",
        }:
            assertion = {
                "field": "editable",
                "operator": "eq",
                "expected": False,
            }

        else:
            continue

        return {
            "type": "ui_semantic",
            "version": 1,
            "compiler": (
                "core_deterministic_v1"
            ),
            "locked": True,
            "subject": subject,
            "assertions": [
                assertion
            ],
        }

    return None


def prepare_locked_requirements(
    plan,
):
    if not isinstance(
        plan,
        list,
    ):
        return plan

    for spec in plan:
        if not isinstance(
            spec,
            dict,
        ):
            continue

        spec["requirement"] = (
            compile_locked_ui_requirement(
                spec
            )
        )

    return plan


def _print_proposed_regression_plan(plan):
    prepare_locked_requirements(
        plan
    )

    console.print()
    console.print(
        "[bold cyan]Proposed regression plan[/bold cyan]"
    )

    for index, spec in enumerate(
        plan,
        1,
    ):
        title = (
            spec.get("title")
            or f"Case {index}"
        )

        task = (
            spec.get("task")
            or title
        )

        expected = spec.get(
            "expected"
        )

        console.print(
            f"{index}. {title}"
        )

        if task != title:
            console.print(
                f"   [dim]Task: {task}[/dim]"
            )

        if expected is not None:
            console.print(
                f"   [dim]Expected: "
                f"{expected}[/dim]"
            )

        planned_checks = _normalize_planned_checks(
            spec.get("checks")
        )

        if planned_checks:
            console.print(
                f"   [dim]Checks: "
                f"{len(planned_checks)}[/dim]"
            )

            for check_index, check in enumerate(
                planned_checks,
                1,
            ):
                console.print(
                    f"      [dim]{check_index}. "
                    f"{check['title']}[/dim]"
                )

        requirement = spec.get(
            "requirement"
        )

        if requirement:
            assertion = (
                requirement[
                    "assertions"
                ][0]
            )

            console.print(
                "   [dim]"
                "Core requirement: "
                f"{requirement['subject']}."
                f"{assertion['field']} "
                f"{assertion['operator']} "
                f"{json.dumps(assertion['expected'])}"
                "[/dim]"
            )

        else:
            console.print(
                "   [dim]"
                "Core requirement: "
                "text-only, not machine-locked"
                "[/dim]"
            )

    console.print()


def _ask_regression_plan_action():
    while True:
        console.print(
            "[Y/Enter] принять план   "
            "[R] уточнить и перепланировать   "
            "[Q] отменить regression"
        )

        raw = read_user_input()

        value = str(
            raw or ""
        ).strip().lower()

        if value in (
            "",
            "y",
            "yes",
            "д",
            "да",
        ):
            return "accept"

        if value in (
            "r",
            "revise",
            "edit",
            "у",
            "уточнить",
        ):
            return "revise"

        if value in (
            "q",
            "quit",
            "cancel",
            "отмена",
        ):
            return "cancel"

        console.print(
            "[yellow]"
            "Введите Y/Enter, R или Q."
            "[/yellow]"
        )


def _ask_regression_plan_refinement():
    while True:
        console.print()
        console.print(
            "[cyan]"
            "Введите уточнение к regression scope:"
            "[/cyan]"
        )

        value = str(
            read_user_input()
            or ""
        ).strip()

        if value:
            return value

        console.print(
            "[yellow]"
            "Уточнение не должно быть пустым."
            "[/yellow]"
        )


CLEANUP_RESULT_START = "[UQA_CLEANUP_JSON]"
CLEANUP_RESULT_END = "[/UQA_CLEANUP_JSON]"

CLEANUP_SYSTEM_PROMPT = """
Ты UQA Cleanup Worker.

Твоя единственная задача — безопасно очистить ОДИН test resource,
который передал UQA Core.

Правила:
- Работай только с указанным ресурсом и указанным стендом.
- Сначала однозначно найди ресурс по type, name, external_id и metadata.
- Если текущая страница не содержит ресурс, используй только переданные Core
  URL и фактически наблюдавшийся navigation trace до первой мутации.
- Navigation trace нужен только для перехода к списку. Не повторяй Create/Add,
  заполнение формы или другие действия исходного теста.
- Не угадывай URL, идентификатор или соседний объект.
- Не трогай другие объекты, даже если они похожи по имени.
- Используй browser tools для фактической проверки и удаления.
- Любые WRITE/DESTRUCTIVE действия контролирует UQA Core.
- Если Core заблокировал действие, не обходи policy другим способом.
- После удаления или архивирования сначала вызови browser_inspect_table_row
  с точным именем ресурса и exact=true. Для табличного ресурса подтверди
  table_row_not_found в активном списке. Если ресурс не представлен строкой
  таблицы, используй browser_inspect_semantic с точным именем/идентификатором
  и подтверди semantic_element_not_found.
- Если Core передал core_observed_rest_cleanup, разрешён универсальный
  browser_delete_json_resource/browser_archive_json_resource только с этими
  точными аргументами. Его
  повторный GET с post_delete_match_count=0 является runtime-проверкой cleanup.
- Если Core сообщил, что exact resource row selected, следующим изменяющим
  действием должен быть только Delete/Remove этого выбранного ресурса.
- Если Core сообщил, что открыл context menu точной строки, используй только
  действия из этого меню; Edit допустим лишь для открытия формы этого ресурса.
- Tool result о клике подтверждает только клик, а не успешный cleanup.
- Если ресурс невозможно однозначно найти или проверить, верни pending.
- Не используй и не сохраняй пароли, токены, cookies или другие секреты.
- Если видна Login/Password форма и Core разрешил saved credentials,
  используй browser_authenticate_saved_stand; пароль никогда не передавай.
- Не выполняй cleanup через SSH-команды или прямое изменение БД.

Когда закончишь, верни короткое объяснение и обязательный блок:
[UQA_CLEANUP_JSON]
{"status":"cleaned|pending|failed","reason":"краткая причина"}
[/UQA_CLEANUP_JSON]

Используй cleaned только после реально выполненного удаления и
последующей runtime-проверки. Никакого UQA_CHECKS_JSON здесь не нужно.
"""


def _cleanup_tools():
    blocked_names = {
        "resource_register",
        "resource_update",
        "resource_list",
        "table_selection_list",
        "stage_test_artifact",
        "browser_upload_staged_artifact_semantic",
        # Core opens an exact row menu once. Exposing this toggle to the
        # worker could immediately close the already-open menu.
        "browser_context_menu_semantic",
    }

    regular_tools = [
        item
        for item in TOOLS
        if item.get("function", {}).get("name")
        not in blocked_names
    ]

    return [
        *regular_tools,
        *CLEANUP_ONLY_TOOLS,
    ]


def order_cleanup_resources(resources):
    resources = [
        dict(resource)
        for resource in resources
        if isinstance(resource, dict)
        and resource.get("resource_id")
    ]

    resources.sort(
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("resource_id") or ""),
        )
    )

    by_id = {
        resource["resource_id"]: resource
        for resource in resources
    }
    visiting = set()
    visited = set()
    dependency_first = []

    def visit(resource_id):
        if resource_id in visited:
            return

        if resource_id in visiting:
            raise ValueError(
                "cleanup_dependency_cycle"
            )

        visiting.add(resource_id)
        resource = by_id[resource_id]

        for dependency_id in resource.get(
            "depends_on",
            [],
        ):
            if dependency_id in by_id:
                visit(dependency_id)

        visiting.remove(resource_id)
        visited.add(resource_id)
        dependency_first.append(resource)

    for resource in resources:
        visit(resource["resource_id"])

    return list(
        reversed(dependency_first)
    )


def _parse_cleanup_result(content):
    text = str(content or "")
    start = text.rfind(CLEANUP_RESULT_START)
    end = text.rfind(CLEANUP_RESULT_END)

    if start < 0 or end < start:
        return None, "cleanup_result_missing"

    payload_text = text[
        start + len(CLEANUP_RESULT_START):end
    ].strip()

    try:
        payload = json.loads(payload_text)
    except Exception as exc:
        return None, (
            "cleanup_result_invalid_json: "
            f"{type(exc).__name__}"
        )

    if not isinstance(payload, dict):
        return None, "cleanup_result_not_object"

    status = str(
        payload.get("status")
        or ""
    ).strip().lower()

    if status not in {
        "cleaned",
        "pending",
        "failed",
    }:
        return None, (
            "cleanup_result_invalid_status: "
            f"{status}"
        )

    return {
        "status": status,
        "reason": str(
            payload.get("reason")
            or ""
        ).strip()[:1500],
    }, None


def _cleanup_tool_succeeded(result):
    if not isinstance(result, dict):
        return False

    if result.get("error"):
        return False

    if result.get("executed") is False:
        return False

    if str(
        result.get("status")
        or ""
    ).strip().lower() in {
        "blocked_by_policy",
        "error",
        "failed",
        "failure",
        "not_executed",
    }:
        return False

    if str(
        result.get("click_status")
        or ""
    ).strip().lower() in {
        "failed",
        "not_executed",
    }:
        return False

    return True


def _cleanup_history_has_confirmed_destructive(
    resource,
):
    for attempt in resource.get(
        "cleanup_attempts",
        [],
    ):
        for event in attempt.get(
            "events",
            [],
        ):
            data = event.get("data") or {}
            result = data.get("result") or {}

            if (
                result.get("action_class") == "destructive"
                and result.get("action_policy_status") == "confirmed"
                and result.get("mutation_executed") is True
                and result.get("executed") is not False
                and not result.get("error")
                and result.get("click_status")
                not in {"failed", "not_executed"}
                and result.get("status")
                not in {"error", "failed", "blocked_by_policy"}
            ):
                return True

    return False


def _cleanup_followup_confirmation_present(
    tool_name,
    arguments,
    result,
):
    if (
        tool_name != "browser_click_semantic"
        or not isinstance(arguments, dict)
        or not isinstance(result, dict)
    ):
        return False

    action_name = " ".join(
        str(arguments.get("name") or "").split()
    ).casefold()

    if not action_name:
        return False

    if int(
        result.get(
            "post_click_same_name_button_count"
        )
        or 0
    ) > 0:
        return True

    for item in result.get(
        "interactive_elements",
        [],
    ):
        if not isinstance(item, dict):
            continue

        role = str(
            item.get("role")
            or ""
        ).strip().casefold()
        label = " ".join(
            str(
                item.get("aria_label")
                or item.get("text")
                or ""
            ).split()
        ).casefold()

        if role == "button" and label == action_name:
            return True

    return False


def _annotate_cleanup_mutation_result(
    tool_name,
    arguments,
    result,
):
    if not isinstance(result, dict):
        return result

    if (
        result.get("action_class") != "destructive"
        or result.get("action_policy_status")
        != "confirmed"
        or result.get("executed") is False
        or result.get("error")
    ):
        return result

    if tool_name in {
        "browser_delete_json_resource",
        "browser_archive_json_resource",
    }:
        result.setdefault(
            "mutation_executed",
            result.get("already_satisfied") is not True,
        )
        return result

    confirmation_pending = (
        _cleanup_followup_confirmation_present(
            tool_name,
            arguments,
            result,
        )
    )
    result["confirmation_pending"] = (
        confirmation_pending
    )
    result["mutation_executed"] = (
        not confirmation_pending
    )
    return result


def _cleanup_browser_verification_succeeded(
    tool_name,
    result,
):
    if not isinstance(result, dict):
        return False

    if tool_name in {
        "browser_delete_json_resource",
        "browser_archive_json_resource",
    }:
        mutation_succeeded = (
            result.get("already_satisfied") is True
            or 200 <= int(
                result.get("mutation_status")
                or result.get("delete_status")
                or 0
            ) < 300
        )
        return (
            result.get("status") == "ok"
            and mutation_succeeded
            and 200 <= int(result.get("post_delete_status") or 0) < 300
            and (
                result.get("post_delete_verified") is True
                or (
                    "post_delete_verified" not in result
                    and result.get("post_delete_match_count") == 0
                )
            )
        )

    expected_not_found_errors = {
        "browser_inspect_semantic": (
            "semantic_element_not_found"
        ),
        "browser_inspect_table_row": (
            "table_row_not_found"
        ),
    }

    expected_error = expected_not_found_errors.get(
        tool_name
    )

    return bool(
        expected_error
        and result.get("error") == expected_error
    )


def _cleanup_can_reconcile_exact_absence(
    resource,
    tool_name,
    result,
):
    return (
        _cleanup_history_has_confirmed_destructive(
            resource
        )
        and _cleanup_browser_verification_succeeded(
            tool_name,
            result,
        )
    )


def _cleanup_resource_was_exact_table_row(
    job,
    resource,
):
    case_id = str(
        resource.get("created_by_case")
        or ""
    ).strip()
    exact_name = str(
        resource.get("name")
        or ""
    ).strip()

    if not case_id or not exact_name:
        return False

    for case in job.get("test_cases", []):
        if str(case.get("case_id") or "") != case_id:
            continue

        for observation in case.get(
            "observations",
            [],
        ):
            data = observation.get("data") or {}

            if (
                observation.get("type")
                == "ui_element"
                or observation.get("source")
                == "browser_semantic"
            ):
                if (
                    data.get("strategy")
                    == "table_row_exact_cell"
                    and data.get("exact") is True
                    and str(
                        data.get("subject")
                        or ""
                    ).strip() == exact_name
                    and data.get("visible") is True
                ):
                    return True

    return False


def _cleanup_inverse_action_visible(
    result,
    action_name,
):
    normalized_action = "".join(
        str(action_name or "")
        .strip()
        .casefold()
        .split()
    )

    if not normalized_action:
        return False

    expected_inverse = "un" + normalized_action

    for item in result.get(
        "interactive_elements",
        [],
    ):
        if not isinstance(item, dict):
            continue

        role = str(
            item.get("role")
            or ""
        ).strip().casefold()
        label = "".join(
            str(
                item.get("aria_label")
                or item.get("text")
                or ""
            )
            .strip()
            .casefold()
            .split()
        )

        if (
            role == "menuitem"
            and label == expected_inverse
        ):
            return True

    return False


def _cleanup_last_confirmed_action_name(
    resource,
):
    for attempt in reversed(
        resource.get("cleanup_attempts", [])
    ):
        for event in reversed(
            attempt.get("events", [])
        ):
            data = event.get("data") or {}
            result = data.get("result") or {}

            if (
                result.get("action_class")
                == "destructive"
                and result.get(
                    "action_policy_status"
                ) == "confirmed"
                and result.get(
                    "mutation_executed"
                ) is True
            ):
                return str(
                    (data.get("arguments") or {})
                    .get("name")
                    or ""
                ).strip()

    return ""


def _cleanup_event_summary(
    tool_name,
    arguments,
    result,
):
    arguments = (
        arguments
        if isinstance(arguments, dict)
        else {}
    )
    result = (
        result
        if isinstance(result, dict)
        else {}
    )

    safe_arguments = {}

    for key in (
        "name",
        "field",
        "exact",
        "role",
        "request_id",
        "stand",
        "container",
        "method",
        "endpoint_contains",
        "collection_endpoint",
        "exact_name",
    ):
        if key in arguments:
            safe_arguments[key] = arguments[key]

    result_summary = {}

    for key in (
        "status",
        "executed",
        "click_status",
        "action_class",
        "action_policy_status",
        "error",
        "reason",
        "semantic_name",
        "screenshot",
        "delete_status",
        "mutation_status",
        "mutation_method",
        "operation_suffix",
        "mutation_executed",
        "confirmation_pending",
        "post_click_same_name_button_count",
        "already_satisfied",
        "post_delete_status",
        "post_delete_match_count",
        "post_delete_archived_match_count",
        "post_delete_verified",
    ):
        if key in result:
            result_summary[key] = result[key]

    return {
        "tool": str(tool_name or ""),
        "arguments": safe_arguments,
        "result": result_summary,
    }


def _cleanup_navigation_context(job):
    request = str(job.get("request") or "")
    urls = []

    for value in re.findall(r"https?://[^\s<>\"']+", request):
        value = value.rstrip(".,;:!?)]}")

        if value and value not in urls:
            urls.append(value)

    trace = []
    stop = False

    for case in job.get("test_cases", []):
        for observation in case.get("observations", []):
            data = observation.get("data") or {}
            tool_name = str(data.get("tool") or "")
            arguments = data.get("input") or {}

            if tool_name == "browser_open_page":
                http_status = int(data.get("http_status") or 0)

                if 200 <= http_status < 400:
                    observed_open_url = str(
                        arguments.get("url")
                        or ""
                    ).strip()

                    if (
                        observed_open_url.startswith(("http://", "https://"))
                        and observed_open_url not in urls
                    ):
                        urls.append(observed_open_url)

            action_class = classify_tool_action(
                tool_name,
                arguments,
            )

            if action_class in {"write", "destructive"}:
                stop = True
                break

            if (
                tool_name
                not in {
                    "browser_click_semantic",
                    "browser_click_role",
                    "browser_click_text",
                }
            ):
                continue

            label = str(
                arguments.get("name")
                or arguments.get("text")
                or ""
            ).strip()

            if label:
                safe_arguments = {
                    key: arguments[key]
                    for key in ("name", "text", "exact", "role")
                    if key in arguments
                }
                step = {
                    "tool": tool_name,
                    "arguments": safe_arguments,
                }

                if step not in trace:
                    trace.append(step)

        if stop:
            break

    return {
        "urls": urls[:5],
        "observed_navigation_before_first_mutation": trace[:20],
    }


def _cleanup_observed_create_endpoint(job, resource):
    """Return one exact REST collection endpoint observed during creation."""
    created_by_case = str(resource.get("created_by_case") or "").strip()
    endpoints = []

    for case in job.get("test_cases", []):
        if created_by_case and case.get("case_id") != created_by_case:
            continue

        for observation in case.get("observations", []):
            data = observation.get("data") or {}
            tool_name = str(data.get("tool") or "")
            arguments = data.get("input") or {}

            if classify_tool_action(tool_name, arguments) != "write":
                continue

            for event in data.get("network_requests", []):
                if str(event.get("method") or "").upper() != "POST":
                    continue

                status = int(event.get("status") or 0)
                endpoint = str(event.get("url") or "").strip()

                if not (200 <= status < 300) or not endpoint.startswith("/"):
                    continue

                endpoint = endpoint.split("?", 1)[0].rstrip("/")
                if endpoint and endpoint not in endpoints:
                    endpoints.append(endpoint)

    return endpoints[0] if len(endpoints) == 1 else None


def _cleanup_exact_rest_target(job, resource):
    endpoint = _cleanup_observed_create_endpoint(job, resource)
    name = str(resource.get("name") or "").strip()
    cleanup_http = (
        (resource.get("metadata") or {}).get("cleanup_http")
        or {}
    )

    if not endpoint or not name or not isinstance(cleanup_http, dict):
        return None

    method = str(cleanup_http.get("method") or "").strip().upper()
    suffix = str(cleanup_http.get("suffix") or "").strip().casefold()
    arguments = {
        "collection_endpoint": endpoint,
        "exact_name": name,
    }

    if method == "POST" and suffix == "archive":
        return {
            "tool": "browser_archive_json_resource",
            "arguments": arguments,
        }

    if method == "DELETE" and not suffix:
        return {
            "tool": "browser_delete_json_resource",
            "arguments": arguments,
        }

    return None


def _build_cleanup_prompt(job, resource):
    safe_resource = {
        key: value
        for key, value in resource.items()
        if key != "cleanup_attempts"
    }

    stand_context = ""
    stand = job.get("stand")

    if stand:
        stand_context = (
            build_stand_context(stand)
            or ""
        )

    navigation_context = _cleanup_navigation_context(job)
    api_context = _cleanup_exact_rest_target(job, resource)

    if api_context:
        api_context = {
            **api_context,
            "source": (
                "observed successful create request plus "
                "resource cleanup_http metadata"
            ),
        }

    return (
        "[UQA CORE: CLEANUP RESOURCE]\n"
        f"job_id: {job.get('job_id')}\n"
        "resource:\n"
        + json.dumps(
            safe_resource,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
        + stand_context
        + "\ncore_navigation_context:\n"
        + json.dumps(
            navigation_context,
            ensure_ascii=False,
            indent=2,
        )
        + "\ncore_observed_rest_cleanup:\n"
        + json.dumps(
            api_context,
            ensure_ascii=False,
            indent=2,
        )
        + "\nОчисти только этот ресурс."
    )


def _cleanup_parent_expand_candidate(state, resource):
    parent = str(
        (resource.get("metadata") or {}).get("parent")
        or ""
    ).strip()

    if not parent or not isinstance(state, dict):
        return None

    parent_key = re.sub(r"\s+", " ", parent).casefold()
    matches = []

    for element in state.get("interactive_elements", []):
        row_text = str(
            ((element.get("table_context") or {}).get("row_text"))
            or ""
        ).strip()
        row_first_line = re.sub(
            r"\s+",
            " ",
            row_text.splitlines()[0] if row_text else "",
        ).casefold()

        if row_first_line != parent_key:
            continue

        labels = {
            str(element.get(key) or "").strip().casefold()
            for key in ("name", "aria_label", "label", "text")
        }
        icon_hints = {
            str(value or "").strip().casefold()
            for value in element.get("icon_hints", [])
        }
        is_expand = (
            "expand" in labels
            or "развернуть" in labels
            or "chevron-right" in icon_hints
            or "angle-right" in icon_hints
        )

        if (
            is_expand
            and element.get("enabled") is not False
            and element.get("element_id")
        ):
            matches.append(element["element_id"])

    return matches[0] if len(matches) == 1 else None


def _cleanup_row_checkbox_available(state, resource):
    resource_name = str(resource.get("name") or "").strip()

    if not resource_name or not isinstance(state, dict):
        return False

    wanted = re.sub(r"\s+", " ", resource_name).casefold()
    matches = 0

    for element in state.get("interactive_elements", []):
        row_text = str(
            ((element.get("table_context") or {}).get("row_text"))
            or ""
        )
        row_lines = {
            re.sub(r"\s+", " ", line.strip()).casefold()
            for line in row_text.splitlines()
            if line.strip()
        }
        role = str(element.get("role") or "").strip().casefold()
        element_type = str(element.get("type") or "").strip().casefold()

        if (
            wanted in row_lines
            and (role == "checkbox" or element_type == "checkbox")
            and element.get("enabled") is not False
        ):
            matches += 1

    return matches == 1


def run_cleanup_resource(
    job_id,
    resource,
):
    resource_id = resource["resource_id"]
    attempt = start_cleanup_attempt(
        job_id,
        resource_id,
    )
    attempt_id = attempt["attempt_id"]
    job = get_job(job_id)
    resource = (
        get_test_resource(
            job_id,
            resource_id,
        )
        or resource
    )
    messages = [
        {
            "role": "system",
            "content": CLEANUP_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": _build_cleanup_prompt(
                job,
                resource,
            ),
        },
    ]
    available_tools = _cleanup_tools()
    available_names = {
        item.get("function", {}).get("name")
        for item in available_tools
    }
    destructive_executed = (
        _cleanup_history_has_confirmed_destructive(
            resource
        )
    )
    browser_verified_after_destructive = False
    exact_rest_cleanup_target = _cleanup_exact_rest_target(
        job,
        resource,
    )

    try:
        try:
            from tools.browser import (
                reset_case_context,
            )

            reset_case_context()
        except Exception as exc:
            finish_cleanup_attempt(
                job_id,
                resource_id,
                attempt_id,
                outcome="failed",
                reason=(
                    "cleanup_browser_context_reset_failed: "
                    f"{type(exc).__name__}"
                ),
            )

            return {
                "status": "failed",
                "reason": (
                    "cleanup_browser_context_reset_failed"
                ),
            }

        navigation_context = _cleanup_navigation_context(job)
        navigation_calls = []
        navigation_urls = navigation_context.get("urls") or []

        if navigation_urls:
            navigation_calls.append((
                "browser_open_page",
                {"url": navigation_urls[0]},
            ))

        for step in navigation_context.get(
            "observed_navigation_before_first_mutation",
            [],
        ):
            navigation_calls.append((
                step.get("tool"),
                step.get("arguments") or {},
            ))

        for name, arguments in navigation_calls:
            action_class = classify_tool_action(name, arguments)

            if action_class not in {"observe", "interact"}:
                reason = "cleanup_navigation_trace_became_mutating"
                finish_cleanup_attempt(
                    job_id,
                    resource_id,
                    attempt_id,
                    outcome="pending",
                    reason=reason,
                )
                return {"status": "pending", "reason": reason}

            try:
                result = execute_tool_with_policy(
                    name,
                    arguments,
                    messages,
                    action_policy="confirm_mutations",
                )
            except Exception as exc:
                result = {
                    "error": "cleanup_navigation_replay_error",
                    "status": "error",
                    "executed": False,
                    "reason": type(exc).__name__,
                }

            add_cleanup_attempt_event(
                job_id,
                resource_id,
                attempt_id,
                _cleanup_event_summary(
                    name,
                    arguments,
                    result,
                ),
            )

            if not _cleanup_tool_succeeded(result):
                reason = "cleanup_navigation_replay_failed"
                finish_cleanup_attempt(
                    job_id,
                    resource_id,
                    attempt_id,
                    outcome="pending",
                    reason=reason,
                )
                return {"status": "pending", "reason": reason}

        if navigation_calls:
            messages.append({
                "role": "user",
                "content": (
                    "[UQA CORE: PRE-NAVIGATION COMPLETE]\n"
                    "Core replayed only the previously observed OBSERVE/INTERACT "
                    "route to the resource list. Do not click Create or Add. "
                    "Now locate only the exact registered resource and clean it."
                ),
            })

        if exact_rest_cleanup_target:
            target_tool = exact_rest_cleanup_target["tool"]
            target_arguments = exact_rest_cleanup_target["arguments"]
            result = execute_tool_with_policy(
                target_tool,
                target_arguments,
                messages,
                action_policy="confirm_mutations",
            )
            add_cleanup_attempt_event(
                job_id,
                resource_id,
                attempt_id,
                _cleanup_event_summary(
                    target_tool,
                    target_arguments,
                    result,
                ),
            )

            if result.get("status") == "blocked_by_policy":
                reason = "cleanup_action_not_approved"
                finish_cleanup_attempt(
                    job_id,
                    resource_id,
                    attempt_id,
                    outcome="pending",
                    reason=reason,
                )
                return {"status": "pending", "reason": reason}

            if (
                _cleanup_tool_succeeded(result)
                and result.get("action_class") == "destructive"
                and result.get("action_policy_status") == "confirmed"
                and _cleanup_browser_verification_succeeded(
                    target_tool,
                    result,
                )
            ):
                reason = "exact metadata-driven REST cleanup verified"
                finish_cleanup_attempt(
                    job_id,
                    resource_id,
                    attempt_id,
                    outcome="cleaned",
                    reason=reason,
                    result={
                        "status": "cleaned",
                        "reason": reason,
                    },
                )
                return {"status": "cleaned", "reason": reason}

            reason = (
                "cleanup_exact_rest_operation_failed: "
                + str(
                    result.get("error")
                    or result.get("status")
                    or "unknown"
                )
            )
            finish_cleanup_attempt(
                job_id,
                resource_id,
                attempt_id,
                outcome="pending",
                reason=reason,
                result=result,
            )
            return {"status": "pending", "reason": reason}

        parent_state = execute_tool_with_policy(
            "browser_get_state",
            {},
            messages,
            action_policy="confirm_mutations",
        )
        add_cleanup_attempt_event(
            job_id,
            resource_id,
            attempt_id,
            _cleanup_event_summary(
                "browser_get_state",
                {},
                parent_state,
            ),
        )
        expand_element_id = _cleanup_parent_expand_candidate(
            parent_state,
            resource,
        )

        if expand_element_id:
            expand_arguments = {
                "name": "Expand",
                "role": "button",
                "exact": True,
                "container": str(
                    (resource.get("metadata") or {}).get("parent")
                    or ""
                ).strip(),
            }
            expand_action_class = classify_tool_action(
                "browser_click_semantic",
                expand_arguments,
            )

            if expand_action_class != "interact":
                reason = "cleanup_parent_expand_became_mutating"
                finish_cleanup_attempt(
                    job_id,
                    resource_id,
                    attempt_id,
                    outcome="pending",
                    reason=reason,
                )
                return {"status": "pending", "reason": reason}

            expand_result = execute_tool_with_policy(
                "browser_click_semantic",
                expand_arguments,
                messages,
                action_policy="confirm_mutations",
            )
            add_cleanup_attempt_event(
                job_id,
                resource_id,
                attempt_id,
                _cleanup_event_summary(
                    "browser_click_semantic",
                    expand_arguments,
                    expand_result,
                ),
            )

            if not _cleanup_tool_succeeded(expand_result):
                reason = "cleanup_parent_expand_failed"
                finish_cleanup_attempt(
                    job_id,
                    resource_id,
                    attempt_id,
                    outcome="pending",
                    reason=reason,
                )
                return {"status": "pending", "reason": reason}

            messages.append({
                "role": "user",
                "content": (
                    "[UQA CORE: EXACT PARENT EXPANDED]\n"
                    "Core expanded the unique observed parent row from the "
                    "resource metadata. Locate only the exact child resource."
                ),
            })

        if (
            destructive_executed
            and _cleanup_resource_was_exact_table_row(
                job,
                resource,
            )
        ):
            recovery_arguments = {
                "name": str(
                    resource.get("name")
                    or ""
                ).strip(),
                "exact": True,
            }
            recovery_result = execute_tool_with_policy(
                "browser_inspect_table_row",
                recovery_arguments,
                messages,
                action_policy="confirm_mutations",
            )
            add_cleanup_attempt_event(
                job_id,
                resource_id,
                attempt_id,
                _cleanup_event_summary(
                    "browser_inspect_table_row",
                    recovery_arguments,
                    recovery_result,
                ),
            )

            if _cleanup_can_reconcile_exact_absence(
                resource,
                "browser_inspect_table_row",
                recovery_result,
            ):
                reason = (
                    "confirmed destructive cleanup verified "
                    "by exact table-row absence"
                )
                finish_cleanup_attempt(
                    job_id,
                    resource_id,
                    attempt_id,
                    outcome="cleaned",
                    reason=reason,
                    result={
                        "status": "cleaned",
                        "reason": reason,
                    },
                )
                return {
                    "status": "cleaned",
                    "reason": reason,
                }

            if _cleanup_tool_succeeded(
                recovery_result
            ):
                previous_action = (
                    _cleanup_last_confirmed_action_name(
                        resource
                    )
                )
                context_arguments = {
                    "name": str(
                        resource.get("name")
                        or ""
                    ).strip(),
                    "exact": True,
                }
                context_result = (
                    execute_tool_with_policy(
                        "browser_context_menu_semantic",
                        context_arguments,
                        messages,
                        action_policy=(
                            "confirm_mutations"
                        ),
                    )
                )
                add_cleanup_attempt_event(
                    job_id,
                    resource_id,
                    attempt_id,
                    _cleanup_event_summary(
                        "browser_context_menu_semantic",
                        context_arguments,
                        context_result,
                    ),
                )

                if _cleanup_inverse_action_visible(
                    context_result,
                    previous_action,
                ):
                    reason = (
                        "confirmed destructive cleanup "
                        "verified by inverse row action"
                    )
                    finish_cleanup_attempt(
                        job_id,
                        resource_id,
                        attempt_id,
                        outcome="cleaned",
                        reason=reason,
                        result={
                            "status": "cleaned",
                            "reason": reason,
                        },
                    )
                    return {
                        "status": "cleaned",
                        "reason": reason,
                    }

            reason = (
                "cleanup_post_destructive_table_row_"
                "still_present"
                if _cleanup_tool_succeeded(
                    recovery_result
                )
                else
                "cleanup_post_destructive_table_"
                "verification_failed"
            )
            finish_cleanup_attempt(
                job_id,
                resource_id,
                attempt_id,
                outcome="pending",
                reason=reason,
            )
            return {
                "status": "pending",
                "reason": reason,
            }

        row_state = execute_tool_with_policy(
            "browser_get_state",
            {},
            messages,
            action_policy="confirm_mutations",
        )
        add_cleanup_attempt_event(
            job_id,
            resource_id,
            attempt_id,
            _cleanup_event_summary(
                "browser_get_state",
                {},
                row_state,
            ),
        )

        if _cleanup_row_checkbox_available(row_state, resource):
            select_arguments = {
                "name": "",
                "role": "checkbox",
                "exact": True,
                "container": str(resource.get("name") or "").strip(),
            }

            if classify_tool_action(
                "browser_click_semantic",
                select_arguments,
            ) != "interact":
                reason = "cleanup_row_selection_became_mutating"
                finish_cleanup_attempt(
                    job_id,
                    resource_id,
                    attempt_id,
                    outcome="pending",
                    reason=reason,
                )
                return {"status": "pending", "reason": reason}

            select_result = execute_tool_with_policy(
                "browser_click_semantic",
                select_arguments,
                messages,
                action_policy="confirm_mutations",
            )
            add_cleanup_attempt_event(
                job_id,
                resource_id,
                attempt_id,
                _cleanup_event_summary(
                    "browser_click_semantic",
                    select_arguments,
                    select_result,
                ),
            )

            if not _cleanup_tool_succeeded(select_result):
                reason = "cleanup_exact_row_selection_failed"
                finish_cleanup_attempt(
                    job_id,
                    resource_id,
                    attempt_id,
                    outcome="pending",
                    reason=reason,
                )
                return {"status": "pending", "reason": reason}

            messages.append({
                "role": "user",
                "content": (
                    "[UQA CORE: EXACT RESOURCE ROW SELECTED]\n"
                    "Core selected the unique checkbox whose table row "
                    "contains the exact registered resource name. The only "
                    "allowed mutation now is Delete/Remove of that selection."
                ),
            })
        else:
            exact_name = str(resource.get("name") or "").strip()
            inspect_arguments = {
                "name": exact_name,
                "exact": True,
            }
            inspect_result = execute_tool_with_policy(
                "browser_inspect_semantic",
                inspect_arguments,
                messages,
                action_policy="confirm_mutations",
            )
            add_cleanup_attempt_event(
                job_id,
                resource_id,
                attempt_id,
                _cleanup_event_summary(
                    "browser_inspect_semantic",
                    inspect_arguments,
                    inspect_result,
                ),
            )

            if not _cleanup_tool_succeeded(inspect_result):
                if _cleanup_can_reconcile_exact_absence(
                    resource,
                    "browser_inspect_semantic",
                    inspect_result,
                ):
                    reason = (
                        "confirmed destructive cleanup verified "
                        "by exact absence on resumed attempt"
                    )
                    finish_cleanup_attempt(
                        job_id,
                        resource_id,
                        attempt_id,
                        outcome="cleaned",
                        reason=reason,
                        result={
                            "status": "cleaned",
                            "reason": reason,
                        },
                    )
                    return {
                        "status": "cleaned",
                        "reason": reason,
                    }

                reason = "cleanup_exact_resource_not_visible"
                finish_cleanup_attempt(
                    job_id,
                    resource_id,
                    attempt_id,
                    outcome="pending",
                    reason=reason,
                )
                return {"status": "pending", "reason": reason}

            context_arguments = {
                "name": exact_name,
                "exact": True,
            }
            context_result = execute_tool_with_policy(
                "browser_context_menu_semantic",
                context_arguments,
                messages,
                action_policy="confirm_mutations",
            )
            add_cleanup_attempt_event(
                job_id,
                resource_id,
                attempt_id,
                _cleanup_event_summary(
                    "browser_context_menu_semantic",
                    context_arguments,
                    context_result,
                ),
            )

            if not _cleanup_tool_succeeded(context_result):
                reason = "cleanup_exact_context_menu_failed"
                finish_cleanup_attempt(
                    job_id,
                    resource_id,
                    attempt_id,
                    outcome="pending",
                    reason=reason,
                )
                return {"status": "pending", "reason": reason}

            messages.append({
                "role": "user",
                "content": (
                    "[UQA CORE: EXACT RESOURCE CONTEXT MENU OPENED]\n"
                    "Core verified the exact registered resource name and "
                    "opened only that table row's context menu. Use only "
                    "the visible menu actions for this resource.\n"
                    "visible_menuitems: "
                    + json.dumps(
                        sorted({
                            str(
                                item.get("aria_label")
                                or item.get("text")
                                or ""
                            ).strip()
                            for item in context_result.get(
                                "interactive_elements",
                                [],
                            )
                            if str(item.get("role") or "").casefold()
                            == "menuitem"
                            and str(
                                item.get("aria_label")
                                or item.get("text")
                                or ""
                            ).strip()
                        }),
                        ensure_ascii=False,
                    )
                ),
            })

        for _ in range(MAX_TOOL_STEPS):
            try:
                data = ask_ollama(
                    messages,
                    tools=available_tools,
                )
            except Exception as exc:
                finish_cleanup_attempt(
                    job_id,
                    resource_id,
                    attempt_id,
                    outcome="failed",
                    reason=(
                        "cleanup_infrastructure_error: "
                        f"{type(exc).__name__}"
                    ),
                )

                return {
                    "status": "failed",
                    "reason": "cleanup_infrastructure_error",
                }

            message = data.get("message", {})
            content = message.get("content", "")
            tool_calls = message.get("tool_calls") or []
            assistant_message = {
                "role": "assistant",
                "content": content,
            }

            if tool_calls:
                assistant_message["tool_calls"] = tool_calls

            messages.append(assistant_message)

            if not tool_calls:
                parsed, error = _parse_cleanup_result(
                    content
                )

                if error:
                    finish_cleanup_attempt(
                        job_id,
                        resource_id,
                        attempt_id,
                        outcome="failed",
                        reason=error,
                    )

                    return {
                        "status": "failed",
                        "reason": error,
                    }

                if parsed["status"] == "cleaned":
                    if not destructive_executed:
                        reason = (
                            "cleanup_claim_without_confirmed_"
                            "destructive_action"
                        )
                        finish_cleanup_attempt(
                            job_id,
                            resource_id,
                            attempt_id,
                            outcome="failed",
                            reason=reason,
                            result=parsed,
                        )

                        return {
                            "status": "failed",
                            "reason": reason,
                        }

                    if not browser_verified_after_destructive:
                        reason = (
                            "cleanup_claim_without_post_action_"
                            "browser_verification"
                        )
                        finish_cleanup_attempt(
                            job_id,
                            resource_id,
                            attempt_id,
                            outcome="failed",
                            reason=reason,
                            result=parsed,
                        )

                        return {
                            "status": "failed",
                            "reason": reason,
                        }

                    finish_cleanup_attempt(
                        job_id,
                        resource_id,
                        attempt_id,
                        outcome="cleaned",
                        reason=parsed.get("reason"),
                        result=parsed,
                    )

                    return parsed

                finish_cleanup_attempt(
                    job_id,
                    resource_id,
                    attempt_id,
                    outcome=parsed["status"],
                    reason=parsed.get("reason"),
                    result=parsed,
                )

                return parsed

            for call in tool_calls:
                function = call.get("function", {})
                name = function.get("name")
                arguments = function.get("arguments") or {}

                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError:
                        arguments = {}

                action_class = classify_tool_action(
                    name,
                    arguments,
                )

                if name not in available_names:
                    result = {
                        "error": "cleanup_tool_not_allowed",
                        "status": "error",
                        "executed": False,
                        "tool": name,
                    }
                elif (
                    destructive_executed
                    and action_class in {
                        "write",
                        "destructive",
                    }
                ):
                    result = {
                        "error": (
                            "cleanup_repeat_mutation_forbidden"
                        ),
                        "status": "blocked_by_policy",
                        "executed": False,
                        "tool": name,
                        "reason": (
                            "A confirmed destructive cleanup action "
                            "already exists for this resource. Only "
                            "read-only post-action verification is "
                            "allowed."
                        ),
                    }
                elif (
                    exact_rest_cleanup_target
                    and action_class in {"write", "destructive"}
                    and not (
                        name == exact_rest_cleanup_target["tool"]
                        and arguments == exact_rest_cleanup_target["arguments"]
                    )
                ):
                    result = {
                        "error": "cleanup_mutation_not_exact_observed_resource",
                        "status": "blocked_by_policy",
                        "executed": False,
                        "tool": name,
                        "reason": (
                            "Core has one exact observed REST cleanup target; "
                            "other mutations are forbidden."
                        ),
                    }
                else:
                    try:
                        result = execute_tool_with_policy(
                            name,
                            arguments,
                            messages,
                            action_policy="confirm_mutations",
                        )
                    except Exception as exc:
                        result = {
                            "error": "cleanup_tool_error",
                            "status": "error",
                            "executed": False,
                            "tool": name,
                            "reason": (
                                f"{type(exc).__name__}: "
                                f"{str(exc)[:500]}"
                            ),
                        }

                result = _annotate_cleanup_mutation_result(
                    name,
                    arguments,
                    result,
                )

                add_cleanup_attempt_event(
                    job_id,
                    resource_id,
                    attempt_id,
                    _cleanup_event_summary(
                        name,
                        arguments,
                        result,
                    ),
                )

                if (
                    result.get("confirmation_pending")
                    is True
                ):
                    confirmation_arguments = {
                        "name": str(
                            arguments.get("name")
                            or ""
                        ).strip(),
                        "exact": True,
                        "role": "button",
                    }

                    try:
                        confirmation_result = (
                            execute_tool_with_policy(
                                "browser_click_semantic",
                                confirmation_arguments,
                                messages,
                                action_policy=(
                                    "confirm_mutations"
                                ),
                            )
                        )
                    except Exception as exc:
                        confirmation_result = {
                            "error": (
                                "cleanup_confirmation_"
                                "tool_error"
                            ),
                            "status": "error",
                            "executed": False,
                            "tool": (
                                "browser_click_semantic"
                            ),
                            "reason": (
                                f"{type(exc).__name__}: "
                                f"{str(exc)[:500]}"
                            ),
                        }

                    confirmation_result = (
                        _annotate_cleanup_mutation_result(
                            "browser_click_semantic",
                            confirmation_arguments,
                            confirmation_result,
                        )
                    )
                    add_cleanup_attempt_event(
                        job_id,
                        resource_id,
                        attempt_id,
                        _cleanup_event_summary(
                            "browser_click_semantic",
                            confirmation_arguments,
                            confirmation_result,
                        ),
                    )
                    arguments = confirmation_arguments
                    result = confirmation_result
                    action_class = classify_tool_action(
                        name,
                        arguments,
                    )

                if (
                    result.get("status")
                    == "blocked_by_policy"
                    and action_class in {
                        "write",
                        "destructive",
                    }
                ):
                    reason = (
                        "cleanup_action_not_approved"
                    )
                    finish_cleanup_attempt(
                        job_id,
                        resource_id,
                        attempt_id,
                        outcome="pending",
                        reason=reason,
                    )

                    return {
                        "status": "pending",
                        "reason": reason,
                    }

                if _cleanup_tool_succeeded(result):
                    if (
                        action_class == "destructive"
                        and result.get(
                            "action_policy_status"
                        ) == "confirmed"
                        and result.get(
                            "mutation_executed"
                        ) is True
                    ):
                        destructive_executed = True
                        browser_verified_after_destructive = (
                            _cleanup_browser_verification_succeeded(
                                name,
                                result,
                            )
                        )

                        if (
                            not browser_verified_after_destructive
                            and _cleanup_resource_was_exact_table_row(
                                job,
                                resource,
                            )
                        ):
                            post_arguments = {
                                "name": str(
                                    resource.get("name")
                                    or ""
                                ).strip(),
                                "exact": True,
                            }
                            post_result = (
                                execute_tool_with_policy(
                                    "browser_inspect_table_row",
                                    post_arguments,
                                    messages,
                                    action_policy=(
                                        "confirm_mutations"
                                    ),
                                )
                            )
                            add_cleanup_attempt_event(
                                job_id,
                                resource_id,
                                attempt_id,
                                _cleanup_event_summary(
                                    "browser_inspect_table_row",
                                    post_arguments,
                                    post_result,
                                ),
                            )
                            browser_verified_after_destructive = (
                                _cleanup_browser_verification_succeeded(
                                    "browser_inspect_table_row",
                                    post_result,
                                )
                            )

                            if (
                                not browser_verified_after_destructive
                                and _cleanup_tool_succeeded(
                                    post_result
                                )
                            ):
                                context_result = (
                                    execute_tool_with_policy(
                                        "browser_context_menu_semantic",
                                        post_arguments,
                                        messages,
                                        action_policy=(
                                            "confirm_mutations"
                                        ),
                                    )
                                )
                                add_cleanup_attempt_event(
                                    job_id,
                                    resource_id,
                                    attempt_id,
                                    _cleanup_event_summary(
                                        "browser_context_menu_semantic",
                                        post_arguments,
                                        context_result,
                                    ),
                                )
                                browser_verified_after_destructive = (
                                    _cleanup_inverse_action_visible(
                                        context_result,
                                        arguments.get("name"),
                                    )
                                )
                    elif (
                        destructive_executed
                        and action_class == "observe"
                        and _cleanup_browser_verification_succeeded(
                            name,
                            result,
                        )
                    ):
                        browser_verified_after_destructive = True

                elif (
                    destructive_executed
                    and action_class == "observe"
                    and _cleanup_browser_verification_succeeded(
                        name,
                        result,
                    )
                ):
                    # semantic_element_not_found is an expected successful
                    # verification for an exact post-delete lookup.
                    browser_verified_after_destructive = True

                messages.append(
                    {
                        "role": "tool",
                        "tool_name": name,
                        "content": json.dumps(
                            tool_result_for_model(name, result),
                            ensure_ascii=False,
                        ),
                    }
                )

        reason = "cleanup_tool_step_limit"
        finish_cleanup_attempt(
            job_id,
            resource_id,
            attempt_id,
            outcome="failed",
            reason=reason,
        )

        return {
            "status": "failed",
            "reason": reason,
        }

    except BaseException as exc:
        try:
            finish_cleanup_attempt(
                job_id,
                resource_id,
                attempt_id,
                outcome="failed",
                reason=(
                    "cleanup_runner_interrupted: "
                    f"{type(exc).__name__}"
                ),
            )
        except Exception:
            pass

        raise


def run_cleanup_job(job_id):
    job = get_job(job_id)

    if job is None:
        raise FileNotFoundError(
            job_id
        )

    candidates = list_cleanup_candidates(
        job_id
    )

    if not candidates:
        status = recompute_cleanup_status(
            job_id
        )
        console.print(
            f"[dim]Cleanup {job_id}: "
            f"no pending resources ({status})."
            f"[/dim]"
        )
        return {
            "job_id": job_id,
            "status": status,
            "cleaned": 0,
            "pending": 0,
            "failed": 0,
        }

    try:
        ordered = order_cleanup_resources(
            candidates
        )
    except ValueError:
        console.print(
            "[red]Cleanup blocked: dependency cycle.[/red]"
        )
        return {
            "job_id": job_id,
            "status": "failed",
            "cleaned": 0,
            "pending": len(candidates),
            "failed": 0,
            "reason": "cleanup_dependency_cycle",
        }

    console.print()
    console.print(
        Panel(
            (
                f"Job: {job_id}\n"
                f"Resources: {len(ordered)}\n"
                "Order: dependents first, then dependencies"
            ),
            title="Cleanup Manager",
        )
    )

    counts = {
        "cleaned": 0,
        "pending": 0,
        "failed": 0,
    }

    for index, resource in enumerate(
        ordered,
        1,
    ):
        console.print(
            f"[cyan]Cleanup {index}/{len(ordered)}:[/cyan] "
            f"{resource.get('type')} "
            f"{resource.get('name') or resource.get('external_id')} "
            f"[dim]({resource.get('resource_id')})[/dim]"
        )

        result = run_cleanup_resource(
            job_id,
            resource,
        )
        outcome = result.get("status")
        counts[outcome] = counts.get(
            outcome,
            0,
        ) + 1

        console.print(
            f"[cyan]Cleanup result:[/cyan] "
            f"{str(outcome).upper()} — "
            f"{result.get('reason') or ''}"
        )

        if outcome in {
            "pending",
            "failed",
        }:
            console.print(
                "[yellow]Cleanup paused before dependencies. "
                f"Resume with /cleanup {job_id}.[/yellow]"
            )
            break

    status = recompute_cleanup_status(
        job_id
    )

    console.print(
        f"[dim]Cleanup status: {status}; "
        f"cleaned={counts.get('cleaned', 0)}, "
        f"pending={counts.get('pending', 0)}, "
        f"failed={counts.get('failed', 0)}"
        f"[/dim]"
    )

    return {
        "job_id": job_id,
        "status": status,
        **counts,
    }


def _parse_cleanup_command(value):
    match = re.fullmatch(
        r"/cleanup(?:\s+([A-Za-z0-9_-]+))?\s*",
        str(value or "").strip(),
    )

    if not match:
        return None

    return match.group(1) or ""



def run_regression_job(
    original_request: str,
    safe_request: str,
    current_stand: str = None,
    stand_identity: dict = None,
):
    job = create_job(
        request=redact_credentials(
            original_request
        ),
        stand=current_stand,
        stand_identity=stand_identity,
        job_type="regression",
    )

    job_id = job["job_id"]

    # Job remains "created" while an LLM-generated
    # regression plan is awaiting user confirmation.
    #
    # Explicit numbered cases are authoritative and
    # do not require a second scope confirmation.
    planning_request = redact_credentials(
        original_request
    )

    explicit_plan = (
        extract_explicit_regression_cases(
            planning_request
        )
    )

    plan_is_authoritative = bool(
        explicit_plan
    )

    # --------------------------------------------------------
    # Planning
    # --------------------------------------------------------

    try:
        if plan_is_authoritative:
            plan = explicit_plan
        else:
            plan = plan_regression_cases(
                planning_request
            )

        plan = _lock_regression_plan_stand(
            plan,
            current_stand,
        )
    except Exception as exc:
        case = add_test_case(
            job_id,
            title="Планирование регресса",
        )

        update_test_case(
            job_id,
            case["case_id"],
            status="blocked",
            result=(
                "[UQA CORE]\n"
                "status=BLOCKED\n"
                "reason=regression_planner_error\n"
                f"detail={type(exc).__name__}: "
                f"{str(exc)[:1500]}"
            ),
        )

        recompute_job_status(
            job_id
        )

        summary = (
            "Regression planning failed: "
            f"{type(exc).__name__}: {str(exc)[:500]}"
        )

        set_job_summary(
            job_id,
            summary,
        )

        console.print(
            f"[red]Regression planner error:[/red] "
            f"{exc}"
        )

        console.print(
            f"[dim]Job saved: {job_id}[/dim]"
        )

        return job_id

    # --------------------------------------------------------
    # LLM-generated scope must be explicitly accepted.
    #
    # No test case is created and no runtime tool is executed
    # before the tester confirms the proposed plan.
    # --------------------------------------------------------

    if not plan_is_authoritative:
        refinements = []

        while True:
            _print_proposed_regression_plan(
                plan
            )

            action = (
                _ask_regression_plan_action()
            )

            if action == "accept":
                break

            if action == "cancel":
                set_job_status(
                    job_id,
                    "cancelled",
                )

                set_job_summary(
                    job_id,
                    (
                        "Regression cancelled before "
                        "execution: proposed plan was "
                        "not confirmed."
                    ),
                )

                console.print()
                console.print(
                    "[yellow]"
                    "Regression отменён. "
                    "Ни один case не запускался."
                    "[/yellow]"
                )

                console.print(
                    f"[dim]Job saved: "
                    f"{job_id}[/dim]"
                )

                return job_id

            refinement = (
                _ask_regression_plan_refinement()
            )

            refinements.append(
                refinement
            )

            revised_request = (
                planning_request
                + "\n\n"
                + "[UQA CORE: USER SCOPE REFINEMENTS]\n"
                + "\n".join(
                    f"- {item}"
                    for item in refinements
                )
            )

            try:
                plan = plan_regression_cases(
                    revised_request
                )

                plan = _lock_regression_plan_stand(
                    plan,
                    current_stand,
                )

            except Exception as exc:
                console.print()
                console.print(
                    "[yellow]"
                    "Не удалось перепланировать: "
                    f"{type(exc).__name__}: "
                    f"{str(exc)[:500]}"
                    "[/yellow]"
                )

                console.print(
                    "[dim]"
                    "Предыдущий план сохранён. "
                    "Можно уточнить ещё раз, "
                    "принять его или отменить."
                    "[/dim]"
                )

    # Compile deterministic locked requirements before
    # any test case exists. Explicit numbered scope also
    # passes here without invoking the LLM Planner.
    prepare_locked_requirements(
        plan
    )

    # Only now does execution actually start.
    set_job_status(
        job_id,
        "running",
    )

    # --------------------------------------------------------
    # Create all cases first.
    # Pending cases keep Job running while regression executes.
    # --------------------------------------------------------

    created = []

    for spec in plan:
        case = add_test_case(
            job_id,
            title=spec["title"],
            expected=spec.get(
                "expected"
            ),
            requirement=spec.get(
                "requirement"
            ),
            planned_checks=spec.get(
                "checks"
            ),
        )

        created.append(
            (case, spec)
        )

    console.print(
        f"\n[bold cyan]Regression Job:[/bold cyan] "
        f"{job_id}"
    )

    console.print(
        f"[cyan]Cases: {len(created)}[/cyan]"
    )

    for index, (case, spec) in enumerate(
        created,
        start=1,
    ):
        console.print(
            f"[dim]"
            f"{index}. {spec['title']} "
            f"({case['case_id']})"
            f"[/dim]"
        )

    # --------------------------------------------------------
    # Execution flow.
    # STEP is the default interactive mode.
    # --------------------------------------------------------

    execution_mode = (
        _ask_regression_execution_mode()
    )

    console.print(
        f"[cyan]"
        f"Execution mode: "
        f"{execution_mode.upper()}"
        f"[/cyan]"
    )

    user_stopped = False

    # --------------------------------------------------------
    # Each case gets a completely fresh LLM context.
    # BrowserSession remains process-local/shared.
    # --------------------------------------------------------

    for index, (case, spec) in enumerate(
        created,
        start=1,
    ):
        case_id = case["case_id"]

        update_test_case(
            job_id,
            case_id,
            status="running",
        )

        console.print(
            f"\n[bold]"
            f"=== Case {index}/{len(created)}: "
            f"{spec['title']} ==="
            f"[/bold]"
        )

        case_messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": _build_regression_case_prompt(
                    original_request=original_request,
                    safe_request=safe_request,
                    job_id=job_id,
                    case_id=case_id,
                    index=index,
                    total=len(created),
                    case_spec=spec,
                ),
            },
        ]

        try:
            # Every regression case gets a clean Playwright
            # BrowserContext. Chromium itself stays alive.
            try:
                from tools.browser import (
                    reset_case_context,
                )

                reset_case_context()

            except Exception as exc:
                finalize_case_blocked(
                    job_id,
                    case_id,
                    "browser_context_reset_failed",
                    (
                        f"{type(exc).__name__}: "
                        f"{str(exc)}"
                    ),
                )

                raise

            run_turn(
                case_messages,
                job_id=job_id,
                case_id=case_id,
                action_policy="confirm_mutations",
            )

            case_artifacts = (
                export_regression_case_artifacts(
                    job_id,
                    case_id,
                    index,
                )
            )

            _print_case_artifact_links(
                case_artifacts
            )

        except Exception as exc:
            console.print(
                f"[red]"
                f"Regression execution aborted after "
                f"case {index}: {exc}"
                f"[/red]"
            )

            # Current case is normally already BLOCKED
            # by run_turn infrastructure finalization.
            # Remaining cases were never attempted.
            for remaining_case, _ in created[index:]:
                update_test_case(
                    job_id,
                    remaining_case["case_id"],
                    status="skipped",
                    result=(
                        "[UQA CORE]\n"
                        "status=SKIPPED\n"
                        "reason=regression_aborted\n"
                        "detail=Previous case caused "
                        "runner/infrastructure exception."
                    ),
                )

            recompute_job_status(
                job_id
            )

            break

        # ----------------------------------------------------
        # STEP mode pause.
        #
        # Do not pause after the last case.
        # ----------------------------------------------------

        if (
            execution_mode == "step"
            and index < len(created)
        ):
            action = (
                _ask_regression_step_action()
            )

            if action == "auto":
                execution_mode = "auto"

                console.print(
                    "[cyan]"
                    "Переключено в AUTO. "
                    "Оставшиеся cases будут "
                    "выполнены без пауз."
                    "[/cyan]"
                )

            elif action == "stop":
                user_stopped = True

                # created[index:] means:
                # all cases AFTER the current
                # 1-based enumerate index.
                for remaining_case, _ in (
                    created[index:]
                ):
                    update_test_case(
                        job_id,
                        remaining_case[
                            "case_id"
                        ],
                        status="skipped",
                        result=(
                            "[UQA CORE]\n"
                            "status=SKIPPED\n"
                            "reason=stopped_by_user\n"
                            "detail=Regression was "
                            "stopped by the user "
                            "between test cases."
                        ),
                    )

                # Important:
                # PASS + SKIPPED must not become
                # a false successful regression.
                set_job_status(
                    job_id,
                    "cancelled",
                )

                console.print(
                    "[yellow]"
                    "Regression остановлен "
                    "пользователем. "
                    "Оставшиеся cases: SKIPPED."
                    "[/yellow]"
                )

                break

    # Cleanup is a separate lifecycle phase. Test verdicts remain
    # machine-derived from evidence/ledger facts; every stand mutation
    # still passes through v069 policy.
    run_cleanup_job(
        job_id
    )

    reconciled_case_ids = (
        reconcile_resource_lifecycle_checks(
            job_id
        )
    )

    # Case bundles were first exported before cleanup. Refresh only the
    # lifecycle cases so their JSON/report contains the final cleanup facts.
    for index, (case, _spec) in enumerate(
        created,
        start=1,
    ):
        if case.get("case_id") in reconciled_case_ids:
            export_regression_case_artifacts(
                job_id,
                case.get("case_id"),
                index,
            )

    final_status = recompute_job_status(
        job_id
    )

    stored = get_job(
        job_id
    )

    summary = _regression_summary(
        stored
    )

    set_job_summary(
        job_id,
        summary,
    )

    regression_artifacts = (
        export_regression_job_artifacts(
            job_id
        )
    )

    console.print()
    console.print(
        Panel(
            (
                f"{summary}\n"
                f"Overall: "
                f"{str(final_status).upper()}"
            ),
            title="Regression Result",
        )
    )

    if regression_artifacts:
        report_url = (
            regression_artifacts.get(
                "report_url"
            )
        )

        zip_url = (
            regression_artifacts.get(
                "zip_url"
            )
        )

        if report_url:
            console.print(
                "[cyan]Regression report:[/cyan] "
                f"{report_url}"
            )

        if zip_url:
            console.print(
                "[cyan]Download regression:[/cyan] "
                f"{zip_url}"
            )

    console.print(
        f"[dim]Job saved: {job_id}[/dim]"
    )

    return job_id


def artifact_public_url(
    artifact_path,
    download=False,
):
    """
    Convert a browser artifact filesystem path into a
    user-scoped HTTP URL.

    This is presentation-only:
    Job/evidence storage continues using the real local path.
    """
    import os
    import pwd
    from pathlib import Path
    from urllib.parse import quote

    try:
        path = Path(
            str(artifact_path)
        ).resolve()

        username = (
            os.getenv("UQA_USER")
            or os.getenv("USER")
        )

        if not username:
            return None

        safe_username = "".join(
            ch
            if ch.isalnum() or ch in "._-"
            else "_"
            for ch in username
        )

        user_root = Path(
            "/opt/uqa/artifacts/browser"
        ) / safe_username

        user_root = user_root.resolve()

        if not path.is_relative_to(
            user_root
        ):
            return None

        user_info = pwd.getpwnam(
            username
        )

        token_file = (
            Path(user_info.pw_dir)
            / ".uqa-artifact-token"
        )

        token = (
            token_file
            .read_text(
                encoding="utf-8"
            )
            .strip()
        )

        if not token:
            return None

        relative = path.relative_to(
            user_root
        )

        encoded_path = "/".join(
            quote(part, safe="")
            for part in relative.parts
        )

        url = (
            "http://192.168.50.72:8765"
            f"/artifact/{quote(token, safe='')}"
            f"/{encoded_path}"
        )

        if download:
            url += "?download=1"

        return url

    except Exception:
        # Evidence display must never break QA execution.
        return None


def run_turn(
    messages,
    job_id=None,
    case_id=None,
    force_read_only=False,
    action_policy="legacy",
):
    failed_semantic_inspections = set()
    blocked_mutation_calls = set()

    for _ in range(MAX_TOOL_STEPS):
        try:
            data = ask_ollama(messages)
        except Exception as exc:
            if job_id and case_id:
                finalize_case_blocked(
                    job_id,
                    case_id,
                    "infrastructure_error",
                    (
                        f"{type(exc).__name__}: "
                        f"{str(exc)}"
                    ),
                )

                console.print(
                    f"[yellow]"
                    f"Job {job_id} / {case_id} "
                    f"marked BLOCKED: "
                    f"infrastructure_error"
                    f"[/yellow]"
                )

            raise

        message = data.get("message", {})
        content = message.get("content", "")
        tool_calls = message.get("tool_calls") or []

        assistant_message = {
            "role": "assistant",
            "content": content,
        }

        if tool_calls:
            assistant_message["tool_calls"] = tool_calls

        messages.append(assistant_message)

        if not tool_calls:
            pending_constrained_action = (
                _PENDING_CONSTRAINED_ACTIONS.get(
                    (
                        str(job_id),
                        str(case_id),
                    )
                )
                if job_id and case_id
                else None
            )

            if pending_constrained_action:
                console.print(
                    "[yellow]UQA Core: an exact task-constrained action is "
                    "still required; continuing the case.[/yellow]"
                )
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "[UQA CORE: CONTINUE EXACT ACTION]\n"
                            "The regression case is not complete. Call this "
                            "exact task-constrained action now. It will still "
                            "require normal policy confirmation:\n"
                            + json.dumps(
                                pending_constrained_action,
                                ensure_ascii=False,
                            )
                        ),
                    }
                )
                continue

            omission_continuation = (
                _PENDING_OMISSION_CONTINUATIONS.pop(
                    (
                        str(job_id),
                        str(case_id),
                    ),
                    None,
                )
                if job_id and case_id
                else None
            )

            if omission_continuation:
                console.print(
                    "[yellow]UQA Core: the blank-field constraint was "
                    "enforced; continuing the case.[/yellow]"
                )
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "[UQA CORE: CONTINUE AFTER OMITTED FIELD]\n"
                            "The regression case is not complete. Core "
                            "enforced the requirement that this field remain "
                            "blank:\n"
                            + json.dumps(
                                omission_continuation,
                                ensure_ascii=False,
                            )
                            + "\nContinue with the next required operation. "
                            "Do not fill that field again."
                        ),
                    }
                )
                continue

            selection_continuation = (
                _PENDING_SELECTION_CONTINUATIONS.pop(
                    (
                        str(job_id),
                        str(case_id),
                    ),
                    None,
                )
                if job_id and case_id
                else None
            )

            if selection_continuation:
                console.print(
                    "[yellow]UQA Core: the required selection was "
                    "completed; continuing the case.[/yellow]"
                )
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "[UQA CORE: CONTINUE AFTER REQUIRED SELECTION]\n"
                            "The regression case is not complete. This exact "
                            "required selection succeeded:\n"
                            + json.dumps(
                                selection_continuation,
                                ensure_ascii=False,
                            )
                            + "\nContinue with the next required operation."
                        ),
                    }
                )
                continue

            pending_navigation = (
                _PENDING_NAVIGATION_CANDIDATES.get(
                    (
                        str(job_id),
                        str(case_id),
                    )
                )
                or _latest_required_navigation_candidate(
                    messages
                )
                if job_id and case_id
                else None
            )

            if pending_navigation:
                console.print(
                    "[yellow]UQA Core: navigation preflight is still "
                    "required; continuing the case.[/yellow]"
                )
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "[UQA CORE: CONTINUE NAVIGATION]\n"
                            "The regression case is not complete. Do not "
                            "return a final answer yet. Call this exact "
                            "already-observed INTERACT candidate now:\n"
                            + json.dumps(
                                pending_navigation,
                                ensure_ascii=False,
                            )
                        ),
                    }
                )
                continue

            (
                structured_checks,
                visible_content,
                structured_error,
            ) = extract_structured_checks(
                content
            )

            if visible_content.strip():
                console.print()
                console.print(
                    Markdown(visible_content)
                )
                console.print()

            if job_id and case_id:
                stored_result = visible_content

                if structured_error:
                    case_status = "blocked"

                    stored_result += (
                        "\n\n"
                        "[UQA CORE]\n"
                        "status=BLOCKED\n"
                        f"reason={structured_error}"
                    )

                elif structured_checks is None:
                    # Для фактического QA Job structured result
                    # обязателен. Обычный текст модели никогда
                    # не является источником PASS/FAIL.
                    case_status = "blocked"

                    stored_result += (
                        "\n\n"
                        "[UQA CORE]\n"
                        "status=BLOCKED\n"
                        "reason=structured_result_missing"
                    )

                else:
                    # Единственный источник статуса test case —
                    # валидный UQA_CHECKS_JSON, whose evidence
                    # is bound to this exact Job/Case.
                    (
                        structured_checks,
                        coverage_errors,
                    ) = verify_planned_check_coverage(
                        job_id,
                        case_id,
                        structured_checks,
                    )

                    (
                        structured_checks,
                        evidence_errors,
                    ) = (
                        verify_structured_check_evidence(
                            job_id,
                            case_id,
                            structured_checks,
                        )
                    )

                    (
                        structured_checks,
                        lifecycle_check_ids,
                    ) = verify_resource_lifecycle_checks(
                        job_id,
                        case_id,
                        structured_checks,
                        phase="case",
                    )

                    # Ledger/cleanup assertions are verified from
                    # persisted Core facts, not browser evidence.
                    evidence_errors = [
                        item
                        for item in evidence_errors
                        if item.get("check_id")
                        not in lifecycle_check_ids
                    ]

                    case_status = (
                        infer_case_status_from_checks(
                            structured_checks
                        )
                    )

                    if coverage_errors:
                        case_status = "blocked"

                        stored_result += (
                            "\n\n"
                            "[UQA CORE]\n"
                            "status=BLOCKED\n"
                            "reason=planned_check_coverage_not_verified\n"
                            "detail="
                            + json.dumps(
                                coverage_errors,
                                ensure_ascii=False,
                            )[:2000]
                        )

                    elif evidence_errors:
                        case_status = "blocked"

                        stored_result += (
                            "\n\n"
                            "[UQA CORE]\n"
                            "status=BLOCKED\n"
                            "reason=evidence_not_verified\n"
                            "detail="
                            + json.dumps(
                                evidence_errors,
                                ensure_ascii=False,
                            )[:2000]
                        )

                if not case_status:
                    case_status = "blocked"
                    stored_result = (
                        content
                        + "\n\n"
                        + "[UQA CORE]\n"
                        + "status=BLOCKED\n"
                        + "reason=verdict_not_detected"
                    )

                if case_status:
                    update_test_case(
                        job_id,
                        case_id,
                        status=case_status,
                        result=stored_result,
                        checks=(
                            structured_checks
                            if structured_checks is not None
                            else None
                        ),
                    )

                    recompute_job_status(
                        job_id
                    )

                    if case_status == "passed":
                        try:
                            candidates = (
                                generate_candidate_facts_for_case(
                                    job_id,
                                    case_id,
                                )
                            )

                            console.print(
                                f"[dim]Candidate facts: "
                                f"{len(candidates)}[/dim]"
                            )

                            knowledge_ingested = 0

                            for candidate in candidates:
                                if not candidate.get(
                                    "fact_key"
                                ):
                                    continue

                                current_job = get_job(
                                    job_id
                                )

                                ingest_candidate(
                                    job_id=job_id,
                                    case_id=case_id,
                                    stand=(
                                        current_job.get(
                                            "stand"
                                        )
                                        if current_job
                                        else None
                                    ),
                                    candidate=candidate,
                                    product_version=None,
                                    stand_identity=(
                                        current_job.get(
                                            "stand_identity"
                                        )
                                        if current_job
                                        else None
                                    ),
                                )

                                knowledge_ingested += 1

                                # После каждого нового confirmation
                                # проверяем version-scoped knowledge.
                                #
                                # Сейчас автоматическая promotion
                                # поддерживается только для известных
                                # validator fact types.
                                identity = (
                                    current_job.get(
                                        "stand_identity"
                                    )
                                    if current_job
                                    else {}
                                ) or {}

                                architecture = (
                                    identity.get(
                                        "installation_architecture"
                                    )
                                )

                                server_version = (
                                    identity.get(
                                        "server_version"
                                    )
                                )

                                if (
                                    architecture
                                    and server_version
                                ):
                                    try:
                                        promotion = (
                                            promote_candidate_scope_if_eligible(
                                                fact_key=(
                                                    candidate[
                                                        "fact_key"
                                                    ]
                                                ),
                                                fact_type=(
                                                    candidate.get(
                                                        "fact_type"
                                                    )
                                                ),
                                                installation_architecture=(
                                                    architecture
                                                ),
                                                server_version=(
                                                    server_version
                                                ),
                                            )
                                        )

                                        console.print(
                                            f"[dim]"
                                            f"Knowledge validation: "
                                            f"{promotion.get('action')}"
                                            f"[/dim]"
                                        )

                                        conflict_check = (
                                            mark_verified_subject_conflicts_for_candidate(
                                                fact_key=(
                                                    candidate[
                                                        "fact_key"
                                                    ]
                                                ),
                                                fact_type=(
                                                    candidate.get(
                                                        "fact_type"
                                                    )
                                                ),
                                                installation_architecture=(
                                                    architecture
                                                ),
                                                server_version=(
                                                    server_version
                                                ),
                                            )
                                        )

                                        console.print(
                                            f"[dim]"
                                            f"Conflict validation: "
                                            f"checked="
                                            f"{conflict_check.get('checked', 0)}, "
                                            f"marked="
                                            f"{conflict_check.get('marked', 0)}"
                                            f"[/dim]"
                                        )

                                    except Exception as exc:
                                        console.print(
                                            f"[yellow]"
                                            f"Knowledge validation warning: "
                                            f"{exc}"
                                            f"[/yellow]"
                                        )

                            console.print(
                                f"[dim]Product knowledge: "
                                f"{knowledge_ingested} "
                                f"candidate(s) ingested"
                                f"[/dim]"
                            )

                        except Exception as exc:
                            console.print(
                                f"[yellow]"
                                f"Candidate fact warning: "
                                f"{exc}"
                                f"[/yellow]"
                            )
                else:
                    update_test_case(
                        job_id,
                        case_id,
                        result=content,
                    )

                console.print(
                    f"[dim]Job saved: "
                    f"{job_id}[/dim]"
                )

            _PENDING_NAVIGATION_CANDIDATES.pop(
                (
                    str(job_id),
                    str(case_id),
                ),
                None,
            )
            _PENDING_CONSTRAINED_ACTIONS.pop(
                (
                    str(job_id),
                    str(case_id),
                ),
                None,
            )
            _PENDING_OMISSION_CONTINUATIONS.pop(
                (
                    str(job_id),
                    str(case_id),
                ),
                None,
            )
            _PENDING_SELECTION_COMPLETIONS.pop(
                (
                    str(job_id),
                    str(case_id),
                ),
                None,
            )
            _PENDING_SELECTION_FIELD_TRANSITIONS.pop(
                (
                    str(job_id),
                    str(case_id),
                ),
                None,
            )
            _COMPLETED_REQUIRED_SELECTIONS.pop(
                (
                    str(job_id),
                    str(case_id),
                ),
                None,
            )
            _PENDING_SELECTION_CONTINUATIONS.pop(
                (
                    str(job_id),
                    str(case_id),
                ),
                None,
            )
            _COMPATIBILITY_PREFLIGHT_BY_CASE.pop(
                (
                    str(job_id),
                    str(case_id),
                ),
                None,
            )
            compact_completed_history(messages)
            return

        if job_id and case_id:
            # A pending continuation is only needed when the model tries to
            # stop immediately after completing a required selection. If it
            # emitted another tool call, it has already continued; retaining
            # the marker could later consume an unrelated error response.
            _PENDING_SELECTION_CONTINUATIONS.pop(
                (str(job_id), str(case_id)),
                None,
            )

        for call in tool_calls:
            function = call.get("function", {})
            name = function.get("name")
            arguments = function.get("arguments") or {}

            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}

            action_class = classify_tool_action(
                name,
                arguments,
            )
            semantic_inspection_key = None
            repeated_semantic_inspection = False
            mutation_call_key = None
            repeated_blocked_mutation = False

            if name == "browser_inspect_semantic":
                semantic_inspection_key = (
                    str(arguments.get("name") or "").strip().casefold(),
                    bool(arguments.get("exact", True)),
                )
                repeated_semantic_inspection = (
                    semantic_inspection_key
                    in failed_semantic_inspections
                )

            if action_class in {"write", "destructive"}:
                mutation_call_key = (
                    str(name or ""),
                    json.dumps(
                        arguments,
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                )
                repeated_blocked_mutation = (
                    mutation_call_key in blocked_mutation_calls
                )

            console.print(
                f"\n[cyan]● TOOL[/cyan] "
                f"[magenta][{action_class.upper()}][/magenta] "
                f"{name} "
                f"[dim]{json.dumps(arguments, ensure_ascii=False)}[/dim]"
            )

            try:
                if repeated_semantic_inspection:
                    result = {
                        "error": "repeated_semantic_inspection_blocked",
                        "status": "blocked",
                        "executed": False,
                        "action_class": "observe",
                        "action_policy_status": "auto_allowed",
                        "semantic_name": arguments.get("name"),
                        "reason": (
                            "The same exact semantic target was already "
                            "searched with all strict fallback strategies."
                        ),
                    }
                elif repeated_blocked_mutation:
                    result = {
                        "error": "repeated_blocked_mutation",
                        "status": "blocked_by_policy",
                        "executed": False,
                        "action_class": action_class,
                        "action_policy_status": "blocked",
                        "reason": (
                            "The same mutation was already denied by policy "
                            "during this case."
                        ),
                    }
                else:
                    result = execute_tool_with_policy(
                        name,
                        arguments,
                        messages,
                        force_read_only=force_read_only,
                        action_policy=action_policy,
                        job_id=job_id,
                        case_id=case_id,
                        require_compatibility_probe=(
                            action_policy == "confirm_mutations"
                        ),
                    )
                record_required_selection_result(
                    job_id,
                    case_id,
                    result,
                    name=name,
                    arguments=arguments,
                )

                status = result.get("http_status")
                final_url = result.get("final_url")
                screenshot = result.get("screenshot")

                if result.get("status") == "blocked_by_policy":
                    console.print(
                        f"[yellow]⊘ TOOL BLOCKED[/yellow] "
                        f"{result.get('reason')}"
                    )
                elif result.get("error"):
                    console.print(
                        f"[red]✗ TOOL ERROR[/red] "
                        f"{result.get('error')}"
                    )
                else:
                    console.print(
                        f"[green]✓ TOOL RESULT[/green] "
                        f"HTTP={status} URL={final_url}"
                    )

                if screenshot:
                    public_url = (
                        artifact_public_url(
                            screenshot
                        )
                    )

                    download_url = (
                        artifact_public_url(
                            screenshot,
                            download=True,
                        )
                    )

                    if public_url:
                        console.print(
                            f"[cyan]Evidence:[/cyan] "
                            f"{public_url}"
                        )

                        console.print(
                            f"[dim]Download: "
                            f"{download_url}"
                            f"[/dim]"
                        )

                    else:
                        console.print(
                            f"[dim]"
                            f"Evidence: {screenshot}"
                            f"[/dim]"
                        )

            except Exception as exc:
                result = {
                    "error": str(exc),
                    "tool": name,
                }

                console.print(
                    f"[red]✗ TOOL ERROR[/red] {exc}"
                )

            tool_observations = (
                record_tool_observations(
                    job_id,
                    case_id,
                    name,
                    arguments,
                    result,
                )
            )

            tool_evidence = (
                record_tool_evidence(
                    job_id,
                    case_id,
                    name,
                    arguments,
                    result,
                    observation_ids=[
                        item[
                            "observation_id"
                        ]
                        for item
                        in tool_observations
                        if item.get(
                            "observation_id"
                        )
                    ],
                )
            )

            if (
                isinstance(result, dict)
                and tool_evidence
                and tool_evidence.get(
                    "evidence_id"
                )
            ):
                result = dict(result)

                result[
                    "uqa_evidence_id"
                ] = tool_evidence[
                    "evidence_id"
                ]

                if tool_observations:
                    result[
                        "uqa_observation_ids"
                    ] = [
                        item[
                            "observation_id"
                        ]
                        for item
                        in tool_observations
                        if item.get(
                            "observation_id"
                        )
                    ]

                result[
                    "uqa_evidence_usable_for_pass"
                ] = tool_evidence.get(
                    "usable_for_pass"
                )

                result[
                    "uqa_evidence_usable_for_verdict"
                ] = tool_evidence.get(
                    "usable_for_verdict"
                )

                result[
                    "uqa_evidence_execution_status"
                ] = tool_evidence.get(
                    "execution_status"
                )

                console.print(
                    "[dim]"
                    "Evidence ID: "
                    f"{tool_evidence['evidence_id']}"
                    "[/dim]"
                )

            messages.append(
                {
                    "role": "tool",
                    "tool_name": name,
                    "content": json.dumps(
                        tool_result_for_model(name, result),
                        ensure_ascii=False,
                    ),
                }
            )

            if repeated_semantic_inspection:
                if job_id and case_id:
                    finalize_case_blocked(
                        job_id,
                        case_id,
                        "repeated_semantic_inspection",
                        (
                            "The agent repeated a failed exact semantic "
                            f"inspection for {arguments.get('name')!r}."
                        ),
                    )

                console.print(
                    "[yellow]UQA Core stopped a repeated failed semantic "
                    "inspection; case marked BLOCKED.[/yellow]"
                )
                compact_completed_history(messages)
                return

            if repeated_blocked_mutation:
                if job_id and case_id:
                    finalize_case_blocked(
                        job_id,
                        case_id,
                        "repeated_blocked_mutation",
                        (
                            "The agent repeated a WRITE/DESTRUCTIVE action "
                            "after the same action was denied by policy."
                        ),
                    )

                console.print(
                    "[yellow]UQA Core stopped a repeated policy-denied "
                    "mutation; case marked BLOCKED.[/yellow]"
                )
                compact_completed_history(messages)
                return

            if (
                mutation_call_key is not None
                and result.get("status") == "blocked_by_policy"
                and result.get("action_policy_status") == "blocked"
            ):
                blocked_mutation_calls.add(mutation_call_key)
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "[UQA CORE: MUTATION DENIED]\n"
                            "Do not repeat the same WRITE or DESTRUCTIVE "
                            "action. Continue without it or return BLOCKED."
                        ),
                    }
                )

            if (
                semantic_inspection_key is not None
                and result.get("error")
                == "semantic_element_not_found"
            ):
                failed_semantic_inspections.add(
                    semantic_inspection_key
                )
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "[UQA CORE: SEMANTIC TARGET NOT FOUND]\n"
                            "Do not repeat browser_inspect_semantic for the "
                            "same name, including with another guessed role. "
                            "Inspect a different actually observed target or "
                            "return BLOCKED with the missing evidence."
                        ),
                    }
                )

    console.print(
        "[red]Достигнут лимит последовательных tool-вызовов.[/red]"
    )

    if job_id and case_id:
        finalize_case_blocked(
            job_id,
            case_id,
            "tool_step_limit",
            (
                "Maximum sequential tool calls reached: "
                f"{MAX_TOOL_STEPS}"
            ),
        )

        console.print(
            f"[yellow]"
            f"Job {job_id} / {case_id} "
            f"marked BLOCKED: tool_step_limit"
            f"[/yellow]"
        )


def sanitize_terminal_input(text: str):
    """
    Remove terminal bracketed-paste markers and control-only tails
    that can remain in stdin after multiline paste over SSH.
    """
    value = str(text or "")

    # Bracketed paste start/end markers.
    value = value.replace("\x1b[200~", "")
    value = value.replace("\x1b[201~", "")

    # Remove common ANSI CSI control sequences.
    value = re.sub(
        r"\x1b\[[0-9;?]*[ -/]*[@-~]",
        "",
        value,
    )

    # Keep normal text/newlines/tabs, remove other control chars.
    value = "".join(
        ch
        for ch in value
        if (
            ch in "\n\t"
            or ord(ch) >= 32
        )
    )

    return value.strip()


def read_user_input():
    """
    Read one normal terminal message.

    Prompt.ask() reads only until the first newline. When a user
    pastes multiple lines into an SSH TTY, the remaining lines stay
    queued in stdin and are later interpreted as separate messages.

    After the first line we therefore drain lines that arrive
    immediately as part of the same paste.

    Normal single-line input still requires only one Enter.
    """
    import select
    import sys

    first = Prompt.ask(
        "\n[bold cyan]>[/bold cyan]"
    )

    lines = [first]

    # Short idle window: pasted lines are already queued / arrive
    # immediately. Human input for the next message will not.
    idle_timeout = 0.08

    while True:
        try:
            readable, _, _ = select.select(
                [sys.stdin],
                [],
                [],
                idle_timeout,
            )
        except (ValueError, OSError):
            break

        if not readable:
            break

        next_line = sys.stdin.readline()

        if next_line == "":
            break

        lines.append(
            next_line.rstrip("\r\n")
        )

    return sanitize_terminal_input(
        "\n".join(lines)
    )


def main():
    banner()

    current_stand = None
    pending_stand = None
    pending_request = None
    version_checked_stands = set()

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

    while True:
        try:
            user_input = read_user_input()
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        if not user_input:
            continue

        if user_input == "/exit":
            break

        if user_input == "/clear":
            messages = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                }
            ]
            console.print("[yellow]Контекст очищен.[/yellow]")
            continue

        if user_input == "/status":
            _recheck_product_blockers_once(
                current_stand,
                version_checked_stands,
            )
            product_blockers = list_product_blockers(
                ["open", "needs_recheck"]
            )
            blocker_summary = (
                f"Open product blockers: {len(product_blockers)}"
            )

            if product_blockers:
                blocker_summary += "\n" + "\n".join(
                    "- "
                    f"{item.get('blocker_id')}: "
                    f"{item.get('status')} — "
                    f"{item.get('capability')}"
                    for item in product_blockers[:5]
                )

            console.print(
                Panel(
                    f"Model: {MODEL}\n"
                    f"Context: {UQA_NUM_CTX}\n"
                    f"Thinking: {'ON' if UQA_THINK else 'OFF'}\n"
                    f"Ollama: {OLLAMA_URL}\n"
                    f"Messages: {len(messages)}\n"
                    f"Tools ({len(_tool_names())}): "
                    f"{', '.join(_tool_names())}\n"
                    f"{blocker_summary}",
                    title="Status",
                )
            )
            continue

        if user_input == "/blockers":
            product_blockers = list_product_blockers(
                ["open", "needs_recheck"]
            )

            if not product_blockers:
                console.print(
                    "[green]No open product blockers.[/green]"
                )
                continue

            lines = []
            for item in product_blockers:
                versions = ", ".join(
                    f"{key}={value}"
                    for key, value in (
                        item.get("product_versions") or {}
                    ).items()
                ) or "unknown"
                lines.extend([
                    f"[bold]{item.get('blocker_id')}[/bold]",
                    f"  status: {item.get('status')}",
                    f"  capability: {item.get('capability')}",
                    f"  versions: {versions}",
                    f"  reason: {item.get('reason')}",
                    f"  retry: {item.get('retry_when') or 'manual'}",
                ])

            console.print(
                Panel(
                    "\n".join(lines),
                    title="Product blockers",
                )
            )
            continue

        cleanup_job_id = _parse_cleanup_command(
            user_input
        )

        if cleanup_job_id is not None:
            if not cleanup_job_id:
                console.print(
                    "[yellow]Usage: /cleanup JOB_ID[/yellow]"
                )
                continue

            try:
                run_cleanup_job(
                    cleanup_job_id
                )
            except Exception as exc:
                console.print(
                    "[red]Cleanup error:[/red] "
                    f"{type(exc).__name__}: "
                    f"{str(exc)[:500]}"
                )

            continue

        explicit_stand_candidate = (
            extract_explicit_stand_candidate(
                user_input
            )
        )

        if explicit_stand_candidate:
            resolved_candidate = resolve_stand(
                explicit_stand_candidate
            )

            if resolved_candidate is None:
                console.print(
                    f"[yellow]"
                    f"Я не знаю стенд "
                    f"\"{explicit_stand_candidate}\". "
                    f"Уточни адрес стенда или добавь его "
                    f"как новый стенд."
                    f"[/yellow]"
                )
                continue

        stand_from_message = extract_known_stand(
            user_input
        )

        if stand_from_message:
            current_stand = stand_from_message
            _recheck_product_blockers_once(
                current_stand,
                version_checked_stands,
            )

        credentials = extract_credentials(
            user_input
        )

        # Если UQA уже запросил SSH credentials для стенда,
        # разрешаем простой ответ:
        #
        #   adminacc <password>
        #
        # Пароль может содержать пробелы: всё после первого
        # пробела считается паролем.
        if (
            credentials is None
            and pending_stand
        ):
            parts = user_input.strip().split(
                maxsplit=1
            )

            if len(parts) == 2:
                credentials = {
                    "username": parts[0],
                    "password": parts[1],
                }

        # Тестировщик прислал login/password.
        # Этот текст НЕ отправляется в Qwen.
        if credentials:
            target_stand = (
                stand_from_message
                or pending_stand
                or current_stand
            )

            if not target_stand:
                console.print(
                    "[yellow]"
                    "Не понимаю, к какому стенду относятся "
                    "эти SSH-данные. Укажи стенд или URL."
                    "[/yellow]"
                )
                continue

            existing = get_stand(
                target_stand
            )

            ssh_host_from_message = (
                extract_ssh_host(
                    user_input
                )
            )

            ssh_host = (
                ssh_host_from_message
                or (
                    existing.get("ssh_host")
                    if existing
                    else target_stand
                )
            )

            save_credentials(
                stand=target_stand,
                username=credentials["username"],
                password=credentials["password"],
                ssh_host=ssh_host,
                web_url=(
                    existing.get("web_url")
                    if existing
                    else f"https://{target_stand}"
                ),
            )

            console.print(
                f"[cyan]Проверяю SSH для "
                f"{target_stand}...[/cyan]"
            )

            probe = probe_stand(
                target_stand
            )

            if probe.get("status") == "ok":
                current_stand = target_stand
                _recheck_product_blockers_once(
                    current_stand,
                    version_checked_stands,
                )
                alias_from_message = (
                    extract_new_stand_alias(
                        user_input
                    )
                )

                if alias_from_message:
                    try:
                        add_alias(
                            target_stand,
                            alias_from_message,
                        )
                    except ValueError as exc:
                        console.print(
                            f"[yellow]"
                            f"Не удалось сохранить alias "
                            f"{alias_from_message}: {exc}"
                            f"[/yellow]"
                        )

                console.print(
                    f"[green]✓ SSH подключение работает.[/green] "
                    f"Стенд {target_stand} запомнен."
                )

                if alias_from_message:
                    console.print(
                        f"[green]✓ Alias "
                        f"{alias_from_message} → "
                        f"{target_stand} сохранён.[/green]"
                    )

                pending_stand = None

                # Если credentials были ответом на запрос UQA,
                # автоматически продолжаем исходную задачу.
                if pending_request:
                    resumed_request = pending_request
                    pending_request = None

                    messages.append(
                        {
                            "role": "user",
                            "content": resumed_request,
                        }
                    )

                    try:
                        run_turn(messages)
                    except Exception as exc:
                        console.print(
                            f"[red]Ошибка UQA:[/red] {exc}"
                        )

                    continue

                # Credentials могли быть переданы сразу
                # в первом сообщении вместе с задачей.
                safe_request = sanitize_onboarding_message(
                    user_input
                )

                # Если кроме реквизитов в сообщении есть
                # содержательная задача — продолжаем её.
                task_words = (
                    "проверь",
                    "проверить",
                    "регресс",
                    "открой",
                    "найди",
                    "посмотри",
                    "протест",
                    "зайди",
                    "подключ",
                    "cmdb",
                    "backend",
                    "бэкенд",
                    "api",
                )

                if any(
                    word in safe_request.lower()
                    for word in task_words
                ):
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                safe_request
                                + "\n\n"
                                + (
                                    f"SSH-доступ к стенду "
                                    f"{target_stand} сохранён "
                                    f"и успешно проверен."
                                )
                            ),
                        }
                    )

                    try:
                        run_turn(messages)
                    except Exception as exc:
                        console.print(
                            f"[red]Ошибка UQA:[/red] {exc}"
                        )

                continue

            if (
                probe.get("status")
                == "authentication_failed"
            ):
                console.print(
                    "[red]SSH-авторизация не прошла.[/red] "
                    "Проверь логин и пароль и сообщи их ещё раз."
                )

                pending_stand = target_stand
                continue

            console.print(
                "[red]Не удалось подключиться по SSH.[/red] "
                f"{probe.get('error') or probe.get('status')}"
            )

            pending_stand = target_stand
            continue

        # Новый стенд + задача, которой понадобится backend.
        # Не отправляем её модели, пока не получили SSH creds.
        if (
            stand_from_message
            and request_needs_ssh(user_input)
        ):
            stand_info = get_stand(
                stand_from_message
            )

            if not (
                stand_info
                and stand_info.get(
                    "has_ssh_credentials"
                )
            ):
                pending_stand = (
                    stand_from_message
                )

                pending_request = (
                    redact_credentials(
                        user_input
                    )
                )

                console.print(
                    f"[yellow]"
                    f"Для стенда {stand_from_message} "
                    f"я ещё не знаю SSH-логин и пароль. "
                    f"Сообщи их одной строкой: "
                    f"adminacc ********"
                    f"[/yellow]"
                )
                continue

        safe_user_input = redact_credentials(
            user_input
        )

        # Если стенд однозначно известен UQA Core,
        # передаём модели точные безопасные параметры.
        # Никаких паролей здесь нет.
        if current_stand:
            stand_context = build_stand_context(
                current_stand
            )

            if stand_context:
                safe_user_input += stand_context

        job_id = None
        case_id = None

        if request_is_qa_job(user_input):
            stand_identity = None

            if current_stand:
                try:
                    from ssh_worker import (
                        detect_stand_identity,
                    )

                    stand_identity = (
                        detect_stand_identity(
                            current_stand
                        )
                    )
                except Exception as exc:
                    stand_identity = {
                        "status": "unknown",
                        "stand": current_stand,
                        "reason": (
                            "stand_identity_detection_failed"
                        ),
                        "error_type": (
                            type(exc).__name__
                        ),
                    }

            if request_is_regression(
                user_input
            ):
                run_regression_job(
                    original_request=user_input,
                    safe_request=safe_user_input,
                    current_stand=current_stand,
                    stand_identity=stand_identity,
                )

                # Regression cases use isolated contexts.
                # Keep only normal conversation history here.
                compact_completed_history(
                    messages
                )

                continue

            job = create_job(
                request=redact_credentials(
                    user_input
                ),
                stand=current_stand,
                stand_identity=stand_identity,
            )

            job_id = job["job_id"]

            set_job_status(
                job_id,
                "running",
            )

            case = add_test_case(
                job_id,
                title=redact_credentials(
                    user_input
                )[:500],
            )

            case_id = case["case_id"]

            update_test_case(
                job_id,
                case_id,
                status="running",
            )

            console.print(
                f"[dim]Job: {job_id} "
                f"Case: {case_id}[/dim]"
            )

        messages.append(
            {
                "role": "user",
                "content": safe_user_input,
            }
        )

        try:
            run_turn(
                messages,
                job_id=job_id,
                case_id=case_id,
            )
        except httpx.HTTPError as exc:
            console.print(
                f"[red]Ошибка Ollama API:[/red] {exc}"
            )
        except Exception as exc:
            console.print(
                f"[red]Ошибка UQA:[/red] {exc}"
            )


if __name__ == "__main__":
    main()
