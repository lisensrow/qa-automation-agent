from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<h2 id="title">Editor</h2><div role="dialog" aria-modal="true" aria-labelledby="title">Body</div>')
 r=s.inspect_dialog_contract_semantic();assert r["dialog_contract_audit"]["dialog_contract_passed"] is True,r
 assert classify_tool_action("browser_inspect_dialog_contract_semantic",{})=="observe"
finally:s.close()
print("dialog contract smoke: PASS")
