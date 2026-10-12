from copy import deepcopy

from run_uconnect_manual_frontend_benchmark import (
    build_job_spec,
    find_existing_prepared_job,
    load_and_validate_manifest,
    materialize_job,
)


document = load_and_validate_manifest()
spec = build_job_spec(
    document,
    "uc-front-009",
    "lab",
    {"exact_ci_name": "home-server-UC-ubuntu22"},
)

existing_job = {
    "job_id": "job-existing",
    "status": "created",
    "job_type": "regression",
    "external_id": "uc-front-009",
    "stand": "lab",
    "test_cases": [
        {
            "case_id": "case-existing",
            "status": "pending",
            "requirement": deepcopy(spec["case"]["requirement"]),
            "planned_checks": list(spec["case"]["planned_checks"]),
        }
    ],
}

match = find_existing_prepared_job(spec, [existing_job])
assert match == {
    "job_id": "job-existing",
    "case_id": "case-existing",
    "source_case_id": "uc-front-009",
    "stand": "lab",
    "reused": True,
}

calls = {"create": 0, "add": 0}


def reject_create(*args, **kwargs):
    calls["create"] += 1
    raise AssertionError("duplicate Job creation was attempted")


def reject_add(*args, **kwargs):
    calls["add"] += 1
    raise AssertionError("duplicate case creation was attempted")


reused = materialize_job(
    spec,
    job_creator=reject_create,
    case_adder=reject_add,
    job_lister=lambda limit: [deepcopy(existing_job)],
)
assert reused == match
assert calls == {"create": 0, "add": 0}

for mutation in (
    lambda job: job.update(status="passed"),
    lambda job: job.update(stand="other"),
    lambda job: job["test_cases"][0]["requirement"]["bindings"].update(
        exact_ci_name="different-ci"
    ),
    lambda job: job["test_cases"][0].update(planned_checks=["different"]),
):
    candidate = deepcopy(existing_job)
    mutation(candidate)
    assert find_existing_prepared_job(spec, [candidate]) is None

print("prepared Job deduplication smoke: PASS")
