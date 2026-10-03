from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<button aria-controls="panel">Toggle</button><div id="panel">Body</div>')
 r=s.inspect_aria_controls_contract_semantic();assert r["aria_controls_audit"]["aria_controls_contract_passed"] is True,r
 s.page.set_content('<button aria-controls="missing">Toggle</button>');bad=s.inspect_aria_controls_contract_semantic();assert bad["aria_controls_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_aria_controls_contract_semantic",{})=="observe"
finally:s.close()
print("aria controls contract smoke: PASS")
