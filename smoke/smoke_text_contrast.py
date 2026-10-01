from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<main style="background:rgb(255,255,255)"><p style="color:rgb(0,0,0)">Readable</p></main>')
 r=s.inspect_text_contrast_semantic();assert r["text_contrast_audit"]["contrast_passed"] is True,r
 s.page.set_content('<main style="background:rgb(255,255,255)"><p style="color:rgb(240,240,240)">Faint</p></main>');bad=s.inspect_text_contrast_semantic();assert bad["text_contrast_audit"]["failure_count"]>=1,bad
 assert classify_tool_action("browser_inspect_text_contrast_semantic",{})=="observe"
finally:s.close()
print("text contrast smoke: PASS")
