from tools.browser import (
    open_page,
    get_state,
    inspect_semantic,
    inspect_table_row,
    click_semantic,
    context_menu_semantic,
    fill_semantic,
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
    }
,
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

    return {
        "error": f"Unknown tool: {name}"
    }
