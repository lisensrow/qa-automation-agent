from tools.browser import BrowserSession
from uqa import classify_tool_action
s=BrowserSession()
try:
 s._ensure_started();s.page.set_content('''<button id="outside">Outside</button><div role="dialog" aria-label="Editor"><button id="a">A</button><button id="b">B</button></div><script>const d=document.querySelector('[role=dialog]');d.addEventListener('keydown',e=>{if(e.key!=='Tab')return;const x=[...d.querySelectorAll('button')];if(document.activeElement===x[x.length-1]){e.preventDefault();x[0].focus();}})</script>''')
 r=s.inspect_dialog_focus_trap_semantic("Editor");assert r["focus_trap_passed"] is True,r
 assert classify_tool_action("browser_inspect_dialog_focus_trap_semantic",{})=="interact"
finally:s.close()
print("dialog focus trap smoke: PASS")
