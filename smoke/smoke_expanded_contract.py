from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<button aria-expanded="false" aria-controls="panel">Details</button><div id="panel"></div>')
 r=s.inspect_expanded_contract_semantic();assert r["expanded_audit"]["expanded_contract_passed"] is True,r
 s.page.set_content('<button aria-expanded="maybe" aria-controls="missing">Details</button>');bad=s.inspect_expanded_contract_semantic();assert bad["expanded_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_expanded_contract_semantic",{})=="observe"
finally:s.close()
print("expanded contract smoke: PASS")
