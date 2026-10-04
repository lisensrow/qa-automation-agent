from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<html lang="ru"><body><span lang="en-US">Online</span></body></html>')
 r=s.inspect_language_contract_semantic();assert r["language_audit"]["language_contract_passed"] is True,r
 s.page.set_content('<html><body><span lang="bad_tag">X</span></body></html>');bad=s.inspect_language_contract_semantic();assert bad["language_audit"]["language_contract_passed"] is False,bad
 assert classify_tool_action("browser_inspect_language_contract_semantic",{})=="observe"
finally:s.close()
print("language contract smoke: PASS")
