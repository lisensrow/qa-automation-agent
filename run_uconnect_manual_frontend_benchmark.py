import json
import os
from collections import Counter
from pathlib import Path


ROOT = Path(os.getenv("UQA_SMOKE_ROOT", "/opt/uqa")).resolve()
MANIFEST = ROOT / "benchmarks" / "uconnect_manual_frontend_cases.json"
ACTION_PROFILES = {"read_only", "write_ui_state", "write_resource"}
EXECUTION_STATUSES = {"ready", "candidate", "blocked_external"}


def load_and_validate_manifest():
    document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1:
        raise ValueError("manual_frontend_schema_version_invalid")
    if document.get("product") != "U-Connect":
        raise ValueError("manual_frontend_product_invalid")
    cases = document.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("manual_frontend_cases_required")

    ids = [case.get("case_id") for case in cases if isinstance(case, dict)]
    if len(ids) != len(cases) or any(not item for item in ids):
        raise ValueError("manual_frontend_case_id_required")
    if len(set(ids)) != len(ids):
        raise ValueError("manual_frontend_case_id_duplicate")

    for case in cases:
        for key in ("category", "title", "task"):
            if not isinstance(case.get(key), str) or not case[key].strip():
                raise ValueError(f"{case['case_id']}:{key}_required")
        if case.get("action_profile") not in ACTION_PROFILES:
            raise ValueError(f"{case['case_id']}:action_profile_invalid")
        if case.get("execution_status") not in EXECUTION_STATUSES:
            raise ValueError(f"{case['case_id']}:execution_status_invalid")
        if len(case.get("prerequisites") or []) < 2:
            raise ValueError(f"{case['case_id']}:prerequisites_incomplete")
        if len(case.get("checks") or []) < 2:
            raise ValueError(f"{case['case_id']}:checks_incomplete")
        if case["action_profile"] != "read_only":
            if case.get("policy_required") is not True:
                raise ValueError(f"{case['case_id']}:policy_required")
            if not case.get("cleanup_contract"):
                raise ValueError(f"{case['case_id']}:cleanup_contract_required")
        if case["execution_status"] == "blocked_external" and not case.get(
            "blocker"
        ):
            raise ValueError(f"{case['case_id']}:blocker_required")
    return document


def summarize(document):
    cases = document["cases"]
    return {
        "total": len(cases),
        "categories": dict(sorted(Counter(
            case["category"] for case in cases
        ).items())),
        "execution_statuses": dict(sorted(Counter(
            case["execution_status"] for case in cases
        ).items())),
        "action_profiles": dict(sorted(Counter(
            case["action_profile"] for case in cases
        ).items())),
    }


def main():
    summary = summarize(load_and_validate_manifest())
    print(
        "UCONNECT_MANUAL_FRONTEND_BENCHMARK_JSON="
        + json.dumps(summary, ensure_ascii=False, sort_keys=True)
    )
    print(f"uconnect manual frontend manifest: PASS ({summary['total']} cases)")


if __name__ == "__main__":
    main()
