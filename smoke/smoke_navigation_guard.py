import ast
import json
import re
from pathlib import Path


tree = ast.parse(Path("uqa.py").read_text(encoding="utf-8"))
names = {
    "_latest_user_text",
    "_request_has_explicit_create_intent",
    "_generic_create_requires_navigation_preflight",
    "_history_has_successful_interact_navigation",
    "_latest_browser_state_for_navigation",
    "_latest_state_matches_navigation_target",
    "_managed_navigation_ready",
    "_successful_clicked_semantic_names",
    "_latest_unique_unnamed_icon_hints",
    "_latest_navigation_labels",
    "_latest_navigation_role",
    "_latest_navigation_knowledge",
    "_navigation_task_text",
    "_deterministic_navigation_label",
    "_parse_navigation_resolver_choice",
    "_resolve_navigation_label",
    "managed_navigation_preflight_check",
    "add_managed_navigation_preflight_advisory",
    "_latest_required_navigation_candidate",
    "_navigation_candidate_matches",
}
module = ast.Module(
    body=[
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ],
    type_ignores=[],
)
scope = {
    "json": json,
    "re": re,
    "_PENDING_NAVIGATION_CANDIDATES": {},
    "NAVIGATION_CONCEPT_GROUPS": (
        ("access", "доступ", "zone", "зон"),
        ("administr", "администр"),
        ("manage", "management", "управлен"),
        ("user", "пользоват"),
        ("role", "рол"),
        ("security", "безопас"),
        ("setting", "настрой"),
        ("server", "сервер"),
        ("agent", "агент"),
        ("integrat", "интеграц"),
        ("policy", "политик"),
        ("repositor", "репозитор"),
        ("computer", "компьют", "свт"),
        ("location", "локац", "местопол", "dictionar", "справоч", "словар"),
    ),
    "execute_tool": lambda name, arguments: {
        "status": "ok",
        "results": [{"heading": "Access zones"}],
    },
    "ask_ollama": lambda messages, tools: {
        "message": {"content": '{"label":"Administration"}'}
    },
}
exec(compile(module, "uqa.py", "exec"), scope)
check = scope["managed_navigation_preflight_check"]
add_advisory = scope[
    "add_managed_navigation_preflight_advisory"
]
latest_knowledge = scope["_latest_navigation_knowledge"]
navigation_task_text = scope["_navigation_task_text"]
latest_required_navigation_candidate = scope[
    "_latest_required_navigation_candidate"
]
navigation_candidate_matches = scope[
    "_navigation_candidate_matches"
]
deterministic_navigation_label = scope[
    "_deterministic_navigation_label"
]
managed_navigation_ready = scope["_managed_navigation_ready"]

assert "Access zones" in latest_knowledge([{
    "role": "tool",
    "tool_name": "knowledge_search",
    "content": {"results": [{"heading": "Access zones"}]},
}])
assert navigation_task_text([{
    "role": "user",
    "content": (
        "[UQA CORE: REGRESSION CASE]\n"
        "Internal workflow instructions.\n"
        "Задача: Создай тестовую зону.\n"
        "Ожидаемый результат: null\n"
        "General context and cleanup instructions."
    ),
}]) == "Создай тестовую зону."
assert deterministic_navigation_label(
    "Создай временную тестовую зону и автоматически очисти ресурс",
    "Зоны доступа",
    [
        "Automation & policies",
        "General settings",
        "Server management",
        "Access management",
    ],
) == "Access management"
assert deterministic_navigation_label(
    "Создай временную тестовую зону",
    "Agent package management",
    ["General settings", "Access management", "Agent management"],
) == "Access management"
assert deterministic_navigation_label(
    "Создай временную тестовую зону",
    "Зоны доступа",
    ["Access zones", "Users", "Roles"],
) == "Access zones"
assert deterministic_navigation_label(
    "Создай тестовую Location",
    "Create Location",
    ["CMDB", "Dictionaries", "Administration"],
) == "Dictionaries"
assert deterministic_navigation_label(
    "Создай тестовую Location",
    "Create Location",
    ["Org Units", "Locations", "Tags"],
) == "Locations"
assert deterministic_navigation_label(
    "Create a resource",
    "",
    ["Section one", "Section two"],
) is None
pending_candidate = {
    "tool": "browser_click_semantic",
    "arguments": {
        "name": "Access management",
        "exact": True,
        "role": "menuitem",
    },
    "action_class": "interact",
}
assert latest_required_navigation_candidate([{
    "role": "tool",
    "tool_name": "browser_click_semantic",
    "content": json.dumps({
        "navigation_preflight_status": "required",
        "required_navigation_candidate": pending_candidate,
    }),
}, {
    "role": "assistant",
    "content": "Navigation successful.",
}]) == pending_candidate
assert latest_required_navigation_candidate([{
    "role": "tool",
    "tool_name": "browser_click_semantic",
    "content": json.dumps({"click_status": "executed"}),
}]) is None
assert navigation_candidate_matches(
    "browser_click_semantic",
    {
        "name": "access MANAGEMENT",
        "exact": True,
        "role": "MENUITEM",
    },
    pending_candidate,
) is True
assert navigation_candidate_matches(
    "browser_click_semantic",
    {
        "name": "General settings",
        "exact": True,
        "role": "menuitem",
    },
    pending_candidate,
) is False


def run(messages, *, semantic_name="Add", job_id="job", case_id="case"):
    return check(
        "browser_click_semantic",
        {"name": semantic_name, "exact": True},
        messages,
        "write",
        "confirm_mutations",
        job_id,
        case_id,
    )


blocked = run([])
assert blocked["error"] == "managed_navigation_preflight_required"
assert blocked["executed"] is False

browser_state = [{
    "role": "tool",
    "tool_name": "browser_open_page",
    "content": json.dumps({
        "status": "observed",
        "unique_unnamed_icon_hints": ["plus"],
        "navigation_labels": ["CMDB", "Administration"],
    }),
}]
candidate = run(browser_state)["required_navigation_candidate"]
assert candidate["tool"] == "browser_click_semantic"
assert candidate["arguments"] == {"name": "plus", "exact": True}
assert run(browser_state)["available_navigation_labels"] == [
    "CMDB",
    "Administration",
]

open_result = json.loads(browser_state[0]["content"])
open_advisory = add_advisory(
    "browser_open_page",
    open_result,
    [{"role": "user", "content": "Create an access zone"}],
    "confirm_mutations",
    "job",
    "case",
)
assert open_advisory["navigation_preflight_status"] == "required"
assert next(iter(open_advisory)) == "navigation_preflight_status"
assert open_advisory["required_navigation_candidate"]["arguments"] == {
    "name": "plus",
    "exact": True,
}

read_only_advisory = add_advisory(
    "browser_open_page",
    open_result,
    [{"role": "user", "content": (
        "Read-only: inspect a CI already visible in CMDB. "
        "Do not create resources. Save evidence."
    )}],
    "confirm_mutations",
    "readonly-job",
    "case",
)
assert "navigation_preflight_status" not in read_only_advisory
assert ("readonly-job", "case") not in scope["_PENDING_NAVIGATION_CANDIDATES"]

menu_state = [{
    "role": "user",
    "content": "Create an access zone",
}, {
    "role": "tool",
    "tool_name": "browser_click_semantic",
    "content": json.dumps({
        "current_url": "https://example.test/start",
        "semantic_strategy": "role",
        "semantic_name": "plus",
        "click_status": "executed",
        "unique_unnamed_icon_hints": ["plus"],
        "navigation_labels": ["CMDB", "Administration"],
    }),
}]
assert scope["_latest_navigation_labels"](
    menu_state + [{
        "role": "tool",
        "tool_name": "browser_click_semantic",
        "content": json.dumps({
            "semantic_name": "Administration",
            "click_status": "executed",
            "navigation_labels": [
                (
                    "Administration\nGeneral settings\n"
                    "Server management\nAccess management"
                ),
                "Administration",
                "Access management",
            ],
        }),
    }]
) == ["Access management"]
assert scope["_latest_navigation_role"]([{
    "role": "tool",
    "tool_name": "browser_click_semantic",
    "content": json.dumps({
        "interactive_elements": [
            {
                "tag": "button",
                "aria_label": "Access zones",
                "enabled": False,
                "disabled_attribute": True,
            },
            {
                "tag": "a",
                "role": "",
                "text": "Access zones",
                "enabled": True,
            },
            {
                "tag": "a",
                "role": "menuitem",
                "text": "Access zones",
                "enabled": True,
            },
        ],
    }),
}], "Access zones") == "menuitem"
assert scope["_latest_navigation_role"]([{
    "role": "tool",
    "tool_name": "browser_click_semantic",
    "content": json.dumps({
        "interactive_elements": [{
            "tag": "a",
            "role": "",
            "text": "Administration",
            "enabled": True,
        }],
    }),
}], "Administration") is None
resolved = run(menu_state)["required_navigation_candidate"]
assert resolved["arguments"] == {
    "name": "Administration",
    "exact": True,
}

menu_result = json.loads(menu_state[-1]["content"])
menu_advisory = add_advisory(
    "browser_click_semantic",
    menu_result,
    menu_state[:-1],
    "confirm_mutations",
    "job",
    "case",
)
assert menu_advisory["navigation_preflight_status"] == "required"
assert next(iter(menu_advisory)) == "navigation_preflight_status"
assert menu_advisory["required_navigation_candidate"]["arguments"] == {
    "name": "Administration",
    "exact": True,
}
assert scope["_PENDING_NAVIGATION_CANDIDATES"][(
    "job",
    "case",
)] == menu_advisory["required_navigation_candidate"]

failed_navigation = [{
    "role": "tool",
    "tool_name": "browser_click_semantic",
    "content": json.dumps({
        "action_class": "interact",
        "status": "error",
        "executed": False,
    }),
}]
assert run(failed_navigation)["status"] == "blocked_by_policy"

successful_navigation = [
    {
        "role": "tool",
        "tool_name": "browser_open_page",
        "content": json.dumps({
            "current_url": "https://example.test/start",
        }),
    },
    {
        "role": "tool",
        "tool_name": "browser_click_semantic",
        "content": json.dumps({
            "action_class": "interact",
            "action_policy_status": "auto_allowed",
            "click_status": "executed",
            "current_url": "https://example.test/target",
        }),
    },
]
assert run(successful_navigation) is None

wrong_location_branch = [
    {
        "role": "user",
        "content": "Create a Location",
    },
    successful_navigation[0],
    {
        "role": "tool",
        "tool_name": "browser_click_semantic",
        "content": json.dumps({
            "action_class": "interact",
            "action_policy_status": "auto_allowed",
            "click_status": "executed",
            "current_url": "https://example.test/settings/general",
            "title": "General settings",
            "text_preview": "System name and access zone settings",
        }),
    },
]
assert managed_navigation_ready(wrong_location_branch) is False
assert run(wrong_location_branch)["status"] == "blocked_by_policy"

correct_location_branch = [
    {
        "role": "user",
        "content": "Create a Location",
    },
    successful_navigation[0],
    {
        "role": "tool",
        "tool_name": "browser_click_semantic",
        "content": json.dumps({
            "action_class": "interact",
            "action_policy_status": "auto_allowed",
            "click_status": "executed",
            "current_url": "https://example.test/locations",
            "title": "Locations",
            "text_preview": "Locations",
        }),
    },
]
assert managed_navigation_ready(correct_location_branch) is True
assert run(correct_location_branch) is None

menu_only = [
    successful_navigation[0],
    {
        "role": "tool",
        "tool_name": "browser_click_semantic",
        "content": json.dumps({
            "action_class": "interact",
            "click_status": "executed",
            "current_url": "https://example.test/start",
        }),
    },
]
assert run(menu_only)["status"] == "blocked_by_policy"
assert run([], semantic_name="Create access zone") is None
assert run([], job_id=None, case_id=None) is None

print("managed navigation preflight smoke: PASS")
