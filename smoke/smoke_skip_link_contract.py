from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<a href="#content">Skip to content</a><nav><a href="/">Home</a></nav><main id="content">Body</main>')
 r=s.inspect_skip_link_contract_semantic();a=r["skip_link_audit"];assert a["skip_link_present"] is True and a["skip_link_contract_passed"] is True,r
 s.page.set_content('<a href="#menu">Skip</a><nav id="menu">Menu</nav>');bad=s.inspect_skip_link_contract_semantic();assert bad["skip_link_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_skip_link_contract_semantic",{})=="observe"
finally:s.close()
print("skip link contract smoke: PASS")
