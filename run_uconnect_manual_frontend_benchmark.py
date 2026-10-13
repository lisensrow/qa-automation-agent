import argparse
import json
import os
from collections import Counter
from pathlib import Path


ROOT = Path(os.getenv("UQA_SMOKE_ROOT", "/opt/uqa")).resolve()
MANIFEST = ROOT / "benchmarks" / "uconnect_manual_frontend_cases.json"
ACTION_PROFILES = {"read_only", "write_ui_state", "write_resource"}
EXECUTION_STATUSES = {"ready", "candidate", "blocked_external"}
ACTIVE_PREPARED_JOB_STATUSES = {"created", "running"}


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
        if "check_contracts" in case:
            from frontend_check_contracts import validate_contracts
            validate_contracts(case["check_contracts"])
            if set(case["check_contracts"]) != {
                f"planned-{index:03d}" for index in range(1, len(case["checks"]) + 1)
            }:
                raise ValueError("frontend_contract_plan_coverage_invalid")
        if case["execution_status"] == "blocked_external" and not case.get(
            "blocker"
        ):
            raise ValueError(f"{case['case_id']}:blocker_required")
        if case["execution_status"] == "candidate" and (
            not isinstance(case.get("candidate_reason"), str)
            or not case["candidate_reason"].strip()
        ):
            raise ValueError(f"{case['case_id']}:candidate_reason_required")
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


def get_case(document, case_id):
    requested = str(case_id or "").strip()
    for case in document["cases"]:
        if case["case_id"] == requested:
            return case
    raise ValueError(f"manual_frontend_case_unknown:{requested}")


def parse_bindings(items):
    bindings = {}
    for item in items or []:
        key, separator, value = str(item).partition("=")
        key = key.strip()
        value = value.strip()
        if not separator or not key or not value:
            raise ValueError("manual_frontend_binding_invalid")
        if key in bindings:
            raise ValueError(f"manual_frontend_binding_duplicate:{key}")
        bindings[key] = value
    return bindings


def build_job_spec(document, case_id, stand, bindings=None):
    case = get_case(document, case_id)
    stand = str(stand or "").strip()
    bindings = dict(bindings or {})

    if case["execution_status"] != "ready":
        raise ValueError(
            f"{case['case_id']}:execution_not_ready:"
            f"{case['execution_status']}"
        )
    if not stand:
        raise ValueError(f"{case['case_id']}:stand_required")

    required_bindings = {
        item for item in case["prerequisites"]
        if item != "saved_stand"
    }
    missing = sorted(required_bindings - set(bindings))
    unknown = sorted(set(bindings) - required_bindings)
    if missing:
        raise ValueError(
            f"{case['case_id']}:bindings_missing:{','.join(missing)}"
        )
    if unknown:
        raise ValueError(
            f"{case['case_id']}:bindings_unknown:{','.join(unknown)}"
        )
    if any(not str(value).strip() for value in bindings.values()):
        raise ValueError(f"{case['case_id']}:binding_value_required")

    normalized_bindings = {
        key: str(bindings[key]).strip()
        for key in sorted(bindings)
    }
    input_lines = [
        f"- {key}: {value}"
        for key, value in normalized_bindings.items()
    ]
    request = case["task"].strip()
    if input_lines:
        request += "\n\nBound inputs:\n" + "\n".join(input_lines)

    requirement = {
        "source": "uconnect_manual_frontend_corpus",
        "product": document["product"],
        "manifest_schema_version": document["schema_version"],
        "source_case_id": case["case_id"],
        "category": case["category"],
        "action_profile": case["action_profile"],
        "execution_status": case["execution_status"],
        "prerequisites": list(case["prerequisites"]),
        "bindings": normalized_bindings,
        "stand": stand,
        "policy_required": case.get("policy_required") is True,
        "cleanup_contract": case.get("cleanup_contract"),
    }
    if "check_contracts" in case:
        from copy import deepcopy
        from frontend_check_contracts import validate_contracts
        validate_contracts(case["check_contracts"])
        if set(case["check_contracts"]) != {f"planned-{i:03d}" for i in range(1,len(case["checks"])+1)}:
            raise ValueError("frontend_contract_plan_coverage_invalid")
        requirement.update(type="frontend_contracts", version=1, locked=True)
        requirement["check_contracts"] = deepcopy(case["check_contracts"])
    if "required_observation" in case:
        from copy import deepcopy
        requirement["required_observation"] = deepcopy(case["required_observation"])
    return {
        "request": request,
        "stand": stand,
        "external_id": case["case_id"],
        "job_type": "regression",
        "case": {
            "title": case["title"],
            "expected": "; ".join(case["checks"]),
            "requirement": requirement,
            "planned_checks": list(case["checks"]),
        },
    }


def find_existing_prepared_job(spec, jobs):
    expected_case = spec["case"]
    expected_requirement = expected_case["requirement"]
    for job in jobs or []:
        if not isinstance(job, dict) or not job.get("job_id"):
            continue
        if job.get("status") not in ACTIVE_PREPARED_JOB_STATUSES:
            continue
        if job.get("job_type") != spec["job_type"]:
            continue
        if job.get("external_id") != spec["external_id"]:
            continue
        if job.get("stand") != spec["stand"]:
            continue
        if job.get("request") != spec["request"]:
            continue

        cases = job.get("test_cases") or []
        if not isinstance(cases, list) or len(cases) != 1:
            continue
        case = cases[0]
        if not isinstance(case, dict) or not case.get("case_id"):
            continue
        if case.get("status") not in {"pending", "running"}:
            continue
        # Reuse only the same execution contract, including safety boundaries.
        # A matching source ID and bindings alone do not identify the same task.
        if case.get("requirement") != expected_requirement:
            continue
        if any(case.get(key) != expected_case.get(key)
               for key in ("title", "expected", "planned_checks")):
            continue

        return {
            "job_id": job.get("job_id"),
            "case_id": case.get("case_id"),
            "source_case_id": spec["external_id"],
            "stand": spec["stand"],
            "reused": True,
        }
    return None


def materialize_job(
    spec,
    job_creator=None,
    case_adder=None,
    job_lister=None,
):
    custom_store = any(
        item is not None
        for item in (job_creator, case_adder, job_lister)
    )
    if job_creator is None or case_adder is None or job_lister is None:
        from job_store import add_test_case, create_job, list_jobs

        job_creator = job_creator or create_job
        case_adder = case_adder or add_test_case
        job_lister = job_lister or (
            (lambda limit: [])
            if custom_store
            else list_jobs
        )

    existing = find_existing_prepared_job(
        spec,
        job_lister(None),
    )
    if existing is not None:
        return existing

    job = job_creator(
        spec["request"],
        stand=spec["stand"],
        external_id=spec["external_id"],
        job_type=spec["job_type"],
    )
    case = case_adder(job["job_id"], **spec["case"])
    return {
        "job_id": job["job_id"],
        "case_id": case["case_id"],
        "source_case_id": spec["external_id"],
        "stand": spec["stand"],
        "reused": False,
    }


def build_parser():
    parser = argparse.ArgumentParser(
        description="Validate or materialize a U-Connect frontend corpus case."
    )
    parser.add_argument("--case-id")
    parser.add_argument("--stand")
    parser.add_argument(
        "--bind",
        action="append",
        default=[],
        metavar="KEY=VALUE",
    )
    parser.add_argument("--create-job", action="store_true")
    return parser


def main():
    document = load_and_validate_manifest()
    summary = summarize(document)
    print(
        "UCONNECT_MANUAL_FRONTEND_BENCHMARK_JSON="
        + json.dumps(summary, ensure_ascii=False, sort_keys=True)
    )
    print(f"uconnect manual frontend manifest: PASS ({summary['total']} cases)")

    args = build_parser().parse_args()
    if args.create_job:
        if not args.case_id:
            raise ValueError("manual_frontend_case_id_required")
        spec = build_job_spec(
            document,
            args.case_id,
            args.stand,
            parse_bindings(args.bind),
        )
        result = materialize_job(spec)
        print(
            "UCONNECT_MANUAL_FRONTEND_JOB_JSON="
            + json.dumps(result, ensure_ascii=False, sort_keys=True)
        )
    elif args.case_id or args.stand or args.bind:
        raise ValueError("manual_frontend_create_job_required")


if __name__ == "__main__":
    main()
