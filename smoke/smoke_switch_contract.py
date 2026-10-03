from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<button role="switch" aria-checked="true">Monitoring</button>')
 r=s.inspect_switch_contract_semantic();assert r["switch_audit"]["switch_contract_passed"] is True,r
 s.page.set_content('<button role="switch" aria-checked="mixed">Monitoring</button>');bad=s.inspect_switch_contract_semantic();assert bad["switch_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_switch_contract_semantic",{})=="observe"
finally:s.close()
print("switch contract smoke: PASS")
