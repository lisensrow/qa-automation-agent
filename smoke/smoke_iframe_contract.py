from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<iframe title="Agent console" srcdoc="<p>Ready</p>"></iframe>')
 r=s.inspect_iframe_contract_semantic();assert r["iframe_contract_audit"]["iframe_contract_passed"] is True,r
 s.page.set_content('<iframe srcdoc="<p>Missing title</p>"></iframe>');bad=s.inspect_iframe_contract_semantic();assert bad["iframe_contract_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_iframe_contract_semantic",{})=="observe"
finally:s.close()
print("iframe contract smoke: PASS")
