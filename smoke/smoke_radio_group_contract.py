from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<label><input type="radio" name="mode" checked>Auto</label><label><input type="radio" name="mode">Manual</label>')
 r=s.inspect_radio_group_contract_semantic();assert r["radio_group_audit"]["radio_group_contract_passed"] is True,r
 assert classify_tool_action("browser_inspect_radio_group_contract_semantic",{})=="observe"
finally:s.close()
print("radio group contract smoke: PASS")
