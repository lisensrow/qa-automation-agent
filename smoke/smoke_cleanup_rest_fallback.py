#!/opt/uqa/.venv/bin/python

import uqa
from tools import registry


resource = {
    "created_by_case": "case-1",
    "name": "uqa-exact-resource",
}
job = {
    "test_cases": [
        {
            "case_id": "case-1",
            "observations": [
                {
                    "data": {
                        "tool": "browser_click_semantic",
                        "input": {"name": "Save", "exact": True},
                        "network_requests": [
                            {
                                "method": "POST",
                                "status": 201,
                                "url": "/api/resources?view=full",
                            },
                            {
                                "method": "GET",
                                "status": 200,
                                "url": "/api/resources?limit=0",
                            },
                        ],
                    }
                }
            ],
        }
    ]
}

assert uqa._cleanup_observed_create_endpoint(job, resource) == "/api/resources"
resource_with_unsupported_delete = {
    **resource,
    "cleanup_attempts": [
        {
            "events": [
                {
                    "data": {
                        "tool": "browser_delete_json_resource",
                        "result": {"delete_status": 405},
                    }
                }
            ]
        }
    ],
}
assert uqa._cleanup_observed_create_endpoint(
    job,
    resource_with_unsupported_delete,
) == "/api/resources"
archive_resource = {
    **resource,
    "metadata": {
        "cleanup_http": {"method": "POST", "suffix": "archive"},
    },
}
assert uqa._cleanup_exact_rest_target(job, archive_resource) == {
    "tool": "browser_archive_json_resource",
    "arguments": {
        "collection_endpoint": "/api/resources",
        "exact_name": "uqa-exact-resource",
    },
}
assert uqa.classify_tool_action(
    "browser_delete_json_resource",
    {
        "collection_endpoint": "/api/resources",
        "exact_name": "uqa-exact-resource",
    },
) == "destructive"
assert uqa.classify_tool_action(
    "browser_archive_json_resource",
    {
        "collection_endpoint": "/api/resources",
        "exact_name": "uqa-exact-resource",
    },
) == "destructive"
assert uqa._cleanup_browser_verification_succeeded(
    "browser_delete_json_resource",
    {
        "status": "ok",
        "delete_status": 204,
        "post_delete_status": 200,
        "post_delete_match_count": 0,
    },
)
assert uqa._cleanup_browser_verification_succeeded(
    "browser_archive_json_resource",
    {
        "status": "ok",
        "mutation_status": 202,
        "post_delete_status": 200,
        "post_delete_match_count": 1,
        "post_delete_archived_match_count": 1,
        "post_delete_verified": True,
    },
)
assert uqa._cleanup_browser_verification_succeeded(
    "browser_inspect_table_row",
    {
        "status": "error",
        "error": "table_row_not_found",
    },
)
assert not uqa._cleanup_browser_verification_succeeded(
    "browser_inspect_table_row",
    {
        "status": "ok",
        "inspection_status": "observed",
        "visible": True,
    },
)
assert uqa._cleanup_browser_verification_succeeded(
    "browser_inspect_semantic",
    {
        "status": "error",
        "error": "semantic_element_not_found",
    },
)
confirmed_resource = {
    "cleanup_attempts": [
        {
            "events": [
                {
                    "data": {
                        "result": {
                            "action_class": "destructive",
                            "action_policy_status": "confirmed",
                            "click_status": "executed",
                            "mutation_executed": True,
                        },
                    },
                },
            ],
        },
    ],
}
assert uqa._cleanup_can_reconcile_exact_absence(
    confirmed_resource,
    "browser_inspect_semantic",
    {
        "status": "error",
        "error": "semantic_element_not_found",
    },
)
assert uqa._cleanup_can_reconcile_exact_absence(
    confirmed_resource,
    "browser_inspect_table_row",
    {
        "status": "error",
        "error": "table_row_not_found",
    },
)
assert not uqa._cleanup_can_reconcile_exact_absence(
    {"cleanup_attempts": []},
    "browser_inspect_table_row",
    {
        "status": "error",
        "error": "table_row_not_found",
    },
)
assert not uqa._cleanup_can_reconcile_exact_absence(
    confirmed_resource,
    "browser_inspect_table_row",
    {
        "status": "ok",
        "inspection_status": "observed",
        "visible": True,
    },
)
assert uqa._cleanup_history_has_confirmed_destructive(
    confirmed_resource
)
assert not uqa._cleanup_history_has_confirmed_destructive(
    {"cleanup_attempts": []}
)
first_archive_click = {
    "action_class": "destructive",
    "action_policy_status": "confirmed",
    "click_status": "executed",
    "interactive_elements": [
        {
            "role": "button",
            "text": "Archive",
        },
    ],
}
uqa._annotate_cleanup_mutation_result(
    "browser_click_semantic",
    {
        "name": "Archive",
        "role": "menuitem",
        "exact": True,
    },
    first_archive_click,
)
assert first_archive_click["confirmation_pending"] is True
assert first_archive_click["mutation_executed"] is False
counted_archive_click = {
    "action_class": "destructive",
    "action_policy_status": "confirmed",
    "click_status": "executed",
    "post_click_same_name_button_count": 1,
    "interactive_elements": [],
}
uqa._annotate_cleanup_mutation_result(
    "browser_click_semantic",
    {
        "name": "Archive",
        "role": "menuitem",
        "exact": True,
    },
    counted_archive_click,
)
assert counted_archive_click["confirmation_pending"] is True
assert counted_archive_click["mutation_executed"] is False
assert uqa._cleanup_inverse_action_visible(
    {
        "interactive_elements": [
            {
                "role": "menuitem",
                "text": "Unarchive",
            },
        ],
    },
    "Archive",
)
assert not uqa._cleanup_inverse_action_visible(
    {
        "interactive_elements": [
            {
                "role": "menuitem",
                "text": "Archive",
            },
        ],
    },
    "Archive",
)
confirmed_archive_click = {
    "action_class": "destructive",
    "action_policy_status": "confirmed",
    "click_status": "executed",
    "interactive_elements": [],
}
uqa._annotate_cleanup_mutation_result(
    "browser_click_semantic",
    {
        "name": "Archive",
        "role": "button",
        "exact": True,
    },
    confirmed_archive_click,
)
assert confirmed_archive_click["confirmation_pending"] is False
assert confirmed_archive_click["mutation_executed"] is True
history_with_action = {
    "cleanup_attempts": [
        {
            "events": [
                {
                    "data": {
                        "arguments": {
                            "name": "Archive",
                        },
                        "result": {
                            "action_class": "destructive",
                            "action_policy_status": "confirmed",
                            "mutation_executed": True,
                        },
                    },
                },
            ],
        },
    ],
}
assert (
    uqa._cleanup_last_confirmed_action_name(
        history_with_action
    )
    == "Archive"
)
table_job = {
    "test_cases": [
        {
            "case_id": "case-1",
            "observations": [
                {
                    "source": "browser_semantic",
                    "type": "ui_element",
                    "data": {
                        "strategy": "table_row_exact_cell",
                        "exact": True,
                        "subject": "uqa-exact-resource",
                        "visible": True,
                    },
                },
            ],
        },
    ],
}
table_resource = {
    "created_by_case": "case-1",
    "name": "uqa-exact-resource",
}
assert uqa._cleanup_resource_was_exact_table_row(
    table_job,
    table_resource,
)
assert not uqa._cleanup_resource_was_exact_table_row(
    table_job,
    {
        **table_resource,
        "name": "another-resource",
    },
)
assert uqa._cleanup_browser_verification_succeeded(
    "browser_archive_json_resource",
    {
        "status": "ok",
        "mutation_status": None,
        "mutation_executed": False,
        "already_satisfied": True,
        "post_delete_status": 200,
        "post_delete_match_count": 1,
        "post_delete_archived_match_count": 1,
        "post_delete_verified": True,
    },
)
assert not uqa._cleanup_browser_verification_succeeded(
    "browser_delete_json_resource",
    {
        "status": "ok",
        "mutation_status": 204,
        "post_delete_status": 200,
        "post_delete_match_count": 1,
        "post_delete_verified": False,
    },
)
assert uqa._cleanup_browser_verification_succeeded(
    "browser_archive_json_resource",
    {
        "status": "ok",
        "mutation_status": 200,
        "post_delete_status": 200,
        "post_delete_match_count": 0,
    },
)

captured = {}


def fake_click(name, exact, role, container):
    captured["click"] = (name, exact, role, container)
    return {"status": "ok"}


def fake_delete(collection_endpoint, exact_name):
    captured["delete"] = (collection_endpoint, exact_name)
    return {"status": "ok"}


def fake_context_menu(name, exact):
    captured["context"] = (name, exact)
    return {"status": "ok"}


def fake_archive(collection_endpoint, exact_name):
    captured["archive"] = (collection_endpoint, exact_name)
    return {"status": "ok"}


registry.click_semantic = fake_click
registry.delete_json_resource = fake_delete
registry.context_menu_semantic = fake_context_menu
registry.archive_json_resource = fake_archive

registry.execute_tool(
    "browser_click_semantic",
    {
        "name": "Expand",
        "exact": True,
        "role": "button",
        "container": "Parent",
    },
)
registry.execute_tool(
    "browser_archive_json_resource",
    {
        "collection_endpoint": "/api/resources",
        "exact_name": "uqa-exact-resource",
    },
)
registry.execute_tool(
    "browser_context_menu_semantic",
    {"name": "uqa-exact-resource", "exact": True},
)
registry.execute_tool(
    "browser_delete_json_resource",
    {
        "collection_endpoint": "/api/resources",
        "exact_name": "uqa-exact-resource",
    },
)

assert captured["click"] == ("Expand", True, "button", "Parent")
assert captured["delete"] == ("/api/resources", "uqa-exact-resource")
assert captured["context"] == ("uqa-exact-resource", True)
assert captured["archive"] == ("/api/resources", "uqa-exact-resource")

tool_names = {
    item.get("function", {}).get("name")
    for item in registry.TOOLS
}
assert "browser_delete_json_resource" not in tool_names
assert "browser_context_menu_semantic" in tool_names
assert "browser_archive_json_resource" not in tool_names
cleanup_only_tool_names = {
    item.get("function", {}).get("name")
    for item in registry.CLEANUP_ONLY_TOOLS
}
assert cleanup_only_tool_names == {
    "browser_delete_json_resource",
    "browser_archive_json_resource",
}
cleanup_tool_names = {
    item.get("function", {}).get("name")
    for item in uqa._cleanup_tools()
}
assert "browser_context_menu_semantic" not in cleanup_tool_names
assert "browser_delete_json_resource" in cleanup_tool_names
assert "browser_archive_json_resource" in cleanup_tool_names

print("smoke_cleanup_rest_fallback: PASS")
