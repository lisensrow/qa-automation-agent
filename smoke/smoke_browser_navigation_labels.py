import ast
import os
from pathlib import Path


root = Path(os.getenv("UQA_SMOKE_ROOT", "."))
tree = ast.parse(
    (root / "tools" / "browser.py").read_text(encoding="utf-8")
)
browser_class = next(
    node
    for node in tree.body
    if isinstance(node, ast.ClassDef)
    and any(
        isinstance(item, ast.FunctionDef)
        and item.name == "_element_is_effectively_disabled"
        for item in node.body
    )
)
method = next(
    item
    for item in browser_class.body
    if isinstance(item, ast.FunctionDef)
    and item.name == "_element_is_effectively_disabled"
)
module = ast.Module(
    body=[
        ast.ClassDef(
            name="BrowserProbe",
            bases=[],
            keywords=[],
            body=[method],
            decorator_list=[],
        )
    ],
    type_ignores=[],
)
scope = {}
exec(compile(ast.fix_missing_locations(module), "browser.py", "exec"), scope)
is_disabled = scope["BrowserProbe"]._element_is_effectively_disabled

assert is_disabled({"enabled": False}) is True
assert is_disabled({"disabled_attribute": True}) is True
assert is_disabled({"aria_disabled": "true"}) is True
assert is_disabled({"aria_disabled": "TRUE"}) is True
assert is_disabled({"enabled": True, "aria_disabled": "false"}) is False
assert is_disabled({}) is False

print("browser navigation-label eligibility smoke: PASS")
