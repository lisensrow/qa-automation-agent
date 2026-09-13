import ast
import re
from copy import deepcopy
from pathlib import Path


source = Path("uqa.py").read_text(encoding="utf-8")
tree = ast.parse(source)
names = {
    "_normalize_planned_checks",
    "_planned_check_lifecycle_kind",
    "verify_planned_check_coverage",
    "_resource_cleanup_absence_confirmed",
    "verify_resource_lifecycle_checks",
}
module = ast.Module(
    body=[
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in names
    ],
    type_ignores=[],
)

planned = [
    {"title": "Object is created", "expected": "visible"},
    {"title": "Resource registered in UQA ledger", "expected": "registered"},
    {"title": "Cleanup deleted the resource", "expected": "deleted"},
    {"title": "After cleanup the resource does not exist", "expected": "absent"},
]
job = {
    "job_id": "job-smoke",
    "test_cases": [{
        "case_id": "case-smoke",
        "planned_checks": planned,
    }],
    "resources": [],
}


def get_job(job_id):
    assert job_id == "job-smoke"
    return deepcopy(job)


scope = {
    "re": re,
    "get_job": get_job,
    "MAX_REGRESSION_CASES": 20,
}
exec(compile(module, "uqa.py", "exec"), scope)

normalized = scope["_normalize_planned_checks"](planned)
assert [item["check_id"] for item in normalized] == [
    "planned-001",
    "planned-002",
    "planned-003",
    "planned-004",
]

old_false_pass = [{
    "check_id": "check-001",
    "title": "Unrelated authorization page",
    "status": "passed",
    "expected": "authorization",
    "actual": "authorization",
    "evidence": ["ev-1"],
}]
bound, errors = scope["verify_planned_check_coverage"](
    "job-smoke",
    "case-smoke",
    old_false_pass,
)
assert errors
assert any(item["issue"] == "planned_check_count_mismatch" for item in errors)
assert all(item["status"] == "blocked" for item in bound)
assert {item["check_id"] for item in bound} >= {
    "planned-001",
    "planned-002",
    "planned-003",
    "planned-004",
}

exact = [
    {
        "check_id": item["check_id"],
        "title": "model text is not authoritative",
        "status": "passed",
        "expected": None,
        "actual": "model claim",
        "evidence": ["ev-1"],
    }
    for item in normalized
]
bound, errors = scope["verify_planned_check_coverage"](
    "job-smoke",
    "case-smoke",
    exact,
)
assert errors == []
assert [item["title"] for item in bound] == [
    item["title"] for item in normalized
]

job["resources"] = [{
    "resource_id": "res-smoke",
    "created_by_case": "case-smoke",
    "cleanup_required": True,
    "status": "active",
    "cleanup_attempts": [],
}]
verified, lifecycle_ids = scope["verify_resource_lifecycle_checks"](
    "job-smoke",
    "case-smoke",
    bound,
    phase="case",
)
by_id = {item["check_id"]: item for item in verified}
assert lifecycle_ids == {"planned-002", "planned-003", "planned-004"}
assert by_id["planned-001"]["status"] == "passed"
assert by_id["planned-002"]["status"] == "passed"
assert by_id["planned-003"]["status"] == "blocked"
assert by_id["planned-004"]["status"] == "blocked"

job["resources"][0].update({
    "status": "cleaned",
    "cleanup_attempts": [{
        "status": "cleaned",
        "events": [
            {
                "data": {
                    "tool": "browser_click_semantic",
                    "result": {
                        "action_class": "destructive",
                        "action_policy_status": "confirmed",
                        "executed": True,
                    },
                },
            },
            {
                "data": {
                    "tool": "browser_inspect_semantic",
                    "result": {
                        "error": "semantic_element_not_found",
                    },
                },
            },
        ],
    }],
})
verified, _ = scope["verify_resource_lifecycle_checks"](
    "job-smoke",
    "case-smoke",
    bound,
    phase="cleanup",
)
by_id = {item["check_id"]: item for item in verified}
assert by_id["planned-002"]["status"] == "passed"
assert by_id["planned-003"]["status"] == "passed"
assert by_id["planned-004"]["status"] == "passed"

print("planned-check/lifecycle verdict smoke: PASS")
