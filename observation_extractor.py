import json
from urllib.parse import (
    urlparse,
    parse_qs,
)


MAX_UI_TEXT = 1500
MAX_DOC_EXCERPT = 800
MAX_BACKEND_MATCHES = 5
MAX_SCALARS = 80


def _parse_json(value):
    if isinstance(
        value,
        (dict, list),
    ):
        return value

    if not isinstance(value, str):
        return None

    stripped = value.strip()

    if not stripped:
        return None

    if stripped[0] not in "[{":
        return None

    try:
        return json.loads(stripped)
    except Exception:
        return None


def _flatten_scalars(
    value,
    prefix="",
    output=None,
    depth=0,
):
    if output is None:
        output = []

    if len(output) >= MAX_SCALARS:
        return output

    if depth > 5:
        return output

    if isinstance(value, dict):
        for key, child in value.items():
            path = (
                f"{prefix}.{key}"
                if prefix
                else str(key)
            )

            _flatten_scalars(
                child,
                path,
                output,
                depth + 1,
            )

            if len(output) >= MAX_SCALARS:
                break

    elif isinstance(value, list):
        for index, child in enumerate(
            value[:3]
        ):
            path = (
                f"{prefix}[{index}]"
                if prefix
                else f"[{index}]"
            )

            _flatten_scalars(
                child,
                path,
                output,
                depth + 1,
            )

            if len(output) >= MAX_SCALARS:
                break

    elif value is None or isinstance(
        value,
        (str, int, float, bool),
    ):
        if isinstance(value, str):
            value = value[:500]

        output.append(
            {
                "path": prefix,
                "value": value,
            }
        )

    return output


def _url_data(url):
    if not url:
        return {}

    parsed = urlparse(
        str(url)
    )

    return {
        "url": str(url),
        "path": parsed.path,
        "query": {
            key: (
                values[0]
                if len(values) == 1
                else values
            )
            for key, values
            in parse_qs(
                parsed.query,
                keep_blank_values=True,
            ).items()
        },
    }


def _documentation_observation(
    arguments,
    result,
):
    refs = []

    for item in result.get(
        "results",
        []
    )[:5]:
        refs.append(
            {
                "source": item.get("source"),
                "chunk_no": item.get(
                    "chunk_no"
                ),
                "heading": item.get(
                    "heading"
                ),
                "content_excerpt": (
                    item.get("content")
                    or ""
                )[:MAX_DOC_EXCERPT],
            }
        )

    return {
        "type": "documentation_search",
        "source": "knowledge",
        "data": {
            "query": arguments.get(
                "query"
            ),
            "result_count": result.get(
                "result_count"
            ),
            "references": refs,
            "product_memory_summary": {
                "status": (result.get("product_memory") or {}).get("status"),
                "loaded_fact_count": len((result.get("product_memory") or {}).get("results") or []),
                "fact_keys": [item.get("fact_key") for item in
                              (result.get("product_memory") or {}).get("results") or []
                              if isinstance(item, dict)],
                "evidence_for_pass": False,
            },
        },
    }


def _browser_state_observation(
    tool_name,
    arguments,
    result,
):
    return {
        "type": "ui_state",
        "source": "browser",
        "data": {
            "tool": tool_name,
            "action": result.get(
                "action"
            ),
            "input": arguments,
            "session_id": result.get(
                "session_id"
            ),
            "action_execution_id": result.get(
                "action_execution_id"
            ),
            "network_window_closed": result.get(
                "network_window_closed"
            ),
            "network_capture_scope": result.get(
                "network_capture_scope"
            ),
            "post_action_wait_ms": result.get(
                "post_action_wait_ms"
            ),
            "network_request_count": result.get(
                "network_request_count"
            ),
            "network_requests": (
                result.get(
                    "network_requests"
                )
                or []
            )[-30:],
            "title": result.get(
                "title"
            ),
            "http_status": result.get(
                "http_status"
            ),
            **_url_data(
                result.get(
                    "current_url"
                )
                or result.get(
                    "final_url"
                )
            ),
            "screenshot": result.get(
                "screenshot"
            ),
            "text_excerpt": (
                result.get(
                    "text_preview"
                )
                or ""
            )[:MAX_UI_TEXT],
        },
    }


def _browser_semantic_observation(
    arguments,
    result,
    tool_name=None,
):
    element = (
        result.get("element")
        if isinstance(
            result.get("element"),
            dict,
        )
        else {}
    )

    return {
        "type": "ui_element",
        "source": "browser_semantic",
        "data": {
            "tool": tool_name,
            "row_match_count": result.get("row_match_count"),
            "table_summary": result.get("table_summary"),
            "table_resolution": result.get("table_resolution"),
            "subject": (
                result.get(
                    "semantic_name"
                )
                or arguments.get("name")
            ),
            "exact": arguments.get(
                "exact",
                True,
            ),
            "strategy": result.get(
                "semantic_strategy"
            ),
            "inspection_status": (
                result.get(
                    "inspection_status"
                )
            ),
            "visible": result.get(
                "visible"
            ),
            "enabled": result.get(
                "enabled"
            ),
            "disabled": result.get(
                "disabled"
            ),
            "editable": result.get(
                "editable"
            ),
            "tag": element.get("tag"),
            "role": element.get("role"),
            "type": element.get("type"),
            "id": element.get("id"),
            "name": element.get("name"),
            "placeholder": element.get(
                "placeholder"
            ),
            "value": element.get("value"),
            "disabled_attribute": (
                element.get(
                    "disabled_attribute"
                )
            ),
            "readonly_attribute": (
                element.get(
                    "readonly_attribute"
                )
            ),
            "aria_disabled": element.get(
                "aria_disabled"
            ),
            "aria_label": element.get(
                "aria_label"
            ),
            "aria_expanded": element.get(
                "aria_expanded"
            ),
            "aria_controls": element.get(
                "aria_controls"
            ),
            "aria_activedescendant": (
                element.get(
                    "aria_activedescendant"
                )
            ),
            "aria_valuetext": element.get(
                "aria_valuetext"
            ),
            "selected_value": element.get(
                "selected_value"
            ),
            "selected_text": element.get(
                "selected_text"
            ),
            "selection_state": element.get(
                "selection_state"
            ),
            "selection_reason": element.get(
                "selection_reason"
            ),
            "text": element.get("text"),
            "cells": element.get("cells"),
            "headers": element.get("headers"),
            "values_by_header": element.get(
                "values_by_header"
            ),
            "session_id": result.get(
                "session_id"
            ),
            "action_execution_id": (
                result.get(
                    "action_execution_id"
                )
            ),
            "screenshot": result.get(
                "screenshot"
            ),
            **_url_data(
                result.get("current_url")
                or result.get("final_url")
            ),
        },
    }


def _api_observation(
    arguments,
    result,
):
    body = _parse_json(
        result.get(
            "response_body"
        )
    )

    data = {
        "request_id": result.get(
            "request_id"
        ),
        "session_id": result.get(
            "session_id"
        ),
        "action_execution_id": result.get(
            "action_execution_id"
        ),
        "method": result.get(
            "method"
        ),
        "resource_type": result.get(
            "resource_type"
        ),
        "http_status": result.get(
            "status"
        ),
        **_url_data(
            result.get("url")
        ),
    }

    if body is not None:
        data["response_type"] = (
            "object"
            if isinstance(body, dict)
            else "array"
        )

        if isinstance(body, dict):
            for key in (
                "count",
                "total",
                "limit",
                "offset",
            ):
                if key in body:
                    data[key] = body[key]

            if isinstance(
                body.get("items"),
                list,
            ):
                data["items_count"] = len(
                    body["items"]
                )

        data["response_scalars"] = (
            _flatten_scalars(body)
        )

    return {
        "type": "api_exchange",
        "source": "browser_xhr",
        "data": data,
    }


def _backend_observation(
    arguments,
    result,
):
    return {
        "type": "backend_request",
        "source": "ssh_backend_logs",
        "data": {
            "stand": result.get(
                "stand"
            )
            or arguments.get(
                "stand"
            ),
            "container": result.get(
                "container"
            ),
            "container_autodetected": (
                result.get(
                    "container_autodetected"
                )
            ),
            "method": result.get(
                "method"
            )
            or arguments.get(
                "method"
            ),
            "endpoint": result.get(
                "endpoint_contains"
            )
            or arguments.get(
                "endpoint_contains"
            ),
            "query_contains": (
                result.get(
                    "query_contains"
                )
                or arguments.get(
                    "query_contains",
                    [],
                )
            ),
            "since": result.get(
                "since"
            )
            or arguments.get(
                "since"
            ),
            "match_count": result.get(
                "match_count"
            ),
            "matches": (
                result.get(
                    "matches",
                    []
                )[
                    -MAX_BACKEND_MATCHES:
                ]
            ),
            "correlation_note": (
                result.get(
                    "correlation_note"
                )
            ),
        },
    }


def extract_observations(
    tool_name,
    arguments,
    result,
):
    if not isinstance(result, dict):
        return []

    form_audits = {
        "browser_inspect_form_validation_semantic": ("validation_audit", {
            "visible_control_count": int, "invalid_control_count": int,
            "validation_passed": bool, "truncated": bool,
        }),
        "browser_inspect_field_label_contract_semantic": ("field_label_audit", {
            "field_count": int, "unlabeled_count": int, "broken_description_count": int,
            "field_label_contract_passed": bool, "truncated": bool,
        }),
        "browser_inspect_dialog_contract_semantic": ("dialog_contract_audit", {
            "dialog_count": int, "failure_count": int,
            "dialog_contract_passed": bool, "truncated": bool,
        }),
    }
    if tool_name in form_audits:
        audit_key, fields = form_audits[tool_name]
        raw = result.get(audit_key)
        audit = raw if isinstance(raw, dict) else {}
        safe = {key: value if type(value) is expected and
                (expected is not int or value >= 0) else None
                for key, expected in fields.items() for value in [audit.get(key)]}
        usable = (not result.get("error") and result.get("executed") is not False
                  and result.get("mutation_executed") is False
                  and all(value is not None for value in safe.values())
                  and safe.get("truncated") is False)
        if usable and audit_key == "validation_audit":
            usable = (safe["invalid_control_count"] <= safe["visible_control_count"]
                      and safe["validation_passed"] == (safe["invalid_control_count"] == 0))
        elif usable and audit_key == "field_label_audit":
            usable = (safe["unlabeled_count"] <= safe["field_count"]
                      and safe["field_label_contract_passed"] ==
                      (safe["unlabeled_count"] == 0 and safe["broken_description_count"] == 0))
        elif usable and audit_key == "dialog_contract_audit":
            usable = (safe["failure_count"] <= safe["dialog_count"]
                      and safe["dialog_contract_passed"] == (safe["failure_count"] == 0))
        states = []
        states_reported = False
        if audit_key == "validation_audit" and usable and audit.get("control_states_reported") is True:
            raw_states = audit.get("control_states")
            if isinstance(raw_states, list) and len(raw_states) == safe["visible_control_count"] and len(raw_states) <= 200:
                valid = all(isinstance(row, dict) and type(row.get("index")) is int and row["index"] == i
                    and isinstance(row.get("tag"), str) and row["tag"] in {"input", "select", "textarea"}
                    and isinstance(row.get("type"), str) and len(row["type"]) <= 40
                    and isinstance(row.get("label_hint"), str) and len(row["label_hint"]) <= 200
                    and all(type(row.get(k)) is bool for k in ("native_required", "native_disabled", "native_will_validate"))
                    and (row.get("native_read_only") is None or type(row.get("native_read_only")) is bool)
                    and "native_read_only" in row for i, row in enumerate(raw_states))
                if valid:
                    states_reported = True
                    states = [{k: row[k] for k in ("index", "tag", "type", "label_hint", "native_required",
                              "native_disabled", "native_read_only", "native_will_validate")} for row in raw_states]
        extra = {"control_states_reported": states_reported, "control_states": states} if audit_key == "validation_audit" else {}
        if states_reported:
            extra["control_state_summary"] = {
                "native_required_count": sum(row["native_required"] for row in states),
                "native_disabled_count": sum(row["native_disabled"] for row in states),
                "native_read_only_count": sum(row["native_read_only"] is True for row in states),
                "native_read_only_unknown_count": sum(row["native_read_only"] is None for row in states)}
        return [{"type": "ui_contract_audit", "source": "browser", "data": {
            "tool": tool_name, "audit_kind": audit_key, "audit": safe,
            **extra,
            "scope_kind": "requested_named_form" if arguments.get("form") else "page",
            "observation_result": "observed" if usable else "blocked",
            "mutation_executed": result.get("mutation_executed") if
                type(result.get("mutation_executed")) is bool else None,
            "session_id": result.get("session_id"),
            "action_execution_id": result.get("action_execution_id"),
            **_url_data(result.get("current_url")),
        }}]

    if tool_name == "knowledge_search":
        return [
            _documentation_observation(
                arguments,
                result,
            )
        ]

    agent_observation_fields = {
        "browser_inspect_agent_telemetry_semantic": (
            "agent_telemetry",
            ("ci_name", "ci_id", "agent_id", "observed_agent_id", "monitoring_ci_id", "agent_version", "os_name", "os_version",
             "architecture", "statuses", "monitoring_at",
             "monitoring_age_seconds", "monitoring_fresh",
             "cpu_usage_raw", "ram_usage_raw", "ram_usage_percent",
             "uptime_seconds",
             "observation_result", "reason", "source_request_ids"),
        ),
        "browser_inspect_agent_plugins_semantic": (
            "agent_plugin_audit",
            ("ci_name", "ci_id", "agent_id", "audit_agent_id", "last_audit_at", "audit_age_seconds",
             "audit_fresh", "plugin_count", "matched_plugins",
             "observation_result", "reason", "source_request_ids"),
        ),
        "browser_inspect_agent_tasks_semantic": (
            "agent_task_list",
            ("ci_name", "agent_id", "task_name", "task_id", "task_count",
             "page_count", "matched_tasks", "task_names",
             "available_task_names",
             "inspection_status", "task_list_observed", "next_step_hint",
             "reason", "execution_result_verified", "source_request_ids"),
        ),
        "browser_inspect_agent_task_result_semantic": (
            "agent_task_result",
            ("ci_name", "agent_id", "task_id", "task_name", "task_status",
             "listed_status", "listed_last_processed_at", "processed_at",
             "error_code", "has_error_message", "result_present",
             "result_type", "inspection_status", "reason",
             "expected_text_sha256", "expected_text_length",
             "text_assertion_checked", "text_assertion_matched",
             "expected_error_code", "error_code_matched",
             "assertion_passed",
             "periodic_verification_requested", "period_seconds",
             "periodic_verification_status",
             "periodic_execution_verified", "previous_processed_at",
             "current_processed_at", "observed_interval_seconds",
             "full_result_observed", "execution_result_verified",
             "full_http_status", "source_request_ids"),
        ),
        "browser_inspect_managed_agent_task_result_semantic": (
            "agent_task_result",
            ("ci_name", "agent_id", "task_id", "task_name", "task_status",
             "listed_status", "listed_last_processed_at", "processed_at",
             "error_code", "has_error_message", "result_present",
             "result_type", "inspection_status", "reason",
             "expected_text_sha256", "expected_text_length",
             "text_assertion_checked", "text_assertion_matched",
             "expected_error_code", "error_code_matched",
             "assertion_passed", "managed_fixture_id",
             "managed_fixture_verified", "full_result_observed",
             "execution_result_verified", "full_http_status",
             "source_request_ids"),
        ),
    }
    if tool_name in agent_observation_fields and not result.get("error"):
        observation_type, fields = agent_observation_fields[tool_name]
        return [{
            "type": observation_type,
            "source": "browser",
            "data": {
                "tool": tool_name,
                **{key: result.get(key) for key in fields},
                **_url_data(result.get("current_url") or result.get("url")),
                "plugin_name": arguments.get("plugin_name"),
                "expected_version": arguments.get("expected_version"),
            },
        }]

    if tool_name == "browser_verify_exact_table_row_tabs_semantic":
        return [{"type": "ui_tab_navigation", "source": "browser", "data": {
            "tool": tool_name, "subject": result.get("name") or arguments.get("name"),
            "requested_tabs": result.get("requested_tabs"), "tabs_verified": result.get("tabs_verified"),
            "details_identity_passed": result.get("details_identity_passed"),
            "details_identity_preserved": result.get("details_identity_preserved"),
            "failed_stage": result.get("failed_stage"), "failed_tab": result.get("failed_tab"),
            "observation_result": result.get("observation_result"),
            **_url_data(result.get("current_url")),
        }}]

    if tool_name == "browser_open_exact_table_row_details_semantic":
        return [{"type": "ui_details_identity", "source": "browser", "data": {
            "tool": tool_name,
            "subject": result.get("name") or arguments.get("name"),
            "row_match_count": result.get("row_match_count"),
            "row_opened": result.get("row_opened"),
            "details_identity_passed": result.get("details_identity_passed"),
            "details_identity_status": result.get("details_identity_status"),
            "session_id": result.get("session_id"),
            **_url_data(result.get("current_url")),
        }}]

    if tool_name in {
        "browser_inspect_semantic",
        "browser_inspect_table_row",
        "browser_inspect_table_semantic",
        "browser_inspect_bulk_action_semantic",
    }:
        return [
            _browser_semantic_observation(
                arguments,
                result,
                tool_name=tool_name,
            )
        ]

    if tool_name in {
        "browser_open_page",
        "browser_get_state",
        "browser_probe_capabilities",
        "browser_click_semantic",
        "browser_fill_semantic",
        "browser_select_semantic",
        "browser_set_checked_semantic",
        "browser_choose_radio_semantic",
        "browser_select_many_semantic",
        "browser_press_key_semantic",
        "browser_check_focus_order_semantic",
        "browser_drag_semantic",
        "browser_inspect_order_semantic",
        "browser_resize_semantic",
        "browser_sort_table_semantic",
        "browser_set_table_row_selected",
        "browser_table_page_semantic",
        "browser_fill_table_filter_semantic",
        "browser_apply_table_filter_popover_semantic",
        "browser_inspect_table_pagination_semantic",
        "browser_set_table_all_selected",
    }:
        return [
            _browser_state_observation(
                tool_name,
                arguments,
                result,
            )
        ]

    if tool_name == (
        "browser_get_network_detail"
    ):
        return [
            _api_observation(
                arguments,
                result,
            )
        ]

    if tool_name == (
        "ssh_find_backend_request"
    ):
        return [
            _backend_observation(
                arguments,
                result,
            )
        ]

    return []
