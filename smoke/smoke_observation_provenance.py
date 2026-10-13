from copy import deepcopy
import uqa

job = {"job_id": "job-local", "job_type": "regression", "test_cases": [{
    "case_id": "case-local", "evidence": [
        {"evidence_id": "ev-local", "type": "browser_open_exact_table_row_details_semantic",
         "observation_ids": ["obs-local"], "usable_for_verdict": True},
        {"evidence_id": "ev-other", "type": "browser_open_page",
         "observation_ids": ["obs-other"], "usable_for_verdict": True}],
    "observations": [{"observation_id": "obs-local", "type": "ui_state", "data": {}},
                     {"observation_id": "obs-other", "type": "ui_state", "data": {}}],
}]}
saved_get_job = uqa.get_job
try:
    uqa.get_job = lambda _: deepcopy(job)
    for status in ("passed", "failed"):
        check = {"check_id": "check-local", "title": "provenance only",
                 "status": status, "evidence": ["ev-local"],
                 "observations": ["obs-local"]}
        verified, errors = uqa.verify_structured_check_evidence("job-local", "case-local", [check])
        assert not errors and verified[0]["status"] == status
        for observations, issue in (
            (["obs-invented"], "unknown_observation_ids"),
            (["obs-other"], "observation_not_linked_to_evidence"),
            ([], "observation_missing"),
            (["obs-local", "obs-invented"], "unknown_observation_ids"),
        ):
            candidate = deepcopy(check)
            candidate["observations"] = observations
            verified, errors = uqa.verify_structured_check_evidence("job-local", "case-local", [candidate])
            assert verified[0]["status"] == "blocked"
            assert issue in str(errors)
            assert candidate["status"] == status  # Caller input unchanged.
        for reference, issue in (
            ("obs-invented", "unknown_observation_ids"),
            ("obs-other", "observation_not_linked_to_evidence"),
        ):
            candidate = deepcopy(check)
            candidate["assertions"] = [{"field": "identity", "operator": "eq",
                                        "expected": True, "observation_id": reference}]
            verified, errors = uqa.verify_structured_check_evidence("job-local", "case-local", [candidate])
            assert verified[0]["status"] == "blocked" and issue in str(errors)
finally:
    uqa.get_job = saved_get_job
print("all-type observation provenance smoke: PASS")
