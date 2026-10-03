from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<button aria-pressed="false">Pin</button>')
 r=s.inspect_toggle_button_contract_semantic();assert r["toggle_button_audit"]["toggle_button_contract_passed"] is True,r
 s.page.set_content('<div aria-pressed="true">Not button</div>');bad=s.inspect_toggle_button_contract_semantic();assert bad["toggle_button_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_toggle_button_contract_semantic",{})=="observe"
finally:s.close()
print("toggle button contract smoke: PASS")
