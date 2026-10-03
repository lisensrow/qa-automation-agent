from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<a href="https://example.com/docs" target="_blank" rel="noopener">Docs</a>')
 r=s.inspect_new_tab_link_contract_semantic();assert r["new_tab_link_audit"]["new_tab_link_contract_passed"] is True,r
 s.page.set_content('<a href="https://example.com" target="_blank">Open</a>');bad=s.inspect_new_tab_link_contract_semantic();assert bad["new_tab_link_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_new_tab_link_contract_semantic",{})=="observe"
finally:s.close()
print("new tab link contract smoke: PASS")
