from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<nav aria-label="Breadcrumb"><a href="/">Home</a><a href="/agents" aria-current="page">Agents</a></nav>')
 r=s.inspect_breadcrumb_contract_semantic();assert r["breadcrumb_audit"]["breadcrumb_contract_passed"] is True,r
 s.page.set_content('<nav aria-label="Breadcrumb"><a href="/">Home</a></nav>');bad=s.inspect_breadcrumb_contract_semantic();assert bad["breadcrumb_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_breadcrumb_contract_semantic",{})=="observe"
finally:s.close()
print("breadcrumb contract smoke: PASS")
