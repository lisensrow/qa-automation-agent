from tools.browser import BrowserSession
from uqa import _core_observation_call_key, classify_tool_action


class FakePage:
    def __init__(self, url="https://stand.example.test/items"):
        self.url = url
        self.identity = {"anchor_match_count": 1, "exact_visible_count": 2, "outside_row_match_count": 1}

    def wait_for_timeout(self, _milliseconds):
        return None

    def evaluate(self, _script, _name):
        return dict(self.identity)


def make_session(selected_by_tab, after_url=None, after_identity=None):
    session = BrowserSession.__new__(BrowserSession)
    session.page = FakePage()
    session._ensure_started = lambda: None
    session.inspect_table_row = lambda name, exact=True: {"row_match_count": 1}
    session.open_exact_table_row_details_semantic = lambda name: {
        "details_identity_passed": True, "row_match_count": 1, "name": name,
    }
    session.inspect_semantic = lambda name, exact=True, role=None: {
        "inspection_status": "observed", "semantic_name": name, "role": role,
    }
    def click(name, exact=True, role=None):
        session.current_tab = name
        if after_url:
            session.page.url = after_url
        if after_identity is not None:
            session.page.identity = after_identity
        return {"click_status": "executed", "semantic_role": role}
    session.click_semantic = click
    def inspect_tabs(_tablist=None, exact=True, _target_tab_name=None):
        selected = selected_by_tab.get(session.current_tab, session.current_tab)
        return {"tabs_audit": {"selected_count": 1, "tabs_contract_passed": True,
            "tabs": [{"label": selected, "selected": True, "controls": "panel-current",
                      "panel_exists": True, "panel_visible": True}]}}
    session.inspect_tabs_contract_semantic = inspect_tabs
    session._capture_state = lambda label: {"current_url": session.page.url, "capture_label": label}
    return session

assert classify_tool_action("browser_verify_exact_table_row_tabs_semantic",
                            {"name": "Exact row", "tabs": ["Summary", "OS"]}) == "interact"
assert _core_observation_call_key("browser_verify_exact_table_row_tabs_semantic",
                                  {"name": " Exact row ", "tabs": ["Summary"]}) == (
                                      "browser_verify_exact_table_row_tabs_semantic", "exact row")
passed = make_session({}).verify_exact_table_row_tabs_semantic("Exact row", ["Summary", "OS"])
assert passed["tabs_workflow_passed"] is True and passed["observation_result"] == "PASS"
assert passed["verified_tab_count"] == 2 and all(item["passed"] for item in passed["tabs_verified"])
assert passed["details_identity_preserved"] is True
repeated_name = make_session({}, after_identity={"anchor_match_count": 0, "exact_visible_count": 2,
                                                "outside_row_match_count": 1})
repeated_name.page.identity = {"anchor_match_count": 0, "exact_visible_count": 3, "outside_row_match_count": 2}
repeated_name = repeated_name.verify_exact_table_row_tabs_semantic("Exact row", ["OS"])
assert repeated_name["details_identity_preserved"] is True  # tab content may remove redundant name fields
mismatch = make_session({"OS": "Summary"}).verify_exact_table_row_tabs_semantic("Exact row", ["OS"])
assert mismatch["error"] == "selected_tab_panel_mismatch" and mismatch["observation_result"] == "BLOCKED"
cross_origin = make_session({}, after_url="https://other.example.test/items").verify_exact_table_row_tabs_semantic(
    "Exact row", ["Summary"])
assert cross_origin["error"] == "tab_navigation_origin_mismatch"
invalid = make_session({}).verify_exact_table_row_tabs_semantic("Exact row", ["Summary", "summary"])
assert invalid["error"] == "requested_tabs_not_unique" and invalid["executed"] is False
lost = make_session({}, after_identity={"anchor_match_count": 0, "exact_visible_count": 1})
lost = lost.verify_exact_table_row_tabs_semantic("Exact row", ["OS"])
assert lost["error"] == "selected_tab_panel_mismatch"
assert lost["tabs_verified"][0]["details_identity_preserved"] is False
unknown = make_session({})
unknown.page.identity = {"anchor_match_count": 0, "exact_visible_count": 1}
unknown = unknown.verify_exact_table_row_tabs_semantic("Exact row", ["OS"])
assert unknown["error"] == "tab_details_identity_baseline_missing"
already_open = make_session({})
already_open.open_exact_table_row_details_semantic = lambda name: (_ for _ in ()).throw(
    AssertionError("already-open details must not be clicked again"))
assert already_open.verify_exact_table_row_tabs_semantic("Exact row", ["OS"])["observation_result"] == "PASS"
duplicate = make_session({})
duplicate.inspect_table_row = lambda name, exact=True: {"row_match_count": 2}
assert duplicate.verify_exact_table_row_tabs_semantic("Exact row", ["OS"])["error"] == "table_row_not_unique"
print("exact table-row tabs workflow smoke: PASS")
