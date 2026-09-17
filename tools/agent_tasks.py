"""Bounded, read-only summary of one agent's observed task-list response."""


def summarize_agent_tasks(ci, task_page, task_name=None):
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
        selected = (
            [item for item in items if item.get("name") == task_name]
            if task_name else []
        )
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
    if reason is None and task_name:
        if total is not None and total > len(items):
            reason = "task_list_incomplete"
        elif sum(item.get("name") == task_name for item in items) != 1:
            reason = "task_absent_or_ambiguous"

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
        "task_count": total,
        "page_count": len(items) if isinstance(items, list) else None,
        "matched_tasks": exact[:20],
        "task_names": [
            {"name": name, "count": count}
            for name, count in list(name_counts.items())[:30]
        ] if not task_name else [],
        "available_task_names": available_names,
        "inspection_status": "observed" if reason is None else "blocked",
        "reason": reason,
        "task_list_observed": isinstance(items, list),
        "execution_result_verified": False,
        "mutation_executed": False,
    }
