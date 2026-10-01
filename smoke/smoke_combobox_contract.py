from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<label>City<input role="combobox" aria-expanded="true" aria-controls="cities" aria-activedescendant="london"></label><div role="listbox" id="cities"><div role="option" id="london">London</div></div>')
 r=s.inspect_combobox_contract_semantic("City");assert r["combobox_audit"]["combobox_contract_passed"] is True,r
 assert classify_tool_action("browser_inspect_combobox_contract_semantic",{})=="observe"
finally:s.close()
print("combobox contract smoke: PASS")
