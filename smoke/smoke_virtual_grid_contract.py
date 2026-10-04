from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<div role="grid" aria-rowcount="100" aria-colcount="3"><div role="row" aria-rowindex="20"><div role="gridcell" aria-colindex="2">Online</div></div></div>')
 r=s.inspect_virtual_grid_contract_semantic();assert r["virtual_grid_audit"]["virtual_grid_contract_passed"] is True,r
 s.page.set_content('<div role="grid" aria-rowcount="10"><div role="row" aria-rowindex="11"></div></div>');bad=s.inspect_virtual_grid_contract_semantic();assert bad["virtual_grid_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_virtual_grid_contract_semantic",{})=="observe"
finally:s.close()
print("virtual grid contract smoke: PASS")
