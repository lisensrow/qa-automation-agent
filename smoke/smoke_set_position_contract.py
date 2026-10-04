from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<div role="option" aria-setsize="100" aria-posinset="20">Agent</div>')
 r=s.inspect_set_position_contract_semantic();assert r["set_position_audit"]["set_position_contract_passed"] is True,r
 s.page.set_content('<div role="option" aria-setsize="10" aria-posinset="11">Agent</div>');bad=s.inspect_set_position_contract_semantic();assert bad["set_position_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_set_position_contract_semantic",{})=="observe"
finally:s.close()
print("set position contract smoke: PASS")
