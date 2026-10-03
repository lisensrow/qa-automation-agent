from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<h2 id="title">Agents</h2><section aria-labelledby="title"></section>')
 r=s.inspect_aria_labelledby_contract_semantic();assert r["aria_labelledby_audit"]["aria_labelledby_contract_passed"] is True,r
 s.page.set_content('<section aria-labelledby="missing"></section>');bad=s.inspect_aria_labelledby_contract_semantic();assert bad["aria_labelledby_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_aria_labelledby_contract_semantic",{})=="observe"
finally:s.close()
print("aria labelledby contract smoke: PASS")
