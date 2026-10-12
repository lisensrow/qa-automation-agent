import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import job_store


saved_jobs_dir = job_store.JOBS_DIR
try:
    with tempfile.TemporaryDirectory(prefix="uqa-job-list-all-") as root:
        job_store.JOBS_DIR = Path(root) / "jobs"
        job_store.JOBS_DIR.mkdir(parents=True)
        created_base = datetime(2026, 10, 13, tzinfo=timezone.utc)
        for index in range(105):
            payload = {
                "job_id": f"job-{index:03d}",
                "created_at": (
                    created_base + timedelta(seconds=index)
                ).isoformat(),
            }
            path = job_store.JOBS_DIR / f"job-{index:03d}.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

        all_jobs = job_store.list_jobs(None)
        bounded_jobs = job_store.list_jobs(100)
        defaulted_jobs = job_store.list_jobs("invalid")
        assert len(all_jobs) == 105
        assert len(bounded_jobs) == 100
        assert len(defaulted_jobs) == 20
        assert all_jobs[0]["job_id"] == "job-104"
finally:
    job_store.JOBS_DIR = saved_jobs_dir

print("unbounded internal Job listing smoke: PASS")
