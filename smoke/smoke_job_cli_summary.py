import uqa


job = {
    "job_id": "job-safe-summary",
    "status": "created",
    "job_type": "regression",
    "stand": "lab",
    "external_id": "uc-front-009",
    "created_at": "2026-10-12T00:00:00+00:00",
    "updated_at": "2026-10-12T00:01:00+00:00",
    "cleanup_status": "not_required",
    "request": "SECRET REQUEST BODY",
    "summary": "SECRET MODEL SUMMARY",
    "resources": [
        {
            "resource_id": "resource-1",
            "name": "SECRET RESOURCE NAME",
        }
    ],
    "test_cases": [
        {
            "case_id": "case-safe-summary",
            "title": "SECRET CASE TITLE",
            "status": "pending",
            "planned_checks": ["SECRET EXPECTATION"],
            "checks": [],
            "evidence": [{"content": "SECRET EVIDENCE"}],
            "observations": [{"content": "SECRET OBSERVATION"}],
        }
    ],
}

assert uqa._parse_job_command("/job job-safe-summary") == "job-safe-summary"
assert uqa._parse_job_command("/job") == ""
assert uqa._parse_job_command("/jobs") is None

overview = uqa._safe_job_overview(job)
assert overview == {
    "job_id": "job-safe-summary",
    "status": "created",
    "job_type": "regression",
    "stand": "lab",
    "external_id": "uc-front-009",
    "created_at": "2026-10-12T00:00:00+00:00",
    "updated_at": "2026-10-12T00:01:00+00:00",
    "cleanup_status": "not_required",
    "case_count": 1,
    "resource_count": 1,
    "cases": [
        {
            "case_id": "case-safe-summary",
            "status": "pending",
            "planned_checks": 1,
            "checks": 0,
            "evidence": 1,
            "observations": 1,
        }
    ],
}
serialized = str(overview)
for secret in (
    "SECRET REQUEST BODY",
    "SECRET MODEL SUMMARY",
    "SECRET RESOURCE NAME",
    "SECRET CASE TITLE",
    "SECRET EXPECTATION",
    "SECRET EVIDENCE",
    "SECRET OBSERVATION",
):
    assert secret not in serialized

saved_get_job = uqa.get_job
saved_list_jobs = uqa.list_jobs
try:
    uqa.get_job = lambda job_id: job
    uqa.list_jobs = lambda limit: [job]
    assert uqa._print_job_overview("job-safe-summary") == overview
    assert uqa._print_recent_jobs() == [overview]
finally:
    uqa.get_job = saved_get_job
    uqa.list_jobs = saved_list_jobs

print("safe Job CLI summary smoke: PASS")
