from tools.browser import BrowserSession
from uqa import classify_tool_action, tool_policy_check


session = BrowserSession()

try:
    session._ensure_started()
    session.page.set_content(
        """
        <html><body>
          <ul>
            <li
              id="alpha"
              draggable="true"
              ondragstart="event.dataTransfer.setData('text/plain', 'alpha')"
            >Alpha</li>
          </ul>
          <div
            id="target"
            role="region"
            aria-label="Drop zone"
            style="width:200px;height:80px;border:1px solid black"
            ondragover="event.preventDefault()"
            ondrop="
              event.preventDefault();
              this.appendChild(
                document.getElementById(
                  event.dataTransfer.getData('text/plain')
                )
              );
            "
          >Drop zone</div>

          <div
            id="panel"
            role="region"
            aria-label="Details panel"
            style="width:200px;height:100px;border:2px solid blue"
          >Details panel</div>
          <script>
            const panel = document.getElementById('panel');
            let resizing = false;
            let startX = 0;
            let startWidth = 0;
            panel.addEventListener('mousedown', event => {
              const rect = panel.getBoundingClientRect();
              if (event.clientX >= rect.right - 5) {
                resizing = true;
                startX = event.clientX;
                startWidth = rect.width;
                event.preventDefault();
              }
            });
            document.addEventListener('mousemove', event => {
              if (resizing) {
                panel.style.width =
                  Math.max(40, startWidth + event.clientX - startX) + 'px';
              }
            });
            document.addEventListener('mouseup', () => {
              resizing = false;
            });
          </script>
        </body></html>
        """
    )

    dragged = session.drag_semantic(
        "Alpha",
        "Drop zone",
        source_role="listitem",
        target_role="region",
    )
    assert dragged.get("drag_status") == "performed", dragged
    assert dragged.get("mutation_executed") is True, dragged
    assert session.page.locator("#target #alpha").count() == 1

    resized = session.resize_semantic(
        "Details panel",
        delta_x=80,
        edge="right",
        role="region",
    )
    assert resized.get("resize_status") == "resized", resized
    assert resized["target_box_after"]["width"] > (
        resized["target_box_before"]["width"] + 60
    ), resized

    for tool_name, arguments in (
        (
            "browser_drag_semantic",
            {"source": "Alpha", "target": "Drop zone"},
        ),
        (
            "browser_resize_semantic",
            {"target": "Details panel", "delta_x": 80},
        ),
    ):
        assert classify_tool_action(tool_name, arguments) == "write"
        blocked = tool_policy_check(
            tool_name,
            arguments,
            [{"role": "user", "content": "Только проверь, не изменяй"}],
        )
        assert blocked.get("status") == "blocked_by_policy", blocked

    invalid = session.resize_semantic(
        "Details panel",
        delta_x=1001,
        role="region",
    )
    assert invalid.get("error") == "resize_delta_out_of_range", invalid
    assert invalid.get("executed") is False, invalid
finally:
    session.close()

print("drag and resize smoke: PASS")
