from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<form role="search"><label>Find agent<input type="search"></label><button type="submit">Search</button></form>')
 r=s.inspect_search_contract_semantic();a=r["search_audit"];assert a["search_contract_passed"] is True and a["form_submit_count"]==1,r
 assert classify_tool_action("browser_inspect_search_contract_semantic",{})=="observe"
finally:s.close()
print("search contract smoke: PASS")
