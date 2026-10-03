from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<img src="logo.png" referrerpolicy="no-referrer" alt="Logo">')
 r=s.inspect_referrerpolicy_contract_semantic();assert r["referrerpolicy_audit"]["referrerpolicy_contract_passed"] is True,r
 s.page.set_content('<img src="logo.png" referrerpolicy="private" alt="Logo">');bad=s.inspect_referrerpolicy_contract_semantic();assert bad["referrerpolicy_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_referrerpolicy_contract_semantic",{})=="observe"
finally:s.close()
print("referrerpolicy contract smoke: PASS")
