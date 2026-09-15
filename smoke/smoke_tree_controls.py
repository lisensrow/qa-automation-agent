from tools.browser import BrowserSession
from uqa import classify_tool_action


session = BrowserSession()
try:
    session._ensure_started()
    session.page.set_content(
        """
        <div role="tree" aria-label="Categories">
          <div id="systems" role="treeitem" aria-label="Systems" aria-level="1"
               aria-expanded="false" tabindex="0">
            Systems
            <div id="children" role="group" hidden>
              <div role="treeitem" aria-label="Servers" aria-level="2">Servers</div>
            </div>
          </div>
          <div role="treeitem" aria-label="Standalone" aria-level="1">Standalone</div>
        </div>
        <button onclick="window.saveClicks += 1">Save</button>
        <script>
          window.saveClicks = 0;
          const systems = document.getElementById('systems');
          systems.addEventListener('keydown', event => {
            if (event.target !== systems) return;
            if (event.key === 'ArrowRight') {
              systems.setAttribute('aria-expanded', 'true');
              document.getElementById('children').hidden = false;
            }
            if (event.key === 'ArrowLeft') {
              systems.setAttribute('aria-expanded', 'false');
              document.getElementById('children').hidden = true;
            }
          });
        </script>
        """
    )

    before = session.inspect_tree_semantic("Categories")
    assert before.get("visible_tree_item_count") == 2, before
    assert before["tree_items"][0]["expanded"] is False, before

    opened = session.set_tree_item_expanded(
        "Systems", True, tree="Categories"
    )
    assert opened.get("tree_expand_status") == "applied", opened
    assert opened.get("expanded") is True, opened
    assert len(opened.get("tree_after") or []) == 3, opened

    opened_again = session.set_tree_item_expanded(
        "Systems", True, tree="Categories"
    )
    assert opened_again.get("tree_expand_status") == "already_satisfied", opened_again

    leaf = session.set_tree_item_expanded(
        "Servers", True, tree="Categories"
    )
    assert leaf.get("error") == "tree_item_not_expandable", leaf

    closed = session.set_tree_item_expanded(
        "Systems", False, tree="Categories"
    )
    assert closed.get("tree_expand_status") == "applied", closed
    assert closed.get("expanded") is False, closed
    assert len(closed.get("tree_after") or []) == 2, closed
    assert session.page.evaluate("window.saveClicks") == 0

    assert classify_tool_action("browser_inspect_tree_semantic", {}) == "observe"
    assert classify_tool_action("browser_set_tree_item_expanded", {}) == "interact"
finally:
    session.close()

print("tree controls smoke: PASS")
