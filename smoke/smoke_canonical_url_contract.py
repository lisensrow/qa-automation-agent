from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<link rel="canonical" href="https://example.test/agents">')
 r=s.inspect_canonical_url_contract_semantic();assert r["canonical_url_audit"]["canonical_url_contract_passed"] is True,r
 s.page.set_content('<link rel="canonical" href="https://example.test/a"><link rel="canonical" href="https://example.test/b">');bad=s.inspect_canonical_url_contract_semantic();assert bad["canonical_url_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_canonical_url_contract_semantic",{})=="observe"
finally:s.close()
print("canonical URL contract smoke: PASS")
