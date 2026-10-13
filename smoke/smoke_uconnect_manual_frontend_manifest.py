from run_uconnect_manual_frontend_benchmark import (
    build_job_spec, get_case, load_and_validate_manifest, materialize_job, parse_bindings, summarize,
)

document = load_and_validate_manifest()
summary = summarize(document)
assert summary["total"] == 17
assert len(summary["categories"]) == 6
assert summary["execution_statuses"] == {"blocked_external": 2, "candidate": 4, "ready": 11}
assert summary["action_profiles"] == {"read_only": 9, "write_resource": 3, "write_ui_state": 5}
assert all(c["execution_status"] != "candidate" or c.get("candidate_reason", "").strip() for c in document["cases"])
assert all(c["execution_status"] != "ready" or c["action_profile"] == "read_only"
           or c.get("policy_required") is True for c in document["cases"])
assert get_case(document, "uc-front-009")["category"] == "agent_ui"
assert parse_bindings(["exact_ci_name = test-linux"]) == {"exact_ci_name": "test-linux"}
spec = build_job_spec(document, "uc-front-009", "uconnect", {"exact_ci_name": "test-linux"})
assert spec["external_id"] == "uc-front-009" and spec["job_type"] == "regression"
assert spec["case"]["requirement"]["bindings"] == {"exact_ci_name": "test-linux"}
assert spec["case"]["requirement"]["stand"] == "uconnect"
assert spec["case"]["requirement"]["locked"] is True
assert spec["case"]["requirement"]["type"] == "frontend_contracts"
assert spec["case"]["planned_checks"] == get_case(document, "uc-front-009")["checks"]
assert "test-linux" in spec["request"]
captured = {}
def fake_create_job(request, **kwargs):
    captured["job"] = {"request": request, **kwargs}
    return {"job_id": "job-corpus-smoke"}
def fake_add_test_case(job_id, **kwargs):
    captured["case"] = {"job_id": job_id, **kwargs}
    return {"case_id": "case-corpus-smoke"}
materialized = materialize_job(spec, job_creator=fake_create_job, case_adder=fake_add_test_case)
assert materialized["job_id"] == "job-corpus-smoke" and materialized["case_id"] == "case-corpus-smoke"
assert captured["job"]["external_id"] == "uc-front-009" and captured["case"]["job_id"] == "job-corpus-smoke"
assert captured["case"]["planned_checks"] == spec["case"]["planned_checks"]
assert captured["case"]["requirement"]["action_profile"] == "read_only"
for case_id, expected_error in (("uc-front-013", "execution_not_ready:candidate"),
                                ("uc-front-011", "execution_not_ready:blocked_external")):
    try:
        build_job_spec(document, case_id, "uconnect", {})
        raise AssertionError(f"{case_id} unexpectedly materialized")
    except ValueError as exc:
        assert expected_error in str(exc)
try:
    build_job_spec(document, "uc-front-009", "uconnect", {})
    raise AssertionError("missing binding unexpectedly accepted")
except ValueError as exc:
    assert "bindings_missing:exact_ci_name" in str(exc)
try:
    parse_bindings(["exact_ci_name=test-linux", "exact_ci_name=test-win"])
    raise AssertionError("duplicate binding unexpectedly accepted")
except ValueError as exc:
    assert "binding_duplicate:exact_ci_name" in str(exc)
renderer = build_job_spec(document, "uc-front-017", "uconnect",
                          {"exact_ci_name": "test-linux", "requested_tab_names": '["Monitoring"]'})
assert renderer["case"]["requirement"]["action_profile"] == "read_only"
assert len(renderer["case"]["requirement"]["check_contracts"]) == 3
print("uconnect manual frontend manifest smoke: PASS (6 categories, 17 cases, deterministic Job spec)")
