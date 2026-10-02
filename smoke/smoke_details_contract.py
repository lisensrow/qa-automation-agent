from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<details open><summary>Advanced</summary><p>Content</p></details>')
 r=s.inspect_details_contract_semantic();assert r["details_audit"]["details_contract_passed"] is True,r
 assert classify_tool_action("browser_inspect_details_contract_semantic",{})=="observe"
finally:s.close()
print("details contract smoke: PASS")
