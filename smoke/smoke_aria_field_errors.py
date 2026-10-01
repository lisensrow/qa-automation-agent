from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started(); s.page.set_content('<form aria-label="Profile"><label>Email<input aria-invalid="true" aria-errormessage="email-error"></label><span id="email-error">Invalid email</span></form>')
 r=s.inspect_aria_field_errors_semantic("Profile"); a=r["aria_error_audit"]
 assert a["invalid_control_count"]==1 and a["invalid_controls"][0]["messages"]==["Invalid email"],r
 assert all("value" not in x for x in a["invalid_controls"])
 assert classify_tool_action("browser_inspect_aria_field_errors_semantic",{})=="observe"
finally:s.close()
print("aria field errors smoke: PASS")
