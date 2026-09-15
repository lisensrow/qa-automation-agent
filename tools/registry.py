from tools.browser import (
    open_page,
    get_state,
    probe_capabilities,
    inspect_semantic,
    inspect_table_row,
    click_semantic,
    context_menu_semantic,
    fill_semantic,
    set_temporal_semantic,
    select_semantic,
    set_checked_semantic,
    choose_radio_semantic,
    select_many_semantic,
    press_key_semantic,
    copy_value_semantic,
    paste_private_semantic,
    clear_private_clipboard,
    check_focus_order_semantic,
    drag_semantic,
    inspect_order_semantic,
    resize_semantic,
    inspect_table_semantic,
    sort_table_semantic,
    set_table_row_selected,
    table_page_semantic,
    fill_table_filter_semantic,
    apply_table_filter_popover_semantic,
    inspect_table_pagination_semantic,
    set_table_all_selected,
    inspect_bulk_action_semantic,
    get_network_detail,
    delete_json_resource,
    archive_json_resource,
    authenticate_saved_stand,
)

from knowledge_tool import knowledge_search

from ssh_worker import (
    docker_ps,
    docker_logs,
    find_backend_request,
)



TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "browser_probe_capabilities",
            "description": (
                "Read-only снимает fingerprint фактических UI-контрактов "
                "текущей страницы: semantic-name coverage, HTML table/ARIA grid, "
                "select/combobox, Shadow DOM, canvas и доступные adapters. "
                "Используй после навигации и до первого WRITE."
            ),
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "knowledge_search",
            "description": (
                "Ищет релевантные фрагменты во внутренней локальной "
                "документации U-Connect. Используй для уточнения "
                "ожидаемого поведения, API, архитектуры, плагинов, "
                "настроек и процедур. Не считай документацию "
                "доказательством фактического состояния стенда."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Короткий точный поисковый запрос, "
                            "например 'CMDB endpoints name' "
                            "или 'VNC плагин'"
                        )
                    },
                    "limit": {
                        "type": "integer",
                        "description": (
                            "Число фрагментов. Обычно 3, максимум 5."
                        )
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ssh_docker_ps",
            "description": (
                "Получает read-only список запущенных Docker-контейнеров "
                "на указанном стенде через сохранённые SSH credentials. "
                "Не изменяет состояние сервера."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "stand": {
                        "type": "string",
                        "description": (
                            "Имя или hostname стенда, например uc.lab.local"
                        )
                    }
                },
                "required": ["stand"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ssh_find_backend_request",
            "description": (
                "Ищет конкретный HTTP-запрос в backend Docker logs "
                "по method, endpoint и частям query. "
                "Используй этот tool вместо чтения большого массива логов "
                "при корреляции browser XHR с backend. "
                "Возвращает только подходящие строки."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "stand": {
                        "type": "string"
                    },
                    "container": {
                        "type": "string",
                        "description": (
                            "Необязательное имя backend-контейнера. "
                            "Обычно не указывай: UQA попробует определить "
                            "стандартный backend-контейнер сама. "
                            "Передавай только если имя уже точно известно."
                        )
                    },
                    "method": {
                        "type": "string",
                        "description": "Например GET, POST, PUT, DELETE"
                    },
                    "endpoint_contains": {
                        "type": "string",
                        "description": (
                            "Backend endpoint, например "
                            "/api/v1/cmdb/endpoints"
                        )
                    },
                    "query_contains": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": (
                            "Значимые части query, например "
                            "name=host1, limit=50"
                        )
                    },
                    "since": {
                        "type": "string",
                        "description": (
                            "Минимальное временное окно, обычно 1m или 2m"
                        )
                    },
                    "tail": {
                        "type": "integer",
                        "description": "От 1 до 1000"
                    },
                    "max_matches": {
                        "type": "integer",
                        "description": "Максимум совпадений, от 1 до 20"
                    }
                },
                "required": [
                    "stand",
                    "method",
                    "endpoint_contains"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ssh_docker_logs",
            "description": (
                "Читает read-only Docker logs конкретного контейнера "
                "на стенде. Используй только релевантный контейнер и "
                "минимальный разумный временной диапазон. "
                "Не запрашивай логи всех контейнеров без необходимости."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "stand": {
                        "type": "string"
                    },
                    "container": {
                        "type": "string"
                    },
                    "since": {
                        "type": "string",
                        "description": (
                            "Период, например 30s, 2m, 1h"
                        )
                    },
                    "tail": {
                        "type": "integer",
                        "description": (
                            "Максимум строк, от 1 до 1000"
                        )
                    }
                },
                "required": [
                    "stand",
                    "container"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_open_page",
            "description": (
                "Открывает URL в постоянной браузерной сессии Chromium. "
                "Возвращает фактическое состояние страницы и screenshot. "
                "Не преобразуй API endpoint в предполагаемый UI URL. "
                "Если пользователь не дал точный глубокий UI URL, сначала "
                "открой корневой web_url стенда и используй наблюдаемую "
                "семантическую навигацию."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Полный URL страницы"
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_get_state",
            "description": (
                "Получает текущее состояние уже открытой страницы. "
                "Используй только если состояния предыдущего "
                "browser tool недостаточно."
            ),
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_authenticate_saved_stand",
            "description": (
                "Выполняет вход в уже открытую web-форму, используя "
                "зашифрованные credentials стенда внутри UQA Core. "
                "Пароль не передаётся модели, tool arguments или evidence. "
                "Вызывай только когда фактически видны Login/Password и "
                "оператор заранее разрешил повторное использование credentials."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "stand": {
                        "type": "string",
                        "description": "Точный stand_id из UQA Core."
                    }
                },
                "required": ["stand"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_get_network_detail",
            "description": (
                "Возвращает детали одного конкретного fetch/XHR по request_id "
                "вида n16: method, URL, status, безопасные headers, "
                "request body и response body. "
                "Используй только для запросов, которые действительно "
                "нужны для текущей проверки. Не запрашивай детали всех "
                "сетевых запросов без необходимости."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "request_id": {
                        "type": "string",
                        "description": (
                            "request_id из network_requests, например n16"
                        )
                    }
                },
                "required": ["request_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_delete_json_resource",
            "description": (
                "Удаляет ровно один объект из ранее наблюдавшегося JSON REST "
                "collection endpoint. Перед DELETE tool сам выполняет GET, "
                "требует ровно одно точное совпадение exact_name и безопасный "
                "идентификатор id/uid/uuid/external_id, затем повторным GET "
                "проверяет отсутствие. Используй только endpoint, который "
                "UQA Core передал из фактически наблюдавшегося create-request."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "collection_endpoint": {
                        "type": "string",
                        "description": "Точный same-origin endpoint от UQA Core."
                    },
                    "exact_name": {
                        "type": "string",
                        "description": "Точное имя одного ledger resource."
                    }
                },
                "required": ["collection_endpoint", "exact_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_archive_json_resource",
            "description": (
                "Архивирует ровно один объект через универсальную REST "
                "операцию POST <collection>/<id>/archive. Перед действием "
                "требует одно точное совпадение exact_name, после действия "
                "повторным GET проверяет исчезновение из активной коллекции. "
                "Используй только когда UQA Core передал эту операцию из "
                "resource metadata."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "collection_endpoint": {"type": "string"},
                    "exact_name": {"type": "string"}
                },
                "required": ["collection_endpoint", "exact_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_click_semantic",
            "description": (
                "Нажимает видимый элемент по смысловому имени. "
                "Сам определяет accessibility role или использует "
                "явно переданный role для разрешения неоднозначности. "
                "уникальный видимый текст. Для безымянной icon-кнопки можно "
                "передать только точный icon_hint, ранее фактически возвращённый "
                "browser tool. Не нужно использовать element_id."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": (
                            "Имя, видимый текст или ранее наблюдённый "
                            "точный icon_hint элемента"
                        )
                    },
                    "exact": {
                        "type": "boolean",
                        "description": "Точное совпадение, по умолчанию true"
                    },
                    "role": {
                        "type": "string",
                        "enum": [
                            "tab", "button", "link", "menuitem",
                            "option", "checkbox", "radio"
                        ],
                        "description": (
                            "Опциональная accessibility role из фактически "
                            "наблюдённых matches"
                        )
                    },
                    "container": {
                        "type": "string",
                        "description": (
                            "Опциональный точный текст строки/контейнера, "
                            "внутри которого должен находиться элемент"
                        )
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_context_menu_semantic",
            "description": (
                "Открывает контекстное меню правой кнопкой для ровно одного "
                "видимого элемента с точным текстом. Если элемент находится "
                "в таблице, действие применяется ко всей его строке. Само "
                "открытие меню не изменяет данные."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Точное видимое имя ресурса."
                    },
                    "exact": {
                        "type": "boolean",
                        "description": "Должно быть true."
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_fill_semantic",
            "description": (
                "Заполняет обычное несекретное поле по смысловому имени. "
                "Сам ищет поле по accessibility role/name, label, "
                "placeholder или HTML metadata. "
                "Не нужно использовать element_id. "
                "Не использовать для паролей, токенов и секретов."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "field": {
                        "type": "string",
                        "description": (
                            "Имя, label или placeholder поля"
                        )
                    },
                    "text": {
                        "type": "string",
                        "description": "Несекретный текст для ввода"
                    },
                    "exact": {
                        "type": "boolean",
                        "description": "Точное совпадение, по умолчанию true"
                    }
                },
                "required": [
                    "field",
                    "text"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_set_temporal_semantic",
            "description": (
                "Идемпотентно устанавливает canonical HTML value нативного "
                "date/time/datetime-local/month/week поля. До изменения "
                "проверяет формат, min, max и step; после изменения сверяет "
                "фактическое value и validity."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "field": {"type": "string"},
                    "value": {
                        "type": "string",
                        "description": (
                            "Canonical HTML value, например 2026-09-16, "
                            "14:30 или 2026-09-16T14:30."
                        )
                    },
                    "exact": {"type": "boolean"}
                },
                "required": ["field", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_select_semantic",
            "description": (
                "Выбирает ровно один вариант в native select или ARIA combobox "
                "по смысловому имени поля и видимому имени option. "
                "Не угадывает при неоднозначности."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "field": {"type": "string"},
                    "option": {"type": "string"},
                    "exact": {"type": "boolean"}
                },
                "required": ["field", "option"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_set_checked_semantic",
            "description": (
                "Идемпотентно устанавливает checkbox или switch в требуемое "
                "состояние. Уже установленное состояние не переключает."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "field": {"type": "string"},
                    "checked": {"type": "boolean"},
                    "exact": {"type": "boolean"}
                },
                "required": ["field", "checked"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_choose_radio_semantic",
            "description": (
                "Выбирает ровно одну radio option по видимому имени, при "
                "необходимости внутри точной именованной radio group. "
                "Уже выбранную option повторно не переключает."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "option": {"type": "string"},
                    "group": {"type": "string"},
                    "exact": {"type": "boolean"}
                },
                "required": ["option"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_select_many_semantic",
            "description": (
                "Устанавливает точный набор выбранных значений native HTML "
                "multiple select, ARIA multiselect listbox или составного "
                "combobox/listbox с chips. Проверяет все option до изменения "
                "и не выполняет повторную мутацию при правильном наборе."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "field": {"type": "string"},
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1
                    },
                    "exact": {"type": "boolean"}
                },
                "required": ["field", "options"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_press_key_semantic",
            "description": (
                "Нажимает одну разрешённую клавишу, опционально после точного "
                "фокуса на смысловом target. Tab/Shift+Tab/Escape безопасны; "
                "клавиши, способные изменить control или отправить форму, "
                "проходят WRITE/DESTRUCTIVE policy."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "enum": [
                            "Tab", "Shift+Tab", "Escape", "Enter", "Space",
                            "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight",
                            "Home", "End", "PageUp", "PageDown",
                            "Backspace", "Delete", "Control+A", "Control+Z",
                            "Control+Y",
                            "Control+Shift+Z", "Shift+Enter", "Alt+ArrowDown"
                        ]
                    },
                    "target": {"type": "string"},
                    "exact": {"type": "boolean"},
                    "role": {"type": "string"}
                },
                "required": ["key"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_copy_value_semantic",
            "description": (
                "Копирует значение точного несекретного input/textarea или "
                "contenteditable только во временный private clipboard "
                "текущей browser session. Содержимое не возвращается модели, "
                "не сохраняется и не попадает в системный clipboard."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "exact": {"type": "boolean"},
                    "role": {"type": "string"}
                },
                "required": ["source"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_paste_private_semantic",
            "description": (
                "Вставляет private clipboard в точное несекретное редактируемое "
                "поле без чтения или записи системного clipboard. Это WRITE."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string"},
                    "replace": {"type": "boolean"},
                    "exact": {"type": "boolean"},
                    "role": {"type": "string"}
                },
                "required": ["target"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_clear_private_clipboard",
            "description": "Очищает временный private clipboard browser session.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_check_focus_order_semantic",
            "description": (
                "Read-only по данным проверка ожидаемого forward Tab order. "
                "Фокусирует первый точный target, проходит Tab и возвращает "
                "полную наблюдаемую последовательность и первое расхождение."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "targets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 2,
                        "maxItems": 50
                    },
                    "exact": {"type": "boolean"}
                },
                "required": ["targets"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_inspect_order_semantic",
            "description": (
                "Read-only возвращает фактический порядок верхнеуровневых "
                "semantic items внутри точного container и при необходимости "
                "сравнивает его с exact order или subsequence."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "container": {"type": "string"},
                    "expected_order": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 2,
                        "maxItems": 100
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["exact", "subsequence"]
                    },
                    "exact": {"type": "boolean"},
                    "role": {"type": "string"}
                },
                "required": ["container"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_drag_semantic",
            "description": (
                "Перетаскивает ровно один видимый semantic source на ровно "
                "один semantic target. Используется для порядка полей, строк, "
                "карточек и других drag-and-drop интерфейсов. При переданном "
                "expected_order проверяет фактический порядок после действия."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "exact": {"type": "boolean"},
                    "source_role": {"type": "string"},
                    "target_role": {"type": "string"},
                    "order_container": {"type": "string"},
                    "expected_order": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 2,
                        "maxItems": 100
                    },
                    "order_mode": {
                        "type": "string",
                        "enum": ["exact", "subsequence"]
                    },
                    "container_role": {"type": "string"}
                },
                "required": ["source", "target"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_resize_semantic",
            "description": (
                "Изменяет размер ровно одного semantic target перетаскиванием "
                "правой, нижней или нижней-правой границы. Проверяет фактическое "
                "изменение bounding box после действия."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string"},
                    "delta_x": {
                        "type": "integer",
                        "minimum": -1000,
                        "maximum": 1000
                    },
                    "delta_y": {
                        "type": "integer",
                        "minimum": -1000,
                        "maximum": 1000
                    },
                    "edge": {
                        "type": "string",
                        "enum": ["right", "bottom", "bottom-right"]
                    },
                    "exact": {"type": "boolean"},
                    "role": {"type": "string"}
                },
                "required": ["target"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_inspect_table_semantic",
            "description": (
                "Read-only структурированный снимок одной видимой таблицы: "
                "headers, aria-sort, строки, cells и values_by_header."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "table": {"type": "string"},
                    "exact": {"type": "boolean"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_sort_table_semantic",
            "description": (
                "Сортирует одну таблицу по точному column header и направлению. "
                "Проверяет aria-sort либо фактическое изменение порядка строк."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "column": {"type": "string"},
                    "direction": {
                        "type": "string",
                        "enum": ["asc", "desc", "ascending", "descending"]
                    },
                    "table": {"type": "string"},
                    "exact": {"type": "boolean"}
                },
                "required": ["column", "direction"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_set_table_row_selected",
            "description": (
                "Идемпотентно устанавливает checkbox выбора ровно одной строки, "
                "найденной по точному значению ячейки внутри одной таблицы. "
                "Возвращает устойчивый ключ таблицы для cross-page ledger и "
                "не запускает bulk action."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "selected": {"type": "boolean"},
                    "exact": {"type": "boolean"},
                    "table": {
                        "type": "string",
                        "description": (
                            "Точное доступное имя таблицы. Обязательно при "
                            "наличии нескольких видимых таблиц."
                        )
                    }
                },
                "required": ["name", "selected"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_table_page_semantic",
            "description": (
                "Активирует точный pagination control и проверяет, что набор "
                "видимых строк выбранной таблицы действительно изменился."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "control": {"type": "string"},
                    "table": {"type": "string"},
                    "exact": {"type": "boolean"}
                },
                "required": ["control"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_fill_table_filter_semantic",
            "description": (
                "Заполняет единственный filter control точной колонки таблицы "
                "и возвращает строки до/после. Это фильтрация, а не изменение "
                "данных сущностей."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "column": {"type": "string"},
                    "text": {"type": "string"},
                    "table": {"type": "string"},
                    "exact": {"type": "boolean"}
                },
                "required": ["column", "text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_apply_table_filter_popover_semantic",
            "description": (
                "Открывает единственный filter popover точной колонки, "
                "опционально выбирает точный native operator, заполняет "
                "единственное value field и нажимает точную Apply-кнопку. "
                "Возвращает rows before/after без изменения данных сущностей."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "column": {"type": "string"},
                    "value": {"type": "string"},
                    "table": {"type": "string"},
                    "trigger": {"type": "string"},
                    "operator": {"type": "string"},
                    "apply_button": {"type": "string"},
                    "exact": {"type": "boolean"}
                },
                "required": ["column", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_inspect_table_pagination_semantic",
            "description": (
                "Read-only возвращает visible row count, server-side total, "
                "видимый диапазон, current page и состояния pagination controls."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "table": {"type": "string"},
                    "exact": {"type": "boolean"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_set_table_all_selected",
            "description": (
                "Идемпотентно устанавливает header select-all checkbox и "
                "проверяет состояние всех видимых row checkboxes. Не нажимает "
                "и не подтверждает bulk action."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "selected": {"type": "boolean"},
                    "table": {"type": "string"},
                    "exact": {"type": "boolean"}
                },
                "required": ["selected"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_inspect_bulk_action_semantic",
            "description": (
                "Read-only проверяет наличие и enabled/disabled состояние "
                "точной bulk-action кнопки, а также число выбранных строк. "
                "Никогда не активирует действие."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "table": {"type": "string"},
                    "exact": {"type": "boolean"},
                    "role": {"type": "string"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_inspect_table_row",
            "description": (
                "Read-only проверка одной видимой строки таблицы. При exact=true "
                "требует ровно одну строку, содержащую ячейку с точным значением "
                "name, и возвращает cells, headers и values_by_header. Используй "
                "для проверки созданной записи вместо предположения ARIA role."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Точное видимое значение одной ячейки строки",
                    },
                    "exact": {
                        "type": "boolean",
                        "description": "Точное совпадение ячейки, по умолчанию true",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_inspect_semantic",
            "description": (
                "Read-only проверка фактического состояния "
                "элемента интерфейса без клика. Возвращает "
                "visible/enabled/disabled, metadata и screenshot. "
                "Используй для проверки наличия и доступности "
                "кнопок, ссылок и других элементов. При неоднозначности "
                "можно передать фактически наблюдённый role. Если DOM "
                "не подтвердит role, runtime продолжит строгий поиск по "
                "имени и явно отметит semantic_role_fallback."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": (
                            "Видимое или accessibility-имя элемента"
                            " либо ранее наблюдённый точный icon_hint"
                        )
                    },
                    "exact": {
                        "type": "boolean",
                        "description": (
                            "Точное совпадение, по умолчанию true"
                        )
                    },
                    "role": {
                        "type": "string",
                        "enum": [
                            "tab", "button", "link", "menuitem", "option",
                            "checkbox", "radio", "textbox", "searchbox",
                            "combobox"
                        ],
                        "description": (
                            "Опциональная accessibility role из фактически "
                            "наблюдённых matches; это сужающий hint, а не "
                            "самостоятельное доказательство"
                        )
                    }
                },
                "required": ["name"]
            }
        }
    }
]


# These mutation tools remain executable by the trusted runtime, but are not
# advertised to the normal QA agent.  UQA exposes them only to Cleanup Manager
# after it has resolved one exact resource from the persistent ledger.
_CLEANUP_ONLY_TOOL_NAMES = {
    "browser_delete_json_resource",
    "browser_archive_json_resource",
}
CLEANUP_ONLY_TOOLS = [
    item
    for item in TOOLS
    if item.get("function", {}).get("name")
    in _CLEANUP_ONLY_TOOL_NAMES
]
TOOLS = [
    item
    for item in TOOLS
    if item.get("function", {}).get("name")
    not in _CLEANUP_ONLY_TOOL_NAMES
]


def execute_tool(name: str, arguments: dict):
    if name == "knowledge_search":
        return knowledge_search(
            query=arguments["query"],
            limit=arguments.get("limit", 3),
        )

    if name == "ssh_docker_ps":
        return docker_ps(
            arguments["stand"]
        )

    if name == "ssh_find_backend_request":
        def _run_backend_search(container_name):
            return find_backend_request(
                stand=arguments["stand"],
                container=container_name,
                method=arguments["method"],
                endpoint_contains=arguments["endpoint_contains"],
                query_contains=arguments.get("query_contains", []),
                since=arguments.get("since", "2m"),
                tail=arguments.get("tail", 500),
                max_matches=arguments.get("max_matches", 10),
            )

        # Если контейнер уже точно известен,
        # используем его без автоподбора.
        explicit_container = (
            arguments.get("container")
            or ""
        ).strip()

        if explicit_container:
            return _run_backend_search(
                explicit_container
            )

        # Стандартные варианты имени backend
        # в U-Connect.
        candidates = (
            "u_backend",
            "u-backend",
        )

        attempts = []

        for candidate in candidates:
            result = _run_backend_search(
                candidate
            )

            if result.get("status") == "ok":
                result["container_autodetected"] = (
                    candidate
                )
                return result

            attempts.append(
                {
                    "container": candidate,
                    "status": result.get(
                        "status"
                    ),
                }
            )

        return {
            "status": "backend_container_not_found",
            "stand": arguments["stand"],
            "attempts": attempts,
            "hint": (
                "Call ssh_docker_ps to discover the "
                "actual backend container name, then "
                "retry ssh_find_backend_request with "
                "container explicitly."
            ),
        }

    if name == "ssh_docker_logs":
        return docker_logs(
            stand=arguments["stand"],
            container=arguments["container"],
            since=arguments.get("since", "2m"),
            tail=arguments.get("tail", 200),
        )

    if name == "browser_open_page":
        return open_page(arguments["url"])

    if name == "browser_get_state":
        return get_state()

    if name == "browser_probe_capabilities":
        return probe_capabilities()

    if name == "browser_authenticate_saved_stand":
        return authenticate_saved_stand(
            arguments["stand"]
        )

    if name == "browser_get_network_detail":
        return get_network_detail(
            arguments["request_id"]
        )

    if name == "browser_delete_json_resource":
        return delete_json_resource(
            arguments["collection_endpoint"],
            arguments["exact_name"],
        )

    if name == "browser_archive_json_resource":
        return archive_json_resource(
            arguments["collection_endpoint"],
            arguments["exact_name"],
        )

    if name == "browser_inspect_semantic":
        return inspect_semantic(
            arguments["name"],
            arguments.get("exact", True),
            arguments.get("role"),
        )

    if name == "browser_inspect_table_row":
        return inspect_table_row(
            arguments["name"],
            arguments.get("exact", True),
        )

    if name == "browser_click_semantic":
        return click_semantic(
            arguments["name"],
            arguments.get("exact", True),
            arguments.get("role"),
            arguments.get("container"),
        )

    if name == "browser_context_menu_semantic":
        return context_menu_semantic(
            arguments["name"],
            arguments.get("exact", True),
        )

    if name == "browser_fill_semantic":
        return fill_semantic(
            arguments["field"],
            arguments["text"],
            arguments.get("exact", True),
        )

    if name == "browser_set_temporal_semantic":
        return set_temporal_semantic(
            arguments["field"],
            arguments["value"],
            arguments.get("exact", True),
        )

    if name == "browser_select_semantic":
        return select_semantic(
            arguments["field"],
            arguments["option"],
            arguments.get("exact", True),
        )

    if name == "browser_set_checked_semantic":
        return set_checked_semantic(
            arguments["field"],
            arguments["checked"],
            arguments.get("exact", True),
        )

    if name == "browser_choose_radio_semantic":
        return choose_radio_semantic(
            arguments["option"],
            arguments.get("group"),
            arguments.get("exact", True),
        )

    if name == "browser_select_many_semantic":
        return select_many_semantic(
            arguments["field"],
            arguments["options"],
            arguments.get("exact", True),
        )

    if name == "browser_press_key_semantic":
        return press_key_semantic(
            arguments["key"],
            arguments.get("target"),
            arguments.get("exact", True),
            arguments.get("role"),
        )

    if name == "browser_copy_value_semantic":
        return copy_value_semantic(
            arguments["source"],
            arguments.get("exact", True),
            arguments.get("role"),
        )

    if name == "browser_paste_private_semantic":
        return paste_private_semantic(
            arguments["target"],
            arguments.get("replace", False),
            arguments.get("exact", True),
            arguments.get("role"),
        )

    if name == "browser_clear_private_clipboard":
        return clear_private_clipboard()

    if name == "browser_check_focus_order_semantic":
        return check_focus_order_semantic(
            arguments["targets"],
            arguments.get("exact", True),
        )

    if name == "browser_drag_semantic":
        return drag_semantic(
            arguments["source"],
            arguments["target"],
            arguments.get("exact", True),
            arguments.get("source_role"),
            arguments.get("target_role"),
            arguments.get("order_container"),
            arguments.get("expected_order"),
            arguments.get("order_mode", "exact"),
            arguments.get("container_role"),
        )

    if name == "browser_inspect_order_semantic":
        return inspect_order_semantic(
            arguments["container"],
            arguments.get("expected_order"),
            arguments.get("mode", "exact"),
            arguments.get("exact", True),
            arguments.get("role"),
        )

    if name == "browser_resize_semantic":
        return resize_semantic(
            arguments["target"],
            arguments.get("delta_x", 0),
            arguments.get("delta_y", 0),
            arguments.get("edge", "right"),
            arguments.get("exact", True),
            arguments.get("role"),
        )

    if name == "browser_inspect_table_semantic":
        return inspect_table_semantic(
            arguments.get("table"),
            arguments.get("exact", True),
        )

    if name == "browser_sort_table_semantic":
        return sort_table_semantic(
            arguments["column"],
            arguments["direction"],
            arguments.get("table"),
            arguments.get("exact", True),
        )

    if name == "browser_set_table_row_selected":
        return set_table_row_selected(
            arguments["name"],
            arguments["selected"],
            arguments.get("exact", True),
            arguments.get("table"),
        )

    if name == "browser_table_page_semantic":
        return table_page_semantic(
            arguments["control"],
            arguments.get("table"),
            arguments.get("exact", True),
        )

    if name == "browser_fill_table_filter_semantic":
        return fill_table_filter_semantic(
            arguments["column"],
            arguments["text"],
            arguments.get("table"),
            arguments.get("exact", True),
        )

    if name == "browser_apply_table_filter_popover_semantic":
        return apply_table_filter_popover_semantic(
            arguments["column"],
            arguments["value"],
            arguments.get("table"),
            arguments.get("trigger"),
            arguments.get("operator"),
            arguments.get("apply_button"),
            arguments.get("exact", True),
        )

    if name == "browser_inspect_table_pagination_semantic":
        return inspect_table_pagination_semantic(
            arguments.get("table"),
            arguments.get("exact", True),
        )

    if name == "browser_set_table_all_selected":
        return set_table_all_selected(
            arguments["selected"],
            arguments.get("table"),
            arguments.get("exact", True),
        )

    if name == "browser_inspect_bulk_action_semantic":
        return inspect_bulk_action_semantic(
            arguments["name"],
            arguments.get("table"),
            arguments.get("exact", True),
            arguments.get("role"),
        )

    return {
        "error": f"Unknown tool: {name}"
    }
