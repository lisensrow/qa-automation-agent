from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<form><button type="submit">Save</button><button type="button">Preview</button></form>')
 r=s.inspect_button_type_contract_semantic();assert r["button_type_audit"]["button_type_contract_passed"] is True,r
 s.page.set_content('<form><button>Accidental</button></form>');bad=s.inspect_button_type_contract_semantic();assert bad["button_type_audit"]["implicit_submit_count"]==1,bad
 assert classify_tool_action("browser_inspect_button_type_contract_semantic",{})=="observe"
finally:s.close()
print("button type contract smoke: PASS")
