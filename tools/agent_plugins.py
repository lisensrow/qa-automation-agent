"""Evidence-oriented summary of an observed agent plugin audit response."""

from datetime import datetime, timezone


def _age_seconds(value, now):
    if not isinstance(value, str):
        return None
    try:
        at = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if at.tzinfo is None:
        return None
    return round((now - at.astimezone(timezone.utc)).total_seconds(), 1)


def summarize_plugin_audit(ci, audit, plugin_name=None, expected_version=None,
                           observed_at=None, max_age_seconds=3600):
    """Never promote an old audit, missing plugin, or uncertain load to PASS."""
    now = observed_at or datetime.now(timezone.utc)
    if now.tzinfo is None or type(max_age_seconds) is not int or not 1 <= max_age_seconds <= 86400:
        raise ValueError("invalid_plugin_audit_age_limit")
    ci = ci if isinstance(ci, dict) else {}
    audit = audit if isinstance(audit, dict) else {}
    agent_id = ci.get("agent_id")
    details = audit.get("detail")
    age = _age_seconds(audit.get("last_audit_at"), now)
    fresh = age is not None and -120 <= age <= max_age_seconds
    valid = isinstance(details, list) and audit.get("agent_id") == agent_id and bool(agent_id)
    items = []
    if valid:
        for raw in details[:200]:
            if not isinstance(raw, dict):
                continue
            name = raw.get("plugin_name")
            if not isinstance(name, str) or not name.strip():
                continue
            items.append({
                "name": name,
                "version": raw.get("plugin_version"),
                "load_status": raw.get("load_status"),
                "file_name": raw.get("file_name"),
                "load_error_present": bool(raw.get("load_error")),
            })
    exact = [item for item in items if item["name"] == plugin_name] if plugin_name else []
    if not valid:
        reason = "plugin_audit_missing_or_agent_mismatch"
    elif not fresh:
        reason = "plugin_audit_stale"
    elif plugin_name and len(exact) != 1:
        reason = "plugin_absent_or_ambiguous"
    elif plugin_name and expected_version and exact[0]["version"] != expected_version:
        reason = "plugin_version_mismatch"
    elif plugin_name and exact[0]["load_status"] is not True:
        reason = "plugin_not_confirmed_loaded"
    else:
        reason = None
    return {
        "ci_name": ci.get("name"),
        "agent_id": agent_id,
        "last_audit_at": audit.get("last_audit_at"),
        "audit_age_seconds": age,
        "audit_fresh": fresh,
        "plugin_count": len(items),
        "plugin_names": [item["name"] for item in items] if not plugin_name else None,
        "matched_plugins": exact if plugin_name else None,
        "observation_result": "PASS" if reason is None and plugin_name else "BLOCKED",
        "reason": reason or ("specific_plugin_not_requested" if not plugin_name else None),
    }
