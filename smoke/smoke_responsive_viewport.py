from tools.browser import BrowserSession
from tools.registry import TOOLS
from uqa import classify_tool_action


session = BrowserSession()
try:
    session._ensure_started()
    session.page.set_content(
        """
        <style>
          body { margin: 0; }
          #mobile-menu { display: none; }
          #overflow-probe { width: auto; height: 1px; }
          @media (max-width: 600px) {
            #desktop-nav { display: none; }
            #mobile-menu { display: block; }
            #overflow-probe { width: 900px; }
          }
        </style>
        <button id="desktop-nav">Desktop navigation</button>
        <button id="mobile-menu">Mobile menu</button>
        <div id="overflow-probe"></div>
        """
    )

    mobile = session.set_viewport_semantic("mobile")
    assert mobile.get("viewport_status") == "applied", mobile
    assert mobile.get("viewport") == {"width": 390, "height": 844}, mobile
    assert mobile["responsive_metrics"]["horizontal_overflow"] is True, mobile
    assert session.page.locator("#mobile-menu").is_visible()
    assert not session.page.locator("#desktop-nav").is_visible()

    tablet = session.set_viewport_semantic("tablet")
    assert tablet.get("viewport") == {"width": 768, "height": 1024}, tablet
    assert tablet["responsive_metrics"]["horizontal_overflow"] is False, tablet

    desktop = session.set_viewport_semantic("desktop")
    assert desktop.get("viewport") == {"width": 1440, "height": 900}, desktop
    assert desktop["responsive_metrics"]["horizontal_overflow"] is False, (
        desktop
    )
    assert session.page.locator("#desktop-nav").is_visible()
    assert not session.page.locator("#mobile-menu").is_visible()

    unsupported = session.set_viewport_semantic("wide-custom")
    assert unsupported.get("error") == "unsupported_viewport_profile", (
        unsupported
    )
    assert unsupported.get("supported_profiles") == [
        "mobile", "tablet", "desktop"
    ]

    assert classify_tool_action(
        "browser_set_viewport_semantic", {"profile": "mobile"}
    ) == "interact"
    viewport_tool = next(
        item["function"]
        for item in TOOLS
        if item["function"]["name"] == "browser_set_viewport_semantic"
    )
    assert viewport_tool["parameters"]["properties"]["profile"]["enum"] == [
        "mobile", "tablet", "desktop"
    ]
finally:
    session.close()

print("responsive viewport smoke: PASS")
