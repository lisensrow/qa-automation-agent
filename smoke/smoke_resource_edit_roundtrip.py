from pathlib import Path
from tempfile import TemporaryDirectory

import job_store
import uqa
from tools.browser import BrowserSession


def install_fixture(session, corrupt_unrelated=False):
    corrupt = (
        "localStorage.setItem('fixture-owner', 'changed');"
        if corrupt_unrelated
        else ""
    )
    html = f"""
      <!doctype html><html><body>
      <form aria-label="Fixture editor">
        <label>Description
          <input id="description" name="description"
                 value="before fixture value">
        </label>
        <label>Owner
          <input id="owner" name="owner" value="qa-owner">
        </label>
        <button type="submit">Save</button>
      </form>
      <script>
        const saved = localStorage.getItem('fixture-description');
        if (saved !== null) document.querySelector('#description').value = saved;
        const savedOwner = localStorage.getItem('fixture-owner');
        if (savedOwner !== null) document.querySelector('#owner').value = savedOwner;
        document.querySelector('form').addEventListener('submit', event => {{
          event.preventDefault();
          localStorage.setItem(
            'fixture-description',
            document.querySelector('#description').value
          );
          {corrupt}
        }});
      </script>
      </body></html>
    """
    session.page.route(
        "https://fixture.test/editor",
        lambda route: route.fulfill(status=200, content_type="text/html", body=html),
    )
    session.page.goto("https://fixture.test/editor")


session = BrowserSession()
try:
    session._ensure_started()
    install_fixture(session)
    passed = session.edit_form_field_roundtrip_semantic(
        "Fixture editor",
        "Description",
        "safe fixture value",
        "Save",
    )
    assert passed["edit_roundtrip_passed"] is True, passed
    assert passed["form_dirty"] is True, passed
    assert passed["save_clicked"] is True, passed
    assert passed["value_persisted"] is True, passed
    assert passed["unrelated_fields_unchanged"] is True, passed
    assert passed["unrelated_field_count"] == 1, passed
    assert "safe fixture value" not in str(passed), passed
finally:
    session.close()


session = BrowserSession()
try:
    session._ensure_started()
    install_fixture(session, corrupt_unrelated=True)
    blocked = session.edit_form_field_roundtrip_semantic(
        "Fixture editor",
        "Description",
        "safe fixture value",
        "Save",
    )
    assert blocked["edit_roundtrip_passed"] is False, blocked
    assert blocked["value_persisted"] is True, blocked
    assert blocked["unrelated_fields_unchanged"] is False, blocked
    assert blocked["observation_result"] == "BLOCKED", blocked
finally:
    session.close()


with TemporaryDirectory() as temporary_directory:
    original_jobs_dir = job_store.JOBS_DIR
    original_browser_workflow = uqa.edit_form_field_roundtrip_semantic
    job_store.JOBS_DIR = Path(temporary_directory)
    browser_calls = []
    uqa.edit_form_field_roundtrip_semantic = lambda **arguments: (
        browser_calls.append(arguments)
        or {
            "status": "verified",
            "executed": True,
            "mutation_executed": True,
            "edit_roundtrip_passed": True,
            "observation_result": "PASS",
        }
    )
    try:
        job = job_store.create_job("fixture edit", job_type="regression")
        case = job_store.add_test_case(job["job_id"], "fixture edit")
        resource = job_store.add_test_resource(
            job["job_id"],
            "record",
            name="owned-fixture",
            created_by_case=case["case_id"],
            cleanup_required=True,
            metadata={
                "disposable": True,
                "cleanup_contract": "registered_resource_cleanup_required",
                "allowed_edit_fields": ["Description"],
                "allowed_edit_values": {
                    "Description": ["safe fixture value"],
                },
            },
        )
        arguments = {
            "resource_id": resource["resource_id"],
            "form": "Fixture editor",
            "field": "Description",
            "value": "safe fixture value",
            "save_button": "Save",
        }
        result = uqa.execute_resource_tool(
            "browser_edit_owned_resource_roundtrip_semantic",
            arguments,
            job["job_id"],
            case["case_id"],
        )
        assert result["edit_roundtrip_passed"] is True, result
        assert result["authorization"]["edit_authorized"] is True, result
        assert len(browser_calls) == 1, browser_calls
        assert uqa.classify_tool_action(
            "browser_edit_owned_resource_roundtrip_semantic", arguments,
        ) == "write"

        denied_arguments = dict(arguments, value="not allowlisted")
        denied = uqa.execute_resource_tool(
            "browser_edit_owned_resource_roundtrip_semantic",
            denied_arguments,
            job["job_id"],
            case["case_id"],
        )
        assert denied["executed"] is False, denied
        assert denied["error"] == "resource_edit_scope_denied", denied
        assert len(browser_calls) == 1, browser_calls
    finally:
        uqa.edit_form_field_roundtrip_semantic = original_browser_workflow
        job_store.JOBS_DIR = original_jobs_dir


print("resource edit roundtrip smoke: PASS")
