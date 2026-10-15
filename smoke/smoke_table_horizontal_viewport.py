"""Isolated browser viewport fixtures, not autonomous product acceptance."""
from tools.browser import BrowserSession
from tools.registry import TOOLS
from uqa import classify_tool_action

assert classify_tool_action('browser_scroll_table_horizontal_semantic',{'edge':'end'})=='interact'
assert any(t['function']['name']=='browser_scroll_table_horizontal_semantic' for t in TOOLS)
s=BrowserSession()
try:
    s._ensure_started()
    def content(extra='',direction='ltr',wide=True):
        s.page.set_content('''<html><body><div style="width:240px;overflow-x:auto;direction:''' + direction + '''">
          <table aria-label="Inventory" style="width:''' + ('1200' if wide else '100') + '''px"><thead><tr><th>Name</th><th>OS</th></tr></thead>
          <tbody><tr><td>fixture</td><td>windows</td></tr></tbody></table></div>''' + extra + '''</body></html>''')
    content()
    r=s.scroll_table_horizontal_semantic('end','Inventory')
    assert r['scroll_status']=='reached' and r['viewport_after']['left']>0,r
    assert not r['business_pass'] and not r['all_columns_observed'] and not r['mutation_executed']
    assert s.scroll_table_horizontal_semantic('end','Inventory')['scroll_status']=='reached'
    r=s.scroll_table_horizontal_semantic('start','Inventory')
    assert r['scroll_status']=='reached' and r['viewport_after']['left']==0
    assert s.scroll_table_horizontal_semantic('end','Not a table').get('error')=='table_not_found'
    assert s.scroll_table_horizontal_semantic('delete').get('executed') is False
    assert s.scroll_table_horizontal_semantic('end',exact='false').get('executed') is False
    content(direction='rtl')
    assert s.scroll_table_horizontal_semantic('end').get('error')=='unsupported_table_scroll_direction'
    content(wide=False)
    assert s.scroll_table_horizontal_semantic('end').get('error')=='table_horizontal_viewport_not_found'
    content('<table><tr><td>another</td></tr></table>')
    assert s.scroll_table_horizontal_semantic('end').get('error')
    content()
    assert s.scroll_table_horizontal_semantic('end')['table_resolution']=='unique_visible'
    assert s.page.locator('tbody td').all_text_contents()==['fixture','windows']
finally:
    s.close()
print('table_horizontal_viewport fixtures PASS; autonomous_acceptance=false')
