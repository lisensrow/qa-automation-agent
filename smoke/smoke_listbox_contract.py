from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<div role="listbox" aria-label="Cities"><div role="option" aria-selected="true">London</div><div role="option" aria-selected="false">Paris</div></div>')
 r=s.inspect_listbox_contract_semantic("Cities");assert r["listbox_audit"]["listbox_contract_passed"] is True,r
 assert classify_tool_action("browser_inspect_listbox_contract_semantic",{})=="observe"
finally:s.close()
print("listbox contract smoke: PASS")
