from pathlib import Path
from tempfile import TemporaryDirectory

import job_store
import uqa


with TemporaryDirectory() as temporary_directory:
    original_jobs_dir = job_store.JOBS_DIR
    job_store.JOBS_DIR = Path(temporary_directory)

    try:
        job = job_store.create_job(
            "Edit one disposable frontend fixture",
            job_type="regression",
        )
        case = job_store.add_test_case(
            job["job_id"],
            "Edit and persist a disposable frontend fixture",
        )
        resource = job_store.add_test_resource(
            job_id=job["job_id"],
            resource_type="record",
            name="uqa-disposable-fixture",
            created_by_case=case["case_id"],
            cleanup_required=True,
            metadata={
                "disposable": True,
                "cleanup_contract": "registered_resource_cleanup_required",
                "allowed_edit_fields": ["description"],
                "allowed_edit_values": {
                    "description": ["safe fixture value"],
                },
                "password": "must-not-survive",
            },
        )

        authorized = job_store.authorize_test_resource_edit(
            job["job_id"],
            resource["resource_id"],
            "description",
            "safe fixture value",
        )
        assert authorized["edit_authorized"] is True, authorized
        assert authorized["status"] == "authorized", authorized
        assert authorized["owned_by_job"] is True, authorized
        assert "allowed_edit_values" not in authorized, authorized
        assert "safe fixture value" not in str(authorized), authorized
        assert "must-not-survive" not in str(authorized), authorized

        wrong_value = job_store.authorize_test_resource_edit(
            job["job_id"],
            resource["resource_id"],
            "description",
            "unapproved value",
        )
        assert wrong_value["edit_authorized"] is False, wrong_value
        assert wrong_value["reason"] == "edit_value_not_allowed", wrong_value

        wrong_field = job_store.authorize_test_resource_edit(
            job["job_id"],
            resource["resource_id"],
            "name",
            "safe fixture value",
        )
        assert wrong_field["edit_authorized"] is False, wrong_field
        assert wrong_field["reason"] == "edit_field_not_allowed", wrong_field

        missing = job_store.authorize_test_resource_edit(
            job["job_id"],
            "res-missing",
            "description",
            "safe fixture value",
        )
        assert missing["reason"] == "resource_not_found", missing

        non_disposable = job_store.add_test_resource(
            job_id=job["job_id"],
            resource_type="record",
            name="ordinary-record",
            created_by_case=case["case_id"],
            cleanup_required=True,
            metadata={
                "cleanup_contract": "registered_resource_cleanup_required",
                "allowed_edit_fields": ["description"],
                "allowed_edit_values": {
                    "description": ["safe fixture value"],
                },
            },
        )
        denied = job_store.authorize_test_resource_edit(
            job["job_id"],
            non_disposable["resource_id"],
            "description",
            "safe fixture value",
        )
        assert denied["reason"] == "resource_not_disposable", denied

        no_cleanup_contract = job_store.add_test_resource(
            job_id=job["job_id"],
            resource_type="record",
            name="fixture-without-cleanup-contract",
            created_by_case=case["case_id"],
            cleanup_required=True,
            metadata={
                "disposable": True,
                "allowed_edit_fields": ["description"],
                "allowed_edit_values": {
                    "description": ["safe fixture value"],
                },
            },
        )
        denied = job_store.authorize_test_resource_edit(
            job["job_id"],
            no_cleanup_contract["resource_id"],
            "description",
            "safe fixture value",
        )
        assert denied["reason"] == "cleanup_contract_missing", denied

        result = uqa.execute_resource_tool(
            "resource_assert_edit_scope",
            {
                "resource_id": resource["resource_id"],
                "field": "description",
                "value": "safe fixture value",
            },
            job["job_id"],
            case["case_id"],
        )
        assert result["status"] == "ok", result
        assert result["executed"] is False, result
        assert result["bookkeeping_only"] is True, result
        assert result["product_evidence"] is False, result
        assert result["authorization"]["edit_authorized"] is True, result
        assert uqa.classify_tool_action(
            "resource_assert_edit_scope", {}
        ) == "observe"
    finally:
        job_store.JOBS_DIR = original_jobs_dir


print("RESOURCE EDIT SCOPE SMOKE OK")
