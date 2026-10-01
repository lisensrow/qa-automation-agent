from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<html lang="en-US"><head><title>Dashboard</title><meta name="viewport" content="width=device-width, initial-scale=1"></head><body>Ok</body></html>')
 r=s.inspect_document_metadata_semantic();assert r["document_metadata_audit"]["document_metadata_passed"] is True,r
 assert classify_tool_action("browser_inspect_document_metadata_semantic",{})=="observe"
finally:s.close()
print("document metadata smoke: PASS")
