from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<label>Name<input minlength="2" maxlength="20"></label>')
 r=s.inspect_text_length_contract_semantic();assert r["text_length_audit"]["text_length_contract_passed"] is True,r
 s.page.set_content('<input minlength="20" maxlength="2">');bad=s.inspect_text_length_contract_semantic();assert bad["text_length_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_text_length_contract_semantic",{})=="observe"
finally:s.close()
print("text length contract smoke: PASS")
