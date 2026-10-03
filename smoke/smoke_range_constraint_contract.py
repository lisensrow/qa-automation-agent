from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<input type="number" min="1" max="10" step="1">')
 r=s.inspect_range_constraint_contract_semantic();assert r["range_constraint_audit"]["range_constraint_contract_passed"] is True,r
 s.page.set_content('<input type="number" min="10" max="1" step="0">');bad=s.inspect_range_constraint_contract_semantic();assert bad["range_constraint_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_range_constraint_contract_semantic",{})=="observe"
finally:s.close()
print("range constraint contract smoke: PASS")
