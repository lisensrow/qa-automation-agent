import uqa


job_id = "smoke-job"
compatible_case = "compatible-case"
incompatible_case = "incompatible-case"
messages = [{"role": "user", "content": "Enable the test option."}]
original_execute_tool = uqa.execute_tool
original_get_job = uqa.get_job
original_policy_decision = uqa.managed_action_policy_decision


def fake_execute_tool(name, arguments):
    if name == "browser_probe_capabilities":
        incompatible = arguments.get("smoke_incompatible") is True
        return {
            "compatibility_status": (
                "incompatible" if incompatible else "compatible"
            ),
            "capability_gaps": (
                ["canvas_only_ui"] if incompatible else []
            ),
            "contract_fingerprint": (
                "bad-fingerprint" if incompatible else "good-fingerprint"
            ),
            "executed": True,
        }
    return {"status": "ok", "executed": True}


try:
    uqa.execute_tool = fake_execute_tool
    uqa.get_job = lambda _job_id: {
        "request": "Enable the test option."
    }
    uqa.managed_action_policy_decision = (
        lambda *args, **kwargs: {
            "allow": True,
            "status": "confirmed",
        }
    )

    compatible_key = (job_id, compatible_case)
    uqa._MANAGED_BROWSER_OPENED_CASES.add(compatible_key)

    required = uqa.execute_tool_with_policy(
        "browser_set_checked_semantic",
        {"name": "Test option", "checked": True},
        messages,
        action_policy="confirm_mutations",
        job_id=job_id,
        case_id=compatible_case,
        require_compatibility_probe=True,
    )
    assert required.get("error") == (
        "managed_compatibility_probe_required"
    ), required
    assert required.get("executed") is False, required

    probe = uqa.execute_tool_with_policy(
        "browser_probe_capabilities",
        {},
        messages,
        action_policy="confirm_mutations",
        job_id=job_id,
        case_id=compatible_case,
        require_compatibility_probe=True,
    )
    assert probe.get("compatibility_status") == "compatible", probe

    allowed = uqa.execute_tool_with_policy(
        "browser_set_checked_semantic",
        {"name": "Test option", "checked": True},
        messages,
        action_policy="confirm_mutations",
        job_id=job_id,
        case_id=compatible_case,
        require_compatibility_probe=True,
    )
    assert allowed.get("status") == "ok", allowed
    assert allowed.get("executed") is True, allowed

    incompatible_key = (job_id, incompatible_case)
    uqa._MANAGED_BROWSER_OPENED_CASES.add(incompatible_key)
    incompatible_probe = uqa.execute_tool_with_policy(
        "browser_probe_capabilities",
        {"smoke_incompatible": True},
        messages,
        action_policy="confirm_mutations",
        job_id=job_id,
        case_id=incompatible_case,
        require_compatibility_probe=True,
    )
    assert incompatible_probe.get("compatibility_status") == (
        "incompatible"
    ), incompatible_probe

    blocked = uqa.execute_tool_with_policy(
        "browser_set_checked_semantic",
        {"name": "Test option", "checked": True},
        messages,
        action_policy="confirm_mutations",
        job_id=job_id,
        case_id=incompatible_case,
        require_compatibility_probe=True,
    )
    assert blocked.get("error") == "managed_frontend_incompatible", blocked
    assert blocked.get("capability_gaps") == ["canvas_only_ui"], blocked
    assert blocked.get("executed") is False, blocked

    cleanup_style = uqa.execute_tool_with_policy(
        "browser_set_checked_semantic",
        {"name": "Test option", "checked": False},
        messages,
        action_policy="confirm_mutations",
    )
    assert cleanup_style.get("status") == "ok", cleanup_style
finally:
    uqa.execute_tool = original_execute_tool
    uqa.get_job = original_get_job
    uqa.managed_action_policy_decision = original_policy_decision
    uqa._MANAGED_BROWSER_OPENED_CASES.discard(
        (job_id, compatible_case)
    )
    uqa._MANAGED_BROWSER_OPENED_CASES.discard(
        (job_id, incompatible_case)
    )
    uqa._COMPATIBILITY_PREFLIGHT_BY_CASE.pop(
        (job_id, compatible_case),
        None,
    )
    uqa._COMPATIBILITY_PREFLIGHT_BY_CASE.pop(
        (job_id, incompatible_case),
        None,
    )

print("compatibility guard smoke: PASS")
