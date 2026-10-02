from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<label>Email<input type="email" required></label>')
 r=s.inspect_required_field_contract_semantic();assert r["required_field_audit"]["required_field_contract_passed"] is True,r
 s.page.set_content('<input required>');bad=s.inspect_required_field_contract_semantic();assert bad["required_field_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_required_field_contract_semantic",{})=="observe"
finally:s.close()
print("required field contract smoke: PASS")
