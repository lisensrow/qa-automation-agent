import tempfile
from pathlib import Path

import job_store
from tools.browser import BrowserSession
from uqa import classify_tool_action


session = BrowserSession()

try:
    session._ensure_started()
    session.page.set_content(
        """
        <html lang="en"><body>
          <button>Save</button>
          <label for="kind">Kind</label>
          <select id="kind"><option>A</option></select>
          <table><tbody><tr><td>One</td></tr></tbody></table>
        </body></html>
        """
    )
    first = session.probe_capabilities()
    assert first.get("compatibility_status") == "compatible", first
    assert "html_table" in first["recommended_adapters"]["table"], first
    assert "native_select" in first["recommended_adapters"]["selection"], first
    assert len(first.get("contract_fingerprint") or "") == 64, first

    session.page.set_content(
        """
        <html lang="en"><body>
          <button>Save</button>
          <div role="grid" aria-label="Items">
            <div role="row"><div role="gridcell">One</div></div>
          </div>
          <label for="kind">Kind</label>
          <input id="kind" role="combobox" aria-label="Kind">
        </body></html>
        """
    )
    second = session.probe_capabilities()
    assert "aria_grid" in second["recommended_adapters"]["table"], second
    assert "aria_combobox" in second["recommended_adapters"]["selection"], (
        second
    )
    assert second["contract_fingerprint"] != first["contract_fingerprint"]

    assert classify_tool_action(
        "browser_probe_capabilities",
        {},
    ) == "observe"

    with tempfile.TemporaryDirectory() as temporary:
        original_jobs_dir = job_store.JOBS_DIR
        job_store.JOBS_DIR = Path(temporary)
        try:
            previous = job_store.create_job(
                "baseline",
                stand="compat.test",
            )
            baseline = job_store.record_compatibility_snapshot(
                previous["job_id"],
                "case-baseline",
                first,
            )
            assert baseline.get("changed") is False, baseline

            current = job_store.create_job(
                "current",
                stand="compat.test",
            )
            changed = job_store.record_compatibility_snapshot(
                current["job_id"],
                "case-current",
                second,
            )
            assert changed.get("changed") is True, changed
            assert changed.get("status") == "changed", changed
            assert "adapters" in changed.get(
                "changed_contract_sections",
                [],
            ), changed

            stored = job_store.get_job(current["job_id"])
            compatibility = stored.get("compatibility") or {}
            assert compatibility.get("current_fingerprint") == (
                second["contract_fingerprint"]
            )
            assert compatibility.get("last_snapshot_id") == (
                changed["snapshot_id"]
            )
        finally:
            job_store.JOBS_DIR = original_jobs_dir
finally:
    session.close()

print("compatibility layer smoke: PASS")
