from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<time datetime="2026-10-04T14:00:00+03:00">4 October, 14:00</time>')
 r=s.inspect_time_contract_semantic();assert r["time_audit"]["time_contract_passed"] is True,r
 s.page.set_content('<time datetime="someday">Soon</time>');bad=s.inspect_time_contract_semantic();assert bad["time_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_time_contract_semantic",{})=="observe"
finally:s.close()
print("time contract smoke: PASS")
