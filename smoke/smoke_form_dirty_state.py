from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started(); s.page.set_content('<form aria-label="Profile"><input name="email" value="before"><input type="checkbox" name="active"></form>')
 a=s.track_form_dirty_state_semantic("Profile","capture"); assert a["form_dirty"] is False,a
 s.page.locator('[name=email]').fill('after')
 b=s.track_form_dirty_state_semantic("Profile","compare"); assert b["form_dirty"] is True,b
 assert "value" not in str(b).lower() and "before" not in str(b) and "after" not in str(b),b
 s.track_form_dirty_state_semantic("Profile","capture")
 c=s.track_form_dirty_state_semantic("Profile","compare"); assert c["form_dirty"] is False,c
 assert classify_tool_action("browser_track_form_dirty_state_semantic",{})=="observe"
finally:s.close()
print("form dirty state smoke: PASS")
