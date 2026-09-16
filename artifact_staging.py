"""Job-scoped, checksum-verified transfer from a saved stand input directory."""

import getpass
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
import uuid

from job_store import get_job, save_job
from ssh_worker import _connect
from stands import normalize_stand


STAGING_BASE = Path("/opt/uqa/state/staged_artifacts")
MAX_ARTIFACT_BYTES = 100 * 1024 * 1024


def _job_for_current_user(job_id):
    job = get_job(job_id)
    if not job:
        raise ValueError("job_not_found")
    current_user = (os.getenv("UQA_USER") or getpass.getuser()).strip()
    if job.get("owner") != current_user:
        raise PermissionError("job_owner_mismatch")
    return job


def _source_path(source_path, username):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", str(username or "")):
        raise ValueError("invalid_stand_ssh_username")
    raw = str(source_path or "")
    path = PurePosixPath(raw)
    prefix = PurePosixPath("/home") / username / "uqa-input"
    if (
        not path.is_absolute()
        or ".." in path.parts
        or str(path) != raw
        or prefix not in path.parents
    ):
        raise ValueError("artifact_source_outside_input_directory")
    return str(path)


def _workspace(job_id):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", str(job_id or "")):
        raise ValueError("invalid_job_id")
    root = STAGING_BASE / job_id
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    return root


def stage_test_artifact(job_id, stand, source_path, expected_sha256):
    """Read a regular file via saved SSH credentials; register only after hash match."""
    job = _job_for_current_user(job_id)
    if not job.get("stand") or normalize_stand(stand or "") != normalize_stand(job["stand"]):
        raise ValueError("artifact_stand_mismatch")
    expected = str(expected_sha256 or "").casefold()
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("invalid_expected_sha256")
    client, info = _connect(stand)
    sftp = None
    temporary = None
    try:
        source = _source_path(source_path, info["ssh_username"])
        sftp = client.open_sftp()
        canonical = sftp.normalize(source)
        _source_path(canonical, info["ssh_username"])
        if canonical != source:
            raise ValueError("artifact_source_symlink_or_alias")
        remote_stat = sftp.lstat(source)
        if not stat.S_ISREG(remote_stat.st_mode):
            raise ValueError("artifact_source_not_regular_file")
        if not 0 < remote_stat.st_size <= MAX_ARTIFACT_BYTES:
            raise ValueError("artifact_size_out_of_range")
        workspace = _workspace(job_id)
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=workspace, prefix=".transfer-", delete=False,
        ) as output:
            temporary = Path(output.name)
            os.chmod(temporary, 0o600)
            digest = hashlib.sha256()
            size = 0
            with sftp.open(source, "rb") as remote:
                while True:
                    chunk = remote.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_ARTIFACT_BYTES:
                        raise ValueError("artifact_size_out_of_range")
                    output.write(chunk)
                    digest.update(chunk)
        if size != remote_stat.st_size or digest.hexdigest() != expected:
            raise ValueError("artifact_sha256_mismatch")
        artifact_id = f"a{uuid.uuid4().hex[:16]}"
        destination = workspace / f"{artifact_id}.bin"
        temporary.replace(destination)
        temporary = None
        destination.chmod(0o600)
        item = {
            "artifact_id": artifact_id,
            "stand": stand,
            "source_path": source,
            "filename": path_basename(source),
            "sha256": expected,
            "size_bytes": size,
            "path": str(destination),
        }
        job.setdefault("staged_artifacts", []).append(item)
        try:
            save_job(job)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        return {
            "status": "staged",
            "artifact_id": artifact_id,
            "filename": item["filename"],
            "sha256": expected,
            "size_bytes": size,
            "stand": stand,
        }
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        if sftp is not None:
            sftp.close()
        client.close()


def path_basename(source):
    return PurePosixPath(source).name


def get_verified_staged_artifact(job_id, artifact_id):
    """Internal only: resolve an artifact ID, rehash it immediately before upload."""
    job = _job_for_current_user(job_id)
    matches = [
        item for item in job.get("staged_artifacts", [])
        if item.get("artifact_id") == artifact_id
    ]
    if len(matches) != 1:
        raise ValueError("staged_artifact_not_found")
    item = matches[0]
    root = _workspace(job_id).resolve()
    path = Path(item["path"])
    if path.is_symlink() or path.resolve().parent != root:
        raise ValueError("staged_artifact_path_invalid")
    if not path.is_file() or path.stat().st_size != item["size_bytes"]:
        raise ValueError("staged_artifact_missing_or_changed")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    if digest.hexdigest() != item["sha256"]:
        raise ValueError("staged_artifact_sha256_mismatch")
    return dict(item)
