from copy import deepcopy
import json
import uqa
from frontend_check_contracts import evaluate_contract
from observation_extractor import extract_observations
from run_uconnect_manual_frontend_benchmark import build_job_spec, load_and_validate_manifest

spec = build_job_spec(load_and_validate_manifest(), "uc-front-002", "lab",
                      {"exact_ci_name": "fixture-ci", "requested_tab_names": '["Agent","Monitoring"]'})
tool = "browser_verify_exact_table_row_tabs_semantic"
case = dict(spec["case"], case_id="case-1")
job = {"job_type": "regression", "test_cases": [case]}
locked = uqa.prepared_observation_contract(job, "case-1")
assert locked == {"tool": tool, "arguments": {"name": "fixture-ci", "tabs": ["Agent", "Monitoring"]}}
templates = uqa.prepared_contract_check_templates(job, "case-1")
for value in ('Agent,Monitoring', '["Agent","agent"]', '[]', '[true]', '{}', '[""]',
              '["Delete"]', '["Save"]', '["Apply"]', '["Add"]',
              json.dumps([f"Tab-{i}" for i in range(21)])):
    candidate = deepcopy(job)
    candidate["test_cases"][0]["requirement"]["bindings"]["requested_tab_names"] = value
    try:
        uqa.prepared_observation_contract(candidate, "case-1")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid list binding accepted")
records = [{"tab": name, "selected_tab": name, "selected_count": 1,
            "panel_exists": True, "panel_visible": True, "controls": "panel-"+name,
            "details_identity_preserved": True} for name in ("Agent", "Monitoring")]
observation = extract_observations(tool, locked["arguments"], {
    "name": "fixture-ci", "requested_tabs": ["Agent", "Monitoring"], "tabs_verified": records,
    "details_identity_passed": True, "details_identity_preserved": True,
    "current_url": "https://fixture.test/items/1"})[0]
observation["observation_id"] = "obs-1"
case.update(observations=[observation], evidence=[{"evidence_id": "ev-1", "type": tool,
            "observation_ids": ["obs-1"], "usable_for_verdict": True}])
def verify(candidate):
    return [evaluate_contract(candidate, case["requirement"], check, "https://fixture.test")[0]
            for check in templates]
assert [check["status"] for check in verify(case)] == ["passed"]*3
for changes, index, status in (
    ({"selected_count": 2}, 0, "failed"), ({"selected_tab": "wrong"}, 0, "failed"),
    ({"selected_count": True}, 0, "blocked"), ({"panel_visible": False}, 1, "failed"),
    ({"panel_exists": None}, 1, "blocked"), ({"controls": ""}, 1, "blocked"),
    ({"details_identity_preserved": False}, 2, "failed"),
    ({"details_identity_preserved": None}, 2, "blocked"),
):
    candidate = deepcopy(case)
    candidate["observations"][0]["data"]["tabs_verified"][1].update(changes)
    assert verify(candidate)[index]["status"] == status, changes
for changes in ({"requested_tabs": ["Agent"]}, {"tabs_verified": records[:1]},
                {"subject": "wrong-ci"}, {"url": "https://other.test/items"}):
    candidate = deepcopy(case)
    candidate["observations"][0]["data"].update(changes)
    assert all(check["status"] == "blocked" for check in verify(candidate)), changes
candidate = deepcopy(case)
candidate["evidence"][0]["usable_for_verdict"] = False
assert all(check["status"] == "blocked" for check in verify(candidate))
print("locked tab navigation contracts: PASS (fixtures only)")
