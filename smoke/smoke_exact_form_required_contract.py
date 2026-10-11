from tools.browser import BrowserSession
from uqa import _core_observation_call_key, classify_tool_action


session = BrowserSession()
try:
    session._ensure_started()
    session.page.set_content("""
      <form aria-label="Profile">
        <label id="email-label">Email</label>
        <p id="email-help">Work address</p>
        <input name="email" type="email" required
               aria-labelledby="email-label" aria-describedby="email-help">
        <label>Age <input name="age" type="number"></label>
        <button type="submit">Save</button>
      </form>
    """)
    passed = session.verify_exact_form_required_contract_semantic(
        "Profile", ["Email"],
    )
    audit = passed["form_required_audit"]
    assert audit["form_required_contract_passed"] is True, passed
    assert audit["required_field_count"] == 1, passed
    assert audit["no_submit_request_sent"] is True, passed
    assert passed["mutation_executed"] is False, passed
    assert passed["observation_result"] == "PASS", passed
    assert classify_tool_action(
        "browser_verify_exact_form_required_contract_semantic", {},
    ) == "observe"
    assert _core_observation_call_key(
        "browser_verify_exact_form_required_contract_semantic",
        {"form": " Profile "},
    ) == ("browser_verify_exact_form_required_contract_semantic", "profile")

    mismatch = session.verify_exact_form_required_contract_semantic(
        "Profile", ["Email", "Name"],
    )
    assert mismatch["error"] == "form_required_contract_failed", mismatch
    assert mismatch["observation_result"] == "BLOCKED", mismatch
    assert mismatch["form_required_audit"][
        "expected_required_fields_match"
    ] is False, mismatch

    session.page.set_content("""
      <form aria-label="Broken">
        <input required aria-labelledby="missing-label"
               aria-describedby="missing-help">
      </form>
    """)
    broken = session.verify_exact_form_required_contract_semantic("Broken")
    assert broken["error"] == "form_required_contract_failed", broken
    assert broken["form_required_audit"][
        "broken_label_reference_count"
    ] == 1, broken
    assert broken["form_required_audit"][
        "broken_description_reference_count"
    ] == 1, broken

    duplicate = session.verify_exact_form_required_contract_semantic(
        "Broken", ["Name", "Name"],
    )
    assert duplicate["error"] == "expected_required_fields_duplicate", duplicate
finally:
    session.close()

print("exact form required contract smoke: PASS")
