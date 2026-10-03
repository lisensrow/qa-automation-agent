from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<label><input type="checkbox" checked>Enabled</label><div role="checkbox" aria-label="Inherited" aria-checked="mixed"></div>')
 r=s.inspect_checkbox_contract_semantic();assert r["checkbox_audit"]["checkbox_contract_passed"] is True,r
 s.page.set_content('<div role="checkbox" aria-label="Bad" aria-checked="yes"></div>');bad=s.inspect_checkbox_contract_semantic();assert bad["checkbox_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_checkbox_contract_semantic",{})=="observe"
finally:s.close()
print("checkbox contract smoke: PASS")
