from copy import deepcopy
import uqa
from observation_extractor import extract_observations
from run_uconnect_manual_frontend_benchmark import build_job_spec, load_and_validate_manifest

spec = build_job_spec(load_and_validate_manifest(), "uc-front-001", "lab", {"exact_ci_name": "fixture-ci"})
requirement = spec["case"]["requirement"]
row = extract_observations("browser_inspect_table_row", {"name": "fixture-ci"},
                           {"row_match_count": 1})[0]
details = extract_observations("browser_open_exact_table_row_details_semantic", {"name": "fixture-ci"},
                               {"name": "fixture-ci", "row_opened": True,
                                "details_identity_passed": True,
                                "current_url": "https://fixture.test:443/items/123?view=agent"})[0]
row["observation_id"] = "obs-row"
details["observation_id"] = "obs-details"
case = {"case_id": "case-fixture", "requirement": requirement, "observations": [row, details],
        "evidence": [{"evidence_id": "ev-row", "type": "browser_inspect_table_row",
                      "observation_ids": ["obs-row"], "usable_for_verdict": True},
                     {"evidence_id": "ev-details", "type": "browser_open_exact_table_row_details_semantic",
                      "observation_ids": ["obs-details"], "usable_for_verdict": True}]}
checks = [{"check_id": f"planned-{i:03d}", "title": title, "status": "passed",
           "evidence": ["ev-invented"], "observations": ["obs-invented"],
           "assertions": [{"field": "made_up", "expected": True}]}
          for i, title in enumerate(spec["case"]["planned_checks"], 1)]
saved_get_job, saved_get_stand = uqa.get_job, uqa.get_stand

def verify(current):
    uqa.get_job = lambda _: {"job_id": "job-fixture", "job_type": "regression", "stand": "lab",
                            "test_cases": [deepcopy(current)]}
    return uqa.verify_structured_check_evidence("job-fixture", "case-fixture", checks)

try:
    uqa.get_stand = lambda _: {"web_url": "https://fixture.test"}
    verified, errors = verify(case)
    assert not errors and [c["status"] for c in verified] == ["passed"] * 3
    assert all(c["assertions"][0]["satisfied"] is True for c in verified)
    assert verified[2]["assertions"][0]["actual"] == ("https", "fixture.test", 443)
    assert checks[0]["observations"] == ["obs-invented"]
    for mutation, index, expected in (
        (lambda c: c["observations"][0]["data"].update(row_match_count=2), 0, "failed"),
        (lambda c: c["observations"][0]["data"].pop("row_match_count"), 0, "blocked"),
        (lambda c: c["observations"][0]["data"].update(row_match_count=True), 0, "blocked"),
        (lambda c: c["observations"][0]["data"].update(exact=False), 0, "blocked"),
        (lambda c: c["observations"][1]["data"].update(details_identity_passed=False), 1, "failed"),
        (lambda c: c["observations"][1]["data"].update(subject="other-ci"), 1, "blocked"),
        (lambda c: c["observations"][1]["data"].update(url="https://other.test/items"), 2, "failed"),
        (lambda c: c["observations"][1]["data"].update(url="https://fixture.test:444/items"), 2, "failed"),
        (lambda c: c["observations"][1]["data"].update(url="not a URL"), 2, "blocked"),
        (lambda c: c["evidence"][1].update(usable_for_verdict=False), 1, "blocked"),
        (lambda c: c["evidence"][1].update(observation_ids=["obs-row"]), 1, "blocked"),
    ):
        candidate = deepcopy(case)
        mutation(candidate)
        verified, _ = verify(candidate)
        assert verified[index]["status"] == expected, (index, expected, verified)
    # A newer unusable/wrong-subject observation must not reuse an older PASS.
    for changes in ({"subject": "other-ci"}, {"details_identity_passed": None}):
        candidate = deepcopy(case)
        newer = deepcopy(details)
        newer["observation_id"] = "obs-newer"
        newer["data"].update(changes)
        candidate["observations"].append(newer)
        candidate["evidence"].append({"evidence_id": "ev-newer",
            "type": "browser_open_exact_table_row_details_semantic",
            "observation_ids": ["obs-newer"], "usable_for_verdict": True})
        verified, _ = verify(candidate)
        assert verified[1]["status"] == "blocked"
finally:
    uqa.get_job, uqa.get_stand = saved_get_job, saved_get_stand
print("frontend machine check contracts smoke: PASS")
