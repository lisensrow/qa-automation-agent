#!/opt/uqa/.venv/bin/python

import ast
from pathlib import Path


tree = ast.parse(Path("uqa.py").read_text(encoding="utf-8"))
function = next(
    node
    for node in tree.body
    if isinstance(node, ast.FunctionDef)
    and node.name == "_managed_initial_browser_open_url"
)
scope = {}
exec(
    compile(ast.Module(body=[function], type_ignores=[]), "uqa.py", "exec"),
    scope,
)
normalize = scope["_managed_initial_browser_open_url"]

url, reason = normalize(
    "https://stand.example.test/api/v1/resources",
    "Create one test resource",
    False,
)
assert url == "https://stand.example.test"
assert reason == "inferred_deep_link_normalized_to_origin"

explicit = "Open https://stand.example.test/ui/resources and verify it"
assert normalize(
    "https://stand.example.test/ui/resources",
    explicit,
    False,
) == ("https://stand.example.test/ui/resources", None)

assert normalize(
    "https://stand.example.test/ui/resources",
    "Create one test resource",
    True,
) == ("https://stand.example.test/ui/resources", None)

assert normalize(
    "https://stand.example.test",
    "Create one test resource",
    False,
) == ("https://stand.example.test", None)

assert normalize("not-a-url", "", False) == ("not-a-url", None)

print("smoke_managed_initial_browser_url: PASS")
