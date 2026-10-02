from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<fieldset><legend>Environment</legend><label><input type="checkbox">Test</label></fieldset>')
 r=s.inspect_fieldset_contract_semantic();assert r["fieldset_audit"]["fieldset_contract_passed"] is True,r
 assert classify_tool_action("browser_inspect_fieldset_contract_semantic",{})=="observe"
finally:s.close()
print("fieldset contract smoke: PASS")
