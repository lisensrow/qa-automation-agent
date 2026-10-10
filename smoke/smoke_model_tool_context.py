#!/opt/uqa/.venv/bin/python

import json

import uqa


uqa_source = open(uqa.__file__, encoding="utf-8").read()
assert "failed_semantic_inspections = {}" in uqa_source
assert "last_browser_fingerprint" in uqa_source
assert "repeated_semantic_inspection_blocked" in uqa_source
assert "Do not repeat browser_inspect_semantic" in uqa_source
assert "managed_agent_route_required" in uqa_source
assert uqa.classify_tool_action(
    "browser_click_semantic", {"name": "plus"},
) == "write"
assert uqa.classify_tool_action(
    "browser_click_semantic", {"name": "+"},
) == "write"
telemetry_key = uqa._core_observation_call_key(
    "browser_inspect_agent_telemetry_semantic",
    {"ci_name": " Example CI ", "max_age_seconds": 60},
)
assert telemetry_key == (
    "browser_inspect_agent_telemetry_semantic", "example ci",
)
assert telemetry_key == uqa._core_observation_call_key(
    "browser_inspect_agent_telemetry_semantic",
    {"ci_name": "example ci", "max_age_seconds": 3600},
)
assert uqa._completed_core_observation_key(
    "browser_inspect_agent_telemetry_semantic",
    {"ci_name": "example ci"},
    {"observation_result": "PASS", "uqa_evidence_id": "ev-one"},
) == telemetry_key
assert uqa._completed_core_observation_key(
    "browser_inspect_agent_telemetry_semantic",
    {"ci_name": "example ci"},
    {"observation_result": "PASS", "uqa_evidence_id": None},
) is None

telemetry_request = (
    "Строго read-only: найди конфигурационную единицу test-windows и "
    "проверь online, CPU и RAM. Не нажимай Add, Save, Delete или плюс."
)
telemetry_ci_name = uqa._agent_telemetry_ci_name_from_request(
    telemetry_request
)
assert telemetry_ci_name == "test-windows"
route_message = uqa._read_only_agent_telemetry_route_message(
    telemetry_request,
    telemetry_ci_name,
)
assert route_message is not None
assert "role=row" in route_message["content"]
assert "Never click Add" in route_message["content"]
assert uqa._read_only_agent_telemetry_route_message(
    "Создай тестовую задачу для test-windows.",
    "test-windows",
) is None
row_followup = uqa._read_only_agent_telemetry_followup(
    "browser_inspect_table_row",
    {"name": "test-windows", "exact": True},
    {"table_row_name": "test-windows"},
    "test-windows",
)
assert row_followup is not None
assert "role='row'" in row_followup["content"]
open_followup = uqa._read_only_agent_telemetry_followup(
    "browser_open_page",
    {"url": "https://example.test/cmdb"},
    {"http_status": 200},
    "test-windows",
)
assert open_followup is not None
assert "browser_inspect_table_row" in open_followup["content"]
assert "Add/plus" in open_followup["content"]
telemetry_followup = uqa._read_only_agent_telemetry_followup(
    "browser_click_semantic",
    {"name": "test-windows", "exact": True, "role": "row"},
    {"clicked_element": {"text": "test-windows"}},
    "test-windows",
)
assert telemetry_followup is not None
assert "browser_inspect_agent_telemetry_semantic" in telemetry_followup["content"]

managed_request = (
    "Create windows_cmd_echo_marker_v1 for exact CI test-windows and verify it"
)
assert uqa._managed_agent_ci_name_from_request(managed_request) == "test-windows"
assert uqa._managed_agent_ci_name_from_request(
    "Create windows_cmd_echo_marker_v1 for exact CI test-windows: verify it"
) == "test-windows"
assert uqa._managed_agent_fixture_from_request(managed_request) == (
    "windows_cmd_echo_marker_v1"
)
managed_request_with_url = (
    managed_request + " on https://uc.lab.local/."
)
assert uqa._managed_agent_stand_url_from_request(
    managed_request_with_url
) == "https://uc.lab.local/"
assert uqa._managed_agent_stand_url_from_request(
    managed_request + " on https://uc.lab.local:"
) == "https://uc.lab.local"
original_get_stand = uqa.get_stand
try:
    uqa.get_stand = lambda stand_id: {
        "stand_id": stand_id,
        "web_url": "https://resolved.lab.local",
    }
    assert uqa._managed_agent_stand_url_for_job(
        {"stand": "saved-stand"}, managed_request_with_url,
    ) == "https://resolved.lab.local"
finally:
    uqa.get_stand = original_get_stand
assert uqa._managed_agent_stand_url_for_job(
    {}, managed_request_with_url,
) == "https://uc.lab.local/"
assert uqa._managed_agent_required_call(
    "open_page", "test-windows", "windows_cmd_echo_marker_v1", None,
    managed_request_with_url,
) == {
    "tool": "browser_open_page",
    "arguments": {"url": "https://uc.lab.local/"},
}
assert uqa._managed_agent_required_call(
    "open_page", "test-windows", "windows_cmd_echo_marker_v1", None,
    managed_request_with_url, "https://resolved.lab.local",
) == {
    "tool": "browser_open_page",
    "arguments": {"url": "https://resolved.lab.local"},
}
assert uqa._managed_agent_required_call(
    "route", "test-windows", "windows_cmd_echo_marker_v1", None,
) == {
    "tool": "browser_open_agent_tasks_semantic",
    "arguments": {"ci_name": "test-windows"},
}
assert uqa._managed_agent_required_call(
    "probe", "test-windows", "windows_cmd_echo_marker_v1", None,
) == {
    "tool": "browser_probe_capabilities",
    "arguments": {},
}
assert uqa._managed_agent_required_call(
    "readiness", "test-windows", "windows_cmd_echo_marker_v1", None,
) == {
    "tool": "browser_inspect_agent_telemetry_semantic",
    "arguments": {"ci_name": "test-windows"},
}
assert uqa._managed_agent_required_call(
    "create", "test-windows", "windows_cmd_echo_marker_v1", None,
) == {
    "tool": "browser_create_managed_agent_task_semantic",
    "arguments": {
        "ci_name": "test-windows",
        "fixture_id": "windows_cmd_echo_marker_v1",
    },
}
assert uqa._managed_agent_required_call(
    "verify", "test-windows", "windows_cmd_echo_marker_v1", "task-id",
) == {
    "tool": "browser_inspect_managed_agent_task_result_semantic",
    "arguments": {"ci_name": "test-windows", "task_id": "task-id"},
}
assert uqa._managed_agent_workflow_call_allowed(
    "probe", "test-windows", "windows_cmd_echo_marker_v1", None,
    "browser_probe_capabilities", {},
)
assert uqa._managed_agent_workflow_call_allowed(
    "readiness", "test-windows", "windows_cmd_echo_marker_v1", None,
    "browser_inspect_agent_telemetry_semantic", {"ci_name": "test-windows"},
)
assert not uqa._managed_agent_workflow_call_allowed(
    "readiness", "test-windows", "windows_cmd_echo_marker_v1", None,
    "browser_inspect_agent_telemetry_semantic", {"ci_name": "other-ci"},
)
ready_result = {
    "ci_name": "test-windows",
    "observation_result": "PASS",
    "monitoring_fresh": True,
    "statuses": {"ui": "online", "ci": "online", "agent": "online"},
    "uqa_evidence_id": "ev-ready",
}
assert uqa._managed_agent_readiness_allows_create("test-windows", ready_result)
assert not uqa._managed_agent_readiness_allows_create(
    "test-windows", {**ready_result, "monitoring_fresh": False},
)
assert not uqa._managed_agent_readiness_allows_create(
    "test-windows", {**ready_result, "statuses": {"agent": "offline"}},
)
assert not uqa._managed_agent_readiness_allows_create(
    "other-ci", ready_result,
)
assert uqa._managed_agent_route_failed({
    "error": "table_row_not_found",
    "navigation_status": "blocked",
    "mutation_executed": False,
})
assert not uqa._managed_agent_route_failed({
    "navigation_status": "ready",
    "mutation_executed": False,
})
assert not uqa._managed_agent_route_failed({
    "error": "unexpected",
    "navigation_status": "blocked",
    "mutation_executed": True,
})
assert not uqa._managed_agent_workflow_call_allowed(
    "create", "test-windows", "windows_cmd_echo_marker_v1", None,
    "browser_probe_capabilities", {},
)
assert not uqa._managed_agent_workflow_call_allowed(
    "create", "test-windows", "windows_cmd_echo_marker_v1", None,
    "browser_click_semantic", {"name": "Create task"},
)
next_step_message = uqa._managed_agent_next_step_message({
    "tool": "browser_probe_capabilities",
    "arguments": {},
})
assert next_step_message["role"] == "user"
assert "browser_probe_capabilities" in next_step_message["content"]
assert 'managed_agent_workflow_phase == "probe"' in uqa_source
assert 'managed_agent_workflow_phase == "readiness"' in uqa_source
assert 'managed_agent_workflow_phase == "verdict"' in uqa_source
assert "[UQA CORE: MANAGED AGENT ROUTE BLOCKED]" in uqa_source
assert "managed_agent_route_required = None" in uqa_source
assert not uqa._managed_agent_workflow_call_allowed(
    "verdict", "test-windows", "windows_cmd_echo_marker_v1", "task-id",
    "resource_register", {"resource_type": "agent_task"},
)
assert uqa._managed_agent_ci_name_from_request(
    "Создай windows_cmd_echo_marker_v1 для точной КЕ test-windows."
) == "test-windows"
route_requirement = uqa._managed_agent_route_requirement(
    managed_request,
    "browser_inspect_table_row",
    {"name": "test-windows", "exact": True},
    {"row_match_count": 1},
)
assert route_requirement == {
    "tool": "browser_open_agent_tasks_semantic",
    "arguments": {"ci_name": "test-windows"},
}
assert uqa._managed_agent_route_call_matches(
    route_requirement,
    "browser_open_agent_tasks_semantic",
    {"ci_name": "test-windows"},
)
assert not uqa._managed_agent_route_call_matches(
    route_requirement,
    "browser_click_semantic",
    {"name": "Administration", "role": "menuitem"},
)
assert uqa._managed_agent_route_requirement(
    managed_request,
    "browser_inspect_table_row",
    {"name": "other-ci", "exact": True},
    {"row_match_count": 1},
) is None

semantic_turns = iter([
    {
        "message": {
            "content": "",
            "tool_calls": [{
                "function": {
                    "name": "browser_inspect_semantic",
                    "arguments": {
                        "name": "missing exact row",
                        "exact": True,
                        "role": "option",
                    },
                }
            }],
        }
    },
    {
        "message": {
            "content": "",
            "tool_calls": [{
                "function": {
                    "name": "browser_inspect_semantic",
                    "arguments": {
                        "name": "missing exact row",
                        "exact": True,
                        "role": "button",
                    },
                }
            }],
        }
    },
])
executed_semantic_calls = []
uqa.ask_ollama = lambda messages: next(semantic_turns)


def fake_execute_tool(name, arguments, messages, **kwargs):
    executed_semantic_calls.append((name, arguments))
    return {
        "error": "semantic_element_not_found",
        "status": "error",
    }


uqa.execute_tool_with_policy = fake_execute_tool
semantic_messages = []
uqa.run_turn(semantic_messages)
assert len(executed_semantic_calls) == 1
assert next(semantic_turns, None) is None

changed_page_turns = iter([
    {"message": {"content": "", "tool_calls": [{"function": {
        "name": "browser_inspect_semantic",
        "arguments": {"name": "Plugins", "role": "tab"},
    }}]}},
    {"message": {"content": "", "tool_calls": [{"function": {
        "name": "browser_click_semantic",
        "arguments": {"name": "Agent", "role": "tab"},
    }}]}},
    {"message": {"content": "", "tool_calls": [{"function": {
        "name": "browser_inspect_semantic",
        "arguments": {"name": "Plugins", "role": "tab"},
    }}]}},
    {"message": {"content": "Observed"}},
])
executed_after_navigation = []
uqa.ask_ollama = lambda messages: next(changed_page_turns)


def fake_changed_page(name, arguments, messages, **kwargs):
    executed_after_navigation.append(name)
    if len(executed_after_navigation) == 1:
        return {
            "error": "semantic_element_not_found", "status": "error",
            "current_url": "https://stand/cmdb", "text_preview": "Summary",
        }
    if len(executed_after_navigation) == 2:
        return {
            "click_status": "executed", "current_url": "https://stand/cmdb",
            "text_preview": "Summary Agent Plugins",
        }
    return {
        "inspection_status": "observed", "current_url": "https://stand/cmdb",
        "text_preview": "Summary Agent Plugins",
    }


uqa.execute_tool_with_policy = fake_changed_page
uqa.run_turn([])
assert executed_after_navigation == [
    "browser_inspect_semantic", "browser_click_semantic",
    "browser_inspect_semantic",
]

mutation_turns = iter([
    {
        "message": {
            "content": "",
            "tool_calls": [{
                "function": {
                    "name": "browser_click_semantic",
                    "arguments": {
                        "name": "Archive",
                        "exact": True,
                        "role": "menuitem",
                    },
                }
            }],
        }
    },
    {
        "message": {
            "content": "",
            "tool_calls": [{
                "function": {
                    "name": "browser_click_semantic",
                    "arguments": {
                        "name": "Archive",
                        "exact": True,
                        "role": "menuitem",
                    },
                }
            }],
        }
    },
])
executed_mutation_calls = []
uqa.ask_ollama = lambda messages: next(mutation_turns)


def fake_blocked_mutation(name, arguments, messages, **kwargs):
    executed_mutation_calls.append((name, arguments))
    return {
        "error": "tool_policy_blocked",
        "status": "blocked_by_policy",
        "executed": False,
        "action_class": "destructive",
        "action_policy_status": "blocked",
    }


uqa.execute_tool_with_policy = fake_blocked_mutation
uqa.run_turn([])
assert len(executed_mutation_calls) == 1
assert next(mutation_turns, None) is None

identifier_messages = [{
    "role": "tool",
    "content": json.dumps({
        "semantic_name": "resource-name",
        "identifier_value": "observed-id-123",
    }),
}]
assert uqa._tool_history_observed_identifier(
    identifier_messages,
    "observed-id-123",
)
assert not uqa._tool_history_observed_identifier(
    identifier_messages,
    "resource-name",
)


elements = []

for index in range(100):
    elements.append({
        "element_id": f"e{index}",
        "tag": "a",
        "role": "link",
        "text": (f"Navigation {index} " * 30),
        "table_context": {
            "section": "tbody",
            "row_text": (f"Row {index} " * 100),
            "data_cell_count": 8,
        },
        "enabled": True,
    })

elements[-1] = {
    "element_id": "e99",
    "tag": "li",
    "role": "menuitem",
    "text": "Create Location",
    "enabled": True,
}

raw = {
    "status": "ok",
    "current_url": "https://qa.example/cmdb",
    "text_preview": "Page text " * 1000,
    "interactive_elements": elements,
    "network_requests": [
        {
            "request_id": f"n{index}",
            "method": "GET",
            "url": "/api/items?payload=" + ("x" * 1000),
            "status": 200,
        }
        for index in range(30)
    ],
    "console_errors": [],
    "http_errors": [],
    "failed_requests": [],
}

view = uqa.tool_result_for_model(
    "browser_click_semantic",
    raw,
    max_chars=14000,
)
serialized = json.dumps(view, ensure_ascii=False)

assert len(serialized) <= 14000
assert view["model_view_compacted"] is True
assert view["interactive_elements_total"] == 100
assert view["network_requests_total"] == 30
assert any(
    item.get("role") == "menuitem"
    and item.get("text") == "Create Location"
    for item in view["interactive_elements"]
)
assert len(raw["text_preview"]) > len(view["text_preview"])
assert len(raw["interactive_elements"]) == 100
assert uqa.tool_result_for_model("ssh_docker_ps", raw) is raw

browser_content = json.dumps(view, ensure_ascii=False)
messages = [
    {"role": "system", "content": "system"},
    {
        "role": "tool",
        "tool_name": "knowledge_search",
        "content": "knowledge stays unchanged",
    },
]

for index in range(4):
    state = dict(view)
    state["current_url"] = f"https://qa.example/step-{index}"
    messages.append({
        "role": "tool",
        "tool_name": "browser_get_state",
        "content": json.dumps(state, ensure_ascii=False),
    })

prepared = uqa.messages_for_model(messages)
assert prepared is not messages
assert prepared[1]["content"] == "knowledge stays unchanged"
assert prepared[-1]["content"] == messages[-1]["content"]
assert len(prepared[-2]["content"]) < len(browser_content) / 4
assert json.loads(prepared[-2]["content"])["model_history_compacted"] is True
assert messages[-2]["content"] != prepared[-2]["content"]

print("smoke_model_tool_context: PASS")
