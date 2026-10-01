from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<form aria-label="Login"><label>User<input autocomplete="username"></label><label>Password<input type="password" autocomplete="current-password"></label></form>')
 r=s.inspect_autofill_contract_semantic("Login");assert r["autofill_audit"]["autofill_contract_passed"] is True,r
 assert "value" not in str(r).lower();assert classify_tool_action("browser_inspect_autofill_contract_semantic",{})=="observe"
finally:s.close()
print("autofill contract smoke: PASS")
