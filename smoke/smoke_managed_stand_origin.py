#!/opt/uqa/.venv/bin/python

import ast
from pathlib import Path


source = Path("uqa.py").read_text(encoding="utf-8")
tree = ast.parse(source)
functions = [
    node
    for node in tree.body
    if isinstance(node, ast.FunctionDef)
    and node.name in {
        "_managed_stand_origin_check",
        "_enforce_managed_stand_origin",
        "_managed_agent_origin_guard_applies",
    }
]
scope = {}
exec(
    compile(ast.Module(body=functions, type_ignores=[]), "uqa.py", "exec"),
    scope,
)
check = scope["_managed_stand_origin_check"]
enforce = scope["_enforce_managed_stand_origin"]
guard_applies = scope["_managed_agent_origin_guard_applies"]

same = check(
    "https://Stand.Example.Test",
    {"current_url": "https://stand.example.test/cmdb?limit=50"},
)
assert same == {
    "matches": True,
    "expected_origin": "https://stand.example.test",
    "actual_origin": "https://stand.example.test",
}

default_port = check(
    "https://stand.example.test:443/path",
    {"final_url": "https://stand.example.test/redirected"},
)
assert default_port["matches"] is True

wrong_host = check(
    "https://stand.example.test",
    {"current_url": "https://stand.example.test.evil.invalid/cmdb"},
)
assert wrong_host["matches"] is False
assert wrong_host["actual_origin"] == (
    "https://stand.example.test.evil.invalid"
)

wrong_scheme = check(
    "https://stand.example.test",
    {"current_url": "http://stand.example.test/cmdb"},
)
assert wrong_scheme["matches"] is False

wrong_port = check(
    "https://stand.example.test",
    {"current_url": "https://stand.example.test:8443/cmdb"},
)
assert wrong_port["matches"] is False

missing = check(
    "https://stand.example.test",
    {"http_status": 200},
)
assert missing == {
    "matches": False,
    "expected_origin": "https://stand.example.test",
    "actual_origin": None,
}

invalid_expected = check(
    "not-a-url",
    {"current_url": "https://stand.example.test/cmdb"},
)
assert invalid_expected["matches"] is False
assert invalid_expected["expected_origin"] is None

allowed_result = {
    "http_status": 200,
    "current_url": "https://stand.example.test/cmdb",
}
assert enforce("https://stand.example.test", allowed_result) is allowed_result

blocked_result = enforce(
    "https://stand.example.test",
    {
        "http_status": 200,
        "current_url": "https://wrong.example.test/cmdb",
    },
)
assert blocked_result["error"] == "managed_stand_origin_mismatch"
assert blocked_result["status"] == "blocked"
assert blocked_result["executed"] is False
assert blocked_result["expected_origin"] == "https://stand.example.test"
assert blocked_result["actual_origin"] == "https://wrong.example.test"

assert guard_applies(
    "open_page",
    "browser_open_page",
    {"http_status": 200, "current_url": "https://stand.example.test"},
)
assert not guard_applies(
    "open_page",
    "browser_open_page",
    {"http_status": 500, "current_url": "https://stand.example.test"},
)
for phase, tool_name in (
    ("route", "browser_open_agent_tasks_semantic"),
    ("probe", "browser_probe_capabilities"),
    ("readiness", "browser_inspect_agent_telemetry_semantic"),
):
    assert guard_applies(
        phase,
        tool_name,
        {"executed": True, "current_url": "https://stand.example.test/cmdb"},
    )
    assert not guard_applies(
        phase,
        tool_name,
        {"error": "failed", "executed": False},
    )
assert not guard_applies(
    "create",
    "browser_create_managed_agent_task_semantic",
    {"executed": True},
)

assert 'managed_agent_workflow_phase = "verdict"' in source
assert "MANAGED STAND ORIGIN BLOCKED" in source

print("managed stand-origin verification smoke: PASS")
