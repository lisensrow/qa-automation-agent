from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started(); s.page.set_content('<button disabled>Save</button><script>setTimeout(()=>document.querySelector("button").disabled=false,250)</script>')
 r=s.inspect_control_state_lifecycle_semantic("Save","button","enabled",2000,True)
 assert r.get("control_state_status")=="verified" and r["control_initial"]["enabled"] is False and r["control_final"]["enabled"] is True,r
 assert classify_tool_action("browser_inspect_control_state_lifecycle_semantic",{})=="observe"
finally:s.close()
print("control state lifecycle smoke: PASS")
