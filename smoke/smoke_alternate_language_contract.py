from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<link rel="alternate" hreflang="en" href="https://example.test/en"><link rel="alternate" hreflang="ru" href="https://example.test/ru">')
 r=s.inspect_alternate_language_contract_semantic();assert r["alternate_language_audit"]["alternate_language_contract_passed"] is True,r
 s.page.set_content('<link rel="alternate" hreflang="bad_tag" href="/x">');bad=s.inspect_alternate_language_contract_semantic();assert bad["alternate_language_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_alternate_language_contract_semantic",{})=="observe"
finally:s.close()
print("alternate language contract smoke: PASS")
