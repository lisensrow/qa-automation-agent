from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<body style="font-family:Arial">Ready</body>')
 r=s.inspect_font_readiness_semantic();assert r["font_readiness_audit"]["font_readiness_passed"] is True,r
 assert classify_tool_action("browser_inspect_font_readiness_semantic",{})=="observe"
finally:s.close()
print("font readiness smoke: PASS")
