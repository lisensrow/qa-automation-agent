from tools.browser import BrowserSession
from tools.registry import TOOLS
from uqa import classify_tool_action


session = BrowserSession()
surface = {
    "document_ready_state": "complete",
    "canvas_count": 1,
    "video_count": 0,
    "canvases": [
        {
            "width": 640,
            "height": 480,
            "display_width": 640,
            "display_height": 480,
            "visible": True,
        }
    ],
    "videos": [],
    "surface_present": True,
    "surface_ready": True,
}


session.inspect_iframe_semantic = lambda *args: {
    "iframe_status": "verified",
    "iframe_name": "Remote console",
    "iframe_url": "https://console.test/vnc/one",
    "iframe_expected_url_prefix": "https://console.test/vnc/",
    "iframe_origin_matches": True,
    "iframe_url_matches": True,
    "iframe_surface": surface,
}
session.observe_iframe_surface_change_semantic = lambda *args: {
    "surface_change_status": "verified",
    "surface_changed": True,
    "surface_change_matches": True,
    "surface_before_sha256": "a" * 64,
    "surface_after_sha256": "b" * 64,
    "mutation_executed": False,
}

verified = session.verify_iframe_surface_readiness_semantic(
    "Remote console",
    "https://console.test/vnc/",
    True,
    wait_ms=500,
)
assert verified["iframe_readiness_status"] == "verified", verified
assert verified["iframe_surface_dimensions_ready"] is True, verified
assert verified["surface_change_status"] == "verified", verified
assert verified["input_action_sent"] is False, verified
assert verified["mutation_executed"] is False, verified

called = {"change": False}
session.inspect_iframe_semantic = lambda *args: {
    "iframe_status": "verified",
    "iframe_surface": {
        "surface_present": True,
        "surface_ready": False,
        "canvases": [],
        "videos": [],
    },
}
session.observe_iframe_surface_change_semantic = lambda *args: called.update(
    change=True
)
blocked = session.verify_iframe_surface_readiness_semantic(
    "Remote console",
    "https://console.test/vnc/",
    True,
)
assert blocked["iframe_readiness_status"] == "not_ready", blocked
assert blocked["error"] == "iframe_surface_not_ready", blocked
assert called["change"] is False

tool_name = "browser_verify_iframe_surface_readiness_semantic"
assert classify_tool_action(tool_name, {}) == "observe"
assert any(item["function"]["name"] == tool_name for item in TOOLS)

print("iframe surface readiness smoke: PASS")
