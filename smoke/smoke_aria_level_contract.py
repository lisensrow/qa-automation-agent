from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<div role="treeitem" aria-level="2">Child</div>')
 r=s.inspect_aria_level_contract_semantic();assert r["aria_level_audit"]["aria_level_contract_passed"] is True,r
 s.page.set_content('<button aria-level="0">Wrong</button>');bad=s.inspect_aria_level_contract_semantic();assert bad["aria_level_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_aria_level_contract_semantic",{})=="observe"
finally:s.close()
print("aria level contract smoke: PASS")
