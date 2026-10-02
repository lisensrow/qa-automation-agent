from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<label>Port<input aria-invalid="true" aria-errormessage="port-error"></label><span id="port-error">Port is required</span>')
 r=s.inspect_invalid_field_contract_semantic();assert r["invalid_field_audit"]["invalid_field_contract_passed"] is True,r
 s.page.set_content('<label>Port<input aria-invalid="true"></label>');bad=s.inspect_invalid_field_contract_semantic();assert bad["invalid_field_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_invalid_field_contract_semantic",{})=="observe"
finally:s.close()
print("invalid field contract smoke: PASS")
