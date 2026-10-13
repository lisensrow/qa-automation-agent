from tools.browser import BrowserSession

class Root:
    def __init__(self, names, visible=True):
        self.names, self.visible = names, visible
    def is_visible(self):
        return self.visible
    def evaluate(self, script, argument=None):
        if argument is not None:
            assert "closest" in script and "tablist" in script
            return argument in self.names
        assert "const owned=" in script and "closest" in script
        return {"tabs": [{"label": self.names[0], "selected": True,
                          "controls": "panel", "panel_exists": True, "panel_visible": True}],
                "selected_count": 1, "tabs_contract_passed": True}
class Roots:
    def __init__(self, roots):
        self.roots = roots
    def count(self):
        return len(self.roots)
    def nth(self, index):
        return self.roots[index]
class Page:
    def __init__(self, roots):
        self.roots = roots
    def get_by_role(self, role, **kwargs):
        assert role == "tablist"
        return Roots(self.roots)
def session(roots):
    result = BrowserSession.__new__(BrowserSession)
    result.page = Page(roots)
    result._ensure_started = result._reset_diagnostics = lambda: None
    result._capture_state = lambda _: {}
    return result

outer, inner = Root(["Agent", "Monitoring"]), Root(["Tasks", "Plugins"])
browser = session([outer, inner])
assert browser.inspect_tabs_contract_semantic()["error"] == "tablist_not_unique"
audit = browser.inspect_tabs_contract_semantic(_target_tab_name="Agent")
assert audit["tabs_audit"]["tabs"][0]["label"] == "Agent"
assert browser.inspect_tabs_contract_semantic(_target_tab_name="Missing")["matches"] == 0
duplicate = session([outer, Root(["Agent"])])
assert duplicate.inspect_tabs_contract_semantic(_target_tab_name="Agent")["matches"] == 2
hidden = session([outer, Root(["Agent"], visible=False)])
assert "error" not in hidden.inspect_tabs_contract_semantic(_target_tab_name="Agent")
print("semantic tablist scope: PASS (fixtures only)")
