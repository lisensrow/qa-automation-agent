from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<a href="#details">Details</a><section id="details">Data</section>')
 r=s.inspect_hash_link_contract_semantic();assert r["hash_link_audit"]["hash_link_contract_passed"] is True,r
 s.page.set_content('<a href="#missing">Broken</a>');bad=s.inspect_hash_link_contract_semantic();assert bad["hash_link_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_hash_link_contract_semantic",{})=="observe"
finally:s.close()
print("hash link contract smoke: PASS")
