from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<div role="status">Ready</div><div aria-live="assertive">Warning</div>')
 r=s.inspect_live_region_contract_semantic();assert r["live_region_audit"]["live_region_contract_passed"] is True,r
 s.page.set_content('<div aria-live="loud">Bad</div>');bad=s.inspect_live_region_contract_semantic();assert bad["live_region_audit"]["invalid_count"]==1,bad
 assert classify_tool_action("browser_inspect_live_region_contract_semantic",{})=="observe"
finally:s.close()
print("live region contract smoke: PASS")
