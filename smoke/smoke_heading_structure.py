from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<h1>Dashboard</h1><section><h2>Agents</h2><h3>Online</h3></section>')
 r=s.inspect_heading_structure_semantic();assert r["heading_audit"]["heading_structure_passed"] is True,r
 s.page.set_content('<h1>Dashboard</h1><h3>Skipped</h3>');bad=s.inspect_heading_structure_semantic();assert bad["heading_audit"]["skipped_level_count"]==1,bad
 assert classify_tool_action("browser_inspect_heading_structure_semantic",{})=="observe"
finally:s.close()
print("heading structure smoke: PASS")
