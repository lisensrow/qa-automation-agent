from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<table><caption>Agents</caption><tr><th>Name</th><th>Status</th></tr><tr><td>A1</td><td>Online</td></tr></table>')
 r=s.inspect_table_structure_contract_semantic();assert r["table_structure_audit"]["table_structure_contract_passed"] is True,r
 s.page.set_content('<table><tr><td>orphan data</td></tr></table>');bad=s.inspect_table_structure_contract_semantic();assert bad["table_structure_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_table_structure_contract_semantic",{})=="observe"
finally:s.close()
print("table structure contract smoke: PASS")
