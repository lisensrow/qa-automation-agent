from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<div role="tablist" aria-label="Settings"><button role="tab" aria-selected="true" aria-controls="p1">General</button><button role="tab" aria-selected="false" aria-controls="p2">Advanced</button></div><section role="tabpanel" id="p1">One</section><section role="tabpanel" id="p2" hidden>Two</section>')
 r=s.inspect_tabs_contract_semantic("Settings");assert r["tabs_audit"]["tabs_contract_passed"] is True,r
 assert classify_tool_action("browser_inspect_tabs_contract_semantic",{})=="observe"
finally:s.close()
print("tabs contract smoke: PASS")
