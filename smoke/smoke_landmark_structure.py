from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<header>Top</header><nav aria-label="Primary">Menu</nav><main>Body</main><footer>Bottom</footer>')
 r=s.inspect_landmark_structure_semantic();assert r["landmark_audit"]["landmark_structure_passed"] is True,r
 assert classify_tool_action("browser_inspect_landmark_structure_semantic",{})=="observe"
finally:s.close()
print("landmark structure smoke: PASS")
