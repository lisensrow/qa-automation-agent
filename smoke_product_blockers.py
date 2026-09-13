#!/opt/uqa/.venv/bin/python

from pathlib import Path
from tempfile import TemporaryDirectory

import job_store


with TemporaryDirectory() as directory:
    job_store.BLOCKERS_PATH = (
        Path(directory) / "product-blockers.json"
    )

    created = job_store.record_product_blocker(
        blocker_id="blk-cleanup-example",
        capability="cleanup.example",
        reason="operation unavailable",
        source_job="job-1",
        affected_resource_id="res-1",
        product_versions={"backend": "1.0", "frontend": "2.0"},
        evidence={"status": 404, "api_token": "must-not-leak"},
        retry_when="backend or frontend version changes",
        required_work="re-run capability probe",
    )
    assert created["status"] == "open"
    assert created["evidence"]["api_token"] == "[REDACTED]"

    updated = job_store.record_product_blocker(
        blocker_id="blk-cleanup-example",
        capability="cleanup.example",
        reason="still unavailable",
        source_job="job-2",
        affected_resource_id="res-2",
        product_versions={"backend": "1.0", "frontend": "2.0"},
        evidence={"status": 404},
    )
    assert updated["source_jobs"] == ["job-1", "job-2"]
    assert updated["affected_resources"] == ["res-1", "res-2"]
    assert len(job_store.list_product_blockers()) == 1

    changed = job_store.mark_product_blockers_for_version_change(
        {"backend": "1.1", "frontend": "2.0"}
    )
    assert changed == ["blk-cleanup-example"]
    assert job_store.list_product_blockers()[0]["status"] == "needs_recheck"

    resolved = job_store.update_product_blocker_status(
        "blk-cleanup-example",
        "resolved",
        reason="verified in backend 1.1",
    )
    assert resolved["resolved_at"]
    assert job_store.list_product_blockers("open") == []

print("smoke_product_blockers: PASS")
