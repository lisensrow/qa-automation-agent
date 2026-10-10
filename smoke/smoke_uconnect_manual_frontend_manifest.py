from run_uconnect_manual_frontend_benchmark import (
    load_and_validate_manifest,
    summarize,
)


document = load_and_validate_manifest()
summary = summarize(document)
assert summary["total"] == 16
assert len(summary["categories"]) == 6
assert summary["execution_statuses"] == {
    "blocked_external": 2,
    "candidate": 4,
    "ready": 10,
}
assert summary["action_profiles"] == {
    "read_only": 8,
    "write_resource": 3,
    "write_ui_state": 5,
}
assert all(
    case["execution_status"] != "ready"
    or case["action_profile"] == "read_only"
    or case.get("policy_required") is True
    for case in document["cases"]
)
print("uconnect manual frontend manifest smoke: PASS (6 categories, 16 cases)")
