from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<style>.box{transition:transform 1s}@media(prefers-reduced-motion:reduce){.box{transition:none}}</style><div class="box">Box</div>')
 r=s.inspect_reduced_motion_contract_semantic();assert r["reduced_motion_audit"]["reduced_motion_contract_passed"] is True,r
 assert r["reduced_motion_audit"]["reduced_motion_rule_present"] is True,r
 assert classify_tool_action("browser_inspect_reduced_motion_contract_semantic",{})=="observe"
finally:s.close()
print("reduced motion contract smoke: PASS")
