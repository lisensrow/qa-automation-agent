#!/opt/uqa/.venv/bin/python

import uqa


request_without_version = (
    "Строго read-only: на точной КЕ home-server-UC-ubuntu22 открой Agent → "
    "Plugins и проверь плагин VncServer по свежему аудиту. Без изменений."
)
target = uqa._agent_plugin_target_from_request(request_without_version)
assert target == {"plugin_name": "VncServer", "expected_version": None}
ci_name = uqa._agent_telemetry_ci_name_from_request(request_without_version)
assert ci_name == "home-server-UC-ubuntu22"
route = uqa._read_only_agent_plugin_route_message(
    request_without_version, ci_name, target,
)
assert route is not None
assert "Do not invent an expected version" in route["content"]
assert "Never click Add" in route["content"]

request_with_version = (
    "Только чтение: для exact CI test-windows в Plugins проверь "
    "VncServer версии 1.3.6 по свежему аудиту."
)
version_target = uqa._agent_plugin_target_from_request(request_with_version)
assert version_target == {
    "plugin_name": "VncServer", "expected_version": "1.3.6",
}
assert uqa._read_only_agent_plugin_route_message(
    "Измени плагин VncServer", "test-windows", version_target,
) is None

plugin_key = uqa._core_observation_call_key(
    "browser_inspect_agent_plugins_semantic",
    {
        "ci_name": " Example CI ",
        "plugin_name": " VncServer ",
        "expected_version": "1.3.6",
        "max_age_seconds": 60,
    },
)
assert plugin_key == (
    "browser_inspect_agent_plugins_semantic",
    "example ci",
    "vncserver",
    "1.3.6",
)
assert plugin_key == uqa._core_observation_call_key(
    "browser_inspect_agent_plugins_semantic",
    {
        "ci_name": "example ci",
        "plugin_name": "vncserver",
        "expected_version": "1.3.6",
        "max_age_seconds": 3600,
    },
)

steps = [
    (
        "browser_open_page", {"url": "https://uc.lab.local"},
        "browser_inspect_table_row",
    ),
    (
        "browser_inspect_table_row",
        {"name": ci_name, "exact": True},
        "browser_click_semantic",
    ),
    (
        "browser_click_semantic",
        {"name": ci_name, "exact": True, "role": "row"},
        "name='Agent'",
    ),
    (
        "browser_click_semantic",
        {"name": "Agent", "exact": True, "role": "tab"},
        "name='Plugins'",
    ),
    (
        "browser_click_semantic",
        {"name": "Plugins", "exact": True, "role": "tab"},
        "browser_inspect_agent_plugins_semantic",
    ),
]
for tool_name, arguments, expected in steps:
    followup = uqa._read_only_agent_plugin_followup(
        tool_name,
        arguments,
        {"status": "ok"},
        ci_name,
        target,
    )
    assert followup is not None
    assert expected in followup["content"]

final_followup = uqa._read_only_agent_plugin_followup(
    "browser_click_semantic",
    {"name": "Plugins", "exact": True, "role": "tab"},
    {"status": "ok"},
    ci_name,
    target,
)
assert '"plugin_name": "VncServer"' in final_followup["content"]
assert "expected_version" not in final_followup["content"]

print("read-only agent plugin route smoke: PASS")
