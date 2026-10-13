"""No inference-format success is required for fully locked machine checks."""
from copy import deepcopy
import json
import uqa
from frontend_check_contracts import evaluate_contract
from run_uconnect_manual_frontend_benchmark import build_job_spec, load_and_validate_manifest

spec = build_job_spec(load_and_validate_manifest(), "uc-front-010", "lab",
                      {"exact_ci_name": "fixture-ci", "plugin_name": "fixture-plugin"})
case = dict(spec["case"], case_id="case-1", observations=[], evidence=[])
job = {"job_type": "regression", "test_cases": [case]}
templates = uqa.prepared_contract_check_templates(job, "case-1")
assert len(templates) == 3 and all(c["status"] == "blocked" for c in templates)
assert all(evaluate_contract(case, case["requirement"], c, None)[0]["status"] == "blocked" for c in templates)
for mutation in (
    lambda j: j.update(job_type="manual"),
    lambda j: j["test_cases"][0]["requirement"].update(action_profile="write_resource"),
    lambda j: j["test_cases"][0]["requirement"].update(execution_status="candidate"),
    lambda j: j["test_cases"][0]["requirement"]["check_contracts"].pop("planned-002"),
    lambda j: j["test_cases"][0]["requirement"]["check_contracts"]["planned-001"].update(tool="browser_inspect_table_row"),
):
    candidate = deepcopy(job)
    mutation(candidate)
    try:
        uqa.prepared_contract_check_templates(candidate, "case-1")
    except ValueError:
        pass
    else:
        raise AssertionError("unsafe or incomplete templates accepted")
assert uqa.prepared_contract_check_templates({}, None) is None
saved = {key: getattr(uqa, key) for key in (
    "prepared_observation_contract", "prepared_contract_check_templates", "ask_ollama", "execute_tool_with_policy")}
calls = []
tool = "browser_inspect_agent_plugins_semantic"
def ask(messages, tools):
    calls.append("inference")
    assert calls.count("inference") == 1, "Core requested model output after complete observer"
    return {"message": {"tool_calls": [{"function": {"name": tool,
            "arguments": {"ci_name": "wrong", "plugin_name": "wrong"}}}]}}
def execute(name, arguments, messages, **kwargs):
    calls.append((name, arguments))
    return {"error": "fixture_observation_unavailable"}
try:
    uqa.prepared_observation_contract = lambda *args: {
        "tool": tool, "arguments": {"ci_name": "fixture-ci", "plugin_name": "fixture-plugin"}}
    uqa.prepared_contract_check_templates = lambda *args: templates
    uqa.ask_ollama, uqa.execute_tool_with_policy = ask, execute
    messages = []
    uqa.run_turn(messages)  # No Job writes; the verifier's missing-evidence refusal is tested above.
    content = next(m["content"] for m in reversed(messages) if m["role"] == "assistant" and m.get("content"))
    checks, _, error = uqa.extract_structured_checks(content)
    assert error is None and len(checks) == 3 and all(c["status"] == "blocked" for c in checks)
    assert calls == ["inference", (tool, {"ci_name": "fixture-ci", "plugin_name": "fixture-plugin"})]
finally:
    for key, value in saved.items():
        setattr(uqa, key, value)
print("prepared Core-owned contract results: PASS (no live actions)")
