from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<nav aria-label="Primary"><a href="/">Home</a><a href="/agents" aria-current="page">Agents</a></nav>')
 r=s.inspect_navigation_current_contract_semantic();assert r["navigation_current_audit"]["navigation_current_contract_passed"] is True,r
 s.page.set_content('<nav><a aria-current="page">A</a><a aria-current="page">B</a></nav>');bad=s.inspect_navigation_current_contract_semantic();assert bad["navigation_current_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_navigation_current_contract_semantic",{})=="observe"
finally:s.close()
print("navigation current contract smoke: PASS")
