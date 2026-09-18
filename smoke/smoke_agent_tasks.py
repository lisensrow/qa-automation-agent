from types import SimpleNamespace

from tools.agent_tasks import summarize_agent_tasks, summarize_agent_task_full
from tools.browser import BrowserSession
from tools.registry import TOOLS
from observation_extractor import extract_observations
import uqa


ci = {"id": "ci-1", "name": "test-linux", "agent_id": "agent-1"}
task_page = {"total": 1, "items": [{
    "id": "task-1", "agent_id": "agent-1", "name": "checkAlive",
    "enabled": True, "period": 60, "status": "Success",
    "last_processed_at": "2026-09-17T10:00:00Z",
    "additional_params": "never-expose-command-or-secret",
}]}
summary = summarize_agent_tasks(ci, task_page, "checkAlive")
assert summary["inspection_status"] == "observed", summary
assert summary["execution_result_verified"] is False
assert summarize_agent_tasks(ci, None)["reason"] == "task_list_get_not_observed"
missing_observation = extract_observations(
    "browser_inspect_agent_tasks_semantic",
    {"ci_name": "test-linux"},
    summarize_agent_tasks(ci, None),
)[0]
missing_observation["observation_id"] = "obs-task-list"
fake_job = {"job_type": "regression", "test_cases": [{
    "case_id": "case-1",
    "evidence": [{
        "evidence_id": "ev-task-list",
        "type": "browser_inspect_agent_tasks_semantic",
        "observation_ids": ["obs-task-list"],
        "usable_for_verdict": False,
    }],
    "observations": [missing_observation],
}]}
original_get_job = uqa.get_job
try:
    uqa.get_job = lambda job_id: fake_job
    verified, errors = uqa.verify_structured_check_evidence(
        "job-1", "case-1",
        [{"title": "Wrong claim", "status": "passed",
          "actual": "The agent has no tasks", "evidence": ["ev-task-list"]}],
    )
    assert not errors, errors
    assert verified[0]["status"] == "blocked", verified[0]
    assert verified[0]["reason"] == "UQA CORE: task_list_get_not_observed"
    assert "The agent has no tasks" not in verified[0]["actual"]
finally:
    uqa.get_job = original_get_job
assert summary["matched_tasks"][0]["period_seconds"] == 60
duplicate_page = {"total": 2, "items": [
    task_page["items"][0],
    {**task_page["items"][0], "id": "task-2", "status": "error"},
]}
assert summarize_agent_tasks(
    ci, duplicate_page, "checkAlive",
)["reason"] == "task_absent_or_ambiguous"
selected_by_id = summarize_agent_tasks(
    ci, duplicate_page, "checkAlive", "task-2",
)
assert selected_by_id["inspection_status"] == "observed"
assert selected_by_id["matched_tasks"][0]["task_id"] == "task-2"
assert selected_by_id["matched_tasks"][0]["status"] == "error"
assert summarize_agent_tasks(
    ci, duplicate_page, task_id="task-2",
)["matched_tasks"][0]["task_id"] == "task-2"
assert summarize_agent_tasks(
    ci, {"total": 3, "items": duplicate_page["items"]}, task_id="task-2",
)["reason"] == "task_list_incomplete"
full = {
    "id": "task-1", "agent_id": "agent-1", "name": "checkAlive",
    "status": "success",
    "additional_params": {"pwd": "never-expose-password"},
    "result": {
        "result": "never-expose-command-output",
        "processed_at": "2026-09-17T10:00:00Z",
        "error_code": 0, "error_msg": "never-expose-error-text",
    },
}
full_summary = summarize_agent_task_full(ci, task_page, "task-1", full)
assert full_summary["full_result_observed"] is True
assert full_summary["execution_result_verified"] is False
assert full_summary["result_present"] is True
assert full_summary["has_error_message"] is True
assert "never-expose" not in str(full_summary)
assert not {"text_excerpt", "screenshot", "additional_params", "result"} & set(full_summary)
assert summarize_agent_task_full(
    ci, task_page, "task-1", {**full, "agent_id": "other"},
)["reason"] == "task_full_identity_mismatch"
assert summarize_agent_task_full(
    ci, task_page, "task-1", {**full, "result": None},
)["reason"] == "task_result_not_available"
assert summarize_agent_task_full(
    ci, {"total": 2, "items": task_page["items"]}, "task-1", full,
)["reason"] == "task_list_incomplete"
assert summarize_agent_task_full(
    ci, {"items": task_page["items"]}, "task-1", full,
)["reason"] == "task_list_completeness_unconfirmed"
full_observation = extract_observations(
    "browser_inspect_agent_task_result_semantic",
    {"ci_name": "test-linux", "task_id": "task-1"}, full_summary,
)[0]
assert full_observation["type"] == "agent_task_result"
assert "never-expose" not in str(full_observation)
full_observation["observation_id"] = "obs-task-full"
full_job = {"job_type": "regression", "test_cases": [{
    "case_id": "case-1",
    "evidence": [{
        "evidence_id": "ev-task-full",
        "type": "browser_inspect_agent_task_result_semantic",
        "observation_ids": ["obs-task-full"],
        "usable_for_verdict": False,
    }],
    "observations": [full_observation],
}]}
original_get_job = uqa.get_job
try:
    uqa.get_job = lambda job_id: full_job
    verified, errors = uqa.verify_structured_check_evidence(
        "job-1", "case-1",
        [{"title": "Incorrect PASS", "status": "passed",
          "actual": "command succeeded", "evidence": ["ev-task-full"]}],
    )
    assert not errors, errors
    assert verified[0]["status"] == "blocked", verified[0]
    assert verified[0]["reason"] == "UQA CORE: task_result_metadata_only"
    assert "command succeeded" not in verified[0]["actual"]
finally:
    uqa.get_job = original_get_job
assert summarize_agent_tasks(
    ci, duplicate_page, "other", "task-2",
)["reason"] == "task_id_absent_or_ambiguous"
assert "never-expose-command-or-secret" not in str(summary)
overview = summarize_agent_tasks(ci, task_page)
assert overview["matched_tasks"] == []
assert overview["task_names"] == [{"name": "checkAlive", "count": 1}]
assert summarize_agent_tasks(
    ci, {**task_page, "items": [{**task_page["items"][0], "agent_id": "wrong"}]},
    "checkAlive",
)["reason"] == "task_agent_mismatch"
assert summarize_agent_tasks(
    ci, {"total": 2, "items": task_page["items"]}, "other",
)["reason"] == "task_list_incomplete"
assert extract_observations(
    "browser_inspect_agent_tasks_semantic", {"ci_name": "test-linux"}, summary,
)[0]["type"] == "agent_task_list"


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


session = BrowserSession()
try:
    session._ensure_started()
    session.page.set_content("<div>test-linux</div><div>Agent</div><div>Tasks</div>")
    assert session.inspect_agent_tasks_semantic(None)["error"] == "ci_name_required"
    assert session.inspect_agent_tasks_semantic(
        "test-linux", task_id=" ",
    )["error"] == "task_id_invalid"
    assert session.inspect_agent_task_result_semantic(
        "test-linux", "not-a-uuid",
    )["error"] == "task_id_invalid"
    session.network_details["ci-request"] = {
        "request": SimpleNamespace(method="GET", url="https://stand/api/v1/cis/ci-1"),
        "response": FakeResponse(ci),
    }
    session.network_details["task-request"] = {
        "request": SimpleNamespace(
            method="GET", url="https://stand/api/v1/agents/agent-1/tasks?limit=999"
        ),
        "response": FakeResponse(task_page),
    }
    observed = session.inspect_agent_tasks_semantic("test-linux", "checkAlive")
    assert observed["inspection_status"] == "observed", observed
    assert observed["source_request_ids"]["tasks"] == "task-request"
    repeated = session.inspect_agent_tasks_semantic("test-linux", "checkAlive")
    assert repeated["error"] == "identical_task_inspection_no_new_data"
    assert repeated["executed"] is False
    missing = summarize_agent_tasks(ci, task_page, "missing")
    assert missing["available_task_names"] == ["checkAlive"], missing
    assert uqa.classify_tool_action(
        "browser_inspect_agent_tasks_semantic", {},
    ) == "observe"
    assert uqa.classify_tool_action(
        "browser_inspect_agent_task_result_semantic", {},
    ) == "observe"
    assert any(
        item["function"]["name"] == "browser_inspect_agent_tasks_semantic"
        for item in TOOLS
    )
    assert any(
        item["function"]["name"] == "browser_inspect_agent_task_result_semantic"
        for item in TOOLS
    )
    original_add_evidence = uqa.add_evidence
    try:
        uqa.add_evidence = lambda *args, **kwargs: kwargs
        evidence = uqa.record_tool_evidence(
            "job-1", "case-1", "browser_inspect_agent_tasks_semantic",
            {"ci_name": "test-linux"}, observed,
        )
        assert evidence["usable_for_verdict"] is False, evidence
        assert evidence["eligibility_reason"] == "task_list_metadata_only"
        full_evidence = uqa.record_tool_evidence(
            "job-1", "case-1", "browser_inspect_agent_task_result_semantic",
            {"ci_name": "test-linux", "task_id": "task-1"}, full_summary,
        )
        assert full_evidence["usable_for_verdict"] is False
        assert full_evidence["eligibility_reason"] == "task_result_metadata_only"
    finally:
        uqa.add_evidence = original_add_evidence
finally:
    session.close()

print("agent tasks smoke: PASS")
