"""Deterministic contracts over trusted browser observations; no product routing."""
from copy import deepcopy
from datetime import datetime
import math
import json
from urllib.parse import urlsplit

TOOL_FIELDS = {
    "browser_inspect_table_row": ("ui_element", {"row_match_count"}),
    "browser_open_exact_table_row_details_semantic": (
        "ui_details_identity", {"details_identity_passed", "row_opened", "url"}),
    "browser_inspect_agent_telemetry_semantic": (
        "agent_telemetry", {"ci_id", "statuses", "monitoring_ci_id", "monitoring_at",
                            "monitoring_age_seconds", "monitoring_fresh"}),
    "browser_inspect_agent_plugins_semantic": (
        "agent_plugin_audit", {"ci_id", "plugin_present", "plugin_version", "last_audit_at",
                               "audit_age_seconds", "audit_fresh"}),
}

REPORT_OPERATORS = {"ci_id": "nonempty", "monitoring_ci_id": "nonempty", "plugin_version": "nonempty",
                    "statuses": "statuses_reported", "monitoring_at": "timestamp_reported",
                    "last_audit_at": "timestamp_reported",
                    "monitoring_age_seconds": "age_reported", "audit_age_seconds": "age_reported"}


def render_contract_check_summary(checks):
    """Publish computed facts, not the model's unverified prose or health verdict."""
    facts = [{key: check.get(key) for key in
              ("check_id", "status", "actual", "freshness", "reason")} for check in checks]
    return ("[UQA CORE: VERIFIED CHECK CONTRACTS]\n"
            "PASS applies only to the declared checks; reporting old data does not prove freshness or agent health.\n"
            + json.dumps(facts, ensure_ascii=False, allow_nan=False))


def validate_contracts(contracts):
    if not isinstance(contracts, dict) or not contracts:
        raise ValueError("frontend_contracts_invalid")
    for check_id, contract in contracts.items():
        if not isinstance(check_id, str) or not isinstance(contract, dict):
            raise ValueError("frontend_contract_invalid")
        tool = contract.get("tool")
        if tool not in TOOL_FIELDS or not isinstance(contract.get("subject_binding"), str):
            raise ValueError("frontend_contract_tool_or_subject_invalid")
        assertions = contract.get("assertions")
        if not isinstance(assertions, list) or not assertions:
            raise ValueError("frontend_contract_assertions_required")
        for assertion in assertions:
            if not isinstance(assertion, dict) or assertion.get("field") not in TOOL_FIELDS[tool][1]:
                raise ValueError("frontend_contract_field_invalid")
            operator = assertion.get("operator")
            if operator not in {"eq", "same_origin"} and REPORT_OPERATORS.get(assertion["field"]) != operator:
                raise ValueError("frontend_contract_operator_invalid")
            if operator == "same_origin" and assertion["field"] != "url":
                raise ValueError("frontend_contract_origin_field_invalid")
            if operator == "eq" and type(assertion.get("expected")) not in (bool, int):
                raise ValueError("frontend_contract_expected_invalid")
            if operator in REPORT_OPERATORS.values() and "expected" in assertion:
                raise ValueError("frontend_contract_report_expected_forbidden")


def agent_fact(data, field, bindings):
    """Validate observed identity before independently judging a reported fact."""
    sources = data.get("source_request_ids")
    if not isinstance(sources, dict) or not all(
            isinstance(sources.get(key), str) and sources[key].strip()
            for key in ("ci", "agent" if data["tool"] == "browser_inspect_agent_telemetry_semantic"
                        else "plugin_audit")):
        raise ValueError("agent_contract_sources_missing")
    if not all(isinstance(data.get(key), str) and data[key].strip() for key in ("ci_id", "agent_id")):
        raise ValueError("agent_contract_identity_missing")
    if data["tool"] == "browser_inspect_agent_telemetry_semantic":
        if data.get("observed_agent_id") != data["agent_id"]:
            raise ValueError("agent_contract_identity_mismatch")
        if field.startswith("monitoring_"):
            if (data.get("monitoring_ci_id") != data["ci_id"] or
                    not isinstance(sources.get("monitoring"), str) or not sources["monitoring"].strip()):
                raise ValueError("agent_contract_monitoring_identity_missing_or_mismatched")
    elif data.get("audit_agent_id") != data["agent_id"]:
        raise ValueError("agent_contract_audit_identity_mismatch")
    if field in {"plugin_present", "plugin_version"}:
        name = bindings.get("plugin_name")
        plugins = data.get("matched_plugins")
        if not isinstance(name, str) or not name.strip() or not isinstance(plugins, list):
            raise ValueError("agent_contract_plugin_missing")
        matched = [item for item in plugins if isinstance(item, dict) and item.get("name") == name]
        if len(matched) > 1 or data.get("plugin_name") != name:
            raise ValueError("agent_contract_plugin_absent_or_ambiguous")
        if field == "plugin_present":
            return len(matched) == 1
        if not matched:
            raise ValueError("agent_contract_plugin_absent_or_ambiguous")
        return matched[0].get("version")
    return data.get(field)


def validate_reported_fact(actual, operator):
    if operator == "nonempty":
        valid = isinstance(actual, str) and bool(actual.strip())
    elif operator == "statuses_reported":
        valid = isinstance(actual, dict) and all(
            actual.get(key) in {"online", "offline"} for key in ("ui", "ci", "agent"))
    elif operator == "age_reported":
        # Same bounded clock-skew tolerance as the observer, no freshness relaxation.
        valid = type(actual) in (int, float) and math.isfinite(actual) and actual >= -120
    elif operator == "timestamp_reported":
        try:
            parsed = datetime.fromisoformat(actual.replace("Z", "+00:00"))
            valid = parsed.tzinfo is not None
        except (ValueError, TypeError, AttributeError):
            valid = False
    else:
        valid = False
    if not valid:
        raise ValueError("frontend_contract_fact_missing_or_invalid")
    return True


def normalized_origin(url):
    parsed = urlsplit(str(url or ""))
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("frontend_contract_url_invalid")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return (parsed.scheme, parsed.hostname.lower(), port)


def evaluate_contract(case, requirement, check, saved_url):
    """Rebuild references and assertions from Core records, never model claims."""
    output = deepcopy(check)
    contract = (requirement.get("check_contracts") or {}).get(check.get("check_id"))
    if contract is None:
        return None
    reason = None
    try:
        validate_contracts({check["check_id"]: contract})
        subject = (requirement.get("bindings") or {}).get(contract["subject_binding"])
        if not isinstance(subject, str) or not subject.strip():
            raise ValueError("frontend_contract_subject_missing")
        tool = contract["tool"]
        observation_type = TOOL_FIELDS[tool][0]
        evidence_by_observation = {}
        for evidence in case.get("evidence") or []:
            if evidence.get("type") != tool:
                continue
            for ref in evidence.get("observation_ids") or []:
                evidence_by_observation.setdefault(ref, []).append(evidence)
        candidates = []
        for observation in case.get("observations") or []:
            data = observation.get("data") or {}
            linked = evidence_by_observation.get(observation.get("observation_id")) or []
            if observation.get("type") == observation_type and data.get("tool") == tool:
                candidates.append((observation, linked))
        if not candidates:
            raise ValueError("frontend_contract_observation_missing")
        # Case-local persistence order determines the latest matching fact.
        observation, linked = candidates[-1]
        data = observation["data"]
        is_agent = observation_type in {"agent_telemetry", "agent_plugin_audit"}
        if is_agent and normalized_origin(data.get("url")) != normalized_origin(saved_url):
            raise ValueError("agent_contract_stand_origin_mismatch")
        if data.get("ci_name" if is_agent else "subject") != subject:
            raise ValueError("frontend_contract_subject_mismatch")
        if observation_type == "ui_element" and data.get("exact") is not True:
            raise ValueError("frontend_contract_exact_row_required")
        if len(linked) != 1 or linked[0].get("usable_for_verdict") is not True:
            raise ValueError("frontend_contract_evidence_unusable_or_ambiguous")
        evidence = linked[0]
        computed = []
        for assertion in contract["assertions"]:
            field = assertion["field"]
            actual = agent_fact(data, field, requirement.get("bindings") or {}) if is_agent else data.get(field)
            if assertion["operator"] == "same_origin":
                expected = normalized_origin(saved_url)
                actual = normalized_origin(actual)
                satisfied = actual == expected
            elif assertion["operator"] == "eq":
                expected = assertion["expected"]
                if type(actual) is not type(expected):
                    raise ValueError("frontend_contract_fact_missing_or_invalid")
                satisfied = actual == expected
            else:
                expected = "reported"
                satisfied = validate_reported_fact(actual, assertion["operator"])
            computed.append({"field": field, "operator": assertion["operator"],
                             "expected": expected, "actual": actual, "satisfied": satisfied,
                             "observation_id": observation["observation_id"]})
        actual_facts = {a["field"]: a["actual"] for a in computed}
        if is_agent:
            actual_facts["freshness"] = {key: data.get(key) for key in (
                "monitoring_at", "monitoring_age_seconds", "monitoring_fresh",
                "last_audit_at", "audit_age_seconds", "audit_fresh") if key in data}
        output.update(status="passed" if all(a["satisfied"] for a in computed) else "failed",
                      subject=subject, evidence=[evidence["evidence_id"]],
                      observations=[observation["observation_id"]], assertions=computed,
                      actual=actual_facts,
                      reason=None if all(a["satisfied"] for a in computed)
                      else "UQA CORE: frontend_contract_mismatch")
    except (ValueError, TypeError, KeyError) as exc:
        reason = str(exc) if isinstance(exc, ValueError) else "frontend_contract_invalid"
        output.update(status="blocked", actual=None, assertions=[], evidence=[], observations=[],
                      reason="UQA CORE: " + reason)
    return output, reason
