from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<video><track kind="captions" srclang="en" label="English" src="captions.vtt"></video>')
 r=s.inspect_media_caption_contract_semantic();assert r["media_caption_audit"]["media_caption_contract_passed"] is True,r
 s.page.set_content('<video></video>');bad=s.inspect_media_caption_contract_semantic();assert bad["media_caption_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_media_caption_contract_semantic",{})=="observe"
finally:s.close()
print("media caption contract smoke: PASS")
