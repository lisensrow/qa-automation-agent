from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<base href="https://example.test/app/">')
 r=s.inspect_base_url_contract_semantic();assert r["base_url_audit"]["base_url_contract_passed"] is True,r
 s.page.set_content('<base href="javascript:alert(1)">');bad=s.inspect_base_url_contract_semantic();assert bad["base_url_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_base_url_contract_semantic",{})=="observe"
finally:s.close()
print("base URL contract smoke: PASS")
