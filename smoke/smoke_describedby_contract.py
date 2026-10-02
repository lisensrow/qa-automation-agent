from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<label>Port<input aria-describedby="port-help"></label><span id="port-help">1 to 65535</span>')
 r=s.inspect_describedby_contract_semantic();assert r["describedby_audit"]["describedby_contract_passed"] is True,r
 s.page.set_content('<input aria-describedby="missing">');bad=s.inspect_describedby_contract_semantic();assert bad["describedby_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_describedby_contract_semantic",{})=="observe"
finally:s.close()
print("describedby contract smoke: PASS")
