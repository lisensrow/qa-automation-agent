from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<div role="meter" aria-label="CPU" aria-valuemin="0" aria-valuemax="100" aria-valuenow="62" style="width:100px;height:10px"></div>')
 r=s.inspect_meter_contract_semantic("CPU");assert r["meter_audit"]["numeric_contract_passed"] is True,r
 assert classify_tool_action("browser_inspect_meter_contract_semantic",{})=="observe"
finally:s.close()
print("meter contract smoke: PASS")
