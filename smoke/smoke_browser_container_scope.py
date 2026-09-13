import ast
import os
from pathlib import Path


root = Path(os.getenv("UQA_SMOKE_ROOT", "."))
browser_path = root / "tools" / "browser.py"
registry_path = root / "tools" / "registry.py"
uqa_path = root / "uqa.py"
browser_tree = ast.parse(browser_path.read_text(encoding="utf-8"))
browser_class = next(
    node for node in browser_tree.body
    if isinstance(node, ast.ClassDef) and node.name == "BrowserSession"
)
methods = {
    node.name: node
    for node in browser_class.body
    if isinstance(node, ast.FunctionDef)
}
module_functions = {
    node.name: node
    for node in browser_tree.body
    if isinstance(node, ast.FunctionDef)
}
assert "container" in [arg.arg for arg in methods["click_semantic"].args.args]
assert "container" in [
    arg.arg for arg in module_functions["click_semantic"].args.args
]
source = browser_path.read_text(encoding="utf-8")
assert "lines.includes(wanted)" in source
assert "semantic_container" in source
registry = registry_path.read_text(encoding="utf-8")
assert '"container": {' in registry
uqa = uqa_path.read_text(encoding="utf-8")
assert '"container": str(' in uqa
assert '"name": "Expand"' in uqa
print("browser container-scope smoke: PASS")
