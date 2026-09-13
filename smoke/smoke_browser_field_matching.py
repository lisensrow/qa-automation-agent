import ast
import os
import re
from pathlib import Path


root = Path(os.getenv("UQA_SMOKE_ROOT", "."))
tree = ast.parse(
    (root / "tools" / "browser.py").read_text(encoding="utf-8")
)
function = next(
    node
    for node in tree.body
    if isinstance(node, ast.FunctionDef)
    and node.name == "_field_metadata_matches"
)
scope = {"re": re}
exec(
    compile(ast.Module(body=[function], type_ignores=[]), "browser.py", "exec"),
    scope,
)
matches = scope["_field_metadata_matches"]

assert matches(["name", "", ""], "Name", True) is True
assert matches(["NAME", "", ""], "name", True) is True
assert matches(["code", "", ""], "Mnemonic code", True) is True
assert matches(["displayName", "", ""], "name", True) is False
assert matches(["displayName", "", ""], "name", False) is True
assert matches(["", "", ""], "Name", True) is False

print("browser field metadata matching smoke: PASS")
