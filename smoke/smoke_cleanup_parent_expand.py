import ast
import re
from pathlib import Path


tree = ast.parse(Path("uqa.py").read_text(encoding="utf-8"))
function = next(
    node
    for node in tree.body
    if isinstance(node, ast.FunctionDef)
    and node.name == "_cleanup_parent_expand_candidate"
)
row_function = next(
    node
    for node in tree.body
    if isinstance(node, ast.FunctionDef)
    and node.name == "_cleanup_row_checkbox_available"
)
scope = {"re": re}
exec(
    compile(
        ast.Module(body=[function, row_function], type_ignores=[]),
        "uqa.py",
        "exec",
    ),
    scope,
)

resource = {"metadata": {"parent": "Master"}}
state = {
    "interactive_elements": [
        {
            "element_id": "wrong-row",
            "aria_label": "Expand",
            "icon_hints": ["chevron-right"],
            "enabled": True,
            "table_context": {"row_text": "CMDB\nCMDB"},
        },
        {
            "element_id": "expected",
            "aria_label": "Expand",
            "icon_hints": ["chevron-right"],
            "enabled": True,
            "table_context": {"row_text": "Master\nMASTER"},
        },
    ]
}
candidate = scope["_cleanup_parent_expand_candidate"](state, resource)
assert candidate == "expected"

state["interactive_elements"].append(dict(
    state["interactive_elements"][1],
    element_id="ambiguous",
))
assert scope["_cleanup_parent_expand_candidate"](state, resource) is None
assert scope["_cleanup_parent_expand_candidate"]({}, resource) is None

row_state = {
    "interactive_elements": [
        {
            "role": "checkbox",
            "type": "checkbox",
            "enabled": True,
            "table_context": {
                "row_text": "uqa-test-resource\nmetadata",
            },
        },
        {
            "role": "checkbox",
            "type": "checkbox",
            "enabled": True,
            "table_context": {"row_text": "other-resource"},
        },
    ]
}
assert scope["_cleanup_row_checkbox_available"](
    row_state,
    {"name": "uqa-test-resource"},
)
row_state["interactive_elements"].append(dict(
    row_state["interactive_elements"][0]
))
assert not scope["_cleanup_row_checkbox_available"](
    row_state,
    {"name": "uqa-test-resource"},
)
print("cleanup parent-expand smoke: PASS")
