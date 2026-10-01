from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<base href="https://app.test/"><form action="/login" method="post"><input type="password"></form>')
 r=s.inspect_form_submission_contract_semantic();assert r["form_submission_audit"]["form_submission_contract_passed"] is True,r
 s.page.set_content('<base href="https://app.test/"><form action="http://bad.test/" method="get"><input type="password"></form>');bad=s.inspect_form_submission_contract_semantic();assert bad["form_submission_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_form_submission_contract_semantic",{})=="observe"
finally:s.close()
print("form submission contract smoke: PASS")
