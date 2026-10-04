from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<canvas aria-label="RAM usage chart"></canvas>')
 r=s.inspect_canvas_fallback_contract_semantic();assert r["canvas_fallback_audit"]["canvas_fallback_contract_passed"] is True,r
 s.page.set_content('<canvas></canvas>');bad=s.inspect_canvas_fallback_contract_semantic();assert bad["canvas_fallback_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_canvas_fallback_contract_semantic",{})=="observe"
finally:s.close()
print("canvas fallback contract smoke: PASS")
