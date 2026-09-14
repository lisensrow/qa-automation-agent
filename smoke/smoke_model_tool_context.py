#!/opt/uqa/.venv/bin/python

import json

import uqa


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
