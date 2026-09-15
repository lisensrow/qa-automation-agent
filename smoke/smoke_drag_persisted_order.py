from tools.browser import BrowserSession
from uqa import classify_tool_action


session = BrowserSession()


def ordered_list_html(order):
    items = "".join(
        f'<li role="listitem" draggable="true" id="{name.lower()}">{name}</li>'
        for name in order
    )
    return f"""
    <html><body>
      <ul id="priority" role="list" aria-label="Priority order">{items}</ul>
      <script>
        let dragged = null;
        document.querySelectorAll('#priority li').forEach(item => {{
          item.addEventListener('dragstart', event => {{
            dragged = item;
            event.dataTransfer.setData('text/plain', item.id);
          }});
          item.addEventListener('dragover', event => event.preventDefault());
          item.addEventListener('drop', event => {{
            event.preventDefault();
            if (dragged && dragged !== item) {{
              item.parentElement.insertBefore(dragged, item);
            }}
          }});
        }});
      </script>
    </body></html>
    """


try:
    session._ensure_started()
    session.page.set_content(ordered_list_html(["Alpha", "Beta", "Gamma"]))

    before = session.inspect_order_semantic(
        "Priority order",
        ["Alpha", "Beta", "Gamma"],
        role="list",
    )
    assert before.get("order_status") == "matched", before
    assert before.get("mutation_executed") is False, before

    dragged = session.drag_semantic(
        "Gamma",
        "Alpha",
        source_role="listitem",
        target_role="listitem",
        order_container="Priority order",
        expected_order=["Gamma", "Alpha", "Beta"],
        container_role="list",
    )
    assert dragged.get("drag_status") == "performed", dragged
    assert dragged.get("order_status") == "matched", dragged
    assert dragged.get("order_before") == ["Alpha", "Beta", "Gamma"], dragged
    assert dragged.get("order_after") == ["Gamma", "Alpha", "Beta"], dragged

    # Simulate a separately loaded persisted page. The read-only inspector is
    # the evidence primitive; the drag result alone only proves current UI.
    session.page.set_content(ordered_list_html(["Gamma", "Alpha", "Beta"]))
    persisted = session.inspect_order_semantic(
        "Priority order",
        ["Gamma", "Alpha", "Beta"],
        role="list",
    )
    assert persisted.get("order_status") == "matched", persisted

    mismatch = session.inspect_order_semantic(
        "Priority order",
        ["Alpha", "Beta", "Gamma"],
        role="list",
    )
    assert mismatch.get("order_status") == "mismatch", mismatch
    assert mismatch.get("order_mismatch", {}).get("index") == 0, mismatch

    assert classify_tool_action(
        "browser_inspect_order_semantic",
        {},
    ) == "observe"
    assert classify_tool_action(
        "browser_drag_semantic",
        {},
    ) == "write"
finally:
    session.close()

print("drag persisted-order smoke: PASS")
