#!/opt/uqa/.venv/bin/python

import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

if len(sys.argv) != 2:
    print("Usage: browser_smoke.py <URL>")
    sys.exit(1)

url = sys.argv[1]

artifact_dir = Path("/opt/uqa/artifacts")
artifact_dir.mkdir(parents=True, exist_ok=True)

screenshot = artifact_dir / "smoke.png"

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True
    )

    context = browser.new_context(
        ignore_https_errors=True,
        viewport={"width": 1920, "height": 1080}
    )

    page = context.new_page()

    print(f"[UQA] Opening: {url}")

    response = page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=30000
    )

    print(f"[UQA] HTTP: {response.status if response else 'no response'}")
    print(f"[UQA] Final URL: {page.url}")
    print(f"[UQA] Title: {page.title()}")

    page.screenshot(
        path=str(screenshot),
        full_page=True
    )

    print(f"[UQA] Screenshot: {screenshot}")

    browser.close()
