from io import BytesIO
import hashlib
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace

import artifact_staging
import job_store
from tools.browser import BrowserSession
from uqa import CORE_RESOURCE_TOOLS, classify_tool_action


CONTENT = b"harmless synthetic package"
EXPECTED = hashlib.sha256(CONTENT).hexdigest()
SOURCE = "/home/adminacc/uqa-input/plugins/test-plugin.tar.gz"


class FakeSFTP:
    def normalize(self, source):
        return source

    def lstat(self, source):
        assert source == SOURCE
        return SimpleNamespace(
            st_mode=stat.S_IFREG | 0o644,
            st_size=len(CONTENT),
        )

    def open(self, source, mode):
        assert source == SOURCE and mode == "rb"
        return BytesIO(CONTENT)

    def close(self):
        pass


class FakeClient:
    def open_sftp(self):
        return FakeSFTP()

    def close(self):
        pass


original_jobs_dir = job_store.JOBS_DIR
original_staging_base = artifact_staging.STAGING_BASE
original_connect = artifact_staging._connect
try:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        job_store.JOBS_DIR = root / "jobs"
        artifact_staging.STAGING_BASE = root / "staged"
        artifact_staging._connect = lambda stand: (
            FakeClient(), {"ssh_username": "adminacc"},
        )
        job = job_store.create_job("Synthetic artifact staging smoke", stand="fake-stand")
        job_id = job["job_id"]
        assert job["staged_artifacts"] == []
        staged = artifact_staging.stage_test_artifact(
            job_id, "fake-stand", SOURCE, EXPECTED,
        )
        assert staged["status"] == "staged", staged
        assert staged["sha256"] == EXPECTED, staged
        assert "path" not in staged and "content" not in staged
        item = artifact_staging.get_verified_staged_artifact(
            job_id, staged["artifact_id"],
        )
        assert Path(item["path"]).read_bytes() == CONTENT
        assert Path(item["path"]).stat().st_mode & 0o077 == 0
        assert len(job_store.get_job(job_id)["staged_artifacts"]) == 1
        try:
            artifact_staging.stage_test_artifact(job_id, "other-stand", SOURCE, EXPECTED)
            raise AssertionError("cross-stand artifact accepted")
        except ValueError as error:
            assert str(error) == "artifact_stand_mismatch"

        try:
            artifact_staging.stage_test_artifact(
                job_id, "fake-stand", SOURCE, "0" * 64,
            )
            raise AssertionError("hash mismatch accepted")
        except ValueError as error:
            assert str(error) == "artifact_sha256_mismatch"
        assert len(job_store.get_job(job_id)["staged_artifacts"]) == 1
        assert not list((root / "staged" / job_id).glob(".transfer-*"))
        try:
            artifact_staging.stage_test_artifact(
                job_id, "fake-stand", "/home/adminacc/uqa-input/../secrets/x", EXPECTED,
            )
            raise AssertionError("traversal accepted")
        except ValueError as error:
            assert str(error) == "artifact_source_outside_input_directory"
        assert classify_tool_action("stage_test_artifact", {}) == "write"
        assert classify_tool_action(
            "browser_upload_staged_artifact_semantic", {}
        ) == "write"
        names = {tool["function"]["name"] for tool in CORE_RESOURCE_TOOLS}
        assert "stage_test_artifact" in names
        assert "browser_upload_staged_artifact_semantic" in names

        session = BrowserSession()
        try:
            session._ensure_started()
            session.page.set_content(
                """
                <label for="package">Package</label>
                <input id="package" type="file" accept=".tar.gz">
                <button onclick="document.getElementById('chooser').click()">
                  Choose package
                </button>
                <input id="chooser" type="file" hidden>
                """
            )
            selected = session.set_staged_file_semantic(
                staged["artifact_id"], "test-plugin.tar.gz",
                CONTENT, field="Package",
            )
            assert selected["file_status"] == "selected", selected
            assert selected["file_after"]["name"] == "test-plugin.tar.gz"
            assert selected["server_persistence_verified"] is False
            chosen = session.set_staged_file_semantic(
                staged["artifact_id"], "test-plugin.tar.gz",
                CONTENT, trigger="Choose package",
            )
            assert chosen["file_status"] == "selected", chosen
            assert chosen["file_after"]["name"] == "test-plugin.tar.gz"
        finally:
            session.close()
finally:
    job_store.JOBS_DIR = original_jobs_dir
    artifact_staging.STAGING_BASE = original_staging_base
    artifact_staging._connect = original_connect

print("artifact staging smoke: PASS")
