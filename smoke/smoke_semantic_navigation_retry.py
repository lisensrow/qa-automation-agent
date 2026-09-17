import uqa


original_execute_tool = uqa.execute_tool
calls = []


def fake_execute_tool(name, arguments):
    calls.append((name, dict(arguments)))
    if arguments.get("role"):
        return {"error": "semantic_element_not_found", "executed": False}
    return {"click_status": "executed", "semantic_strategy": "text"}


try:
    uqa.execute_tool = fake_execute_tool
    request = [{"role": "user", "content": "Read-only inspect the Agent tab"}]
    result = uqa.execute_tool_with_policy(
        "browser_click_semantic",
        {"name": "Agent", "role": "tab", "container": "Agent", "exact": True},
        request, action_policy="confirm_mutations",
    )
    assert result["click_status"] == "executed", result
    assert result["semantic_hint_retry"]["retry_exact_name_only"] is True
    assert calls == [
        ("browser_click_semantic", {
            "name": "Agent", "role": "tab", "container": "Agent", "exact": True,
        }),
        ("browser_click_semantic", {"name": "Agent", "exact": True}),
    ], calls

    calls.clear()
    blocked = uqa.execute_tool_with_policy(
        "browser_click_semantic",
        {"name": "Agent", "role": "tab", "container": "Another row", "exact": True},
        request, action_policy="confirm_mutations",
    )
    assert blocked["error"] == "semantic_element_not_found", blocked
    assert len(calls) == 1, calls
finally:
    uqa.execute_tool = original_execute_tool

print("semantic navigation retry smoke: PASS")
