"""Bounded, read-only summary of one agent's observed task-list response."""

from datetime import datetime


def summarize_agent_tasks(ci, task_page, task_name=None, task_id=None):
    ci = ci if isinstance(ci, dict) else {}
    task_page = task_page if isinstance(task_page, dict) else {}
    agent_id = ci.get("agent_id")
    items = task_page.get("items")
    total = task_page.get("total")
    if not isinstance(total, int) or isinstance(total, bool) or total < 0:
        total = task_page.get("count")
    if not isinstance(total, int) or isinstance(total, bool) or total < 0:
        total = None

    if not ci.get("id") or not agent_id:
        reason = "ci_observation_missing_or_mismatched"
    elif not isinstance(items, list):
        reason = "task_list_get_not_observed"
    elif any(
        not isinstance(item, dict) or item.get("agent_id") != agent_id
        for item in items
    ):
        reason = "task_agent_mismatch"
    else:
        reason = None

    name_counts = {}
    if reason is None:
        for item in items:
            name = item.get("name")
            if isinstance(name, str) and name:
                name_counts[name[:120]] = name_counts.get(name[:120], 0) + 1

    summaries = []
    if reason is None:
        selected = [
            item for item in items
            if (task_name is None or item.get("name") == task_name)
            and (task_id is None or item.get("id") == task_id)
        ] if task_name or task_id else []
        for item in selected[:20]:
            summaries.append({
                "task_id": item.get("id"),
                "name": item.get("name"),
                "enabled": item.get("enabled"),
                "period_seconds": item.get("period"),
                "status": item.get("status"),
                "last_processed_at": item.get("last_processed_at"),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
            })
    exact = summaries
    if reason is None and (task_name or task_id):
        if total is not None and total > len(items):
            reason = "task_list_incomplete"
        elif len(selected) != 1:
            reason = (
                "task_id_absent_or_ambiguous" if task_id
                else "task_absent_or_ambiguous"
            )

    available_names = []
    if reason == "task_absent_or_ambiguous":
        for item in items:
            name = item.get("name")
            if isinstance(name, str) and name and name not in available_names:
                available_names.append(name[:120])
            if len(available_names) >= 20:
                break

    return {
        "ci_name": ci.get("name"),
        "agent_id": agent_id,
        "task_name": task_name,
        "task_id": task_id,
        "task_count": total,
        "page_count": len(items) if isinstance(items, list) else None,
        "matched_tasks": exact[:20],
        "task_names": [
            {"name": name, "count": count}
            for name, count in list(name_counts.items())[:30]
        ] if not (task_name or task_id) else [],
        "available_task_names": available_names,
        "inspection_status": "observed" if reason is None else "blocked",
        "reason": reason,
        "task_list_observed": isinstance(items, list),
        "execution_result_verified": False,
        "mutation_executed": False,
    }


def summarize_agent_task_full(ci, task_page, task_id, full):
    """Describe a full task response without exposing its payload or parameters."""
    listed = summarize_agent_tasks(ci, task_page, task_id=task_id)
    base = {
        "ci_name": listed["ci_name"],
        "agent_id": listed["agent_id"],
        "task_id": task_id,
        "inspection_status": "blocked",
        "reason": listed["reason"],
        "full_result_observed": False,
        "execution_result_verified": False,
        "mutation_executed": False,
    }
    if listed["reason"]:
        return base
    total = task_page.get("total") if isinstance(task_page, dict) else None
    items = task_page.get("items") if isinstance(task_page, dict) else None
    if (
        not isinstance(total, int) or isinstance(total, bool)
        or not isinstance(items, list) or total != len(items)
    ):
        return {**base, "reason": "task_list_completeness_unconfirmed"}
    item = listed["matched_tasks"][0]
    if not isinstance(full, dict) or (
        full.get("id") != task_id
        or full.get("agent_id") != listed["agent_id"]
        or full.get("name") != item["name"]
    ):
        return {**base, "reason": "task_full_identity_mismatch"}

    envelope = full.get("result")
    if envelope is None:
        return {
            **base, "reason": "task_result_not_available",
            "task_name": item["name"], "task_status": full.get("status"),
        }
    if not isinstance(envelope, dict):
        return {**base, "reason": "task_result_envelope_invalid"}

    processed_at = envelope.get("processed_at")
    if not isinstance(processed_at, str) or len(processed_at) > 80:
        return {**base, "reason": "task_result_processed_at_invalid"}
    try:
        datetime.fromisoformat(processed_at.replace("Z", "+00:00"))
    except ValueError:
        return {**base, "reason": "task_result_processed_at_invalid"}

    payload = envelope.get("result")
    error_code = envelope.get("error_code")
    if not isinstance(error_code, int) or isinstance(error_code, bool):
        error_code = None
    return {
        **base,
        "task_name": item["name"],
        "task_status": full.get("status"),
        "listed_status": item["status"],
        "listed_last_processed_at": item["last_processed_at"],
        "processed_at": processed_at,
        "error_code": error_code,
        "has_error_message": bool(envelope.get("error_msg")),
        "result_present": payload not in (None, "", [], {}),
        "result_type": (
            "text" if isinstance(payload, str)
            else "object" if isinstance(payload, dict)
            else "list" if isinstance(payload, list)
            else "other" if payload is not None else "none"
        ),
        "inspection_status": "observed",
        "reason": None,
        "full_result_observed": True,
    }
