from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<div style="width:40px;white-space:nowrap;overflow:hidden">Long visible text</div>')
 r=s.inspect_text_clipping_semantic();assert r["text_clipping_audit"]["clipped_count"]==1,r
 assert classify_tool_action("browser_inspect_text_clipping_semantic",{})=="observe"
finally:s.close()
print("text clipping smoke: PASS")
