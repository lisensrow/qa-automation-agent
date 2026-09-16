from tools.browser import BrowserSession
from tools.registry import TOOLS
from uqa import classify_tool_action


session = BrowserSession()
try:
    session._ensure_started()
    session.page.set_content(
        """
        <label for="document">Document</label>
        <input id="document" type="file" accept=".txt,text/plain"
               onchange="window.changeCount++; window.lastName = this.files[0].name">
        <label for="hidden-file">Hidden document</label>
        <input id="hidden-file" type="file" hidden>
        <label for="image-file">Image</label>
        <input id="image-file" type="file" accept="image/png">
        <label for="disabled-file">Disabled document</label>
        <input id="disabled-file" type="file" disabled>
        <label>Duplicate<input type="file"></label>
        <label>Duplicate<input type="file"></label>
        <input type="file" aria-label="Inaccessible" hidden>
        <script>window.changeCount = 0;</script>
        """
    )
    observed = session.inspect_file_input_semantic("Document")
    assert observed["file_input"]["file_count"] == 0, observed
    assert observed["file_input"]["accept"] == ".txt,text/plain", observed
    assert session.inspect_file_input_semantic("Missing")["error"] == "file_input_not_unique"
    assert session.inspect_file_input_semantic("Duplicate")["error"] == "file_input_not_unique"
    assert session.inspect_file_input_semantic("Inaccessible")["error"] == "file_input_not_unique"
    assert session.inspect_file_input_semantic("Disabled document")["error"] == "file_input_disabled"
    assert session.inspect_file_input_semantic("Hidden document")["file_input"]["file_count"] == 0
    assert session.set_upload_fixture_semantic(
        "Document", "/opt/uqa/secrets/password.txt"
    )["error"] == "upload_fixture_not_allowed"
    assert session.set_upload_fixture_semantic(
        "Image", "sample-text"
    )["error"] == "upload_fixture_type_not_accepted"
    assert session.page.evaluate("window.changeCount") == 0
    selected = session.set_upload_fixture_semantic("Document", "sample-text")
    assert selected["file_status"] == "selected", selected
    assert selected["file_after"]["name"] == "uqa-sample.txt", selected
    assert session.page.evaluate("window.changeCount") == 1
    assert session.page.evaluate("window.lastName") == "uqa-sample.txt"
    content = session.page.evaluate(
        "async () => await document.getElementById('document').files[0].text()"
    )
    assert content == "UQA harmless upload fixture\n", content
    assert classify_tool_action(
        "browser_inspect_file_input_semantic", {"field": "Document"}
    ) == "observe"
    assert classify_tool_action(
        "browser_set_upload_fixture_semantic", {"field": "Document"}
    ) == "write"
    names = {item["function"]["name"] for item in TOOLS}
    assert "browser_inspect_file_input_semantic" in names
    assert "browser_set_upload_fixture_semantic" in names
finally:
    session.close()

print("upload fixture smoke: PASS")
