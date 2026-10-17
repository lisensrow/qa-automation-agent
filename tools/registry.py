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
    open_exact_table_row_details_semantic,
    verify_exact_table_row_tabs_semantic,
    click_semantic,
    download_semantic,
    verify_download_structure_semantic,
    inspect_new_tab_semantic,
    navigate_history_semantic,
    inspect_iframe_semantic,
    observe_iframe_surface_change_semantic,
    verify_iframe_surface_readiness_semantic,
    click_iframe_surface_semantic,
    press_iframe_surface_key_semantic,
    inspect_hover_tooltip_semantic,
    handle_native_dialog_semantic,
    inspect_form_validation_semantic,
    verify_exact_form_required_contract_semantic,
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
    inspect_combobox_contract_semantic,
    inspect_listbox_contract_semantic,
    inspect_menu_contract_semantic,
    inspect_progressbar_contract_semantic,
    inspect_meter_contract_semantic,
    inspect_spinbutton_contract_semantic,
    inspect_text_contrast_semantic,
    inspect_text_clipping_semantic,
    inspect_target_size_semantic,
    inspect_live_region_contract_semantic,
    inspect_dialog_contract_semantic,
    inspect_field_label_contract_semantic,
    inspect_document_metadata_semantic,
    inspect_keyboard_shortcuts_semantic,
    inspect_autofill_contract_semantic,
    inspect_form_submission_contract_semantic,
    inspect_script_security_semantic,
    inspect_media_resource_semantic,
    inspect_lazy_media_contract_semantic,
    inspect_font_readiness_semantic,
    inspect_reduced_motion_contract_semantic,
    inspect_details_contract_semantic,
    inspect_popover_contract_semantic,
    inspect_native_dialog_element_semantic,
    inspect_fieldset_contract_semantic,
    inspect_radio_group_contract_semantic,
    inspect_button_type_contract_semantic,
    inspect_contenteditable_contract_semantic,
    inspect_search_contract_semantic,
    inspect_breadcrumb_contract_semantic,
    inspect_table_structure_contract_semantic,
    inspect_list_structure_contract_semantic,
    inspect_description_list_contract_semantic,
    inspect_hash_link_contract_semantic,
    inspect_navigation_current_contract_semantic,
    inspect_skip_link_contract_semantic,
    inspect_required_field_contract_semantic,
    inspect_describedby_contract_semantic,
    inspect_invalid_field_contract_semantic,
    inspect_text_length_contract_semantic,
    inspect_range_constraint_contract_semantic,
    inspect_inputmode_contract_semantic,
    inspect_new_tab_link_contract_semantic,
    inspect_iframe_contract_semantic,
    inspect_referrerpolicy_contract_semantic,
    inspect_tabindex_contract_semantic,
    inspect_disabled_control_contract_semantic,
    inspect_readonly_contract_semantic,
    inspect_aria_controls_contract_semantic,
    inspect_aria_labelledby_contract_semantic,
    inspect_aria_owns_contract_semantic,
    inspect_checkbox_contract_semantic,
    inspect_switch_contract_semantic,
    inspect_toggle_button_contract_semantic,
    inspect_expanded_contract_semantic,
    inspect_haspopup_contract_semantic,
    inspect_activedescendant_contract_semantic,
    inspect_set_position_contract_semantic,
    inspect_virtual_grid_contract_semantic,
    inspect_aria_level_contract_semantic,
    inspect_svg_accessibility_contract_semantic,
    inspect_canvas_fallback_contract_semantic,
    inspect_media_caption_contract_semantic,
    inspect_language_contract_semantic,
    inspect_direction_contract_semantic,
    inspect_time_contract_semantic,
    inspect_canonical_url_contract_semantic,
    inspect_alternate_language_contract_semantic,
    inspect_base_url_contract_semantic,
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
    scroll_table_horizontal_semantic,
    sort_table_semantic,
    verify_table_sort_roundtrip_semantic,
    set_table_row_selected,
    table_page_semantic,
    verify_table_pagination_roundtrip_semantic,
    fill_table_filter_semantic,
    verify_table_text_filter_roundtrip_semantic,
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
    verify_dialog_wizard_roundtrip_semantic,
    inspect_table_pagination_semantic,
    set_table_all_selected,
    inspect_bulk_action_semantic,
    get_network_detail,
    inspect_saved_block_graph_semantic,
    delete_json_resource,
    archive_json_resource,
    authenticate_saved_stand,
)

from knowledge_tool import knowledge_search
from regression_source_reader import read_case as read_regression_case,read_step_cell as read_regression_step_cell
from api_contract_sources import inspect_registered_contract_page

from ssh_worker import (
    docker_ps,
    docker_logs,
    find_backend_request,
)



TOOLS = [
    {'type':'function','function':{'name':'browser_remove_exact_legacy_msi_semantic',
      'description':'DESTRUCTIVE: only locked human-authorized Windows legacy TightVNC2.8.85.0 exact MSI product. Fresh native identity preflight, no arbitrary command/manual deletion/reboot/plugin changes; Core context/policy/journal required.',
      'parameters':{'type':'object','additionalProperties':False,'required':['target'],
          'properties':{'target':{'type':'string','enum':['windows']}}}}},
    {'type':'function','function':{'name':'browser_start_closed_endpoint_metadata_semantic',
      'description':'WRITE: locked fixed endpoint probe: Astra log/tray metadata, Windows exact legacy absence, or Windows/Astra local WTS/logind session census. No arbitrary command/log contents/login/unlock/settings. Core/journal and own result required; observation is not desktop PASS.',
      'parameters':{'type':'object','additionalProperties':False,'required':['target'],
          'properties':{'target':{'type':'string','enum':['windows','astra']}}}}},
    {'type':'function','function':{'name':'browser_inspect_closed_endpoint_metadata_semantic',
      'description':'READ: own same-session fixed endpoint probe full result only; metadata is not Tray desktop.',
      'parameters':{'type':'object','additionalProperties':False,'required':['target'],
          'properties':{'target':{'type':'string','enum':['windows','astra']}}}}},
    {'type':'function','function':{'name':'browser_read_closed_endpoint_metadata_readiness_semantic',
      'description':'READ: exact target/OS/core, loaded executeCommand1.4.0 and complete safe command list. Unknown unresolved tasks block. Windows requires separately locked legacy-MSI/absence or local-session-census profile; no cancellation or permission grant.',
      'parameters':{'type':'object','additionalProperties':False,'required':['target'],
          'properties':{'target':{'type':'string','enum':['windows','astra']}}}}},
    {'type':'function','function':{'name':'browser_start_closed_vnc_session_semantic',
      'description':'WRITE: one locked supplied-release VNC session on dedicated Windows/Astra/core1.3.27. Two linked own tasks and receive-only image channel. No input, delivery, settings or URL/token disclosure.',
      'parameters':{'type':'object','additionalProperties':False,'required':['target'],
          'properties':{'target':{'type':'string','enum':['windows','astra']}}}}},
    {'type':'function','function':{'name':'browser_inspect_closed_vnc_session_semantic',
      'description':'READ: own linked VNC tasks and captured decoded-image metadata only; no URL, input or restart.',
      'parameters':{'type':'object','additionalProperties':False,'required':['target'],
          'properties':{'target':{'type':'string','enum':['windows','astra']}}}}},
    {'type':'function','function':{'name':'browser_read_closed_vnc_readiness_semantic',
      'description':'READ: exact locked target/core and fresh loaded displayMonitoring1.3.1/vncServer1.5.5, complete terminal prior task lists. No delivery or session.',
      'parameters':{'type':'object','additionalProperties':False,'required':['target'],
          'properties':{'target':{'type':'string','enum':['windows','astra']}}}}},
    {'type':'function','function':{'name':'browser_compare_owned_dmi_identity_semantic',
        'description':'OBSERVE exact locked owned Windows/Astra DMI and SMBIOS recorded pair. GET same originally model-hashed payloads; compare all eight predeclared raw identity fields, singleton arrays and unknown placeholders. No normalization, CPU/DIMM/all hardware/UI/full case, new task or delivery authority.',
        'parameters':{'type':'object','additionalProperties':False,'required':['target'],'properties':{'target':{'type':'string','enum':['windows','astra']}}}}},
    {'type':'function','function':{'name':'browser_compare_owned_os_identity_semantic',
        'description':'OBSERVE exact locked owned Windows/Astra recorded native OS/osAudit pair. Validate original proofs, pre-dispatch raw hypothesis and explicit operator data-digest preparation, GET both payloads, compare only declared raw hostname/kernel fields. Not normative product naming, current live state, all OS/UI/full-case PASS or new task authority. Operator first full audit hash is NOT original model full-hash proof.',
        'parameters':{'type':'object','additionalProperties':False,'required':['target'],'properties':{'target':{'type':'string','enum':['windows','astra']}}}}},
    {'type':'function','function':{'name':'browser_compare_owned_software_values_semantic',
        'description':'OBSERVE locked owned Astra recorded OS592/softAudit594 pair. GET same hash-verified full payloads and compare every exact unique package name/version; no architecture stripping/normalization, new task, other-field/UI/all-app/full-case proof or replay authority. Bounded explicit difference samples, not raw inventory export.',
        'parameters':{'type':'object','additionalProperties':False,'required':['target'],'properties':{'target':{'type':'string','enum':['astra']}}}}},
    {'type':'function','function':{'name':'browser_compare_owned_gpu_names_semantic',
        'description':'OBSERVE locked owned Astra GPU/OS recorded pair. GET same hash-verified gpuDeviceAudit payload, compare predeclared exact vendor-space-device name hypothesis only. No new tasks/delivery, note/all-GPU/render/full-case proof or replay authority.',
        'parameters':{'type':'object','additionalProperties':False,'required':['target'],'properties':{'target':{'type':'string','enum':['astra']}}}}},
    {'type':'function','function':{'name':'browser_compare_owned_drive_values_semantic',
        'description':'OBSERVE exact locked owned Astra drive/OS observation pair. GET same hash-verified drive payload; compare mounted point/filesystem/numeric capacity against independent lsblk. No new tasks, units/serial/UID/full-case proof or replay authority.',
        'parameters':{'type':'object','additionalProperties':False,'required':['target'],'properties':{'target':{'type':'string','enum':['astra']}}}}},
    {'type':'function','function':{'name':'browser_review_plugin_result_semantic',
        'description':'OBSERVE locked historical audit, Windows VNC error, or supplied Tray start report-content invariants. Own source proof and full digest required; no reported users is not desktop success. Not current OS correctness/full case PASS/task creation/permission.',
        'parameters':{'type':'object','additionalProperties':False,'required':['target','plugin_name'],
            'properties':{'target':{'type':'string','enum':['windows','astra']},'plugin_name':{'type':'string','enum':['storageAudit','defaultNetworkDeviceAudit','vncServer','trayControl']}}}}},
    {'type':'function','function':{'name':'operation_read_attempt_history',
        'description':'OBSERVE exact locked historical Job/case/operation native proof. request_sent true/false/null; never current PASS, retry permission or live verification. No writes or external requests.',
        'parameters':{'type':'object','additionalProperties':False,'required':['source_job_id','source_case_id','operation_id'],
            'properties':{'source_job_id':{'type':'string'},'source_case_id':{'type':'string'},'operation_id':{'type':'string'}}}}},
    {'type':'function','function':{'name':'browser_inspect_tray_catalog_semantic',
        'description':'OBSERVE: closed same-origin Tray versions or dependency GET for an exact locked dedicated lab case. Available files/versions are NOT installed/compatible/session PASS. No file downloads or task creation.',
        'parameters':{'type':'object','additionalProperties':False,'required':['target','kind'],
            'properties':{'target':{'type':'string','enum':['windows','astra']},'kind':{'type':'string','enum':['versions','dependencies']}}}}},
    {'type':'function','function':{'name':'browser_create_closed_plugin_discovery_semantic',
        'description':'WRITE: locked audit discovery, exact Windows VncServer start, or supplied trayControl action=start candidate on Windows/Astra. Core policy/journal and immutable preconditions; no delivery/arbitrary shell/remote session/consent change. Execution shape is not semantic PASS.',
        'parameters':{'type':'object','additionalProperties':False,'required':['target','plugin_name','stage_id'],
            'properties':{'target':{'type':'string','enum':['windows','astra']},'plugin_name':{'type':'string','enum':['checkAlive','remoteConnections','storageAudit','defaultNetworkDeviceAudit','vncServer','trayControl']},'stage_id':{'type':'string','enum':['main_discovery']}}}}},
    {'type':'function','function':{'name':'browser_inspect_closed_plugin_discovery_semantic',
        'description':'OBSERVE own same-case/session discovery full result; bounded type census and digest, not semantic oracle.',
        'parameters':{'type':'object','additionalProperties':False,'required':['target','plugin_name','task_id'],
            'properties':{'target':{'type':'string','enum':['windows','astra']},'plugin_name':{'type':'string','enum':['checkAlive','remoteConnections','storageAudit','defaultNetworkDeviceAudit','vncServer','trayControl']},'task_id':{'type':'string'}}}}},
    {'type':'function','function':{'name':'browser_read_closed_plugin_discovery_semantic',
        'description':'OBSERVE exact locked discovery target readiness/core/OS/version. No tasks or delivery.',
        'parameters':{'type':'object','additionalProperties':False,'required':['target','plugin_name'],
            'properties':{'target':{'type':'string','enum':['windows','astra']},'plugin_name':{'type':'string','enum':['checkAlive','remoteConnections','storageAudit','defaultNetworkDeviceAudit','vncServer','trayControl']}}}}},
    {'type':'function','function':{'name':'browser_create_closed_plugin_preparation_semantic',
        'description':'WRITE: locked pinned plugin preparation on dedicated Windows/Astra. displayMonitoring1.3.1 is supplied-release only, not workbook1.3.2 PASS. Inventory/delivery/post_inventory; policy/OS-check/no-deletion. No main/VNC session.',
        'parameters':{'type':'object','additionalProperties':False,'required':['target','plugin_name','stage_id'],
            'properties':{'target':{'type':'string','enum':['windows','astra']},'plugin_name':{'type':'string','enum':['checkAlive','remoteConnections','storageAudit','defaultNetworkDeviceAudit','vncServer','displayMonitoring','trayControl']},
                'stage_id':{'type':'string','enum':['initial_inventory','delivery','post_inventory']}}}}},
    {'type':'function','function':{'name':'browser_inspect_closed_plugin_preparation_semantic',
        'description':'READ-only: full только own preparation receipt того же case/session. Download не loaded, fresh loaded не основной кейс.',
        'parameters':{'type':'object','additionalProperties':False,'required':['target','plugin_name','task_id'],
            'properties':{'target':{'type':'string','enum':['windows','astra']},'plugin_name':{'type':'string','enum':['checkAlive','remoteConnections','storageAudit','defaultNetworkDeviceAudit','vncServer','displayMonitoring','trayControl']},'task_id':{'type':'string'}}}}},
    {'type':'function','function':{'name':'browser_read_closed_plugin_preparation_semantic',
        'description':'READ-only: fresh inventory/core/OS pinned preparation plugins. Locked exact-target case. No main task/VNC session/command.',
        'parameters':{'type':'object','additionalProperties':False,'required':['target','plugin_name'],
            'properties':{'target':{'type':'string','enum':['windows','astra']},'plugin_name':{'type':'string','enum':['checkAlive','remoteConnections','storageAudit','defaultNetworkDeviceAudit','vncServer','displayMonitoring','trayControl']}}}}},
    {"type":"function","function":{"name":"api_inspect_request_contract",
        "description":"OBSERVE: read a registered historical operation and its direct application/json request schema together. Exactly two source/pin-checked pages; no HTTP, recursive schema closure, defaults, enum values, payload validation or business PASS. Same stand/source selection and caller lock as api_inspect_contract_page. Use when the question needs required request fields, not just operation roots.",
        "parameters":{"type":"object","additionalProperties":False,"properties":{
            "stand":{"type":"string"},"method":{"type":"string"},"path":{"type":"string"},"source_id":{"type":"string"}},
            "required":["method","path"]}}},
    {"type":"function","function":{"name":"api_inspect_contract_page",
        "description":"Read-only: одна страница исторического API-контракта зарегистрированного источника текущего стенда. При нескольких редакциях выбери source_id только из available_source_ids; не смешивай редакции и не считай выбранную текущей автоматически. Пустая reference_chain читает operation, затем передавай цепочку только раскрытых direct_schema_references. Не выполняет HTTP, не знает enum values/полную валидацию, не доказывает свежесть, permission или PASS. Pins/пути файлов/исходное evidence задаёт оператор, не модель.",
        "parameters":{"type":"object","additionalProperties":False,"properties":{
            "stand":{"type":"string"},"method":{"type":"string"},"path":{"type":"string"},
            "source_id":{"type":"string","description":"Exact registered source ID for this stand, as returned in available_source_ids. Not a file path, digest, URL or permission; caller-locked source cannot be changed."},
            "reference_chain":{"type":"array","maxItems":8,"items":{"type":"string"}}},"required":["method","path"]}}},
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
            "name": "knowledge_read_indexed_source_window",
            "description": "READ-only two allowlisted indexed sources (official UC user guide and reviewed software-comparison memory). First call without expected_index_sha256 returns manifest only; then supply its exact digest for complete 1..3 chunk windows. No silent truncation, raw-file provenance/current-state/permission/fullcase claim. Use own observed source/cursors and next_chunk to read missing context.",
            "parameters": {"type":"object","additionalProperties":False,"required":["source"],"properties":{"source":{"type":"string","enum":["UQA-docs/UC Руководство пользователя от 06.07.2026.docx","UQA-experience/UQA_SOFTWARE_VALUE_COMPARISON_20261017.md"]},"first_chunk":{"type":"integer"},"chunk_count":{"type":"integer"},"expected_index_sha256":{"type":"string"}}}
        }
    },
    {
        "type":"function",
        "function":{
            "name": "knowledge_read_regression_case",
            "description": "Read a hash-pinned archived Windows/Astra regression source window (1..3 steps), including exact expected/test data. Source only, no execution/permission or current-state proof. Use next_step to read every required window; an oversized result is refused, never truncated.",
            "parameters": {"type":"object","additionalProperties":False,"properties":{"case_key":{"type":"string"},"first_step":{"type":"integer"},"step_count":{"type":"integer"}},"required":["case_key"]}
        }
    },
    {
        "type":"function",
        "function":{
            "name":"knowledge_read_regression_step_cell",
            "description":"Read an explicit hash-pinned page of one archived step field when a complete source step exceeds its result budget. Use next_char_offset, join all pages and verify cell_sha256. A page/cell is not a complete step/case, current state or execution authority.",
            "parameters":{"type":"object","additionalProperties":False,"required":["case_key","step_number","field"],
                "properties":{"case_key":{"type":"string"},"step_number":{"type":"integer"},
                    "field":{"type":"string","enum":["description_html","test_data_html","expected_html"]},
                    "char_offset":{"type":"integer"},"char_count":{"type":"integer"}}}
        }
    },
    {'type':'function','function':{
        'name':'knowledge_inspect_own_regression_read_coverage',
        'description':'READ-only verify own current Job/case archived-source receipts against exact pinned primary cells. Report contiguous page/field hashes and gaps for one step, precondition and whole-case SOURCE coverage separately. Never supplies the described plugin name, proves comprehension/current oracle/runtime/PASS, adopts other Jobs or grants execution. Requires an existing exact locked source-read profile.',
        'parameters':{'type':'object','additionalProperties':False,'required':['case_key','step_number'],
            'properties':{'case_key':{'type':'string','pattern':'^US-T[0-9]{1,8}$'},'step_number':{'type':'integer','minimum':1,'maximum':100}}}}},
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
                " source_namespace=product_docs ищет только продуктовые руководства, "
                "experience только опыт/кейсы, all сохраняет общий поиск. Scope не подтверждает актуальность или authority."
                " required_term задаёт один обязательный редкий alphanumeric identifier token, чтобы общие name/note не вытесняли предмет поиска; это фильтр, не контракт."
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
                    },
                    "source_namespace": {
                        "type":"string","enum":["all","product_docs","experience"],
                        "description":"Fixed source-location filter before ranking/limit, default all. No arbitrary path or permission."
                    },
                    "required_term": {
                        "type":"string","pattern":"^[A-Za-z0-9]{2,80}$",
                        "description":"Optional exact identifier token required in every indexed hit. Remaining query terms keep normal ranking; not current-source/semantic proof."
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
            "name": "browser_inspect_saved_block_graph_semantic",
            "description": "Read one exact saved block-XML record from a previously observed GET request_id. Requires current session/origin, a fixed 60-second freshness limit and a complete collection. Returns counts only, never XML/commands/field values. Does not prove workspace binding, business correctness or execution; never Save/Run or PASS authority.",
            "parameters": {"type":"object","properties":{
                "request_id":{"type":"string","description":"Native network_requests request_id, e.g. n16."},
                "exact_name":{"type":"string","description":"Exact name of the single saved record to inspect."}},
                "required":["request_id","exact_name"],"additionalProperties":False}
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
                    },
                    "expected_identifier": {"type":"string", "description":"Observed ledger ID; mismatch blocks mutation."}
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
                    "exact_name": {"type": "string"},
                    "expected_identifier": {"type":"string", "description":"Observed ledger ID; mismatch blocks mutation."}
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
            "name": "browser_verify_iframe_surface_readiness_semantic",
            "description": (
                "Read-only атомарно проверяет точный iframe, ожидаемый "
                "HTTP(S) origin/URL prefix, готовую видимую canvas/video "
                "поверхность ненулевого размера и ожидаемую смену или "
                "стабильность кадра по приватным SHA-256. Не отправляет "
                "клавиатурный или pointer input."
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
            "description": "Read-only audit native form controls без Submit и без values: для каждого видимого input/select/textarea сообщает snapshot-local index, tag/type, label_hint и native_required/disabled/read_only/will_validate, плюс invalid controls. Label_hint не гарантирует accessible name; index не является устойчивой целью изменения. Native flags не доказывают бизнес-правила required или кастомную валидацию.",
            "parameters": {"type": "object", "properties": {
                "form": {"type": "string", "description": "Только наблюдённые aria-label/name/id реального HTML form; не заголовок панели. Если нужна page-wide перепись native controls, OMIT form. Это не доказательство identity именованной формы."}, "exact": {"type": "boolean"}
            }}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_verify_exact_form_required_contract_semantic",
            "description": "Read-only atomic audit одной exact form: обязательные поля, labels, aria-labelledby/aria-describedby и отсутствие write/submit requests; поля не изменяются и Submit не нажимается.",
            "parameters": {"type": "object", "properties": {
                "form": {"type": "string"},
                "expected_required_fields": {
                    "type": "array", "items": {"type": "string"},
                    "maxItems": 50, "uniqueItems": True
                }
            }, "required": ["form"]}
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
    {"type":"function","function":{"name":"browser_inspect_combobox_contract_semantic","description":"Read-only audit exact combobox: expanded, controls, popup role/visibility и active descendant.","parameters":{"type":"object","properties":{"target":{"type":"string"},"exact":{"type":"boolean"}},"required":["target"]}}},
    {"type":"function","function":{"name":"browser_inspect_listbox_contract_semantic","description":"Read-only audit exact listbox: options, names, selected count и multiselect contract.","parameters":{"type":"object","properties":{"target":{"type":"string"},"exact":{"type":"boolean"}},"required":["target"]}}},
    {"type":"function","function":{"name":"browser_inspect_menu_contract_semantic","description":"Read-only audit exact menu: menuitems, accessible names, disabled и popup metadata.","parameters":{"type":"object","properties":{"target":{"type":"string"},"exact":{"type":"boolean"}},"required":["target"]}}},
    {"type":"function","function":{"name":"browser_inspect_progressbar_contract_semantic","description":"Read-only audit exact progressbar: accessible name, min/max/now, диапазон и indeterminate state.","parameters":{"type":"object","properties":{"target":{"type":"string"},"exact":{"type":"boolean"}},"required":["target"]}}},
    {"type":"function","function":{"name":"browser_inspect_meter_contract_semantic","description":"Read-only audit exact meter: accessible name и корректный bounded numeric range.","parameters":{"type":"object","properties":{"target":{"type":"string"},"exact":{"type":"boolean"}},"required":["target"]}}},
    {"type":"function","function":{"name":"browser_inspect_spinbutton_contract_semantic","description":"Read-only audit exact spinbutton: accessible name, min/max/now и значение внутри диапазона.","parameters":{"type":"object","properties":{"target":{"type":"string"},"exact":{"type":"boolean"}},"required":["target"]}}},
    {"type":"function","function":{"name":"browser_inspect_text_contrast_semantic","description":"Read-only WCAG contrast audit видимого прямого текста на solid backgrounds.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_text_clipping_semantic","description":"Read-only обнаруживает фактически обрезанный видимый текст по client/scroll geometry и overflow.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_target_size_semantic","description":"Read-only audit размеров видимых interactive controls по порогу 16–44 px (по умолчанию 24).","parameters":{"type":"object","properties":{"minimum_px":{"type":"integer","minimum":16,"maximum":44}}}}},
    {"type":"function","function":{"name":"browser_inspect_live_region_contract_semantic","description":"Read-only audit aria-live и implicit live roles alert/status/log.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_dialog_contract_semantic","description":"Read-only audit dialog/alertdialog names, aria-labelledby references и modal metadata.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_field_label_contract_semantic","description":"Read-only audit labels и aria-describedby references полей без возврата values.","parameters":{"type":"object","properties":{"form":{"type":"string"},"exact":{"type":"boolean"}}}}},
    {"type":"function","function":{"name":"browser_inspect_document_metadata_semantic","description":"Read-only audit page title, html lang и responsive viewport metadata.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_keyboard_shortcuts_semantic","description":"Read-only audit accesskey/aria-keyshortcuts: names, syntax и duplicate declarations.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_autofill_contract_semantic","description":"Read-only audit autocomplete contracts без возврата field values; password purpose обязателен.","parameters":{"type":"object","properties":{"form":{"type":"string"},"exact":{"type":"boolean"}}}}},
    {"type":"function","function":{"name":"browser_inspect_form_submission_contract_semantic","description":"Read-only audit form method/action; блокирует mixed content и password через GET, values не читает.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_script_security_semantic","description":"Read-only audit scripts: mixed content и integrity для cross-origin sources; URL очищаются.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_media_resource_semantic","description":"Read-only audit img/video/audio: broken images, mixed content и unmuted autoplay; содержимое не скачивает.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_lazy_media_contract_semantic","description":"Read-only audit offscreen img/iframe: loading=lazy и стабильные dimensions/aspect-ratio.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_font_readiness_semantic","description":"Read-only ожидает document.fonts.ready и возвращает только status/body font family.","parameters":{"type":"object","properties":{"wait_ms":{"type":"integer","minimum":0,"maximum":10000}}}}},
    {"type":"function","function":{"name":"browser_inspect_reduced_motion_contract_semantic","description":"Read-only audit long CSS animation/transition и prefers-reduced-motion rules.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_details_contract_semantic","description":"Read-only audit native details/summary names и open content visibility.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_popover_contract_semantic","description":"Read-only audit HTML Popover API ids, popovertarget references и actions.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_native_dialog_element_semantic","description":"Read-only audit native dialog accessible names и open/rendered consistency.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_fieldset_contract_semantic","description":"Read-only audit fieldset direct legend, group name и наличие controls.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_radio_group_contract_semantic","description":"Read-only audit radio groups: group identity, labels и не более одного checked.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_button_type_contract_semantic","description":"Read-only audit form buttons: accessible name и explicit type против случайного submit.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_contenteditable_contract_semantic","description":"Read-only audit contenteditable regions: accessible name, valid mode и compatible textbox role.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_search_contract_semantic","description":"Read-only audit searchboxes, search landmarks и submit/live-filter structure.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_breadcrumb_contract_semantic","description":"Read-only audit breadcrumb navigation, named links и ровно один aria-current page.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_table_structure_contract_semantic","description":"Read-only audit native data tables: headers, row geometry и label references.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_list_structure_contract_semantic","description":"Read-only audit native и ARIA list ownership/direct listitems.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_description_list_contract_semantic","description":"Read-only audit dl term/description pairing и empty items.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_hash_link_contract_semantic","description":"Read-only audit same-document links: accessible names и существующие hash targets.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_navigation_current_contract_semantic","description":"Read-only audit navigation links и допустимый единственный aria-current внутри landmark.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_skip_link_contract_semantic","description":"Read-only audit ранних skip links, ведущих к main content.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_required_field_contract_semantic","description":"Read-only audit required fields: supported role и accessible name.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_describedby_contract_semantic","description":"Read-only audit aria-describedby: существующие непустые references.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_invalid_field_contract_semantic","description":"Read-only audit aria-invalid fields: name и linked error message.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_text_length_contract_semantic","description":"Read-only audit minlength/maxlength syntax и ordering.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_range_constraint_contract_semantic","description":"Read-only audit input min/max/step syntax и ordering.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_inputmode_contract_semantic","description":"Read-only audit inputmode tokens, editable targets и accessible names.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_new_tab_link_contract_semantic","description":"Read-only audit target=_blank names, destinations и opener isolation для external links.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_iframe_contract_semantic","description":"Read-only audit iframe title, source, sandbox и loading metadata.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_referrerpolicy_contract_semantic","description":"Read-only audit declared referrerpolicy tokens и resource targets.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_tabindex_contract_semantic","description":"Read-only audit explicit tabindex и positive focus-order overrides.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_disabled_control_contract_semantic","description":"Read-only audit native/ARIA disabled controls, names и focusability metadata.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_readonly_contract_semantic","description":"Read-only audit native/ARIA readonly controls и supported roles.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_aria_controls_contract_semantic","description":"Read-only audit aria-controls references, duplicates и self-reference.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_aria_labelledby_contract_semantic","description":"Read-only audit aria-labelledby references и resulting non-empty names.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_aria_owns_contract_semantic","description":"Read-only audit aria-owns references, duplicates и ownership cycles.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_checkbox_contract_semantic","description":"Read-only audit native/ARIA checkbox names и checked states.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_switch_contract_semantic","description":"Read-only audit ARIA switch names и boolean aria-checked.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_toggle_button_contract_semantic","description":"Read-only audit aria-pressed toggle buttons, names и state tokens.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_expanded_contract_semantic","description":"Read-only audit aria-expanded controls и optional controlled targets.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_haspopup_contract_semantic","description":"Read-only audit aria-haspopup tokens, names и popup references.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_activedescendant_contract_semantic","description":"Read-only audit aria-activedescendant target, focusability и ownership relation.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_set_position_contract_semantic","description":"Read-only audit aria-setsize/aria-posinset pairs и ordering.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_virtual_grid_contract_semantic","description":"Read-only audit virtual grid row/column counts и indexes.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_aria_level_contract_semantic","description":"Read-only audit positive aria-level values на hierarchical roles.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_svg_accessibility_contract_semantic","description":"Read-only audit exposed SVG graphics и accessible names.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_canvas_fallback_contract_semantic","description":"Read-only audit canvas accessible labels или fallback content.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_media_caption_contract_semantic","description":"Read-only audit video caption tracks и metadata без playback.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_language_contract_semantic","description":"Read-only audit document/element lang tags и xml:lang consistency.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_direction_contract_semantic","description":"Read-only audit dir tokens и document text direction.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_time_contract_semantic","description":"Read-only audit time elements, visible text и parseable datetime.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_canonical_url_contract_semantic","description":"Read-only audit canonical URL uniqueness и absolute HTTP(S) target.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_alternate_language_contract_semantic","description":"Read-only audit alternate hreflang links, targets и duplicates.","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"browser_inspect_base_url_contract_semantic","description":"Read-only audit base element uniqueness, href и target.","parameters":{"type":"object","properties":{}}}},
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
                " Имя действия из задачи не заменяет фактическое имя элемента. "
                "Для наблюдённой безымянной icon-кнопки передай icon_hint "
                "без role/container; инструмент заново проверит уникальность."
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
                            "option", "checkbox", "radio", "row", "treeitem", "combobox"
                        ],
                        "description": (
                            "Опциональная accessibility role из фактически "
                            "наблюдённых matches"
                        )
                    },
                    "container": {
                        "type": "string",
                        "description": (
                            "Опциональный точный текст наблюдённого owner tr/[role=row], "
                            "li или [role=treeitem], внутри которого находится элемент. "
                            "Не заголовок страницы, раздела или таблицы. "
                            "Без такого наблюдённого owner не передавай container."
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
                "levels, expanded, selected, checked и disabled states. "
                "Если деревьев несколько, item привязывает дерево по уникальному видимому точному пункту; exact=true обязателен."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tree": {"type": "string"},
                    "item": {"type": "string"},
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
            "name": "browser_scroll_table_horizontal_semantic",
            "description": (
                "Прокручивает только горизонтальную область одной таблицы к start/end. "
                "При заданном table требует точное реальное имя; без имени — единственную видимую таблицу. "
                "Возвращает геометрию и снимки до/после; не изменяет записи, не доказывает полноту колонок или PASS."
            ),
            "parameters": {"type": "object", "properties": {
                "edge": {"type": "string", "enum": ["start", "end"]},
                "table": {"type": "string"}, "exact": {"type": "boolean"}
            }, "required": ["edge"]}
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
            "name": "browser_verify_table_sort_roundtrip_semantic",
            "description": "Переключает одну точную sortable column в заданное направление, проверяет aria-sort и фактическую монотонность строк, затем обязательно восстанавливает исходный sort state и row identity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "column": {"type": "string"},
                    "direction": {"type": "string", "enum": ["ascending", "descending", "asc", "desc"]},
                    "table": {"type": "string"}
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
            "name": "browser_verify_table_pagination_roundtrip_semantic",
            "description": "Переходит точным pagination control на одну соседнюю страницу, проверяет page/range/total и row identity, затем обязательно возвращается точным обратным control и доказывает восстановление исходной страницы.",
            "parameters": {
                "type": "object",
                "properties": {
                    "forward_control": {"type": "string"},
                    "return_control": {"type": "string"},
                    "table": {"type": "string"}
                },
                "required": ["forward_control", "return_control"]
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
            "name": "browser_verify_table_text_filter_roundtrip_semantic",
            "description": "Атомарно применяет точный именованный text/search filter, проверяет строки выбранной колонки и reported total, затем обязательно восстанавливает исходный filter и набор строк. Записи продукта не изменяются.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter_name": {"type": "string"},
                    "value": {"type": "string"},
                    "column": {"type": "string"},
                    "table": {"type": "string"}
                },
                "required": ["filter_name", "value", "column"]
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
            "name": "browser_verify_dialog_wizard_roundtrip_semantic",
            "description": (
                "Открывает exact wizard, проверяет заданные active steps через "
                "Next и Back, закрывает Cancel/Close и доказывает отсутствие "
                "POST/PUT/PATCH/DELETE. Save/Submit/Finish запрещены."
            ),
            "parameters": {"type": "object", "properties": {
                "trigger": {"type": "string"},
                "dialog": {"type": "string"},
                "steps": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 10},
                "next_button": {"type": "string"},
                "back_button": {"type": "string"},
                "close_button": {"type": "string"},
                "exact": {"type": "boolean"}
            }, "required": ["trigger", "dialog", "steps"]}
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
            "name": "browser_open_exact_table_row_details_semantic",
            "description": (
                "Проверяет ровно одну строку таблицы по точному значению ячейки, "
                "открывает только эту уже проверенную строку и машинно подтверждает "
                "identity details-поверхности. Не нажимает Add/Save/Delete и не "
                "изменяет данные."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Точное видимое значение ячейки строки",
                    }
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_verify_exact_table_row_tabs_semantic",
            "description": (
                "Read-only открывает одну точную строку таблицы, подтверждает "
                "identity details-поверхности, затем по порядку выбирает "
                "заданные exact ARIA tabs и после каждой машинно проверяет "
                "единственный selected tab и видимую aria-controls panel."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "tabs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                        "maxItems": 20,
                    },
                    "tablist": {"type": "string"},
                },
                "required": ["name", "tabs"],
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
            "name": "agent_build_pinned_audit_report",
            "description": "Сформировать канонический expected/actual отчёт из locked oracle и первичных доказательств собственной audit-задачи текущего case. Поддерживает osAudit и закреплённые inventory-профили. Не принимает произвольные verdict/evidence/expected, не пишет Zephyr. Используй этот отчёт для итогового ответа.",
            "parameters": {"type": "object", "additionalProperties": False, "properties": {
                "task_id": {"type": "string"}
            }, "required": ["task_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_create_closed_command_stage_semantic",
            "description": "WRITE: закрытый этап command microcase на одной выделенной Windows/Astra КЕ. Версия, payload и private marker не переопределяются. Только locked typed case, прежняя policy и durable journal; не общий command executor.",
            "parameters": {"type":"object","additionalProperties":False,"required":["target","stage_id"],
                "properties":{"target":{"type":"string","enum":["windows","astra"]},
                    "stage_id":{"type":"string","enum":["initial_inventory","deliver_command_plugin","post_delivery_inventory","execute_command"]}}}
        }
    },
    {
        "type":"function",
        "function":{
            "name":"browser_inspect_closed_command_stage_semantic",
            "description":"Read-only: только собственный новый command-stage task того же case/session. Проверяет identity/freshness/private marker; не возвращает raw stdout.",
            "parameters":{"type":"object","additionalProperties":False,"required":["target","task_id"],
                "properties":{"target":{"type":"string","enum":["windows","astra"]},"task_id":{"type":"string"}}}
        }
    },
    {
        "type":"function",
        "function":{
            "name": "browser_inspect_lab_plugin_inventory_semantic",
            "description": "Read-only: шесть известных имён VNC/remoteConnections/checkAlive из руководства и исторического server catalogue только на выделенных Windows/Astra/core1.3.27. Только текущий GET; не открывает remote session, не доставляет и не запускает задачи. Наличие не PASS, expected versions unknown; guide action name не равен binary plugin name.",
            "parameters":{"type":"object","additionalProperties":False,"required":["target"],
                "properties":{"target":{"type":"string","enum":["windows","astra"]}}}
        }
    },
    {
        "type":"function",
        "function":{
            "name": "browser_inspect_pinned_agent_readiness_semantic",
            "description": "Read-only: текущие core/online и свежая загрузка закреплённого плагина на точной КЕ. Без plugin_name/plugin_version проверяет osAudit1.3.4. ready не означает выполнение теста.",
            "parameters": {"type": "object", "additionalProperties": False, "properties": {
                "ci_name": {"type": "string"}, "agent_id": {"type": "string"},
                "plugin_name": {"type":"string"}, "plugin_version": {"type":"string"}
            }, "required": ["ci_name", "agent_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_inspect_pinned_agent_audit_semantic",
            "description": "Read-only: full результата только собственной новой audit-задачи текущего context; сверяет task/agent/CI IDs и время. Возвращает безопасные поля ОС, Core сравнивает locked expected. Не принимает старые/чужие task IDs.",
            "parameters": {"type": "object", "additionalProperties": False, "properties": {
                "ci_name": {"type": "string"}, "agent_id": {"type": "string"}, "task_id": {"type": "string"}
            }, "required": ["ci_name", "agent_id", "task_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_create_pinned_agent_audit_semantic",
            "description": "WRITE: новая непериодическая задача разрешённого inventory-профиля или pluginAudit, без произвольных параметров. Точная КЕ/core1.3.27, locked scope, fresh loaded version и journal обязательны. Выбирай текущие допустимые аргументы; ACK не PASS.",
            "parameters": {"type": "object", "additionalProperties": False, "properties": {
                "ci_name": {"type": "string"}, "agent_id": {"type": "string"},
                "core_version": {"type": "string", "enum": ["1.3.27"]},
                "task_name": {"type": "string", "enum": ["pluginAudit", "osAudit","driveDeviceAudit","gpuDeviceAudit","softAudit","smbiosAudit","networkDeviceAudit","serviceAudit","displayDeviceAudit","processMonitoring","baseSystemMonitoring"]},
                "plugin_name":{"type":"string"},"plugin_version":{"type":"string"}
            }, "required": ["ci_name", "agent_id", "core_version", "task_name"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_deliver_pinned_agent_plugin_semantic",
            "description": "WRITE: точечная доставка закреплённой версии разрешённого inventory-плагина на КЕ/core1.3.27. OS-check включён, удаление/понижение/повтор запрещены. Locked scope и journal обязательны. ACK202 не загрузка: прочитай свою managePlugin задачу, затем pluginAudit.",
            "parameters": {"type": "object", "additionalProperties": False, "properties": {
                "ci_name": {"type": "string"}, "agent_id": {"type": "string"},
                "core_version": {"type": "string", "enum": ["1.3.27"]},
                "plugin_name": {"type": "string"},
                "version": {"type": "string"}
            }, "required": ["ci_name", "agent_id", "core_version", "plugin_name", "version"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_create_pinned_agent_update_semantic",
            "description": "WRITE: updateAgent только на точной наблюдённой КЕ/agent_id, с явной числовой версией. Без latest, downgrade и повторов. ACK не доказывает обновление; нужен свежий GET версии и online.",
            "parameters": {"type": "object", "additionalProperties": False, "properties": {
                "ci_name": {"type": "string"}, "agent_id": {"type": "string"},
                "version": {"type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$"}
            }, "required": ["ci_name", "agent_id", "version"]}
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


TOOLS.append({"type":"function","function":{"name":"browser_table_cell_control_semantic",
    "description":"Inspect/fill/select one control by an exact row label and exact column header in a native table or bounded labeled div grid. Ambiguous rows/columns refuse. fill/select are WRITE; never submits the form.",
    "parameters":{"type":"object","properties":{"row":{"type":"string"},"column":{"type":"string"},
        "action":{"type":"string","enum":["inspect","fill","select"]},"value":{"type":"string"},"table":{"type":"string"}},
        "required":["row","column"]}}})

TOOLS.append({'type':'function','function':{'name':'browser_inspect_labeled_grid_values_semantic',
    'description':'OBSERVE exact labeled div-grid row/column controls, returning only value hashes and lengths. Requires current native session/URL; refuses ambiguity and passwords. Does not submit or change controls.',
    'parameters':{'type':'object','additionalProperties':False,'properties':{
        'cells':{'type':'array','minItems':1,'maxItems':32,'items':{'type':'object','additionalProperties':False,
            'properties':{'row':{'type':'string'},'column':{'type':'string'}},'required':['row','column']}},
        'session_id':{'type':'string'},'current_url':{'type':'string'}},'required':['cells','session_id','current_url']}}})

TOOLS.append({'type':'function','function':{'name':'browser_add_tree_row_semantic',
    'description':'Add ONE new condition row: expand exact tree parents, drag exact leaf to an observed logical target, set exact column controls. Use for condition builders instead of clicking leaves/And. Never saves. Refuses an existing row, changed session/URL, ambiguity or partial failure; do not retry automatically. Read parents/columns/choices from memory and current UI.',
    'parameters':{'type':'object','additionalProperties':False,'properties':{
        'source':{'type':'string','description':'Exact visible LEAF/ATTRIBUTE label to drag. NOT the tree name, category, header, backend key or a path. Example: source="Attribute A".'},
        'row_label':{'type':'string','description':'Optional separately observed exact resulting row label when different from the tree leaf. Must come from reviewed profile/current UI, never guessed; defaults to source.'},
        'target':{'type':'string','description':'Exact visible logical GROUP drop-target label, not a tree or column. For example the currently observed And group.'},
        'parents':{'type':'array','maxItems':5,'items':{'type':'string'},'description':'Ordered visible CATEGORY labels to expand first. Categories belong HERE, never in source. Empty if the leaf is already visible.'},
        'cells':{'type':'array','minItems':1,'maxItems':4,'items':{'type':'object','additionalProperties':False,
            'properties':{'column':{'type':'string','description':'Exact column HEADER in the new row, e.g. Value or Operator. NEVER the attribute/row label from source.'},
                'action':{'type':'string','enum':['fill','select'],'description':'select for a dropdown/combobox, fill for a text input.'},
                'value':{'type':'string','description':'Exact observed option label or requested input text. An operator such as Wildcard is a separate cell with column Operator, not part of the Value text.'}},
            'required':['column','action','value']}},
        'session_id':{'type':'string'},'current_url':{'type':'string'}},
        'required':['source','target','parents','cells','session_id','current_url']}}})

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
    if name == "knowledge_inspect_own_regression_read_coverage":
        return {'error':'trusted_Core_job_case_context_required','executed':False}
    if name == "browser_compare_owned_dmi_identity_semantic":
        return {'error':'trusted_Core_job_case_context_required','executed':False}
    if name == "browser_compare_owned_os_identity_semantic":
        return {'error':'trusted_Core_job_case_context_required','executed':False}
    if name == "browser_compare_owned_software_values_semantic":
        return {'error':'trusted_Core_job_case_context_required','executed':False}
    if name == "browser_compare_owned_gpu_names_semantic":
        return {'error':'trusted_Core_job_case_context_required','executed':False}
    if name == "browser_compare_owned_drive_values_semantic":
        return {'error':'trusted_Core_job_case_context_required','executed':False}
    if name == "browser_review_plugin_result_semantic":
        return {'error':'trusted_Core_job_case_context_required','executed':False}
    if name == "operation_read_attempt_history":
        return {'error':'trusted_Core_job_case_context_required','executed':False}
    if name == "browser_inspect_tray_catalog_semantic":
        return {'error':'trusted_Core_job_case_context_required','executed':False}
    if name == "browser_create_closed_plugin_discovery_semantic":
        return {'error':'trusted_Core_job_case_context_required','executed':False}
    if name == "browser_inspect_closed_plugin_discovery_semantic":
        return {'error':'trusted_Core_job_case_context_required','executed':False}
    if name == "browser_read_closed_plugin_discovery_semantic":
        return {'error':'trusted_Core_job_case_context_required','executed':False}
    if name == "browser_remove_exact_legacy_msi_semantic":
        return {'error':'trusted_Core_job_case_context_required','executed':False}
    if name == "browser_start_closed_endpoint_metadata_semantic":
        return {'error':'trusted_Core_job_case_context_required','executed':False}
    if name == "browser_inspect_closed_endpoint_metadata_semantic":
        return {'error':'trusted_Core_job_case_context_required','executed':False}
    if name == "browser_read_closed_endpoint_metadata_readiness_semantic":
        return {'error':'trusted_Core_job_case_context_required','executed':False}
    if name == "browser_start_closed_vnc_session_semantic":
        return {'error':'trusted_Core_job_case_context_required','executed':False}
    if name == "browser_inspect_closed_vnc_session_semantic":
        return {'error':'trusted_Core_job_case_context_required','executed':False}
    if name == "browser_read_closed_vnc_readiness_semantic":
        return {'error':'trusted_Core_job_case_context_required','executed':False}
    if name == "browser_create_closed_plugin_preparation_semantic":
        return {'error':'trusted_Core_job_case_context_required','executed':False}
    if name == "browser_inspect_closed_plugin_preparation_semantic":
        return {'error':'trusted_Core_job_case_context_required','executed':False}
    if name == "browser_read_closed_plugin_preparation_semantic":
        return {'error':'trusted_Core_job_case_context_required','executed':False}
    if name == 'api_inspect_request_contract':
        from api_contract_sources import inspect_registered_request_contract
        if set(arguments)-{'stand','method','path','source_id'}:
            from api_contract_projection import FLAGS
            return {'contract_observation_status':'unavailable','reason':'contract_tool_arguments_invalid',**FLAGS}
        return inspect_registered_request_contract(arguments.get('stand'),arguments.get('method'),
            arguments.get('path'),source_id=arguments.get('source_id'))
    if name == "browser_inspect_labeled_grid_values_semantic":
        from tools.browser import _session
        from tools.grid_value_readback import inspect_values
        return inspect_values(_session, **arguments)
    if name == "browser_add_tree_row_semantic":
        from tools.browser import _session
        from tools.tree_row_controls import add_tree_row
        return add_tree_row(_session, **arguments)
    if name == "api_inspect_contract_page":
        if set(arguments)-{'stand','method','path','reference_chain','source_id'}:
            from api_contract_projection import FLAGS
            return {'contract_observation_status':'unavailable','reason':'contract_tool_arguments_invalid',**FLAGS}
        return inspect_registered_contract_page(arguments.get("stand"), arguments.get("method"), arguments.get("path"),
            arguments.get("reference_chain", ()),source_id=arguments.get('source_id'))
    if name == "browser_table_cell_control_semantic":
        from tools.browser import _session
        from tools.table_cell_controls import operate
        return operate(_session, **arguments)
    if name == "knowledge_read_indexed_source_window":
        from indexed_source_reader import read_window
        if set(arguments)-{'source','first_chunk','chunk_count','expected_index_sha256'}:
            return {'status':'indexed_source_unavailable','reason':'indexed_reader_arguments_invalid','executed':False}
        return read_window(arguments.get('source'),arguments.get('first_chunk',1),arguments.get('chunk_count',1),arguments.get('expected_index_sha256'))
    if name == "knowledge_read_regression_case":
        if set(arguments)-{'case_key','first_step','step_count'}:
            return {'error':'source_reader_arguments_invalid','executed':False}
        return read_regression_case(arguments.get('case_key'),arguments.get('first_step',1),arguments.get('step_count',1))
    if name == "knowledge_read_regression_step_cell":
        if set(arguments)-{'case_key','step_number','field','char_offset','char_count'}:
            return {'error':'source_reader_arguments_invalid','executed':False}
        return read_regression_step_cell(arguments.get('case_key'),arguments.get('step_number'),arguments.get('field'),arguments.get('char_offset',0),arguments.get('char_count',1500))
    if name == "knowledge_search":
        return knowledge_search(
            query=arguments["query"],
            limit=arguments.get("limit", 3),
            **({'source_namespace':arguments['source_namespace']} if arguments.get('source_namespace','all')!='all' else {}),
            **({'required_term':arguments['required_term']} if 'required_term' in arguments else {}),
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

    if name == "browser_inspect_saved_block_graph_semantic":
        if set(arguments) != {'request_id', 'exact_name'}:
            return {'error': 'saved_graph_arguments_invalid', 'executed': False}
        return inspect_saved_block_graph_semantic(
            arguments['request_id'], arguments['exact_name'],
        )

    if name == "browser_get_network_detail":
        return get_network_detail(
            arguments["request_id"]
        )

    if name == "browser_delete_json_resource":
        return delete_json_resource(
            arguments["collection_endpoint"],
            arguments["exact_name"],
            **({"expected_identifier": arguments["expected_identifier"]}
               if arguments.get("expected_identifier") is not None else {}),
        )

    if name == "browser_archive_json_resource":
        return archive_json_resource(
            arguments["collection_endpoint"],
            arguments["exact_name"],
            **({"expected_identifier": arguments["expected_identifier"]}
               if arguments.get("expected_identifier") is not None else {}),
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

    if name == "browser_verify_iframe_surface_readiness_semantic":
        return verify_iframe_surface_readiness_semantic(
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

    if name == "browser_verify_exact_form_required_contract_semantic":
        return verify_exact_form_required_contract_semantic(
            arguments["form"], arguments.get("expected_required_fields"),
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
    if name == "browser_inspect_combobox_contract_semantic":
        return inspect_combobox_contract_semantic(arguments["target"], arguments.get("exact", True))
    if name == "browser_inspect_listbox_contract_semantic":
        return inspect_listbox_contract_semantic(arguments["target"], arguments.get("exact", True))
    if name == "browser_inspect_menu_contract_semantic":
        return inspect_menu_contract_semantic(arguments["target"], arguments.get("exact", True))
    if name == "browser_inspect_progressbar_contract_semantic":
        return inspect_progressbar_contract_semantic(arguments["target"], arguments.get("exact", True))
    if name == "browser_inspect_meter_contract_semantic":
        return inspect_meter_contract_semantic(arguments["target"], arguments.get("exact", True))
    if name == "browser_inspect_spinbutton_contract_semantic":
        return inspect_spinbutton_contract_semantic(arguments["target"], arguments.get("exact", True))
    if name == "browser_inspect_text_contrast_semantic":
        return inspect_text_contrast_semantic()
    if name == "browser_inspect_text_clipping_semantic":
        return inspect_text_clipping_semantic()
    if name == "browser_inspect_target_size_semantic":
        return inspect_target_size_semantic(arguments.get("minimum_px", 24))
    if name == "browser_inspect_live_region_contract_semantic":
        return inspect_live_region_contract_semantic()
    if name == "browser_inspect_dialog_contract_semantic":
        return inspect_dialog_contract_semantic()
    if name == "browser_inspect_field_label_contract_semantic":
        return inspect_field_label_contract_semantic(arguments.get("form"), arguments.get("exact", True))
    if name == "browser_inspect_document_metadata_semantic":
        return inspect_document_metadata_semantic()
    if name == "browser_inspect_keyboard_shortcuts_semantic":
        return inspect_keyboard_shortcuts_semantic()
    if name == "browser_inspect_autofill_contract_semantic":
        return inspect_autofill_contract_semantic(arguments.get("form"), arguments.get("exact", True))
    if name == "browser_inspect_form_submission_contract_semantic":
        return inspect_form_submission_contract_semantic()
    if name == "browser_inspect_script_security_semantic":
        return inspect_script_security_semantic()
    if name == "browser_inspect_media_resource_semantic":
        return inspect_media_resource_semantic()
    if name == "browser_inspect_lazy_media_contract_semantic":
        return inspect_lazy_media_contract_semantic()
    if name == "browser_inspect_font_readiness_semantic":
        return inspect_font_readiness_semantic(arguments.get("wait_ms", 2000))
    if name == "browser_inspect_reduced_motion_contract_semantic":
        return inspect_reduced_motion_contract_semantic()
    if name == "browser_inspect_details_contract_semantic":
        return inspect_details_contract_semantic()
    if name == "browser_inspect_popover_contract_semantic":
        return inspect_popover_contract_semantic()
    if name == "browser_inspect_native_dialog_element_semantic":
        return inspect_native_dialog_element_semantic()
    if name == "browser_inspect_fieldset_contract_semantic":
        return inspect_fieldset_contract_semantic()
    if name == "browser_inspect_radio_group_contract_semantic":
        return inspect_radio_group_contract_semantic()
    if name == "browser_inspect_button_type_contract_semantic":
        return inspect_button_type_contract_semantic()
    if name == "browser_inspect_contenteditable_contract_semantic":
        return inspect_contenteditable_contract_semantic()
    if name == "browser_inspect_search_contract_semantic":
        return inspect_search_contract_semantic()
    if name == "browser_inspect_breadcrumb_contract_semantic":
        return inspect_breadcrumb_contract_semantic()
    if name == "browser_inspect_table_structure_contract_semantic":
        return inspect_table_structure_contract_semantic()
    if name == "browser_inspect_list_structure_contract_semantic":
        return inspect_list_structure_contract_semantic()
    if name == "browser_inspect_description_list_contract_semantic":
        return inspect_description_list_contract_semantic()
    if name == "browser_inspect_hash_link_contract_semantic":
        return inspect_hash_link_contract_semantic()
    if name == "browser_inspect_navigation_current_contract_semantic":
        return inspect_navigation_current_contract_semantic()
    if name == "browser_inspect_skip_link_contract_semantic":
        return inspect_skip_link_contract_semantic()
    if name == "browser_inspect_required_field_contract_semantic":
        return inspect_required_field_contract_semantic()
    if name == "browser_inspect_describedby_contract_semantic":
        return inspect_describedby_contract_semantic()
    if name == "browser_inspect_invalid_field_contract_semantic":
        return inspect_invalid_field_contract_semantic()
    if name == "browser_inspect_text_length_contract_semantic":
        return inspect_text_length_contract_semantic()
    if name == "browser_inspect_range_constraint_contract_semantic":
        return inspect_range_constraint_contract_semantic()
    if name == "browser_inspect_inputmode_contract_semantic":
        return inspect_inputmode_contract_semantic()
    if name == "browser_inspect_new_tab_link_contract_semantic":
        return inspect_new_tab_link_contract_semantic()
    if name == "browser_inspect_iframe_contract_semantic":
        return inspect_iframe_contract_semantic()
    if name == "browser_inspect_referrerpolicy_contract_semantic":
        return inspect_referrerpolicy_contract_semantic()
    if name == "browser_inspect_tabindex_contract_semantic":
        return inspect_tabindex_contract_semantic()
    if name == "browser_inspect_disabled_control_contract_semantic":
        return inspect_disabled_control_contract_semantic()
    if name == "browser_inspect_readonly_contract_semantic":
        return inspect_readonly_contract_semantic()
    if name == "browser_inspect_aria_controls_contract_semantic":
        return inspect_aria_controls_contract_semantic()
    if name == "browser_inspect_aria_labelledby_contract_semantic":
        return inspect_aria_labelledby_contract_semantic()
    if name == "browser_inspect_aria_owns_contract_semantic":
        return inspect_aria_owns_contract_semantic()
    if name == "browser_inspect_checkbox_contract_semantic":
        return inspect_checkbox_contract_semantic()
    if name == "browser_inspect_switch_contract_semantic":
        return inspect_switch_contract_semantic()
    if name == "browser_inspect_toggle_button_contract_semantic":
        return inspect_toggle_button_contract_semantic()
    if name == "browser_inspect_expanded_contract_semantic":
        return inspect_expanded_contract_semantic()
    if name == "browser_inspect_haspopup_contract_semantic":
        return inspect_haspopup_contract_semantic()
    if name == "browser_inspect_activedescendant_contract_semantic":
        return inspect_activedescendant_contract_semantic()
    if name == "browser_inspect_set_position_contract_semantic":
        return inspect_set_position_contract_semantic()
    if name == "browser_inspect_virtual_grid_contract_semantic":
        return inspect_virtual_grid_contract_semantic()
    if name == "browser_inspect_aria_level_contract_semantic":
        return inspect_aria_level_contract_semantic()
    if name == "browser_inspect_svg_accessibility_contract_semantic":
        return inspect_svg_accessibility_contract_semantic()
    if name == "browser_inspect_canvas_fallback_contract_semantic":
        return inspect_canvas_fallback_contract_semantic()
    if name == "browser_inspect_media_caption_contract_semantic":
        return inspect_media_caption_contract_semantic()
    if name == "browser_inspect_language_contract_semantic":
        return inspect_language_contract_semantic()
    if name == "browser_inspect_direction_contract_semantic":
        return inspect_direction_contract_semantic()
    if name == "browser_inspect_time_contract_semantic":
        return inspect_time_contract_semantic()
    if name == "browser_inspect_canonical_url_contract_semantic":
        return inspect_canonical_url_contract_semantic()
    if name == "browser_inspect_alternate_language_contract_semantic":
        return inspect_alternate_language_contract_semantic()
    if name == "browser_inspect_base_url_contract_semantic":
        return inspect_base_url_contract_semantic()

    if name == "browser_inspect_agent_telemetry_semantic":
        return inspect_agent_telemetry_semantic(
            arguments["ci_name"],
            arguments.get("max_age_seconds", 300),
        )

    if name == "browser_open_exact_table_row_details_semantic":
        return open_exact_table_row_details_semantic(arguments.get("name"))

    if name == "browser_verify_exact_table_row_tabs_semantic":
        return verify_exact_table_row_tabs_semantic(
            arguments.get("name"),
            arguments.get("tabs"),
            arguments.get("tablist"),
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

    if name == "browser_create_closed_command_stage_semantic":
        return {'error':'trusted_Core_job_case_context_required','executed':False}

    if name == "browser_inspect_closed_command_stage_semantic":
        return {'error':'trusted_Core_job_case_context_required','executed':False}

    if name == "browser_inspect_lab_plugin_inventory_semantic":
        if set(arguments)!={'target'}:return {'error':'exact_lab_inventory_arguments_required','mutation_executed':False}
        from tools.browser import _session
        from lab_plugin_inventory import inspect
        return inspect(_session,arguments['target'])

    if name == "browser_inspect_pinned_agent_readiness_semantic":
        from tools.browser import _session
        return _session.inspect_pinned_agent_readiness_semantic(arguments.get('ci_name'), arguments.get('agent_id'),
            arguments.get('plugin_name','osAudit'),arguments.get('plugin_version','1.3.4'))

    if name == "browser_inspect_pinned_agent_audit_semantic":
        from tools.browser import _session
        return _session.inspect_pinned_agent_audit_semantic(
            arguments.get('ci_name'), arguments.get('agent_id'), arguments.get('task_id'))

    if name == "browser_create_pinned_agent_audit_semantic":
        from tools.browser import _session
        return _session.create_pinned_agent_audit_semantic(
            arguments.get('ci_name'), arguments.get('agent_id'), arguments.get('core_version'), arguments.get('task_name'),
            arguments.get('plugin_name'),arguments.get('plugin_version'))

    if name == "browser_deliver_pinned_agent_plugin_semantic":
        from tools.browser import _session
        return _session.deliver_pinned_agent_plugin_semantic(
            arguments.get('ci_name'), arguments.get('agent_id'), arguments.get('core_version'),
            arguments.get('plugin_name'), arguments.get('version'))

    if name == "browser_create_pinned_agent_update_semantic":
        from tools.browser import _session
        return _session.create_pinned_agent_update_semantic(
            arguments.get('ci_name'), arguments.get('agent_id'), arguments.get('version'))

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
            arguments.get("item"),
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

    if name == "browser_scroll_table_horizontal_semantic":
        return scroll_table_horizontal_semantic(arguments.get("edge"), arguments.get("table"), arguments.get("exact", True))

    if name == "browser_sort_table_semantic":
        return sort_table_semantic(
            arguments["column"],
            arguments["direction"],
            arguments.get("table"),
            arguments.get("exact", True),
        )

    if name == "browser_verify_table_sort_roundtrip_semantic":
        return verify_table_sort_roundtrip_semantic(
            arguments["column"],
            arguments["direction"],
            arguments.get("table"),
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

    if name == "browser_verify_table_pagination_roundtrip_semantic":
        return verify_table_pagination_roundtrip_semantic(
            arguments["forward_control"],
            arguments["return_control"],
            arguments.get("table"),
        )

    if name == "browser_fill_table_filter_semantic":
        return fill_table_filter_semantic(
            arguments["column"],
            arguments["text"],
            arguments.get("table"),
            arguments.get("exact", True),
        )

    if name == "browser_verify_table_text_filter_roundtrip_semantic":
        return verify_table_text_filter_roundtrip_semantic(
            arguments["filter_name"],
            arguments["value"],
            arguments["column"],
            arguments.get("table"),
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

    if name == "browser_verify_dialog_wizard_roundtrip_semantic":
        return verify_dialog_wizard_roundtrip_semantic(
            arguments["trigger"], arguments["dialog"], arguments["steps"],
            arguments.get("next_button", "Next"),
            arguments.get("back_button", "Back"),
            arguments.get("close_button", "Cancel"),
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
