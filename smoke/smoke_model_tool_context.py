#!/opt/uqa/.venv/bin/python

import json

import uqa


uqa_source = open(uqa.__file__, encoding="utf-8").read()
assert "failed_semantic_inspections = {}" in uqa_source
assert "last_browser_fingerprint" in uqa_source
assert "repeated_semantic_inspection_blocked" in uqa_source
assert "Do not repeat browser_inspect_semantic" in uqa_source

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
