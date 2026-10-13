"""Pure fixtures: stale reporting is not fresh monitoring or a healthy agent."""
from copy import deepcopy
from datetime import datetime, timezone
import uqa
from observation_extractor import extract_observations
from tools.agent_observability import summarize_agent_observation
from tools.agent_plugins import summarize_plugin_audit
from frontend_check_contracts import evaluate_contract, render_contract_check_summary
from run_uconnect_manual_frontend_benchmark import build_job_spec, load_and_validate_manifest

now = datetime(2026, 10, 13, 12, tzinfo=timezone.utc)
ci = {"id": "ci-1", "name": "fixture-ci", "agent_id": "agent-1", "endpoint_status": "online"}
telemetry = summarize_agent_observation(ci["name"], ci,
    {"id": "agent-1", "status": "online", "version": "1"},
    {"uid": "ci-1", "created_at": "2026-10-12T01:00:00Z", "cpu_usage": [1],
     "ram_usage": 1024, "ram_usage_percent": 50, "uptime": 123}, "online", now)
plugins = summarize_plugin_audit(ci, {"agent_id": "agent-1", "last_audit_at": "2026-10-12T01:00:00Z",
    "detail": [{"plugin_name": "fixture-plugin", "plugin_version": "1.2", "load_status": True}]},
    "fixture-plugin", observed_at=now)
saved_job, saved_stand = uqa.get_job, uqa.get_stand
try:
    for case_id, tool, result, sources in (
        ("uc-front-009", "browser_inspect_agent_telemetry_semantic", telemetry,
         {"ci": "n1", "agent": "n2", "monitoring": "n3"}),
        ("uc-front-010", "browser_inspect_agent_plugins_semantic", plugins,
         {"ci": "n1", "plugin_audit": "n2"}),
    ):
        bindings = {"exact_ci_name": "fixture-ci"}
        if case_id == "uc-front-010":
            bindings["plugin_name"] = "fixture-plugin"
        spec = build_job_spec(load_and_validate_manifest(), case_id, "lab", bindings)
        requirement = spec["case"]["requirement"]
        result = dict(result, source_request_ids=sources, current_url="https://fixture.test/items/1")
        assert result["observation_result"] == "BLOCKED"
        observation = extract_observations(tool, {"ci_name": "fixture-ci", "plugin_name": "fixture-plugin"}, result)[0]
        observation["observation_id"] = "obs-1"
        case = {"case_id": "case-1", "requirement": requirement, "observations": [observation],
                "evidence": [{"evidence_id": "ev-1", "type": tool, "observation_ids": ["obs-1"],
                              "usable_for_verdict": True}]}
        checks = [{"check_id": key, "status": "blocked", "title": "fixture"}
                  for key in requirement["check_contracts"]]
        uqa.get_stand = lambda _: {"web_url": "https://fixture.test"}
        def verify(candidate):
            uqa.get_job = lambda _: {"job_type": "regression", "stand": "lab", "test_cases": [candidate]}
            return uqa.verify_structured_check_evidence("fixture-job", "case-1", checks)[0]
        verified = verify(case)
        assert all(check["status"] == "passed" for check in verified), verified
        fresh_field = "monitoring_fresh" if case_id == "uc-front-009" else "audit_fresh"
        assert all(check["actual"]["freshness"][fresh_field] is False for check in verified)
        from job_store import _normalize_checks
        persisted = _normalize_checks(verified)
        assert all(fresh_field in check["actual"] and "False" in check["actual"] for check in persisted)
        summary = render_contract_check_summary(verified)
        assert '"' + fresh_field + '": false' in summary and "does not prove freshness" in summary
        assert "fixture-plugin" not in summary  # only computed check facts, not request/prose
        # An explicitly required fresh sample still fails, despite reporting passing.
        fresh = deepcopy(requirement)
        fresh["check_contracts"]["planned-003"]["assertions"] = [
            {"field": fresh_field, "operator": "eq", "expected": True}]
        assert evaluate_contract(case, fresh, checks[2], "https://fixture.test")[0]["status"] == "failed"
        identity_field = "observed_agent_id" if case_id == "uc-front-009" else "audit_agent_id"
        for changes in ({identity_field: "wrong"}, {"ci_name": "wrong"}, {"ci_id": None},
                        {"source_request_ids": {}}, {"agent_id": None},
                        {"url": "https://other.test/items"}, {"url": "https://fixture.test:444/items"},
                        {"url": None}, {"url": "https://user:secret@fixture.test/items"}):
            candidate = deepcopy(case)
            candidate["observations"][0]["data"].update(changes)
            assert all(c["status"] == "blocked" for c in verify(candidate)), changes
        age = "monitoring_age_seconds" if case_id == "uc-front-009" else "audit_age_seconds"
        timestamp = "monitoring_at" if case_id == "uc-front-009" else "last_audit_at"
        for changes in ({age: float("nan")}, {age: float("inf")}, {age: True}, {age: -121},
                        {timestamp: "invalid"}, {timestamp: "2026-10-13T12:00:00"}):
            candidate = deepcopy(case)
            candidate["observations"][0]["data"].update(changes)
            assert verify(candidate)[2]["status"] == "blocked", changes
            assert verify(candidate)[0]["status"] == "passed"
        candidate = deepcopy(case)
        candidate["evidence"][0]["usable_for_verdict"] = False
        assert all(c["status"] == "blocked" for c in verify(candidate))
        if case_id == "uc-front-009":
            candidate = deepcopy(case)
            candidate["observations"][0]["data"].update(monitoring_ci_id="wrong")
            assert verify(candidate)[2]["status"] == "blocked"
            assert verify(candidate)[0]["status"] == "passed"
            candidate["observations"][0]["data"]["statuses"] = {"ui": "online", "ci": "offline", "agent": "offline"}
            assert verify(candidate)[1]["status"] == "passed"  # reporting, not agreement/health
        else:
            for matched in ([], [{"name": "wrong", "version": "1"}],
                            [{"name": "fixture-plugin", "version": None}],
                            [{"name": "fixture-plugin", "version": "1"}] * 2):
                candidate = deepcopy(case)
                candidate["observations"][0]["data"]["matched_plugins"] = matched
                assert verify(candidate)[1]["status"] == "blocked"
finally:
    uqa.get_job, uqa.get_stand = saved_job, saved_stand
print("agent independent fact contracts: PASS (fixtures only; no live writes)")
