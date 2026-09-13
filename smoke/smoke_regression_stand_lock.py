import ast
import re
from pathlib import Path


tree = ast.parse(Path("uqa.py").read_text(encoding="utf-8"))
module = ast.Module(
    body=[
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_lock_regression_plan_stand"
    ],
    type_ignores=[],
)


def get_stand(stand):
    assert stand == "uc.lab.local"
    return {
        "stand_id": "uc.lab.local",
        "web_url": "https://uc.lab.local",
    }


scope = {
    "get_stand": get_stand,
    "re": re,
}
exec(compile(module, "uqa.py", "exec"), scope)

source = [{
    "title": "Same stand",
    "task": (
        "Open https://uc.lab.local:8080, then verify "
        "https://uc.lab.local:8080/access/zones. "
        "Broken planner punctuation https://uc.lab.local:."
    ),
    "expected": "https://uc.lab.local:8080 must work",
    "checks": [{
        "title": "At https://uc.lab.local:8080/access/zones",
        "expected": "Keep unrelated https://docs.example.test/page unchanged",
    }],
}]
locked = scope["_lock_regression_plan_stand"](
    source,
    "uc.lab.local",
)

assert ":8080" not in str(locked)
assert "https://uc.lab.local:." not in str(locked)
assert "https://uc.lab.local/access/zones" in locked[0]["task"]
assert "https://docs.example.test/page" in locked[0]["checks"][0]["expected"]
assert ":8080" in str(source), "function must not mutate the planner output"

print("regression stand-origin lock smoke: PASS")
