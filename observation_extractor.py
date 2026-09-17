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
            ("ci_name", "agent_version", "os_name", "os_version",
             "architecture", "statuses", "monitoring_at",
             "monitoring_age_seconds", "monitoring_fresh",
             "observation_result", "reason", "source_request_ids"),
        ),
        "browser_inspect_agent_plugins_semantic": (
            "agent_plugin_audit",
            ("ci_name", "last_audit_at", "audit_age_seconds",
             "audit_fresh", "plugin_count", "matched_plugins",
             "observation_result", "reason", "source_request_ids"),
        ),
    }
    if tool_name in agent_observation_fields and not result.get("error"):
        observation_type, fields = agent_observation_fields[tool_name]
        return [{
            "type": observation_type,
            "source": "browser",
            "data": {
                **{key: result.get(key) for key in fields},
                "plugin_name": arguments.get("plugin_name"),
                "expected_version": arguments.get("expected_version"),
            },
        }]

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
