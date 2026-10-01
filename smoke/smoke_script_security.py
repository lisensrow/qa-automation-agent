from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<base href="https://app.test/"><script src="/app.js" defer></script>')
 r=s.inspect_script_security_semantic();assert r["script_security_audit"]["script_security_passed"] is True,r
 s.page.set_content('<base href="https://app.test/"><script src="http://cdn.test/app.js"></script>');bad=s.inspect_script_security_semantic();assert bad["script_security_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_script_security_semantic",{})=="observe"
finally:s.close()
print("script security smoke: PASS")
