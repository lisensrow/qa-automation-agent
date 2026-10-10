from tools.browser import BrowserSession
from uqa import _core_observation_call_key, classify_tool_action


class FakePage:
    def __init__(self, before_url, after_url, identity):
        self.url = before_url
        self.after_url = after_url
        self.identity = identity
        self.evaluate_count = 0

    def wait_for_timeout(self, _milliseconds):
        self.url = self.after_url

    def evaluate(self, _script, _wanted):
        if isinstance(self.identity, list):
            index = min(self.evaluate_count, len(self.identity) - 1)
            value = self.identity[index]
            self.evaluate_count += 1
            return dict(value)
        return dict(self.identity)


def make_session(before_url, after_url, identity):
    session = BrowserSession.__new__(BrowserSession)
    session.page = FakePage(before_url, after_url, identity)
    session._ensure_started = lambda: None
    session.inspect_table_row = lambda name, exact=True: {
        "row_match_count": 1,
        "current_url": before_url,
        "semantic_name": name,
    }
    session.click_semantic = lambda name, exact=True, role=None: {
        "click_status": "executed",
        "current_url": after_url,
        "semantic_name": name,
        "semantic_role": role,
    }
    session._capture_state = lambda label: {
        "current_url": session.page.url,
        "capture_label": label,
    }
    return session


assert classify_tool_action(
    "browser_open_exact_table_row_details_semantic", {"name": "Exact row"}
) == "interact"
assert _core_observation_call_key(
    "browser_open_exact_table_row_details_semantic", {"name": " Exact  row "}
) == ("browser_open_exact_table_row_details_semantic", "exact row")

heading_session = make_session(
    "https://stand.example.test/items",
    "https://stand.example.test/items/one",
    {
        "anchor_types": ["h1"],
        "anchor_match_count": 1,
        "exact_visible_count": 2,
        "document_title_match": False,
    },
)
heading_result = heading_session.open_exact_table_row_details_semantic("Exact row")
assert heading_result["details_identity_passed"] is True
assert heading_result["details_identity_status"] == "verified"
assert heading_result["observation_result"] == "PASS"
assert heading_result["mutation_executed"] is False
assert heading_result["url_changed"] is True

transition_session = make_session(
    "https://stand.example.test/items",
    "https://stand.example.test/items/one",
    {
        "anchor_types": [],
        "anchor_match_count": 0,
        "exact_visible_count": 1,
        "document_title_match": False,
    },
)
assert transition_session.open_exact_table_row_details_semantic(
    "Exact row"
)["details_identity_passed"] is True

drawer_session = make_session(
    "https://stand.example.test/items",
    "https://stand.example.test/items",
    [
        {
            "anchor_types": [],
            "anchor_match_count": 0,
            "exact_visible_count": 1,
            "document_title_match": False,
        },
        {
            "anchor_types": [],
            "anchor_match_count": 0,
            "exact_visible_count": 2,
            "document_title_match": False,
        },
    ],
)
drawer_result = drawer_session.open_exact_table_row_details_semantic("Exact row")
assert drawer_result["details_identity_passed"] is True
assert drawer_result["url_changed"] is False
assert drawer_result["exact_visible_count_increased"] is True

unproven_session = make_session(
    "https://stand.example.test/items",
    "https://stand.example.test/items",
    {
        "anchor_types": [],
        "anchor_match_count": 0,
        "exact_visible_count": 4,
        "document_title_match": False,
    },
)
unproven = unproven_session.open_exact_table_row_details_semantic("Exact row")
assert unproven["error"] == "details_identity_not_confirmed"
assert unproven["details_identity_passed"] is False

cross_origin_session = make_session(
    "https://stand.example.test/items",
    "https://other.example.test/items/one",
    {
        "anchor_types": ["h1"],
        "anchor_match_count": 1,
        "exact_visible_count": 1,
        "document_title_match": False,
    },
)
cross_origin = cross_origin_session.open_exact_table_row_details_semantic(
    "Exact row"
)
assert cross_origin["error"] == "details_origin_mismatch"
assert cross_origin["executed"] is False

not_unique = make_session(
    "https://stand.example.test/items",
    "https://stand.example.test/items/one",
    {},
)
not_unique.inspect_table_row = lambda name, exact=True: {
    "error": "ambiguous_table_row",
    "row_match_count": 2,
}
blocked = not_unique.open_exact_table_row_details_semantic("Exact row")
assert blocked["error"] == "ambiguous_table_row"
assert blocked["executed"] is False

print("exact table-row details workflow smoke: PASS")
