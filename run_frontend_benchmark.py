import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(os.getenv("UQA_SMOKE_ROOT", "/opt/uqa")).resolve()
SMOKE = ROOT / "smoke"

BENCHMARK = {
    "forms": [
        "smoke_form_controls.py", "smoke_advanced_form_controls.py",
        "smoke_form_validation.py", "smoke_field_label_contract.py",
        "smoke_form_dirty_state.py",
    ],
    "navigation": [
        "smoke_tabs_contract.py", "smoke_disclosure_contract.py",
        "smoke_breadcrumb_contract.py", "smoke_hash_link_contract.py",
        "smoke_skip_link_contract.py",
    ],
    "data_views": [
        "smoke_table_controls.py", "smoke_table_filters_bulk.py",
        "smoke_virtual_grid_contract.py", "smoke_list_structure_contract.py",
        "smoke_description_list_contract.py",
    ],
    "overlays": [
        "smoke_dialog_notifications.py", "smoke_popover_lifecycle.py",
        "smoke_calendar_overlay.py", "smoke_time_picker_overlay.py",
        "smoke_dialog_wizard.py",
    ],
    "keyboard_interaction": [
        "smoke_keyboard_focus.py", "smoke_keyboard_chords_clipboard.py",
        "smoke_keyboard_shortcuts.py", "smoke_drag_resize.py",
        "smoke_control_state_lifecycle.py",
    ],
    "accessibility": [
        "smoke_accessibility_audit.py", "smoke_heading_structure.py",
        "smoke_landmark_structure.py", "smoke_text_contrast.py",
        "smoke_target_size.py",
    ],
    "responsive_health": [
        "smoke_responsive_viewport.py", "smoke_layout_visibility.py",
        "smoke_loading_state.py", "smoke_browser_health.py",
        "smoke_reduced_motion_contract.py",
    ],
    "non_text_document": [
        "smoke_media_resource.py", "smoke_svg_accessibility_contract.py",
        "smoke_canvas_fallback_contract.py", "smoke_media_caption_contract.py",
        "smoke_document_metadata.py",
    ],
}


def validate_manifest():
    names = [name for cases in BENCHMARK.values() for name in cases]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    missing = sorted(name for name in names if not (SMOKE / name).is_file())
    if duplicates or missing:
        raise SystemExit(json.dumps({"duplicates": duplicates, "missing": missing}))
    return names


def main():
    validate_manifest()
    environment = os.environ.copy()
    environment["UQA_SMOKE_ROOT"] = str(ROOT)
    environment["PYTHONPATH"] = str(ROOT)
    category_results = {}
    failures = []
    for category, cases in BENCHMARK.items():
        passed = 0
        case_results = []
        for name in cases:
            completed = subprocess.run(
                [sys.executable, str(SMOKE / name)], cwd=ROOT,
                env=environment, text=True, capture_output=True,
            )
            ok = completed.returncode == 0
            passed += int(ok)
            case_results.append({"name": name, "passed": ok})
            if not ok:
                failures.append(name)
        category_results[category] = {
            "passed": passed, "total": len(cases),
            "percent": round(100 * passed / len(cases), 1),
            "cases": case_results,
        }
        print(f"{category}: {passed}/{len(cases)}")
    total = sum(item["total"] for item in category_results.values())
    passed = sum(item["passed"] for item in category_results.values())
    summary = {
        "passed": passed, "total": total,
        "percent": round(100 * passed / total, 1),
        "categories": category_results, "failures": failures,
    }
    print("FRONTEND_BENCHMARK_JSON=" + json.dumps(summary, ensure_ascii=False))
    if failures:
        raise SystemExit(1)
    print(f"frontend benchmark: PASS ({passed}/{total}, {summary['percent']}%)")


if __name__ == "__main__":
    main()
