from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<button aria-expanded="true" aria-controls="details">Details</button><section id="details">Content</section>')
 r=s.inspect_disclosure_contract_semantic("Details");assert r["disclosure_audit"]["disclosure_contract_passed"] is True,r
 assert classify_tool_action("browser_inspect_disclosure_contract_semantic",{})=="observe"
finally:s.close()
print("disclosure contract smoke: PASS")
