from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<div role="menu" aria-label="Actions"><button role="menuitem">Open</button><button role="menuitem" aria-disabled="true">Archive</button></div>')
 r=s.inspect_menu_contract_semantic("Actions");assert r["menu_audit"]["menu_contract_passed"] is True,r
 assert classify_tool_action("browser_inspect_menu_contract_semantic",{})=="observe"
finally:s.close()
print("menu contract smoke: PASS")
