"""Real browser fixtures for exact tree identity, not a UConnect acceptance test."""
from playwright.sync_api import sync_playwright
from tools.browser import BrowserSession
import uqa

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    session = BrowserSession.__new__(BrowserSession)
    session.page = page
    session._ensure_started = lambda: None
    session._reset_diagnostics = lambda: None
    session._begin_action_execution = lambda: None
    session._capture_state = lambda action: {'action': action, 'fixture': True}
    session._finish_action_execution = lambda result: result
    page.set_content('''<ul role="tree" aria-label="Objects"><li role="treeitem">Existing object</li></ul>
      <ul role="tree"><li role="treeitem" aria-label="Common" aria-expanded="false" tabindex="0"
       onkeydown="if(event.key==='ArrowRight')this.setAttribute('aria-expanded','true');
       if(event.key==='ArrowLeft')this.setAttribute('aria-expanded','false')">Common</li>
       <li role="treeitem" hidden>Common</li></ul>''')
    assert session.inspect_tree_semantic()['error'] == 'ambiguous_tree'
    state = session.inspect_tree_semantic(item='Common')
    assert state['visible_tree_item_count'] == 1 and state['tree_anchor_item'] == 'Common'
    assert state['tree_items'][0]['expanded'] is False
    assert session.set_tree_item_expanded('Common', True)['tree_expand_status'] == 'applied'
    assert session.set_tree_item_expanded('Common', True)['tree_expand_status'] == 'already_satisfied'
    assert session.set_tree_item_expanded('Common', False)['tree_expand_status'] == 'applied'
    assert session.inspect_tree_semantic(tree='Objects', item='Common')['error'] == 'tree_anchor_not_found'
    assert session.inspect_tree_semantic(tree='Missing', item='Common')['error'] == 'tree_anchor_not_found'
    assert session.inspect_tree_semantic(item='Common', exact=False)['error'] == 'exact_bounded_tree_anchor_required'
    assert session.inspect_tree_semantic(item='x'*161)['error'] == 'exact_bounded_tree_anchor_required'
    page.set_content('<ul role="tree"><li role="treeitem">Duplicate</li><li role="treeitem">Duplicate</li></ul>')
    assert session.inspect_tree_semantic(item='Duplicate')['error'] == 'ambiguous_tree_anchor'
    page.set_content('<ul role="tree"><li role="treeitem">Same</li></ul><ul role="tree"><li role="treeitem">Same</li></ul>')
    assert session.set_tree_item_expanded('Same', True)['error'] == 'ambiguous_tree_anchor'
    page.set_content('''<ul role="tree" aria-label="Outer"><li role="treeitem">Parent
       <ul role="tree" aria-label="Inner"><li role="treeitem" aria-label="Leaf">Leaf</li></ul></li></ul>''')
    root, error = session._resolve_tree(item='Leaf')
    assert error is None and root.get_attribute('aria-label') == 'Inner'
    assert session.inspect_tree_semantic(tree='Outer', item='Leaf')['error'] == 'tree_anchor_not_found'
    page.set_content('<ul role="tree"><li role="treeitem">Only</li></ul>'*51)
    assert session.inspect_tree_semantic(item='Only')['error'] == 'tree_scope_limit_exceeded'
    browser.close()

assert uqa.classify_tool_action('browser_inspect_tree_semantic', {'item':'Common'}) == 'observe'
print('PASS exact tree anchor: unique visible item, no named fallback, duplicates/nested/hidden/limits, keyboard postcondition; not business PASS')
