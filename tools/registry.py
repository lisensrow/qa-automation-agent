from tools.browser import (
    open_page,
    get_state,
    set_viewport_semantic,
    inspect_accessibility_semantic,
    probe_capabilities,
    inspect_semantic,
    inspect_agent_telemetry_semantic,
    inspect_agent_plugins_semantic,
    inspect_agent_tasks_semantic,
    inspect_agent_task_result_semantic,
    open_agent_tasks_semantic,
    create_managed_agent_task_semantic,
    inspect_managed_agent_task_result_semantic,
    disable_agent_task_semantic,
    inspect_table_row,
    click_semantic,
    download_semantic,
    verify_download_structure_semantic,
    inspect_new_tab_semantic,
    navigate_history_semantic,
    inspect_iframe_semantic,
    observe_iframe_surface_change_semantic,
    click_iframe_surface_semantic,
    press_iframe_surface_key_semantic,
    inspect_hover_tooltip_semantic,
    handle_native_dialog_semantic,
    inspect_form_validation_semantic,
    inspect_loading_state_semantic,
    inspect_notification_lifecycle_semantic,
    inspect_aria_field_errors_semantic,
    inspect_control_state_lifecycle_semantic,
    track_form_dirty_state_semantic,
    inspect_tabs_contract_semantic,
    inspect_disclosure_contract_semantic,
    inspect_dialog_focus_trap_semantic,
    inspect_heading_structure_semantic,
    inspect_landmark_structure_semantic,
    inspect_link_contracts_semantic,
    context_menu_semantic,
    fill_semantic,
    inspect_file_input_semantic,
    set_upload_fixture_semantic,
    set_temporal_semantic,
    set_slider_semantic,
    inspect_tree_semantic,
    set_tree_item_expanded,
    set_tree_item_selected,
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
    inspect_popover_semantic,
    open_popover_semantic,
    select_popover_option_semantic,
    click_popover_button_semantic,
    close_popover_semantic,
    inspect_calendar_semantic,
    open_calendar_semantic,
    select_calendar_option_semantic,
    inspect_time_picker_semantic,
    open_time_picker_semantic,
    select_time_picker_option_semantic,
    inspect_dialog_semantic,
    click_dialog_button_semantic,
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
            "name": "browser_set_viewport_semantic",
            "description": (
                "Переключает только размер тестового браузера на фиксированный "
                "responsive-профиль и возвращает screenshot, точные размеры "
                "viewport/document и horizontal_overflow. Не изменяет данные "
                "продукта и не принимает произвольные размеры."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "profile": {
                        "type": "string",
                        "enum": ["mobile", "tablet", "desktop"],
                    }
                },
                "required": ["profile"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_inspect_accessibility_semantic",
            "description": (
                "Read-only DOM accessibility audit текущей страницы: "
                "безымянные видимые controls, изображения без alt, duplicate "
                "id и broken aria-labelledby/aria-describedby/aria-controls. "
                "Возвращает машинный accessibility_passed и screenshot."
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
            "name": "browser_verify_download_structure_semantic",
            "description": (
                "Read-only проверяет только download_id, выданный этой браузерной "
                "сессией: CSV — точные заголовки и диапазон строк, PDF — число "
                "страниц, JSON — top-level type, обязательные ключи и диапазон "
                "числа элементов, PNG/JPEG — точные размеры изображения. "
                "Содержимое файла не возвращается."
            ),
            "parameters": {"type": "object", "properties": {
                "download_id": {"type": "string"},
                "format": {
                    "type": "string",
                    "enum": ["csv", "pdf", "json", "png", "jpeg"]
                },
                "expected_headers": {
                    "type": "array", "items": {"type": "string"}
                },
                "min_rows": {"type": "integer"},
                "max_rows": {"type": "integer"},
                "expected_pages": {"type": "integer"},
                "expected_json_type": {
                    "type": "string", "enum": ["object", "array"]
                },
                "required_keys": {
                    "type": "array", "items": {"type": "string"}
                },
                "min_items": {"type": "integer"},
                "max_items": {"type": "integer"},
                "expected_width": {"type": "integer"},
                "expected_height": {"type": "integer"}
            }, "required": ["download_id", "format"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_inspect_new_tab_semantic",
            "description": (
                "INTERACT: открывает одну точную видимую HTTP(S)-ссылку с "
                "target=_blank, проверяет ожидаемый URL/title/text preview, "
                "закрывает дочернюю вкладку и подтверждает возврат в исходный "
                "browser context. Origin ссылки обязан совпадать с явно "
                "переданным expected_url_prefix; query/fragment в ожидании "
                "запрещены."
            ),
            "parameters": {"type": "object", "properties": {
                "name": {"type": "string"},
                "expected_url_prefix": {"type": "string"},
                "exact": {"type": "boolean"}
            }, "required": ["name", "expected_url_prefix"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_navigate_history_semantic",
            "description": (
                "INTERACT: выполняет ровно один шаг browser Back или Forward "
                "и проверяет ожидаемый URL. Разрешена только same-origin "
                "навигация HTTP(S); query/fragment в expected prefix запрещены. "
                "После шага используй semantic inspectors для проверки "
                "восстановленного состояния формы или страницы."
            ),
            "parameters": {"type": "object", "properties": {
                "direction": {"type": "string", "enum": ["back", "forward"]},
                "expected_url_prefix": {"type": "string"}
            }, "required": ["direction", "expected_url_prefix"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_inspect_iframe_semantic",
            "description": (
                "Read-only проверяет один видимый iframe по точному title, "
                "aria-label или name. Требует ожидаемый HTTP(S) URL prefix, "
                "сверяет origin и возвращает title/text preview и число "
                "интерактивных элементов frame, а также canvas/video metrics "
                "и surface_ready для VNC/preview, не меняя top-level context."
            ),
            "parameters": {"type": "object", "properties": {
                "name": {"type": "string"},
                "expected_url_prefix": {"type": "string"},
                "exact": {"type": "boolean"}
            }, "required": ["name", "expected_url_prefix"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_observe_iframe_surface_change_semantic",
            "description": (
                "Read-only делает два приватных screenshot точного iframe с "
                "ограниченной паузой и сравнивает SHA-256, не возвращая pixels. "
                "Проверяет ожидаемое наличие или отсутствие изменения кадра; "
                "используй для VNC/video только после iframe inspection."
            ),
            "parameters": {"type": "object", "properties": {
                "name": {"type": "string"},
                "expected_url_prefix": {"type": "string"},
                "expect_change": {"type": "boolean"},
                "wait_ms": {"type": "integer", "minimum": 100, "maximum": 5000},
                "exact": {"type": "boolean"}
            }, "required": ["name", "expected_url_prefix", "expect_change"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_click_iframe_surface_semantic",
            "description": (
                "WRITE: после подтверждённого iframe surface кликает одну "
                "нормализованную координату внутри frame и сравнивает private "
                "before/after screenshot hashes. На реальном VNC требует v069 "
                "confirmation; изменение кадра не доказывает правильность "
                "бизнес-результата."
            ),
            "parameters": {"type": "object", "properties": {
                "name": {"type": "string"},
                "expected_url_prefix": {"type": "string"},
                "x_ratio": {"type": "number", "minimum": 0, "maximum": 1},
                "y_ratio": {"type": "number", "minimum": 0, "maximum": 1},
                "expect_change": {"type": "boolean"},
                "wait_ms": {"type": "integer", "minimum": 100, "maximum": 5000},
                "exact": {"type": "boolean"}
            }, "required": [
                "name", "expected_url_prefix", "x_ratio", "y_ratio",
                "expect_change"
            ]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_press_iframe_surface_key_semantic",
            "description": (
                "WRITE: фокусирует подтверждённую iframe surface точечным "
                "кликом, затем отправляет одну allowlisted служебную клавишу "
                "без произвольного текста и проверяет private before/after "
                "hashes. Всегда требует v069 confirmation."
            ),
            "parameters": {"type": "object", "properties": {
                "name": {"type": "string"},
                "expected_url_prefix": {"type": "string"},
                "key": {"type": "string"},
                "x_ratio": {"type": "number", "minimum": 0, "maximum": 1},
                "y_ratio": {"type": "number", "minimum": 0, "maximum": 1},
                "expect_change": {"type": "boolean"},
                "focus_expect_change": {"type": "boolean"},
                "wait_ms": {"type": "integer", "minimum": 100, "maximum": 5000},
                "exact": {"type": "boolean"}
            }, "required": [
                "name", "expected_url_prefix", "key", "x_ratio", "y_ratio",
                "expect_change"
            ]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_inspect_hover_tooltip_semantic",
            "description": (
                "INTERACT: наводит курсор на один точный semantic element, "
                "проверяет появление одного конкретного role=tooltip, фиксирует "
                "его текст и доказывает исчезновение после ухода курсора."
            ),
            "parameters": {"type": "object", "properties": {
                "target": {"type": "string"},
                "target_role": {"type": "string", "enum": [
                    "button", "link", "img", "checkbox", "radio",
                    "textbox", "combobox", "tab", "menuitem"
                ]},
                "expected_tooltip": {"type": "string"},
                "exact": {"type": "boolean"}
            }, "required": ["target", "target_role", "expected_tooltip"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_handle_native_dialog_semantic",
            "description": "Обрабатывает один ожидаемый native alert/confirm/prompt. Несовпавший type/message всегда dismiss. Accept проходит v069 policy как WRITE/DESTRUCTIVE; prompt text не возвращается.",
            "parameters": {"type": "object", "properties": {
                "target": {"type": "string"},
                "expected_type": {"type": "string", "enum": ["alert", "confirm", "prompt", "beforeunload"]},
                "expected_message": {"type": "string"},
                "decision": {"type": "string", "enum": ["accept", "dismiss"]},
                "prompt_text": {"type": "string"},
                "exact": {"type": "boolean"}
            }, "required": ["target", "expected_type", "expected_message", "decision"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_inspect_form_validation_semantic",
            "description": "Read-only audit native form validation без Submit и без возврата values: invalid controls и причины required/type/pattern/range/custom validity.",
            "parameters": {"type": "object", "properties": {
                "form": {"type": "string"}, "exact": {"type": "boolean"}
            }}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_inspect_loading_state_semantic",
            "description": "Read-only проверяет ARIA loading lifecycle в точном scope: aria-busy/role=progressbar, ожидание busy или ready и опционально доказанный переход busy→ready.",
            "parameters": {"type": "object", "properties": {
                "scope": {"type": "string"},
                "expected_state": {"type": "string", "enum": ["busy", "ready"]},
                "wait_ms": {"type": "integer", "minimum": 0, "maximum": 10000},
                "require_transition": {"type": "boolean"},
                "exact": {"type": "boolean"}
            }}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_inspect_notification_lifecycle_semantic",
            "description": "Read-only ожидает одно точное ARIA-уведомление role=alert/status или доказывает его появление и последующее исчезновение за ограниченное время.",
            "parameters": {"type": "object", "properties": {
                "expected_text": {"type": "string"},
                "role": {"type": "string", "enum": ["alert", "status"]},
                "expected_state": {"type": "string", "enum": ["visible", "dismissed"]},
                "wait_ms": {"type": "integer", "minimum": 0, "maximum": 10000},
                "require_seen": {"type": "boolean"},
                "exact": {"type": "boolean"}
            }, "required": ["expected_text"]}
        }
    },
    {"type":"function","function":{"name":"browser_inspect_aria_field_errors_semantic","description":"Read-only audit aria-invalid и связанных aria-errormessage/aria-describedby без значений полей.","parameters":{"type":"object","properties":{"form":{"type":"string"},"exact":{"type":"boolean"}}}}},
    {"type":"function","function":{"name":"browser_inspect_control_state_lifecycle_semantic","description":"Read-only ожидает состояние одного exact semantic control: visible/hidden/enabled/disabled/checked/unchecked.","parameters":{"type":"object","properties":{"target":{"type":"string"},"role":{"type":"string","enum":["button","link","textbox","combobox","checkbox","radio","switch","tab","menuitem"]},"expected_state":{"type":"string","enum":["visible","hidden","enabled","disabled","checked","unchecked"]},"wait_ms":{"type":"integer","minimum":0,"maximum":10000},"require_seen":{"type":"boolean"},"exact":{"type":"boolean"}},"required":["target","role","expected_state"]}}},
    {"type":"function","function":{"name":"browser_track_form_dirty_state_semantic","description":"Хранит приватный SHA-256 baseline формы и сообщает только dirty/clean; значения полей модели не возвращаются.","parameters":{"type":"object","properties":{"form":{"type":"string"},"operation":{"type":"string","enum":["capture","compare","clear"]},"exact":{"type":"boolean"}},"required":["form"]}}},
    {"type":"function","function":{"name":"browser_inspect_tabs_contract_semantic","description":"Read-only audit одного ARIA tablist: ровно один selected tab, aria-controls и видимая связанная panel.","parameters":{"type":"object","properties":{"tablist":{"type":"string"},"exact":{"type":"boolean"}}}}},
    {"type":"function","function":{"name":"browser_inspect_disclosure_contract_semantic","description":"Read-only проверяет согласованность aria-expanded, aria-controls и видимости controlled panel.","parameters":{"type":"object","properties":{"target":{"type":"string"},"exact":{"type":"boolean"}},"required":["target"]}}},
    {"type":"function","function":{"name":"browser_inspect_dialog_focus_trap_semantic","description":"Проверяет Tab focus trap внутри exact dialog; меняет только фокус, не данные продукта.","parameters":{"type":"object","properties":{"dialog":{"type":"string"},"cycles":{"type":"integer","minimum":1,"maximum":5},"exact":{"type":"boolean"}},"required":["dialog"]}}},
    {"type":"function","function":{"name":"browser_inspect_heading_structure_semantic","description":"Read-only audit видимой heading hierarchy: уровни, пустые имена, пропуски уровней и число h1.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_landmark_structure_semantic","description":"Read-only audit main/navigation/banner/contentinfo/complementary/region и уникальности labels.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_link_contracts_semantic","description":"Read-only audit видимых links: accessible name, безопасная URL scheme и rel для target=_blank; URL очищаются от секретов.","parameters":{"type":"object","properties":{}}}},
    {
        "type": "function",
        "function": {
            "name": "browser_download_semantic",
            "description": (
                "Нажимает единственную точную button/link и ждёт download. "
                "Сохраняет файл приватно (до 10 MiB), проверяет имя, сигнатуру "
                "формата и опциональный SHA-256 без возврата содержимого. "
                "Без expected_sha256 результат только metadata_only, не PASS. "
                "Действие проходит WRITE/DESTRUCTIVE policy."
            ),
            "parameters": {"type": "object", "properties": {
                "name": {"type": "string"},
                "expected_filename": {"type": "string"},
                "expected_format": {
                    "type": "string", "enum": ["text", "pdf", "png", "jpeg"]
                },
                "expected_sha256": {"type": "string"},
                "exact": {"type": "boolean"}
            }, "required": ["name", "expected_filename"]}
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
            "name": "browser_inspect_file_input_semantic",
            "description": (
                "Read-only проверяет единственное file-поле по видимой метке: "
                "accept, multiple и число выбранных файлов без содержимого."
            ),
            "parameters": {"type": "object", "properties": {
                "field": {"type": "string"},
                "exact": {"type": "boolean"}
            }, "required": ["field"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_set_upload_fixture_semantic",
            "description": (
                "Выбирает встроенный безопасный fixture sample-text в точном "
                "file-поле. Не принимает путь к файлу. Это WRITE: change может "
                "сразу запустить upload; успех на backend проверяй отдельно."
            ),
            "parameters": {"type": "object", "properties": {
                "field": {"type": "string"},
                "fixture": {"type": "string", "enum": ["sample-text"]},
                "exact": {"type": "boolean"}
            }, "required": ["field", "fixture"]}
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
            "name": "browser_set_slider_semantic",
            "description": (
                "Идемпотентно устанавливает точное значение native range или "
                "ARIA slider. Проверяет min/max/step, использует ограниченное "
                "число keyboard steps и сверяет фактическое значение."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "field": {"type": "string"},
                    "value": {"type": "number"},
                    "exact": {"type": "boolean"}
                },
                "required": ["field", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_inspect_tree_semantic",
            "description": (
                "Read-only снимок одной точной ARIA tree: видимые items, "
                "levels, expanded, selected, checked и disabled states."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tree": {"type": "string"},
                    "exact": {"type": "boolean"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_set_tree_item_expanded",
            "description": (
                "Идемпотентно раскрывает или сворачивает один точный ARIA "
                "treeitem стандартной Arrow-клавишей и проверяет aria-expanded."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "item": {"type": "string"},
                    "expanded": {"type": "boolean"},
                    "tree": {"type": "string"},
                    "exact": {"type": "boolean"}
                },
                "required": ["item", "expanded"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_set_tree_item_selected",
            "description": (
                "Идемпотентно устанавливает selected state одного точного "
                "treeitem только при явном aria-selected или aria-checked. "
                "Использует Space и проверяет итоговое состояние; не сохраняет форму."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "item": {"type": "string"},
                    "selected": {"type": "boolean"},
                    "tree": {"type": "string"},
                    "exact": {"type": "boolean"}
                },
                "required": ["item", "selected"]
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
            "name": "browser_inspect_popover_semantic",
            "description": "Read-only снимок открытого popup, связанного с точной кнопкой через aria-controls.",
            "parameters": {"type": "object", "properties": {
                "trigger": {"type": "string"}, "exact": {"type": "boolean"}
            }, "required": ["trigger"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_open_popover_semantic",
            "description": "Открывает однозначный aria-controls popup по точной кнопке без Apply/Save.",
            "parameters": {"type": "object", "properties": {
                "trigger": {"type": "string"}, "exact": {"type": "boolean"}
            }, "required": ["trigger"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_close_popover_semantic",
            "description": "Закрывает однозначный popup клавишей Escape и проверяет исчезновение без Apply/Save.",
            "parameters": {"type": "object", "properties": {
                "trigger": {"type": "string"}, "exact": {"type": "boolean"}
            }, "required": ["trigger"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_inspect_calendar_semantic",
            "description": (
                "Read-only снимок уже открытого ARIA calendar overlay. "
                "Требует точный trigger с aria-controls и фактический role=grid; "
                "возвращает наблюдаемые date options без угадывания локали."
            ),
            "parameters": {"type": "object", "properties": {
                "trigger": {"type": "string"},
                "exact": {"type": "boolean"}
            }, "required": ["trigger"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_open_calendar_semantic",
            "description": (
                "Открывает точный calendar trigger с aria-controls и "
                "fail-closed проверяет наличие ARIA grid и наблюдаемых дат."
            ),
            "parameters": {"type": "object", "properties": {
                "trigger": {"type": "string"},
                "exact": {"type": "boolean"}
            }, "required": ["trigger"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_select_calendar_option_semantic",
            "description": (
                "WRITE: выбирает только одну точную дату, ранее наблюдаемую "
                "в открытом ARIA calendar. Проверяет selected state, изменение "
                "trigger либо штатное закрытие overlay."
            ),
            "parameters": {"type": "object", "properties": {
                "trigger": {"type": "string"},
                "option": {"type": "string"},
                "exact": {"type": "boolean"}
            }, "required": ["trigger", "option"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_inspect_time_picker_semantic",
            "description": (
                "Read-only снимок уже открытого ARIA time-picker. Требует "
                "точный trigger с aria-controls и role=listbox; возвращает "
                "наблюдаемые time options без угадывания формата или локали."
            ),
            "parameters": {"type": "object", "properties": {
                "trigger": {"type": "string"},
                "exact": {"type": "boolean"}
            }, "required": ["trigger"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_open_time_picker_semantic",
            "description": (
                "Открывает точный time-picker trigger с aria-controls и "
                "fail-closed проверяет наличие ARIA listbox."
            ),
            "parameters": {"type": "object", "properties": {
                "trigger": {"type": "string"},
                "exact": {"type": "boolean"}
            }, "required": ["trigger"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_select_time_picker_option_semantic",
            "description": (
                "WRITE: выбирает одну точную, ранее наблюдаемую time option "
                "и проверяет selected state, изменение trigger либо штатное "
                "закрытие overlay."
            ),
            "parameters": {"type": "object", "properties": {
                "trigger": {"type": "string"},
                "option": {"type": "string"},
                "exact": {"type": "boolean"}
            }, "required": ["trigger", "option"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_inspect_dialog_semantic",
            "description": (
                "Read-only снимок одного точного видимого dialog/alertdialog: "
                "активный wizard step, scoped buttons и число полей. Не "
                "смешивает одноимённые controls вне модального окна."
            ),
            "parameters": {"type": "object", "properties": {
                "dialog": {"type": "string"},
                "exact": {"type": "boolean"}
            }, "required": ["dialog"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_click_dialog_button_semantic",
            "description": (
                "Нажимает одну точную кнопку только внутри одного точного "
                "видимого dialog/alertdialog и проверяет смену active step "
                "или закрытие окна. Класс действия определяется именем кнопки."
            ),
            "parameters": {"type": "object", "properties": {
                "dialog": {"type": "string"},
                "button": {"type": "string"},
                "exact": {"type": "boolean"}
            }, "required": ["dialog", "button"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_select_popover_option_semantic",
            "description": (
                "Выбирает единственную точную role=option с явным aria-selected "
                "в уже открытом aria-controls popup. Это WRITE; Apply/Save отдельно."
            ),
            "parameters": {"type": "object", "properties": {
                "trigger": {"type": "string"},
                "option": {"type": "string"},
                "exact": {"type": "boolean"}
            }, "required": ["trigger", "option"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_click_popover_button_semantic",
            "description": (
                "Нажимает единственную точную enabled-кнопку внутри уже открытого "
                "aria-controls popup. WRITE или DESTRUCTIVE по имени кнопки; "
                "сам клик не доказывает результат действия."
            ),
            "parameters": {"type": "object", "properties": {
                "trigger": {"type": "string"},
                "button": {"type": "string"},
                "exact": {"type": "boolean"}
            }, "required": ["trigger", "button"]}
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
            "name": "browser_inspect_agent_telemetry_semantic",
            "description": (
                "Read-only связывает открытую карточку точной КЕ с уже "
                "наблюдёнными браузером ответами CI, agent и monitoring. "
                "Возвращает UI/API статусы, ОС, архитектуру, версию и свежесть "
                "CPU/RAM. Противоречие или устаревшие данные дают BLOCKED, "
                "не PASS. Не открывает Monitoring dashboard и не запускает задач."
            ),
            "parameters": {"type": "object", "properties": {
                "ci_name": {"type": "string"},
                "max_age_seconds": {"type": "integer"}
            }, "required": ["ci_name"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_inspect_agent_plugins_semantic",
            "description": (
                "Read-only проверка plugin audit открытой КЕ по уже наблюдённому "
                "GET ответу. Проверяет agent ID, давность аудита, точное имя, "
                "версию и load_status. Старый аудит не подтверждает установку."
            ),
            "parameters": {"type": "object", "properties": {
                "ci_name": {"type": "string"},
                "plugin_name": {"type": "string"},
                "expected_version": {"type": "string"},
                "max_age_seconds": {"type": "integer"}
            }, "required": ["ci_name"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_open_agent_tasks_semantic",
            "description": (
                "INTERACT: детерминированно открывает точную строку КЕ в "
                "текущей CMDB-таблице, затем вкладки Agent и Tasks. Каждый "
                "этап использует exact semantic target; в конце подтверждает "
                "наблюдённый GET списка задач того же agent ID. Ничего не "
                "создаёт, не запускает и не изменяет."
            ),
            "parameters": {"type": "object", "properties": {
                "ci_name": {"type": "string"},
            }, "required": ["ci_name"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_inspect_agent_tasks_semantic",
            "description": (
                "Read-only список задач выбранного агента по уже увиденному "
                "GET ответу после открытия Agent → Tasks. Можно указать точное "
                "имя задачи и/или ID из наблюдённого списка; ID различает "
                "повторяющиеся имена. Возвращает только безопасные метаданные: enabled, "
                "period, status и last_processed_at. Не запускает задачу и "
                "не подтверждает результат её выполнения. Если GET ещё не "
                "наблюдался, открой вкладку Agent → Tasks и повтори."
            ),
            "parameters": {"type": "object", "properties": {
                "ci_name": {"type": "string"},
                "task_name": {"type": "string"},
                "task_id": {"type": "string"},
            }, "required": ["ci_name"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_inspect_agent_task_result_semantic",
            "description": (
                "Read-only чтение сохранённого результата одной задачи через "
                "штатный GET /full. Требует точный task_id из уже наблюдённого "
                "полного списка выбранного агента. Возвращает только наличие, "
                "тип, время и код ошибки; содержимое результата, параметры "
                "и текст ошибки не раскрывает. Не запускает задачу и не "
                "доказывает корректность выполнения без expected_text или "
                "expected_error_code, явно записанных пользователем в Job. "
                "verify_periodic сравнивает два вызова для того же task_id "
                "и требует явного запроса periodic-проверки в Job."
            ),
            "parameters": {"type": "object", "properties": {
                "ci_name": {"type": "string"},
                "task_id": {"type": "string"},
                "expected_text": {"type": "string"},
                "expected_error_code": {"type": "integer"},
                "verify_periodic": {"type": "boolean"},
            }, "required": ["ci_name", "task_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_create_managed_agent_task_semantic",
            "description": (
                "WRITE: создаёт на точно наблюдённом агенте одну безопасную "
                "executeCommand-фикстуру из закрытого allowlist. Произвольную "
                "команду, shell, sudo или аргументы передать нельзя. Созданная "
                "задача автоматически регистрируется Core в resource ledger."
            ),
            "parameters": {"type": "object", "properties": {
                "ci_name": {"type": "string"},
                "fixture_id": {
                    "type": "string",
                    "enum": [
                        "posix_printf_marker_v1",
                        "windows_cmd_echo_marker_v1",
                    ],
                },
            }, "required": ["ci_name", "fixture_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_inspect_managed_agent_task_result_semantic",
            "description": (
                "Read-only проверяет результат созданной в текущей browser "
                "session managed task по приватному маркеру. Содержимое "
                "команды и результата модели не возвращается."
            ),
            "parameters": {"type": "object", "properties": {
                "ci_name": {"type": "string"},
                "task_id": {"type": "string"},
            }, "required": ["ci_name", "task_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_disable_agent_task_semantic",
            "description": (
                "DESTRUCTIVE cleanup: отключает ровно одну наблюдённую "
                "executeCommand-задачу по точному UUID и проверяет enabled=0 "
                "повторным GET. Используется только для ledger-managed cleanup."
            ),
            "parameters": {"type": "object", "properties": {
                "ci_name": {"type": "string"},
                "task_id": {"type": "string"},
            }, "required": ["ci_name", "task_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_inspect_semantic",
            "description": (
                "Read-only проверка фактического состояния "
                "элемента интерфейса без клика. Возвращает "
                "visible/enabled/disabled, metadata, screenshot и layout: "
                "координаты, попадание во viewport, долю видимой области и "
                "перекрытие центра другим элементом. Metadata также содержит "
                "focus/hover/checked/invalid и безопасный набор computed CSS. "
                "Используй для проверки наличия и доступности "
                "кнопок, ссылок, modal/dialog и toast/notification. "
                "Dialog проверяется через role dialog/alertdialog, а "
                "уведомление — через alert/status. При неоднозначности "
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
                            "dialog", "alertdialog", "alert", "status",
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

    if name == "browser_set_viewport_semantic":
        return set_viewport_semantic(arguments["profile"])

    if name == "browser_inspect_accessibility_semantic":
        return inspect_accessibility_semantic()

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

    if name == "browser_inspect_new_tab_semantic":
        return inspect_new_tab_semantic(
            arguments["name"],
            arguments["expected_url_prefix"],
            arguments.get("exact", True),
        )

    if name == "browser_navigate_history_semantic":
        return navigate_history_semantic(
            arguments["direction"],
            arguments["expected_url_prefix"],
        )

    if name == "browser_inspect_iframe_semantic":
        return inspect_iframe_semantic(
            arguments["name"],
            arguments["expected_url_prefix"],
            arguments.get("exact", True),
        )

    if name == "browser_observe_iframe_surface_change_semantic":
        return observe_iframe_surface_change_semantic(
            arguments["name"],
            arguments["expected_url_prefix"],
            arguments["expect_change"],
            arguments.get("wait_ms", 1000),
            arguments.get("exact", True),
        )

    if name == "browser_click_iframe_surface_semantic":
        return click_iframe_surface_semantic(
            arguments["name"],
            arguments["expected_url_prefix"],
            arguments["x_ratio"],
            arguments["y_ratio"],
            arguments["expect_change"],
            arguments.get("wait_ms", 1000),
            arguments.get("exact", True),
        )

    if name == "browser_press_iframe_surface_key_semantic":
        return press_iframe_surface_key_semantic(
            arguments["name"], arguments["expected_url_prefix"],
            arguments["key"], arguments["x_ratio"], arguments["y_ratio"],
            arguments["expect_change"],
            arguments.get("focus_expect_change", False),
            arguments.get("wait_ms", 500), arguments.get("exact", True),
        )

    if name == "browser_inspect_hover_tooltip_semantic":
        return inspect_hover_tooltip_semantic(
            arguments["target"], arguments["target_role"],
            arguments["expected_tooltip"], arguments.get("exact", True),
        )

    if name == "browser_handle_native_dialog_semantic":
        return handle_native_dialog_semantic(
            arguments["target"], arguments["expected_type"],
            arguments["expected_message"], arguments.get("decision", "dismiss"),
            arguments.get("prompt_text"), arguments.get("exact", True),
        )

    if name == "browser_inspect_form_validation_semantic":
        return inspect_form_validation_semantic(
            arguments.get("form"), arguments.get("exact", True),
        )

    if name == "browser_inspect_loading_state_semantic":
        return inspect_loading_state_semantic(
            arguments.get("scope"), arguments.get("expected_state", "ready"),
            arguments.get("wait_ms", 2000),
            arguments.get("require_transition", False),
            arguments.get("exact", True),
        )

    if name == "browser_inspect_notification_lifecycle_semantic":
        return inspect_notification_lifecycle_semantic(
            arguments["expected_text"], arguments.get("role", "alert"),
            arguments.get("expected_state", "visible"),
            arguments.get("wait_ms", 2000),
            arguments.get("require_seen", False),
            arguments.get("exact", True),
        )

    if name == "browser_inspect_aria_field_errors_semantic":
        return inspect_aria_field_errors_semantic(arguments.get("form"), arguments.get("exact", True))
    if name == "browser_inspect_control_state_lifecycle_semantic":
        return inspect_control_state_lifecycle_semantic(arguments["target"], arguments["role"], arguments["expected_state"], arguments.get("wait_ms", 2000), arguments.get("require_seen", False), arguments.get("exact", True))
    if name == "browser_track_form_dirty_state_semantic":
        return track_form_dirty_state_semantic(arguments["form"], arguments.get("operation", "compare"), arguments.get("exact", True))
    if name == "browser_inspect_tabs_contract_semantic":
        return inspect_tabs_contract_semantic(arguments.get("tablist"), arguments.get("exact", True))
    if name == "browser_inspect_disclosure_contract_semantic":
        return inspect_disclosure_contract_semantic(arguments["target"], arguments.get("exact", True))
    if name == "browser_inspect_dialog_focus_trap_semantic":
        return inspect_dialog_focus_trap_semantic(arguments["dialog"], arguments.get("cycles", 1), arguments.get("exact", True))
    if name == "browser_inspect_heading_structure_semantic":
        return inspect_heading_structure_semantic()
    if name == "browser_inspect_landmark_structure_semantic":
        return inspect_landmark_structure_semantic()
    if name == "browser_inspect_link_contracts_semantic":
        return inspect_link_contracts_semantic()

    if name == "browser_inspect_agent_telemetry_semantic":
        return inspect_agent_telemetry_semantic(
            arguments["ci_name"],
            arguments.get("max_age_seconds", 300),
        )

    if name == "browser_inspect_agent_plugins_semantic":
        return inspect_agent_plugins_semantic(
            arguments["ci_name"], arguments.get("plugin_name"),
            arguments.get("expected_version"),
            arguments.get("max_age_seconds", 3600),
        )

    if name == "browser_inspect_agent_tasks_semantic":
        return inspect_agent_tasks_semantic(
            arguments.get("ci_name"), arguments.get("task_name"),
            arguments.get("task_id"),
        )

    if name == "browser_open_agent_tasks_semantic":
        return open_agent_tasks_semantic(arguments.get("ci_name"))

    if name == "browser_inspect_agent_task_result_semantic":
        return inspect_agent_task_result_semantic(
            arguments.get("ci_name"), arguments.get("task_id"),
            arguments.get("expected_text"), arguments.get("expected_error_code"),
            arguments.get("verify_periodic", False),
        )

    if name == "browser_create_managed_agent_task_semantic":
        return create_managed_agent_task_semantic(
            arguments.get("ci_name"), arguments.get("fixture_id"),
        )

    if name == "browser_inspect_managed_agent_task_result_semantic":
        return inspect_managed_agent_task_result_semantic(
            arguments.get("ci_name"), arguments.get("task_id"),
        )

    if name == "browser_disable_agent_task_semantic":
        return disable_agent_task_semantic(
            arguments.get("ci_name"), arguments.get("task_id"),
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

    if name == "browser_download_semantic":
        return download_semantic(
            arguments["name"],
            arguments["expected_filename"],
            arguments.get("expected_format"),
            arguments.get("expected_sha256"),
            arguments.get("exact", True),
        )

    if name == "browser_verify_download_structure_semantic":
        return verify_download_structure_semantic(
            arguments["download_id"],
            arguments["format"],
            arguments.get("expected_headers"),
            arguments.get("min_rows"),
            arguments.get("max_rows"),
            arguments.get("expected_pages"),
            arguments.get("expected_json_type"),
            arguments.get("required_keys"),
            arguments.get("min_items"),
            arguments.get("max_items"),
            arguments.get("expected_width"),
            arguments.get("expected_height"),
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

    if name == "browser_inspect_file_input_semantic":
        return inspect_file_input_semantic(
            arguments["field"],
            arguments.get("exact", True),
        )

    if name == "browser_set_upload_fixture_semantic":
        return set_upload_fixture_semantic(
            arguments["field"],
            arguments["fixture"],
            arguments.get("exact", True),
        )

    if name == "browser_set_temporal_semantic":
        return set_temporal_semantic(
            arguments["field"],
            arguments["value"],
            arguments.get("exact", True),
        )

    if name == "browser_set_slider_semantic":
        return set_slider_semantic(
            arguments["field"],
            arguments["value"],
            arguments.get("exact", True),
        )

    if name == "browser_inspect_tree_semantic":
        return inspect_tree_semantic(
            arguments.get("tree"),
            arguments.get("exact", True),
        )

    if name == "browser_set_tree_item_expanded":
        return set_tree_item_expanded(
            arguments["item"],
            arguments["expanded"],
            arguments.get("tree"),
            arguments.get("exact", True),
        )

    if name == "browser_set_tree_item_selected":
        return set_tree_item_selected(
            arguments["item"],
            arguments["selected"],
            arguments.get("tree"),
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

    if name == "browser_inspect_popover_semantic":
        return inspect_popover_semantic(
            arguments["trigger"], arguments.get("exact", True),
        )

    if name == "browser_open_popover_semantic":
        return open_popover_semantic(
            arguments["trigger"], arguments.get("exact", True),
        )

    if name == "browser_close_popover_semantic":
        return close_popover_semantic(
            arguments["trigger"], arguments.get("exact", True),
        )

    if name == "browser_inspect_calendar_semantic":
        return inspect_calendar_semantic(
            arguments["trigger"], arguments.get("exact", True),
        )

    if name == "browser_open_calendar_semantic":
        return open_calendar_semantic(
            arguments["trigger"], arguments.get("exact", True),
        )

    if name == "browser_select_calendar_option_semantic":
        return select_calendar_option_semantic(
            arguments["trigger"], arguments["option"],
            arguments.get("exact", True),
        )

    if name == "browser_inspect_time_picker_semantic":
        return inspect_time_picker_semantic(
            arguments["trigger"], arguments.get("exact", True),
        )

    if name == "browser_open_time_picker_semantic":
        return open_time_picker_semantic(
            arguments["trigger"], arguments.get("exact", True),
        )

    if name == "browser_select_time_picker_option_semantic":
        return select_time_picker_option_semantic(
            arguments["trigger"], arguments["option"],
            arguments.get("exact", True),
        )

    if name == "browser_inspect_dialog_semantic":
        return inspect_dialog_semantic(
            arguments["dialog"], arguments.get("exact", True),
        )

    if name == "browser_click_dialog_button_semantic":
        return click_dialog_button_semantic(
            arguments["dialog"], arguments["button"],
            arguments.get("exact", True),
        )

    if name == "browser_select_popover_option_semantic":
        return select_popover_option_semantic(
            arguments["trigger"],
            arguments["option"],
            arguments.get("exact", True),
        )

    if name == "browser_click_popover_button_semantic":
        return click_popover_button_semantic(
            arguments["trigger"],
            arguments["button"],
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
