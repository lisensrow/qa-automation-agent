import ast
import json
from pathlib import Path


tree = ast.parse(Path("uqa.py").read_text(encoding="utf-8"))
function = next(
    node
    for node in tree.body
    if isinstance(node, ast.FunctionDef)
    and node.name == "_cleanup_navigation_context"
)
scope = {"re": __import__("re"), "json": json}
exec(
    compile(ast.Module(body=[function], type_ignores=[]), "uqa.py", "exec"),
    scope,
)


def observation(tool, name):
    return {
        "data": {
            "tool": tool,
            "input": {"name": name},
        }
    }


job = {
    "request": (
        "Создай ресурс на https://uc.lab.local. "
        "После проверки удали его."
    ),
    "test_cases": [{
        "observations": [
            observation("browser_click_semantic", "plus"),
            observation("browser_click_semantic", "Administration"),
            observation("browser_click_semantic", "Access zones"),
            observation("browser_click_semantic", "Create"),
            observation("browser_click_semantic", "Save"),
        ]
    }],
}
scope["classify_tool_action"] = lambda tool, arguments: (
    "write"
    if arguments.get("name") in {"Create", "Save"}
    else "interact"
)
result = scope["_cleanup_navigation_context"](job)
assert result == {
    "urls": ["https://uc.lab.local"],
    "observed_navigation_before_first_mutation": [
        {
            "tool": "browser_click_semantic",
            "arguments": {"name": "plus"},
        },
        {
            "tool": "browser_click_semantic",
            "arguments": {"name": "Administration"},
        },
        {
            "tool": "browser_click_semantic",
            "arguments": {"name": "Access zones"},
        },
    ],
}
assert "Create" not in str(result)
assert "Save" not in str(result)
print("cleanup navigation context smoke: PASS")
