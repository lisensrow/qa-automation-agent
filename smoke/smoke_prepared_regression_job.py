import copy

import uqa
import tools.browser as browser


def prepared_job(status="created", case_status="pending"):
    return {
        "job_id": "job-prepared",
        "job_type": "regression",
        "status": status,
        "stand": "uconnect",
        "request": "Inspect exact CI.\n\nBound inputs:\n- exact_ci_name: test-linux",
        "test_cases": [
            {
                "case_id": "case-prepared",
                "title": "Read exact agent telemetry",
                "expected": "freshness is explicit",
                "status": case_status,
                "requirement": {
                    "source": "uconnect_manual_frontend_corpus",
                    "execution_status": "ready",
                    "action_profile": "read_only",
                    "bindings": {"exact_ci_name": "test-linux"},
                },
                "planned_checks": ["freshness is explicit"],
            }
        ],
    }


assert uqa._parse_run_job_command("/run-job job-123") == "job-123"
assert uqa._parse_run_job_command("/run-job") == ""
assert uqa._parse_run_job_command("run-job job-123") is None

saved = {
    "get_job": uqa.get_job,
    "lock": uqa._lock_regression_plan_stand,
    "get_stand": uqa.get_stand,
    "prepare": uqa.prepare_locked_requirements,
    "set_job": uqa.set_job_status,
    "update_case": uqa.update_test_case,
    "run_turn": uqa.run_turn,
    "case_artifacts": uqa.export_regression_case_artifacts,
    "cleanup": uqa.run_cleanup_job,
    "reconcile": uqa.reconcile_resource_lifecycle_checks,
    "recompute": uqa.recompute_job_status,
    "summary": uqa.set_job_summary,
    "job_artifacts": uqa.export_regression_job_artifacts,
    "reset": browser.reset_case_context,
}

store = prepared_job()
captured = {}


def fake_get_job(job_id):
    assert job_id == "job-prepared"
    return copy.deepcopy(store)


def fake_set_job_status(job_id, status):
    store["status"] = status


def fake_update_case(job_id, case_id, status=None, **kwargs):
    store["test_cases"][0]["status"] = status


def fake_run_turn(messages, **kwargs):
    captured["messages"] = messages
    captured["kwargs"] = kwargs
    store["test_cases"][0]["status"] = "passed"


try:
    uqa.get_job = fake_get_job
    uqa.get_stand = lambda stand: {
        "stand_id": stand,
        "name": stand,
        "web_url": "https://uconnect.test",
        "ssh_host": "uconnect.test",
        "ssh_username": "tester",
        "has_ssh_credentials": True,
    }
    uqa._lock_regression_plan_stand = lambda plan, stand: plan
    uqa.prepare_locked_requirements = lambda plan: captured.update(plan=plan)
    uqa.set_job_status = fake_set_job_status
    uqa.update_test_case = fake_update_case
    uqa.run_turn = fake_run_turn
    uqa.export_regression_case_artifacts = lambda *args: {}
    uqa.run_cleanup_job = lambda job_id: {"status": "not_required"}
    uqa.reconcile_resource_lifecycle_checks = lambda job_id: set()
    uqa.recompute_job_status = lambda job_id: "passed"
    uqa.set_job_summary = lambda job_id, summary: captured.update(summary=summary)
    uqa.export_regression_job_artifacts = lambda job_id: {}
    browser.reset_case_context = lambda: None

    result = uqa.run_prepared_regression_job("job-prepared")
    assert result == "job-prepared"
    assert captured["kwargs"] == {
        "job_id": "job-prepared",
        "case_id": "case-prepared",
        "action_policy": "confirm_mutations",
    }
    assert captured["plan"][0]["checks"] == ["freshness is explicit"]
    assert "test-linux" in captured["messages"][1]["content"]
finally:
    uqa.get_job = saved["get_job"]
    uqa.get_stand = saved["get_stand"]
    uqa._lock_regression_plan_stand = saved["lock"]
    uqa.prepare_locked_requirements = saved["prepare"]
    uqa.set_job_status = saved["set_job"]
    uqa.update_test_case = saved["update_case"]
    uqa.run_turn = saved["run_turn"]
    uqa.export_regression_case_artifacts = saved["case_artifacts"]
    uqa.run_cleanup_job = saved["cleanup"]
    uqa.reconcile_resource_lifecycle_checks = saved["reconcile"]
    uqa.recompute_job_status = saved["recompute"]
    uqa.set_job_summary = saved["summary"]
    uqa.export_regression_job_artifacts = saved["job_artifacts"]
    browser.reset_case_context = saved["reset"]

for invalid in (
    prepared_job(status="passed"),
    prepared_job(case_status="running"),
):
    try:
        uqa.get_job = lambda job_id, value=invalid: copy.deepcopy(value)
        uqa.get_stand = lambda stand: {
            "stand_id": stand,
            "name": stand,
            "web_url": "https://uconnect.test",
            "ssh_host": "uconnect.test",
            "ssh_username": "tester",
            "has_ssh_credentials": True,
        }
        uqa._lock_regression_plan_stand = lambda plan, stand: plan
        uqa._prepared_regression_case("job-prepared")
        raise AssertionError("invalid prepared Job unexpectedly accepted")
    except ValueError:
        pass
    finally:
        uqa.get_job = saved["get_job"]
        uqa.get_stand = saved["get_stand"]
        uqa._lock_regression_plan_stand = saved["lock"]

print("prepared regression Job smoke: PASS")
