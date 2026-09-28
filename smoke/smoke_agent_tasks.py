from types import SimpleNamespace

from tools.agent_tasks import (
    summarize_agent_tasks, summarize_agent_task_full,
    summarize_periodic_progress,
)
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
verified_summary = summarize_agent_task_full(
    ci, task_page, "task-1", full,
    expected_text="command-output", expected_error_code=0,
)
assert verified_summary["execution_result_verified"] is True
assert verified_summary["assertion_passed"] is True
assert verified_summary["text_assertion_matched"] is True
assert "command-output" not in str(verified_summary)
failed_summary = summarize_agent_task_full(
    ci, task_page, "task-1", full, expected_text="not present",
)
assert failed_summary["execution_result_verified"] is False
assert failed_summary["assertion_passed"] is False
assert failed_summary["reason"] == "task_result_assertion_failed"
periodic_task = {
    **summary["matched_tasks"][0], "period_seconds": 10, "enabled": 1,
}
baseline, snapshot = summarize_periodic_progress(
    periodic_task, full_summary,
)
assert baseline["periodic_verification_status"] == "baseline_recorded"
assert baseline["periodic_execution_verified"] is False
unchanged, _ = summarize_periodic_progress(
    periodic_task, full_summary, snapshot,
)
assert unchanged["periodic_verification_status"] == "awaiting_next_execution"
older_full = {
    **full_summary, "processed_at": "2026-09-17T09:59:59Z",
}
older, preserved_snapshot = summarize_periodic_progress(
    periodic_task, older_full, snapshot,
)
assert older["periodic_execution_verified"] is False
assert preserved_snapshot == snapshot
next_full = {
    **full_summary, "processed_at": "2026-09-17T10:00:10Z",
}
periodic_verified, _ = summarize_periodic_progress(
    periodic_task, next_full, snapshot,
)
assert periodic_verified["periodic_execution_verified"] is True
assert periodic_verified["observed_interval_seconds"] == 10
periodic_result = {**next_full, **periodic_verified}
periodic_observation = extract_observations(
    "browser_inspect_agent_task_result_semantic",
    {"ci_name": "test-linux", "task_id": "task-1",
     "verify_periodic": True},
    periodic_result,
)[0]
periodic_observation["observation_id"] = "obs-task-periodic"
periodic_job = {"job_type": "regression", "test_cases": [{
    "case_id": "case-1",
    "evidence": [{
        "evidence_id": "ev-task-periodic",
        "type": "browser_inspect_agent_task_result_semantic",
        "observation_ids": ["obs-task-periodic"],
        "usable_for_verdict": True,
    }],
    "observations": [periodic_observation],
}]}
original_get_job = uqa.get_job
try:
    uqa.get_job = lambda job_id: periodic_job
    verified, errors = uqa.verify_structured_check_evidence(
        "job-1", "case-1",
        [{"title": "Periodic", "status": "blocked",
          "evidence": ["ev-task-periodic"]}],
    )
    assert not errors, errors
    assert verified[0]["status"] == "passed", verified[0]
    assert verified[0]["reason"] == (
        "UQA CORE: two_distinct_periodic_executions_observed"
    )
finally:
    uqa.get_job = original_get_job
disabled_periodic, _ = summarize_periodic_progress(
    {**periodic_task, "enabled": 0}, full_summary,
)
assert disabled_periodic["reason"] == "task_not_enabled_periodic"
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
verified_observation = extract_observations(
    "browser_inspect_agent_task_result_semantic",
    {"ci_name": "test-linux", "task_id": "task-1"}, verified_summary,
)[0]
verified_observation["observation_id"] = "obs-task-verified"
verified_job = {"job_type": "regression", "test_cases": [{
    "case_id": "case-1",
    "evidence": [{
        "evidence_id": "ev-task-verified",
        "type": "browser_inspect_agent_task_result_semantic",
        "observation_ids": ["obs-task-verified"],
        "usable_for_verdict": True,
    }],
    "observations": [verified_observation],
}]}
original_get_job = uqa.get_job
try:
    uqa.get_job = lambda job_id: verified_job
    verified, errors = uqa.verify_structured_check_evidence(
        "job-1", "case-1",
        [{"title": "Result", "status": "blocked",
          "evidence": ["ev-task-verified"]}],
    )
    assert not errors, errors
    assert verified[0]["status"] == "passed", verified[0]
    assert verified[0]["reason"] == "UQA CORE: task_result_assertion_passed"
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
        verified_evidence = uqa.record_tool_evidence(
            "job-1", "case-1", "browser_inspect_agent_task_result_semantic",
            {"ci_name": "test-linux", "task_id": "task-1"}, verified_summary,
        )
        assert verified_evidence["usable_for_verdict"] is True
    finally:
        uqa.add_evidence = original_add_evidence
finally:
    session.close()

original_get_job = uqa.get_job
original_execute_tool = uqa.execute_tool
try:
    uqa.get_job = lambda job_id: {
        "request": "Проверь, что результат содержит READY и код 0."
    }
    uqa.execute_tool = lambda name, arguments: {"executed": False, "safe": True}
    denied = uqa.execute_tool_with_policy(
        "browser_inspect_agent_task_result_semantic",
        {"ci_name": "test-linux", "task_id": "task-1",
         "expected_text": "secret guess"},
        [], action_policy="confirm_mutations", job_id="job-1", case_id="case-1",
    )
    assert denied["error"] == "expected_text_not_user_authored", denied
    denied_code = uqa.execute_tool_with_policy(
        "browser_inspect_agent_task_result_semantic",
        {"ci_name": "test-linux", "task_id": "task-1",
         "expected_text": "READY", "expected_error_code": 2},
        [], action_policy="confirm_mutations", job_id="job-1", case_id="case-1",
    )
    assert denied_code["error"] == "expected_error_code_not_user_authored"
    allowed = uqa.execute_tool_with_policy(
        "browser_inspect_agent_task_result_semantic",
        {"ci_name": "test-linux", "task_id": "task-1",
         "expected_text": "READY", "expected_error_code": 0},
        [], action_policy="confirm_mutations", job_id="job-1", case_id="case-1",
    )
    assert allowed["safe"] is True, allowed
    periodic_denied = uqa.execute_tool_with_policy(
        "browser_inspect_agent_task_result_semantic",
        {"ci_name": "test-linux", "task_id": "task-1",
         "verify_periodic": True},
        [], action_policy="confirm_mutations", job_id="job-1", case_id="case-1",
    )
    assert periodic_denied["error"] == "periodic_verification_not_user_authored"
    uqa.get_job = lambda job_id: {
        "request": "Проверь два запуска periodic задачи."
    }
    periodic_allowed = uqa.execute_tool_with_policy(
        "browser_inspect_agent_task_result_semantic",
        {"ci_name": "test-linux", "task_id": "task-1",
         "verify_periodic": True},
        [], action_policy="confirm_mutations", job_id="job-1", case_id="case-1",
    )
    assert periodic_allowed["safe"] is True
    assert uqa._request_explicitly_names_error_code(
        "Версия 2026.09, ожидается код ошибки -1.", -1,
    )
    assert not uqa._request_explicitly_names_error_code(
        "Версия 2026.09 без ожидаемого кода.", 0,
    )
finally:
    uqa.get_job = original_get_job
    uqa.execute_tool = original_execute_tool

managed_task_id = "11111111-1111-4111-8111-111111111111"


class FakeBody:
    def inner_text(self):
        return "test-linux Agent Tasks"


class FakePage:
    url = "https://stand/cmdb/test-linux"

    def locator(self, selector):
        assert selector == "body"
        return FakeBody()


class ManagedRequest:
    def __init__(self):
        self.created_payload = None
        self.enabled = True
        self.marker = None

    def post(self, url, data, timeout):
        assert url == "https://stand/api/v1/agents/agent-1/tasks"
        assert data["name"] == "executeCommand"
        assert data["additional_params"]["programm"] == "/usr/bin/printf"
        self.created_payload = data
        self.marker = data["additional_params"]["arguments"][0]
        return SimpleNamespace(
            status=201,
            json=lambda: {
                "id": managed_task_id, "agent_id": "agent-1",
                "name": "executeCommand", "enabled": 1,
            },
        )

    def get(self, url, timeout):
        if url.endswith("/full"):
            payload = {
                "id": managed_task_id, "agent_id": "agent-1",
                "name": "executeCommand", "status": "success",
                "result": {
                    "result": "success",
                    "data": {
                        "stdout": self.marker,
                        "stderr": "",
                        "errorlevel": "0",
                    },
                    "processed_at": "2026-09-27T20:00:00Z",
                },
            }
        else:
            payload = {
                "id": managed_task_id, "agent_id": "agent-1",
                "name": "executeCommand", "enabled": int(self.enabled),
            }
        return SimpleNamespace(status=200, json=lambda: payload)

    def put(self, url, data, timeout):
        assert url.endswith("/" + managed_task_id)
        assert data == {"enabled": 0}
        self.enabled = False
        return SimpleNamespace(status=200, json=lambda: {"enabled": 0})


managed_session = object.__new__(BrowserSession)
managed_session._ensure_started = lambda: None
managed_session.page = FakePage()
managed_session.context = SimpleNamespace(request=ManagedRequest())
managed_session.network_details = {
    "ci": {
        "request": SimpleNamespace(method="GET", url="https://stand/api/v1/cis/ci-1"),
        "response": FakeResponse(ci),
    },
    "tasks": {
        "request": SimpleNamespace(
            method="GET", url="https://stand/api/v1/agents/agent-1/tasks"
        ),
        "response": FakeResponse({"total": 0, "items": []}),
    },
}
managed_session._managed_agent_tasks = {}
managed_session._agent_task_result_snapshots = {}
# A large agent task history is paginated in the UI. Creation needs only the
# exact observed CI/agent collection; cleanup still requires the exact task UUID.
managed_session.network_details["tasks"]["response"] = FakeResponse(
    {"total": 664, "items": []}
)
assert managed_session.create_managed_agent_task_semantic(
    "test-linux", "arbitrary-command",
)["error"] == "managed_task_fixture_not_allowed"
created = managed_session.create_managed_agent_task_semantic(
    "test-linux", "posix_printf_marker_v1",
)
assert created["task_id"] == managed_task_id, created
assert created["mutation_executed"] is True
assert "UQA_EXEC_OK_" not in str(created)
managed_task = {
    "id": managed_task_id, "agent_id": "agent-1", "name": "executeCommand",
    "enabled": 1, "period": None, "status": "success",
    "last_processed_at": "2026-09-27T20:00:00Z",
}
managed_session.network_details["tasks"]["response"] = FakeResponse(
    {"total": 1, "items": [managed_task]}
)
verified_managed = managed_session.inspect_managed_agent_task_result_semantic(
    "test-linux", managed_task_id,
)
assert verified_managed["managed_fixture_verified"] is True, verified_managed
assert "UQA_EXEC_OK_" not in str(verified_managed)
# Crash recovery may happen after the task has moved off the current page.
# Ledger UUID + direct GET identity remain authoritative.
managed_session.network_details["tasks"]["response"] = FakeResponse(
    {"total": 665, "items": []}
)
disabled = managed_session.disable_agent_task_semantic(
    "test-linux", managed_task_id,
)
assert disabled["post_disable_verified"] is True, disabled
assert disabled["mutation_executed"] is True
assert uqa.classify_tool_action(
    "browser_create_managed_agent_task_semantic", {},
) == "write"
assert uqa.classify_tool_action(
    "browser_inspect_managed_agent_task_result_semantic", {},
) == "observe"
assert uqa.classify_tool_action(
    "browser_disable_agent_task_semantic", {},
) == "destructive"
assert all(any(
    item["function"]["name"] == tool_name for item in TOOLS
) for tool_name in {
    "browser_create_managed_agent_task_semantic",
    "browser_inspect_managed_agent_task_result_semantic",
    "browser_disable_agent_task_semantic",
})
resource = {
    "external_id": managed_task_id,
    "metadata": {
        "cleanup_contract": "agent_task_disable_v1",
        "ci_name": "test-linux",
    },
}
assert uqa._cleanup_exact_rest_target({}, resource) == {
    "tool": "browser_disable_agent_task_semantic",
    "arguments": {"ci_name": "test-linux", "task_id": managed_task_id},
}
assert uqa._cleanup_browser_verification_succeeded(
    "browser_disable_agent_task_semantic", disabled,
)

original_execute_tool = uqa.execute_tool
original_add_resource = uqa.add_test_resource
try:
    uqa.execute_tool = lambda name, arguments: {
        **created, "ci_name": "test-linux", "agent_id": "agent-1",
    }
    captured_resource = {}

    def fake_add_resource(job_id, **kwargs):
        captured_resource.update({"job_id": job_id, **kwargs})
        return {"resource_id": "res-managed-task"}

    uqa.add_test_resource = fake_add_resource
    registered = uqa.execute_tool_with_policy(
        "browser_create_managed_agent_task_semantic",
        {"ci_name": "test-linux", "fixture_id": "posix_printf_marker_v1"},
        [], action_policy="legacy", job_id="job-1", case_id="case-1",
    )
    assert registered["resource_registered"] is True, registered
    assert registered["resource_id"] == "res-managed-task"
    assert captured_resource["resource_type"] == "agent_task"
    assert captured_resource["external_id"] == managed_task_id
    assert captured_resource["metadata"]["cleanup_contract"] == (
        "agent_task_disable_v1"
    )
finally:
    uqa.execute_tool = original_execute_tool
    uqa.add_test_resource = original_add_resource

print("agent tasks smoke: PASS")
