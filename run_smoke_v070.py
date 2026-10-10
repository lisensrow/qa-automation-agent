#!/opt/uqa/.venv/bin/python

import os
import py_compile
import subprocess
import sys
from pathlib import Path


ROOT = Path(os.getenv("UQA_SMOKE_ROOT", "/opt/uqa")).resolve()
SMOKE_DIR = ROOT / "smoke"
PRODUCTION_FILES = [
    ROOT / "uqa.py",
    ROOT / "job_store.py",
    ROOT / "tools" / "registry.py",
    ROOT / "tools" / "browser.py",
]
SMOKES = [
    "smoke_v069c_v070c.py",
    "smoke_ui_assertion_library.py",
    "smoke_navigation_guard.py",
    "smoke_managed_initial_browser_url.py",
    "smoke_managed_stand_origin.py",
    "smoke_regression_stand_lock.py",
    "smoke_planned_lifecycle_verdict.py",
    "smoke_exact_resource_name.py",
    "smoke_browser_field_matching.py",
    "smoke_form_controls.py",
    "smoke_advanced_form_controls.py",
    "smoke_temporal_controls.py",
    "smoke_slider_controls.py",
    "smoke_tree_controls.py",
    "smoke_popover_lifecycle.py",
    "smoke_dialog_notifications.py",
    "smoke_responsive_viewport.py",
    "smoke_accessibility_audit.py",
    "smoke_layout_visibility.py",
    "smoke_browser_health.py",
    "smoke_new_tab.py",
    "smoke_history_navigation.py",
    "smoke_iframe_inspection.py",
    "smoke_iframe_surface_change.py",
    "smoke_iframe_surface_click.py",
    "smoke_iframe_surface_key.py",
    "smoke_hover_tooltip.py",
    "smoke_native_dialog.py",
    "smoke_form_validation.py",
    "smoke_loading_state.py",
    "smoke_notification_lifecycle.py",
    "smoke_aria_field_errors.py",
    "smoke_control_state_lifecycle.py",
    "smoke_form_dirty_state.py",
    "smoke_tabs_contract.py",
    "smoke_disclosure_contract.py",
    "smoke_dialog_focus_trap.py",
    "smoke_heading_structure.py",
    "smoke_landmark_structure.py",
    "smoke_link_contracts.py",
    "smoke_combobox_contract.py",
    "smoke_listbox_contract.py",
    "smoke_menu_contract.py",
    "smoke_progressbar_contract.py",
    "smoke_meter_contract.py",
    "smoke_spinbutton_contract.py",
    "smoke_text_contrast.py",
    "smoke_text_clipping.py",
    "smoke_target_size.py",
    "smoke_live_region_contract.py",
    "smoke_dialog_contract.py",
    "smoke_field_label_contract.py",
    "smoke_document_metadata.py",
    "smoke_keyboard_shortcuts.py",
    "smoke_autofill_contract.py",
    "smoke_form_submission_contract.py",
    "smoke_script_security.py",
    "smoke_media_resource.py",
    "smoke_lazy_media_contract.py",
    "smoke_font_readiness.py",
    "smoke_reduced_motion_contract.py",
    "smoke_details_contract.py",
    "smoke_popover_api_contract.py",
    "smoke_native_dialog_element.py",
    "smoke_fieldset_contract.py",
    "smoke_radio_group_contract.py",
    "smoke_button_type_contract.py",
    "smoke_contenteditable_contract.py",
    "smoke_search_contract.py",
    "smoke_breadcrumb_contract.py",
    "smoke_table_structure_contract.py",
    "smoke_list_structure_contract.py",
    "smoke_description_list_contract.py",
    "smoke_hash_link_contract.py",
    "smoke_navigation_current_contract.py",
    "smoke_skip_link_contract.py",
    "smoke_required_field_contract.py",
    "smoke_describedby_contract.py",
    "smoke_invalid_field_contract.py",
    "smoke_text_length_contract.py",
    "smoke_range_constraint_contract.py",
    "smoke_inputmode_contract.py",
    "smoke_new_tab_link_contract.py",
    "smoke_iframe_contract.py",
    "smoke_referrerpolicy_contract.py",
    "smoke_tabindex_contract.py",
    "smoke_disabled_control_contract.py",
    "smoke_readonly_contract.py",
    "smoke_aria_controls_contract.py",
    "smoke_aria_labelledby_contract.py",
    "smoke_aria_owns_contract.py",
    "smoke_checkbox_contract.py",
    "smoke_switch_contract.py",
    "smoke_toggle_button_contract.py",
    "smoke_expanded_contract.py",
    "smoke_haspopup_contract.py",
    "smoke_activedescendant_contract.py",
    "smoke_set_position_contract.py",
    "smoke_virtual_grid_contract.py",
    "smoke_aria_level_contract.py",
    "smoke_svg_accessibility_contract.py",
    "smoke_canvas_fallback_contract.py",
    "smoke_media_caption_contract.py",
    "smoke_language_contract.py",
    "smoke_direction_contract.py",
    "smoke_time_contract.py",
    "smoke_canonical_url_contract.py",
    "smoke_alternate_language_contract.py",
    "smoke_base_url_contract.py",
    "smoke_tool_registry_integrity.py",
    "smoke_private_clipboard_clear.py",
    "smoke_network_detail_redaction.py",
    "smoke_frontend_benchmark_manifest.py",
    "smoke_uconnect_manual_frontend_manifest.py",
    "smoke_calendar_overlay.py",
    "smoke_time_picker_overlay.py",
    "smoke_dialog_wizard.py",
    "smoke_aria_multiselect_chips.py",
    "smoke_keyboard_focus.py",
    "smoke_keyboard_chords_clipboard.py",
    "smoke_drag_resize.py",
    "smoke_drag_persisted_order.py",
    "smoke_table_controls.py",
    "smoke_table_filters_bulk.py",
    "smoke_table_popover_totals.py",
    "smoke_cross_page_selection.py",
    "smoke_compatibility_layer.py",
    "smoke_compatibility_guard.py",
    "smoke_labeled_field_fallback.py",
    "smoke_browser_navigation_labels.py",
    "smoke_browser_container_scope.py",
    "smoke_saved_web_auth.py",
    "smoke_cleanup_navigation_context.py",
    "smoke_cleanup_parent_expand.py",
    "smoke_cleanup_rest_fallback.py",
    "smoke_product_blockers.py",
    "smoke_product_version_recheck.py",
    "smoke_model_tool_context.py",
]


for path in PRODUCTION_FILES:
    py_compile.compile(str(path), doraise=True)

environment = os.environ.copy()
environment["UQA_SMOKE_ROOT"] = str(ROOT)
environment["PYTHONPATH"] = str(ROOT)

failures = []

for name in SMOKES:
    path = SMOKE_DIR / name
    completed = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
    )
    output = "\n".join(
        part.strip()
        for part in (completed.stdout, completed.stderr)
        if part.strip()
    )

    if completed.returncode == 0:
        print(f"PASS {name}: {output}")
    else:
        failures.append(name)
        print(f"FAIL {name}: {output}")

if failures:
    raise SystemExit(
        "smoke suite failed: " + ", ".join(failures)
    )

print(f"smoke_v070_suite: PASS ({len(SMOKES)} tests)")
