from tools.browser import BrowserSession


session = BrowserSession()
try:
    session._ensure_started()
    session.page.set_content(
        '<div id="target" onclick="document.body.dataset.clicked=\'yes\'">'
        'Exact CI</div>'
    )
    refused = session.click_semantic("Exact CI", role="link")
    assert refused["error"] == "semantic_element_not_found", refused
    assert session.page.locator("body").get_attribute("data-clicked") is None

    inspected = session.inspect_semantic("Exact CI", role="link")
    assert inspected["semantic_role_fallback"] is True, inspected
    clicked = session.click_semantic("Exact CI", role="link")
    assert clicked["click_status"] == "executed", clicked
    assert clicked["role_hint_ignored_after_inspection"] is True, clicked
    assert session.page.locator("body").get_attribute("data-clicked") == "yes"

    session.page.set_content(
        '<div id="target" onclick="document.body.dataset.clicked=\'again\'">'
        'Exact CI</div>'
    )
    inspected_again = session.inspect_semantic("Exact CI", role="button")
    assert inspected_again["semantic_role_fallback"] is True, inspected_again
    changed_role = session.click_semantic(
        "Exact CI", role="link", container="Exact CI",
    )
    assert changed_role["click_status"] == "executed", changed_role
    assert changed_role["role_hint_ignored_after_inspection"] is True
    assert changed_role["self_container_hint_ignored_after_inspection"] is True
    assert session.page.locator("body").get_attribute("data-clicked") == "again"

    session.page.set_content('<div>Exact CI</div><div>Exact CI</div>')
    ambiguous = session.inspect_semantic("Exact CI", role="link")
    assert "ambiguous" in ambiguous["error"].lower(), ambiguous
    still_refused = session.click_semantic("Exact CI", role="link")
    assert still_refused["error"] == "semantic_element_not_found", still_refused
finally:
    session.close()

print("semantic role click fallback smoke: PASS")
