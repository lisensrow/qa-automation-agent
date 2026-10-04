from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<svg role="img"><title>CPU usage</title><circle cx="5" cy="5" r="4"/></svg>')
 r=s.inspect_svg_accessibility_contract_semantic();assert r["svg_accessibility_audit"]["svg_accessibility_contract_passed"] is True,r
 s.page.set_content('<svg role="img"><circle cx="5" cy="5" r="4"/></svg>');bad=s.inspect_svg_accessibility_contract_semantic();assert bad["svg_accessibility_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_svg_accessibility_contract_semantic",{})=="observe"
finally:s.close()
print("svg accessibility contract smoke: PASS")
