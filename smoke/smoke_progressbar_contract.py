from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<div role="progressbar" aria-label="Upload" aria-valuemin="0" aria-valuemax="100" aria-valuenow="40" style="width:100px;height:10px"></div>')
 r=s.inspect_progressbar_contract_semantic("Upload");assert r["progressbar_audit"]["numeric_contract_passed"] is True,r
 assert classify_tool_action("browser_inspect_progressbar_contract_semantic",{})=="observe"
finally:s.close()
print("progressbar contract smoke: PASS")
