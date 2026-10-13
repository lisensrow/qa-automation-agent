from copy import deepcopy
import uqa
from run_uconnect_manual_frontend_benchmark import build_job_spec, load_and_validate_manifest

document = load_and_validate_manifest()
for source, bindings, tool, expected in (
    ("uc-front-009", {"exact_ci_name": "fixture-ci"},
     "browser_inspect_agent_telemetry_semantic", {"ci_name": "fixture-ci"}),
    ("uc-front-010", {"exact_ci_name": "fixture-ci", "plugin_name": "FixturePlugin"},
     "browser_inspect_agent_plugins_semantic", {"ci_name": "fixture-ci", "plugin_name": "FixturePlugin"}),
):
    spec = build_job_spec(document, source, "lab", bindings)
    job = {"test_cases": [{"case_id": "case-fixture", "requirement": spec["case"]["requirement"]}]}
    resolved = uqa.prepared_observation_contract(job, "case-fixture")
    assert resolved == {"tool": tool, "arguments": expected}
    assert "expected_version" not in resolved["arguments"]
    for change in (
        lambda r: r.update(action_profile="write_resource"),
        lambda r: r["required_observation"].update(tool="browser_click_semantic"),
        lambda r: r["required_observation"].update(tool="unknown"),
        lambda r: r["bindings"].pop("exact_ci_name"),
        lambda r: r["required_observation"]["arguments"].update(ci_name={"literal": "other"}),
        lambda r: r["required_observation"]["arguments"].update(unknown={"binding": "exact_ci_name"}),
    ):
        candidate = deepcopy(job)
        change(candidate["test_cases"][0]["requirement"])
        try:
            uqa.prepared_observation_contract(candidate, "case-fixture")
            raise AssertionError("unsafe observation contract accepted")
        except ValueError:
            pass

assert uqa.prepared_observation_contract({"test_cases": []}, "legacy") is None

saved_contract, saved_ask, saved_execute = (
    uqa.prepared_observation_contract, uqa.ask_ollama, uqa.execute_tool_with_policy)
calls = []
seen = []
tool = "browser_inspect_agent_plugins_semantic"
locked = {"ci_name": "fixture-ci", "plugin_name": "FixturePlugin"}
content = uqa.UQA_CHECKS_START + '\n{"checks":[{"check_id":"planned-001","title":"fixture","status":"blocked","reason":"fixture unavailable"}]}\n' + uqa.UQA_CHECKS_END
responses = iter([
    {"message": {"content": "Already done"}},
    {"message": {"tool_calls": [{"function": {"name": tool, "arguments": {
        "ci_name": "wrong", "plugin_name": "wrong", "expected_version": "invented"}}}]}},
    {"message": {"content": "No structured output"}},
    {"message": {"content": content}},
])

def fake_ask(messages, tools):
    assert tool in {t["function"]["name"] for t in tools}
    seen[:] = messages
    return next(responses)

def fake_execute(name, arguments, messages, **kwargs):
    calls.append((name, dict(arguments)))
    return {"error": "fixture_unavailable"}

try:
    uqa.prepared_observation_contract = lambda *args: {"tool": tool, "arguments": locked}
    uqa.ask_ollama = fake_ask
    uqa.execute_tool_with_policy = fake_execute
    uqa.run_turn([])
    assert calls == [(tool, locked)]
    assert any("REQUIRED READ-ONLY OBSERVATION" in m.get("content", "") for m in seen)
    assert any("STRUCTURED RESULT REQUIRED" in m.get("content", "") for m in seen)
    assert next(responses, None) is None
finally:
    uqa.prepared_observation_contract, uqa.ask_ollama, uqa.execute_tool_with_policy = (
        saved_contract, saved_ask, saved_execute)
print("prepared read-only observation contract smoke: PASS")
