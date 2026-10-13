"""Reported numeric samples do not prove current load, charts, or fresh data."""
from copy import deepcopy
from datetime import datetime, timezone
from frontend_check_contracts import evaluate_contract
from observation_extractor import extract_observations
from tools.agent_observability import summarize_agent_observation
from run_uconnect_manual_frontend_benchmark import build_job_spec, load_and_validate_manifest

tool = "browser_inspect_agent_telemetry_semantic"
ci = {"id": "ci-1", "agent_id": "agent-1", "name": "fixture-ci", "endpoint_status": "online"}
result = summarize_agent_observation("fixture-ci", ci,
    {"id": "agent-1", "status": "online", "version": "1"},
    {"uid": "ci-1", "created_at": "2026-10-12T01:00:00Z", "cpu_usage": [0, 12.5],
     "ram_usage": 1024, "ram_usage_percent": 50, "uptime": 0}, "online",
    datetime(2026, 10, 13, tzinfo=timezone.utc))
result.update(source_request_ids={"ci": "n1", "agent": "n2", "monitoring": "n3"},
              current_url="https://fixture.test/items/1")
observation = extract_observations(tool, {"ci_name": "fixture-ci"}, result)[0]
observation["observation_id"] = "obs-1"
spec = build_job_spec(load_and_validate_manifest(), "uc-front-009", "lab", {"exact_ci_name": "fixture-ci"})
requirement = spec["case"]["requirement"]
case = {"observations": [observation], "evidence": [{"type": tool, "evidence_id": "ev-1",
         "observation_ids": ["obs-1"], "usable_for_verdict": True}]}
check = {"check_id": "planned-005", "status": "blocked", "title": "fixture metrics"}
def evaluate(candidate, target=check):
    return evaluate_contract(candidate, requirement, target, "https://fixture.test")[0]
verified = evaluate(case)
assert verified["status"] == "passed"
assert verified["actual"]["monitoring_metrics"]["cpu_usage_raw"] == [0, 12.5]
assert verified["actual"]["freshness"]["monitoring_fresh"] is False
for changes in (
    {"cpu_usage_raw": []}, {"cpu_usage_raw": [None]}, {"cpu_usage_raw": [True]},
    {"cpu_usage_raw": [-1]}, {"cpu_usage_raw": [float("nan")]}, {"cpu_usage_raw": [0] * 129},
    {"ram_usage_raw": None}, {"ram_usage_raw": -1}, {"ram_usage_raw": float("inf")},
    {"ram_usage_percent": 101}, {"ram_usage_percent": "50"}, {"ram_usage_percent": True},
    {"uptime_seconds": -1}, {"uptime_seconds": None},
):
    candidate = deepcopy(case)
    candidate["observations"][0]["data"].update(changes)
    assert evaluate(candidate)["status"] == "blocked", changes
    identity = {"check_id": "planned-001", "status": "blocked"}
    assert evaluate(candidate, identity)["status"] == "passed"
for changes in ({"monitoring_ci_id": "wrong"}, {"source_request_ids": {"ci": "n1", "agent": "n2"}}):
    candidate = deepcopy(case)
    candidate["observations"][0]["data"].update(changes)
    assert evaluate(candidate)["status"] == "blocked"
candidate = deepcopy(case)
newer = deepcopy(observation)
newer["observation_id"] = "obs-newer"
newer["data"]["ram_usage_percent"] = None
candidate["observations"].append(newer)
candidate["evidence"].append({"type": tool, "evidence_id": "ev-newer",
    "observation_ids": ["obs-newer"], "usable_for_verdict": True})
assert evaluate(candidate)["status"] == "blocked"
print("agent numeric sample reporting: PASS (fixtures only)")
