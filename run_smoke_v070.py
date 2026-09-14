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
    "smoke_navigation_guard.py",
    "smoke_regression_stand_lock.py",
    "smoke_planned_lifecycle_verdict.py",
    "smoke_exact_resource_name.py",
    "smoke_browser_field_matching.py",
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
