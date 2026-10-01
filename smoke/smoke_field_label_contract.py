from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<form aria-label="Profile"><label>Email<input name="email" aria-describedby="hint"></label><span id="hint">Work address</span></form>')
 r=s.inspect_field_label_contract_semantic("Profile");assert r["field_label_audit"]["field_label_contract_passed"] is True,r
 assert "value" not in str(r).lower();assert classify_tool_action("browser_inspect_field_label_contract_semantic",{})=="observe"
finally:s.close()
print("field label contract smoke: PASS")
