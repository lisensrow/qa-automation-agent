from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<div aria-label="Comment" contenteditable="plaintext-only"></div>')
 r=s.inspect_contenteditable_contract_semantic();assert r["contenteditable_audit"]["contenteditable_contract_passed"] is True,r
 s.page.set_content('<div contenteditable="maybe"></div>');bad=s.inspect_contenteditable_contract_semantic();assert bad["contenteditable_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_contenteditable_contract_semantic",{})=="observe"
finally:s.close()
print("contenteditable contract smoke: PASS")
