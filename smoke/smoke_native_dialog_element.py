from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<dialog open aria-label="Editor">Body</dialog>')
 r=s.inspect_native_dialog_element_semantic();assert r["native_dialog_element_audit"]["native_dialog_contract_passed"] is True,r
 assert classify_tool_action("browser_inspect_native_dialog_element_semantic",{})=="observe"
finally:s.close()
print("native dialog element smoke: PASS")
