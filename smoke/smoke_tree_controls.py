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
          <div id="standalone" role="treeitem" aria-label="Standalone"
               aria-level="1" aria-selected="false" tabindex="0">Standalone</div>
          <div id="checkable" role="treeitem" aria-label="Checkable"
               aria-level="1" aria-checked="false" tabindex="0">Checkable</div>
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
          for (const id of ['standalone', 'checkable']) {
            document.getElementById(id).addEventListener('keydown', event => {
              if (event.key !== ' ') return;
              const attr = event.currentTarget.hasAttribute('aria-selected')
                ? 'aria-selected' : 'aria-checked';
              const next = event.currentTarget.getAttribute(attr) !== 'true';
              event.currentTarget.setAttribute(attr, String(next));
            });
          }
        </script>
        """
    )

    before = session.inspect_tree_semantic("Categories")
    assert before.get("visible_tree_item_count") == 3, before
    assert before["tree_items"][0]["expanded"] is False, before

    opened = session.set_tree_item_expanded(
        "Systems", True, tree="Categories"
    )
    assert opened.get("tree_expand_status") == "applied", opened
    assert opened.get("expanded") is True, opened
    assert len(opened.get("tree_after") or []) == 4, opened

    opened_again = session.set_tree_item_expanded(
        "Systems", True, tree="Categories"
    )
    assert opened_again.get("tree_expand_status") == "already_satisfied", opened_again

    leaf = session.set_tree_item_expanded(
        "Servers", True, tree="Categories"
    )
    assert leaf.get("error") == "tree_item_not_expandable", leaf

    selected = session.set_tree_item_selected(
        "Standalone", True, tree="Categories"
    )
    assert selected.get("tree_selection_status") == "applied", selected
    assert selected.get("tree_selection_attribute") == "aria-selected", selected
    selected_again = session.set_tree_item_selected(
        "Standalone", True, tree="Categories"
    )
    assert selected_again.get("tree_selection_status") == "already_satisfied", selected_again
    deselected = session.set_tree_item_selected(
        "Standalone", False, tree="Categories"
    )
    assert deselected.get("selected") is False, deselected
    checked = session.set_tree_item_selected(
        "Checkable", True, tree="Categories"
    )
    assert checked.get("tree_selection_attribute") == "aria-checked", checked
    missing_contract = session.set_tree_item_selected(
        "Servers", True, tree="Categories"
    )
    assert missing_contract.get("error") == "tree_item_selection_contract_missing", missing_contract

    closed = session.set_tree_item_expanded(
        "Systems", False, tree="Categories"
    )
    assert closed.get("tree_expand_status") == "applied", closed
    assert closed.get("expanded") is False, closed
    assert len(closed.get("tree_after") or []) == 3, closed
    assert session.page.evaluate("window.saveClicks") == 0

    assert classify_tool_action("browser_inspect_tree_semantic", {}) == "observe"
    assert classify_tool_action("browser_set_tree_item_expanded", {}) == "interact"
    assert classify_tool_action("browser_set_tree_item_selected", {}) == "write"
finally:
    session.close()

print("tree controls smoke: PASS")
