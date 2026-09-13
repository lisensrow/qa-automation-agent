import ast
import os
import re
import sys
import types
from pathlib import Path
from urllib.parse import urlsplit


root = Path(os.getenv("UQA_SMOKE_ROOT", "."))
browser_path = (
    root / "tools" / "browser.py"
    if (root / "tools" / "browser.py").exists()
    else root / "browser.py"
)
registry_path = (
    root / "tools" / "registry.py"
    if (root / "tools" / "registry.py").exists()
    else root / "registry.py"
)
browser_source = browser_path.read_text(encoding="utf-8")
browser_tree = ast.parse(browser_source)
browser_class = next(
    node
    for node in browser_tree.body
    if isinstance(node, ast.ClassDef)
    and node.name == "BrowserSession"
)
method = next(
    node
    for node in browser_class.body
    if isinstance(node, ast.FunctionDef)
    and node.name == "authenticate_saved_stand"
)
scope = {
    "os": os,
    "re": re,
    "urlsplit": urlsplit,
}
exec(
    compile(ast.Module(body=[method], type_ignores=[]), "browser.py", "exec"),
    scope,
)


class Control:
    def __init__(self, page, kind):
        self.page = page
        self.kind = kind
        self.filled = None

    def is_visible(self):
        return not self.page.authenticated

    def fill(self, value):
        self.filled = value

    def click(self, timeout=None, no_wait_after=None):
        assert timeout == 10000
        assert no_wait_after is True
        self.page.authenticated = True


class Locator:
    def __init__(self, control):
        self.control = control

    def count(self):
        return 1

    def nth(self, index):
        assert index == 0
        return self.control


class Page:
    def __init__(self):
        self.url = "https://uc.lab.local/administration/access-zones"
        self.authenticated = False
        self.user = Control(self, "user")
        self.password = Control(self, "password")
        self.button = Control(self, "button")

    def locator(self, selector):
        if selector == 'input[type="password"]':
            return Locator(self.password)
        return Locator(self.user)

    def get_by_role(self, role, name=None):
        assert role == "button"
        assert name.search("Sign in")
        return Locator(self.button)

    def wait_for_load_state(self, *args, **kwargs):
        return None

    def wait_for_function(self, expression, timeout=None):
        assert "passwordVisible" in expression
        assert "signInVisible" in expression
        assert timeout == 15000
        return None

    def wait_for_timeout(self, value):
        assert value == 500


class Session:
    def __init__(self):
        self.page = Page()

    def _ensure_started(self):
        return None

    def _reset_diagnostics(self):
        return None

    def _begin_action_execution(self):
        return "a1"

    def _capture_state(self, action):
        return {"action": action, "current_url": self.page.url}

    def _finish_action_execution(self, result):
        result["finished"] = True
        return result


stands = types.ModuleType("stands")
stands.get_stand = lambda stand, include_password=False: {
    "web_url": "https://uc.lab.local",
    "ssh_username": "test-user",
    "ssh_password": "test-secret",
}
sys.modules["stands"] = stands
os.environ["UQA_USE_SSH_CREDS_FOR_WEB"] = "1"

session = Session()
result = scope["authenticate_saved_stand"](session, "uc.lab.local")
assert result["success"] is True
assert result["authentication_status"] == "authenticated"
assert result["credential_source"] == "encrypted_stand_store"
assert "test-secret" not in str(result)
assert session.page.user.filled == "test-user"
assert session.page.password.filled == "test-secret"


class TimeoutAfterSubmitControl(Control):
    def click(self, timeout=None, no_wait_after=None):
        assert timeout == 10000
        assert no_wait_after is True
        self.page.authenticated = True
        raise TimeoutError("simulated click wait timeout")


session = Session()
session.page.button = TimeoutAfterSubmitControl(session.page, "button")
result = scope["authenticate_saved_stand"](session, "uc.lab.local")
assert result["success"] is True
assert result["authentication_status"] == "authenticated"
assert result["submission_wait_status"] == "click_wait_error"
assert "error" not in result
assert "simulated click wait timeout" not in str(result)

session = Session()
session.page.url = "https://other.example.test/login"
result = scope["authenticate_saved_stand"](session, "uc.lab.local")
assert result["error"] == "saved_web_auth_origin_mismatch"
assert session.page.user.filled is None
assert session.page.password.filled is None

uqa_tree = ast.parse((root / "uqa.py").read_text(encoding="utf-8"))
uqa_names = {
    "classify_tool_action",
    "add_saved_web_auth_advisory",
}
uqa_functions = [
    node
    for node in uqa_tree.body
    if isinstance(node, ast.FunctionDef)
    and node.name in uqa_names
]
pending = {}
action_scope = {
    "re": re,
    "os": os,
    "_PENDING_CONSTRAINED_ACTIONS": pending,
}
exec(
    compile(ast.Module(body=uqa_functions, type_ignores=[]), "uqa.py", "exec"),
    action_scope,
)
assert action_scope["classify_tool_action"](
    "browser_authenticate_saved_stand",
    {"stand": "uc.lab.local"},
) == "interact"

auth_challenge = action_scope["add_saved_web_auth_advisory"](
    "browser_click_semantic",
    {
        "executed": True,
        "current_url": "https://uc.lab.local/administration/access-zones",
        "text_preview": "Login\nPassword\nSign in",
        "interactive_elements": [{
            "type": "password",
            "enabled": True,
        }],
    },
    "confirm_mutations",
    "job-smoke",
    "case-smoke",
)
assert auth_challenge["auth_challenge_status"] == "required"
candidate = auth_challenge["required_action_candidate"]
assert candidate == {
    "tool": "browser_authenticate_saved_stand",
    "arguments": {"stand": "uc.lab.local"},
    "action_class": "interact",
    "basis": (
        "UQA Core detected a visible Login/Password challenge and "
        "will keep credentials outside model context and evidence."
    ),
}
assert pending[("job-smoke", "case-smoke")] == candidate

registry_source = registry_path.read_text(encoding="utf-8")
assert '"name": "browser_authenticate_saved_stand"' in registry_source
assert '"required": ["stand"]' in registry_source

print("saved web-auth boundary smoke: PASS")
