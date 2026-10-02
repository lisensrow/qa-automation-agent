from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<div style="height:1200px"></div><img alt="Chart" loading="lazy" width="100" height="50">')
 r=s.inspect_lazy_media_contract_semantic();assert r["lazy_media_audit"]["lazy_media_contract_passed"] is True,r
 assert classify_tool_action("browser_inspect_lazy_media_contract_semantic",{})=="observe"
finally:s.close()
print("lazy media contract smoke: PASS")
