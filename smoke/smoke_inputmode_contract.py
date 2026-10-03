from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<label>Phone<input inputmode="tel"></label>')
 r=s.inspect_inputmode_contract_semantic();assert r["inputmode_audit"]["inputmode_contract_passed"] is True,r
 s.page.set_content('<input inputmode="telephone">');bad=s.inspect_inputmode_contract_semantic();assert bad["inputmode_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_inputmode_contract_semantic",{})=="observe"
finally:s.close()
print("inputmode contract smoke: PASS")
