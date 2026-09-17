"""Core must not confuse telemetry freshness with plugin-audit freshness."""

import uqa
from observation_extractor import extract_observations


telemetry = {
    "ci_name": "test-ubuntu",
    "statuses": {"ui": "online", "ci": "online", "agent": "online"},
    "monitoring_fresh": True,
    "monitoring_at": "2026-09-17T08:29:00Z",
    "observation_result": "PASS",
    "reason": None,
}
audit = {
    "ci_name": "test-ubuntu",
    "audit_fresh": False,
    "last_audit_at": "2026-09-01T00:00:00Z",
    "observation_result": "BLOCKED",
    "reason": "plugin_audit_stale",
}
telemetry_observation = extract_observations(
    "browser_inspect_agent_telemetry_semantic",
    {"ci_name": "test-ubuntu"}, telemetry,
)[0]
audit_observation = extract_observations(
    "browser_inspect_agent_plugins_semantic",
    {"ci_name": "test-ubuntu", "plugin_name": "VncServer",
     "expected_version": "1.3.6"}, audit,
)[0]
assert telemetry_observation["type"] == "agent_telemetry"
assert audit_observation["type"] == "agent_plugin_audit"
telemetry_observation["observation_id"] = "obs-telemetry"
audit_observation["observation_id"] = "obs-audit"
job = {
    "job_type": "regression",
    "test_cases": [{
        "case_id": "tc-1",
        "evidence": [
            {"evidence_id": "ev-telemetry",
             "type": "browser_inspect_agent_telemetry_semantic",
             "observation_ids": ["obs-telemetry"],
             "usable_for_verdict": True},
            {"evidence_id": "ev-audit",
             "type": "browser_inspect_agent_plugins_semantic",
             "observation_ids": ["obs-audit"],
             "usable_for_verdict": True},
        ],
        "observations": [telemetry_observation, audit_observation],
    }],
}
original_get_job = uqa.get_job
try:
    uqa.get_job = lambda job_id: job
    checks = [
        {"title": "Wrong telemetry claim", "status": "blocked",
         "actual": "Telemetry stale because last audit is old",
         "evidence": ["ev-telemetry"], "observations": ["obs-invented"]},
        {"title": "Plugin check", "status": "passed",
         "actual": "Installed", "evidence": ["ev-audit"]},
    ]
    verified, errors = uqa.verify_structured_check_evidence(
        "job-1", "tc-1", checks,
    )
    assert not errors, errors
    assert verified[0]["status"] == "passed", verified[0]
    assert "audit" not in verified[0]["actual"], verified[0]
    assert verified[0]["observations"] == ["obs-telemetry"]
    assert verified[1]["status"] == "blocked", verified[1]
    assert verified[1]["reason"] == "UQA CORE: plugin_audit_stale"
    assert verified[1]["observations"] == ["obs-audit"]
finally:
    uqa.get_job = original_get_job

print("agent check binding smoke: PASS")
