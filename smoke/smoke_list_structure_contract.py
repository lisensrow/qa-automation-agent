from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<div role="list"><div role="listitem">One</div><div role="listitem">Two</div></div>')
 r=s.inspect_list_structure_contract_semantic();assert r["list_structure_audit"]["list_structure_contract_passed"] is True,r
 s.page.set_content('<div role="list"><div>Broken</div></div>');bad=s.inspect_list_structure_contract_semantic();assert bad["list_structure_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_list_structure_contract_semantic",{})=="observe"
finally:s.close()
print("list structure contract smoke: PASS")
