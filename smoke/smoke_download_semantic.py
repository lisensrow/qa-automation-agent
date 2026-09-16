import hashlib
from pathlib import Path

from tools.browser import BrowserSession
from tools.registry import TOOLS
from uqa import classify_tool_action


CONTENT = b"UQA harmless download fixture\n"
EXPECTED_SHA = hashlib.sha256(CONTENT).hexdigest()

session = BrowserSession()
try:
    session._ensure_started()
    session.page.set_content(
        """
        <button onclick="makeDownload()">Download report</button>
        <button disabled>Disabled download</button>
        <button>Duplicate</button><button>Duplicate</button>
        <script>
          window.clicks = 0;
          function makeDownload() {
            window.clicks++;
            const blob = new Blob(
              ['UQA harmless download fixture\\n'], {type: 'text/plain'}
            );
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'report.txt';
            document.body.appendChild(a);
            a.click();
            a.remove();
          }
        </script>
        """
    )
    assert session.download_semantic(
        "Download report", "", "text", EXPECTED_SHA
    )["error"] == "download_expected_filename_required"
    assert session.download_semantic(
        "Download report", "report.txt", "text", "bad"
    )["error"] == "download_expected_sha256_invalid"
    assert session.download_semantic(
        "Duplicate", "report.txt"
    )["error"] == "download_trigger_not_unique"
    assert session.download_semantic(
        "Disabled download", "report.txt"
    )["error"] == "download_trigger_disabled"
    assert session.page.evaluate("window.clicks") == 0

    verified = session.download_semantic(
        "Download report", "report.txt", "text", EXPECTED_SHA
    )
    assert verified["download_status"] == "verified", verified
    assert verified["download_name_matches"] is True, verified
    assert verified["download_format_matches"] is True, verified
    assert verified["download_hash_matches"] is True, verified
    assert verified["download_sha256"] == EXPECTED_SHA, verified
    artifact = Path(verified["download_artifact"])
    assert artifact.is_file() and artifact.read_bytes() == CONTENT
    assert artifact.stat().st_mode & 0o077 == 0

    metadata = session.download_semantic("Download report", "report.txt", "text")
    assert metadata["download_status"] == "metadata_only", metadata
    mismatch = session.download_semantic(
        "Download report", "wrong.txt", "text", EXPECTED_SHA
    )
    assert mismatch["download_status"] == "mismatch", mismatch
    assert session.page.evaluate("window.clicks") == 3
    assert classify_tool_action(
        "browser_download_semantic", {"name": "Download report"}
    ) == "write"
    assert classify_tool_action(
        "browser_download_semantic", {"name": "Delete export"}
    ) == "destructive"
    assert any(
        item["function"]["name"] == "browser_download_semantic"
        for item in TOOLS
    )
finally:
    session.close()

print("download semantic smoke: PASS")
