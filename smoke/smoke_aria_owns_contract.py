from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<div id="owner" aria-owns="item"></div><div id="item">Owned</div>')
 r=s.inspect_aria_owns_contract_semantic();assert r["aria_owns_audit"]["aria_owns_contract_passed"] is True,r
 s.page.set_content('<div id="owner" aria-owns="owner"></div>');bad=s.inspect_aria_owns_contract_semantic();assert bad["aria_owns_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_aria_owns_contract_semantic",{})=="observe"
finally:s.close()
print("aria owns contract smoke: PASS")
