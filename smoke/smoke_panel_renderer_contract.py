from copy import deepcopy
from frontend_check_contracts import evaluate_contract
from observation_extractor import extract_observations
from run_uconnect_manual_frontend_benchmark import build_job_spec, load_and_validate_manifest
import uqa

spec = build_job_spec(load_and_validate_manifest(), "uc-front-017", "lab",
                      {"exact_ci_name": "fixture-ci", "requested_tab_names": '["Monitoring"]'})
case = dict(spec["case"], case_id="case-1")
job = {"job_type": "regression", "test_cases": [case]}
tool = "browser_verify_exact_table_row_tabs_semantic"
checks = uqa.prepared_contract_check_templates(job, "case-1")
record = {"tab": "Monitoring", "selected_tab": "Monitoring", "selected_count": 1,
          "controls": "panel", "panel_exists": True, "panel_visible": True,
          "details_identity_preserved": True, "panel_renderer_audit_observed": True,
          "panel_renderer_scan_complete": True, "panel_renderer_error_markers": []}
observation = extract_observations(tool, {"name": "fixture-ci", "tabs": ["Monitoring"]}, {
    "name": "fixture-ci", "requested_tabs": ["Monitoring"], "tabs_verified": [record],
    "details_identity_passed": True, "current_url": "https://fixture.test/items/1"})[0]
observation["observation_id"] = "obs-1"
case.update(observations=[observation], evidence=[{"type": tool, "evidence_id": "ev-1",
    "observation_ids": ["obs-1"], "usable_for_verdict": True}])
def verify(candidate):
    return [evaluate_contract(candidate, case["requirement"], c, "https://fixture.test")[0] for c in checks]
assert [c["status"] for c in verify(case)] == ["passed"]*3
for marker in ("infinite_extent", "javascript_type_error", "javascript_reference_error", "javascript_syntax_error"):
    candidate = deepcopy(case)
    candidate["observations"][0]["data"]["tabs_verified"][0]["panel_renderer_error_markers"] = [marker]
    verified = verify(candidate)
    assert [c["status"] for c in verified] == ["passed", "passed", "failed"]
    assert verified[2]["actual"]["renderer_errors_by_tab"] == {"Monitoring": [marker]}
for changes in ({"panel_renderer_audit_observed": False}, {"panel_renderer_scan_complete": False},
                {"panel_renderer_error_markers": None}, {"panel_renderer_error_markers": ["unknown"]}):
    candidate = deepcopy(case)
    candidate["observations"][0]["data"]["tabs_verified"][0].update(changes)
    assert verify(candidate)[2]["status"] == "blocked", changes
    assert verify(candidate)[0]["status"] == "passed"
candidate = deepcopy(case)
candidate["observations"][0]["data"]["tabs_verified"][0].update(
    panel_renderer_scan_complete=False, panel_renderer_error_markers=["infinite_extent"])
assert verify(candidate)[2]["status"] == "failed"  # Positive visible error remains proven, not an absence claim.
candidate["evidence"][0]["usable_for_verdict"] = False
assert all(c["status"] == "blocked" for c in verify(candidate))
print("known panel renderer message contracts: PASS (fixtures only)")
