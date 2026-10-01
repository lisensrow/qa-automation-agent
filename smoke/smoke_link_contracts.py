from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<a href="https://example.test/path?token=secret&view=full" target="_blank" rel="noopener">Docs</a>')
 r=s.inspect_link_contracts_semantic();a=r["link_audit"];assert a["link_contracts_passed"] is True,r
 assert "secret" not in str(a) and "redacted" in str(a).lower(),a
 s.page.set_content('<a href="javascript:void(0)" target="_blank" style="display:block;width:20px;height:20px"></a>');bad=s.inspect_link_contracts_semantic();assert bad["link_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_link_contracts_semantic",{})=="observe"
finally:s.close()
print("link contracts smoke: PASS")
