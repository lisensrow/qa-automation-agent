from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<div role="listbox" tabindex="0" aria-activedescendant="o1"><div id="o1" role="option">One</div></div>')
 r=s.inspect_activedescendant_contract_semantic();assert r["activedescendant_audit"]["activedescendant_contract_passed"] is True,r
 s.page.set_content('<div role="listbox" tabindex="0" aria-activedescendant="missing"></div>');bad=s.inspect_activedescendant_contract_semantic();assert bad["activedescendant_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_activedescendant_contract_semantic",{})=="observe"
finally:s.close()
print("activedescendant contract smoke: PASS")
