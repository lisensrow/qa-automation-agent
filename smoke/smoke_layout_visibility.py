from tools.browser import BrowserSession


session = BrowserSession()
try:
    session._ensure_started()
    session.page.set_content(
        """
        <style>
          #target {
            position: absolute;
            left: 20px;
            top: 20px;
            width: 120px;
            height: 48px;
          }
          #target:focus {
            outline: 3px solid rgb(255, 0, 0);
            background-color: rgb(1, 2, 3);
          }
          #cover {
            display: none;
            position: absolute;
            left: 10px;
            top: 10px;
            width: 180px;
            height: 100px;
            z-index: 10;
            background: white;
          }
        </style>
        <button id="target">Save layout</button>
        <div id="cover"></div>
        """
    )

    clear = session.inspect_semantic("Save layout", role="button")
    assert clear["visible"] is True, clear
    assert clear["geometry_actionable"] is True, clear
    assert clear["layout"]["fully_in_viewport"] is True, clear
    assert clear["layout"]["visible_area_ratio"] == 1, clear
    assert clear["layout"]["touch_target_44px"] is True, clear

    session.page.locator("#target").focus()
    focused = session.inspect_semantic("Save layout", role="button")
    assert focused["element"]["visual_state"]["focused"] is True, focused
    assert focused["element"]["computed_style"]["outline_width"] == "3px", focused
    assert (
        focused["element"]["computed_style"]["background_color"]
        == "rgb(1, 2, 3)"
    ), focused

    session.page.locator("#cover").evaluate("el => el.style.display = 'block'")
    covered = session.inspect_semantic("Save layout", role="button")
    assert covered["visible"] is True, covered
    assert covered["layout"]["center_unobscured"] is False, covered
    assert covered["geometry_actionable"] is False, covered
finally:
    session.close()

print("layout visibility smoke: PASS")
