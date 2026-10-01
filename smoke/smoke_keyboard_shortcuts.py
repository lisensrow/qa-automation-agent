from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('<button accesskey="s">Save</button><button aria-keyshortcuts="Control+K">Search</button>')
 r=s.inspect_keyboard_shortcuts_semantic();assert r["keyboard_shortcut_audit"]["keyboard_shortcuts_passed"] is True,r
 s.page.set_content('<button accesskey="x">One</button><button accesskey="x">Two</button>');bad=s.inspect_keyboard_shortcuts_semantic();assert bad["keyboard_shortcut_audit"]["duplicate_count"]==1,bad
 assert classify_tool_action("browser_inspect_keyboard_shortcuts_semantic",{})=="observe"
finally:s.close()
print("keyboard shortcuts smoke: PASS")
