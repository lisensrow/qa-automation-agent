import uqa


prepared = {
    "job_id": "job-queue-safe",
    "job_type": "regression",
    "status": "created",
    "stand": "lab",
    "external_id": "case-source-safe",
    "updated_at": "2026-10-13T00:00:00+00:00",
    "request": "SECRET REQUEST",
    "resources": [{"name": "SECRET RESOURCE"}],
    "test_cases": [
        {
            "case_id": "case-queue-safe",
            "status": "pending",
            "title": "SECRET TITLE",
            "requirement": {
                "source": "manual_frontend_corpus",
                "execution_status": "ready",
                "bindings": {"secret": "SECRET BINDING"},
            },
            "planned_checks": ["SECRET CHECK ONE", "SECRET CHECK TWO"],
            "evidence": [{"content": "SECRET EVIDENCE"}],
            "observations": [{"content": "SECRET OBSERVATION"}],
        }
    ],
}

overview = uqa._prepared_queue_overview(prepared)
assert overview == {
    "job_id": "job-queue-safe",
    "status": "created",
    "stand": "lab",
    "external_id": "case-source-safe",
    "updated_at": "2026-10-13T00:00:00+00:00",
    "case_id": "case-queue-safe",
    "case_status": "pending",
    "planned_checks": 2,
}
serialized = str(overview)
for secret in (
    "SECRET REQUEST",
    "SECRET RESOURCE",
    "SECRET TITLE",
    "SECRET BINDING",
    "SECRET CHECK ONE",
    "SECRET EVIDENCE",
    "SECRET OBSERVATION",
):
    assert secret not in serialized

for invalid in (
    {**prepared, "status": "passed"},
    {**prepared, "job_type": "chat"},
    {**prepared, "test_cases": []},
):
    assert uqa._prepared_queue_overview(invalid) is None

saved_list_jobs = uqa.list_jobs
try:
    uqa.list_jobs = lambda limit: [prepared]
    assert uqa._print_prepared_job_queue() == [overview]
finally:
    uqa.list_jobs = saved_list_jobs

print("prepared Job queue smoke: PASS")
