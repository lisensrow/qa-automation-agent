from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<div tabindex="0">Panel</div><button tabindex="-1">Hidden action</button>')
 r=s.inspect_tabindex_contract_semantic();assert r["tabindex_audit"]["tabindex_contract_passed"] is True,r
 s.page.set_content('<button tabindex="2">Forced</button>');bad=s.inspect_tabindex_contract_semantic();assert bad["tabindex_audit"]["positive_count"]==1,bad
 assert classify_tool_action("browser_inspect_tabindex_contract_semantic",{})=="observe"
finally:s.close()
print("tabindex contract smoke: PASS")
