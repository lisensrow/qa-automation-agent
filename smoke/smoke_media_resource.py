from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<base href="https://app.test/"><img alt="Pixel" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==">');s.page.wait_for_timeout(100)
 r=s.inspect_media_resource_semantic();assert r["media_resource_audit"]["media_resource_passed"] is True,r
 s.page.set_content('<base href="https://app.test/"><video src="http://media.test/a.mp4" autoplay></video>');bad=s.inspect_media_resource_semantic();assert bad["media_resource_audit"]["failure_count"]==1,bad
 assert classify_tool_action("browser_inspect_media_resource_semantic",{})=="observe"
finally:s.close()
print("media resource smoke: PASS")
