from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<div role="spinbutton" aria-label="Retries" aria-valuemin="0" aria-valuemax="10" aria-valuenow="3" style="width:100px;height:20px"></div>')
 r=s.inspect_spinbutton_contract_semantic("Retries");assert r["spinbutton_audit"]["numeric_contract_passed"] is True,r
 assert classify_tool_action("browser_inspect_spinbutton_contract_semantic",{})=="observe"
finally:s.close()
print("spinbutton contract smoke: PASS")
