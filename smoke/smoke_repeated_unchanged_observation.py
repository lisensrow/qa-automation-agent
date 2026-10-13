#!/opt/uqa/.venv/bin/python

import uqa


assert uqa._unchanged_snapshot_observation_key(
    "browser_inspect_table_semantic",
    {"table": " Exact CI "},
) == (
    "browser_inspect_table_semantic",
    '{"table": " Exact CI "}',
)
assert uqa._unchanged_snapshot_observation_key(
    "browser_get_state", {},
) is None

unchanged_turns = iter([
    {"message": {"content": "", "tool_calls": [{"function": {
        "name": "browser_inspect_table_semantic",
        "arguments": {"table": "home-server-UC-ubuntu22"},
    }}]}},
    {"message": {"content": "", "tool_calls": [{"function": {
        "name": "browser_inspect_table_semantic",
        "arguments": {"table": "home-server-UC-ubuntu22"},
    }}]}},
])
executed_unchanged = []
uqa.ask_ollama = lambda messages, **kwargs: next(unchanged_turns)


def fake_unchanged(name, arguments, messages, **kwargs):
    executed_unchanged.append((name, arguments))
    return {
        "inspection_status": "observed",
        "current_url": "https://stand/cmdb",
        "text_preview": "home-server-UC-ubuntu22 online",
    }


uqa.execute_tool_with_policy = fake_unchanged
unchanged_messages = []
uqa.run_turn(unchanged_messages)
assert len(executed_unchanged) == 1
assert next(unchanged_turns, None) is None

changed_turns = iter([
    {"message": {"content": "", "tool_calls": [{"function": {
        "name": "browser_inspect_table_semantic",
        "arguments": {"table": "home-server-UC-ubuntu22"},
    }}]}},
    {"message": {"content": "", "tool_calls": [{"function": {
        "name": "browser_click_semantic",
        "arguments": {"name": "Agent", "role": "tab"},
    }}]}},
    {"message": {"content": "", "tool_calls": [{"function": {
        "name": "browser_inspect_table_semantic",
        "arguments": {"table": "home-server-UC-ubuntu22"},
    }}]}},
    {"message": {"content": "Observed"}},
])
executed_changed = []
uqa.ask_ollama = lambda messages, **kwargs: next(changed_turns)


def fake_changed(name, arguments, messages, **kwargs):
    executed_changed.append(name)
    if len(executed_changed) == 1:
        return {
            "inspection_status": "observed",
            "current_url": "https://stand/cmdb",
            "text_preview": "Summary home-server-UC-ubuntu22",
        }
    if len(executed_changed) == 2:
        return {
            "click_status": "executed",
            "current_url": "https://stand/cmdb/agent",
            "text_preview": "Agent Plugins",
        }
    return {
        "inspection_status": "observed",
        "current_url": "https://stand/cmdb/agent",
        "text_preview": "Agent Plugins VncServer",
    }


uqa.execute_tool_with_policy = fake_changed
uqa.run_turn([])
assert executed_changed == [
    "browser_inspect_table_semantic",
    "browser_click_semantic",
    "browser_inspect_table_semantic",
]

print("smoke_repeated_unchanged_observation: PASS")
