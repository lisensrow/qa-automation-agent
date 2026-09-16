"""Normalize one CI/agent/monitoring observation without product-side effects."""

from datetime import datetime, timezone
import math


def _timestamp(value):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else None


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if math.isfinite(value) else None


def summarize_agent_observation(
    ci_name, ci, agent, monitoring, ui_status,
    observed_at=None, max_age_seconds=300,
):
    """Return bounded, evidence-oriented facts; never expose full API objects."""
    now = observed_at or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("observed_at must be timezone-aware")
    if type(max_age_seconds) is not int or not 1 <= max_age_seconds <= 3600:
        raise ValueError("max_age_seconds must be 1..3600")
    ci = ci if isinstance(ci, dict) else {}
    agent = agent if isinstance(agent, dict) else {}
    monitoring = monitoring if isinstance(monitoring, dict) else {}
    detail = ci.get("detail")
    detail = detail if isinstance(detail, dict) else {}
    os_info = detail.get("os") or {}
    if not isinstance(os_info, dict):
        os_info = {}
    ci_id = ci.get("id")
    agent_id = ci.get("agent_id")
    statuses = {
        "ui": str(ui_status or "").strip().casefold() or None,
        "ci": str(ci.get("endpoint_status") or "").strip().casefold() or None,
        "agent": str(agent.get("status") or "").strip().casefold() or None,
    }
    sample_time = _timestamp(monitoring.get("created_at"))
    age = (now - sample_time).total_seconds() if sample_time else None
    fresh = age is not None and -120 <= age <= max_age_seconds
    cpu_values = monitoring.get("cpu_usage")
    if not isinstance(cpu_values, list):
        cpu_values = []
    cpu_values = [_number(value) for value in cpu_values[:128]]
    result = {
        "ci_name": ci_name,
        "ci_id": ci_id,
        "agent_id": agent_id,
        "agent_version": agent.get("version"),
        "os_name": os_info.get("name"),
        "os_version": os_info.get("version"),
        "architecture": os_info.get("architecture"),
        "statuses": statuses,
        "agent_last_online_at": agent.get("last_online_at"),
        "monitoring_at": monitoring.get("created_at"),
        "monitoring_age_seconds": round(age, 1) if age is not None else None,
        "monitoring_fresh": fresh,
        "cpu_usage_raw": cpu_values,
        "ram_usage_raw": _number(monitoring.get("ram_usage")),
        "ram_usage_percent": _number(monitoring.get("ram_usage_percent")),
        "uptime_seconds": _number(monitoring.get("uptime")),
    }
    if ci.get("name") != ci_name or not ci_id or not agent_id:
        reason = "ci_observation_missing_or_mismatched"
    elif agent.get("id") != agent_id:
        reason = "agent_observation_missing_or_mismatched"
    elif monitoring and monitoring.get("uid") != ci_id:
        reason = "monitoring_ci_mismatch"
    elif any(status not in {"online", "offline"} for status in statuses.values()):
        reason = "status_observation_incomplete"
    elif len(set(statuses.values())) != 1:
        reason = "status_sources_disagree"
    elif statuses["agent"] == "offline":
        reason = "agent_offline"
    elif not fresh:
        reason = "monitoring_missing_or_stale"
    else:
        reason = None
    result["observation_result"] = "PASS" if reason is None else "BLOCKED"
    result["reason"] = reason
    return result
