from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<div dir="auto">Name</div><span dir="rtl">Text</span>')
 r=s.inspect_direction_contract_semantic();assert r["direction_audit"]["direction_contract_passed"] is True,r
 s.page.set_content('<div dir="right">X</div>');bad=s.inspect_direction_contract_semantic();assert bad["direction_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_direction_contract_semantic",{})=="observe"
finally:s.close()
print("direction contract smoke: PASS")
