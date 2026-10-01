from tools.browser import BrowserSession
from tools.registry import TOOLS
from uqa import classify_tool_action


session = BrowserSession()
try:
    session._ensure_started()
    session.page.set_content(
        """
        <style>
          #tip { display: none; position: absolute; left: 20px; top: 60px; }
          #help:hover + #tip { display: block; }
        </style>
        <button id="help" aria-describedby="tip">Help</button>
        <div id="tip" role="tooltip">Open documentation</div>
        """
    )
    result = session.inspect_hover_tooltip_semantic(
        "Help", "button", "Open documentation",
    )
    assert result["tooltip_status"] == "verified", result
    assert result["tooltip_opened"] is True, result
    assert result["tooltip_closed_after_hover"] is True, result
    assert result["tooltip_text"] == "Open documentation", result

    missing = session.inspect_hover_tooltip_semantic(
        "Help", "button", "Wrong tooltip",
    )
    assert missing["tooltip_status"] == "mismatch", missing
    assert classify_tool_action(
        "browser_inspect_hover_tooltip_semantic", {}
    ) == "interact"
    assert any(
        item["function"]["name"] == "browser_inspect_hover_tooltip_semantic"
        for item in TOOLS
    )
finally:
    session.close()

print("hover tooltip smoke: PASS")
