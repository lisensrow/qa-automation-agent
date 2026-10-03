from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<button disabled>Save</button><button aria-disabled="true">Delete</button>')
 r=s.inspect_disabled_control_contract_semantic();assert r["disabled_control_audit"]["disabled_control_contract_passed"] is True,r
 s.page.set_content('<div aria-disabled="true">Not a control</div>');bad=s.inspect_disabled_control_contract_semantic();assert bad["disabled_control_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_disabled_control_contract_semantic",{})=="observe"
finally:s.close()
print("disabled control contract smoke: PASS")
