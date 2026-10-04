from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<button aria-haspopup="menu" aria-controls="menu">Actions</button><div id="menu" role="menu"></div>')
 r=s.inspect_haspopup_contract_semantic();assert r["haspopup_audit"]["haspopup_contract_passed"] is True,r
 s.page.set_content('<button aria-haspopup="popup">Actions</button>');bad=s.inspect_haspopup_contract_semantic();assert bad["haspopup_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_haspopup_contract_semantic",{})=="observe"
finally:s.close()
print("haspopup contract smoke: PASS")
