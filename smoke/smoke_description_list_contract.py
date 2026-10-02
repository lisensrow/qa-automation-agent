from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<dl><dt>CPU</dt><dd>20%</dd><dt>RAM</dt><dd>4 GB</dd></dl>')
 r=s.inspect_description_list_contract_semantic();assert r["description_list_audit"]["description_list_contract_passed"] is True,r
 s.page.set_content('<dl><dt>CPU</dt></dl>');bad=s.inspect_description_list_contract_semantic();assert bad["description_list_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_description_list_contract_semantic",{})=="observe"
finally:s.close()
print("description list contract smoke: PASS")
