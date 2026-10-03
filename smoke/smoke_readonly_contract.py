from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<label>Identifier<input readonly value="42"></label><div role="textbox" aria-label="Result" aria-readonly="true"></div>')
 r=s.inspect_readonly_contract_semantic();assert r["readonly_audit"]["readonly_contract_passed"] is True,r
 s.page.set_content('<button aria-label="Wrong" aria-readonly="true">X</button>');bad=s.inspect_readonly_contract_semantic();assert bad["readonly_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_readonly_contract_semantic",{})=="observe"
finally:s.close()
print("readonly contract smoke: PASS")
