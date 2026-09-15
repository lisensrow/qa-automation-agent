from tools.browser import BrowserSession
from uqa import classify_tool_action


session = BrowserSession()

try:
    session._ensure_started()
    session.page.set_content(
        """
        <html><body>
          <label for="source">Source</label>
          <input id="source" value="public test value">
          <label for="target">Target</label>
          <input id="target" value="old value">
          <label for="password">Password</label>
          <input id="password" type="password" value="never-copy-this">
          <script>
            window.lastChord = null;
            document.getElementById('target').addEventListener('keydown', event => {
              window.lastChord = {
                key: event.key,
                control: event.ctrlKey,
                shift: event.shiftKey
              };
            });
          </script>
        </body></html>
        """
    )

    chord = session.press_key_semantic(
        "Control+Shift+Z",
        target="Target",
    )
    assert chord.get("keyboard_event_executed") is True, chord
    observed = session.page.evaluate("window.lastChord")
    assert observed == {
        "key": "Z",
        "control": True,
        "shift": True,
    }, observed

    unsupported = session.press_key_semantic(
        "Control+C",
        target="Source",
    )
    assert unsupported.get("error") == "unsupported_keyboard_key", unsupported

    copied = session.copy_value_semantic("Source")
    assert copied.get("status") == "copied_to_private_clipboard", copied
    assert copied.get("character_count") == len("public test value"), copied
    assert copied.get("clipboard_content_exposed") is False, copied
    assert "public test value" not in str(copied), copied

    pasted = session.paste_private_semantic("Target", replace=True)
    assert pasted.get("status") == "pasted_from_private_clipboard", pasted
    assert session.page.locator("#target").input_value() == (
        "public test value"
    ), pasted
    assert pasted.get("clipboard_content_exposed") is False, pasted

    blocked = session.copy_value_semantic("Password")
    assert blocked.get("error") == (
        "private_clipboard_sensitive_source_blocked"
    ), blocked
    assert "never-copy-this" not in str(blocked), blocked

    cleared = session.clear_private_clipboard()
    assert cleared.get("status") == "private_clipboard_cleared", cleared
    empty = session.paste_private_semantic("Target")
    assert empty.get("error") == "private_clipboard_empty", empty

    assert classify_tool_action(
        "browser_press_key_semantic",
        {"key": "Control+A"},
    ) == "interact"
    assert classify_tool_action(
        "browser_press_key_semantic",
        {"key": "Control+Z"},
    ) == "write"
    assert classify_tool_action(
        "browser_copy_value_semantic",
        {},
    ) == "interact"
    assert classify_tool_action(
        "browser_paste_private_semantic",
        {},
    ) == "write"
finally:
    session.clear_private_clipboard()
    session.close()

print("keyboard chords/private clipboard smoke: PASS")
