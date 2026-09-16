from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from tools.agent_observability import summarize_agent_observation
from tools.browser import BrowserSession
from tools.registry import TOOLS
from uqa import classify_tool_action


now = datetime.now(timezone.utc)
ci = {
    "id": "ci-123",
    "name": "test-linux-ci",
    "agent_id": "agent-123",
    "endpoint_status": "online",
    "detail": {"os": {
        "name": "linux", "version": "1", "architecture": "x86_64"
    }},
}
agent = {
    "id": "agent-123", "status": "online", "version": "1.2.3",
    "last_online_at": (now - timedelta(minutes=20)).isoformat(),
    "public_key": "never-return-this",
}
monitoring = {
    "uid": "ci-123", "created_at": now.isoformat(),
    "cpu_usage": [2.5], "ram_usage": 1000,
    "ram_usage_percent": 50.0, "uptime": 100.0,
}
good = summarize_agent_observation(
    "test-linux-ci", ci, agent, monitoring, "online", now,
)
assert good["observation_result"] == "PASS", good
assert good["monitoring_fresh"] is True, good
assert good["architecture"] == "x86_64", good
assert "never-return-this" not in str(good)
assert summarize_agent_observation(
    "test-linux-ci", ci, agent, monitoring, "offline", now,
)["reason"] == "status_sources_disagree"
assert summarize_agent_observation(
    "test-linux-ci", {**ci, "endpoint_status": "offline"},
    {**agent, "status": "offline"}, monitoring, "offline", now,
)["reason"] == "agent_offline"
assert summarize_agent_observation(
    "test-linux-ci", ci, agent,
    {**monitoring, "created_at": (now - timedelta(minutes=10)).isoformat()},
    "online", now,
)["reason"] == "monitoring_missing_or_stale"
assert summarize_agent_observation(
    "test-linux-ci", ci, agent, {**monitoring, "uid": "wrong"},
    "online", now,
)["reason"] == "monitoring_ci_mismatch"


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


session = BrowserSession()
try:
    session._ensure_started()
    session.page.set_content(
        "<div><div>test-linux-ci</div><div>online</div></div>"
    )
    for request_id, payload in [
        ("n-ci", ci), ("n-agent", agent), ("n-monitoring", monitoring),
    ]:
        session.network_details[request_id] = {
            "request": SimpleNamespace(method="GET"),
            "response": FakeResponse(payload),
        }
    observed = session.inspect_agent_telemetry_semantic("test-linux-ci")
    assert observed["observation_result"] == "PASS", observed
    assert observed["statuses"]["ui"] == "online", observed
    assert observed["source_request_ids"] == {
        "ci": "n-ci", "agent": "n-agent", "monitoring": "n-monitoring",
    }, observed
    assert classify_tool_action(
        "browser_inspect_agent_telemetry_semantic", {}
    ) == "observe"
    assert any(
        item["function"]["name"] == "browser_inspect_agent_telemetry_semantic"
        for item in TOOLS
    )
finally:
    session.close()

print("agent observability smoke: PASS")
