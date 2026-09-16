from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from tools.agent_plugins import summarize_plugin_audit
from tools.browser import BrowserSession
from tools.registry import TOOLS
from uqa import classify_tool_action


now = datetime.now(timezone.utc)
ci = {"id": "ci-1", "name": "test-ci", "agent_id": "agent-1"}
audit = {
    "agent_id": "agent-1", "last_audit_at": now.isoformat(),
    "detail": [{
        "plugin_name": "ExamplePlugin", "plugin_version": "1.0",
        "load_status": True, "file_name": "example.bin",
        "load_error": "never-expose-secret",
    }],
}
good = summarize_plugin_audit(
    ci, audit, "ExamplePlugin", "1.0", observed_at=now,
)
assert good["observation_result"] == "PASS", good
assert "never-expose-secret" not in str(good)
assert summarize_plugin_audit(
    ci, {**audit, "last_audit_at": (now - timedelta(days=2)).isoformat()},
    "ExamplePlugin", "1.0", observed_at=now,
)["reason"] == "plugin_audit_stale"
assert summarize_plugin_audit(
    ci, {**audit, "agent_id": "wrong"}, "ExamplePlugin", "1.0", observed_at=now,
)["reason"] == "plugin_audit_missing_or_agent_mismatch"
assert summarize_plugin_audit(
    ci, audit, "Missing", "1.0", observed_at=now,
)["reason"] == "plugin_absent_or_ambiguous"
assert summarize_plugin_audit(
    ci, audit, "ExamplePlugin", "2.0", observed_at=now,
)["reason"] == "plugin_version_mismatch"
assert summarize_plugin_audit(
    ci, {**audit, "detail": [{**audit["detail"][0], "load_status": False}]},
    "ExamplePlugin", "1.0", observed_at=now,
)["reason"] == "plugin_not_confirmed_loaded"


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


session = BrowserSession()
try:
    session._ensure_started()
    session.page.set_content("<div>test-ci</div><div>Agent</div><div>Plugins</div>")
    session.network_details["ci-request"] = {
        "request": SimpleNamespace(method="GET", url="https://stand/api/v1/cis/ci-1"),
        "response": FakeResponse(ci),
    }
    session.network_details["plugin-request"] = {
        "request": SimpleNamespace(
            method="GET", url="https://stand/api/v1/agents/agent-1/plugin"
        ),
        "response": FakeResponse(audit),
    }
    observed = session.inspect_agent_plugins_semantic(
        "test-ci", "ExamplePlugin", "1.0",
    )
    assert observed["observation_result"] == "PASS", observed
    assert observed["source_request_ids"]["plugin_audit"] == "plugin-request"
    assert classify_tool_action("browser_inspect_agent_plugins_semantic", {}) == "observe"
    assert any(
        tool["function"]["name"] == "browser_inspect_agent_plugins_semantic"
        for tool in TOOLS
    )
finally:
    session.close()

print("agent plugin audit smoke: PASS")
