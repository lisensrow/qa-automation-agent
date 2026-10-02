from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<button popovertarget="info">Info</button><div id="info" popover>Details</div>')
 r=s.inspect_popover_contract_semantic();assert r["popover_api_audit"]["popover_contract_passed"] is True,r
 assert classify_tool_action("browser_inspect_popover_contract_semantic",{})=="observe"
finally:s.close()
print("popover API contract smoke: PASS")
