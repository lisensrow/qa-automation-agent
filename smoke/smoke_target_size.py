from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<button style="width:40px;height:40px">Good</button><button style="width:12px;height:12px;padding:0">Bad</button>')
 r=s.inspect_target_size_semantic();a=r["target_size_audit"];assert a["checked_count"]==2 and a["too_small_count"]==1,r
 assert classify_tool_action("browser_inspect_target_size_semantic",{})=="observe"
finally:s.close()
print("target size smoke: PASS")
