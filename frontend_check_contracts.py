"""Deterministic contracts over trusted browser observations; no product routing."""
from copy import deepcopy
from urllib.parse import urlsplit

TOOL_FIELDS = {
    "browser_inspect_table_row": ("ui_element", {"row_match_count"}),
    "browser_open_exact_table_row_details_semantic": (
        "ui_details_identity", {"details_identity_passed", "row_opened", "url"}),
}


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
            if operator not in {"eq", "same_origin"}:
                raise ValueError("frontend_contract_operator_invalid")
            if operator == "same_origin" and assertion["field"] != "url":
                raise ValueError("frontend_contract_origin_field_invalid")
            if operator == "eq" and type(assertion.get("expected")) not in (bool, int):
                raise ValueError("frontend_contract_expected_invalid")


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
        if data.get("subject") != subject:
            raise ValueError("frontend_contract_subject_mismatch")
        if observation_type == "ui_element" and data.get("exact") is not True:
            raise ValueError("frontend_contract_exact_row_required")
        if len(linked) != 1 or linked[0].get("usable_for_verdict") is not True:
            raise ValueError("frontend_contract_evidence_unusable_or_ambiguous")
        evidence = linked[0]
        computed = []
        for assertion in contract["assertions"]:
            field = assertion["field"]
            actual = data.get(field)
            if assertion["operator"] == "same_origin":
                expected = normalized_origin(saved_url)
                actual = normalized_origin(actual)
                satisfied = actual == expected
            else:
                expected = assertion["expected"]
                if type(actual) is not type(expected):
                    raise ValueError("frontend_contract_fact_missing_or_invalid")
                satisfied = actual == expected
            computed.append({"field": field, "operator": assertion["operator"],
                             "expected": expected, "actual": actual, "satisfied": satisfied,
                             "observation_id": observation["observation_id"]})
        output.update(status="passed" if all(a["satisfied"] for a in computed) else "failed",
                      subject=subject, evidence=[evidence["evidence_id"]],
                      observations=[observation["observation_id"]], assertions=computed,
                      actual={a["field"]: a["actual"] for a in computed},
                      reason=None if all(a["satisfied"] for a in computed)
                      else "UQA CORE: frontend_contract_mismatch")
    except (ValueError, TypeError, KeyError) as exc:
        reason = str(exc) if isinstance(exc, ValueError) else "frontend_contract_invalid"
        output.update(status="blocked", actual=None, assertions=[], evidence=[], observations=[],
                      reason="UQA CORE: " + reason)
    return output, reason
