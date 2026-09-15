import tempfile
from pathlib import Path

import job_store
import uqa
from tools.browser import BrowserSession


original_jobs_dir = job_store.JOBS_DIR
session = BrowserSession()

try:
    with tempfile.TemporaryDirectory(prefix="uqa-selection-ledger-") as temp:
        job_store.JOBS_DIR = Path(temp)
        job = job_store.create_job("Select Alpha and Gamma across pages")
        case = job_store.add_test_case(job["job_id"], "Cross-page selection")
        job_id = job["job_id"]
        case_id = case["case_id"]

        session._ensure_started()
        session.page.set_content(
            """
            <html><body>
              <table aria-label="Other">
                <tbody><tr><td><input type="checkbox"></td><td>Alpha</td></tr></tbody>
              </table>
              <table aria-label="Assets">
                <thead><tr><th>Select</th><th>Name</th></tr></thead>
                <tbody id="asset-rows">
                  <tr><td><input type="checkbox"></td><td>Alpha</td></tr>
                  <tr><td><input type="checkbox"></td><td>Beta</td></tr>
                </tbody>
              </table>
              <button id="bulk" onclick="window.bulkClicks += 1">Archive selected</button>
              <script>window.bulkClicks = 0;</script>
            </body></html>
            """
        )

        alpha = session.set_table_row_selected(
            "Alpha", True, table="Assets"
        )
        assert alpha.get("row_selection_status") == "selected", alpha
        assert alpha.get("table_name") == "Assets", alpha
        assert alpha.get("table_row_key", "").startswith("row-"), alpha
        uqa.record_tool_observations(
            job_id,
            case_id,
            "browser_set_table_row_selected",
            {"name": "Alpha", "selected": True, "table": "Assets"},
            alpha,
        )
        assert alpha.get("cross_page_selected_rows") == ["Alpha"], alpha

        session.page.locator("#asset-rows").evaluate(
            """
            body => body.innerHTML =
              '<tr><td><input type="checkbox"></td><td>Gamma</td></tr>' +
              '<tr><td><input type="checkbox"></td><td>Delta</td></tr>'
            """
        )
        gamma = session.set_table_row_selected(
            "Gamma", True, table="Assets"
        )
        assert gamma.get("table_selection_key") == (
            alpha.get("table_selection_key")
        ), gamma
        assert gamma.get("table_page_signature") != (
            alpha.get("table_page_signature")
        ), gamma
        assert gamma.get("table_row_key") != alpha.get("table_row_key"), gamma
        uqa.record_tool_observations(
            job_id,
            case_id,
            "browser_set_table_row_selected",
            {"name": "Gamma", "selected": True, "table": "Assets"},
            gamma,
        )
        assert gamma.get("cross_page_selected_rows") == [
            "Alpha", "Gamma"
        ], gamma
        assert gamma.get("cross_page_selected_count") == 2, gamma
        assert len(gamma.get("cross_page_selected_entries") or []) == 2, gamma
        assert gamma.get("bulk_action_authorized") is False, gamma

        listed = uqa.execute_resource_tool(
            "table_selection_list",
            {
                "table_selection_key": gamma["table_selection_key"],
                "selected_only": True,
            },
            job_id,
            case_id,
        )
        assert listed.get("count") == 2, listed
        assert listed.get("bookkeeping_only") is True, listed
        assert listed.get("bulk_action_authorized") is False, listed

        session.page.locator("#asset-rows").evaluate(
            """
            body => body.innerHTML =
              '<tr><td><input type="checkbox" checked></td><td>Alpha</td></tr>' +
              '<tr><td><input type="checkbox"></td><td>Beta</td></tr>'
            """
        )
        alpha_off = session.set_table_row_selected(
            "Alpha", False, table="Assets"
        )
        assert alpha_off.get("row_selection_status") == "deselected", alpha_off
        uqa.record_tool_observations(
            job_id,
            case_id,
            "browser_set_table_row_selected",
            {"name": "Alpha", "selected": False, "table": "Assets"},
            alpha_off,
        )
        assert alpha_off.get("cross_page_selected_rows") == ["Gamma"], alpha_off
        assert session.page.evaluate("window.bulkClicks") == 0
        assert uqa.classify_tool_action("table_selection_list", {}) == "observe"
finally:
    session.close()
    job_store.JOBS_DIR = original_jobs_dir

print("cross-page selection ledger smoke: PASS")
